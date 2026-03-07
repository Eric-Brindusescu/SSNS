"""Router for the text curation endpoint (LM Studio)."""
import logging

from fastapi import APIRouter, HTTPException

from app.schemas.curate import CurateRequest, CurateResponse
from app.services.curate_service import curate_text

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post(
    "/curate",
    response_model=CurateResponse,
    summary="Curate text into a structured aviation report",
)
async def curate_text_endpoint(request: CurateRequest):
    try:
        curated = await curate_text(request.text)
    except ConnectionError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Curation failed")
        raise HTTPException(
            status_code=500, detail=f"Curation failed: {exc}"
        ) from exc

    return CurateResponse(original=request.text, curated=curated)
