from pydantic import BaseModel, Field


class TranscriptionResponse(BaseModel):
    text: str = Field(..., description="Transcribed text from the audio file")
    duration_seconds: float = Field(
        ..., description="Duration of the audio in seconds"
    )
    language: str = Field(default="ro", description="Language of transcription")
