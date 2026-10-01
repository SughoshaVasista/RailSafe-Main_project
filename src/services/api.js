import axios from 'axios'

export const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api',
  timeout: 8000,
})

let unauthorizedHandler
export const registerUnauthorizedHandler = (handler) => { unauthorizedHandler = handler }

api.interceptors.request.use((config) => {
  const raw = window.localStorage.getItem('amrin_auth') || window.sessionStorage.getItem('amrin_auth')
  const auth = raw ? JSON.parse(raw) : null
  if (auth?.token) config.headers.Authorization = `Bearer ${auth.token}`
  return config
})

api.interceptors.response.use((response) => response, (error) => {
  if (error.response?.status === 401) unauthorizedHandler?.()
  return Promise.reject(error)
})

const get = (path, params) => api.get(path, { params }).then(({ data }) => data)
const post = (path, body) => api.post(path, body).then(({ data }) => data)

export const loginRequest = (credentials) => post('/auth/login', credentials)
export const getAlerts = (filters = {}) => get('/alerts', filters)
export const getAlert = (id) => get(`/alerts/${id}`)
export const acknowledgeAlert = (id, body) => post(`/alerts/${id}/acknowledge`, body)
export const resolveAlert = (id, body) => post(`/alerts/${id}/resolve`, body)
export const markFalsePositive = (id, body) => post(`/alerts/${id}/false-positive`, body)
export const assignAlert = (id, body) => post(`/alerts/${id}/assign`, body)
export const changeAlertPriority = (id, body) => post(`/alerts/${id}/priority`, body)
export const getAlertHistory = (id) => get(`/alerts/${id}/history`)
export const getDevices = () => get('/devices')
export const getDeviceSensors = (id, params = {}) => get(`/devices/${id}/sensors`, params)
export const getDeviceDiagnostics = (id) => get(`/devices/${id}/diagnostics`)
export const getTasks = (params = {}) => get('/tasks', params)
export const createTask = (body) => post('/tasks', body)
export const getWorkers = () => get('/workers')
export const updateTaskStatus = (id, body) => api.put(`/tasks/${id}/status`, body).then(({ data }) => data)
export const uploadTaskEvidence = (id, body) => api.post(`/tasks/${id}/evidence`, body).then(({ data }) => data)
export const getTracks = (params = {}) => get('/tracks', params)
export const getTrains = (params = {}) => get('/trains', params)
export const getSwitchStatus = (params = {}) => get('/switch/status', params)
export const postSwitchDecision = (body) => post('/switch/decision', body)
export const setSimulationMode = (body) => post('/simulation/mode', body)
export const getSimulationState = () => get('/simulation/state')
export const getDashboardSummary = (params = {}) => get('/dashboard/summary', params)
export const getDashboardEventLog = (params = {}) => get('/dashboard/event-log', params)
export const getModelStatus = () => get('/model/status')
export const getAIDetection = () => get('/ai/detection')
