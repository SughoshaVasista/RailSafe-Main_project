import React, { useEffect, useMemo, useState } from 'react'
import { Search, UserPlus } from 'lucide-react'
import Header from '../components/Header'
import { EmptyState, ErrorState, LoadingState } from '../components/StateMessage'
import { useAuth } from '../context/AuthContext'
import { apiErrorMessage, createManagedUser, getManagedUsers, setManagedUserActive } from '../services/api'

const emptyForm = { name: '', username: '', email: '', password: '', role: 'admin', city: '' }

function dateLabel(value) {
  if (!value) return 'Not recorded'
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? 'Not recorded' : date.toLocaleString()
}

export default function Users() {
  const { user: currentUser } = useAuth()
  const [users, setUsers] = useState([])
  const [loading, setLoading] = useState(true)
  const [listError, setListError] = useState('')
  const [search, setSearch] = useState('')
  const [formOpen, setFormOpen] = useState(false)
  const [form, setForm] = useState(emptyForm)
  const [saving, setSaving] = useState(false)
  const [busyId, setBusyId] = useState('')
  const [notice, setNotice] = useState('')
  const [error, setError] = useState('')

  async function refreshUsers() {
    setLoading(true)
    setListError('')
    try {
      const response = await getManagedUsers()
      setUsers(Array.isArray(response.items) ? response.items : [])
    } catch (failure) {
      setListError(apiErrorMessage(failure, 'Unable to load users.'))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { refreshUsers() }, [])

  const filteredUsers = useMemo(() => {
    const query = search.trim().toLowerCase()
    if (!query) return users
    return users.filter((item) => `${item.username || ''} ${item.email || ''}`.toLowerCase().includes(query))
  }, [search, users])

  function updateField(event) {
    setForm((current) => ({ ...current, [event.target.name]: event.target.value }))
  }

  async function submitUser(event) {
    event.preventDefault()
    setSaving(true)
    setError('')
    setNotice('')
    try {
      const created = await createManagedUser({ ...form, city: form.city.trim() || null })
      setNotice(`${created.role === 'admin' ? 'Administrator' : 'Worker'} account created for ${created.name}.`)
      setForm(emptyForm)
      setFormOpen(false)
      await refreshUsers()
    } catch (failure) {
      setError(apiErrorMessage(failure, 'Unable to create this account.'))
    } finally {
      setSaving(false)
    }
  }

  async function toggleActive(account) {
    const isActive = account.status !== 'ACTIVE'
    setBusyId(account.id)
    setError('')
    setNotice('')
    try {
      const updated = await setManagedUserActive(account.id, isActive)
      setUsers((current) => current.map((item) => item.id === account.id ? updated : item))
      setNotice(`${updated.name} is now ${updated.status.toLowerCase()}.`)
    } catch (failure) {
      setError(apiErrorMessage(failure, 'Unable to update account status.'))
    } finally {
      setBusyId('')
    }
  }

  return <>
    <Header title="Manage Users" text="Create accounts and manage access for administrators and workers." />
    <section className="user-management" aria-labelledby="user-list-title">
      <div className="user-management-toolbar">
        <div><h2 id="user-list-title">User accounts</h2><p className="muted">Only administrators can create or change accounts. Public signup requests remain worker accounts.</p></div>
        <button className="primary user-add-button" type="button" onClick={() => { setFormOpen((open) => !open); setError(''); setNotice('') }}><UserPlus size={16} />{formOpen ? 'Close form' : 'Add user'}</button>
      </div>

      {notice && <p className="user-notice" role="status">{notice}</p>}
      {error && <p className="login-error" role="alert">{error}</p>}

      {formOpen && <form className="user-create-form" onSubmit={submitUser}>
        <div className="user-form-heading"><h2>Create account</h2><p className="muted">Accounts created here are approved immediately. Use at least 12 characters for the password.</p></div>
        <label>Name<input name="name" value={form.name} onChange={updateField} maxLength="160" autoComplete="name" required /></label>
        <label>Username<input name="username" value={form.username} onChange={updateField} minLength="3" maxLength="80" autoComplete="username" pattern="[A-Za-z0-9._-]+" title="Use letters, numbers, periods, underscores, or hyphens." required /></label>
        <label>Email<input name="email" type="email" value={form.email} onChange={updateField} maxLength="254" autoComplete="email" required /></label>
        <label>Password<input name="password" type="password" value={form.password} onChange={updateField} minLength="12" maxLength="256" autoComplete="new-password" required /></label>
        <label>Role<select name="role" value={form.role} onChange={updateField}><option value="admin">Administrator</option><option value="worker">Worker</option></select></label>
        <label>City <span className="muted">(optional)</span><input name="city" value={form.city} onChange={updateField} maxLength="80" autoComplete="address-level2" /></label>
        <div className="user-form-actions"><button className="primary" type="submit" disabled={saving}>{saving ? 'Creating account...' : 'Create account'}</button><button className="button-secondary" type="button" disabled={saving} onClick={() => { setForm(emptyForm); setFormOpen(false); setError('') }}>Cancel</button></div>
      </form>}

      <label className="user-search"><Search size={16} aria-hidden="true" /><span className="sr-only">Search users by username or email</span><input type="search" value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Search username or email" /></label>
      {loading ? <LoadingState>Loading users...</LoadingState> : listError ? <ErrorState>{listError}</ErrorState> : filteredUsers.length === 0 ? <EmptyState>{search ? 'No accounts match that search' : 'No user accounts found'}</EmptyState> : <div className="admin-list user-account-list">{filteredUsers.map((account) => <article className="admin-row user-account-row" key={account.id}>
        <div className="user-account-main"><div className="user-account-heading"><strong>{account.name}</strong><span className={`user-status ${account.status === 'ACTIVE' ? 'active' : 'inactive'}`}>{account.status}</span></div><span>{account.username ? `@${account.username} · ` : ''}{account.email}</span><small>{account.role === 'admin' ? 'Administrator' : 'Worker'}{account.city ? ` · ${account.city}` : ''} · {account.approval_status}</small>
          <details className="user-account-details"><summary>Account details</summary><dl><dt>User ID</dt><dd>{account.id}</dd><dt>Worker ID</dt><dd>{account.worker_id || '—'}</dd><dt>Created</dt><dd>{dateLabel(account.created_at)}</dd></dl></details>
        </div>
        <button className="button-secondary user-status-button" type="button" disabled={busyId === account.id || account.id === currentUser?.id} title={account.id === currentUser?.id ? 'You cannot deactivate your own account.' : undefined} onClick={() => toggleActive(account)}>{busyId === account.id ? 'Saving...' : account.status === 'ACTIVE' ? 'Deactivate' : 'Activate'}</button>
      </article>)}</div>}
    </section>
  </>
}
