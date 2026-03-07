"""Router for the text + dictionary -> HTML rendering endpoint."""
from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse

from app.schemas.render import RenderRequest, RenderResponse
from app.services.render_service import render_html

router = APIRouter()


@router.post(
    "/render-html",
    response_model=RenderResponse,
    summary="Render text + dictionary into HTML",
)
async def render_html_endpoint(request: RenderRequest):
    try:
        html = render_html(request.text, request.variables)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return RenderResponse(html=html)


@router.post(
    "/render-html/preview",
    response_class=HTMLResponse,
    summary="Preview rendered HTML directly in the browser",
)
async def render_html_preview(request: RenderRequest):
    try:
        html = render_html(request.text, request.variables)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return HTMLResponse(content=html)
