from pydantic import BaseModel, Field


class CurateRequest(BaseModel):
    text: str = Field(
        ...,
        min_length=1,
        max_length=50000,
        description="Raw text to curate into a structured aviation report",
    )


class CurateResponse(BaseModel):
    original: str = Field(..., description="Original input text")
    curated: str = Field(..., description="Curated aviation report")
