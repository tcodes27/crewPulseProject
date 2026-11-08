import { useCallback, useEffect, useState } from 'react'

type Flight = {
  flight_id: number
  flight_number: string
  origin: string
  destination: string
  scheduled_departure: string
  status: string
  crew_assignments: number
  crew_coverage: 'ADEQUATE' | 'INSUFFICIENT'
}

type FlightResponse = {
  flights: Flight[]
  kpis: {
    total_flights: number
    scheduled_flights: number
    delayed_flights: number
    crew_assignments: number
  }
}

const emptyKpis: FlightResponse['kpis'] = {
  total_flights: 0,
  scheduled_flights: 0,
  delayed_flights: 0,
  crew_assignments: 0,
}

function formatDeparture(value: string) {
  return new Intl.DateTimeFormat('en-US', {
    month: 'short',
    day: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    timeZoneName: 'short',
  }).format(new Date(value))
}

function App() {
  const [data, setData] = useState<FlightResponse>({ flights: [], kpis: emptyKpis })
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null)

  const loadFlights = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const response = await fetch('/api/flights')
      if (!response.ok) throw new Error('Flight data could not be loaded. Check that the API and database are available.')
      const payload = (await response.json()) as FlightResponse
      setData(payload)
      setLastUpdated(new Date())
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Something went wrong while loading flights.')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void loadFlights()
  }, [loadFlights])

  const cards = [
    { label: 'Total flights', value: data.kpis.total_flights, tone: 'blue', icon: '✈' },
    { label: 'Scheduled', value: data.kpis.scheduled_flights, tone: 'green', icon: '◷' },
    { label: 'Delayed', value: data.kpis.delayed_flights, tone: 'amber', icon: '↗' },
    { label: 'Crew assignments', value: data.kpis.crew_assignments, tone: 'violet', icon: '♧' },
  ]

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <a className="brand" href="#overview" aria-label="CrewPulse home">
          <span className="brand-mark">C<span>✦</span></span>
          <span className="brand-name">Crew<span>Pulse</span></span>
        </a>
        <div className="nav-caption">WORKSPACE</div>
        <a className="nav-link active" href="#overview"><span className="nav-icon">▦</span> Overview</a>
        <div className="sidebar-bottom">
          <div className="data-note"><span className="note-icon">i</span><span><b>Synthetic data</b><small>Portfolio demonstration</small></span></div>
          <div className="profile"><span className="avatar">CP</span><span><b>Operations</b><small>Flight control</small></span><span className="profile-dots">···</span></div>
        </div>
      </aside>

      <main className="main-content" id="overview">
        <header className="topbar">
          <div className="breadcrumb"><span>Workspace</span><span className="crumb-separator">/</span><b>Operations overview</b></div>
          <div className="topbar-right"><span className="live-indicator"><i /> SYSTEM ONLINE</span><span className="topbar-date">Flight operations</span></div>
        </header>

        <section className="page-content">
          <div className="page-heading">
            <div>
              <div className="eyebrow">FLIGHT CONTROL CENTER</div>
              <h1>Operations overview</h1>
              <p className="subtitle">A clear view of today’s flight activity and crew readiness.</p>
            </div>
            <button className="refresh-button" onClick={() => void loadFlights()} disabled={loading}>
              <span className={loading ? 'refresh-symbol spinning' : 'refresh-symbol'}>↻</span> Refresh data
            </button>
          </div>

          <div className="overview-strip"><span className="strip-dot" /> Live operations snapshot <span className="strip-divider">•</span> {lastUpdated ? `Updated ${lastUpdated.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}` : 'Waiting for data'}</div>

          <section className="kpi-grid" aria-label="Flight overview metrics">
            {cards.map((card, index) => (
              <article className="kpi-card" key={card.label} style={{ animationDelay: `${index * 70}ms` }}>
                <div className="kpi-top"><span>{card.label}</span><span className={`kpi-icon ${card.tone}`}>{card.icon}</span></div>
                <div className="kpi-value">{loading ? <span className="skeleton-number" /> : card.value.toLocaleString()}</div>
                <div className="kpi-foot"><span className={`kpi-foot-dot ${card.tone}`} /> Current network total</div>
              </article>
            ))}
          </section>

          <section className="flights-panel">
            <div className="panel-heading">
              <div><div className="panel-title-row"><h2>Flight schedule</h2><span className="row-count">{loading ? '—' : data.flights.length} flights</span></div><p>Scheduled departures and crew coverage across the network.</p></div>
              <span className="schedule-badge"><span /> LIVE SCHEDULE</span>
            </div>
            {error ? (
              <div className="state-box error-state"><span className="state-symbol">!</span><h3>Unable to load flights</h3><p>{error}</p><button className="retry-button" onClick={() => void loadFlights()}>Try again</button></div>
            ) : loading ? (
              <div className="table-wrap"><table><thead><tr><th>FLIGHT</th><th>ROUTE</th><th>SCHEDULED DEPARTURE</th><th>STATUS</th><th>CREW COVERAGE</th></tr></thead><tbody>{[1, 2, 3, 4].map((n) => <tr className="loading-row" key={n}><td><i /><i /></td><td><i /></td><td><i /></td><td><i /></td><td><i /></td></tr>)}</tbody></table></div>
            ) : data.flights.length === 0 ? (
              <div className="state-box"><span className="state-symbol">✈</span><h3>No flights in the schedule</h3><p>Flight activity will appear here when data is available.</p></div>
            ) : (
              <div className="table-wrap"><table><thead><tr><th>FLIGHT</th><th>ROUTE</th><th>SCHEDULED DEPARTURE</th><th>STATUS</th><th>CREW COVERAGE</th></tr></thead><tbody>{data.flights.map((flight) => <tr key={flight.flight_id}>
                <td><span className="flight-number"><span className="flight-glyph">✈</span>{flight.flight_number}</span></td>
                <td><span className="route-cell"><b>{flight.origin}</b><span className="route-line">⟶</span><b>{flight.destination}</b></span></td>
                <td className="departure-cell">{formatDeparture(flight.scheduled_departure)}</td>
                <td><span className={`status-pill ${flight.status.toLowerCase()}`}><i />{flight.status}</span></td>
                <td><span className={`coverage-pill ${flight.crew_coverage.toLowerCase()}`}><span className="coverage-icon">{flight.crew_coverage === 'ADEQUATE' ? '✓' : '!'}</span><span>{flight.crew_coverage === 'ADEQUATE' ? 'Adequate' : 'Insufficient'}<small>{flight.crew_assignments} assigned</small></span></span></td>
              </tr>)}</tbody></table></div>
            )}
            {!loading && !error && data.flights.length > 0 && <div className="table-footer"><span>Showing <b>{data.flights.length}</b> scheduled flights</span><span>Data refreshes on demand</span></div>}
          </section>
          <footer className="page-footer"><span>CREWPULSE OPERATIONS</span><span>Independent portfolio project · Synthetic data for demonstration</span></footer>
        </section>
      </main>
    </div>
  )
}

export default App
