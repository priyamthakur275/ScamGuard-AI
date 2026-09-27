from fastapi import APIRouter, Request

router = APIRouter(tags=["system"])


@router.get("/health")
def health() -> dict:
    """Liveness probe: process is up and serving HTTP."""
    return {"status": "ok"}


@router.get("/ready")
def ready(request: Request) -> dict:
    """Readiness probe: distinct from liveness because a healthy process
    with no model loaded must NOT receive traffic. Kubernetes uses this
    endpoint to gate the pod out of the load-balancer pool until a model
    is actually ready to serve.
    """
    engine = getattr(request.app.state, "inference_engine", None)
    is_ready = engine is not None and engine.is_ready
    return {
        "status": "ready" if is_ready else "not_ready",
        "model_loaded": is_ready,
    }
