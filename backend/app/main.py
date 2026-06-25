"""Entry point da aplicação FastAPI."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .api.v1 import spools, joints, kpis, uploads, mto, valves

app = FastAPI(title="Piping CMS", version="0.1.0")

import os

_origins = os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(spools.router,  prefix="/api/v1")
app.include_router(joints.router,  prefix="/api/v1")
app.include_router(kpis.router,    prefix="/api/v1")
app.include_router(uploads.router, prefix="/api/v1")
app.include_router(mto.router,     prefix="/api/v1")
app.include_router(valves.router,  prefix="/api/v1")


@app.get("/health")
def health():
    return {"status": "ok"}
