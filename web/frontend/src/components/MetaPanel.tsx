import { useEffect, useState } from 'react'
import { fetchItemMeta } from '../api'
import type { MediaItem } from '../types'
import { fmt, fmtDur, fmtFps } from '../utils'

interface Props {
  item: MediaItem
  onClose: () => void
}

function Row({ label, value }: { label: string; value: React.ReactNode }) {
  if (value == null || value === '' || value === false) return null
  return (
    <div className="flex gap-2 py-1.5 border-b border-gray-800 last:border-0">
      <span className="text-xs text-gray-500 w-28 shrink-0">{label}</span>
      <span className="text-xs text-gray-200 break-all">{value}</span>
    </div>
  )
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="mb-4">
      <p className="text-xs font-semibold text-gray-400 uppercase tracking-wide mb-1">{title}</p>
      {children}
    </div>
  )
}

const ORIENTATION_LABELS: Record<number, string> = {
  1: 'Normal',
  3: '180°',
  6: '90° CW',
  8: '90° CCW',
}

export function MetaPanel({ item, onClose }: Props) {
  const [meta, setMeta] = useState<{ persons: string[]; concepts: { stem: string; confidence: number }[] } | null>(null)

  useEffect(() => {
    setMeta(null)
    fetchItemMeta(item.id).then(setMeta).catch(() => {})
  }, [item.id])

  const fps = fmtFps(item.fps)
  const audioChannel = item.audio_channel != null
    ? ['—', 'Mono', 'Stereo'][item.audio_channel] ?? `${item.audio_channel}ch`
    : null

  const videoRes = item.vres_x && item.vres_y ? `${item.vres_x}×${item.vres_y}` : item.vres_x ? `${item.vres_x}p` : null
  const orientation = item.orientation != null && item.orientation !== 1
    ? ORIENTATION_LABELS[item.orientation] ?? `${item.orientation}`
    : null

  return (
    <div
      className="fixed right-0 top-0 bottom-0 w-80 bg-gray-900 border-l border-gray-700 z-[100001] flex flex-col shadow-2xl"
      onClick={e => e.stopPropagation()}
    >
      <div className="flex items-center justify-between px-4 py-3 border-b border-gray-700 shrink-0">
        <span className="text-sm font-semibold text-gray-200">Info</span>
        <button onClick={onClose} className="text-gray-400 hover:text-white text-xl leading-none">×</button>
      </div>

      <div className="flex-1 overflow-y-auto px-4 py-3">

        <Section title="File">
          <Row label="Filename"    value={item.filename} />
          <Row label="Type"        value={item.type_name} />
          <Row label="ID"          value={item.id} />
          <Row label="Date"        value={item.taken_iso?.slice(0, 19).replace('T', ' ')} />
          <Row label="Size"        value={fmt(item.filesize)} />
          <Row label="Folder"      value={item.folder_path} />
          <Row label="Description" value={item.description} />
        </Section>

        <Section title="Photo">
          <Row label="Dimensions"   value={item.width && item.height ? `${item.width} × ${item.height}` : null} />
          <Row label="Orientation"  value={orientation} />
          <Row label="Camera"       value={item.camera} />
          <Row label="Lens"         value={item.lens} />
          <Row label="Focal length" value={item.focal_length} />
          <Row label="Aperture"     value={item.aperture} />
          <Row label="ISO"          value={item.iso} />
          <Row label="Exposure"     value={item.exposure_time} />
          <Row label="Flash"        value={item.flash != null ? (item.flash ? 'On' : 'Off') : null} />
        </Section>

        <Section title="Video">
          <Row label="Duration"      value={item.duration ? fmtDur(item.duration) : null} />
          <Row label="Resolution"    value={videoRes} />
          <Row label="FPS"           value={fps} />
          <Row label="Video codec"   value={item.video_codec} />
          <Row label="Container"     value={item.container_type} />
          <Row label="Video bitrate" value={item.video_bitrate ? `${(item.video_bitrate / 1_000_000).toFixed(1)} Mbps` : null} />
          <Row label="Audio codec"   value={item.audio_codec} />
          <Row label="Audio"         value={audioChannel} />
          <Row label="Audio bitrate" value={item.audio_bitrate ? `${Math.round(item.audio_bitrate / 1000)} kbps` : null} />
          <Row label="Sample rate"   value={item.audio_frequency ? `${item.audio_frequency / 1000} kHz` : null} />
        </Section>

        <Section title="Location">
          <Row label="Country"   value={item.country} />
          <Row label="Region"    value={item.first_level} />
          <Row label="District"  value={item.district} />
          <Row label="Latitude"  value={item.latitude != null ? item.latitude.toFixed(6) : null} />
          <Row label="Longitude" value={item.longitude != null ? item.longitude.toFixed(6) : null} />
          {item.latitude != null && item.longitude != null && (
            <div className="pt-1.5">
              <a
                href={`https://maps.google.com/?q=${item.latitude},${item.longitude}`}
                target="_blank"
                rel="noopener noreferrer"
                className="text-xs text-blue-400 hover:text-blue-300"
              >
                Open in Google Maps ↗
              </a>
            </div>
          )}
        </Section>

        {meta && (meta.persons.length > 0 || meta.concepts.length > 0) && (
          <Section title="AI Tags">
            {meta.persons.length > 0 && (
              <Row label="Persons" value={meta.persons.join(', ')} />
            )}
            {meta.concepts.length > 0 && (
              <div className="py-1.5">
                <span className="text-xs text-gray-500 block mb-1.5">Concepts</span>
                <div className="flex flex-wrap gap-1">
                  {meta.concepts.map(c => (
                    <span key={c.stem} className="text-xs bg-gray-800 text-gray-300 px-1.5 py-0.5 rounded" title={`${Math.round(c.confidence * 100)}%`}>
                      {c.stem}
                    </span>
                  ))}
                </div>
              </div>
            )}
          </Section>
        )}

      </div>
    </div>
  )
}
