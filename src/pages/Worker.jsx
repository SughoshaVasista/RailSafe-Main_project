import React, { useEffect, useMemo, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { ArrowLeft, MapPin, Upload } from 'lucide-react'
import { MapContainer, Marker, TileLayer } from 'react-leaflet'
import Header from '../components/Header'
import Lamp from '../components/Lamp'
import { EmptyState, ErrorState, ImageUnavailable, LoadingState, GpsUnavailable } from '../components/StateMessage'
import { useAuth } from '../context/AuthContext'
import { useTheme } from '../context/ThemeContext'
import { useTasks } from '../hooks/useData'
import { updateTaskStatus, uploadTaskEvidence } from '../services/api'

const steps = ['ASSIGNED', 'ACCEPTED', 'IN_PROGRESS', 'COMPLETED']
const labels = { ASSIGNED: 'Assigned', ACCEPTED: 'Accepted', IN_PROGRESS: 'In Progress', COMPLETED: 'Completed' }
const nextStatus = { ASSIGNED: 'ACCEPTED', ACCEPTED: 'IN_PROGRESS', IN_PROGRESS: 'COMPLETED' }
const buttonLabel = { ASSIGNED: 'Accept', ACCEPTED: 'Start Repair', IN_PROGRESS: 'Upload Photo', COMPLETED: 'Completed' }
const display = (value) => value === undefined || value === null || value === '' ? 'NO DATA' : value
const distanceKm = (from, to) => {
  const radians = (degrees) => degrees * Math.PI / 180
  const [lat1, lon1] = from.map(radians); const [lat2, lon2] = to.map(radians)
  const a = Math.sin((lat2 - lat1) / 2) ** 2 + Math.cos(lat1) * Math.cos(lat2) * Math.sin((lon2 - lon1) / 2) ** 2
  return 6371 * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a))
}

function MiniMap({ task }) {
  const gps = task.gps || {}; const lat = Number(gps.lat ?? gps.latitude); const lng = Number(gps.lng ?? gps.longitude)
  if (!Number.isFinite(lat) || !Number.isFinite(lng)) return <GpsUnavailable />
  return <div className="mini-map"><MapContainer center={[lat, lng]} zoom={15} scrollWheelZoom={false} dragging={false} tap={false}><TileLayer url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" attribution="&copy; OpenStreetMap contributors" /><Marker position={[lat, lng]} /></MapContainer></div>
}

function JobRow({ task, index, position }) {
  const gps = task.gps || {}
  const lat = Number(gps.lat ?? gps.latitude ?? task.lat ?? task.latitude)
  const lng = Number(gps.lng ?? gps.longitude ?? task.lng ?? task.longitude)
  const hasDestination = Number.isFinite(lat) && Number.isFinite(lng)
  const away = position && hasDestination ? distanceKm(position, [lat, lng]) : null
  return <Link className={`worker-card ${index === 0 ? 'next-job' : ''}`} to={`/worker/${task.id}`}>
    <div className="worker-card-top"><Lamp severity={String(task.priority || task.severity || 'offline').toLowerCase()} label={task.priority || task.severity || 'NO DATA'} /><code>{display(task.id)}</code></div>
    <div className="worker-card-body"><div><p className="eyebrow">{index === 0 ? 'Next job' : 'Assigned job'}</p><h2>{display(task.defect || task.type)}</h2><p className="data-line">{display(task.chainage)} · {display(task.track)}</p><small>{display(labels[task.status] || task.status)}</small>{index === 0 && away !== null && <p className="worker-distance">{away.toFixed(1)} km away</p>}{hasDestination && <span className="worker-navigate"><a href={`https://www.google.com/maps/dir/?api=1&destination=${lat},${lng}`} onClick={(event) => event.stopPropagation()}>Navigate</a></span>}</div>{task.thumbnail || task.image_url ? <img src={task.thumbnail || task.image_url} alt="Defect thumbnail" /> : <div className="thumbnail-empty"><ImageUnavailable /></div>}</div>
  </Link>
}
function Comparison({ before, after }) {
  const [position, setPosition] = useState(50)
  if (!before && !after) return <ImageUnavailable />
  return <div className={`comparison ${before && after ? 'has-both' : ''}`}><div className="comparison-image comparison-after">{after ? <img src={after} alt="After repair" /> : <ImageUnavailable />}</div>{before && after && <div className="comparison-before" style={{ width: `${position}%` }}><img src={before} alt="Before repair" /></div>}{before && after && <input aria-label="Compare before and after repair" type="range" min="0" max="100" value={position} onChange={(event) => setPosition(event.target.value)} />}</div>
}

function StatusStepper({ status }) {
  const currentIndex = steps.indexOf(status)
  return <div className="worker-stepper">{steps.map((step, index) => <div className={`worker-step ${index <= currentIndex ? 'complete' : ''} ${step === status ? 'current' : ''}`} key={step}><Lamp severity={index <= currentIndex ? 'clear' : 'offline'} label={labels[step]} /></div>)}</div>
}

function TaskDetail({ task, refresh }) {
  const [file, setFile] = useState(null); const [notes, setNotes] = useState(''); const [busy, setBusy] = useState(false); const [error, setError] = useState(''); const [uploaded, setUploaded] = useState(false)
  const status = String(task.status || 'ASSIGNED').toUpperCase(); const canUpload = status === 'IN_PROGRESS'; const actionText = canUpload && uploaded ? 'Mark Complete' : buttonLabel[status] || 'NO DATA'
  const advance = async () => { setBusy(true); setError(''); try { if (canUpload && !uploaded) { if (!file) { setError('Select a repair photo before continuing.'); return } const body = new FormData(); body.append('file', file); body.append('notes', notes); await uploadTaskEvidence(task.id, body); setUploaded(true); return } const next = nextStatus[status]; if (next) { await updateTaskStatus(task.id, { status: next }); refresh?.() } } catch { setError('The server did not accept this update.') } finally { setBusy(false) } }
  const sensors = Array.isArray(task.sensors) ? task.sensors : task.sensors && typeof task.sensors === 'object' ? Object.entries(task.sensors).map(([name, value]) => ({ name, value })) : []
  const before = task.before_image || task.before_image_url; const after = task.after_image || task.after_image_url
  return <div className="worker-detail"><div className="worker-detail-head"><Link className="back-link" to="/worker"><ArrowLeft size={18} />Assigned jobs</Link><Lamp severity={String(task.priority || 'offline').toLowerCase()} label={task.priority || 'NO DATA'} /></div><div className="worker-detail-grid"><section className="worker-detail-main"><div className="worker-image">{task.image_url || task.image ? <img src={task.image_url || task.image} alt="Defect" /> : <ImageUnavailable />}</div><section className="worker-section"><h2>Before / after</h2><Comparison before={before} after={after} /></section><section className="worker-section"><h2>Location</h2><p className="data-line"><MapPin size={15} /> {display(task.chainage)} · {display(task.track)}</p><MiniMap task={task} /></section></section><aside className="worker-detail-side"><section className="worker-section"><p className="eyebrow">Defect</p><h1>{display(task.defect || task.type)}</h1><p className="data-line">{display(task.chainage)}</p></section><section className="worker-section"><h2>Status</h2><StatusStepper status={status} /></section><section className="worker-section"><h2>Sensor readout</h2>{sensors.length ? <div className="worker-sensor-table">{sensors.map((sensor, index) => <div key={sensor.name || index}><span>{display(sensor.name)}</span><code>{display(sensor.value)} {sensor.unit || ''}</code><small>{display(sensor.status)}</small></div>)}</div> : <EmptyState>No sensor data</EmptyState>}</section><section className="worker-section"><h2>Notes from admin</h2><p className="muted">{display(task.admin_notes || task.notes)}</p></section>{canUpload && !uploaded && <section className="worker-section upload-box"><label className="file-button"><Upload size={17} />Upload Repair Photo<input type="file" accept="image/*" capture="environment" onChange={(event) => setFile(event.target.files?.[0] || null)} /></label><textarea value={notes} onChange={(event) => setNotes(event.target.value)} placeholder="Repair notes" rows="4" /></section>}{error && <p className="login-error">{error}</p>}<button className="primary worker-primary" disabled={busy || status === 'COMPLETED' || !nextStatus[status] || (canUpload && !uploaded && !file)} onClick={advance}>{busy ? 'Updating...' : actionText}</button></aside></div></div>
}

export default function Worker() {
  const { taskId } = useParams(); const { user } = useAuth(); const { theme, setTheme } = useTheme(); const workerId = user?.worker_id || user?.id; const state = useTasks(workerId); const [position, setPosition] = useState(null); const [locationMessage, setLocationMessage] = useState('')
  useEffect(() => { if (!window.localStorage.getItem('amrin_theme') && theme !== 'light') setTheme('light') }, [theme, setTheme])
  const items = useMemo(() => { const list = Array.isArray(state.data) ? state.data : []; return list.filter((task) => !task.worker_id || task.worker_id === workerId) }, [state.data, workerId]); const critical = items.some((task) => String(task.priority || task.severity).toUpperCase() === 'S3'); const task = taskId ? items.find((item) => String(item.id) === String(taskId)) : null
  if (taskId) return <>{state.loading ? <LoadingState>Loading task...</LoadingState> : state.error ? <ErrorState /> : task ? <TaskDetail task={task} refresh={state.refresh} /> : <EmptyState>No maintenance tasks assigned</EmptyState>}</>
  const requestLocation = () => { setLocationMessage(''); if (!navigator.geolocation) { setLocationMessage('Location is unavailable in this browser.'); return } navigator.geolocation.getCurrentPosition(({ coords }) => { setPosition([coords.latitude, coords.longitude]); setLocationMessage('Distance uses your current browser location.') }, (error) => { setLocationMessage(error.code === error.PERMISSION_DENIED ? 'Location permission was not granted.' : 'Could not read your current location.') }, { enableHighAccuracy: false, timeout: 10000, maximumAge: 60000 }) }
  return <>
    <Header title="Assigned jobs" text={`${display(user?.name)} · ${display(user?.city || 'Assigned city')}`} />
    {critical && <div className="critical-banner"><Lamp severity="critical" label="S3" /><strong>Critical defect assigned. Follow the safety procedure.</strong></div>}
    {items.length > 0 && <div className="worker-location-control"><button className="button-secondary" onClick={requestLocation}>Calculate distance from my location</button>{locationMessage && <small role="status">{locationMessage}</small>}</div>}
    <div className="worker-list">
      {state.loading ? <LoadingState>Loading tasks...</LoadingState> : state.error ? <ErrorState /> : items.length ? items.map((taskItem, index) => <JobRow key={taskItem.id} task={taskItem} index={index} position={position} />) : <EmptyState>No maintenance tasks assigned</EmptyState>}
    </div>
  </>
}



