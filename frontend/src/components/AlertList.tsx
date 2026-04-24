import { useState, useEffect } from 'react'
import { useAuth } from '../hooks/useAuth'

export type AlertItem = {
  id: string
  message: string
  type: 'info' | 'success' | 'warning' | 'danger'
  time: string
  zoneId?: number
}

type Violation = {
  id: number
  camera_id: number
  camera_name: string
  person_count: number
  helmet_count: number
  violation_count: number
  confidence: number
  snapshot_url: string | null
  created_at: string
}

type AlertListProps = {
  items?: AlertItem[]
  cameraId?: number
}

const typeStyles = {
  info: 'border-l-text-muted',
  success: 'border-l-success',
  warning: 'border-l-accent',
  danger: 'border-l-danger',
}

export default function AlertList({ items = [], cameraId }: AlertListProps) {
  const { user } = useAuth()
  const [violations, setViolations] = useState<Violation[]>([])
  const [loading, setLoading] = useState(false)
  const [selectedImage, setSelectedImage] = useState<string | null>(null)

  useEffect(() => {
    if (!cameraId || !user?.id) {
      setViolations([])
      return
    }
    setLoading(true)
    fetch(`/api/violations?user_id=${user.id}&camera_id=${cameraId}&limit=10&offset=0`)
      .then((r) => {
        if (!r.ok) throw new Error('Failed')
        return r.json()
      })
      .then((data) => setViolations(data.violations ?? []))
      .catch(() => setViolations([]))
      .finally(() => setLoading(false))
  }, [cameraId, user?.id])

  return (
    <div className="flex flex-col gap-3 overflow-y-auto pr-1">
      {/* System alerts (existing items) */}
      {items.length > 0 && (
        <div className="space-y-2">
          {items.map((a) => (
            <div
              key={a.id}
              className={`bg-card border border-border rounded-lg p-3 border-l-4 ${typeStyles[a.type]}`}
            >
              <p className="text-sm text-white">{a.message}</p>
              <p className="text-xs text-text-dim mt-1">{a.time}</p>
            </div>
          ))}
        </div>
      )}

      {/* Camera incidents (violations) */}
      {cameraId != null && (
        <div className="space-y-2">
          <h3 className="text-xs font-semibold text-accent uppercase tracking-wider">
            Recent incidents
          </h3>
          {loading ? (
            <p className="text-xs text-text-muted py-2">Loading incidents...</p>
          ) : violations.length === 0 ? (
            <p className="text-xs text-text-dim py-2">No incidents for this camera</p>
          ) : (
            violations.map((v) => (
              <div
                key={v.id}
                className="bg-card border border-border rounded-lg overflow-hidden hover:border-accent/30 transition-colors"
              >
                {v.snapshot_url ? (
                  <button
                    onClick={() => setSelectedImage(v.snapshot_url)}
                    className="w-full aspect-video bg-black block relative group"
                  >
                    <img
                      src={v.snapshot_url}
                      alt={`Incident ${v.id}`}
                      className="w-full h-full object-cover"
                      loading="lazy"
                    />
                    <span className="absolute bottom-1 right-1 px-1.5 py-0.5 text-[10px] font-semibold bg-black/70 text-danger rounded">
                      {v.violation_count} violation{v.violation_count !== 1 ? 's' : ''}
                    </span>
                  </button>
                ) : (
                  <div className="w-full aspect-video bg-black/50 flex items-center justify-center">
                    <span className="text-[10px] text-text-dim">No snapshot</span>
                  </div>
                )}
                <div className="p-2 space-y-0.5">
                  <div className="flex items-center justify-between gap-2 text-[11px]">
                    <span className="text-text-muted truncate">P:{v.person_count} H:{v.helmet_count}</span>
                    <span className="text-text-dim shrink-0">
                      {new Date(v.created_at).toLocaleString(undefined, { dateStyle: 'short', timeStyle: 'short' })}
                    </span>
                  </div>
                </div>
              </div>
            ))
          )}
        </div>
      )}

      {/* Image lightbox */}
      {selectedImage && (
        <div
          className="fixed inset-0 z-50 bg-black/80 flex items-center justify-center p-4"
          onClick={() => setSelectedImage(null)}
        >
          <div className="relative max-w-2xl w-full" onClick={(e) => e.stopPropagation()}>
            <button
              onClick={() => setSelectedImage(null)}
              className="absolute -top-10 right-0 text-white/70 hover:text-white text-sm"
            >
              Close
            </button>
            <img
              src={selectedImage}
              alt="Incident snapshot"
              className="w-full rounded-lg shadow-2xl"
            />
          </div>
        </div>
      )}
    </div>
  )
}
