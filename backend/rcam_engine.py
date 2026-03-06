"""
ICAO RCAM (Runway Condition Assessment Matrix) Classification Engine
Based on ICAO Doc 9981 PANS-Aerodromes standard
"""
from dataclasses import dataclass
from enum import Enum


class PrecipType(str, Enum):
    NONE = "none"
    RAIN = "rain"
    DRIZZLE = "drizzle"
    SNOW = "snow"
    FREEZING_RAIN = "freezing_rain"
    SLEET = "sleet"


@dataclass
class SensorReading:
    zone: str                    # "touchdown" | "midpoint" | "rollout"
    temp_c: float                # Air temperature in Celsius
    precip_type: PrecipType      # Type of precipitation
    water_depth_mm: float        # Water / slush / snow depth in mm
    friction_coefficient: float  # Measured friction (0.0 – 1.0)
    surface_condition: str       # Human-readable description


@dataclass
class RCCResult:
    zone: str
    rcc: int                     # 0 – 6
    condition_description: str
    braking_action: str
    color: str                   # Hex colour for UI
    risk_level: str              # LOW | MEDIUM | HIGH | CRITICAL


# ── ICAO RCAM lookup tables ──────────────────────────────────────────────────

_BRAKING = {
    6: "GOOD",
    5: "GOOD",
    4: "MEDIUM TO GOOD",
    3: "MEDIUM",
    2: "MEDIUM TO POOR",
    1: "POOR",
    0: "NIL",
}

_COLOR = {
    6: "#00C851",
    5: "#7CFC00",
    4: "#FFD700",
    3: "#FFA500",
    2: "#FF4444",
    1: "#CC0000",
    0: "#8B0000",
}

_RISK = {
    6: "LOW",
    5: "LOW",
    4: "MEDIUM",
    3: "MEDIUM",
    2: "HIGH",
    1: "HIGH",
    0: "CRITICAL",
}


# ── Core classification logic ────────────────────────────────────────────────

def _classify(
    temp_c: float,
    precip_type: PrecipType,
    water_depth_mm: float,
    friction: float,
) -> tuple[int, str]:
    """Return (rcc, description) based on ICAO RCAM rules."""

    pt = precip_type.value if hasattr(precip_type, "value") else str(precip_type)

    # ── Rain / drizzle ───────────────────────────────────────────────────────
    if pt in ("rain", "drizzle"):
        if temp_c > 2:
            if water_depth_mm <= 3:
                return 5, "Wet"
            elif water_depth_mm <= 6:
                return 3, "Standing water forming"
            else:
                return 2, "Standing water"
        else:
            # Freezing rain zone
            if friction >= 0.30:
                return 2, "Wet ice / Freezing rain"
            elif friction >= 0.15:
                return 1, "Ice (freezing rain)"
            else:
                return 0, "Wet ice"

    # ── Freezing rain ────────────────────────────────────────────────────────
    if pt == "freezing_rain":
        if friction >= 0.30:
            return 2, "Wet ice"
        elif friction >= 0.15:
            return 1, "Ice"
        else:
            return 0, "Wet ice"

    # ── Sleet ────────────────────────────────────────────────────────────────
    if pt == "sleet":
        if friction >= 0.36:
            return 3, "Slush / Sleet"
        elif friction >= 0.20:
            return 2, "Wet snow / Sleet"
        else:
            return 1, "Ice / Sleet"

    # ── Snow ─────────────────────────────────────────────────────────────────
    if pt == "snow":
        if temp_c > 0:
            # Melting / wet snow → slush risk
            if friction >= 0.36:
                return 3, "Wet snow"
            else:
                return 2, "Slush"
        else:
            # Dry / compacted snow
            if water_depth_mm < 10:
                if friction >= 0.45:
                    return 4, "Dry snow"
                elif friction >= 0.30:
                    return 3, "Compacted snow"
                elif friction >= 0.15:
                    return 2, "Compacted snow (hard)"
                else:
                    return 1, "Ice beneath snow"
            else:
                if friction >= 0.30:
                    return 3, "Deep compacted snow"
                elif friction >= 0.15:
                    return 2, "Deep snow / ice"
                else:
                    return 1, "Ice"

    # ── No active precipitation ──────────────────────────────────────────────
    # Residual ice / frozen water
    if temp_c <= 0 and water_depth_mm > 0.1:
        if friction < 0.10:
            return 0, "Wet ice (nil braking)"
        elif friction < 0.20:
            return 1, "Ice"
        elif friction < 0.30:
            return 2, "Wet ice"
        elif friction < 0.40:
            return 3, "Compacted snow"
        else:
            return 4, "Frost"

    # Near-freezing frost risk
    if -2 <= temp_c <= 2 and water_depth_mm < 0.1:
        if friction < 0.40:
            return 4, "Frost"
        else:
            return 5, "Wet (frost risk)"

    # Dry
    return 6, "Dry"


# ── Public API ───────────────────────────────────────────────────────────────

def calculate_rcc(reading: SensorReading) -> RCCResult:
    rcc, description = _classify(
        reading.temp_c,
        reading.precip_type,
        reading.water_depth_mm,
        reading.friction_coefficient,
    )
    return RCCResult(
        zone=reading.zone,
        rcc=rcc,
        condition_description=description,
        braking_action=_BRAKING[rcc],
        color=_COLOR[rcc],
        risk_level=_RISK[rcc],
    )
