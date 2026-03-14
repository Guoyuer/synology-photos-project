import type { Camera, CollectRequest, CollectResult, Concept, Location, Person } from './types'

const BASE = '/api'

export async function fetchPersons(): Promise<Person[]> {
  const res = await fetch(`${BASE}/persons`)
  return res.json()
}

export async function fetchLocations(): Promise<Location[]> {
  const res = await fetch(`${BASE}/locations`)
  return res.json()
}

export async function fetchConcepts(): Promise<Concept[]> {
  const res = await fetch(`${BASE}/concepts`)
  return res.json()
}

export async function fetchCameras(): Promise<Camera[]> {
  const res = await fetch(`${BASE}/cameras`)
  return res.json()
}

export async function runCollect(req: CollectRequest): Promise<CollectResult> {
  const res = await fetch(`${BASE}/collect`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(req),
  })
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}

export function thumbnailUrl(id: number, size: 'sm' | 'md' | 'lg' = 'sm') {
  return `${BASE}/thumbnail/${id}?size=${size}`
}

export async function downloadItems(itemIds: number[]): Promise<void> {
  const res = await fetch(`${BASE}/download`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ item_ids: itemIds }),
  })
  if (!res.ok) throw new Error(await res.text())
  const blob = await res.blob()
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `photos_${itemIds.length}.zip`
  a.click()
  URL.revokeObjectURL(url)
}
