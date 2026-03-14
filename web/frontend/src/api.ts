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

export async function runCollect(req: CollectRequest, signal?: AbortSignal): Promise<CollectResult> {
  const res = await fetch(`${BASE}/collect`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(req),
    signal,
  })
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}

export function mediaUrl(id: number, asVideo = false) {
  return asVideo ? `${BASE}/media/${id}?as_video=true` : `${BASE}/media/${id}`
}

export function thumbnailUrl(id: number, cacheKey: string, size: 'sm' | 'md' | 'lg' = 'sm') {
  return `${BASE}/thumbnail/${id}/${cacheKey}?size=${size}`
}

export function fetchItemMeta(id: number): Promise<{ persons: string[]; concepts: { stem: string; confidence: number }[] }> {
  return apiFetch(`${BASE}/meta/${id}`)
}

export async function downloadItems(itemIds: number[]): Promise<void> {
  const res = await fetch(`${BASE}/download`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ item_ids: itemIds }),
  })
  if (!res.ok) throw new Error(await res.text())

  const filename = `photos_${itemIds.length}.zip`

  // Stream directly to disk via the File System Access API — no in-memory blob
  if ('showSaveFilePicker' in window && res.body) {
    try {
      const handle = await (window as any).showSaveFilePicker({
        suggestedName: filename,
        types: [{ description: 'ZIP archive', accept: { 'application/zip': ['.zip'] } }],
      })
      await res.body.pipeTo(await handle.createWritable())
      return
    } catch (e) {
      if ((e as Error).name === 'AbortError') throw e  // user cancelled picker
      // API unavailable — fall through to blob
    }
  }

  // Fallback: buffer as blob (works everywhere)
  const blob = await res.blob()
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  a.click()
  URL.revokeObjectURL(url)
}
