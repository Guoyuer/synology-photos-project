import { useEffect, useState } from 'react'
import { askQuestion, fetchCameras, fetchConcepts, fetchLocations, fetchPersons, runCollect, runSql } from './api'
import { FilterPanel } from './components/FilterPanel'
import { ResultsGrid } from './components/ResultsGrid'
import { SqlPanel } from './components/SqlPanel'
import { SqlResultsTable } from './components/SqlResultsTable'
import type { Camera, CollectRequest, CollectResult, Concept, Location, Person, SqlResult } from './types'

type Mode = 'filters' | 'sql'

export default function App() {
  const [mode, setMode] = useState<Mode>('filters')

  const [persons, setPersons] = useState<Person[]>([])
  const [locations, setLocations] = useState<Location[]>([])
  const [concepts, setConcepts] = useState<Concept[]>([])
  const [cameras, setCameras] = useState<Camera[]>([])

  const [filterResult, setFilterResult] = useState<CollectResult | null>(null)
  const [filterLoading, setFilterLoading] = useState(false)

  const [sqlResult, setSqlResult] = useState<SqlResult | null>(null)
  const [sqlLoading, setSqlLoading] = useState(false)

  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    Promise.all([fetchPersons(), fetchLocations(), fetchConcepts(), fetchCameras()])
      .then(([p, l, c, cam]) => { setPersons(p); setLocations(l); setConcepts(c); setCameras(cam) })
      .catch(e => setError(String(e)))
  }, [])

  const handleSearch = async (req: CollectRequest) => {
    setFilterLoading(true)
    setError(null)
    try { setFilterResult(await runCollect(req)) }
    catch (e) { setError(String(e)) }
    finally { setFilterLoading(false) }
  }

  const handleAsk = async (question: string) => {
    setSqlLoading(true)
    setError(null)
    try { setSqlResult(await askQuestion(question)) }
    catch (e) { setError(String(e)) }
    finally { setSqlLoading(false) }
  }

  const handleSql = async (sql: string) => {
    setSqlLoading(true)
    setError(null)
    try { setSqlResult(await runSql(sql)) }
    catch (e) { setError(String(e)) }
    finally { setSqlLoading(false) }
  }

  const tab = (active: boolean) =>
    `px-3 py-1 rounded text-sm font-medium transition-colors ${active ? 'bg-blue-600 text-white' : 'text-gray-400 hover:text-gray-200'}`

  return (
    <div className="flex flex-col h-screen bg-gray-950 text-gray-100 overflow-hidden">
      {/* Top bar */}
      <div className="flex items-center gap-3 px-4 py-2 bg-gray-900 border-b border-gray-700 shrink-0">
        <span className="text-sm font-bold text-white mr-2">📸 Photo Collect</span>
        <button onClick={() => setMode('filters')} className={tab(mode === 'filters')}>Filters</button>
        <button onClick={() => setMode('sql')} className={tab(mode === 'sql')}>Ask AI</button>
      </div>

      <div className="flex flex-1 min-h-0">
        {/* Left panel */}
        {mode === 'filters'
          ? <FilterPanel persons={persons} locations={locations} concepts={concepts} cameras={cameras}
              onSearch={handleSearch} loading={filterLoading} />
          : <SqlPanel onAsk={handleAsk} onSql={handleSql} loading={sqlLoading}
              generatedSql={sqlResult?.sql ?? null} />
        }

        {/* Right panel */}
        <div className="flex-1 flex flex-col min-w-0">
          {error && (
            <div className="p-4 bg-red-900/50 text-red-300 text-sm border-b border-red-700">{error}</div>
          )}
          {mode === 'filters' ? (
            filterLoading
              ? <div className="flex-1 flex items-center justify-center text-gray-500 text-lg">Searching…</div>
              : filterResult
                ? <ResultsGrid items={filterResult.items} totalMb={filterResult.total_mb} />
                : <div className="flex-1 flex flex-col items-center justify-center text-gray-600 gap-3">
                    <span className="text-5xl">🎬</span>
                    <span className="text-lg">Set filters and search to find your vlog material</span>
                  </div>
          ) : (
            sqlLoading
              ? <div className="flex-1 flex items-center justify-center text-gray-500 text-lg">Thinking…</div>
              : <SqlResultsTable result={sqlResult} />
          )}
        </div>
      </div>
    </div>
  )
}
