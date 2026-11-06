"""Read-only pending queries and project-scoped cleanup. Public execution fails closed."""
import json
from pathlib import Path
import sqlite3
from contextlib import closing
from project_builder.platform_paths import PlatformPaths, reject_links
from project_builder.supervision.supervisor import Supervisor


def pending_resources(project_id):
    path=PlatformPaths.user_state_root()/"resources.sqlite3"
    reject_links(path)
    if not path.exists(): return []
    with closing(sqlite3.connect(path.resolve().as_uri()+"?mode=ro",uri=True,timeout=2)) as db:
        pending={row[0] for row in db.execute("SELECT id FROM leases WHERE project=? AND active=1",(project_id,))}
        for lease,receipt in db.execute("SELECT l.id,h.receipt FROM leases l JOIN handles h ON h.lease=l.id WHERE l.project=?",(project_id,)):
            if receipt is None or json.loads(receipt).get("status")!="CLEANED": pending.add(lease)
        if db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='launch_intents'").fetchone():
            pending.update(row[0] for row in db.execute("SELECT l.id FROM leases l JOIN launch_intents i ON i.lease=l.id WHERE l.project=? AND i.phase='cleanup_pending'",(project_id,)))
        return sorted(pending)


def cleanup_project(project_id):
    if not pending_resources(project_id): return {"status":"CLEANED","receipts":[]}
    with Supervisor() as supervisor:
        receipts=[r.model_dump(mode="json") for r in supervisor.reconcile(project_id)]
    return {"status":"CLEANED" if not pending_resources(project_id) else "CLEANUP_PENDING","receipts":receipts}
