"""Deliberately crashable supervisor parent, created only by native test harness."""
from pathlib import Path
import sys
import time

from project_builder.contracts import RunIdentity
from project_builder.supervision.ledger import ResourceLedger
from project_builder.supervision.models import ProcessSpec, ResourceRequest
from project_builder.supervision.supervisor import Supervisor

root, output, handle_file, fixture = sys.argv[1:]
supervisor = Supervisor(ResourceLedger(Path(root)), trusted_group_recipes=frozenset({"native-fixture"}))
owner = RunIdentity(project_id="crash", run_id="run", scope_id="scope", stage="poc", contract_revision=1)
spec = ProcessSpec(executable=Path(sys.executable), argv=[fixture, "tree", output], cwd=Path(root).parent,
                   env={}, budget=ResourceRequest(project_id="crash", memory_bytes=64 * 2**20), timeout_seconds=20.0,
                   containment="cooperative_group" if sys.platform == "darwin" else "contained_tree", trusted_recipe_id="native-fixture")
try:
    handle = supervisor.start(spec, owner)
    Path(handle_file).write_text(handle.model_dump_json(), encoding="utf-8")
    time.sleep(22)
finally:
    supervisor.close()
