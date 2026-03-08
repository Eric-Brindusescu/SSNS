"""
Service for fetching aviation weather (METAR/TAF) from multiple sources.
Aggregates data from NOAA, AVWX, and CheckWX APIs.
"""
import asyncio
import logging

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

_TIMEOUT = 15.0


# ─────────────────────────────────────────────
#  NOAA / aviationweather.gov  (no key needed)
# ─────────────────────────────────────────────

async def _fetch_noaa(client: httpx.AsyncClient, icao: str) -> dict:
    base = "https://aviationweather.gov/api/data"
    metar_url = f"{base}/metar?ids={icao}&format=json"
    taf_url = f"{base}/taf?ids={icao}&format=json"
    station_url = f"{base}/stationinfo?ids={icao}&format=json"

    try:
        results = await asyncio.gather(
            client.get(metar_url),
            client.get(taf_url),
            client.get(station_url),
            return_exceptions=True,
        )

        metar_raw = results[0].json() if not isinstance(results[0], Exception) else []
        taf_raw = results[1].json() if not isinstance(results[1], Exception) else []
        station_raw = results[2].json() if not isinstance(results[2], Exception) else []

        metar = metar_raw[0] if metar_raw else None
        taf = taf_raw[0] if taf_raw else None
        station = station_raw[0] if station_raw else None

        return {
            "source": "NOAA / aviationweather.gov",
            "station": _parse_noaa_station(station),
            "metar": _parse_noaa_metar(metar),
            "taf": _parse_noaa_taf(taf),
            "error": None,
        }
    except Exception as exc:
        logger.warning("NOAA fetch failed for %s: %s", icao, exc)
        return {
            "source": "NOAA / aviationweather.gov",
            "station": None,
            "metar": None,
            "taf": None,
            "error": str(exc),
        }


def _parse_noaa_station(s):
    if not s:
        return None
    return {
        "name": s.get("site"),
        "country": s.get("country"),
        "state": s.get("state"),
        "latitude": s.get("lat"),
        "longitude": s.get("lon"),
        "elevation_m": s.get("elev"),
        "icao": s.get("icaoId"),
        "iata": s.get("iataId"),
    }


def _parse_noaa_metar(m):
    if not m:
        return None
    clouds = m.get("clouds") or []
    return {
        "raw": m.get("rawOb"),
        "time": m.get("reportTime"),
        "wind": {
            "direction_deg": m.get("wdir"),
            "speed_kt": m.get("wspd"),
            "gust_kt": m.get("wgst"),
        },
        "visibility_sm": m.get("visib"),
        "temperature_c": m.get("temp"),
        "dewpoint_c": m.get("dewp"),
        "altimeter_hpa": m.get("altim"),
        "wx_string": m.get("wxString"),
        "sky_cover": m.get("cover"),
        "clouds": [
            {"cover": c.get("cover"), "base_ft": c.get("base")}
            for c in clouds
        ],
        "flight_category": m.get("fltcat"),
        "ceiling_ft": m.get("ceil"),
    }


def _parse_noaa_taf(t):
    if not t:
        return None
    return {
        "raw": t.get("rawTAF"),
        "time": t.get("issueTime"),
        "valid_from": t.get("validTimeFrom"),
        "valid_to": t.get("validTimeTo"),
        "forecasts": [
            {
                "from": f.get("timeFrom"),
                "to": f.get("timeTo"),
                "change_indicator": f.get("changeIndicator"),
                "wind_dir_deg": f.get("wdir"),
                "wind_speed_kt": f.get("wspd"),
                "wind_gust_kt": f.get("wgst"),
                "visibility_sm": f.get("visib"),
                "wx_string": f.get("wxString"),
                "sky_cover": f.get("cover"),
            }
            for f in (t.get("fcsts") or [])
        ],
    }


# ─────────────────────────────────────────────
#  AVWX  (avwx.rest  —  free key required)
# ─────────────────────────────────────────────

async def _fetch_avwx(client: httpx.AsyncClient, icao: str, token: str | None) -> dict:
    if not token:
        return {
            "source": "AVWX (avwx.rest)",
            "station": None,
            "metar": None,
            "taf": None,
            "error": "No token. Set APP_AVWX_TOKEN in .env or pass X-AVWX-Token header.",
        }

    headers = {"Authorization": f"BEARER {token}"}
    base = "https://avwx.rest/api"

    try:
        results = await asyncio.gather(
            client.get(f"{base}/metar/{icao}", headers=headers),
            client.get(f"{base}/taf/{icao}", headers=headers),
            return_exceptions=True,
        )

        def safe_json(r):
            if isinstance(r, Exception):
                return {"error": str(r)}
            try:
                return r.json()
            except Exception as e:
                return {"error": str(e)}

        metar_raw = safe_json(results[0])
        taf_raw = safe_json(results[1])

        return {
            "source": "AVWX (avwx.rest)",
            "station": None,
            "metar": _parse_avwx_metar(metar_raw),
            "taf": _parse_avwx_taf(taf_raw),
            "error": None,
        }
    except Exception as exc:
        logger.warning("AVWX fetch failed for %s: %s", icao, exc)
        return {
            "source": "AVWX (avwx.rest)",
            "station": None,
            "metar": None,
            "taf": None,
            "error": str(exc),
        }


def _val(obj):
    if obj is None:
        return None
    if isinstance(obj, dict):
        return obj.get("value")
    return obj


def _parse_avwx_metar(m):
    if not m or m.get("error"):
        return {"error": m.get("error") if m else "No data"}
    clouds = m.get("clouds") or []
    return {
        "raw": m.get("raw"),
        "time": m.get("time", {}).get("dt") if m.get("time") else None,
        "wind": {
            "direction_deg": _val(m.get("wind_direction")),
            "speed_kt": _val(m.get("wind_speed")),
            "gust_kt": _val(m.get("wind_gust")),
            "variable": m.get("wind_variable_direction") is not None,
        },
        "visibility": {
            "value": _val(m.get("visibility")),
            "unit": (m.get("units") or {}).get("visibility"),
        },
        "temperature_c": _val(m.get("temperature")),
        "dewpoint_c": _val(m.get("dewpoint")),
        "altimeter": {
            "value": _val(m.get("altimeter")),
            "unit": (m.get("units") or {}).get("altimeter"),
        },
        "wx_codes": [w.get("value") for w in (m.get("wx_codes") or [])],
        "clouds": [
            {
                "type": c.get("type"),
                "altitude_ft": _val(c.get("altitude")),
                "modifier": c.get("modifier"),
            }
            for c in clouds
        ],
        "flight_rules": m.get("flight_rules"),
        "remarks": m.get("remarks"),
        "translate": m.get("translate"),
        "summary": m.get("summary"),
    }


def _parse_avwx_taf(t):
    if not t or t.get("error"):
        return {"error": t.get("error") if t else "No data"}
    return {
        "raw": t.get("raw"),
        "time": t.get("time", {}).get("dt") if t.get("time") else None,
        "start_time": t.get("start_time", {}).get("dt") if t.get("start_time") else None,
        "end_time": t.get("end_time", {}).get("dt") if t.get("end_time") else None,
        "remarks": t.get("remarks"),
        "forecasts": [
            {
                "start_time": f.get("start_time", {}).get("dt") if f.get("start_time") else None,
                "end_time": f.get("end_time", {}).get("dt") if f.get("end_time") else None,
                "change_indicator": f.get("type"),
                "wind": {
                    "direction_deg": _val(f.get("wind_direction")),
                    "speed_kt": _val(f.get("wind_speed")),
                    "gust_kt": _val(f.get("wind_gust")),
                },
                "visibility": {
                    "value": _val(f.get("visibility")),
                    "unit": (t.get("units") or {}).get("visibility"),
                },
                "wx_codes": [w.get("value") for w in (f.get("wx_codes") or [])],
                "clouds": [
                    {"type": c.get("type"), "altitude_ft": _val(c.get("altitude"))}
                    for c in (f.get("clouds") or [])
                ],
                "flight_rules": f.get("flight_rules"),
            }
            for f in (t.get("forecast") or [])
        ],
    }


# ─────────────────────────────────────────────
#  CheckWX  (checkwxapi.com  —  free key required)
# ─────────────────────────────────────────────

async def _fetch_checkwx(client: httpx.AsyncClient, icao: str, api_key: str | None) -> dict:
    if not api_key:
        return {
            "source": "CheckWX (checkwxapi.com)",
            "station": None,
            "metar": None,
            "taf": None,
            "error": "No key. Set APP_CHECKWX_API_KEY in .env or pass X-CheckWX-Key header.",
        }

    headers = {"X-API-Key": api_key}
    base = "https://api.checkwx.com"

    try:
        results = await asyncio.gather(
            client.get(f"{base}/metar/{icao}/decoded", headers=headers),
            client.get(f"{base}/taf/{icao}/decoded", headers=headers),
            client.get(f"{base}/station/{icao}", headers=headers),
            return_exceptions=True,
        )

        def safe_json(r):
            if isinstance(r, Exception):
                return {"error": str(r)}
            try:
                return r.json()
            except Exception as e:
                return {"error": str(e)}

        metar_raw = safe_json(results[0])
        taf_raw = safe_json(results[1])
        station_raw = safe_json(results[2])

        metar = (metar_raw.get("data") or [None])[0]
        taf = (taf_raw.get("data") or [None])[0]
        station = (station_raw.get("data") or [None])[0]

        return {
            "source": "CheckWX (checkwxapi.com)",
            "station": _parse_checkwx_station(station),
            "metar": _parse_checkwx_metar(metar, metar_raw),
            "taf": _parse_checkwx_taf(taf, taf_raw),
            "error": None,
        }
    except Exception as exc:
        logger.warning("CheckWX fetch failed for %s: %s", icao, exc)
        return {
            "source": "CheckWX (checkwxapi.com)",
            "station": None,
            "metar": None,
            "taf": None,
            "error": str(exc),
        }


def _d(val):
    return val if isinstance(val, dict) else {}


def _safe_list(val):
    return [x for x in (val or []) if isinstance(x, dict)]


def _parse_checkwx_station(s):
    if not s or not isinstance(s, dict):
        return None
    try:
        coords = _d(s.get("location")).get("coordinates", [None, None])
        return {
            "name": s.get("name"),
            "icao": s.get("icao"),
            "iata": s.get("iata"),
            "country": _d(s.get("country")).get("name"),
            "city": s.get("city"),
            "latitude": coords[1] if len(coords) > 1 else None,
            "longitude": coords[0] if len(coords) > 0 else None,
            "elevation_m": _d(s.get("elevation")).get("meters"),
            "status": s.get("status"),
        }
    except Exception as e:
        return {"error": f"Parse error: {e}"}


def _parse_checkwx_metar(m, metar_raw):
    if not m or not isinstance(m, dict):
        return {"error": metar_raw.get("message", "No data")}
    try:
        return {
            "raw": m.get("raw_text"),
            "time": m.get("observed"),
            "wind": {
                "direction_deg": _d(m.get("wind")).get("degrees"),
                "speed_kt": _d(m.get("wind")).get("speed_kts"),
                "gust_kt": _d(m.get("wind")).get("gust_kts"),
                "variable": _d(m.get("wind")).get("variable_direction") == "VRB",
            },
            "visibility": {
                "miles": _d(m.get("visibility")).get("miles_float"),
                "meters": _d(m.get("visibility")).get("meters_float"),
            },
            "temperature_c": _d(m.get("temperature")).get("celsius"),
            "dewpoint_c": _d(m.get("dewpoint")).get("celsius"),
            "altimeter_hpa": _d(m.get("barometer")).get("hpa"),
            "humidity_pct": _d(m.get("humidity")).get("percent"),
            "wx_codes": [c.get("text") for c in _safe_list(m.get("conditions"))],
            "clouds": [
                {
                    "code": c.get("code"),
                    "text": c.get("text"),
                    "base_ft": c.get("base_feet_agl"),
                    "base_m": c.get("base_meters_agl"),
                }
                for c in _safe_list(m.get("clouds"))
            ],
            "flight_category": m.get("flight_category"),
            "ceiling_ft": _d(m.get("ceiling")).get("feet"),
            "elevation_m": _d(m.get("elevation")).get("meters"),
        }
    except Exception as e:
        return {"error": f"Parse error: {e}", "raw": m.get("raw_text")}


def _parse_checkwx_taf(t, taf_raw):
    if not t or not isinstance(t, dict):
        return {"error": taf_raw.get("message", "No TAF data")}
    try:
        return {
            "raw": t.get("raw_text"),
            "time": _d(t.get("timestamp")).get("issued"),
            "valid_from": _d(t.get("timestamp")).get("from"),
            "valid_to": _d(t.get("timestamp")).get("to"),
            "forecasts": [
                {
                    "from": _d(f.get("timestamp")).get("from"),
                    "to": _d(f.get("timestamp")).get("to"),
                    "change_indicator": _d(_d(f.get("change")).get("indicator")).get("code"),
                    "wind": {
                        "direction_deg": _d(f.get("wind")).get("degrees"),
                        "speed_kt": _d(f.get("wind")).get("speed_kts"),
                        "gust_kt": _d(f.get("wind")).get("gust_kts"),
                    },
                    "visibility_miles": _d(f.get("visibility")).get("miles_float"),
                    "wx_codes": [c.get("text") for c in _safe_list(f.get("conditions"))],
                    "clouds": [
                        {"code": c.get("code"), "base_ft": c.get("base_feet_agl")}
                        for c in _safe_list(f.get("clouds"))
                    ],
                }
                for f in _safe_list(t.get("forecast"))
            ],
        }
    except Exception as e:
        return {"error": f"Parse error: {e}", "raw": t.get("raw_text")}


# ─────────────────────────────────────────────
#  Public API
# ─────────────────────────────────────────────

async def fetch_all_weather(
    icao: str,
    *,
    avwx_token: str | None = None,
    checkwx_key: str | None = None,
) -> list[dict]:
    """Fetch METAR + TAF from all three sources concurrently."""
    resolved_avwx = avwx_token or settings.avwx_token
    resolved_checkwx = checkwx_key or settings.checkwx_api_key

    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        results = await asyncio.gather(
            _fetch_noaa(client, icao),
            _fetch_avwx(client, icao, resolved_avwx),
            _fetch_checkwx(client, icao, resolved_checkwx),
        )

    return list(results)


async def fetch_all_metar(
    icao: str,
    *,
    avwx_token: str | None = None,
    checkwx_key: str | None = None,
) -> list[dict]:
    """Fetch METAR only from all sources."""
    results = await fetch_all_weather(
        icao, avwx_token=avwx_token, checkwx_key=checkwx_key,
    )
    for r in results:
        r["taf"] = None
    return results


async def fetch_all_taf(
    icao: str,
    *,
    avwx_token: str | None = None,
    checkwx_key: str | None = None,
) -> list[dict]:
    """Fetch TAF only from all sources."""
    results = await fetch_all_weather(
        icao, avwx_token=avwx_token, checkwx_key=checkwx_key,
    )
    for r in results:
        r["metar"] = None
    return results
