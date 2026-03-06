import { useState, useEffect, useRef } from 'react'

const WS_URL  = 'ws://localhost:8000/ws'
const API_URL = 'http://localhost:8000'

// ── RCC metadata ─────────────────────────────────────────────────────────────

const RCC_META = {
  6: { label: 'DRY',           color: '#00C851', glow: 'rgba(0,200,81,0.35)',   bg: 'rgba(0,200,81,0.08)' },
  5: { label: 'WET',           color: '#7CFC00', glow: 'rgba(124,252,0,0.35)', bg: 'rgba(124,252,0,0.08)' },
  4: { label: 'CAUTION',       color: '#FFD700', glow: 'rgba(255,215,0,0.35)', bg: 'rgba(255,215,0,0.08)' },
  3: { label: 'REDUCED',       color: '#FFA500', glow: 'rgba(255,165,0,0.35)', bg: 'rgba(255,165,0,0.08)' },
  2: { label: 'POOR',          color: '#FF4444', glow: 'rgba(255,68,68,0.40)',  bg: 'rgba(255,68,68,0.10)' },
  1: { label: 'POOR',          color: '#CC0000', glow: 'rgba(204,0,0,0.45)',   bg: 'rgba(204,0,0,0.12)' },
  0: { label: 'NIL',           color: '#FF0000', glow: 'rgba(255,0,0,0.55)',   bg: 'rgba(140,0,0,0.18)' },
}
const meta = (rcc) => RCC_META[rcc] ?? { label: '--', color: '#607080', glow: 'transparent', bg: 'transparent' }

const ZONE_LABELS = ['TOUCHDOWN', 'MIDPOINT', 'ROLLOUT']

const SCENARIOS = [
  { id: 'clear_summer',  label: '☀️ Clear',         rcc: 6 },
  { id: 'light_rain',    label: '🌧 Light Rain',     rcc: 5 },
  { id: 'heavy_rain',    label: '⛈ Heavy Rain',     rcc: 3 },
  { id: 'snow',          label: '🌨 Snow',           rcc: 4 },
  { id: 'freezing_rain', label: '❄️ Freezing Rain',  rcc: 2 },
  { id: 'icy',           label: '🧊 Black Ice',      rcc: 1 },
]


// ── Runway diagram ────────────────────────────────────────────────────────────

function RunwayDiagram({ zones }) {
  if (!zones?.length) return <div className="runway-placeholder">Awaiting sensor data…</div>

  return (
    <div className="runway-wrap">
      <div className="runway-id">RWY 09 ←————————————————————→ RWY 27 &nbsp;|&nbsp; ORADEA INTL (OMR)</div>

      <div className="runway">
        {/* Threshold markings */}
        <div className="rwy-threshold left">
          {[...Array(6)].map((_, i) => <div key={i} className="threshold-bar" />)}
        </div>

        {zones.map((z, i) => {
          const m = meta(z.rcc)
          return (
            <div
              key={z.zone}
              className="rwy-zone"
              style={{ background: m.bg, borderColor: m.color, boxShadow: `inset 0 0 30px ${m.bg}` }}
            >
              <div className="rzy-label">{ZONE_LABELS[i]}</div>
              <div className="rzy-rcc" style={{ color: m.color, textShadow: `0 0 12px ${m.glow}` }}>
                {z.rcc}
              </div>
              <div className="rzy-cond">{z.condition}</div>
              <div className="rzy-brake" style={{ color: m.color }}>{z.braking_action}</div>
              <div className="rzy-metrics">
                <span title="Temperature">🌡 {z.temp_c}°C</span>
                <span title="Water/snow depth">💧 {z.water_depth_mm}mm</span>
                <span title="Friction coefficient">μ {z.friction}</span>
              </div>
            </div>
          )
        })}

        {/* Threshold markings */}
        <div className="rwy-threshold right">
          {[...Array(6)].map((_, i) => <div key={i} className="threshold-bar" />)}
        </div>

        {/* Centre-line dashes */}
        <div className="rwy-centreline" />
      </div>
    </div>
  )
}


// ── Alert feed ────────────────────────────────────────────────────────────────

function AlertFeed({ alerts }) {
  return (
    <div className="alert-feed">
      <div className="feed-title">⚡ LIVE ALERTS</div>
      {!alerts?.length
        ? <div className="feed-ok">✓ No active alerts — runway nominal</div>
        : [...alerts].reverse().map((a, i) => (
            <div key={i} className={`feed-item feed-${a.level.toLowerCase()}`}>
              <span className="feed-lvl">{a.level}</span>
              <span className="feed-msg">{a.message}</span>
              <span className="feed-time">{a.timestamp?.slice(11, 19)} UTC</span>
            </div>
          ))
      }
    </div>
  )
}


// ── Scenario selector ─────────────────────────────────────────────────────────

function ScenarioSelector({ current, onSelect }) {
  return (
    <div className="scenarios">
      <div className="scenarios-title">▸ DEMO SCENARIOS</div>
      <div className="scenarios-row">
        {SCENARIOS.map(s => {
          const m = meta(s.rcc)
          const active = current === s.id
          return (
            <button
              key={s.id}
              className={`scn-btn ${active ? 'scn-active' : ''}`}
              style={active ? { borderColor: m.color, color: m.color, background: m.bg } : {}}
              onClick={() => onSelect(s.id)}
            >
              {s.label}
            </button>
          )
        })}
      </div>
    </div>
  )
}


// ── ATC Dashboard view ────────────────────────────────────────────────────────

function ATCView({ data, onScenario }) {
  const rcc = data?.overall_rcc ?? 6
  const m   = meta(rcc)

  return (
    <div className="atc-view">
      <div className="atc-left">
        <RunwayDiagram zones={data?.zones} />
        <ScenarioSelector current={data?.scenario} onSelect={onScenario} />
      </div>

      <div className="atc-right">
        <div className="overall-card" style={{ borderColor: m.color, background: m.bg }}>
          <div className="ov-label">OVERALL RCC</div>
          <div className="ov-number" style={{ color: m.color, textShadow: `0 0 30px ${m.glow}` }}>
            {rcc}
          </div>
          <div className="ov-brake" style={{ color: m.color }}>{data?.overall_braking ?? '--'}</div>
          <div className="ov-status" style={{ color: m.color }}>{m.label}</div>
        </div>

        <AlertFeed alerts={data?.alert_history} />
      </div>
    </div>
  )
}


// ── Cockpit Display view ──────────────────────────────────────────────────────

function CockpitView({ data }) {
  const rcc      = data?.overall_rcc ?? 6
  const m        = meta(rcc)
  const critical = rcc <= 1
  const warning  = rcc <= 3

  const warningMsg =
    rcc === 0 ? 'NIL BRAKING — DO NOT LAND' :
    rcc === 1 ? 'EXTREME CAUTION — POOR BRAKING ACTION' :
    rcc === 2 ? 'CAUTION — MEDIUM TO POOR BRAKING' :
                'REDUCED BRAKING — USE CAUTION'

  return (
    <div className="cockpit" style={{ background: `radial-gradient(ellipse at 50% 40%, ${m.bg} 0%, #050a12 65%)` }}>
      <div className="ck-header">RUNWAY CONDITION REPORT</div>
      <div className="ck-airport">ORADEA INTERNATIONAL (OMR) &nbsp;·&nbsp; RWY 09/27</div>

      <div className={`ck-rcc-wrap ${critical ? 'ck-pulse' : ''}`}>
        <div className="ck-rcc-lbl">RUNWAY CONDITION CODE</div>
        <div className="ck-rcc-num" style={{ color: m.color, textShadow: `0 0 60px ${m.glow}, 0 0 20px ${m.glow}` }}>
          {rcc}
        </div>
        <div className="ck-rcc-sub" style={{ color: m.color }}>{m.label}</div>
      </div>

      <div className="ck-brake" style={{ color: m.color }}>
        BRAKING ACTION: {data?.zones?.[0]?.braking_action ?? '--'}
      </div>

      {warning && (
        <div className={`ck-warning ${critical ? 'ck-critical-warn' : ''}`} style={{ color: m.color, borderColor: m.color }}>
          ⚠&nbsp; {warningMsg}
        </div>
      )}

      <div className="ck-zones">
        {(data?.zones ?? []).map((z, i) => {
          const zm = meta(z.rcc)
          return (
            <div key={z.zone} className="ck-zone" style={{ borderColor: zm.color, background: zm.bg }}>
              <div className="ck-zone-lbl">{ZONE_LABELS[i]}</div>
              <div className="ck-zone-rcc" style={{ color: zm.color }}>RCC {z.rcc}</div>
              <div className="ck-zone-cond">{z.condition}</div>
              <div className="ck-zone-brake" style={{ color: zm.color }}>{z.braking_action}</div>
              <div className="ck-zone-temp">{z.temp_c}°C · μ {z.friction}</div>
            </div>
          )
        })}
      </div>

      <div className="ck-ts">
        Last update: {data?.timestamp?.slice(0, 19).replace('T', ' ') ?? '--'} UTC
      </div>
    </div>
  )
}


// ── Root App ─────────────────────────────────────────────────────────────────

export default function App() {
  const [view,      setView]      = useState('atc')
  const [data,      setData]      = useState(null)
  const [connected, setConnected] = useState(false)
  const [clock,     setClock]     = useState(new Date())
  const wsRef = useRef(null)

  // UTC clock
  useEffect(() => {
    const t = setInterval(() => setClock(new Date()), 1000)
    return () => clearInterval(t)
  }, [])

  // WebSocket with auto-reconnect
  useEffect(() => {
    let alive = true
    function connect() {
      if (!alive) return
      const ws = new WebSocket(WS_URL)
      wsRef.current = ws
      ws.onopen    = () => setConnected(true)
      ws.onmessage = e => { try { setData(JSON.parse(e.data)) } catch {} }
      ws.onclose   = () => { setConnected(false); if (alive) setTimeout(connect, 3000) }
      ws.onerror   = () => ws.close()
    }
    connect()
    return () => { alive = false; wsRef.current?.close() }
  }, [])

  const handleScenario = (name) =>
    fetch(`${API_URL}/api/scenario/${name}`, { method: 'POST' })

  const rcc = data?.overall_rcc ?? 6
  const m   = meta(rcc)

  return (
    <div className="app">
      {/* ── Header ── */}
      <header className="hdr">
        <div className="hdr-left">
          <span className="hdr-logo">🛬 RunwayGuard</span>
          <span className={`hdr-live ${connected ? 'hdr-live-on' : 'hdr-live-off'}`}>
            {connected ? '● LIVE' : '○ CONNECTING…'}
          </span>
        </div>

        <div className="hdr-center">
          <button className={`vtab ${view === 'atc'     ? 'vtab-on' : ''}`} onClick={() => setView('atc')}>
            ATC DASHBOARD
          </button>
          <button className={`vtab ${view === 'cockpit' ? 'vtab-on' : ''}`} onClick={() => setView('cockpit')}>
            COCKPIT DISPLAY
          </button>
        </div>

        <div className="hdr-right">
          <span className="hdr-rcc" style={{ color: m.color }}>RCC {rcc} — {m.label}</span>
          <span className="hdr-clock">
            {clock.toUTCString().slice(17, 25)} UTC
          </span>
        </div>
      </header>

      {/* ── Main ── */}
      <main className="main-area">
        {view === 'atc'
          ? <ATCView     data={data} onScenario={handleScenario} />
          : <CockpitView data={data} />
        }
      </main>
    </div>
  )
}
