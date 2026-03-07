"""Router for the speech-to-text API endpoint."""
import logging

from fastapi import APIRouter, File, HTTPException, UploadFile

from app.config import settings
from app.schemas.speech import TranscriptionResponse
from app.services.speech_service import transcribe_audio

logger = logging.getLogger(__name__)
router = APIRouter()

ALLOWED_EXTENSIONS = {
    ".wav", ".mp3", ".flac", ".ogg", ".opus",
    ".webm", ".m4a", ".mp4", ".wma",
}


@router.post(
    "/speech-to-text",
    response_model=TranscriptionResponse,
    summary="Transcribe Romanian speech to text",
)
async def speech_to_text(
    file: UploadFile = File(
        ..., description="Audio file to transcribe (WAV, MP3, FLAC, OGG, etc.)"
    ),
):
    # Validate file extension
    filename = file.filename or "audio.wav"
    ext = ""
    if "." in filename:
        ext = "." + filename.rsplit(".", 1)[-1].lower()
    if ext and ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file extension: {ext}. "
            f"Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}",
        )

    # Read and validate file size
    file_bytes = await file.read()

    max_bytes = settings.max_audio_file_size_mb * 1024 * 1024
    if len(file_bytes) > max_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"File too large: {len(file_bytes) / 1024 / 1024:.1f} MB "
            f"(max {settings.max_audio_file_size_mb} MB)",
        )

    if len(file_bytes) == 0:
        raise HTTPException(status_code=400, detail="Empty audio file")

    try:
        result = await transcribe_audio(file_bytes, filename)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Transcription failed")
        raise HTTPException(
            status_code=500, detail=f"Transcription failed: {exc}"
        ) from exc

    return TranscriptionResponse(**result)
