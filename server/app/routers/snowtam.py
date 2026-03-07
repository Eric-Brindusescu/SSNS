"""Router for the SNOWTAM extraction endpoint (LM Studio + Qwen3)."""
import logging
import smtplib
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel, Field

from app.config import settings
from app.schemas.snowtam import SnowtamRequest, SnowtamResponse
from app.services.db_service import save_generation
from app.services.snowtam_service import DEFAULTS, extract_snowtam

logger = logging.getLogger(__name__)
router = APIRouter()


class HtmlToPdfRequest(BaseModel):
    html: str = Field(..., min_length=1, description="HTML content to convert to PDF")


class SendEmailRequest(BaseModel):
    to: str = Field(..., min_length=1, description="Recipient email address")
    html: str = Field(..., min_length=1, description="SNOWTAM HTML to attach as PDF")


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

    generation_id = save_generation(
        speech_text=request.speech_text,
        curated_text=request.curated_text,
        default_parameters=DEFAULTS,
        extracted_parameters=result["dtc"],
        generated_html=result["html"],
    )

    return SnowtamResponse(
        dtc=result["dtc"],
        html=result["html"],
        generation_id=generation_id,
    )


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


@router.post(
    "/snowtam/send-email",
    summary="Send SNOWTAM PDF via email",
)
async def snowtam_send_email(request: SendEmailRequest):
    if not settings.smtp_user or not settings.smtp_password:
        raise HTTPException(
            status_code=503,
            detail="Serverul SMTP nu este configurat. "
                   "Setați APP_SMTP_USER și APP_SMTP_PASSWORD în .env",
        )

    try:
        from weasyprint import HTML
        pdf_bytes = HTML(string=request.html).write_pdf()
    except Exception as exc:
        logger.exception("PDF generation for email failed")
        raise HTTPException(
            status_code=500, detail=f"Generarea PDF a eșuat: {exc}"
        ) from exc

    msg = MIMEMultipart()
    msg["From"] = settings.smtp_from or settings.smtp_user
    msg["To"] = request.to
    msg["Subject"] = "Raport SNOWTAM LROD"

    body = (
        "Bună ziua,\n\n"
        "Vă transmit atașat formularul SNOWTAM generat automat.\n\n"
        "Cu stimă,\n"
        "Sistemul de Completare Automată SNOWTAM LROD"
    )
    msg.attach(MIMEText(body, "plain", "utf-8"))

    attachment = MIMEApplication(pdf_bytes, _subtype="pdf")
    attachment.add_header(
        "Content-Disposition", "attachment", filename="SNOWTAM_LROD.pdf"
    )
    msg.attach(attachment)

    try:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as smtp:
            smtp.starttls()
            smtp.login(settings.smtp_user, settings.smtp_password)
            smtp.send_message(msg)
    except Exception as exc:
        logger.exception("Email sending failed")
        raise HTTPException(
            status_code=500, detail=f"Trimiterea email-ului a eșuat: {exc}"
        ) from exc

    return {"status": "sent", "to": request.to}
