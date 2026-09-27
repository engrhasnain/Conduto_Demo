"""BM25 keyword search over document pages (Spanish, Portuguese and English).

Good enough for a few thousand pages and needs no embedding service; swap for
pgvector/hybrid search when the corpus grows."""
import math
import re
from collections import Counter

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import Document, DocumentChunk, Project
from .ingestion.normalize import norm

STOP = set("""
a al ante bajo con contra de del desde durante e el en entre hacia hasta la las le lo los mas o para por que se sin sobre su sus un una uno y
ao aos as com da das do dos em na nas no nos o os ou pela pelo pelas pelos sem um uma
the of and to in for on by with at from is are was were be this that it an or as
""".split())


def tokens(text: str) -> list[str]:
    return [t for t in norm(text).split() if t not in STOP and len(t) > 1]


class Index:
    def __init__(self):
        self.docs: list[dict] = []
        self.df: Counter = Counter()
        self.avgdl = 1.0
        self.built = False

    def build(self, db: Session):
        rows = db.execute(
            select(DocumentChunk, Document, Project.code)
            .join(Document, Document.id == DocumentChunk.document_id)
            .outerjoin(Project, Project.id == Document.project_id)
        ).all()
        self.docs, self.df = [], Counter()
        for chunk, doc, code in rows:
            toks = tokens(chunk.text)
            tf = Counter(toks)
            self.docs.append(dict(document_id=doc.id, title=doc.title, doc_type=doc.doc_type, project_code=code,
                                  page=chunk.page, text=chunk.text, tf=tf, len=len(toks)))
            self.df.update(tf.keys())
        self.avgdl = sum(d["len"] for d in self.docs) / max(len(self.docs), 1)
        self.built = True

    def search(self, db: Session, query: str, project_code: str | None = None, top_k: int = 6) -> list[dict]:
        if not self.built:
            self.build(db)
        q = tokens(query)
        n = len(self.docs)
        k1, b = 1.5, 0.75
        scored = []
        for d in self.docs:
            if project_code and d["project_code"] != project_code:
                continue
            s = 0.0
            for t in q:
                # prefix match lets "lluvia" hit "lluvias", "soldad" hit "soldadura"
                f = d["tf"].get(t) or sum(c for w, c in d["tf"].items() if len(t) >= 5 and w.startswith(t[:5]))
                if not f:
                    continue
                df = self.df.get(t) or 1
                idf = math.log(1 + (n - df + 0.5) / (df + 0.5))
                s += idf * f * (k1 + 1) / (f + k1 * (1 - b + b * d["len"] / self.avgdl))
            if s > 0:
                scored.append((s, d))
        scored.sort(key=lambda x: -x[0])
        return [dict(document_id=d["document_id"], title=d["title"], doc_type=d["doc_type"], project_code=d["project_code"],
                     page=d["page"], score=round(s, 2), snippet=snippet(d["text"], q)) for s, d in scored[:top_k]]


def snippet(text: str, q: list[str], width: int = 420) -> str:
    sentences = re.split(r"(?<=[.:])\s+|\n", text)
    best, best_score = "", -1
    for s in sentences:
        toks = set(tokens(s))
        score = sum(1 for t in q if t in toks or any(w.startswith(t[:5]) for w in toks if len(t) >= 5))
        if score > best_score:
            best, best_score = s, score
    return best[:width]


INDEX = Index()


def invalidate():
    INDEX.built = False
