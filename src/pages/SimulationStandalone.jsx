import React, { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { decide } from '../sim/decision'
import SeverityBadge from '../components/ui/SeverityBadge'

const scenarios = {
  clear_clear: { label: 'Clear / Clear', state: {} },
  s3_on_A: { label: 'S3 on A', state: { track_A_defect: 'S3' } },
  s2_on_A_B_occupied: { label: 'S2 on A + B occupied', state: { track_A_defect: 'S2', track_B_occupied: true } },
  both_s3: { label: 'Both S3', state: { track_A_defect: 'S3', track_B_defect: 'S3' } },
  too_close: { label: 'Too close', state: { distance_to_switch: 10 } },
}
const initialCustom = { track_A_defect: 'NONE', track_B_defect: 'NONE', track_A_occupied: false, track_B_occupied: false, switch_A_available: true, switch_B_available: true, distance_to_switch: 80 }

export default function SimulationStandalone() {
  const [scenario, setScenario] = useState('clear_clear')
  const [custom, setCustom] = useState(initialCustom)
  const [speed, setSpeed] = useState(1)
  const [position, setPosition] = useState(0)
  const [playing, setPlaying] = useState(false)
  const [events, setEvents] = useState([])
  const customMode = scenario === 'custom'
  const selectedState = customMode ? custom : scenarios[scenario].state
  const decision = useMemo(() => decide({ distance_to_switch: 80, delay_score: 1, ...selectedState }, { trainId: 'demo-train', switchId: 'demo-switch', position }), [selectedState, position])
  useEffect(() => {
    if (!playing) return undefined
    const reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches
    const timer = window.setInterval(() => {
      setPosition((current) => {
        if (current >= 620) { setPlaying(false); return 0 }
        return Math.min(620, current + (reduced ? 155 : 4 * speed))
      })
    }, reduced ? 300 : 100)
    return () => window.clearInterval(timer)
  }, [playing, speed])
  useEffect(() => { setEvents((current) => [{ time: new Date().toISOString(), action: decision.action, target: decision.target_track || 'NONE' }, ...current].slice(0, 12)) }, [decision.action, decision.target_track, scenario, position])
  const setCustomValue = (key, value) => setCustom((current) => ({ ...current, [key]: value }))
  const step = () => setPosition((current) => current >= 620 ? 0 : Math.min(620, current + 62))
  const reset = () => { setPlaying(false); setPosition(0); setScenario('clear_clear'); setCustom(initialCustom) }
  const scorePercent = (score) => score === null ? 0 : Math.max(0, Math.min(100, score * 100))
  return <main className="simulator">
    <div className="simulation-warning">SIMULATION: NO LIVE DATA</div>
    <header className="simulator-head"><div><p className="eyebrow">AMRIN decision support</p><h1>Track simulator</h1></div><Link to="/login">Back to dashboard</Link></header>
    <div className="simulator-layout">
      <section className="schematic" aria-label="Track schematic">
        <svg viewBox="0 0 760 300" role="img" aria-label="Two track simulation schematic">
          <text x="20" y="32">START</text><text x="660" y="32">END</text><text x="230" y="103">TRACK A</text><text x="230" y="215">TRACK B</text><text x="278" y="72">JCT A</text><text x="410" y="184">JCT B</text>
          <path d="M70 90H690M70 200H690M300 90L430 200" />
          <circle cx="300" cy="90" r="5" /><circle cx="430" cy="200" r="5" />
          {selectedState.track_A_defect && selectedState.track_A_defect !== 'NONE' && <><path className={`sim-segment sim-${selectedState.track_A_defect.toLowerCase()}`} d="M450 90H530" /><text className="sim-severity-label" x="474" y="80">{selectedState.track_A_defect}</text></>}
          {selectedState.track_B_defect && selectedState.track_B_defect !== 'NONE' && <><path className={`sim-segment sim-${selectedState.track_B_defect.toLowerCase()}`} d="M450 200H530" /><text className="sim-severity-label" x="474" y="190">{selectedState.track_B_defect}</text></>}
          <rect className="sim-train" x={70 + position} y={position > 360 ? 188 : 78} width="30" height="18" />
        </svg>
        <div className="sim-controls"><button className="button-secondary" onClick={() => setPlaying(true)} disabled={playing}>Play</button><button className="button-secondary" onClick={() => setPlaying(false)} disabled={!playing}>Pause</button><button className="button-secondary" onClick={step}>Step</button><button className="button-secondary" onClick={reset}>Reset</button><span>Speed</span>{[1, 2, 4].map((value) => <button className={`speed-button ${speed === value ? 'selected' : ''}`} key={value} onClick={() => setSpeed(value)}>{value}x</button>)}</div>
        <p className="mono">Train position {position} m · {playing ? 'MOVING' : 'STOPPED'}</p>
      </section>
      <section className="sim-panel">
        <h2>Scenarios</h2>
        {Object.entries(scenarios).map(([key, item]) => <label className="scenario-option" key={key}><input type="radio" checked={scenario === key} onChange={() => { setScenario(key); setPlaying(false) }} />{item.label}</label>)}
        <label className="scenario-option"><input type="radio" checked={customMode} onChange={() => { setScenario('custom'); setPlaying(false) }} />Custom</label>
        {customMode && <div className="custom-scenario">{['A', 'B'].map((track) => <fieldset key={track}><legend>Track {track}</legend><label>Defect<select value={custom[`track_${track}_defect`]} onChange={(event) => setCustomValue(`track_${track}_defect`, event.target.value)}>{['NONE', 'S1', 'S2', 'S3'].map((value) => <option key={value}>{value}</option>)}</select></label><label><input type="checkbox" checked={custom[`track_${track}_occupied`]} onChange={(event) => setCustomValue(`track_${track}_occupied`, event.target.checked)} />Occupied</label><label><input type="checkbox" checked={custom[`switch_${track}_available`]} onChange={(event) => setCustomValue(`switch_${track}_available`, event.target.checked)} />Switch available</label></fieldset>)}<label>Distance to switch (m)<input type="number" min="0" value={custom.distance_to_switch} onChange={(event) => setCustomValue('distance_to_switch', Number(event.target.value))} /></label></div>}
        <h2>Decision</h2><dl className="detail-list"><dt>Action</dt><dd>{decision.action}</dd><dt>Target</dt><dd>{decision.target_track || 'NONE'}</dd><dt>Confidence</dt><dd className="mono">{decision.confidence}</dd><dt>Reason</dt><dd>{decision.reason}</dd></dl>
        <div className="sim-rules">{decision.rules_checked.map((rule) => <p key={rule.rule}><span className={rule.passed ? 'pass' : 'fail'}>{rule.passed ? '✓ PASS' : '× FAIL'}</span>{rule.rule}</p>)}</div>
        <div className="sim-scores">{Object.entries(decision.raw_scores).map(([track, score]) => <div key={track}>Track {track}<div className="sim-score-track"><i style={{ width: `${scorePercent(score)}%` }} /></div><strong>{score === null ? 'BLOCKED' : score.toFixed(2)}</strong></div>)}</div>
        <div className="sim-lamps"><span className={decision.action === 'MAINTAIN' ? 'active' : ''}>Maintain A</span><span className={decision.action === 'SWITCH' ? 'active' : ''}>Switch B</span><span className={decision.action === 'EMERGENCY_STOP' ? 'active' : ''}>Emergency stop</span></div>
        <SeverityBadge severity={decision.action === 'EMERGENCY_STOP' ? 'S3' : decision.action_level === 'WARNING' ? 'S2' : 'S1'} />
        <h2>Event log</h2><ol className="sim-event-log">{events.map((event, index) => <li key={`${event.time}-${index}`}><time>{event.time}</time> {event.action} · {event.target}</li>)}</ol>
      </section>
    </div>
  </main>
}
