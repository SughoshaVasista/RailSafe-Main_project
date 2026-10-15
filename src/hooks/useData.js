import { useEffect, useState } from 'react'
import { getAIDetection, getAlerts, getDashboardEventLog, getDashboardSummary, getDevices, getDeviceDiagnostics, getDeviceSensors, getModelStatus, getSimulationState, getSwitchStatus, getTasks, getTracks, getTrains, getWorkers } from '../services/api'

const unwrap = (value) => value?.items ?? value?.data ?? value ?? []

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

export const useAlerts = (filters = {}) => useLiveResource({ path: 'alerts', fetcher: () => getAlerts(filters), deps: [JSON.stringify(filters)], transform: (value) => unwrap(value).filter((item) => Object.entries(filters).every(([key, expected]) => { if (!expected) return true; if (key === 'type') return (item.type || item.defect || item.class) === expected; return item[key] === expected })) })
export const useDashboardSummary = () => useLiveResource({ path: 'dashboard/summary', fetcher: getDashboardSummary, deps: [], transform: (value) => value?.summary ?? value })
export const useSwitchStatus = () => useLiveResource({ path: 'switch/status', fetcher: getSwitchStatus, deps: [] })
export const useSensorsLatest = (deviceId) => useLiveResource({ path: deviceId ? `devices/${deviceId}/sensors` : null, fetcher: () => getDeviceSensors(deviceId), deps: [deviceId] })
export const useSensorHistory = (deviceId, windowName = '24h') => useLiveResource({ path: null, fetcher: () => getDeviceSensors(deviceId, { history: true, window: windowName }), deps: [deviceId, windowName] })
export const useDeviceDiagnostics = (deviceId) => useLiveResource({ path: deviceId ? `devices/${deviceId}/diagnostics` : null, fetcher: () => getDeviceDiagnostics(deviceId), deps: [deviceId], transform: (value) => value })
export const useModelStatus = () => useLiveResource({ path: null, fetcher: getModelStatus, deps: [], transform: (value) => value?.model ?? value })
export const useAIDetection = () => useLiveResource({ path: null, fetcher: getAIDetection, deps: [], transform: (value) => value?.detection ?? value })
export const useSimulationState = () => useLiveResource({ path: null, fetcher: getSimulationState, deps: [] })
export const useWorkers = () => useLiveResource({ path: null, fetcher: getWorkers, deps: [] })
export const useDevices = () => useLiveResource({ path: 'devices', fetcher: getDevices, deps: [] })
export const useTasks = (workerId) => useLiveResource({ path: workerId ? `tasks/${workerId}` : null, fetcher: () => getTasks(workerId ? { worker_id: workerId } : {}), deps: [workerId] })
export const useMapData = () => useLiveResource({ path: null, fetcher: () => Promise.all([getTracks(), getTrains()]).then(([tracks, trains]) => ({ tracks: unwrap(tracks), trains: unwrap(trains) })), deps: [], transform: (value) => value })
export const useEventLog = (since = '') => useLiveResource({ path: null, fetcher: () => getDashboardEventLog({ since }), deps: [since], transform: (value) => unwrap(value).sort((a, b) => new Date(b.timestamp || b.created_at || 0) - new Date(a.timestamp || a.created_at || 0)) })
