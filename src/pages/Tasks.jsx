import React, { useState } from 'react'
import Header from '../components/Header'
import Drawer from '../components/Drawer'
import Lamp from '../components/Lamp'
import { EmptyState, ErrorState, LoadingState } from '../components/StateMessage'
import { useAlerts, usePendingUsers, useTasks, useWorkers } from '../hooks/useData'
import { apiErrorMessage, approveUser, createTask, rejectUser } from '../services/api'

export default function Tasks() {
  const [status, setStatus] = useState('')
  const [open, setOpen] = useState(false)
  const [alertId, setAlertId] = useState('')
  const [workerId, setWorkerId] = useState('')
  const [message, setMessage] = useState('')
  const [busyUserId, setBusyUserId] = useState('')
  const tasksState = useTasks()
  const alertsState = useAlerts({ status: 'ACKNOWLEDGED' })
  const workersState = useWorkers()
  const pendingState = usePendingUsers()
  const tasks = (Array.isArray(tasksState.data) ? tasksState.data : []).filter((task) => !status || task.status === status)
  const acknowledged = Array.isArray(alertsState.data) ? alertsState.data : []
  const workers = Array.isArray(workersState.data) ? workersState.data : []
  const pendingUsers = Array.isArray(pendingState.data) ? pendingState.data : []

  const submit = async (event) => {
    event.preventDefault()
    setMessage('')
    try {
      await createTask({ alert_id: alertId, worker_id: workerId, status: 'ASSIGNED' })
      setMessage('Task created.')
      setOpen(false)
      setAlertId('')
      setWorkerId('')
      tasksState.refresh()
      alertsState.refresh()
    } catch (error) {
      setMessage(apiErrorMessage(error, 'Task creation failed.'))
    }
  }

  const decideSignup = async (user, action) => {
    setBusyUserId(user.id)
    setMessage('')
    try {
      if (action === 'approve') await approveUser(user.id)
      else await rejectUser(user.id)
      setMessage(action === 'approve' ? `${user.name} approved as a worker.` : `${user.name} rejected.`)
      pendingState.refresh()
      workersState.refresh()
    } catch (error) {
      setMessage(apiErrorMessage(error, 'The account decision was not saved.'))
    } finally {
      setBusyUserId('')
    }
  }

  return <>
    <Header title="Tasks" text="Assign and monitor maintenance work." />
    <section className="panel pending-approvals" aria-labelledby="pending-approvals-title">
      <div className="panel-head"><h2 id="pending-approvals-title">Signup approvals</h2><span>{pendingState.loading ? 'Loading' : `${pendingUsers.length} pending`}</span></div>
      {pendingState.loading ? <LoadingState>Loading signup requests...</LoadingState> : pendingState.error ? <ErrorState>Unable to load pending accounts.</ErrorState> : pendingUsers.length ? <div className="admin-list">{pendingUsers.map((user) => <article className="admin-row pending-user-row" key={user.id}>
        <div><b>{user.name}</b><small className="data-line">{user.email} · {user.city || 'City not set'}</small></div>
        <div className="pending-user-actions"><button type="button" disabled={Boolean(busyUserId)} onClick={() => decideSignup(user, 'approve')}>{busyUserId === user.id ? 'Saving...' : 'Approve worker'}</button><button type="button" className="button-secondary" disabled={Boolean(busyUserId)} onClick={() => decideSignup(user, 'reject')}>Reject</button></div>
      </article>)}</div> : <EmptyState>No pending signup requests</EmptyState>}
    </section>

    <div className="toolbar-row"><label>Status<select value={status} onChange={(event) => setStatus(event.target.value)}><option value="">ALL</option><option>ASSIGNED</option><option>ACCEPTED</option><option>IN_PROGRESS</option><option>COMPLETED</option></select></label><button className="primary" onClick={() => setOpen(true)}>Assign Worker</button></div>
    {message && <p className="muted" role="status">{message}</p>}
    {tasksState.loading ? <LoadingState>Loading tasks...</LoadingState> : tasksState.error ? <ErrorState /> : tasks.length ? <div className="admin-list">{tasks.map((task) => <article className="admin-row" key={task.id}><Lamp severity={String(task.priority || task.severity || 'missing_data').toLowerCase()} label={task.priority || task.severity || 'NO DATA'} /><div><b>{task.defect || task.type || 'NO DATA'}</b><small className="data-line">{task.chainage || 'NO DATA'} · {task.worker_id || 'NO DATA'}</small></div><code>{task.status || 'NO DATA'}</code></article>)}</div> : <EmptyState>No tasks</EmptyState>}
    <Drawer open={open} title="Assign Worker" onClose={() => setOpen(false)}><form className="drawer-form" onSubmit={submit}><label>Acknowledged alert<select required value={alertId} onChange={(event) => setAlertId(event.target.value)}><option value="">Select alert</option>{acknowledged.map((alert) => <option key={alert.id} value={alert.id}>{alert.id} · {alert.defect || 'NO DATA'}</option>)}</select></label><label>Worker<select required value={workerId} onChange={(event) => setWorkerId(event.target.value)}><option value="">Select worker</option>{workers.map((worker) => <option key={worker.id || worker.worker_id} value={worker.id || worker.worker_id}>{worker.name || worker.id || 'NO DATA'}</option>)}</select></label><button className="primary" type="submit">Create task</button></form></Drawer>
  </>
}
