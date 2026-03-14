import type { Camera, CollectRequest, CollectResult, Concept, Location, Person } from './types'

const BASE = '/api'

async function apiFetch<T>(url: string): Promise<T> {
  const res = await fetch(url)
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}

export function fetchPersons(): Promise<Person[]> {
  return apiFetch(`${BASE}/persons`)
}

export function fetchLocations(): Promise<Location[]> {
  return apiFetch(`${BASE}/locations`)
}

export function fetchConcepts(): Promise<Concept[]> {
  return apiFetch(`${BASE}/concepts`)
}

export function fetchCameras(): Promise<Camera[]> {
  return apiFetch(`${BASE}/cameras`)
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

export function mediaUrl(id: number, asVideo = false) {
  return asVideo ? `${BASE}/media/${id}?as_video=true` : `${BASE}/media/${id}`
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
