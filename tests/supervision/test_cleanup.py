import json
import os
from pathlib import Path
import time

import psutil
import pytest


def wait_until(predicate, timeout=6):
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        if predicate():
            return
        time.sleep(0.03)
    assert predicate(), "condition did not become true within bounded timeout"


def test_reused_pid_and_forged_handle_are_never_killed(supervisor, spec, owner):
    handle = supervisor.start(spec, owner)
    forged = handle.model_copy(update={"process_started_at": handle.process_started_at - 1})
    assert supervisor.stop(forged).status == "OWNERSHIP_UNVERIFIED"
    assert psutil.pid_exists(handle.pid)
    forged_owner = handle.model_copy(update={"owner": owner.model_copy(update={"run_id": "other"})})
    assert supervisor.stop(forged_owner).status == "OWNERSHIP_UNVERIFIED"
    assert supervisor.stop(handle).status == "CLEANED"


def test_unicode_path_and_metacharacters_are_literal(supervisor, spec, owner):
    cwd = spec.cwd / "งาน ทดสอบ"
    cwd.mkdir()
    output = cwd / "result.json"
    args = ["a&b", "$(noop)", 'a"b', "trail\\", "", "ไทย"]
    changed = spec.model_copy(update={"cwd": cwd, "argv": [spec.argv[0], "echo", str(output), *args]})
    handle = supervisor.start(changed, owner)
    wait_until(output.exists)
    assert json.loads(output.read_text(encoding="utf-8")) == args
    wait_until(lambda: supervisor.receipt(handle.id) is not None)
    assert supervisor.ledger.active_count() == 0


@pytest.mark.parametrize("mode", ["tree", "detached"])
def test_stop_cleans_descendants(supervisor, spec, owner, mode):
    if mode == "detached" and os.name != "nt":
        pytest.skip("macOS detached workloads are denied, not group-contained")
    output = Path(spec.argv[2])
    handle = supervisor.start(spec.model_copy(update={"argv": [spec.argv[0], mode, str(output)]}), owner)
    wait_until(output.exists)
    pids = json.loads(output.read_text())
    identities = [(pid, psutil.Process(pid).create_time()) for pid in pids]
    assert supervisor.stop(handle, grace_seconds=0.1).status == "CLEANED"
    def gone():
        return all(not psutil.pid_exists(pid) or psutil.Process(pid).create_time() != started for pid, started in identities)
    wait_until(gone)
    assert supervisor.ledger.active_count() == 0


@pytest.mark.parametrize("mode", ["echo", "fail", "timeout"])
def test_exit_failure_and_timeout_release_lease(supervisor, spec, owner, mode):
    argv = [spec.argv[0], "sleep" if mode == "timeout" else mode, spec.argv[2]]
    handle = supervisor.start(spec.model_copy(update={"argv": argv, "timeout_seconds": 0.2}), owner)
    wait_until(lambda: supervisor.receipt(handle.id) is not None)
    assert supervisor.receipt(handle.id).status == "CLEANED"
    assert supervisor.ledger.active_count() == 0


def test_failed_launch_releases_reservation(supervisor, spec, owner):
    with pytest.raises(OSError):
        supervisor.start(spec.model_copy(update={"executable": spec.cwd / "absent.exe"}), owner)
    assert supervisor.ledger.active_count() == 0


def test_scratch_marker_and_path_escape_are_refused(supervisor, spec, owner, tmp_path):
    handle = supervisor.start(spec, owner)
    scratch = handle.owned_paths[0]
    foreign = tmp_path / "foreign"
    foreign.mkdir()
    (foreign / "important.txt").write_text("keep")
    if os.name == "nt":
        import subprocess
        # Windows junction needs no symlink privilege; exact test-owned directories only.
        subprocess.run(["cmd", "/c", "mklink", "/J", str(scratch / "escape"), str(foreign)], check=True, capture_output=True)
    else:
        (scratch / "escape").symlink_to(foreign, target_is_directory=True)
    result = supervisor.stop(handle, grace_seconds=0.1)
    assert result.status == "CLEANUP_PENDING"
    assert (foreign / "important.txt").read_text() == "keep"
    (scratch / "escape").rmdir() if os.name == "nt" else (scratch / "escape").unlink()
    assert supervisor.stop(handle).status == "CLEANED"


def test_missing_marker_keeps_scratch_and_receipt(supervisor, spec, owner):
    handle = supervisor.start(spec, owner)
    marker = handle.owned_paths[0] / ".owner"
    original = marker.read_text()
    marker.write_text("foreign")
    assert supervisor.stop(handle).status == "CLEANUP_PENDING"
    assert marker.exists()
    marker.write_text(original)
    assert supervisor.stop(handle).status == "CLEANED"


def test_two_pressure_samples_stop_owned_workload(supervisor, spec, owner, sample):
    handle = supervisor.start(spec, owner)
    low = sample.model_copy(update={"available_ram_bytes": 2**29})
    supervisor.sampler = lambda: low
    wait_until(lambda: supervisor.receipt(handle.id) is not None)
    assert supervisor.receipt(handle.id).status == "CLEANED"
    assert not psutil.pid_exists(handle.pid)
    from project_builder.supervision.ledger import admit
    assert not admit(spec.budget, sample, supervisor.ledger).allowed


def test_observed_pid_reuse_refuses_native_signal(supervisor, spec, owner, monkeypatch):
    from project_builder.supervision import supervisor as module
    handle = supervisor.start(spec, owner)
    real = module.identity_state
    monkeypatch.setattr(module, "identity_state", lambda pid, started: "reused")
    assert supervisor.stop(handle, 0).status == "OWNERSHIP_UNVERIFIED"
    assert psutil.pid_exists(handle.pid)
    monkeypatch.setattr(module, "identity_state", real)
    assert supervisor.stop(handle, 0).status == "CLEANED"


def test_pending_receipt_is_not_proof_of_workload_exit(supervisor, spec, owner, monkeypatch):
    from project_builder.supervision import supervisor as module
    from project_builder.supervision.models import CleanupReceipt
    handle = supervisor.start(spec, owner)
    active = supervisor._live.pop(handle.id)
    try:
        supervisor.ledger.save_receipt(CleanupReceipt(handle_id=handle.id, status="CLEANUP_PENDING", reason="unverified"))
        monkeypatch.setattr(module, "identity_state", lambda pid, started: "gone" if pid == handle.pid else "same")
        assert supervisor.stop(handle, 0).status == "CLEANUP_PENDING"
        assert supervisor.ledger.active_count() == 1
    finally:
        supervisor._live[handle.id] = active
        monkeypatch.undo()


def test_closed_supervisor_has_no_monitor_thread(ledger, sample):
    from project_builder.supervision.supervisor import Supervisor
    instance = Supervisor(ledger, sampler=lambda: sample)
    instance.close()
    assert not instance._thread.is_alive()


@pytest.mark.parametrize("change", [
    {"argv": ["bad\0arg"]}, {"env": {"BAD=KEY": "v"}},
    {"executable": Path("C:/Windows/System32/cmd.exe")},
    {"executable": Path("C:/unsafe.cmd")},
])
def test_execution_boundary_revalidates_unsafe_spec(supervisor, spec, owner, change):
    with pytest.raises(ValueError):
        supervisor.start(spec.model_copy(update=change), owner)
    assert supervisor.ledger.active_count() == 0
