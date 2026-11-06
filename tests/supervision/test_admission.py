from concurrent.futures import ThreadPoolExecutor
import time


def test_machine_budget_is_shared_between_projects(ledger, sample):
    from project_builder.supervision.ledger import ResourceLedger, admit
    from project_builder.supervision.models import ResourceRequest
    first = admit(ResourceRequest(project_id="p1", memory_bytes=100), sample, ledger)
    assert first.allowed and first.lease_id
    second = admit(ResourceRequest(project_id="p2", memory_bytes=100), sample, ResourceLedger(ledger.root))
    assert not second.allowed


def test_atomic_competition_for_last_slot(ledger, sample):
    from project_builder.supervision.ledger import ResourceLedger, admit
    from project_builder.supervision.models import ResourceRequest
    def reserve(index):
        return admit(ResourceRequest(project_id=f"p{index}", memory_bytes=100), sample, ResourceLedger(ledger.root))
    with ThreadPoolExecutor(max_workers=8) as pool:
        assert sum(item.allowed for item in pool.map(reserve, range(16))) == 1


def test_expired_lease_does_not_free_unknown_workload(ledger, sample):
    from project_builder.supervision.ledger import admit
    from project_builder.supervision.models import ResourceRequest
    request = ResourceRequest(project_id="p1", memory_bytes=100)
    first = admit(request, sample, ledger)
    ledger.heartbeat(first.lease_id, now=time.time() - 100)
    assert not admit(request, sample, ledger).allowed
    assert ledger.active_count() == 1


def test_unknown_heavy_memory_and_pressure_are_denied(ledger, sample):
    from project_builder.supervision.ledger import admit
    from project_builder.supervision.models import ResourceRequest
    assert not admit(ResourceRequest(project_id="p1", memory_bytes=None), sample, ledger).allowed
    low = sample.model_copy(update={"available_ram_bytes": 2**29})
    assert not admit(ResourceRequest(project_id="p1", memory_bytes=100), low, ledger).allowed
    assert ledger.active_count() == 0


def test_ram_and_disk_reservations_count_across_light_jobs(ledger, sample):
    from project_builder.supervision.ledger import admit
    from project_builder.supervision.models import ResourceRequest
    first = ResourceRequest(project_id="p1", heavy=False, specialist=False, memory_bytes=3 * 2**30,
                            disk_bytes=30 * 2**30)
    assert admit(first, sample, ledger).allowed
    assert not admit(first.model_copy(update={"project_id": "p2"}), sample, ledger).allowed
