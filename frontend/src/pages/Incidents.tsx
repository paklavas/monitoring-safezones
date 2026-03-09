import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth'
import Header from '../components/Header'

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

type AutoDeleteOption = 'none' | 'day' | 'week' | 'month' | 'year'

export default function Incidents() {
  const navigate = useNavigate()
  const { user } = useAuth()
  const [violations, setViolations] = useState<Violation[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)
  const [page, setPage] = useState(0)
  const [selectedImage, setSelectedImage] = useState<string | null>(null)
  const [fetchError, setFetchError] = useState<string | null>(null)
  const [autoDelete, setAutoDelete] = useState<AutoDeleteOption>('none')
  const [settingsLoading, setSettingsLoading] = useState(true)
  const [deleteAllLoading, setDeleteAllLoading] = useState(false)
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false)
  const perPage = 20

  const fetchViolations = async (pageOverride?: number) => {
    if (!user) return
    const p = pageOverride ?? page
    setLoading(true)
    setFetchError(null)
    try {
      const resp = await fetch(`/api/violations?user_id=${user.id}&limit=${perPage}&offset=${p * perPage}`)
      if (resp.ok) {
        const data = await resp.json()
        setViolations(data.violations ?? [])
        setTotal(data.total ?? 0)
      } else {
        const err = await resp.json().catch(() => ({}))
        setFetchError(err.error || 'Failed to load violations')
      }
    } catch (e) {
      setFetchError('Connection error. Is the backend running?')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (!user) return
    fetchViolations()
  }, [user?.id, page])

  useEffect(() => {
    if (!user) return
    const loadSettings = async () => {
      setSettingsLoading(true)
      try {
        const resp = await fetch(`/api/users/${user.id}/settings`)
        if (resp.ok) {
          const data = await resp.json()
          setAutoDelete((data.violation_auto_delete || 'none') as AutoDeleteOption)
        }
      } catch { /* ignore */ } finally {
        setSettingsLoading(false)
      }
    }
    loadSettings()
  }, [user?.id])

  const handleAutoDeleteChange = async (value: AutoDeleteOption) => {
    setAutoDelete(value)
    if (!user) return
    try {
      await fetch(`/api/users/${user.id}/settings`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ violation_auto_delete: value }),
      })
    } catch { /* ignore */ }
  }

  const handleDeleteAllNow = async () => {
    if (!user) return
    setDeleteAllLoading(true)
    setShowDeleteConfirm(false)
    try {
      const resp = await fetch('/api/violations/delete-all', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_id: user.id }),
      })
      if (resp.ok) {
        setPage(0)
        fetchViolations(0)
      }
    } catch { /* ignore */ } finally {
      setDeleteAllLoading(false)
    }
  }

  const totalPages = Math.ceil(total / perPage)

  return (
    <div className="h-screen flex flex-col bg-surface">
      <Header
        title="Incident Review"
        subtitle="Violation snapshots captured by the detection system"
        showBack
        onBack={() => navigate('/')}
      />

      <div className="flex-1 overflow-auto p-3 sm:p-6">
        <div className="max-w-5xl mx-auto space-y-4">

          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 flex-wrap">
            <h2 className="text-sm font-semibold text-accent uppercase tracking-wider">
              Violations ({total})
            </h2>
            <div className="flex flex-wrap items-center gap-2">
              <label className="flex items-center gap-2 text-xs text-text-muted">
                <span>Auto-delete:</span>
                <select
                  value={autoDelete}
                  onChange={(e) => handleAutoDeleteChange(e.target.value as AutoDeleteOption)}
                  disabled={settingsLoading}
                  className="bg-card border border-border rounded px-2 py-1.5 text-white text-xs focus:outline-none focus:ring-1 focus:ring-accent"
                >
                  <option value="none">Never</option>
                  <option value="day">Every day</option>
                  <option value="week">Every week</option>
                  <option value="month">Every month</option>
                  <option value="year">Every year</option>
                </select>
              </label>
              <button
                onClick={() => setShowDeleteConfirm(true)}
                disabled={deleteAllLoading || total === 0}
                className="px-3 py-1.5 text-xs font-medium border border-danger/50 text-danger rounded hover:bg-danger/10 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
              >
                {deleteAllLoading ? 'Deleting...' : 'Delete All Now'}
              </button>
              {totalPages > 1 && (
                <div className="flex items-center gap-2 text-xs">
                  <button
                    onClick={() => setPage(p => Math.max(0, p - 1))}
                    disabled={page === 0}
                    className="px-2 py-1 border border-border rounded text-text-muted hover:text-white disabled:opacity-30 transition-colors"
                  >
                    Prev
                  </button>
                  <span className="text-text-muted tabular-nums">{page + 1} / {totalPages}</span>
                  <button
                    onClick={() => setPage(p => Math.min(totalPages - 1, p + 1))}
                    disabled={page >= totalPages - 1}
                    className="px-2 py-1 border border-border rounded text-text-muted hover:text-white disabled:opacity-30 transition-colors"
                  >
                    Next
                  </button>
                </div>
              )}
            </div>
          </div>
          {showDeleteConfirm && (
            <div className="flex items-center gap-3 p-3 bg-card border border-border rounded-lg">
              <span className="text-sm text-text-muted">Delete all {total} violation(s) from your cameras? This cannot be undone.</span>
              <div className="flex gap-2 shrink-0">
                <button
                  onClick={() => setShowDeleteConfirm(false)}
                  className="px-3 py-1.5 text-xs border border-border rounded hover:bg-white/5"
                >
                  Cancel
                </button>
                <button
                  onClick={handleDeleteAllNow}
                  disabled={deleteAllLoading}
                  className="px-3 py-1.5 text-xs font-medium bg-danger text-white rounded hover:opacity-90 disabled:opacity-60"
                >
                  Yes, Delete All
                </button>
              </div>
            </div>
          )}
          <div className="h-px bg-border" />

          {fetchError && (
            <div className="bg-danger/10 border border-danger/30 text-danger px-4 py-3 rounded text-sm">{fetchError}</div>
          )}

          {loading ? (
            <p className="text-text-muted text-sm py-8 text-center">Loading incidents...</p>
          ) : violations.length === 0 ? (
            <div className="text-center py-16 space-y-4">
              <svg className="w-12 h-12 mx-auto text-text-dim opacity-30" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
                  d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <p className="text-text-muted text-sm">No violations found.</p>
              <p className="text-text-dim text-xs max-w-md mx-auto">
                You only see violations from cameras assigned to your account. Assign cameras in Manage Cameras to view their incident snapshots.
              </p>
            </div>
          ) : (
            <div className="grid gap-3 grid-cols-1 sm:grid-cols-2 lg:grid-cols-3">
              {violations.map(v => (
                <div key={v.id} className="bg-card border border-border rounded-lg overflow-hidden">
                  {v.snapshot_url ? (
                    <button
                      onClick={() => setSelectedImage(v.snapshot_url)}
                      className="w-full aspect-video bg-black relative group cursor-pointer"
                    >
                      <img
                        src={v.snapshot_url}
                        alt={`Violation ${v.id}`}
                        className="w-full h-full object-cover"
                        loading="lazy"
                      />
                      <div className="absolute inset-0 bg-black/0 group-hover:bg-black/30 transition-colors flex items-center justify-center">
                        <svg className="w-8 h-8 text-white opacity-0 group-hover:opacity-80 transition-opacity" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                            d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0zM10 7v3m0 0v3m0-3h3m-3 0H7" />
                        </svg>
                      </div>
                    </button>
                  ) : (
                    <div className="w-full aspect-video bg-black/50 flex items-center justify-center">
                      <span className="text-text-dim text-xs">No snapshot</span>
                    </div>
                  )}
                  <div className="p-3 space-y-1.5">
                    <div className="flex items-center justify-between">
                      <span className="text-white text-sm font-medium truncate">{v.camera_name}</span>
                      <span className="text-danger text-xs font-semibold bg-danger/10 border border-danger/30 px-1.5 py-0.5 rounded">
                        {v.violation_count} violation{v.violation_count !== 1 ? 's' : ''}
                      </span>
                    </div>
                    <div className="flex items-center gap-3 text-xs text-text-muted">
                      <span>Persons: {v.person_count}</span>
                      <span>Helmets: {v.helmet_count}</span>
                      <span>Conf: {(v.confidence * 100).toFixed(0)}%</span>
                    </div>
                    <p className="text-xs text-text-dim">
                      {new Date(v.created_at).toLocaleString()}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {selectedImage && (
        <div
          className="fixed inset-0 z-50 bg-black/80 flex items-center justify-center p-4"
          onClick={() => setSelectedImage(null)}
        >
          <div className="relative max-w-4xl w-full" onClick={e => e.stopPropagation()}>
            <button
              onClick={() => setSelectedImage(null)}
              className="absolute -top-10 right-0 text-white/70 hover:text-white text-sm transition-colors"
            >
              Close
            </button>
            <img
              src={selectedImage}
              alt="Violation snapshot"
              className="w-full rounded-lg shadow-2xl"
            />
          </div>
        </div>
      )}
    </div>
  )
}
