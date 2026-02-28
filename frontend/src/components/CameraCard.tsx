import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'

type CameraCardProps = {
  cameraId: number
  zoneId: number
  streamUrl: string | null
  status: 'ok' | 'violation'
  statusText: string
  cameraName?: string
  fill?: boolean
}

export default function CameraCard({ cameraId, zoneId, streamUrl, status, statusText, cameraName, fill }: CameraCardProps) {
  const navigate = useNavigate()
  const [imageError, setImageError] = useState(false)

  useEffect(() => {
    setImageError(false)
  }, [streamUrl])

  const isLive = !!streamUrl && !imageError

  return (
    <div
      className={`group bg-card border border-border rounded-xl overflow-hidden cursor-pointer
                 hover:border-accent/40 hover:shadow-lg hover:shadow-accent/5 transition-all flex flex-col
                 ${fill ? 'h-full' : ''}`}
      onClick={() => navigate(`/camera/${cameraId}`)}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => e.key === 'Enter' && navigate(`/camera/${cameraId}`)}
    >
      {/* Header: camera name + live badge */}
      <div className="flex items-center justify-between px-3 sm:px-4 py-2 border-b border-border/50">
        <p className="text-sm font-medium text-white truncate">
          {cameraName ?? `Safe Zone ${zoneId}`}
        </p>
        {isLive && (
          <span className="flex items-center gap-1.5 text-[11px] font-semibold text-success uppercase tracking-wider shrink-0 ml-2">
            <span className="w-1.5 h-1.5 rounded-full bg-success animate-pulse" />
            Live
          </span>
        )}
      </div>

      {/* Video feed — 16:9 when in grid, stretch-to-fill when single camera */}
      <div className={`${fill ? 'flex-1 min-h-0' : 'aspect-video'} bg-black relative overflow-hidden`}>
        {streamUrl ? (
          <>
            {!imageError ? (
              <img
                src={streamUrl}
                alt={`Zone ${zoneId}`}
                className="absolute inset-0 w-full h-full object-cover"
                onError={() => setImageError(true)}
              />
            ) : (
              <div className="absolute inset-0 flex flex-col items-center justify-center gap-2 text-text-dim">
                <svg className="w-8 h-8 opacity-30" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
                    d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
                </svg>
                <span className="text-xs">Camera offline</span>
                <span className="text-[11px] text-text-dim/60">Check backend server</span>
              </div>
            )}
          </>
        ) : (
          <div className="absolute inset-0 flex flex-col items-center justify-center gap-1.5 text-text-dim">
            <svg className="w-6 h-6 opacity-20" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
                d="M18.364 18.364A9 9 0 005.636 5.636m12.728 12.728L5.636 5.636" />
            </svg>
            <span className="text-xs">No feed</span>
          </div>
        )}

        {/* Subtle bottom gradient */}
        <div className="absolute inset-x-0 bottom-0 h-8 bg-gradient-to-t from-black/40 to-transparent pointer-events-none" />
      </div>

      {/* Status bar */}
      <div className="px-3 sm:px-4 py-2 flex items-center justify-between border-t border-border/50">
        <div className="flex items-center gap-2 min-w-0">
          <span className={`w-2 h-2 rounded-full shrink-0 ${status === 'ok' ? 'bg-success' : 'bg-danger animate-pulse'}`} />
          <span className="text-xs text-text-muted truncate">{statusText}</span>
        </div>
        <span className="text-[11px] text-text-dim opacity-0 group-hover:opacity-100 transition-opacity shrink-0 ml-2">
          Expand &rarr;
        </span>
      </div>
    </div>
  )
}
