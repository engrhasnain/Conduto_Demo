"""Executes model-written SQL on a read-only connection with a time and row budget."""
import re
import sqlite3
import time

from ...config import DB_PATH

FORBIDDEN = re.compile(r"\b(insert|update|delete|drop|alter|create|attach|detach|pragma|replace|vacuum|reindex|load_extension)\b", re.I)


class SqlError(ValueError):
    pass


def run_readonly(query: str, max_rows: int = 200, timeout_s: float = 5.0) -> dict:
    q = (query or "").strip().rstrip(";").strip()
    if not q:
        raise SqlError("Empty query.")
    if ";" in q:
        raise SqlError("Only a single statement is allowed.")
    if not re.match(r"(?is)^(select|with)\b", q):
        raise SqlError("Only SELECT queries are allowed.")
    if FORBIDDEN.search(q):
        raise SqlError("Query contains a forbidden keyword.")
    conn = sqlite3.connect(f"file:{DB_PATH.as_posix()}?mode=ro", uri=True, timeout=timeout_s)
    t0 = time.monotonic()
    conn.set_progress_handler(lambda: 1 if time.monotonic() - t0 > timeout_s else 0, 10_000)
    try:
        cur = conn.execute(q)
        cols = [d[0] for d in cur.description or []]
        rows = cur.fetchmany(max_rows + 1)
    except sqlite3.Error as e:
        raise SqlError(str(e)) from e
    finally:
        conn.close()
    return {"columns": cols, "rows": [list(r) for r in rows[:max_rows]], "truncated": len(rows) > max_rows}
