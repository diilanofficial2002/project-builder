"""Atomic user-machine reservations. TTL marks stale leases; it NEVER frees capacity."""
from contextlib import contextmanager
import os
from pathlib import Path
import sqlite3
import time
import uuid
import json
import psutil

from project_builder.platform_paths import PlatformPaths, reject_links, verify_owner
from .models import AdmissionDecision, CleanupReceipt, MachineSample, ResourceHandle, ResourceRequest


class ResourceLedger:
    """Default root is shared across all projects/hosts of the current OS user.

    Explicit roots are for isolated installations/tests, never a project-local default.
    SQLite is trusted user state, not an authentication boundary against that same user.
    """
    def __init__(self, root: Path | None = None):
        self.root = (root or PlatformPaths.user_state_root()).absolute()
        reject_links(self.root)
        self.root.mkdir(parents=True, exist_ok=True, mode=0o700)
        verify_owner(self.root)
        self.path = self.root / "resources.sqlite3"
        with self.transaction() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS leases (
                    id TEXT PRIMARY KEY, project TEXT NOT NULL, memory INTEGER NOT NULL,
                    disk INTEGER NOT NULL, heavy INTEGER NOT NULL, specialist INTEGER NOT NULL,
                    heartbeat REAL NOT NULL, active INTEGER NOT NULL DEFAULT 1);
                CREATE TABLE IF NOT EXISTS handles (
                    id TEXT PRIMARY KEY, lease TEXT UNIQUE NOT NULL, body TEXT NOT NULL,
                    receipt TEXT, launcher_pid INTEGER NOT NULL, launcher_started REAL NOT NULL);
                CREATE TABLE IF NOT EXISTS policy (id INTEGER PRIMARY KEY CHECK(id=1), pressure INTEGER NOT NULL);
                INSERT OR IGNORE INTO policy VALUES(1, 0);
                CREATE TABLE IF NOT EXISTS launch_intents (
                    lease TEXT PRIMARY KEY,launcher_pid INTEGER NOT NULL,launcher_started REAL NOT NULL,
                    phase TEXT NOT NULL,body TEXT NOT NULL);
            """)

    @contextmanager
    def transaction(self):
        verify_owner(self.root)
        for suffix in ("", "-journal", "-wal", "-shm"):
            path = Path(str(self.path) + suffix)
            reject_links(path)
            if path.exists():
                try:
                    verify_owner(path)
                except FileNotFoundError:
                    if not suffix:
                        raise
                    # A concurrent SQLite commit legitimately unlinks sidecars.
                    # Permission/link errors still fail closed.
        db = sqlite3.connect(self.path, timeout=15)
        db.row_factory = sqlite3.Row
        try:
            db.execute("BEGIN IMMEDIATE")
            yield db
            db.commit()
        except BaseException:
            db.rollback()
            raise
        finally:
            db.close()

    def active_count(self) -> int:
        with self.transaction() as db:
            return db.execute("SELECT COUNT(*) FROM leases WHERE active=1").fetchone()[0]

    def heartbeat(self, lease_id: str, now: float | None = None) -> None:
        with self.transaction() as db:
            db.execute("UPDATE leases SET heartbeat=? WHERE id=? AND active=1", (time.time() if now is None else now, lease_id))

    def release(self, lease_id: str) -> None:
        """Trusted supervisor only: release after proven containment exit, never on TTL."""
        with self.transaction() as db:
            db.execute("UPDATE leases SET active=0 WHERE id=?", (lease_id,))

    def persist(self, handle: ResourceHandle, launcher_pid: int, launcher_started: float) -> None:
        with self.transaction() as db:
            row = db.execute("SELECT project, active FROM leases WHERE id=?", (handle.lease_id,)).fetchone()
            if not row or not row["active"] or row["project"] != handle.owner.project_id:
                raise ValueError("handle has no matching active reservation")
            db.execute("INSERT INTO handles VALUES(?,?,?,NULL,?,?)", (handle.id, handle.lease_id,
                       handle.model_dump_json(), launcher_pid, launcher_started))

    def resolve(self, handle_id: str) -> ResourceHandle | None:
        with self.transaction() as db:
            row = db.execute("SELECT body FROM handles WHERE id=?", (handle_id,)).fetchone()
            return ResourceHandle.model_validate_json(row[0]) if row else None

    def records(self) -> list[tuple[ResourceHandle, int, float]]:
        with self.transaction() as db:
            rows = db.execute("SELECT h.* FROM handles h JOIN leases l ON h.lease=l.id WHERE l.active=1 OR h.receipt IS NULL OR h.receipt LIKE '%CLEANUP_PENDING%'").fetchall()
            return [(ResourceHandle.model_validate_json(row["body"]), row["launcher_pid"], row["launcher_started"]) for row in rows]

    def prepare(self,lease_id,body):
        with self.transaction() as db:
            changed=db.execute("UPDATE launch_intents SET phase='preparing',body=? WHERE lease=? AND phase='reserved'",
                (json.dumps(body),lease_id)).rowcount
            if changed!=1: raise ValueError("reservation is not eligible to launch")

    def orphan_reservations(self):
        with self.transaction() as db:
            rows=db.execute("SELECT l.id,l.project,i.launcher_pid,i.launcher_started,i.phase,i.body FROM leases l LEFT JOIN launch_intents i ON i.lease=l.id LEFT JOIN handles h ON h.lease=l.id WHERE h.id IS NULL AND (l.active=1 OR i.phase='cleanup_pending')").fetchall()
            return [dict(row)|{"body":json.loads(row["body"]) if row["body"] else {}} for row in rows]

    def finish_intent(self,lease_id,phase):
        with self.transaction() as db: db.execute("UPDATE launch_intents SET phase=? WHERE lease=?",(phase,lease_id))

    def save_receipt(self, receipt: CleanupReceipt) -> None:
        with self.transaction() as db:
            db.execute("UPDATE handles SET receipt=? WHERE id=?", (receipt.model_dump_json(), receipt.handle_id))

    def receipt(self, handle_id: str) -> CleanupReceipt | None:
        with self.transaction() as db:
            row = db.execute("SELECT receipt FROM handles WHERE id=?", (handle_id,)).fetchone()
            return CleanupReceipt.model_validate_json(row[0]) if row and row[0] else None

    def set_pressure(self, blocked: bool) -> None:
        with self.transaction() as db:
            db.execute("UPDATE policy SET pressure=? WHERE id=1", (int(blocked),))


def admit(spec: ResourceRequest, sample: MachineSample, ledger: ResourceLedger) -> AdmissionDecision:
    """Check and reserve in ONE BEGIN IMMEDIATE transaction; caller owns returned lease."""
    # Revalidate model_copy/constructed values at the execution boundary.
    spec = ResourceRequest.model_validate(spec.model_dump())
    sample = MachineSample.model_validate(sample.model_dump())
    with ledger.transaction() as db:
        code = "ADMITTED"
        used = db.execute("SELECT COALESCE(SUM(memory),0), COALESCE(SUM(disk),0), COALESCE(SUM(heavy),0), COALESCE(SUM(specialist),0) FROM leases WHERE active=1").fetchone()
        if spec.memory_bytes is None:
            code = "UNKNOWN_FOOTPRINT"
        elif db.execute("SELECT pressure FROM policy WHERE id=1").fetchone()[0] or sample.pressured:
            code = "RESOURCE_PRESSURE"
        elif spec.heavy and used[2] >= 1 or spec.specialist and used[3] >= 1:
            code = "GLOBAL_CONCURRENCY_LIMIT"
        elif sample.available_ram_bytes - used[0] - spec.memory_bytes < sample.ram_reserve:
            code = "RAM_RESERVE"
        elif sample.disk_free_bytes - used[1] - spec.disk_bytes < sample.disk_reserve:
            code = "DISK_RESERVE"
        if code != "ADMITTED":
            return AdmissionDecision(allowed=False, code=code)
        lease = uuid.uuid4().hex
        db.execute("INSERT INTO leases VALUES(?,?,?,?,?,?,?,1)", (lease, spec.project_id, spec.memory_bytes,
                   spec.disk_bytes, int(spec.heavy), int(spec.specialist), time.time()))
        db.execute("INSERT INTO launch_intents VALUES(?,?,?,'reserved','{}')",(lease,os.getpid(),psutil.Process().create_time()))
        return AdmissionDecision(allowed=True, code=code, lease_id=lease)
