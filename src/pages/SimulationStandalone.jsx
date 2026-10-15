import React, { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { decide } from '../sim/decision'
import SeverityBadge from '../components/ui/SeverityBadge'

const scenarios = { clear_clear: { label: 'Clear / Clear', state: {} }, s3_on_A: { label: 'S3 on A', state: { track_A_defect: 'S3' } }, s2_on_A_B_occupied: { label: 'S2 on A + B occupied', state: { track_A_defect: 'S2', track_B_occupied: true } }, both_s3: { label: 'Both S3', state: { track_A_defect: 'S3', track_B_defect: 'S3' } }, too_close: { label: 'Too close', state: { distance_to_switch: 10 } } }

export default function SimulationStandalone() {
  const [scenario, setScenario] = useState('clear_clear')
  const [playing, setPlaying] = useState(false)
  const [speed, setSpeed] = useState(1)
  const [position, setPosition] = useState(0)
  const selected = scenarios[scenario]
  const decision = useMemo(() => decide({ distance_to_switch: 80, delay_score: 1, ...selected.state }, { trainId: 'demo-train', switchId: 'demo-switch' }), [selected])

  useEffect(() => {
    if (!playing) return undefined
    const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches
    const timer = window.setInterval(() => {
      setPosition((current) => {
        if (current >= 600) { setPlaying(false); return 0 }
        return Math.min(600, current + (reducedMotion ? 60 : speed * 6))
      })
    }, reducedMotion ? 500 : 100)
    return () => window.clearInterval(timer)
  }, [playing, speed])

  const step = () => setPosition((current) => current >= 600 ? 0 : Math.min(600, current + 60))
  const reset = () => { setPlaying(false); setPosition(0); setScenario('clear_clear') }
  return <main className="simulator"><div className="simulation-warning">SIMULATION: NO LIVE DATA</div><header className="simulator-head"><div><p className="eyebrow">AMRIN decision support</p><h1>Track simulator</h1></div><Link to="/login">Back to dashboard</Link></header><div className="simulator-layout"><section className="schematic" aria-label="Track schematic"><svg viewBox="0 0 760 300" role="img"><text x="20" y="32">START</text><text x="660" y="32">END</text><text x="230" y="103">TRACK A</text><text x="230" y="215">TRACK B</text><path d="M70 90H690M70 200H690M300 90L430 200" /><circle cx="300" cy="90" r="5" /><circle cx="430" cy="200" r="5" /><rect x={70 + position} y="78" width="30" height="18" /></svg><div className="sim-controls"><button className="button-secondary" onClick={() => setPlaying(true)} disabled={playing}>Play</button><button className="button-secondary" onClick={() => setPlaying(false)} disabled={!playing}>Pause</button><button className="button-secondary" onClick={step}>Step</button><button className="button-secondary" onClick={reset}>Reset</button><span className="speed-label">Speed</span><div className="speed-control" role="group" aria-label="Playback speed">{[1, 2, 4].map((value) => <button key={value} type="button" className={speed === value ? 'selected' : ''} aria-pressed={speed === value} onClick={() => setSpeed(value)}>{value}×</button>)}</div><span className="sim-position">{position} m · {playing ? 'MOVING' : 'STOPPED'}</span></div></section><section className="sim-panel"><h2>Scenarios</h2>{Object.entries(scenarios).map(([key, item]) => <label className="scenario-option" key={key}><input type="radio" checked={scenario === key} onChange={() => setScenario(key)} />{item.label}</label>)}<h2>Decision</h2><dl className="detail-list"><dt>Action</dt><dd>{decision.action}</dd><dt>Target</dt><dd>{decision.target_track || 'NONE'}</dd><dt>Confidence</dt><dd className="mono">{decision.confidence}</dd><dt>Reason</dt><dd>{decision.reason}</dd></dl><div className="sim-rules">{decision.rules_checked.map((rule) => <p key={rule.rule}><span className={rule.passed ? 'pass' : 'fail'}>{rule.passed ? 'PASS' : 'FAIL'}</span>{rule.rule}</p>)}</div><div className="sim-scores"><div>Track A <strong>{decision.raw_scores.A ?? 'BLOCKED'}</strong></div><div>Track B <strong>{decision.raw_scores.B ?? 'BLOCKED'}</strong></div></div><SeverityBadge severity={decision.action === 'EMERGENCY_STOP' ? 'S3' : decision.action_level === 'WARNING' ? 'S2' : 'S1'} /></section></div></main>
}
