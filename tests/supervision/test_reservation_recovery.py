import os
from pathlib import Path
import subprocess
import sys
import pytest

@pytest.mark.skipif(sys.platform!="win32",reason="native Windows crash phase probe")
@pytest.mark.parametrize("phase",["reserved","before-persist"])
def test_dead_launcher_reservations_are_reconciled_without_ttl(tmp_path,phase):
    fixture=Path(__file__).parents[1]/"fixtures"/"crash_reservation.py"
    environment=dict(os.environ);environment["PYTHONPATH"]=str(Path(__file__).parents[2]/"src")
    result=subprocess.run([sys.executable,str(fixture),str(tmp_path/"state"),phase],env=environment,
        capture_output=True,timeout=10,creationflags=subprocess.CREATE_NO_WINDOW)
    assert result.returncode==73,result.stderr.decode()
    from project_builder.supervision.ledger import ResourceLedger
    from project_builder.supervision.supervisor import Supervisor
    ledger=ResourceLedger(tmp_path/"state")
    assert ledger.active_count()==1
    with Supervisor(ledger) as supervisor:
        receipts=supervisor.reconcile()
    assert receipts and all(r.status=="CLEANED" for r in receipts)
    assert ledger.active_count()==0

def test_missing_program_is_rejected_before_launch_on_all_drivers(supervisor,spec,owner,monkeypatch):
    from project_builder.supervision.supervisor import Supervisor
    monkeypatch.setattr(sys,"platform","darwin")
    with pytest.raises(FileNotFoundError):
        supervisor.start(spec.model_copy(update={"executable":spec.cwd/"missing-program"}),owner)
    assert supervisor.ledger.active_count()==0
