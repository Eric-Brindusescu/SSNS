"""
Simulated IoT sensor readings for hackathon demo.
Each scenario drifts realistically so the dashboard feels live.
"""
import random
from rcam_engine import PrecipType, SensorReading


# ── Scenario definitions ─────────────────────────────────────────────────────

SCENARIOS: dict[str, dict] = {
    "clear_summer": {
        "description": "Clear summer day",
        "temp_range": (18, 30),
        "precip_type": PrecipType.NONE,
        "water_depth_range": (0.0, 0.2),
        "friction_range": (0.72, 0.85),
    },
    "light_rain": {
        "description": "Light rain",
        "temp_range": (6, 15),
        "precip_type": PrecipType.RAIN,
        "water_depth_range": (0.5, 3.0),
        "friction_range": (0.52, 0.65),
    },
    "heavy_rain": {
        "description": "Heavy rain / standing water",
        "temp_range": (5, 14),
        "precip_type": PrecipType.RAIN,
        "water_depth_range": (4.0, 8.0),
        "friction_range": (0.28, 0.45),
    },
    "snow": {
        "description": "Snowfall",
        "temp_range": (-5, -0.5),
        "precip_type": PrecipType.SNOW,
        "water_depth_range": (5.0, 18.0),
        "friction_range": (0.28, 0.46),
    },
    "freezing_rain": {
        "description": "Freezing rain",
        "temp_range": (-3, 1),
        "precip_type": PrecipType.FREEZING_RAIN,
        "water_depth_range": (0.5, 3.0),
        "friction_range": (0.10, 0.28),
    },
    "icy": {
        "description": "Black ice",
        "temp_range": (-10, -2),
        "precip_type": PrecipType.NONE,
        "water_depth_range": (0.5, 1.5),
        "friction_range": (0.04, 0.18),
    },
}

# Per-zone offsets so each zone reads slightly differently
_ZONE_OFFSETS = {
    "touchdown": {"temp": +0.0, "friction": -0.025, "water": +0.40},
    "midpoint":  {"temp": +0.0, "friction": +0.000, "water": +0.00},
    "rollout":   {"temp": +0.5, "friction": +0.015, "water": -0.15},
}

ZONES = ["touchdown", "midpoint", "rollout"]


# ── Simulator class ──────────────────────────────────────────────────────────

class SensorSimulator:
    def __init__(self) -> None:
        self.scenario: str = "clear_summer"
        self._state: dict[str, dict] = {}
        self._reset_state()

    # ── Public ───────────────────────────────────────────────────────────────

    def set_scenario(self, name: str) -> None:
        if name in SCENARIOS:
            self.scenario = name
            self._reset_state()

    def get_readings(self) -> list[SensorReading]:
        cfg = SCENARIOS[self.scenario]
        readings: list[SensorReading] = []

        t_lo, t_hi = cfg["temp_range"]
        f_lo, f_hi = cfg["friction_range"]
        w_lo, w_hi = cfg["water_depth_range"]

        for zone in ZONES:
            s = self._state[zone]
            off = _ZONE_OFFSETS[zone]

            # Apply small random drift each tick
            s["temp"]    = self._drift(s["temp"],    t_lo, t_hi, step=0.004)
            s["friction"]= self._drift(s["friction"], f_lo, f_hi, step=0.004)
            s["water"]   = self._drift(s["water"],   w_lo, w_hi, step=0.008)

            readings.append(SensorReading(
                zone=zone,
                temp_c=round(s["temp"] + off["temp"], 2),
                precip_type=cfg["precip_type"],
                water_depth_mm=round(max(0.0, s["water"] + off["water"]), 2),
                friction_coefficient=round(
                    max(0.01, min(1.0, s["friction"] + off["friction"])), 3
                ),
                surface_condition=cfg["description"],
            ))

        return readings

    # ── Private ──────────────────────────────────────────────────────────────

    def _reset_state(self) -> None:
        cfg = SCENARIOS[self.scenario]
        for zone in ZONES:
            self._state[zone] = {
                "temp":     random.uniform(*cfg["temp_range"]),
                "friction": random.uniform(*cfg["friction_range"]),
                "water":    random.uniform(*cfg["water_depth_range"]),
            }

    @staticmethod
    def _drift(value: float, lo: float, hi: float, step: float = 0.02) -> float:
        delta = random.uniform(-step, step) * (hi - lo)
        return max(lo, min(hi, value + delta))
