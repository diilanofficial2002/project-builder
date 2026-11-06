"""Small transactional workspace documents. Reads do not create files or services."""
from contextlib import closing
import copy
import json
from pathlib import Path
import sqlite3
from uuid import uuid4
from .rules import digest

class Documents:
    def __init__(self, path: Path):
        self.path=path

    def read(self):
        if not self.path.exists():
            return None
        with closing(sqlite3.connect(self.path.resolve().as_uri()+"?mode=ro", uri=True, timeout=2)) as connection:
            row=connection.execute("SELECT value FROM documents WHERE id=1").fetchone()
            return json.loads(row[0]) if row else None

    def initialize(self, document):
        with closing(sqlite3.connect(self.path, timeout=2, isolation_level=None)) as connection:
            connection.execute("PRAGMA busy_timeout=2000")
            connection.execute("BEGIN IMMEDIATE")
            try:
                connection.execute("CREATE TABLE IF NOT EXISTS documents(id INTEGER PRIMARY KEY CHECK(id=1),value TEXT NOT NULL)")
                connection.execute("CREATE TABLE IF NOT EXISTS requests(id TEXT PRIMARY KEY,fingerprint TEXT NOT NULL,outcome TEXT NOT NULL)")
                connection.execute("INSERT OR IGNORE INTO documents VALUES(1,?)",(json.dumps(document,allow_nan=False),))
                connection.commit()
            except BaseException:
                connection.rollback()
                raise
        return self.read()

    def mutate(self, intent, payload, transform, *, request_id=None, expected_revision=None):
        request_id=request_id or str(uuid4())
        fingerprint=digest({"intent":intent,"payload":payload,"expected_revision":expected_revision})
        with closing(sqlite3.connect(self.path,timeout=2,isolation_level=None)) as connection:
            connection.execute("PRAGMA busy_timeout=2000")
            connection.execute("BEGIN IMMEDIATE")
            try:
                old=connection.execute("SELECT fingerprint,outcome FROM requests WHERE id=?",(request_id,)).fetchone()
                if old:
                    if old[0] != fingerprint:
                        raise ValueError("request ID reused with different content")
                    connection.rollback()
                    return json.loads(old[1])
                row=connection.execute("SELECT value FROM documents WHERE id=1").fetchone()
                if not row:
                    raise ValueError("workspace is not initialized")
                doc=json.loads(row[0])
                if expected_revision is not None and (type(expected_revision) is not int or expected_revision != doc["revision"]):
                    raise ValueError("stale workspace revision")
                new=copy.deepcopy(doc)
                result=transform(new)
                new["revision"]=doc["revision"]+1
                result=result | {"revision":new["revision"]}
                encoded=json.dumps(new,ensure_ascii=False,allow_nan=False)
                outcome=json.dumps(result,ensure_ascii=False,allow_nan=False)
                connection.execute("UPDATE documents SET value=? WHERE id=1",(encoded,))
                connection.execute("INSERT INTO requests VALUES(?,?,?)",(request_id,fingerprint,outcome))
                connection.commit()
                return result
            except BaseException:
                connection.rollback()
                raise
