import { useEffect, useState } from 'react'
import { getAIDetection, getAlerts, getDashboardEventLog, getDevices, getDeviceDiagnostics, getDeviceSensors, getModelStatus, getSwitchStatus, getTasks, getTracks, getTrains, getWorkers } from '../services/api'
import { useCity } from '../context/CityContext'
import { cityOf } from '../utils/city'

const unwrap = (value) => value?.items ?? value?.data ?? value ?? []
const cityMatches = (item, city) => city === 'all' || cityOf(item) === city

function useLiveResource({ path, fetcher, deps = [], transform = unwrap }) {
  const [refreshToken, setRefreshToken] = useState(0)
  const [state, setState] = useState({ data: null, loading: true, error: null, updatedAt: null })
  useEffect(() => {
    let cancelled = false
    let timer
    const success = (value) => !cancelled && setState({ data: transform(value), loading: false, error: null, updatedAt: Date.now() })
    const failure = (error) => !cancelled && setState({ data: null, loading: false, error, updatedAt: null })
    setState({ data: null, loading: true, error: null, updatedAt: null })
    const poll = () => fetcher().then(success).catch(failure)
    poll()
    timer = window.setInterval(poll, 3000)
    return () => { cancelled = true; window.clearInterval(timer) }
  }, [...deps, refreshToken])
  return { ...state, refresh: () => setRefreshToken((value) => value + 1) }
}

export const useAlerts = (filters = {}) => { const { city } = useCity(); const apiFilters = Object.fromEntries(Object.entries(filters).filter(([key]) => ['severity', 'status', 'track', 'from', 'to'].includes(key))); return useLiveResource({ path: 'alerts', fetcher: () => getAlerts(apiFilters), deps: [JSON.stringify(filters), city], transform: (value) => unwrap(value).filter((item) => cityMatches(item, city)).filter((item) => Object.entries(filters).every(([key, expected]) => { if (!expected || ['time', 'q', 'tab'].includes(key)) return true; if (key === 'type') return (item.type || item.defect || item.class) === expected; return item[key] === expected })) }) }
export const useDashboardSummary = () => { const { city } = useCity(); const alerts = useAlerts(); const tasks = useTasks(); const devices = useDevices(); const items = Array.isArray(alerts.data) ? alerts.data : []; const taskItems = Array.isArray(tasks.data) ? tasks.data : []; const deviceItems = Array.isArray(devices.data) ? devices.data : []; return { data: { active_alerts: items.filter((item) => ['ACTIVE', 'ACKNOWLEDGED', 'ASSIGNED', 'UNDER_REPAIR'].includes(item.status)).length, s3_alerts: items.filter((item) => item.severity === 'S3').length, s2_alerts: items.filter((item) => item.severity === 'S2').length, s1_alerts: items.filter((item) => item.severity === 'S1').length, pending_tasks: taskItems.filter((item) => item.status !== 'COMPLETED').length, online_devices: deviceItems.filter((item) => item.status === 'ONLINE').length, total_devices: deviceItems.length, city }, loading: alerts.loading || tasks.loading || devices.loading, error: alerts.error || tasks.error || devices.error, updatedAt: Math.max(alerts.updatedAt || 0, tasks.updatedAt || 0, devices.updatedAt || 0) } }
export const useSwitchStatus = () => useLiveResource({ path: 'switch/status', fetcher: getSwitchStatus, deps: [] })
export const useSensorsLatest = (deviceId) => useLiveResource({ path: deviceId ? `devices/${deviceId}/sensors` : null, fetcher: () => getDeviceSensors(deviceId), deps: [deviceId] })
export const useSensorHistory = (deviceId, windowName = '24h') => useLiveResource({ path: null, fetcher: () => getDeviceSensors(deviceId, { history: true, window: windowName }), deps: [deviceId, windowName] })
export const useDeviceDiagnostics = (deviceId) => useLiveResource({ path: deviceId ? `devices/${deviceId}/diagnostics` : null, fetcher: () => getDeviceDiagnostics(deviceId), deps: [deviceId], transform: (value) => value })
export const useModelStatus = () => useLiveResource({ path: null, fetcher: getModelStatus, deps: [], transform: (value) => value?.model ?? value })
export const useAIDetection = () => useLiveResource({ path: null, fetcher: getAIDetection, deps: [], transform: (value) => value?.detection ?? value })
export const useWorkers = () => { const { city } = useCity(); return useLiveResource({ path: null, fetcher: getWorkers, deps: [city], transform: (value) => unwrap(value).filter((item) => cityMatches(item, city)) }) }
export const useDevices = () => { const { city } = useCity(); return useLiveResource({ path: 'devices', fetcher: getDevices, deps: [city], transform: (value) => unwrap(value).filter((item) => cityMatches(item, city)) }) }
export const useTasks = (workerId) => { const { city } = useCity(); return useLiveResource({ path: workerId ? `tasks/${workerId}` : null, fetcher: () => getTasks(workerId ? { worker_id: workerId } : {}), deps: [workerId, city], transform: (value) => unwrap(value).filter((item) => cityMatches(item, city)) }) }
export const useMapData = () => { const { city } = useCity(); return useLiveResource({ path: null, fetcher: () => Promise.all([getTracks(), getTrains()]).then(([tracks, trains]) => ({ tracks: unwrap(tracks).filter((item) => cityMatches(item, city)), trains: unwrap(trains).filter((item) => cityMatches(item, city)) })), deps: [city], transform: (value) => value }) }
export const useEventLog = (since = '') => useLiveResource({ path: null, fetcher: () => getDashboardEventLog({ since }), deps: [since], transform: (value) => unwrap(value).sort((a, b) => new Date(b.timestamp || b.created_at || 0) - new Date(a.timestamp || a.created_at || 0)) })
