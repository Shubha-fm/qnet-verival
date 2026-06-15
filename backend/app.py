from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from backend.qnet_verival.engine import FAULTS, MUTATIONS, inject_fault, mutate, validate, verify
from backend.qnet_verival.models import FaultRequest, MutationRequest, ProtocolModel
from backend.qnet_verival.sample import metropolitan_qkd_model

ROOT = Path(__file__).resolve().parents[1]
FRONTEND_DIR = ROOT / "frontend"
EXAMPLES_DIR = ROOT / "examples"

app = FastAPI(
    title="QNet-VeriVal",
    description="Verification and validation framework for critical distributed QKD protocols.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")


@app.get("/")
def index() -> FileResponse:
    return FileResponse(FRONTEND_DIR / "index.html")


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok", "framework": "QNet-VeriVal", "version": "1.0.0"}


@app.get("/api/model")
def get_sample_model() -> ProtocolModel:
    return metropolitan_qkd_model()


@app.post("/api/verify")
def verify_model(model: ProtocolModel | None = None) -> Any:
    target = model or metropolitan_qkd_model()
    return verify(target)


@app.post("/api/validate")
def validate_model(model: ProtocolModel | None = None) -> Any:
    target = model or metropolitan_qkd_model()
    return validate(target)


@app.post("/api/fault")
def inject_fault_endpoint(request: FaultRequest) -> Any:
    try:
        return inject_fault(metropolitan_qkd_model(), request.fault_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/mutation")
def mutation_endpoint(request: MutationRequest) -> Any:
    try:
        return mutate(metropolitan_qkd_model(), request.mutation_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/api/catalog")
def catalog() -> dict[str, Any]:
    return {
        "faults": [{"id": k, "description": v[0]} for k, v in FAULTS.items()],
        "mutations": [{"id": k, "description": v[0]} for k, v in MUTATIONS.items()],
    }


@app.get("/api/export/model")
def export_model() -> dict[str, Any]:
    return json.loads(metropolitan_qkd_model().model_dump_json())


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.app:app", host="0.0.0.0", port=8000, reload=False)
