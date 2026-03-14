export interface Person {
  id: number
  name: string
  item_count: number
}

export interface Location {
  country: string
  first_level: string
  second_level: string
  item_count: number
}

export interface Concept {
  id: number
  stem: string
  usage_count: number
}

export interface Camera {
  camera: string
  item_count: number
}

export interface MediaItem {
  id: number
  filename: string
  takentime: number
  taken_iso: string
  item_type: number
  type_name: string
  filesize: number
  width: number | null
  height: number | null
  duration: number | null
  vres_x: number | null
  fps: number | null
  country: string | null
  district: string | null
  camera: string | null
  latitude: number | null
  longitude: number | null
}

export interface CollectResult {
  items: MediaItem[]
  count: number
  total_mb: number
}

export interface SqlResult {
  columns: string[]
  rows: (string | number | boolean | null)[][]
  count: number
}

export interface CollectRequest {
  person_ids: number[]
  all_persons: boolean
  country: string | null
  district: string | null
  from_date: string | null
  to_date: string | null
  item_types: number[]
  concepts: string[]
  min_confidence: number
  cameras: string[]
  min_duration: number | null
  min_width: number | null
  limit: number | null
}
