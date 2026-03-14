import { useState, useCallback, useEffect } from 'react'

export interface FilterState {
  personIds: number[]
  allPersons: boolean
  country: string
  firstLevel: string
  district: string
  fromDate: string
  toDate: string
  itemTypes: number[]
  selectedConcepts: string[]
  minConfidence: number
  selectedCameras: string[]
  minDuration: string
  minWidth: string
  maxDuration: string
  minFps: string
  videoCodecs: string[]
  hasAudio: string
  hasGps: string
  limit: string
  sortDesc: boolean
}

export const DEFAULT_FILTERS: FilterState = {
  personIds: [],
  allPersons: false,
  country: '',
  firstLevel: '',
  district: '',
  fromDate: '',
  toDate: '',
  itemTypes: [],
  selectedConcepts: [],
  minConfidence: 0.7,
  selectedCameras: [],
  minDuration: '',
  minWidth: '',
  maxDuration: '',
  minFps: '',
  videoCodecs: [],
  hasAudio: '',
  hasGps: '',
  limit: '',
  sortDesc: false,
}

function fromParams(p: URLSearchParams): FilterState {
  const conf = parseFloat(p.get('conf') ?? '')
  return {
    personIds: p.getAll('persons').map(Number).filter(n => !isNaN(n)),
    allPersons: p.get('allPersons') === '1',
    country: p.get('country') ?? '',
    firstLevel: p.get('city') ?? '',
    district: p.get('district') ?? '',
    fromDate: p.get('from') ?? '',
    toDate: p.get('to') ?? '',
    itemTypes: p.getAll('types').map(Number).filter(n => !isNaN(n)),
    selectedConcepts: p.getAll('concepts'),
    minConfidence: isNaN(conf) ? 0.7 : conf,
    selectedCameras: p.getAll('cameras'),
    minDuration: p.get('dur') ?? '',
    minWidth: p.get('width') ?? '',
    maxDuration: p.get('maxdur') ?? '',
    minFps: p.get('fps') ?? '',
    videoCodecs: p.getAll('codec'),
    hasAudio: p.get('audio') ?? '',
    hasGps: p.get('gps') ?? '',
    limit: p.get('limit') ?? '',
    sortDesc: p.get('sort') === 'desc',
  }
}

export function toSearch(f: FilterState): string {
  const p = new URLSearchParams()
  f.personIds.forEach(id => p.append('persons', String(id)))
  if (f.allPersons) p.set('allPersons', '1')
  if (f.country) p.set('country', f.country)
  if (f.firstLevel) p.set('city', f.firstLevel)
  if (f.district) p.set('district', f.district)
  if (f.fromDate) p.set('from', f.fromDate)
  if (f.toDate) p.set('to', f.toDate)
  f.itemTypes.forEach(t => p.append('types', String(t)))
  f.selectedConcepts.forEach(c => p.append('concepts', c))
  if (f.minConfidence !== 0.7) p.set('conf', f.minConfidence.toFixed(2))
  f.selectedCameras.forEach(c => p.append('cameras', c))
  if (f.minDuration) p.set('dur', f.minDuration)
  if (f.minWidth) p.set('width', f.minWidth)
  if (f.maxDuration) p.set('maxdur', f.maxDuration)
  if (f.minFps) p.set('fps', f.minFps)
  f.videoCodecs.forEach(c => p.append('codec', c))
  if (f.hasAudio) p.set('audio', f.hasAudio)
  if (f.hasGps) p.set('gps', f.hasGps)
  if (f.limit) p.set('limit', f.limit)
  if (f.sortDesc) p.set('sort', 'desc')
  const qs = p.toString()
  return qs ? `?${qs}` : ''
}

export function useUrlFilters() {
  const [filters, setFiltersRaw] = useState<FilterState>(() =>
    fromParams(new URLSearchParams(window.location.search))
  )

  const setFilters = useCallback((next: FilterState) => {
    setFiltersRaw(next)
    history.replaceState(null, '', window.location.pathname + toSearch(next))
  }, [])

  // Sync back when user navigates with browser back/forward
  useEffect(() => {
    const onPop = () => setFiltersRaw(fromParams(new URLSearchParams(window.location.search)))
    window.addEventListener('popstate', onPop)
    return () => window.removeEventListener('popstate', onPop)
  }, [])

  return { filters, setFilters }
}
