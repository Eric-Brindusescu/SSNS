# RunwayGuard — Backend

FastAPI server that classifies runway surface conditions in real time using the **ICAO RCAM standard** and streams results to connected clients via WebSocket.

---

## File Overview

```
backend/
├── main.py              # API server, WebSocket, snapshot builder
├── rcam_engine.py       # ICAO classification logic → outputs RCC 0–6
├── sensor_simulator.py  # Simulated IoT sensor readings with drift
└── requirements.txt     # Python dependencies
```

---

## How It Works

### Data flow

```
sensor_simulator.py
      │
      │  SensorReading (per zone)
      │  - temp_c
      │  - precip_type
      │  - water_depth_mm
      │  - friction_coefficient
      ▼
rcam_engine.py
      │
      │  RCCResult (per zone)
      │  - rcc (0–6)
      │  - condition_description
      │  - braking_action
      │  - color / risk_level
      ▼
main.py  →  build_snapshot()
      │
      ├─ REST  GET /api/status        → JSON snapshot
      ├─ REST  POST /api/scenario/... → switch scenario + broadcast
      └─ WS    /ws                    → push snapshot every 3 seconds
```

### Each tick (every 3 seconds)

1. `simulator.get_readings()` — returns one `SensorReading` per runway zone, with small random drift applied to each sensor value so the numbers feel live
2. `calculate_rcc(reading)` — passes each reading through the RCAM rule engine and gets an `RCCResult`
3. `build_snapshot()` — packages all zones + alerts into a single JSON dict
4. The WebSocket loop pushes that dict to every connected client

---

## RCAM Engine (`rcam_engine.py`)

This is the core classification logic. It maps sensor inputs to an ICAO Runway Condition Code.

### Inputs

| Field | Type | Description |
|-------|------|-------------|
| `temp_c` | float | Air temperature in Celsius |
| `precip_type` | PrecipType enum | none / rain / drizzle / snow / freezing_rain / sleet |
| `water_depth_mm` | float | Water or snow depth on surface in mm |
| `friction_coefficient` | float | Measured friction (0.0 = no grip, 1.0 = full grip) |

### Output: RCC 0–6

| RCC | Condition | Braking |
|-----|-----------|---------|
| 6 | Dry | Good |
| 5 | Wet ≤ 3mm | Good |
| 4 | Frost / Dry snow | Medium to Good |
| 3 | Wet snow / Compacted snow | Medium |
| 2 | Standing water / Slush | Medium to Poor |
| 1 | Ice | Poor |
| 0 | Wet ice | Nil |

### Decision tree (simplified)

```
precip = rain/drizzle  AND  temp > 2°C
    water ≤ 3mm   →  RCC 5 (Wet)
    water ≤ 6mm   →  RCC 3 (Standing water forming)
    water > 6mm   →  RCC 2 (Standing water)

precip = rain/drizzle  AND  temp ≤ 2°C  (freezing)
    friction ≥ 0.30  →  RCC 2 (Wet ice)
    friction ≥ 0.15  →  RCC 1 (Ice)
    friction < 0.15  →  RCC 0 (Wet ice — nil braking)

precip = freezing_rain
    friction ≥ 0.30  →  RCC 2
    friction ≥ 0.15  →  RCC 1
    friction < 0.15  →  RCC 0

precip = snow  AND  temp > 0°C  (melting/wet snow)
    friction ≥ 0.36  →  RCC 3 (Wet snow)
    friction < 0.36  →  RCC 2 (Slush)

precip = snow  AND  temp ≤ 0°C  (dry/compacted)
    depth < 10mm:
        friction ≥ 0.45  →  RCC 4 (Dry snow)
        friction ≥ 0.30  →  RCC 3 (Compacted snow)
        friction ≥ 0.15  →  RCC 2 (Hard compacted)
        friction < 0.15  →  RCC 1 (Ice beneath snow)

precip = none  AND  temp ≤ 0°C  AND  water > 0.1mm  (residual ice)
    friction < 0.10  →  RCC 0 (Wet ice)
    friction < 0.20  →  RCC 1 (Ice)
    friction < 0.30  →  RCC 2 (Wet ice)
    friction < 0.40  →  RCC 3 (Compacted snow)
    friction ≥ 0.40  →  RCC 4 (Frost)

precip = none  AND  -2°C ≤ temp ≤ 2°C  (frost risk)
    friction < 0.40  →  RCC 4 (Frost)
    friction ≥ 0.40  →  RCC 5 (Wet — frost risk)

everything else → RCC 6 (Dry)
```

---

## Sensor Simulator (`sensor_simulator.py`)

Replaces real IoT hardware for the hackathon demo. Each call to `get_readings()` returns realistic-looking values with small random drift, so the dashboard numbers change every tick without jumping around wildly.

### How drift works

Each sensor value drifts by a tiny random step each tick, clamped to the scenario's defined range:

```python
new_value = old_value + random.uniform(-step, +step) * (max - min)
new_value = clamp(new_value, min, max)
```

### Scenarios

Each scenario defines ranges for temperature, friction, water depth, and precipitation type:

```python
SCENARIOS = {
    "clear_summer":  { temp: (18,30),  friction: (0.72,0.85), water: (0.0,0.2),  precip: NONE          },
    "light_rain":    { temp: (6,15),   friction: (0.52,0.65), water: (0.5,3.0),  precip: RAIN          },
    "heavy_rain":    { temp: (5,14),   friction: (0.28,0.45), water: (4.0,8.0),  precip: RAIN          },
    "snow":          { temp: (-5,-0.5),friction: (0.28,0.46), water: (5.0,18.0), precip: SNOW          },
    "freezing_rain": { temp: (-3,1),   friction: (0.10,0.28), water: (0.5,3.0),  precip: FREEZING_RAIN },
    "icy":           { temp: (-10,-2), friction: (0.04,0.18), water: (0.5,1.5),  precip: NONE          },
}
```

### Zone offsets

Each zone (touchdown, midpoint, rollout) reads slightly differently to simulate real runway variation:

```python
_ZONE_OFFSETS = {
    "touchdown": { friction: -0.025, water: +0.40 },  # worst grip, most water accumulation
    "midpoint":  { friction:  0.000, water:  0.00 },  # baseline
    "rollout":   { friction: +0.015, water: -0.15 },  # slightly better
}
```

---

## How to Modify

### Change how often updates are pushed

In `main.py`, find the WebSocket loop:

```python
await asyncio.sleep(3)   # ← change this value (seconds)
```

### Change alert thresholds

In `main.py`, inside `build_snapshot()`:

```python
if r.rcc <= 1:           # ← CRITICAL threshold
    ...
elif r.rcc <= 3:         # ← WARNING threshold
    ...
```

### Tune friction thresholds in the RCAM engine

Open `rcam_engine.py` and edit the `_classify()` function. Each `if friction >= X` line is a threshold you can tune to match your real sensor data.

### Change how many alerts are kept in history

In `main.py`:

```python
while len(alert_history) > 50:   # ← change 50 to whatever you need
```

---

## How to Extend

### 1. Add a new scenario

In `sensor_simulator.py`, add an entry to `SCENARIOS`:

```python
"slush": {
    "description": "Slush / wet compacted snow",
    "temp_range": (-1, 2),
    "precip_type": PrecipType.SLEET,
    "water_depth_range": (3.0, 8.0),
    "friction_range": (0.18, 0.32),
},
```

Then add the button in the frontend's `SCENARIOS` array in `App.jsx`.

### 2. Plug in a real weather API

Replace the simulator with live OpenWeatherMap data. Create a `weather_service.py`:

```python
import httpx
from rcam_engine import PrecipType

WEATHER_CODE_MAP = {
    500: PrecipType.RAIN,
    600: PrecipType.SNOW,
    511: PrecipType.FREEZING_RAIN,
    611: PrecipType.SLEET,
    800: PrecipType.NONE,
    # add more OpenWeatherMap codes as needed
}

async def fetch_weather(lat: float, lon: float, api_key: str) -> dict:
    url = f"https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={api_key}&units=metric"
    async with httpx.AsyncClient() as client:
        r = await client.get(url, timeout=5.0)
        d = r.json()
    return {
        "temp_c":         d["main"]["temp"],
        "precip_type":    WEATHER_CODE_MAP.get(d["weather"][0]["id"], PrecipType.NONE),
        "water_depth_mm": d.get("rain", {}).get("1h", 0) * 0.5,
    }
```

Then call `fetch_weather()` inside `build_snapshot()` and pass the result to the RCAM engine instead of the simulator.

### 3. Add a real friction sensor

If you have a Dynatest or ASFT friction measuring device, replace `sensor_simulator.py` with a serial/UDP reader:

```python
import serial

def read_friction_sensor(port="/dev/ttyUSB0", baud=9600) -> float:
    with serial.Serial(port, baud, timeout=1) as s:
        line = s.readline().decode().strip()
        return float(line)  # adjust parsing to your device's output format
```

### 4. Add a new runway zone

In `sensor_simulator.py`, add the zone to `ZONES` and `_ZONE_OFFSETS`:

```python
ZONES = ["touchdown", "midpoint", "rollout", "exit_taxiway"]

_ZONE_OFFSETS = {
    ...
    "exit_taxiway": { "temp": +0.5, "friction": +0.02, "water": -0.2 },
}
```

The RCAM engine and API will pick it up automatically.

### 5. Send alerts via email or SMS

Install a notifier and call it inside `build_snapshot()` when a CRITICAL alert is generated:

```python
# pip install sendgrid
import sendgrid

def send_email_alert(message: str):
    sg = sendgrid.SendGridAPIClient(api_key=os.environ["SENDGRID_KEY"])
    sg.client.mail.send.post(request_body={
        "personalizations": [{"to": [{"email": "atc@airport.com"}]}],
        "from": {"email": "alerts@runwayguard.io"},
        "subject": "⚠ Runway Condition Alert",
        "content": [{"type": "text/plain", "value": message}],
    })
```

### 6. Store historical data in a database

```python
# pip install sqlalchemy aiosqlite
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import DeclarativeBase, mapped_column, Mapped
import datetime

engine = create_async_engine("sqlite+aiosqlite:///runwayguard.db")

class RCCLog(Base):
    __tablename__ = "rcc_log"
    id:        Mapped[int]      = mapped_column(primary_key=True)
    timestamp: Mapped[datetime.datetime]
    zone:      Mapped[str]
    rcc:       Mapped[int]
    condition: Mapped[str]
    friction:  Mapped[float]
    temp_c:    Mapped[float]
```

Then insert a row each tick for full historical replay.

---

## Environment Variables (optional)

Create a `.env` file in the `backend/` folder:

```env
OPENWEATHER_API_KEY=your_key_here
AIRPORT_LAT=47.0258
AIRPORT_LON=21.9025
SENDGRID_KEY=your_key_here
```

Load them with:

```python
from dotenv import load_dotenv
load_dotenv()
api_key = os.getenv("OPENWEATHER_API_KEY")
```

---

## Running in Production

```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 1
```

> Use `--workers 1` — WebSocket state (connected clients, alert history) is held in memory and must stay on one process. For multi-worker deployments, move shared state to Redis.
