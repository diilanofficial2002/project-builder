from pathlib import Path
import sys

import pytest


@pytest.fixture
def owner():
    from project_builder.contracts import RunIdentity
    return RunIdentity(project_id="p1", run_id="r1", scope_id="s1", stage="poc", contract_revision=1)


@pytest.fixture
def sample():
    from project_builder.supervision.models import MachineSample
    return MachineSample(total_ram_bytes=8 * 2**30, available_ram_bytes=6 * 2**30,
                         disk_total_bytes=100 * 2**30, disk_free_bytes=50 * 2**30)


@pytest.fixture
def ledger(tmp_path):
    from project_builder.supervision.ledger import ResourceLedger
    return ResourceLedger(tmp_path / "state")


@pytest.fixture
def supervisor(ledger, sample):
    from project_builder.supervision.supervisor import Supervisor
    with Supervisor(ledger, sampler=lambda: sample, interval=0.05,trusted_group_recipes=frozenset({"native-fixture"})) as supervisor:
        yield supervisor


@pytest.fixture
def spec(tmp_path):
    from project_builder.supervision.models import ProcessSpec, ResourceRequest
    fixture = Path(__file__).parents[1] / "fixtures" / "child_process.py"
    return ProcessSpec(executable=Path(sys.executable), argv=[str(fixture), "sleep", str(tmp_path / "result.json")],
                       cwd=tmp_path, env={}, budget=ResourceRequest(project_id="p1", memory_bytes=32 * 2**20),
                       containment="cooperative_group" if sys.platform == "darwin" else "contained_tree",
                       trusted_recipe_id="native-fixture",timeout_seconds=8.0)
