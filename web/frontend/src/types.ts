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
  cache_key: string
  width: number | null
  height: number | null
  duration: number | null
  vres_x: number | null
  vres_y: number | null
  fps: number | null
  video_codec: string | null
  video_bitrate: number | null
  container_type: string | null
  audio_codec: string | null
  audio_channel: number | null
  audio_frequency: number | null
  audio_bitrate: number | null
  country: string | null
  first_level: string | null
  district: string | null
  folder_path: string | null
  camera: string | null
  lens: string | null
  focal_length: string | null
  aperture: string | null
  iso: string | null
  exposure_time: string | null
  flash: number | null
  orientation: number | null
  description: string | null
  latitude: number | null
  longitude: number | null
}

export interface CollectResult {
  items: MediaItem[]
  count: number
  total_mb: number
}

export interface CollectRequest {
  person_ids: number[]
  person_count: string | null   // null | 'none' | '1' | '2+'
  country: string | null
  first_level: string | null
  district: string | null
  from_date: string | null
  to_date: string | null
  item_types: number[]
  concepts: string[]
  min_confidence: number
  cameras: string[]
  min_duration: number | null
  min_width: number | null
  max_duration: number | null
  min_fps: number | null
  video_codecs: string[]
  has_audio: boolean | null
  has_gps: boolean | null
  limit: number | null
  sort_desc: boolean
}
