"""Crash exactly before a handle is persisted, testing phase-specific recovery."""
import os
from pathlib import Path
import sys
from project_builder.supervision.ledger import ResourceLedger,admit
from project_builder.supervision.models import ResourceRequest,MachineSample,ProcessSpec
from project_builder.supervision.supervisor import Supervisor
from project_builder.contracts import RunIdentity

root,phase=Path(sys.argv[1]),sys.argv[2]
ledger=ResourceLedger(root)
sample=MachineSample(total_ram_bytes=8*2**30,available_ram_bytes=6*2**30,disk_total_bytes=100*2**30,disk_free_bytes=50*2**30)
request=ResourceRequest(project_id="crash-reservation",memory_bytes=32*2**20)
if phase=="reserved":
    assert admit(request,sample,ledger).allowed
    os._exit(73)
supervisor=Supervisor(ledger,sampler=lambda:sample)
ledger.persist=lambda *args:os._exit(73)
supervisor.start(ProcessSpec(executable=Path(sys.executable),argv=["-c","import time;time.sleep(15)"],cwd=root,env={},budget=request,timeout_seconds=20.0),
    RunIdentity(project_id="crash-reservation",run_id="r",scope_id="s",stage="final",contract_revision=1))
