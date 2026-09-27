"""Build step for Vercel: generate the demo dataset and trained models into ./data so they ship with the deployment.

Vercel runs this after installing dependencies (see [tool.vercel.scripts] in pyproject.toml). At runtime each
server instance copies ./data to its writable temporary folder (see app/config.py), so a cold start only has to
copy a few megabytes instead of regenerating everything.

Locally: python build.py
"""
import os
import sqlite3
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
os.environ["DATA_DIR"] = str(HERE / "data")  # write next to the code, not to the temporary folder

from app.db import engine  # noqa: E402  (imported after DATA_DIR is set)
from app.seed.run import seed  # noqa: E402


def main() -> None:
    t0 = time.time()
    seed(force=True)
    engine.dispose()
    # fold the write-ahead log into the database file so the shipped copy is complete on its own
    db = HERE / "data" / "conduto.db"
    conn = sqlite3.connect(db)
    try:
        conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        conn.execute("PRAGMA journal_mode=DELETE")
    finally:
        conn.close()
    for leftover in (db.with_name("conduto.db-wal"), db.with_name("conduto.db-shm")):
        leftover.unlink(missing_ok=True)
    size = sum(f.stat().st_size for f in (HERE / "data").rglob("*") if f.is_file())
    print(f"Demo dataset built in {time.time() - t0:.1f}s ({size / 1e6:.1f} MB) at {HERE / 'data'}")


if __name__ == "__main__":
    main()
