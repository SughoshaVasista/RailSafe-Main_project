import React, { createContext, useContext, useEffect, useMemo, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { cities } from '../config/cities'

const CityContext = createContext(null)

export function CityProvider({ children }) {
  const [params, setParams] = useSearchParams()
  const [city, setCityState] = useState(() => window.localStorage.getItem('amrin_city') || params.get('city') || 'all')
  const setCity = (value) => { setCityState(value); window.localStorage.setItem('amrin_city', value); const next = new URLSearchParams(window.location.search); if (value === 'all') next.delete('city'); else next.set('city', value); setParams(next, { replace: true }) }
  useEffect(() => { const urlCity = params.get('city'); if (urlCity && urlCity !== city && (urlCity === 'all' || cities.some((item) => item.id === urlCity))) setCityState(urlCity) }, [params, city])
  const value = useMemo(() => ({ city, setCity, cities }), [city])
  return <CityContext.Provider value={value}>{children}</CityContext.Provider>
}

export const useCity = () => useContext(CityContext) || { city: 'all', setCity: () => {}, cities }
