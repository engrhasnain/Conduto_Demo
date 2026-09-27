import logging

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..config import ai_enabled
from ..db import get_db
from ..services.ask import local
from ..services.ask.agent import ask
from ..services.llm import LLMError

router = APIRouter(prefix="/api/ask")
log = logging.getLogger("conduto.ask")

FAILED_MSG = {
    "es": "No pude contactar al modelo de IA externo; respondió el motor local.",
    "en": "I couldn't reach the external AI model; the local engine answered.",
    "pt": "Não consegui contatar o modelo de IA externo; o motor local respondeu.",
}


class Turn(BaseModel):
    role: str
    content: str


class AskIn(BaseModel):
    question: str = Field(min_length=1, max_length=2000)
    lang: str = Field(default="es", pattern="^(es|en|pt)$")
    history: list[Turn] = []
    engine: str = Field(default="auto", pattern="^(auto|local)$")
    context: dict | None = None  # previous answer's question type and entities, for follow-ups


@router.get("/suggestions")
def get_suggestions(lang: str = "es"):
    return dict(ai_enabled=ai_enabled(), suggestions=local.suggestions(lang))


@router.post("")
def post_ask(body: AskIn, db: Session = Depends(get_db)):
    if ai_enabled() and body.engine == "auto":
        try:
            return ask(db, body.question, body.lang, [t.model_dump() for t in body.history])
        except LLMError as e:
            log.warning("Ask via Claude failed, using the local engine: %s", e)
            res = local.answer(db, body.question, body.lang, body.context)
            res["warning"] = FAILED_MSG[body.lang]
            return res
    return local.answer(db, body.question, body.lang, body.context)
