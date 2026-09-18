import json
import sqlite3
import time
from contextlib import contextmanager
from pathlib import Path


class Store:
    def __init__(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.path = path
        with self.connect() as db:
            db.executescript("""
                PRAGMA journal_mode=WAL;
                CREATE TABLE IF NOT EXISTS cache (key TEXT PRIMARY KEY, payload TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS results (id TEXT PRIMARY KEY, payload TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS batches (id TEXT PRIMARY KEY, created REAL NOT NULL);
                CREATE TABLE IF NOT EXISTS jobs (
                  id TEXT PRIMARY KEY, batch_id TEXT NOT NULL, file_id TEXT NOT NULL,
                  sha256 TEXT NOT NULL, kind TEXT NOT NULL, options TEXT NOT NULL,
                  status TEXT NOT NULL, result_id TEXT, error TEXT, created REAL NOT NULL);
                CREATE INDEX IF NOT EXISTS jobs_status ON jobs(status, created);
            """)

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.path, timeout=30)
        db.row_factory = sqlite3.Row
        try:
            yield db
            db.commit()
        except BaseException:
            db.rollback()
            raise
        finally:
            db.close()

    def cached(self, key):
        with self.connect() as db:
            row = db.execute("SELECT payload FROM cache WHERE key=?", (key,)).fetchone()
        return json.loads(row[0]) if row else None

    def save(self, result, key=None):
        payload = result.model_dump_json()
        with self.connect() as db:
            db.execute("INSERT OR REPLACE INTO results VALUES (?,?)", (result.id, payload))
            if key:
                db.execute("INSERT OR REPLACE INTO cache VALUES (?,?)", (key, payload))

    def result(self, ident):
        with self.connect() as db:
            row = db.execute("SELECT payload FROM results WHERE id=?", (ident,)).fetchone()
        return json.loads(row[0]) if row else None

    def submit_batch(self, ident, jobs, options, limit):
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            queued = db.execute("SELECT count(*) FROM jobs WHERE status IN ('QUEUED','RUNNING')").fetchone()[
                0
            ]
            if queued + len(jobs) > limit:
                raise ValueError("Queue capacity exceeded")
            db.execute("INSERT INTO batches VALUES (?,?)", (ident, time.time()))
            db.executemany(
                "INSERT INTO jobs VALUES (?,?,?,?,?,?,'QUEUED',NULL,NULL,?)",
                [
                    (
                        j["id"],
                        ident,
                        j["file_id"],
                        j["sha256"],
                        j["kind"],
                        options.model_dump_json(),
                        time.time(),
                    )
                    for j in jobs
                ],
            )

    def recover(self):
        with self.connect() as db:
            db.execute("UPDATE jobs SET status='QUEUED' WHERE status='RUNNING'")

    def claim(self):
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT * FROM jobs WHERE status='QUEUED' ORDER BY created LIMIT 1").fetchone()
            if row:
                db.execute("UPDATE jobs SET status='RUNNING' WHERE id=?", (row["id"],))
        return dict(row) if row else None

    def finish(self, ident, result_id=None, error=None):
        with self.connect() as db:
            db.execute(
                "UPDATE jobs SET status=?,result_id=?,error=? WHERE id=?",
                ("FAILED" if error else "COMPLETED", result_id, error, ident),
            )

    def batch(self, ident):
        with self.connect() as db:
            exists = db.execute("SELECT 1 FROM batches WHERE id=?", (ident,)).fetchone()
            rows = db.execute(
                "SELECT id,file_id,status,result_id,error FROM jobs WHERE batch_id=? ORDER BY created,id",
                (ident,),
            ).fetchall()
        if not exists:
            return None
        counts = {
            s: sum(r["status"] == s for r in rows) for s in ("QUEUED", "RUNNING", "COMPLETED", "FAILED")
        }
        return {
            "id": ident,
            "finished": counts["QUEUED"] + counts["RUNNING"] == 0,
            "counts": counts,
            "jobs": [dict(row) for row in rows],
        }
