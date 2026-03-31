"""Korzennik - Automated Genealogy Tree Builder."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api import discovery, gedcom, persons, relationships, search, tree
from .database import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(
    title="Korzennik",
    description="Automated genealogy tree builder with Polish source support",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(persons.router)
app.include_router(relationships.router)
app.include_router(search.router)
app.include_router(tree.router)
app.include_router(gedcom.router)
app.include_router(discovery.router)


@app.get("/api/health")
async def health():
    return {"status": "ok", "version": "0.1.0"}
