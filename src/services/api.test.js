import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import axios from 'axios'
import { api, apiErrorMessage, getWorkers, registerUnauthorizedHandler } from './api'

const makeStorage = (entries = {}) => {
  const values = new Map(Object.entries(entries))
  return {
    getItem: (key) => values.get(key) ?? null,
    setItem: (key, value) => values.set(key, value),
    removeItem: (key) => values.delete(key),
  }
}

describe('API client auth and response handling', () => {
  let originalWindow

  beforeEach(() => {
    originalWindow = globalThis.window
    globalThis.window = { localStorage: makeStorage(), sessionStorage: makeStorage() }
  })

  afterEach(() => {
    registerUnauthorizedHandler(undefined)
    api.defaults.adapter = axios.defaults.adapter
    globalThis.window = originalWindow
  })

  it('ignores malformed local auth and uses valid session auth safely', async () => {
    window.localStorage = makeStorage({ amrin_auth: '{broken' })
    window.sessionStorage = makeStorage({ amrin_auth: JSON.stringify({ token: 'session-token' }) })
    const config = { headers: new axios.AxiosHeaders(), data: null }
    const prepared = await api.interceptors.request.handlers[0].fulfilled(config)
    expect(prepared.headers.Authorization).toBe('Bearer session-token')
    expect(window.localStorage.getItem('amrin_auth')).toBeNull()
  })

  it('does not throw when all stored auth is malformed', async () => {
    window.localStorage = makeStorage({ amrin_auth: '{broken' })
    window.sessionStorage = makeStorage({ amrin_auth: 'null' })
    const config = { headers: new axios.AxiosHeaders(), data: null }
    expect(api.interceptors.request.handlers[0].fulfilled(config)).toBe(config)
    expect(config.headers.Authorization).toBeUndefined()
  })

  it('lets the browser set the multipart content boundary', async () => {
    const headers = new axios.AxiosHeaders({ 'Content-Type': 'application/json' })
    const config = { headers, data: new FormData() }
    await api.interceptors.request.handlers[0].fulfilled(config)
    expect(headers.hasContentType()).toBe(false)
  })

  it('clears the current session on private 401s but not failed login attempts', async () => {
    const logout = vi.fn()
    registerUnauthorizedHandler(logout)
    const reject = api.interceptors.response.handlers[0].rejected
    await expect(reject({ response: { status: 401 }, config: { url: '/auth/login' } })).rejects.toBeTruthy()
    expect(logout).not.toHaveBeenCalled()
    await expect(reject({ response: { status: 401 }, config: { url: '/tasks' } })).rejects.toBeTruthy()
    expect(logout).toHaveBeenCalledOnce()
  })

  it('keeps API error messages and list envelopes intact', async () => {
    expect(apiErrorMessage({ response: { data: { error: { message: 'Pending approval' } } } })).toBe('Pending approval')
    api.defaults.adapter = async (config) => ({
      data: { items: [{ id: 'worker-01', status: 'ACTIVE' }] },
      status: 200,
      statusText: 'OK',
      headers: new axios.AxiosHeaders(),
      config,
    })
    await expect(getWorkers()).resolves.toEqual({ items: [{ id: 'worker-01', status: 'ACTIVE' }] })
  })
})
