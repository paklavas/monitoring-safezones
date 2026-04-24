import { useParams, useNavigate } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth'
import PageHeader from '../components/PageHeader'
import AlertList, { type AlertItem } from '../components/AlertList'

export default function CameraDetail() {
  const { cameraId } = useParams<{ cameraId: string }>()
  const navigate = useNavigate()
  const { cameras } = useAuth()
  const id = parseInt(cameraId || '0', 10) || 0

  const camera = cameras.find(c => c.id === id)
  const hasAccess = !!camera
  const streamUrl = hasAccess && camera.is_active ? `/stream/${camera.id}` : null

  const alerts: AlertItem[] = hasAccess
    ? [{ id: '1', message: `Viewing ${camera.name}`, type: 'info', time: new Date().toLocaleTimeString() }]
    : [{ id: '1', message: `No access to camera ${id}`, type: 'danger', time: new Date().toLocaleTimeString() }]

  return (
    <div className="flex-1 flex flex-col min-h-0 bg-surface">
      <PageHeader
        title={camera ? `${camera.name} – Live feed` : `Camera ${id} – No access`}
        subtitle={hasAccess ? 'Full-screen camera view' : 'You do not have access to this camera'}
        showBack
        onBack={() => navigate('/')}
      />

      <div className="flex-1 min-h-0 overflow-auto lg:overflow-hidden">
        <div className="flex flex-col lg:flex-row lg:h-full p-3 sm:p-4 gap-4">

          {/* Video feed */}
          <div className="flex-1 flex flex-col min-w-0 min-h-0">
            <h2 className="text-xs font-semibold text-accent uppercase tracking-wider mb-3">Live feed</h2>
            <div className="h-px bg-border mb-4" />
            <div className="flex-1 min-h-[240px] sm:min-h-[360px] lg:min-h-0 bg-black rounded-lg flex items-center justify-center overflow-hidden">
              {!hasAccess ? (
                <div className="text-center text-text-dim space-y-2 p-4">
                  <p className="text-lg">Access Denied</p>
                  <p className="text-sm">This camera is not assigned to your account.</p>
                  <button
                    onClick={() => navigate('/')}
                    className="mt-4 px-4 py-2 bg-accent text-black rounded hover:bg-accent-soft transition-colors text-sm font-medium"
                  >
                    Back to Dashboard
                  </button>
                </div>
              ) : streamUrl ? (
                <img
                  src={streamUrl}
                  alt={camera.name}
                  className="w-full h-full object-contain"
                />
              ) : (
                <span className="text-text-dim">Camera offline</span>
              )}
            </div>
            {hasAccess && (
              <div className="flex items-center gap-2 mt-3">
                <span className="w-2 h-2 rounded-full bg-success" />
                <span className="text-sm text-text-muted">All workers compliant</span>
              </div>
            )}
          </div>

          {/* Alerts */}
          <aside className="shrink-0 lg:w-72 xl:w-80 flex flex-col">
            <h2 className="text-xs font-semibold text-accent uppercase tracking-wider mb-3">
              Alerts{camera ? ` – ${camera.name}` : ''}
            </h2>
            <div className="h-px bg-border mb-4" />
            <div className="max-h-60 lg:max-h-none lg:flex-1 overflow-y-auto">
              <AlertList items={alerts} cameraId={hasAccess ? id : undefined} />
            </div>
          </aside>

        </div>
      </div>
    </div>
  )
}
