import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware

from .api import ask, connectors, data, ingest
from .config import CORS_ORIGINS
from .seed.run import seed
from .services.search import invalidate

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    if seed(force=False):
        logging.getLogger("conduto").info("Demo dataset generated")
    yield


app = FastAPI(title="Conduto Project Intelligence API", version="0.1.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=CORS_ORIGINS, allow_methods=["*"], allow_headers=["*"])
app.add_middleware(GZipMiddleware, minimum_size=1000)
app.include_router(data.router)
app.include_router(ask.router)
app.include_router(ingest.router)
app.include_router(connectors.router)


@app.get("/")
def root():
    return {"name": "Conduto Project Intelligence API", "docs": "/docs", "health": "/api/health"}


@app.post("/api/admin/reset")
def reset(x_admin_token: str | None = Header(default=None)):
    """Regenerates the demo dataset (drops uploaded files and imported data)."""
    token = os.getenv("ADMIN_TOKEN")
    if token and x_admin_token != token:
        raise HTTPException(403, "Invalid admin token")
    seed(force=True)
    invalidate()
    return {"status": "reset"}
