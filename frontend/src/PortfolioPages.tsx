import { useState } from 'react'

const TABLEAU_URL = 'https://public.tableau.com/views/CrewPulseFlightOperationsAnalytics/Dashboard1?:showVizHome=no&:showTabs=false&:toolbar=yes'

const stages = [
  { title: 'Data ingestion and synthetic data generation', tech: 'Python · pandas · OurAirports', body: 'The airport ingestion script downloads the OurAirports CSV (or accepts a local source), validates IATA codes, removes duplicates, and upserts eligible rows. A seeded generator creates 100 synthetic crew members, 200 flights, and two assignments per flight.' },
  { title: 'PostgreSQL database architecture', tech: 'PostgreSQL · raw / core / ops / analytics', body: 'Schemas separate source data, operational entities, run and quality records, and reporting views. Core tables store airports, crew, flights, assignments, and assignment history; SQL defines constraints and reusable analytics views.' },
  { title: 'Python pipeline and orchestration', tech: 'Python · SQLAlchemy · subprocess', body: 'The orchestration entry point records an ops.pipeline_runs row and runs the ingestion and data-quality scripts as subprocesses. Steps report success or failure; individual scripts persist their run outcomes and counts.' },
  { title: 'Data quality and bitemporal history', tech: 'SQL · pytest · PostgreSQL', body: 'Quality checks persist PASS, WARNING, or FAIL results for flight schedules, routes, duplicate assignments, and history consistency. Assignment history records effective time and recorded time, with SQL queries for as-of and audit analysis.' },
  { title: 'FastAPI backend development', tech: 'FastAPI · SQLAlchemy', body: 'The API serves flight schedule and KPI data plus read-only pipeline monitoring endpoints. Requests use a shared SQLAlchemy session dependency, parameterized queries, read-only transactions, and sanitized database errors.' },
  { title: 'React and TypeScript frontend', tech: 'React · TypeScript · Vite', body: 'The Vite application fetches flight rows from /api/flights and renders operational KPIs, loading and error states, a schedule, and crew coverage. VITE_API_BASE_URL configures the API origin; Vite proxies /api during local development.' },
  { title: 'GitHub source control', tech: 'Git · GitHub Actions', body: 'The repository tracks application, SQL, and pipeline code. A GitHub Actions workflow runs the automated Python test suite against a PostgreSQL test service.' },
  { title: 'Render backend deployment', tech: 'FastAPI · Render', body: 'The production API is deployed as a FastAPI service on Render. The frontend calls its public API origin through VITE_API_BASE_URL, and the backend allows configured frontend origins through FRONTEND_ORIGINS.' },
  { title: 'Cloudflare frontend deployment', tech: 'Vite · Cloudflare Workers static assets', body: 'Vite builds the React application into frontend/dist. wrangler.jsonc points Cloudflare Workers static assets to that directory and enables single-page application fallback for client-side paths.' },
  { title: 'Neon production database connectivity', tech: 'PostgreSQL · Neon · DATABASE_URL', body: 'The project database was migrated from local PostgreSQL to Neon. Render receives the production connection string as a server-side DATABASE_URL; it is not embedded in frontend assets.' },
  { title: 'Production testing and troubleshooting', tech: 'HTTP · browser · pytest', body: 'The live dashboard was checked against API responses. Deployment fixes included correcting the API base URL, adding Vite environment types, setting production CORS origins and environment variables, and confirming Cloudflare serves the built assets.' },
]

const components = [
  { id: 'pipeline', title: 'Python data pipeline', detail: 'Reads and transforms airport source data, generates synthetic operations records, records pipeline outcomes, and runs data-quality checks. Writes to PostgreSQL / Neon.', lane: 'engineering' },
  { id: 'database', title: 'PostgreSQL / Neon', detail: 'Stores raw, core, ops, and analytics schemas. It receives pipeline writes and serves the live FastAPI read path.', lane: 'shared' },
  { id: 'api', title: 'FastAPI / Render', detail: 'Reads operational and monitoring data from PostgreSQL through read-only SQLAlchemy transactions, then returns JSON to the browser.', lane: 'live' },
  { id: 'frontend', title: 'React / TypeScript / Vite', detail: 'The dashboard requests /api/flights from the configured API origin and renders the returned operational data.', lane: 'live' },
  { id: 'cloudflare', title: 'Cloudflare Workers', detail: 'Serves the Vite production build from frontend/dist with SPA fallback. Browser API requests go to the configured Render origin.', lane: 'live' },
  { id: 'github', title: 'GitHub', detail: 'Holds project source and runs the automated test workflow. It is the source control layer, not the live data path.', lane: 'delivery' },
  { id: 'tableau', title: 'Tableau Public', detail: 'Hosts the interactive analytics workbook built from exported CSV analytical datasets. It is a separate visualization path from the live React API dashboard.', lane: 'analytics' },
]

const metrics = [
  ['9,053', 'Airports'], ['100', 'Crew members'], ['200', 'Flights'], ['400', 'Crew assignments'],
  ['401', 'Assignment history records'], ['13', 'Pipeline run records'], ['39', 'Data quality results'], ['3', 'Analytics views'],
]

const lessons = [
  ['Local PostgreSQL to Neon', 'The application initially depended on a local database. The project data was migrated to Neon and connection settings were moved to environment configuration.', 'Keep database connection configuration outside source and verify the migrated data at the destination.'],
  ['FastAPI production connectivity', 'The deployed API needed to reach the production database. Render was configured with the production DATABASE_URL and the API reused its normal SQLAlchemy session setup.', 'Test the deployed service against the real configured database rather than relying only on local development.'],
  ['Render backend deployment', 'The API needed an always-addressable production endpoint for the frontend. It was deployed on Render and its origin configured for browser requests.', 'Keep the API origin explicit and validate the health and data endpoints after deployment.'],
  ['Cloudflare Vite assets', 'Cloudflare needed the generated Vite files and a fallback for application paths. Wrangler was pointed at frontend/dist with single-page application handling.', 'Check build output paths and SPA fallback settings together.'],
  ['Incorrect API base URL', 'The production frontend initially targeted the wrong API origin. VITE_API_BASE_URL was corrected to the deployed backend URL.', 'Inspect the built application’s public configuration when a page loads but its data request fails.'],
  ['Vite environment types', 'TypeScript did not know the Vite import.meta.env shape. The project added the Vite client type reference.', 'Type environment access so configuration mistakes surface during the production build.'],
  ['CORS and production variables', 'Browser calls needed an allowed frontend origin and deployment-specific variables. FRONTEND_ORIGINS and the frontend API origin were configured in their respective services.', 'CORS is part of the browser request path; configure exact deployed origins alongside environment values.'],
  ['Production dashboard verification', 'A successful static deploy did not prove that live data loaded. The dashboard was checked against actual API responses.', 'Validate the full browser-to-API-to-database path after deployment, including returned data and failure states.'],
]

export function AnalyticsPage() {
  const [loaded, setLoaded] = useState(false)
  return <section className="portfolio-page" id="analytics">
    <div className="page-heading"><div><div className="eyebrow">VISUAL ANALYTICS</div><h1>Flight operations analytics</h1><p className="subtitle">Explore the interactive Tableau Public workbook.</p></div></div>
    <div className="portfolio-panel tableau-panel">
      <div className="portfolio-panel-heading"><div><h2>CrewPulse Flight Operations Analytics</h2><p>Interactive workbook · Dashboard1 · Tableau Public</p></div><a className="external-link" href="https://public.tableau.com/views/CrewPulseFlightOperationsAnalytics/Dashboard1" target="_blank" rel="noreferrer">Open dashboard ↗</a></div>
      <div className="tableau-frame-wrap">
        {!loaded && <div className="tableau-loading" role="status">Loading interactive Tableau dashboard…</div>}
        <iframe title="CrewPulse Flight Operations Analytics Tableau dashboard" src={TABLEAU_URL} onLoad={() => setLoaded(true)} allowFullScreen />
      </div>
      <p className="embed-note">The Tableau toolbar is available inside the dashboard. Tableau tabs are hidden to keep the view focused. If the embed does not load, <a href="https://public.tableau.com/views/CrewPulseFlightOperationsAnalytics/Dashboard1" target="_blank" rel="noreferrer">open the workbook directly</a>.</p>
    </div>
  </section>
}

export function EngineeringPage() {
  const [selected, setSelected] = useState(components[0].id)
  const activeComponent = components.find((component) => component.id === selected)!
  return <section className="portfolio-page" id="engineering">
    <div className="page-heading"><div><div className="eyebrow">ENGINEERING PORTFOLIO</div><h1>How CrewPulse was built</h1><p className="subtitle">A walkthrough of the implemented data platform and production application.</p></div></div>

    <section className="portfolio-panel architecture-panel" aria-labelledby="architecture-title">
      <div className="portfolio-panel-heading"><div><h2 id="architecture-title">Interactive system architecture</h2><p>Select a component to see its role and connections.</p></div><a className="external-link github-link" href="https://github.com/tcodes27/crewPulseProject" target="_blank" rel="noreferrer"><svg viewBox="0 0 24 24" aria-hidden="true"><path fill="currentColor" d="M12 .9a11.1 11.1 0 0 0-3.51 21.63c.55.1.76-.24.76-.53v-2.07c-3.1.67-3.75-1.32-3.75-1.32-.5-1.28-1.24-1.62-1.24-1.62-1.01-.69.08-.68.08-.68 1.12.08 1.71 1.15 1.71 1.15 1 .1.76 2.3 3.64 1.63.1-.72.39-1.21.7-1.49-2.48-.28-5.09-1.24-5.09-5.53 0-1.22.44-2.22 1.15-3-.12-.28-.5-1.42.11-2.96 0 0 .94-.3 3.06 1.15a10.65 10.65 0 0 1 5.57 0c2.12-1.44 3.05-1.15 3.05-1.15.61 1.54.23 2.68.12 2.96.71.78 1.14 1.78 1.14 3.01 0 4.3-2.61 5.24-5.1 5.52.4.35.75 1.03.75 2.08V22c0 .29.2.63.76.52A11.1 11.1 0 0 0 12 .9Z"/></svg>View on GitHub <span aria-hidden="true">↗</span></a></div>
      <div className="architecture-lanes">
        <div className="architecture-lane"><span className="lane-label">DATA ENGINEERING</span><div className="architecture-nodes"><button className={`architecture-node ${selected === 'pipeline' ? 'selected' : ''}`} onClick={() => setSelected('pipeline')}>Python data pipeline</button><span className="flow-arrow" aria-label="writes to">→</span><button className={`architecture-node ${selected === 'database' ? 'selected' : ''}`} onClick={() => setSelected('database')}>PostgreSQL / Neon</button></div><p className="lane-caption">Pipeline writes and persists run and quality history</p></div>
        <div className="architecture-lane"><span className="lane-label">LIVE APPLICATION REQUEST PATH</span><div className="architecture-nodes"><button className={`architecture-node ${selected === 'cloudflare' ? 'selected' : ''}`} onClick={() => setSelected('cloudflare')}>Cloudflare Workers</button><span className="flow-arrow" aria-label="serves">→</span><button className={`architecture-node ${selected === 'frontend' ? 'selected' : ''}`} onClick={() => setSelected('frontend')}>React / TypeScript / Vite</button><span className="flow-arrow" aria-label="requests JSON from">→</span><button className={`architecture-node ${selected === 'api' ? 'selected' : ''}`} onClick={() => setSelected('api')}>FastAPI / Render</button><span className="flow-arrow" aria-label="reads from">→</span><button className={`architecture-node ${selected === 'database' ? 'selected' : ''}`} onClick={() => setSelected('database')}>PostgreSQL / Neon</button></div><p className="lane-caption">Cloudflare serves the UI; the browser calls Render, which reads the database</p></div>
        <div className="architecture-lane"><span className="lane-label">SOURCE CONTROL AND ANALYTICS EXPORT</span><div className="architecture-nodes"><button className={`architecture-node ${selected === 'github' ? 'selected' : ''}`} onClick={() => setSelected('github')}>GitHub</button><span className="lane-caption inline-caption">Source control and CI tests</span><span className="architecture-divider" aria-hidden="true" /><button className={`architecture-node ${selected === 'database' ? 'selected' : ''}`} onClick={() => setSelected('database')}>PostgreSQL analytics</button><span className="flow-arrow" aria-label="exports datasets to">→</span><button className={`architecture-node ${selected === 'tableau' ? 'selected' : ''}`} onClick={() => setSelected('tableau')}>Tableau Public</button></div><p className="lane-caption">CSV analytical exports feed the Tableau workbook; this path is separate from live API requests.</p></div>
      </div>
      <div className="architecture-detail" aria-live="polite"><strong>{activeComponent.title}</strong><span>{activeComponent.detail}</span><small>{activeComponent.lane === 'engineering' ? 'DATA ENGINEERING PIPELINE' : activeComponent.lane === 'live' ? 'LIVE APPLICATION PATH' : activeComponent.lane.toUpperCase()}</small></div>
    </section>

    <section className="portfolio-panel metrics-panel"><div className="portfolio-panel-heading"><div><h2>Verified project checkpoint</h2><p>Synthetic portfolio data · checkpoint counts from the project snapshot</p></div><span className="synthetic-tag">SYNTHETIC DATA</span></div><div className="portfolio-metrics">{metrics.map(([value, label]) => <article key={label}><strong>{value}</strong><span>{label}</span></article>)}</div></section>

    <section className="portfolio-panel walkthrough-panel"><div className="portfolio-panel-heading"><div><h2>Engineering walkthrough</h2><p>How source data becomes validated operational analytics and a deployed application.</p></div></div><ol className="stage-list">{stages.map((stage, index) => <li key={stage.title}><span className="stage-number">{String(index + 1).padStart(2, '0')}</span><div><h3>{stage.title}</h3><span className="stage-tech">{stage.tech}</span><p>{stage.body}</p></div></li>)}</ol></section>

    <section className="portfolio-panel lessons-panel"><div className="portfolio-panel-heading"><div><h2>Engineering lessons</h2><p>Production issues, the changes that resolved them, and the operational takeaway.</p></div></div><div className="lesson-list">{lessons.map(([title, problem, lesson]) => <details key={title}><summary>{title}</summary><div className="lesson-content"><p><b>Problem and fix</b>{problem}</p><p><b>What we learned</b>{lesson}</p></div></details>)}</div></section>
  </section>
}
