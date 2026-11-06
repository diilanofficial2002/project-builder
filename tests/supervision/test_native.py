"""Native probes: tiny bounded processes; skipped platforms are NOT native PASS."""
import json
import os
from pathlib import Path
import subprocess
import sys
import time

import psutil
import pytest

from test_cleanup import wait_until


@pytest.mark.skipif(sys.platform != "win32", reason="native Windows Job probe")
def test_assignment_failure_never_runs_child_and_closes_handles(supervisor, spec, owner, monkeypatch):
    from project_builder.supervision import windows_job
    import ctypes
    real_api = windows_job._api
    pids = []
    class RejectAssignment:
        def __init__(self):
            self.api = real_api()
        def __getattr__(self, name):
            return getattr(self.api, name)
        def IsProcessInJob(self, process, job, result):
            pids.extend(item.pid for item in psutil.Process().children() if item.pid not in pids)
            ctypes.set_last_error(5)
            return 0
    monkeypatch.setattr(windows_job, "_api", RejectAssignment)
    output = Path(spec.argv[2])
    with pytest.raises(OSError):
        supervisor.start(spec.model_copy(update={"argv": [spec.argv[0], "echo", str(output), "ran"]}), owner)
    assert not output.exists()
    assert pids and all(not psutil.pid_exists(pid) for pid in pids)
    assert supervisor.ledger.active_count() == 0


@pytest.mark.skipif(sys.platform not in {"win32", "darwin"}, reason="native supported OS only")
def test_parent_crash_cleans_descendants_and_preserves_foreign_process(tmp_path, spec):
    # Every signaled process is a Popen directly created by this fixture.
    harness = Path(__file__).parents[1] / "fixtures" / "crash_parent.py"
    output, state, handle_file = tmp_path / "pids.json", tmp_path / "state", tmp_path / "handle.json"
    environment = dict(os.environ)
    environment["PYTHONPATH"] = str(Path(__file__).parents[2] / "src")
    flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
    foreign = subprocess.Popen([sys.executable, spec.argv[0], "sleep", str(tmp_path / "foreign")], creationflags=flags)
    parent = None
    try:
        foreign_started = psutil.Process(foreign.pid).create_time()
        parent = subprocess.Popen([sys.executable, str(harness), str(state), str(output), str(handle_file), spec.argv[0]],
                                  env=environment, creationflags=flags, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        wait_until(lambda: (output.exists() and handle_file.exists()) or parent.poll() is not None)
        assert parent.poll() is None, parent.stderr.read(8192).decode(errors="replace")
        pids = json.loads(output.read_text())
        identities = [(pid, psutil.Process(pid).create_time()) for pid in pids]
        parent.kill()
        parent.wait(timeout=5)
        def all_gone():
            for pid, started in identities:
                try:
                    proc = psutil.Process(pid)
                    if proc.create_time() == started and proc.status() != psutil.STATUS_ZOMBIE:
                        return False
                except psutil.NoSuchProcess:
                    pass
            return True
        wait_until(all_gone)
        assert foreign.poll() is None and psutil.Process(foreign.pid).create_time() == foreign_started
        from project_builder.supervision.ledger import ResourceLedger
        from project_builder.supervision.supervisor import Supervisor
        with Supervisor(ResourceLedger(state)) as supervisor:
            receipts = supervisor.reconcile()
            if sys.platform == "win32":
                assert receipts and all(receipt.status == "CLEANED" for receipt in receipts)
                assert supervisor.ledger.active_count() == 0
            else:
                # Watchdog's persisted completion proof is required for cooperative groups.
                assert receipts and all(receipt.status == "CLEANED" for receipt in receipts)
    finally:
        for process in [parent, foreign]:
            if process is not None:
                if process.poll() is None:
                    process.kill()
                process.wait(timeout=5)
                if process.stderr:
                    process.stderr.close()


@pytest.mark.skipif(sys.platform != "darwin", reason="native macOS watchdog NOT_RUN on Windows")
def test_macos_rejects_unapproved_or_tree_containment(supervisor, spec, owner):
    from project_builder.supervision.supervisor import AdmissionDenied
    for change in [{"containment": "contained_tree"}, {"trusted_recipe_id": None}, {"trusted_recipe_id": "unapproved"}]:
        with pytest.raises(AdmissionDenied):
            supervisor.start(spec.model_copy(update=change), owner)
    assert supervisor.ledger.active_count() == 0
