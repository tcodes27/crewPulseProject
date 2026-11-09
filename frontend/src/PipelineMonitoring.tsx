import { useCallback, useEffect, useState } from 'react'
import { API_BASE_URL } from './api'
import { getSafePipelineFailureMessage, UNKNOWN_PIPELINE_FAILURE } from './pipelineErrors.mjs'

type PipelineSummary = {
  total_runs: number
  successful_runs: number
  failed_runs: number
  other_runs: number
  total_data_quality_checks: number
  pass_checks: number
  warning_checks: number
  fail_checks: number
  latest_execution_at: string | null
}

type PipelineRun = {
  run_id: number
  pipeline_name: string
  status: string
  started_at: string
  finished_at: string | null
  records_read: number
  records_inserted: number
  records_rejected: number
  error_message: string | null
}

type QualityResult = {
  result_id: number
  run_id: number
  table_name: string
  check_name: string
  failed_records: number
  status: 'PASS' | 'WARNING' | 'FAIL' | string
  details: string | null
  checked_at: string
}

const formatTimestamp = (value: string | null | undefined) => {
  if (!value) return '—'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return '—'
  return new Intl.DateTimeFormat('en-US', {
    dateStyle: 'medium', timeStyle: 'short', timeZoneName: 'short',
  }).format(date)
}

const formatDuration = (start: string, finish: string | null) => {
  if (!finish) return 'In progress'
  const startTime = new Date(start).getTime()
  const finishTime = new Date(finish).getTime()
  if (!Number.isFinite(startTime) || !Number.isFinite(finishTime) || finishTime < startTime) return '—'
  const seconds = Math.floor((finishTime - startTime) / 1000)
  if (seconds < 60) return `${seconds}s`
  const minutes = Math.floor(seconds / 60)
  return `${minutes}m ${seconds % 60}s`
}

const statusTone = (status: string) => {
  const normalized = status.toLowerCase()
  return normalized === 'success' || normalized === 'pass'
    ? 'success'
    : normalized === 'failed' || normalized === 'fail'
      ? 'failure'
      : normalized === 'warning'
        ? 'warning'
        : 'neutral'
}

async function requestJson<T>(path: string, signal?: AbortSignal): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, { signal })
  if (!response.ok) throw new Error('Pipeline monitoring request failed.')
  return response.json() as Promise<T>
}

function MetricCard({ label, value, tone = '' }: { label: string; value: string | number; tone?: string }) {
  return <article className="monitor-metric-card">
    <div className="monitor-metric-label">{label}</div>
    <strong className={tone ? `monitor-metric-value ${tone}` : 'monitor-metric-value'}>{value}</strong>
  </article>
}

function QualityTable({ results, compact = false }: { results: QualityResult[]; compact?: boolean }) {
  if (results.length === 0) {
    return <div className="monitor-empty">No data-quality results were recorded{compact ? ' for this run' : ''}.</div>
  }
  return <div className="monitor-table-wrap"><table className="monitor-table">
    <thead><tr>
      {!compact && <th>RUN</th>}
      <th>CHECK</th><th>TABLE</th><th>RESULT</th><th>FAILED RECORDS</th><th>CHECKED</th>
    </tr></thead>
    <tbody>{results.map((result) => <tr key={result.result_id}>
      {!compact && <td>#{result.run_id}</td>}
      <td><strong>{result.check_name}</strong>{result.details && <small className="monitor-cell-detail">{result.details}</small>}</td>
      <td><code>{result.table_name}</code></td>
      <td><span className={`monitor-status ${statusTone(result.status)}`}>{result.status}</span></td>
      <td>{result.failed_records.toLocaleString()}</td>
      <td>{formatTimestamp(result.checked_at)}</td>
    </tr>)}</tbody>
  </table></div>
}

export function PipelineMonitoringPage() {
  const [summary, setSummary] = useState<PipelineSummary | null>(null)
  const [runs, setRuns] = useState<PipelineRun[]>([])
  const [qualityResults, setQualityResults] = useState<QualityResult[]>([])
  const [summaryLoading, setSummaryLoading] = useState(true)
  const [runsLoading, setRunsLoading] = useState(true)
  const [qualityLoading, setQualityLoading] = useState(true)
  const [summaryError, setSummaryError] = useState('')
  const [runsError, setRunsError] = useState('')
  const [qualityError, setQualityError] = useState('')
  const [selectedRunId, setSelectedRunId] = useState<number | null>(null)
  const [selectedResults, setSelectedResults] = useState<QualityResult[]>([])
  const [selectedLoading, setSelectedLoading] = useState(false)
  const [selectedError, setSelectedError] = useState('')
  const [selectedRefresh, setSelectedRefresh] = useState(0)
  const selectedRun = runs.find((run) => run.run_id === selectedRunId) ?? null
  const safeFailureMessage = selectedRun?.status.toUpperCase() === 'FAILED'
    ? getSafePipelineFailureMessage(selectedRun.error_message)
    : null

  const loadSummary = useCallback(async (signal?: AbortSignal) => {
    setSummaryLoading(true)
    setSummaryError('')
    try {
      setSummary(await requestJson<PipelineSummary>('/api/pipeline/summary', signal))
    } catch {
      if (!signal?.aborted) setSummaryError('Pipeline summary could not be loaded. Try refreshing.')
    } finally {
      if (!signal?.aborted) setSummaryLoading(false)
    }
  }, [])

  const loadRuns = useCallback(async (signal?: AbortSignal) => {
    setRunsLoading(true)
    setRunsError('')
    try {
      const payload = await requestJson<{ runs: PipelineRun[] }>('/api/pipeline/runs?limit=100', signal)
      setRuns(payload.runs)
    } catch {
      if (!signal?.aborted) setRunsError('Execution history could not be loaded. Try refreshing.')
    } finally {
      if (!signal?.aborted) setRunsLoading(false)
    }
  }, [])

  const loadQuality = useCallback(async (signal?: AbortSignal) => {
    setQualityLoading(true)
    setQualityError('')
    try {
      const payload = await requestJson<{ results: QualityResult[] }>('/api/pipeline/data-quality?limit=100', signal)
      setQualityResults(payload.results)
    } catch {
      if (!signal?.aborted) setQualityError('Data-quality history could not be loaded. Try refreshing.')
    } finally {
      if (!signal?.aborted) setQualityLoading(false)
    }
  }, [])

  const refreshAll = () => {
    void loadSummary()
    void loadRuns()
    void loadQuality()
    if (selectedRunId !== null) setSelectedRefresh((refresh) => refresh + 1)
  }

  useEffect(() => {
    const controller = new AbortController()
    void loadSummary(controller.signal)
    void loadRuns(controller.signal)
    void loadQuality(controller.signal)
    return () => controller.abort()
  }, [loadQuality, loadRuns, loadSummary])

  useEffect(() => {
    if (selectedRunId === null) {
      setSelectedResults([])
      setSelectedError('')
      setSelectedLoading(false)
      return
    }
    const controller = new AbortController()
    const loadSelected = async () => {
      setSelectedLoading(true)
      setSelectedError('')
      try {
        const query = new URLSearchParams({ run_id: String(selectedRunId), limit: '100' })
        const payload = await requestJson<{ results: QualityResult[] }>(`/api/pipeline/data-quality?${query}`, controller.signal)
        setSelectedResults(payload.results)
      } catch {
        if (!controller.signal.aborted) setSelectedError('Checks for this execution could not be loaded. Try refreshing.')
      } finally {
        if (!controller.signal.aborted) setSelectedLoading(false)
      }
    }
    void loadSelected()
    return () => controller.abort()
  }, [selectedRunId, selectedRefresh])

  const summaryCards = summary ? [
    { label: 'Total executions', value: summary.total_runs },
    { label: 'Successful', value: summary.successful_runs, tone: 'success' },
    { label: 'Failed', value: summary.failed_runs, tone: 'failure' },
    { label: 'Other statuses', value: summary.other_runs, tone: 'neutral' },
    { label: 'Data-quality checks', value: summary.total_data_quality_checks },
    { label: 'PASS checks', value: summary.pass_checks, tone: 'success' },
    { label: 'WARNING checks', value: summary.warning_checks, tone: 'warning' },
    { label: 'FAIL checks', value: summary.fail_checks, tone: 'failure' },
  ] : []

  return <section className="portfolio-page pipeline-page" id="pipeline">
    <div className="page-heading">
      <div><div className="eyebrow">DATA OPERATIONS</div><h1>Pipeline monitoring</h1><p className="subtitle">Execution history and data-quality results from the CrewPulse pipeline.</p></div>
      <button className="refresh-button" onClick={refreshAll} disabled={summaryLoading || runsLoading || qualityLoading || selectedLoading}>
        <span className={summaryLoading || runsLoading || qualityLoading || selectedLoading ? 'refresh-symbol spinning' : 'refresh-symbol'}>↻</span> Refresh monitoring
      </button>
    </div>

    <section className="portfolio-panel" aria-labelledby="pipeline-summary-title">
      <div className="portfolio-panel-heading"><div><h2 id="pipeline-summary-title">Pipeline summary</h2><p>Counts returned by the monitoring API.</p></div><div className="latest-execution"><span>Latest execution</span><strong>{summaryLoading ? 'Loading…' : summaryError ? 'Unavailable' : formatTimestamp(summary?.latest_execution_at)}</strong></div></div>
      {summaryError ? <div className="monitor-error" role="alert"><span>{summaryError}</span><button onClick={() => void loadSummary()}>Retry summary</button></div> : summaryLoading && !summary ? <div className="monitor-state" role="status">Loading pipeline summary…</div> : summary ? <div className="monitor-metric-grid">{summaryCards.map((card) => <MetricCard key={card.label} {...card} />)}</div> : <div className="monitor-empty">No summary data is available.</div>}
    </section>

    <section className="portfolio-panel" aria-labelledby="pipeline-runs-title">
      <div className="portfolio-panel-heading"><div><h2 id="pipeline-runs-title">Execution history</h2><p>Select an execution to inspect its recorded results.</p></div><span className="row-count">{runsLoading ? 'Loading' : `${runs.length} runs`}</span></div>
      {runsError ? <div className="monitor-error" role="alert"><span>{runsError}</span><button onClick={() => void loadRuns()}>Retry history</button></div> : runsLoading && runs.length === 0 ? <div className="monitor-state" role="status">Loading execution history…</div> : runs.length === 0 ? <div className="monitor-empty">No pipeline executions have been recorded.</div> : <div className="monitor-table-wrap"><table className="monitor-table runs-table">
        <thead><tr><th>RUN ID</th><th>PIPELINE</th><th>STATUS</th><th>STARTED</th><th>DURATION</th><th>READ</th><th>INSERTED</th><th>REJECTED</th></tr></thead>
        <tbody>{runs.map((run) => <tr key={run.run_id} className={selectedRunId === run.run_id ? 'selected-run' : ''}>
          <td><button className="run-select" aria-pressed={selectedRunId === run.run_id} onClick={() => setSelectedRunId(selectedRunId === run.run_id ? null : run.run_id)}>#{run.run_id}</button></td>
          <td><strong>{run.pipeline_name}</strong></td>
          <td><span className={`monitor-status ${statusTone(run.status)}`}>{run.status}</span></td>
          <td>{formatTimestamp(run.started_at)}</td><td>{formatDuration(run.started_at, run.finished_at)}</td>
          <td>{run.records_read.toLocaleString()}</td><td>{run.records_inserted.toLocaleString()}</td><td>{run.records_rejected.toLocaleString()}</td>
        </tr>)}</tbody>
      </table></div>}
    </section>

    {selectedRun && <section className="portfolio-panel run-detail-panel" aria-labelledby="run-details-title">
      <div className="portfolio-panel-heading"><div><h2 id="run-details-title">Run #{selectedRun.run_id} details</h2><p>{selectedRun.pipeline_name}</p></div><button className="detail-close" onClick={() => setSelectedRunId(null)}>Close details</button></div>
      <div className="run-detail-grid">
        <div><span>Status</span><strong><span className={`monitor-status ${statusTone(selectedRun.status)}`}>{selectedRun.status}</span></strong></div>
        <div><span>Started</span><strong>{formatTimestamp(selectedRun.started_at)}</strong></div>
        <div><span>Finished</span><strong>{formatTimestamp(selectedRun.finished_at)}</strong></div>
        <div><span>Duration</span><strong>{formatDuration(selectedRun.started_at, selectedRun.finished_at)}</strong></div>
        <div><span>Records read</span><strong>{selectedRun.records_read.toLocaleString()}</strong></div>
        <div><span>Records inserted</span><strong>{selectedRun.records_inserted.toLocaleString()}</strong></div>
        <div><span>Records rejected</span><strong>{selectedRun.records_rejected.toLocaleString()}</strong></div>
        {selectedRun.status.toUpperCase() === 'FAILED' && selectedRun.error_message?.trim() && <div className="run-failure-note"><strong>Failure details</strong><p>{safeFailureMessage ?? UNKNOWN_PIPELINE_FAILURE}</p></div>}
      </div>
      <div className="run-quality-heading"><div><h3>Checks for run #{selectedRun.run_id}</h3><p>Results are filtered by this run ID.</p></div></div>
      {selectedLoading ? <div className="monitor-state" role="status">Loading checks for this execution…</div> : selectedError ? <div className="monitor-error" role="alert"><span>{selectedError}</span><button onClick={() => setSelectedRefresh((refresh) => refresh + 1)}>Retry checks</button></div> : <QualityTable results={selectedResults} compact />}
    </section>}

    <section className="portfolio-panel" aria-labelledby="quality-history-title">
      <div className="portfolio-panel-heading"><div><h2 id="quality-history-title">Data-quality history</h2><p>Latest recorded checks across all pipeline runs.</p></div><span className="row-count">{qualityLoading ? 'Loading' : `${qualityResults.length} results`}</span></div>
      {qualityError ? <div className="monitor-error" role="alert"><span>{qualityError}</span><button onClick={() => void loadQuality()}>Retry quality history</button></div> : qualityLoading && qualityResults.length === 0 ? <div className="monitor-state" role="status">Loading data-quality history…</div> : <QualityTable results={qualityResults} />}
    </section>
  </section>
}
