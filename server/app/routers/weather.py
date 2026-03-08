"""Router for the aviation weather aggregation endpoints (METAR/TAF)."""
import logging
import re

from fastapi import APIRouter, HTTPException, Header

from app.services.weather_service import (
    fetch_all_metar,
    fetch_all_taf,
    fetch_all_weather,
)

logger = logging.getLogger(__name__)
router = APIRouter()

_ICAO_PATTERN = re.compile(r"^[A-Z]{4}$")


def _validate_icao(icao: str) -> str:
    icao = icao.upper().strip()
    if not _ICAO_PATTERN.match(icao):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid ICAO code: '{icao}'. Must be exactly 4 uppercase letters.",
        )
    return icao


@router.get(
    "/weather/{icao}",
    summary="Fetch METAR and TAF from all sources",
)
async def weather_endpoint(
    icao: str,
    x_avwx_token: str | None = Header(None, alias="X-AVWX-Token"),
    x_checkwx_key: str | None = Header(None, alias="X-CheckWX-Key"),
):
    icao = _validate_icao(icao)
    try:
        results = await fetch_all_weather(
            icao, avwx_token=x_avwx_token, checkwx_key=x_checkwx_key,
        )
    except Exception as exc:
        logger.exception("Weather fetch failed for %s", icao)
        raise HTTPException(
            status_code=500, detail=f"Weather fetch failed: {exc}"
        ) from exc

    return {"icao": icao, "sources": results}


@router.get(
    "/metar/{icao}",
    summary="Fetch METAR only from all sources",
)
async def metar_endpoint(
    icao: str,
    x_avwx_token: str | None = Header(None, alias="X-AVWX-Token"),
    x_checkwx_key: str | None = Header(None, alias="X-CheckWX-Key"),
):
    icao = _validate_icao(icao)
    try:
        results = await fetch_all_metar(
            icao, avwx_token=x_avwx_token, checkwx_key=x_checkwx_key,
        )
    except Exception as exc:
        logger.exception("METAR fetch failed for %s", icao)
        raise HTTPException(
            status_code=500, detail=f"METAR fetch failed: {exc}"
        ) from exc

    return {"icao": icao, "sources": results}


@router.get(
    "/taf/{icao}",
    summary="Fetch TAF only from all sources",
)
async def taf_endpoint(
    icao: str,
    x_avwx_token: str | None = Header(None, alias="X-AVWX-Token"),
    x_checkwx_key: str | None = Header(None, alias="X-CheckWX-Key"),
):
    icao = _validate_icao(icao)
    try:
        results = await fetch_all_taf(
            icao, avwx_token=x_avwx_token, checkwx_key=x_checkwx_key,
        )
    except Exception as exc:
        logger.exception("TAF fetch failed for %s", icao)
        raise HTTPException(
            status_code=500, detail=f"TAF fetch failed: {exc}"
        ) from exc

    return {"icao": icao, "sources": results}
