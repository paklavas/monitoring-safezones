import { useState, useEffect, useRef } from 'react'
import { useAuth } from '../hooks/useAuth'
import Header from '../components/Header'
import StatCard from '../components/StatCard'
import CameraCard from '../components/CameraCard'
import AlertList, { type AlertItem } from '../components/AlertList'

function formatUptime(ms: number) {
  const h = Math.floor(ms / 3600000)
  const m = Math.floor((ms % 3600000) / 60000)
  return `${h}h ${m}m`
}

export default function Dashboard() {
  const { cameras } = useAuth()
  const [alertsOpen, setAlertsOpen] = useState(false)

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
    setStats(prev => ({ ...prev, cameras: cameras.length }))
    const zs: Record<number, { status: 'ok' | 'violation'; text: string }> = {}
    cameras.forEach(c => { zs[c.zone_id] = { status: 'ok', text: 'All workers compliant' } })
    setZoneStatus(zs)
  }, [cameras])

  useEffect(() => {
    const t = setInterval(() => setStats(s => ({ ...s, uptime: Date.now() - startRef.current })), 60_000)
    return () => clearInterval(t)
  }, [])

  useEffect(() => {
    let lastStatus: 'checking' | 'connected' | 'disconnected' = 'checking'

    const checkBackend = async () => {
      try {
        const response = await fetch('/api/health')
        if (response.ok) {
          const data = await response.json()
          if (lastStatus !== 'connected') {
            setBackendStatus('connected')
            lastStatus = 'connected'
            const cam1 = data.camera1 ? 'OK' : 'OFF'
            const cam2 = data.camera2 ? 'OK' : 'OFF'
            setAlerts(prev => {
              const exists = prev.some(a => a.message.includes('Backend connected'))
              if (exists) return prev
              return [...prev, {
                id: `backend-${Date.now()}`,
                message: `Backend connected - Camera 1: ${cam1}, Camera 2: ${cam2}`,
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
              message: 'Backend server not running. Start Flask: python -m app.server',
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
    <div className="h-screen flex flex-col bg-surface">
      <Header />

      {/* ── Compact stats strip — minimal height, always visible ── */}
      <div className="shrink-0 border-b border-border bg-header/40 px-3 sm:px-5 py-2">
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
          <StatCard label="Compliant" value={String(stats.compliant)} color="success" />
          <StatCard label="Violations" value={String(stats.violations)} color="danger" />
          <StatCard label="Cameras" value={String(stats.cameras)} color="accent" />
          <StatCard label="Uptime" value={formatUptime(stats.uptime)} color="muted" />
        </div>
      </div>

      {/* ── Main content area — cameras dominate, alerts are secondary ── */}
      <div className="flex-1 min-h-0 flex flex-col">

        {/* Cameras (primary) + desktop alerts sidebar */}
        <div className="flex-1 min-h-0 flex">

          {/* Camera grid — fills all available space */}
          <main className="flex-1 min-w-0 overflow-auto p-3 sm:p-4 lg:p-5">
            {cameras.length === 0 ? (
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
            ) : cameras.length === 1 ? (
              <div className="h-full">
                <CameraCard
                  key={cameras[0].id}
                  zoneId={cameras[0].zone_id}
                  streamUrl={cameras[0].is_active ? `/stream/${cameras[0].zone_id}` : null}
                  status={zoneStatus[cameras[0].zone_id]?.status ?? 'ok'}
                  statusText={zoneStatus[cameras[0].zone_id]?.text ?? 'All workers compliant'}
                  cameraName={cameras[0].name}
                  fill
                />
              </div>
            ) : (
              <div className={`grid gap-3 sm:gap-4 ${
                cameras.length <= 4
                  ? 'grid-cols-1 sm:grid-cols-2'
                  : 'grid-cols-1 sm:grid-cols-2 2xl:grid-cols-3'
              }`}>
                {cameras.map((cam) => (
                  <CameraCard
                    key={cam.id}
                    zoneId={cam.zone_id}
                    streamUrl={cam.is_active ? `/stream/${cam.zone_id}` : null}
                    status={zoneStatus[cam.zone_id]?.status ?? 'ok'}
                    statusText={zoneStatus[cam.zone_id]?.text ?? 'All workers compliant'}
                    cameraName={cam.name}
                  />
                ))}
              </div>
            )}
          </main>

          {/* Alerts sidebar — visible on xl+ screens */}
          <aside className="hidden xl:flex flex-col shrink-0 w-72 border-l border-border bg-card/20">
            <div className="shrink-0 px-4 py-3 border-b border-border flex items-center justify-between">
              <h3 className="text-xs font-semibold text-accent uppercase tracking-wider">Alert Log</h3>
              <span className="text-[11px] text-text-dim tabular-nums">{alerts.length}</span>
            </div>
            <div className="flex-1 overflow-y-auto p-3">
              <AlertList items={alerts} />
            </div>
          </aside>

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
