def test_sqlite_sidecar_disappearing_during_owner_check_does_not_break_ledger(ledger,monkeypatch):
    import project_builder.supervision.ledger as module
    verify=module.verify_owner
    journal=ledger.path.with_name(ledger.path.name+"-journal")
    journal.write_bytes(b"")
    def owner_check(path):
        if path==journal and path.exists():
            path.unlink()  # SQLite may remove this between exists() and the native owner query.
        return verify(path)
    monkeypatch.setattr(module,"verify_owner",owner_check)
    assert ledger.active_count()==0
