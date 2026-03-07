"""
Speech-to-Text & Template Rendering Server
"""
import logging
from contextlib import asynccontextmanager
from pathlib import Path

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.dependencies import preload_model
from app.routers import curate, render, snowtam, speech, web

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
)

BASE_DIR = Path(__file__).resolve().parent


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load the wav2vec2 model once at startup."""
    preload_model()
    yield


app = FastAPI(
    title="Completare Automata Bază Snowtam LROD",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")

app.include_router(speech.router, prefix="/api", tags=["Speech-to-Text"])
app.include_router(render.router, prefix="/api", tags=["HTML Rendering"])
app.include_router(curate.router, prefix="/api", tags=["Text Curation"])
app.include_router(snowtam.router, prefix="/api", tags=["SNOWTAM Extraction"])
app.include_router(web.router, tags=["Web UI"])

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
