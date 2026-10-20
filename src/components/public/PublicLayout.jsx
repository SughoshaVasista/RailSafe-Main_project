import React, { useState } from 'react'
import { Link, NavLink, Outlet } from 'react-router-dom'
import { ArrowUpRight, Menu, TrainFront, X } from 'lucide-react'
import { useAuth } from '../../context/AuthContext'
import '../../styles/public.css'

const links = [
  ['/about', 'About'],
  ['/how-it-works', 'How it works'],
  ['/technology', 'Technology'],
  ['/contact', 'Contact'],
]

export function PublicFooter() {
  return <footer className="public-footer"><div className="public-container public-footer-main"><div><Link className="public-brand" to="/"><span className="public-brand-mark"><TrainFront size={17} /></span><span>AMRIN</span></Link><p>Autonomous Multi-Sensor Rail Inspection Node</p><small>Prototype · Monitoring and maintenance decision support</small></div><nav aria-label="Footer navigation">{links.map(([to, label]) => <Link key={to} to={to}>{label}</Link>)}<Link to="/login">Dashboard login</Link></nav></div><div className="public-container public-footer-bottom"><span>AMRIN railway monitoring prototype</span><span>Decision support only · Not signalling control</span></div></footer>
}

export default function PublicLayout() {
  const { user } = useAuth()
  const [menuOpen, setMenuOpen] = useState(false)
  const dashboardPath = user?.role === 'admin' ? '/admin' : '/worker'
  return <div className="public-site"><a className="public-skip" href="#main-content">Skip to content</a><header className="public-header"><div className="public-container public-header-inner"><Link className="public-brand" to="/" aria-label="AMRIN home"><span className="public-brand-mark"><TrainFront size={17} /></span><span>AMRIN</span></Link><button className="public-menu-toggle" type="button" aria-label={menuOpen ? 'Close navigation' : 'Open navigation'} aria-expanded={menuOpen} onClick={() => setMenuOpen((open) => !open)}>{menuOpen ? <X size={20} /> : <Menu size={20} />}</button><nav className={`public-nav ${menuOpen ? 'is-open' : ''}`} aria-label="Main navigation">{links.map(([to, label]) => <NavLink key={to} to={to} onClick={() => setMenuOpen(false)} className={({ isActive }) => isActive ? 'public-nav-link active' : 'public-nav-link'}>{label}</NavLink>)}<Link className="public-login" to={user ? dashboardPath : '/login'} onClick={() => setMenuOpen(false)}>{user ? 'Open dashboard' : 'Dashboard login'}<ArrowUpRight size={15} aria-hidden="true" /></Link></nav></div></header><main id="main-content"><Outlet /></main><PublicFooter /></div>
}
