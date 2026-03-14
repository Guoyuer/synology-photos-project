import { useEffect, useState } from 'react'
import { fetchCameras, fetchConcepts, fetchLocations, fetchPersons, runCollect } from './api'
import { FilterPanel } from './components/FilterPanel'
import { ResultsGrid } from './components/ResultsGrid'
import type { Camera, CollectRequest, CollectResult, Concept, Location, Person } from './types'

export default function App() {
  const [persons, setPersons] = useState<Person[]>([])
  const [locations, setLocations] = useState<Location[]>([])
  const [concepts, setConcepts] = useState<Concept[]>([])
  const [cameras, setCameras] = useState<Camera[]>([])
  const [result, setResult] = useState<CollectResult | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    Promise.all([fetchPersons(), fetchLocations(), fetchConcepts(), fetchCameras()])
      .then(([p, l, c, cam]) => {
        setPersons(p)
        setLocations(l)
        setConcepts(c)
        setCameras(cam)
      })
      .catch(e => setError(String(e)))
  }, [])

  const handleSearch = async (req: CollectRequest) => {
    setLoading(true)
    setError(null)
    try {
      const res = await runCollect(req)
      setResult(res)
    } catch (e) {
      setError(String(e))
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="flex h-screen bg-gray-950 text-gray-100 overflow-hidden">
      <FilterPanel
        persons={persons}
        locations={locations}
        concepts={concepts}
        cameras={cameras}
        onSearch={handleSearch}
        loading={loading}
      />
      <div className="flex-1 flex flex-col min-w-0">
        {error && (
          <div className="p-4 bg-red-900/50 text-red-300 text-sm border-b border-red-700">{error}</div>
        )}
        {loading && (
          <div className="flex-1 flex items-center justify-center text-gray-500 text-lg">Searching…</div>
        )}
        {!loading && result && (
          <ResultsGrid items={result.items} totalMb={result.total_mb} />
        )}
        {!loading && !result && !error && (
          <div className="flex-1 flex flex-col items-center justify-center text-gray-600 gap-3">
            <span className="text-5xl">🎬</span>
            <span className="text-lg">Set filters and search to find your vlog material</span>
          </div>
        )}
      </div>
    </div>
  )
}
