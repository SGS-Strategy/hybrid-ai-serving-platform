import os
from typing import Any

import httpx
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field


def _predict_url() -> str:
    base_url = os.getenv(
        "PREDICTOR_URL",
        "http://predictor-predictor-default.inference.svc.cluster.local",
    ).rstrip("/")
    endpoint = os.getenv("PREDICTOR_ENDPOINT", "/v1/models/default:predict")
    return f"{base_url}{endpoint}"


class InferenceRequest(BaseModel):
    inputs: list[Any] = Field(default_factory=list)
    parameters: dict[str, Any] = Field(default_factory=dict)


app = FastAPI(title="inference-api", version="0.1.0")


@app.get("/healthz")
async def healthz() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/infer")
async def infer(request: InferenceRequest) -> dict[str, Any]:
    payload = request.model_dump()
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(_predict_url(), json=payload)
            response.raise_for_status()
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"predictor request failed: {exc}") from exc

    data = response.json()
    return {
        "status": "accepted",
        "predictor_url": _predict_url(),
        "result": data,
    }
