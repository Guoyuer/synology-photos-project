import type { Camera, CollectRequest, CollectResult, Concept, Location, Person, SqlResult } from './types'

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

export async function fetchSchema(): Promise<string> {
  const res = await fetch(`${BASE}/schema`)
  const data = await res.json()
  return data.schema
}

export async function runSql(sql: string): Promise<SqlResult> {
  const res = await fetch(`${BASE}/sql`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ sql }),
  })
  if (!res.ok) {
    const data = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(data.detail ?? res.statusText)
  }
  return res.json()
}

export function thumbnailUrl(id: number, size: 'sm' | 'md' | 'lg' = 'sm') {
  return `${BASE}/thumbnail/${id}?size=${size}`
}
