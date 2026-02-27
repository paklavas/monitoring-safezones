import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth, type UserCamera } from '../hooks/useAuth'
import Header from '../components/Header'

type SystemCamera = {
  id: number
  zone_id: number
  name: string
  type: string
  url: string | null
  is_active: boolean
}

export default function ManageCameras() {
  const navigate = useNavigate()
  const { user, cameras, setCameras } = useAuth()
  const [allCameras, setAllCameras] = useState<SystemCamera[]>([])
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState<number | null>(null)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')

  // Fetch all system cameras
  useEffect(() => {
    const fetchCameras = async () => {
      try {
        const resp = await fetch('/api/cameras')
        if (resp.ok) {
          const data = await resp.json()
          setAllCameras(data.cameras ?? [])
        }
      } catch {
        setError('Failed to load cameras')
      } finally {
        setLoading(false)
      }
    }
    fetchCameras()
  }, [])

  const assignedIds = new Set(cameras.map(c => c.id))

  const handleAssign = async (cameraId: number) => {
    if (!user) return
    setSaving(cameraId)
    setError('')
    setSuccess('')
    try {
      const resp = await fetch(`/api/users/${user.id}/cameras`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ camera_id: cameraId }),
      })
      const data = await resp.json()
      if (resp.ok && data.success) {
        // Refresh cameras from backend
        await refreshUserCameras()
        setSuccess('Camera assigned successfully')
      } else {
        setError(data.error || 'Failed to assign camera')
      }
    } catch {
      setError('Connection error')
    } finally {
      setSaving(null)
    }
  }

  const handleRemove = async (cameraId: number) => {
    if (!user) return
    setSaving(cameraId)
    setError('')
    setSuccess('')
    try {
      const resp = await fetch(`/api/users/${user.id}/cameras/${cameraId}`, {
        method: 'DELETE',
      })
      const data = await resp.json()
      if (resp.ok && data.success) {
        await refreshUserCameras()
        setSuccess('Camera removed successfully')
      } else {
        setError(data.error || 'Failed to remove camera')
      }
    } catch {
      setError('Connection error')
    } finally {
      setSaving(null)
    }
  }

  const refreshUserCameras = async () => {
    if (!user) return
    try {
      const resp = await fetch(`/api/users/${user.id}/cameras`)
      if (resp.ok) {
        const data = await resp.json()
        setCameras(data.cameras ?? [])
      }
    } catch {
      // ignore
    }
  }

  return (
    <div className="h-screen flex flex-col bg-surface">
      <Header
        title="Manage Cameras"
        subtitle="Assign or remove cameras from your account"
        showBack
        onBack={() => navigate('/')}
      />

      <div className="flex-1 overflow-auto p-3 sm:p-6">
        <div className="max-w-3xl mx-auto space-y-6">
          {/* Status messages */}
          {error && (
            <div className="bg-danger/10 border border-danger/30 text-danger px-4 py-3 rounded text-sm">
              {error}
            </div>
          )}
          {success && (
            <div className="bg-success/10 border border-success/30 text-success px-4 py-3 rounded text-sm">
              {success}
            </div>
          )}

          {/* My cameras */}
          <section>
            <h2 className="text-sm font-semibold text-accent uppercase tracking-wider mb-3">
              My assigned cameras ({cameras.length})
            </h2>
            <div className="h-px bg-border mb-4" />
            {cameras.length === 0 ? (
              <p className="text-text-muted text-sm">No cameras assigned yet. Add cameras from the list below.</p>
            ) : (
              <div className="space-y-2">
                {cameras.map(cam => (
                  <div key={cam.id} className="bg-card border border-border rounded-lg p-4 flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <span className={`w-2 h-2 rounded-full ${cam.is_active ? 'bg-success' : 'bg-text-dim'}`} />
                      <div>
                        <p className="text-white text-sm font-medium">{cam.name}</p>
                        <p className="text-text-muted text-xs">
                          Zone {cam.zone_id} &middot; {cam.type} &middot; {cam.is_active ? 'Active' : 'Inactive'}
                        </p>
                      </div>
                    </div>
                    <button
                      onClick={() => handleRemove(cam.id)}
                      disabled={saving === cam.id}
                      className="px-3 py-1.5 bg-danger/20 text-danger border border-danger/30 rounded text-xs font-medium hover:bg-danger/30 transition-colors disabled:opacity-50"
                    >
                      {saving === cam.id ? 'Removing...' : 'Remove'}
                    </button>
                  </div>
                ))}
              </div>
            )}
          </section>

          {/* All available cameras */}
          <section>
            <h2 className="text-sm font-semibold text-accent uppercase tracking-wider mb-3">
              Available cameras
            </h2>
            <div className="h-px bg-border mb-4" />
            {loading ? (
              <p className="text-text-muted text-sm">Loading cameras...</p>
            ) : allCameras.length === 0 ? (
              <p className="text-text-muted text-sm">No cameras configured in the system.</p>
            ) : (
              <div className="space-y-2">
                {allCameras.map(cam => {
                  const isAssigned = assignedIds.has(cam.id)
                  return (
                    <div key={cam.id} className="bg-card border border-border rounded-lg p-4 flex items-center justify-between">
                      <div className="flex items-center gap-3">
                        <span className={`w-2 h-2 rounded-full ${cam.is_active ? 'bg-success' : 'bg-text-dim'}`} />
                        <div>
                          <p className="text-white text-sm font-medium">{cam.name}</p>
                          <p className="text-text-muted text-xs">
                            Zone {cam.zone_id} &middot; {cam.type} &middot; {cam.is_active ? 'Active' : 'Inactive'}
                          </p>
                        </div>
                      </div>
                      {isAssigned ? (
                        <span className="px-3 py-1.5 bg-success/10 text-success border border-success/30 rounded text-xs font-medium">
                          Assigned
                        </span>
                      ) : (
                        <button
                          onClick={() => handleAssign(cam.id)}
                          disabled={saving === cam.id}
                          className="px-3 py-1.5 bg-accent/20 text-accent border border-accent/30 rounded text-xs font-medium hover:bg-accent/30 transition-colors disabled:opacity-50"
                        >
                          {saving === cam.id ? 'Adding...' : 'Add'}
                        </button>
                      )}
                    </div>
                  )
                })}
              </div>
            )}
          </section>
        </div>
      </div>
    </div>
  )
}
