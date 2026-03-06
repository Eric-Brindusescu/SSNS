# 🛬 RunwayGuard — Live Runway Condition Monitor

Real-time runway grip prediction system built for **HackTech Airport Chapter 2026**.

Calculates and transmits runway contamination levels (ice, snow, water) to ATC and cockpit displays using the **ICAO RCAM standard (RCC 0–6)**.

---

## What It Does

- Ingests live sensor data (temperature, friction coefficient, precipitation type, water/snow depth)
- Classifies each runway zone (Touchdown / Midpoint / Rollout) using the ICAO Runway Condition Assessment Matrix
- Streams real-time updates to an ATC dashboard and a cockpit display via WebSocket
- Fires CRITICAL / WARNING alerts when grip degrades below safe thresholds

---

## ICAO Runway Condition Codes (RCC)

| RCC | Surface Condition | Braking Action |
|-----|------------------|----------------|
| 6   | Dry              | Good           |
| 5   | Wet (≤ 3 mm)     | Good           |
| 4   | Dry snow / Frost | Medium to Good |
| 3   | Wet snow / Compacted snow | Medium |
| 2   | Standing water / Slush | Medium to Poor |
| 1   | Ice              | Poor           |
| 0   | Wet ice          | Nil            |

---

## Project Structure

```
HAC/
├── backend/
│   ├── main.py              # FastAPI server + WebSocket endpoint
│   ├── rcam_engine.py       # ICAO RCAM classification logic
│   ├── sensor_simulator.py  # Simulated IoT sensor readings
│   └── requirements.txt
└── frontend/
    ├── index.html
    ├── vite.config.js
    ├── package.json
    └── src/
        ├── main.jsx
        ├── App.jsx          # ATC Dashboard + Cockpit Display
        └── App.css
```

---

## Requirements

- **Python** 3.10+
- **Node.js** 18+ and **npm**

---

## How to Run

### 1. Clone the repository

```bash
git clone https://github.com/Eric-Brindusescu/HAC.git
cd HAC
```

### 2. Start the backend

```bash
cd backend

# Install Python dependencies
pip install -r requirements.txt

# Start the server
python main.py
```

Backend runs at: `http://localhost:8000`

### 3. Start the frontend

Open a **second terminal**:

```bash
cd frontend

# Install Node dependencies
npm install

# Start the dev server
npm run dev
```

Frontend runs at: `http://localhost:5173`

### 4. Open the app

Go to **http://localhost:5173** in your browser.

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/status` | Current snapshot of all zones |
| GET | `/api/scenarios` | List available demo scenarios |
| POST | `/api/scenario/{name}` | Switch active scenario |
| WS | `/ws` | WebSocket stream (updates every 3s) |

---

## Demo Scenarios

Switch scenarios in real time using the buttons in the UI:

| Scenario | Conditions | Expected RCC |
|----------|-----------|--------------|
| ☀️ Clear | Dry, 18–30°C | 6 |
| 🌧 Light Rain | Rain, water ≤ 3mm | 5 |
| ⛈ Heavy Rain | Rain, standing water | 3 |
| 🌨 Snow | Snowfall, -5 to 0°C | 3–4 |
| ❄️ Freezing Rain | Freezing rain, -3 to 1°C | 2 |
| 🧊 Black Ice | Ice, -10 to -2°C | 1 |

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python, FastAPI, WebSockets |
| Classification | ICAO RCAM rule engine |
| Sensor data | Simulated IoT readings with realistic drift |
| Frontend | React 18, Vite |
| Styling | Pure CSS (aviation dark theme) |
| Real-time | Native WebSocket |

---

## Team

Built at **HackTech Airport Chapter — Oradea International Airport (OMR), 6–8 March 2026**
