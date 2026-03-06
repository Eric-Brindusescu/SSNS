"""
RunwayGuard — FastAPI backend
Serves live runway condition data via REST + WebSocket.
"""
import asyncio
import json
from datetime import datetime, timezone
from typing import Any

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from rcam_engine import calculate_rcc
from sensor_simulator import SensorSimulator, SCENARIOS

# ── App setup ────────────────────────────────────────────────────────────────

app = FastAPI(title="RunwayGuard API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Shared state ─────────────────────────────────────────────────────────────

simulator = SensorSimulator()
alert_history: list[dict] = []
connected_clients: list[WebSocket] = []

ZONE_LABELS = {
    "touchdown": "TOUCHDOWN",
    "midpoint": "MIDPOINT",
    "rollout": "ROLLOUT",
}


# ── Snapshot builder ─────────────────────────────────────────────────────────

def build_snapshot() -> dict[str, Any]:
    readings = simulator.get_readings()
    results  = [calculate_rcc(r) for r in readings]

    overall_rcc = min(r.rcc for r in results)

    # Generate alerts for degraded zones
    new_alerts: list[dict] = []
    for r in results:
        if r.rcc <= 1:
            new_alerts.append({
                "level":     "CRITICAL",
                "zone":      r.zone,
                "message":   f"{ZONE_LABELS[r.zone]}: {r.condition_description} — RCC {r.rcc} ({r.braking_action})",
                "timestamp": _utcnow(),
            })
        elif r.rcc <= 3:
            new_alerts.append({
                "level":     "WARNING",
                "zone":      r.zone,
                "message":   f"{ZONE_LABELS[r.zone]}: {r.condition_description} — RCC {r.rcc} ({r.braking_action})",
                "timestamp": _utcnow(),
            })

    if new_alerts:
        alert_history.extend(new_alerts)
        # Keep last 50 alerts
        while len(alert_history) > 50:
            alert_history.pop(0)

    zones_out = []
    for i, (reading, result) in enumerate(zip(readings, results)):
        zones_out.append({
            "zone":            result.zone,
            "label":           ZONE_LABELS[result.zone],
            "rcc":             result.rcc,
            "condition":       result.condition_description,
            "braking_action":  result.braking_action,
            "color":           result.color,
            "risk_level":      result.risk_level,
            "temp_c":          reading.temp_c,
            "water_depth_mm":  reading.water_depth_mm,
            "friction":        reading.friction_coefficient,
            "precip_type":     reading.precip_type.value,
        })

    return {
        "timestamp":       _utcnow(),
        "scenario":        simulator.scenario,
        "overall_rcc":     overall_rcc,
        "overall_braking": _BRAKING_LABEL[overall_rcc],
        "overall_color":   _COLOR[overall_rcc],
        "zones":           zones_out,
        "active_alerts":   new_alerts,
        "alert_history":   alert_history[-15:],
    }


# ── REST endpoints ────────────────────────────────────────────────────────────

@app.get("/api/status")
async def get_status():
    return build_snapshot()


@app.get("/api/scenarios")
async def list_scenarios():
    return [
        {"id": k, "description": v["description"]}
        for k, v in SCENARIOS.items()
    ]


@app.post("/api/scenario/{scenario_name}")
async def set_scenario(scenario_name: str):
    if scenario_name not in SCENARIOS:
        return {"success": False, "error": "Unknown scenario"}
    simulator.set_scenario(scenario_name)
    snapshot = build_snapshot()
    await _broadcast(snapshot)
    return {"success": True, "scenario": scenario_name}


# ── WebSocket ─────────────────────────────────────────────────────────────────

@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()
    connected_clients.append(ws)
    try:
        # Push initial state immediately
        await ws.send_json(build_snapshot())
        while True:
            await asyncio.sleep(3)
            await ws.send_json(build_snapshot())
    except (WebSocketDisconnect, Exception):
        pass
    finally:
        if ws in connected_clients:
            connected_clients.remove(ws)


# ── Helpers ───────────────────────────────────────────────────────────────────

async def _broadcast(data: dict) -> None:
    dead: list[WebSocket] = []
    for ws in connected_clients:
        try:
            await ws.send_json(data)
        except Exception:
            dead.append(ws)
    for ws in dead:
        connected_clients.remove(ws)


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


_BRAKING_LABEL = {
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


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
