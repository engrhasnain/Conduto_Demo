import os
import sys
import tempfile
from pathlib import Path

import pytest

# Isolated data dir and offline mode, set before the app modules are imported.
os.environ["DATA_DIR"] = tempfile.mkdtemp(prefix="conduto-test-")
os.environ["AI_DISABLED"] = "1"
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


@pytest.fixture(scope="session")
def client():
    from fastapi.testclient import TestClient

    from app.main import app

    with TestClient(app) as c:
        yield c
