"""Lifecycle coordinator; persisted identity is authoritative, handles are not authority."""
import math
import os
from pathlib import Path
import secrets
import sys
import threading
import time
import uuid

import psutil

from project_builder.contracts import RunIdentity
from project_builder.platform_paths import reject_links
from .ledger import ResourceLedger, admit
from .models import CleanupReceipt, MachineSample, ProcessSpec, ResourceHandle
from .scratch import remove_scratch


def identity_state(pid: int, started: float) -> str:
    """Return same/gone/reused/unknown without signaling anything."""
    try:
        process = psutil.Process(pid)
        if process.create_time() != started:
            return "reused"
        if process.status() == psutil.STATUS_ZOMBIE:
            return "gone"
        return "same"
    except psutil.NoSuchProcess:
        return "gone"
    except (psutil.AccessDenied, OSError):
        return "unknown"


class AdmissionDenied(RuntimeError):
    pass


class Supervisor:
    def __init__(self, ledger: ResourceLedger | None = None, *, sampler=None, interval: float = 2.0,
                 trusted_group_recipes: frozenset[str] = frozenset()):
        if not math.isfinite(interval) or not 0 < interval <= 2:
            raise ValueError("monitor interval must be in (0, 2] seconds")
        self.ledger = ledger or ResourceLedger()
        self.scratch_root = self.ledger.root / "scratch"
        reject_links(self.scratch_root)
        self.scratch_root.mkdir(exist_ok=True, mode=0o700)
        self.sampler = sampler or self.sample
        self.interval = interval
        self.trusted_group_recipes = trusted_group_recipes
        self._lock = threading.RLock()
        self._live = {}
        self._halt = threading.Event()
        self._closed = False
        self._pressure_samples = 0
        self._thread = threading.Thread(target=self._monitor, name="project-builder-supervisor", daemon=True)
        self._thread.start()

    def sample(self) -> MachineSample:
        memory, disk = psutil.virtual_memory(), psutil.disk_usage(str(self.ledger.root))
        return MachineSample(total_ram_bytes=memory.total, available_ram_bytes=memory.available,
                             disk_total_bytes=disk.total, disk_free_bytes=disk.free)

    def start(self, spec: ProcessSpec, owner: RunIdentity) -> ResourceHandle:
        spec = ProcessSpec.model_validate(spec.model_dump())
        owner = RunIdentity.model_validate(owner.model_dump())
        if spec.budget.project_id != owner.project_id:
            raise ValueError("budget project does not match owner")
        if sys.platform == "darwin":
            if spec.containment != "cooperative_group" or not spec.trusted_recipe_id or spec.trusted_recipe_id not in self.trusted_group_recipes:
                raise AdmissionDenied("macOS requires an explicitly configured trusted cooperative recipe; detached/untrusted trees unsupported")
        elif sys.platform != "win32":
            raise AdmissionDenied("native containment unsupported on this platform")
        with self._lock:
            if self._closed:
                raise RuntimeError("supervisor is closed")
            decision = admit(spec.budget, self.sampler(), self.ledger)
            if not decision.allowed:
                raise AdmissionDenied(decision.code)
            lease = decision.lease_id
            handle_id, token = uuid.uuid4().hex, secrets.token_hex(32)
            scratch = self.scratch_root / handle_id
            backend = None
            try:
                reject_links(self.scratch_root)
                scratch.mkdir(mode=0o700)
                (scratch / ".owner").write_text(token, encoding="utf-8")
                if sys.platform == "win32":
                    from .windows_job import WindowsJob
                    backend = WindowsJob(spec, handle_id)
                else:
                    from .macos_group import MacOSGroup
                    backend = MacOSGroup(spec, scratch, token)
                handle = ResourceHandle(id=handle_id, owner=owner, pid=backend.pid,
                    process_started_at=backend.started, process_group_id=backend.process_group_id,
                    owned_paths=[scratch], lease_id=lease, owner_token=token, containment=spec.containment)
                self.ledger.persist(handle, os.getpid(), psutil.Process().create_time())
                self._live[handle.id] = (handle, backend, time.monotonic() + spec.timeout_seconds)
                backend.resume()
                return handle
            except BaseException:
                self._live.pop(handle_id, None)
                try:
                    if backend is not None:
                        backend.stop(0)
                finally:
                    if backend is not None:
                        backend.close()
                    self.ledger.release(lease)
                    if scratch.exists():
                        remove_scratch(self.scratch_root, scratch, token)
                raise

    def stop(self, handle: ResourceHandle, grace_seconds: float = 5.0) -> CleanupReceipt:
        if not math.isfinite(grace_seconds) or not 0 <= grace_seconds <= 30:
            raise ValueError("grace must be between 0 and 30 seconds")
        with self._lock:
            saved = self.ledger.resolve(handle.id)
            if saved is None or saved != handle:
                return CleanupReceipt(handle_id=handle.id, status="OWNERSHIP_UNVERIFIED", reason="handle differs from authoritative ledger")
            prior = self.ledger.receipt(handle.id)
            if prior and prior.status == "CLEANED":
                return prior
            state = identity_state(saved.pid, saved.process_started_at)
            if state in {"reused", "unknown"}:
                receipt = CleanupReceipt(handle_id=handle.id, status="OWNERSHIP_UNVERIFIED", reason=f"PID identity {state}; no signal sent")
                self.ledger.save_receipt(receipt)
                return receipt
            active = self._live.get(saved.id)
            exit_code = None
            if active:
                backend = active[1]
                try:
                    exit_code = backend.poll()
                    backend.stop(grace_seconds)
                    exit_code = backend.poll() if exit_code is None else exit_code
                except (OSError, RuntimeError, TimeoutError) as error:
                    receipt = CleanupReceipt(handle_id=handle.id, status="CLEANUP_PENDING", reason=str(error))
                    self.ledger.save_receipt(receipt)
                    return receipt
                backend.close()
                self._live.pop(saved.id, None)
            elif state != "gone":
                receipt = CleanupReceipt(handle_id=handle.id, status="CLEANUP_PENDING", reason="native containment handle unavailable; no PID-only kill")
                self.ledger.save_receipt(receipt)
                return receipt
            elif not prior or not prior.workload_stopped:
                # Reconciliation needs separate proof that the original launcher exited.
                records = {record.id: (pid, started) for record, pid, started in self.ledger.records()}
                launcher = records.get(saved.id)
                if not launcher or identity_state(*launcher) not in {"gone", "reused"}:
                    receipt = CleanupReceipt(handle_id=handle.id, status="CLEANUP_PENDING", reason="launcher/group containment not verified after restart")
                    self.ledger.save_receipt(receipt)
                    return receipt
                try:
                    if sys.platform == "win32":
                        from .windows_job import reconcile_job
                        reconcile_job(saved.id)
                    elif sys.platform == "darwin":
                        from .macos_group import verify_completion
                        verify_completion(saved.owned_paths[0], saved.owner_token)
                    else:
                        raise RuntimeError("unsupported containment")
                except (OSError, ValueError, RuntimeError) as error:
                    receipt = CleanupReceipt(handle_id=handle.id, status="CLEANUP_PENDING", reason=str(error))
                    self.ledger.save_receipt(receipt)
                    return receipt
            self.ledger.release(saved.lease_id)
            removed = []
            try:
                if saved.owned_paths != [self.scratch_root / saved.id]:
                    raise ValueError("ledger scratch boundary mismatch")
                for path in saved.owned_paths:
                    remove_scratch(self.scratch_root, path, saved.owner_token)
                    removed.append(path)
                receipt = CleanupReceipt(handle_id=saved.id, status="CLEANED", reason="owned containment exited and scratch removed",
                                         exit_code=exit_code, paths_removed=removed, workload_stopped=True)
            except (OSError, ValueError, TimeoutError) as error:
                receipt = CleanupReceipt(handle_id=saved.id, status="CLEANUP_PENDING", reason=str(error), exit_code=exit_code, paths_removed=removed, workload_stopped=True)
            self.ledger.save_receipt(receipt)
            return receipt

    def receipt(self, handle_id: str) -> CleanupReceipt | None:
        return self.ledger.receipt(handle_id)

    def reconcile(self) -> list[CleanupReceipt]:
        return [self.stop(handle, 0) for handle, _, _ in self.ledger.records()]

    def _monitor(self):
        while not self._halt.wait(self.interval):
            with self._lock:
                try:
                    sample = self.sampler()
                    self._pressure_samples = self._pressure_samples + 1 if sample.pressured else 0
                    self.ledger.set_pressure(self._pressure_samples >= 2)
                    for handle, backend, deadline in list(self._live.values()):
                        if self._pressure_samples >= 2 or time.monotonic() >= deadline or backend.poll() is not None:
                            self.stop(handle, 0)
                        else:
                            self.ledger.heartbeat(handle.lease_id)
                except Exception as error:
                    # Fail closed on sampling/ledger failures; persist what can be persisted.
                    for handle, backend, _ in list(self._live.values()):
                        try:
                            self.stop(handle, 0)
                        except Exception:
                            backend.close()  # Windows kill-on-close; Mac watchdog handles control EOF
                    self._halt.set()

    def close(self):
        self._halt.set()
        self._thread.join(timeout=40)
        with self._lock:
            self._closed = True
            for handle, backend, _ in list(self._live.values()):
                try:
                    self.stop(handle, 0)
                finally:
                    backend.close()
            self._live.clear()
        if self._thread.is_alive():
            raise RuntimeError("supervisor monitor did not stop")

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()
