from pydantic import BaseModel, Field


class RenderRequest(BaseModel):
    text: str = Field(
        ...,
        min_length=1,
        max_length=50000,
        description="Main text content (may contain Jinja2 template syntax)",
    )
    variables: dict[str, str] = Field(
        default_factory=dict,
        description="Key-value pairs used as Jinja2 template variables",
    )


class RenderResponse(BaseModel):
    html: str = Field(..., description="Rendered HTML content")
