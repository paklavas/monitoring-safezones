import { useState, useEffect, useRef } from 'react'
import { useAuth } from '../hooks/useAuth'
import PageHeader from '../components/PageHeader'
import StatCard from '../components/StatCard'
import CameraCard from '../components/CameraCard'
import AlertList, { type AlertItem } from '../components/AlertList'

function formatUptime(ms: number) {
  const h = Math.floor(ms / 3600000)
  const m = Math.floor((ms % 3600000) / 60000)
  return `${h}h ${m}m`
}

export default function Dashboard() {
  const { user, cameras, setCameras } = useAuth()
  const [alertsOpen, setAlertsOpen] = useState(false)

  // Only show cameras that are marked active (checked on Manage Cameras page)
  const visibleCameras = cameras.filter(c => c.is_active)

  const [stats, setStats] = useState({
    compliant: 0,
    violations: 0,
    cameras: cameras.length,
    uptime: 0,
  })
  const [alerts, setAlerts] = useState<AlertItem[]>([
    { id: '1', message: 'System initialized', type: 'info', time: new Date().toLocaleTimeString() },
  ])
  const [zoneStatus, setZoneStatus] = useState<Record<number, { status: 'ok' | 'violation'; text: string }>>({})

  const startRef = useRef(Date.now())
  const [, setBackendStatus] = useState<'checking' | 'connected' | 'disconnected'>('checking')

  useEffect(() => {
    setStats(prev => ({ ...prev, cameras: visibleCameras.length }))
    const zs: Record<number, { status: 'ok' | 'violation'; text: string }> = {}
    cameras.forEach(c => { zs[c.zone_id] = { status: 'ok', text: 'All workers compliant' } })
    setZoneStatus(zs)
  }, [cameras])

  useEffect(() => {
    if (!user) return
    const refreshUserCameras = async () => {
      try {
        const resp = await fetch(`/api/users/${user.id}/cameras`)
        if (resp.ok) {
          const data = await resp.json()
          const list = data.cameras ?? []
          setCameras(list.map((c: { id: number; zone_id: number; name: string; type: string; is_active: boolean }) =>
            ({ id: c.id, zone_id: c.zone_id, name: c.name, type: c.type, is_active: c.is_active })))
        }
      } catch { /* ignore */ }
    }
    refreshUserCameras()
  }, [user?.id])

  useEffect(() => {
    const t = setInterval(() => setStats(s => ({ ...s, uptime: Date.now() - startRef.current })), 60_000)
    return () => clearInterval(t)
  }, [])

  useEffect(() => {
    const pollStats = async () => {
      try {
        const url = user?.id != null ? `/api/stats?user_id=${user.id}` : '/api/stats'
        const resp = await fetch(url)
        if (resp.ok) {
          const data = await resp.json()
          setStats(s => ({
            ...s,
            compliant: data.compliant ?? 0,
            violations: data.violations ?? 0,
          }))
        }
      } catch { /* ignore */ }
    }
    pollStats()
    const interval = setInterval(pollStats, 2000)
    return () => clearInterval(interval)
  }, [user?.id])

  useEffect(() => {
    let lastStatus: 'checking' | 'connected' | 'disconnected' = 'checking'

    const checkBackend = async () => {
      try {
        const response = await fetch('/api/health')
        if (response.ok) {
          if (lastStatus !== 'connected') {
            setBackendStatus('connected')
            lastStatus = 'connected'
            setAlerts(prev => {
              const exists = prev.some(a => a.message.includes('Backend connected'))
              if (exists) return prev
              return [...prev, {
                id: `backend-${Date.now()}`,
                message: `Backend connected${user?.id != null && cameras.length > 0 ? ` – ${cameras.length} camera(s) in your account` : ''}`,
                type: 'success',
                time: new Date().toLocaleTimeString(),
              }]
            })
          }
        } else {
          if (lastStatus !== 'disconnected') {
            setBackendStatus('disconnected')
            lastStatus = 'disconnected'
          }
        }
      } catch {
        if (lastStatus !== 'disconnected') {
          setBackendStatus('disconnected')
          lastStatus = 'disconnected'
          setAlerts(prev => {
            const exists = prev.some(a => a.message.includes('Backend server not running'))
            if (exists) return prev
            return [...prev, {
              id: `backend-error-${Date.now()}`,
              message: 'Backend server not running. Start Flask: python -m backend.server',
              type: 'danger',
              time: new Date().toLocaleTimeString(),
            }]
          })
        }
      }
    }
    checkBackend()
    const interval = setInterval(checkBackend, 10000)
    return () => clearInterval(interval)
  }, [])

  return (
    <div className="flex-1 flex flex-col min-h-0 bg-surface">
      <PageHeader
        title="Dashboard"
        subtitle=""
        showTime
      />
      {/* Stats strip — compact, modern cards */}
      <div className="shrink-0 border-b border-border bg-card/30">
        <div className="h-0.5 bg-accent" />
        <div className="px-3 sm:px-5 py-3">
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 sm:gap-3">
            <StatCard label="Compliant" value={String(stats.compliant)} color="success" />
            <StatCard label="Violations" value={String(stats.violations)} color="danger" />
            <StatCard label="Cameras" value={String(visibleCameras.length)} color="accent" />
            <StatCard label="Uptime" value={formatUptime(stats.uptime)} color="muted" />
          </div>
        </div>
      </div>

      {/* ── Main content area — cameras dominate, alerts are secondary ── */}
      <div className="flex-1 min-h-0 flex flex-col">

        {/* Cameras (primary) + desktop alerts sidebar */}
        <div className="flex-1 min-h-0 flex">

          {/* Camera grid — fills all available space */}
          <main className="flex-1 min-w-0 overflow-auto p-3 sm:p-4 lg:p-5">
            {visibleCameras.length === 0 ? (
              <div className="h-full flex items-center justify-center">
                <div className="text-center text-text-muted space-y-3">
                  <svg className="w-14 h-14 mx-auto opacity-20" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
                      d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
                  </svg>
                  <p className="text-lg font-medium">No cameras assigned</p>
                  <p className="text-sm text-text-dim">Contact your administrator to assign cameras.</p>
                </div>
              </div>
            ) : visibleCameras.length === 1 ? (
              <div className="h-full">
                <CameraCard
                  key={visibleCameras[0].id}
                  cameraId={visibleCameras[0].id}
                  zoneId={visibleCameras[0].zone_id}
                  streamUrl={`/stream/${visibleCameras[0].id}`}
                  status={zoneStatus[visibleCameras[0].zone_id]?.status ?? 'ok'}
                  statusText={zoneStatus[visibleCameras[0].zone_id]?.text ?? 'All workers compliant'}
                  cameraName={visibleCameras[0].name}
                  fill
                />
              </div>
            ) : (
              <div className={`grid gap-3 sm:gap-4 ${
                visibleCameras.length <= 4
                  ? 'grid-cols-1 sm:grid-cols-2'
                  : 'grid-cols-1 sm:grid-cols-2 2xl:grid-cols-3'
              }`}>
                {visibleCameras.map((cam) => (
                  <CameraCard
                    key={cam.id}
                    cameraId={cam.id}
                    zoneId={cam.zone_id}
                    streamUrl={`/stream/${cam.id}`}
                    status={zoneStatus[cam.zone_id]?.status ?? 'ok'}
                    statusText={zoneStatus[cam.zone_id]?.text ?? 'All workers compliant'}
                    cameraName={cam.name}
                  />
                ))}
              </div>
            )}
          </main>

        </div>

        {/* Alerts panel — mobile/tablet: collapsible bottom strip */}
        <div className="xl:hidden shrink-0 border-t border-border bg-card/30">
          <button
            onClick={() => setAlertsOpen(o => !o)}
            className="w-full flex items-center justify-between px-4 py-2.5 hover:bg-white/[0.02] active:bg-white/[0.04] transition-colors"
          >
            <span className="text-xs font-semibold text-accent uppercase tracking-wider">
              Alerts ({alerts.length})
            </span>
            <svg
              className={`w-4 h-4 text-text-dim transition-transform duration-200 ${alertsOpen ? 'rotate-180' : ''}`}
              fill="none" stroke="currentColor" viewBox="0 0 24 24"
            >
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 15l7-7 7 7" />
            </svg>
          </button>
          {alertsOpen && (
            <div className="max-h-52 overflow-y-auto px-3 pb-3 border-t border-border/50">
              <AlertList items={alerts} />
            </div>
          )}
        </div>

      </div>
    </div>
  )
}
