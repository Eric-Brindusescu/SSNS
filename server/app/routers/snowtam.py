"""Router for the SNOWTAM extraction endpoint (LM Studio + Qwen3)."""
import logging

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel, Field

from app.schemas.snowtam import SnowtamRequest, SnowtamResponse
from app.services.snowtam_service import extract_snowtam

logger = logging.getLogger(__name__)
router = APIRouter()


class HtmlToPdfRequest(BaseModel):
    html: str = Field(..., min_length=1, description="HTML content to convert to PDF")


@router.post(
    "/snowtam",
    response_model=SnowtamResponse,
    summary="Extract SNOWTAM fields from curated text and generate filled form",
)
async def snowtam_endpoint(request: SnowtamRequest):
    try:
        result = await extract_snowtam(request.text)
    except ConnectionError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except (RuntimeError, ValueError) as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("SNOWTAM extraction failed")
        raise HTTPException(
            status_code=500, detail=f"SNOWTAM extraction failed: {exc}"
        ) from exc

    return SnowtamResponse(dtc=result["dtc"], html=result["html"])


@router.post(
    "/snowtam/pdf",
    summary="Convert SNOWTAM HTML to PDF",
    response_class=Response,
)
async def snowtam_pdf_endpoint(request: HtmlToPdfRequest):
    try:
        from weasyprint import HTML
        pdf_bytes = HTML(string=request.html).write_pdf()
    except Exception as exc:
        logger.exception("PDF generation failed")
        raise HTTPException(
            status_code=500, detail=f"Generarea PDF a eșuat: {exc}"
        ) from exc

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=SNOWTAM_LROD.pdf"},
    )
