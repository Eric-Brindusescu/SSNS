"""
Validation service for SNOWTAM reports.

Compares newly extracted runway conditions against the most recent historical
report for the same airport and correlates with current weather data to detect
inconsistencies.
"""
import logging

logger = logging.getLogger(__name__)

# Condition groups for semantic matching
SNOW_CONDITIONS = {
    "DRY SNOW", "COMPACTED SNOW", "DRY SNOW ON TOP OF COMPACTED SNOW",
    "DRY SNOW ON TOP OF ICE", "WET SNOW", "WET SNOW ON TOP OF COMPACTED SNOW",
    "WET SNOW ON TOP OF ICE",
}
ICE_CONDITIONS = {
    "ICE", "WET ICE", "FROST",
    "DRY SNOW ON TOP OF ICE", "WET SNOW ON TOP OF ICE",
    "WATER ON TOP OF COMPACTED SNOW",
}
WET_CONDITIONS = {
    "WET", "SLIPPERY WET", "STANDING WATER", "SLUSH",
    "WATER ON TOP OF COMPACTED SNOW",
}
DRY_CONDITIONS = {"DRY"}
WINTER_CONDITIONS = SNOW_CONDITIONS | ICE_CONDITIONS | {"SLUSH"}


def _get_conditions(params: dict) -> list[str]:
    """Extract the three condition descriptions from a parameters dict."""
    return [
        str(params.get(f"condition_description_third_{i}", "DRY")).upper()
        for i in range(1, 4)
    ]


def _get_coverages(params: dict) -> list[str]:
    return [
        str(params.get(f"percent_coverage_third_{i}", "NR"))
        for i in range(1, 4)
    ]


def _get_rwycc(params: dict) -> list[int]:
    return [
        int(params.get(f"runway_condition_code_third_{i}", 5))
        for i in range(1, 4)
    ]


def _get_depths(params: dict) -> list[str]:
    return [
        str(params.get(f"depth_loose_contaminant_third_{i}", "NR"))
        for i in range(1, 4)
    ]


def _extract_weather_info(weather_data: list | None) -> dict:
    """
    Extract the best available temperature, wx_string, and precipitation info
    from the weather sources list.  Prefers NOAA, falls back to others.
    """
    info = {
        "temperature_c": None,
        "wx_string": None,
        "has_snow_wx": False,
        "has_rain_wx": False,
        "has_freezing_wx": False,
    }
    if not weather_data:
        return info

    for source in weather_data:
        metar = source.get("metar")
        if not metar or source.get("error"):
            continue

        if info["temperature_c"] is None:
            temp = metar.get("temperature_c") or metar.get("temperature")
            if temp is not None:
                try:
                    info["temperature_c"] = float(temp)
                except (ValueError, TypeError):
                    pass

        if info["wx_string"] is None:
            wx = metar.get("wx_string") or ""
            if wx:
                info["wx_string"] = wx.upper()
                # SN = snow, RA = rain, FZ = freezing, DZ = drizzle
                if "SN" in wx.upper():
                    info["has_snow_wx"] = True
                if "RA" in wx.upper() or "DZ" in wx.upper():
                    info["has_rain_wx"] = True
                if "FZ" in wx.upper():
                    info["has_freezing_wx"] = True

    return info


def _extract_prev_weather_info(prev: dict) -> dict:
    """Extract weather info from a previous generation record."""
    return _extract_weather_info(prev.get("weather_data"))


def validate_snowtam(
    new_params: dict,
    previous_gen: dict | None,
    current_weather: list | None,
) -> list[dict]:
    """
    Validate a new SNOWTAM report against historical data and weather.

    Returns a list of warning dicts:
        [{"level": "warning"|"info", "code": str, "message": str}, ...]
    """
    warnings = []
    new_conditions = _get_conditions(new_params)
    new_coverages = _get_coverages(new_params)
    new_rwycc = _get_rwycc(new_params)
    new_depths = _get_depths(new_params)

    wx = _extract_weather_info(current_weather)
    temp = wx["temperature_c"]

    new_has_snow = any(c in SNOW_CONDITIONS for c in new_conditions)
    new_has_ice = any(c in ICE_CONDITIONS for c in new_conditions)
    new_has_wet = any(c in WET_CONDITIONS for c in new_conditions)
    new_has_dry = any(c in DRY_CONDITIONS for c in new_conditions)
    new_has_winter = any(c in WINTER_CONDITIONS for c in new_conditions)

    # ── Rule 1: Snow reported but temperature is high ──────────────────
    if new_has_snow and temp is not None and temp > 10:
        warnings.append({
            "level": "warning",
            "code": "SNOW_HIGH_TEMP",
            "message": (
                f"Raportul indică zăpadă pe pistă, dar temperatura actuală "
                f"este {temp}°C (peste 10°C). Verificați dacă zăpada este "
                f"încă prezentă."
            ),
        })

    # ── Rule 2: Snow reported but temperature is above freezing ───────
    if new_has_snow and temp is not None and 0 < temp <= 10:
        warnings.append({
            "level": "info",
            "code": "SNOW_ABOVE_ZERO",
            "message": (
                f"Raportul indică zăpadă pe pistă, iar temperatura actuală "
                f"este {temp}°C (peste 0°C). Zăpada ar putea fi în topire."
            ),
        })

    # ── Rule 3: Ice/frost reported but temperature is high ────────────
    if new_has_ice and temp is not None and temp > 5:
        warnings.append({
            "level": "warning",
            "code": "ICE_HIGH_TEMP",
            "message": (
                f"Raportul indică gheață/polei pe pistă, dar temperatura "
                f"actuală este {temp}°C. Verificați condițiile."
            ),
        })

    # ── Rule 4: Dry runway but weather shows active precipitation ─────
    if new_has_dry and not new_has_wet and not new_has_snow:
        if wx["has_snow_wx"] or wx["has_rain_wx"]:
            precip = "ninsoare" if wx["has_snow_wx"] else "ploaie"
            warnings.append({
                "level": "warning",
                "code": "DRY_WITH_PRECIP",
                "message": (
                    f"Raportul indică pista uscată, dar datele meteo arată "
                    f"precipitații active ({precip}). Verificați condițiile."
                ),
            })

    # ── Rule 5: RWYCC high but winter conditions reported ─────────────
    if new_has_winter and all(r >= 5 for r in new_rwycc):
        warnings.append({
            "level": "info",
            "code": "HIGH_RWYCC_WINTER",
            "message": (
                "Codul RWYCC este 5 sau 6 pe toate treimile, dar sunt raportate "
                "condiții de iarnă. Verificați dacă RWYCC reflectă corect "
                "aderența pistei."
            ),
        })

    # ── Historical comparison rules ───────────────────────────────────
    if previous_gen:
        prev_params = previous_gen.get("extracted_parameters", {})
        prev_conditions = _get_conditions(prev_params)
        prev_wx = _extract_prev_weather_info(previous_gen)
        prev_temp = prev_wx["temperature_c"]

        prev_has_snow = any(c in SNOW_CONDITIONS for c in prev_conditions)
        prev_has_ice = any(c in ICE_CONDITIONS for c in prev_conditions)
        prev_has_wet = any(c in WET_CONDITIONS for c in prev_conditions)
        prev_has_rain_wx = prev_wx["has_rain_wx"]

        # ── Rule 6: Previous had snow, now warm, still reporting snow ─
        if (prev_has_snow and new_has_snow
                and temp is not None and temp > 10):
            warnings.append({
                "level": "warning",
                "code": "HIST_SNOW_PERSISTS_HOT",
                "message": (
                    f"Raportul anterior indica zăpadă, iar raportul curent "
                    f"tot indică zăpadă, deși temperatura este {temp}°C. "
                    f"Este foarte puțin probabil ca zăpada să persiste."
                ),
            })

        # ── Rule 7: Previous had rain/wet + above zero, now below zero,
        #            but no ice reported (polei scenario) ──────────────
        if ((prev_has_wet or prev_has_rain_wx)
                and prev_temp is not None and prev_temp > 0
                and temp is not None and temp < 0
                and not new_has_ice):
            warnings.append({
                "level": "warning",
                "code": "HIST_RAIN_NOW_FREEZING_NO_ICE",
                "message": (
                    f"Raportul anterior indica ploaie/umezeală la "
                    f"{prev_temp}°C, iar acum temperatura a scăzut la "
                    f"{temp}°C (sub 0°C), dar nu este raportat polei/gheață. "
                    f"Există risc de polei — verificați suprafața pistei."
                ),
            })

        # ── Rule 8: Previous had snow/ice, now reporting dry without
        #            any transition or warm weather ────────────────────
        if (prev_has_snow or prev_has_ice) and new_has_dry and not new_has_wet:
            if temp is not None and temp < 3:
                warnings.append({
                    "level": "warning",
                    "code": "HIST_WINTER_TO_DRY_COLD",
                    "message": (
                        f"Raportul anterior indica zăpadă/gheață, iar acum "
                        f"pista este raportată ca uscată, deși temperatura "
                        f"este doar {temp}°C. Verificați dacă pista a fost "
                        f"curățată sau dacă condițiile s-au schimbat."
                    ),
                })

        # ── Rule 9: Coverage/depth increased without weather justification
        prev_coverages = _get_coverages(prev_params)
        for i in range(3):
            p_cov = prev_coverages[i]
            n_cov = new_coverages[i]
            if p_cov != "NR" and n_cov != "NR":
                try:
                    if int(n_cov) > int(p_cov) + 25:
                        if not wx["has_snow_wx"] and not wx["has_rain_wx"]:
                            warnings.append({
                                "level": "info",
                                "code": f"HIST_COVERAGE_JUMP_T{i+1}",
                                "message": (
                                    f"Acoperirea pe treimea {i+1} a crescut "
                                    f"de la {p_cov}% la {n_cov}% fără "
                                    f"precipitații active în datele meteo."
                                ),
                            })
                except ValueError:
                    pass

        # ── Rule 10: RWYCC dropped significantly ─────────────────────
        prev_rwycc = _get_rwycc(prev_params)
        for i in range(3):
            if new_rwycc[i] < prev_rwycc[i] - 2:
                warnings.append({
                    "level": "info",
                    "code": f"HIST_RWYCC_DROP_T{i+1}",
                    "message": (
                        f"RWYCC pe treimea {i+1} a scăzut de la "
                        f"{prev_rwycc[i]} la {new_rwycc[i]}. "
                        f"Verificați dacă degradarea este justificată."
                    ),
                })

    return warnings
