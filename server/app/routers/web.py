"""Router for the web interface (server-rendered HTML pages)."""
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.services.db_service import get_all_generations, get_generation

router = APIRouter()

_template_dir = Path(__file__).resolve().parent.parent / "templates"
templates = Jinja2Templates(directory=str(_template_dir))


@router.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@router.get("/history", response_class=HTMLResponse)
async def history(request: Request):
    generations = get_all_generations()
    return templates.TemplateResponse(
        "history.html", {"request": request, "generations": generations}
    )


@router.get("/history/{generation_id}", response_class=HTMLResponse)
async def history_detail(request: Request, generation_id: int):
    gen = get_generation(generation_id)
    if gen is None:
        raise HTTPException(status_code=404, detail="Raportul nu a fost găsit")
    return templates.TemplateResponse(
        "history_detail.html", {"request": request, "gen": gen}
    )
