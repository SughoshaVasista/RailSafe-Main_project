import React from 'react'
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import 'leaflet/dist/leaflet.css'
import './styles/tokens.css'
import './styles/base.css'
import './styles/components.css'
import Login from './pages/Login'
import Shell from './components/Shell'
import ProtectedRoute from './components/ProtectedRoute'
import { AuthProvider } from './context/AuthContext'
import { ThemeProvider } from './context/ThemeContext'

export default function App() {
  return <BrowserRouter><AuthProvider><ThemeProvider><Routes><Route path="/login" element={<Login />} /><Route element={<ProtectedRoute allowedRoles={['admin', 'worker']} />}><Route path="/*" element={<Shell />} /></Route><Route path="*" element={<Navigate to="/login" replace />} /></Routes></ThemeProvider></AuthProvider></BrowserRouter>
}
