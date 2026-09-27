"""Lazy access to the trained models (trained on first use if the files are missing)."""
import json
import threading

import joblib
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import DATA_DIR
from ..models import Meta, Project
from .entities import ProjectIndex

_lock = threading.Lock()
_cache: dict = {}


def reset():
    _cache.clear()


def _load(name: str, trainer):
    with _lock:
        if name not in _cache:
            path = DATA_DIR / "models" / f"{name}.joblib"
            if path.exists():
                _cache[name] = joblib.load(path)
            else:
                _cache[name] = trainer()[0]
        return _cache[name]


def label_model():
    from . import label_model as lm
    return _load("label_model", lm.train)


def intent_model():
    from . import intent_model as im
    return _load("intent_model", im.train)


def project_index(db: Session) -> ProjectIndex:
    """Built from the database so projects imported through Ingest are recognized too."""
    return ProjectIndex([(c, n) for c, n in db.execute(select(Project.code, Project.name))])


def metrics(db: Session) -> dict:
    row = db.get(Meta, "models")
    return json.loads(row.value) if row else {}
