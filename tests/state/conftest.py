"""Synthetic local persistence fixtures, never human or native evidence."""

import importlib
from datetime import datetime, timezone

import pytest

from project_builder.contracts import StageContract


@pytest.fixture
def state_api():
    try:
        return importlib.import_module("project_builder.state.store")
    except ModuleNotFoundError as error:
        if error.name in {"project_builder.state", "project_builder.state.store"}:
            pytest.fail("Task 2 StateStore interface is not implemented")
        raise


@pytest.fixture
def database_path(tmp_path):
    return tmp_path / "owned-runtime" / "state.sqlite3"


@pytest.fixture
def store(state_api, database_path):
    with state_api.StateStore(database_path) as instance:
        yield instance


@pytest.fixture
def contract(raw_contract):
    return StageContract(**(raw_contract | {"revision": 3}))


@pytest.fixture
def ready_run(store, contract):
    # The historical fixture name does not imply a workflow transition.
    return store.create_run(contract)


@pytest.fixture
def evidence_data():
    return {
        "id": "synthetic-evidence", "kind": "synthetic-test",
        "producer_id": "test-only", "build_digest": "test-build",
        "contract_digest": "test-contract", "content_digest": "test-content",
        "observed_at": datetime(2026, 11, 7, tzinfo=timezone.utc),
        "provenance": "automated-test",
    }
