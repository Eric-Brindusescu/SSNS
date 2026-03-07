from pydantic import BaseModel, Field


class SnowtamRequest(BaseModel):
    text: str = Field(
        ...,
        min_length=1,
        max_length=50000,
        description="Curated aviation text to extract SNOWTAM fields from",
    )
    speech_text: str = Field(
        "",
        max_length=50000,
        description="Original speech-to-text output",
    )
    curated_text: str = Field(
        "",
        max_length=50000,
        description="Curated aviation report text",
    )


class SnowtamResponse(BaseModel):
    dtc: dict = Field(..., description="Extracted SNOWTAM data dictionary")
    html: str = Field(..., description="Filled SNOWTAM HTML form")
    generation_id: int = Field(..., description="Database record ID")
