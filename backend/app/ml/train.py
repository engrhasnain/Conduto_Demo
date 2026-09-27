"""Trains the local models, stores them next to the data and records their metrics."""
import json
import logging

import joblib
from sqlalchemy.orm import Session

from ..config import DATA_DIR
from ..models import Meta
from . import intent_model, label_model

MODELS_DIR = DATA_DIR / "models"
log = logging.getLogger("conduto.ml")


def train_models(db: Session) -> dict:
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    lm, lm_metrics = label_model.train()
    im, im_metrics = intent_model.train()
    joblib.dump(lm, MODELS_DIR / "label_model.joblib")
    joblib.dump(im, MODELS_DIR / "intent_model.joblib")
    metrics = {"label_mapper": lm_metrics, "intent_classifier": im_metrics}
    row = db.get(Meta, "models")
    if row:
        row.value = json.dumps(metrics)
    else:
        db.add(Meta(key="models", value=json.dumps(metrics)))
    db.commit()
    log.info("Models trained: label mapper %.1f%%, intent classifier %.1f%%",
             lm_metrics["accuracy"] * 100, im_metrics["accuracy"] * 100)
    from . import registry
    registry.reset()
    return metrics
