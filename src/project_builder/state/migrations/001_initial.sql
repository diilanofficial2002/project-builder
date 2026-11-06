CREATE TABLE runs (
    run_id TEXT PRIMARY KEY NOT NULL,
    revision INTEGER NOT NULL CHECK (revision > 0),
    snapshot_json TEXT NOT NULL CHECK (json_valid(snapshot_json)),
    contract_json TEXT NOT NULL CHECK (json_valid(contract_json))
);

CREATE TABLE operations (
    operation_id TEXT PRIMARY KEY NOT NULL,
    receipt_json TEXT NOT NULL CHECK (json_valid(receipt_json))
);

CREATE TABLE evidence (
    evidence_id TEXT PRIMARY KEY NOT NULL,
    reference_json TEXT NOT NULL CHECK (json_valid(reference_json))
);
