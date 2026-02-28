import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth'
import Header from '../components/Header'
import AddCameraModal, { type CameraFormData } from '../components/AddCameraModal'

type UserCamera = {
  id: number
  zone_id: number
  name: string
  type: string
  config: Record<string, string | number>
  is_active: boolean
}

const TYPE_BADGE: Record<string, { label: string; cls: string }> = {
  webcam: { label: 'Webcam', cls: 'bg-blue-500/20 text-blue-400 border-blue-500/30' },
  rtsp:   { label: 'RTSP',   cls: 'bg-purple-500/20 text-purple-400 border-purple-500/30' },
  http:   { label: 'HTTP',   cls: 'bg-amber-500/20 text-amber-400 border-amber-500/30' },
  hls:    { label: 'HLS',    cls: 'bg-teal-500/20 text-teal-400 border-teal-500/30' },
}

export default function ManageCameras() {
  const navigate = useNavigate()
  const { user, setCameras } = useAuth()
  const [myCameras, setMyCameras] = useState<UserCamera[]>([])
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState<number | null>(null)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')

  const [modalOpen, setModalOpen] = useState(false)
  const [editCamera, setEditCamera] = useState<UserCamera | null>(null)
  const [confirmDelete, setConfirmDelete] = useState<number | null>(null)

  const fetchMyCameras = async () => {
    if (!user) return
    try {
      const resp = await fetch(`/api/users/${user.id}/cameras`)
      if (resp.ok) {
        const data = await resp.json()
        const cams: UserCamera[] = data.cameras ?? []
        setMyCameras(cams)
        setCameras(cams.map(c => ({ id: c.id, zone_id: c.zone_id, name: c.name, type: c.type, is_active: c.is_active })))
      }
    } catch {
      setError('Failed to load cameras')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { fetchMyCameras() }, [user])

  const handleAddOrEdit = async (formData: CameraFormData) => {
    if (editCamera) {
      const resp = await fetch(`/api/cameras/${editCamera.id}`, {
        method: 'PUT', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(formData),
      })
      const data = await resp.json()
      if (!resp.ok) throw new Error(data.error || 'Update failed')
      setSuccess('Camera updated')
    } else {
      const resp = await fetch('/api/cameras', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(formData),
      })
      const data = await resp.json()
      if (!resp.ok) throw new Error(data.error || 'Create failed')
      if (user && data.camera?.id) {
        await fetch(`/api/users/${user.id}/cameras`, {
          method: 'POST', headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ camera_id: data.camera.id }),
        })
      }
      setSuccess('Camera added')
    }
    setEditCamera(null)
    await fetchMyCameras()
  }

  const handleDelete = async (cameraId: number) => {
    setError(''); setSuccess('')
    setSaving(cameraId)
    try {
      const resp = await fetch(`/api/cameras/${cameraId}`, { method: 'DELETE' })
      const data = await resp.json()
      if (resp.ok && data.success) {
        setSuccess('Camera deleted')
        await fetchMyCameras()
      } else {
        setError(data.error || 'Delete failed')
      }
    } catch { setError('Connection error') }
    finally { setConfirmDelete(null); setSaving(null) }
  }

  const openEdit = (cam: UserCamera) => { setEditCamera(cam); setModalOpen(true) }
  const openAdd = () => { setEditCamera(null); setModalOpen(true) }

  return (
    <div className="h-screen flex flex-col bg-surface">
      <Header
        title="My Cameras"
        subtitle="Add, edit, or remove cameras from your account"
        showBack
        onBack={() => navigate('/')}
      />

      <div className="flex-1 overflow-auto p-3 sm:p-6">
        <div className="max-w-3xl mx-auto space-y-6">

          {error && (
            <div className="bg-danger/10 border border-danger/30 text-danger px-4 py-3 rounded text-sm">{error}</div>
          )}
          {success && (
            <div className="bg-success/10 border border-success/30 text-success px-4 py-3 rounded text-sm">{success}</div>
          )}

          {/* Header with Add button */}
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-semibold text-accent uppercase tracking-wider">
              My cameras ({myCameras.length})
            </h2>
            <button
              onClick={openAdd}
              className="flex items-center gap-1.5 px-3 py-1.5 bg-accent text-black rounded-lg text-xs font-semibold hover:bg-accent-soft transition-colors"
            >
              <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
              </svg>
              Add Camera
            </button>
          </div>
          <div className="h-px bg-border" />

          {/* Camera list */}
          {loading ? (
            <p className="text-text-muted text-sm">Loading cameras...</p>
          ) : myCameras.length === 0 ? (
            <div className="text-center py-12 space-y-3">
              <svg className="w-12 h-12 mx-auto text-text-dim opacity-30" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
                  d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
              </svg>
              <p className="text-text-muted text-sm">No cameras yet. Click "Add Camera" to get started.</p>
            </div>
          ) : (
            <div className="space-y-2">
              {myCameras.map(cam => {
                const badge = TYPE_BADGE[cam.type]
                return (
                  <div key={cam.id} className="bg-card border border-border rounded-lg p-4">
                    <div className="flex items-center justify-between gap-3">
                      <div className="flex items-center gap-3 min-w-0">
                        <span className={`w-2 h-2 rounded-full shrink-0 ${cam.is_active ? 'bg-success' : 'bg-text-dim'}`} />
                        <div className="min-w-0">
                          <div className="flex items-center gap-2 flex-wrap">
                            <p className="text-white text-sm font-medium truncate">{cam.name}</p>
                            {badge && (
                              <span className={`text-[10px] font-semibold px-1.5 py-0.5 rounded border shrink-0 ${badge.cls}`}>
                                {badge.label}
                              </span>
                            )}
                          </div>
                          <p className="text-text-muted text-xs">
                            Zone {cam.zone_id} &middot; {cam.is_active ? 'Active' : 'Inactive'}
                          </p>
                        </div>
                      </div>

                      <div className="flex items-center gap-2 shrink-0">
                        <button onClick={() => openEdit(cam)}
                          className="px-2.5 py-1.5 text-text-muted hover:text-white border border-border rounded text-xs transition-colors">
                          Edit
                        </button>
                        {confirmDelete === cam.id ? (
                          <div className="flex items-center gap-1">
                            <button onClick={() => handleDelete(cam.id)} disabled={saving === cam.id}
                              className="px-2 py-1 bg-danger text-white rounded text-xs font-medium disabled:opacity-50">
                              {saving === cam.id ? '...' : 'Yes'}
                            </button>
                            <button onClick={() => setConfirmDelete(null)}
                              className="px-2 py-1 border border-border text-text-muted rounded text-xs">No</button>
                          </div>
                        ) : (
                          <button onClick={() => setConfirmDelete(cam.id)}
                            className="px-2.5 py-1.5 text-danger/70 hover:text-danger border border-border rounded text-xs transition-colors">
                            Delete
                          </button>
                        )}
                      </div>
                    </div>
                  </div>
                )
              })}
            </div>
          )}

        </div>
      </div>

      <AddCameraModal
        open={modalOpen}
        onClose={() => { setModalOpen(false); setEditCamera(null) }}
        onSave={handleAddOrEdit}
        initial={editCamera ? { name: editCamera.name, type: editCamera.type, config: editCamera.config, is_active: editCamera.is_active } : undefined}
        title={editCamera ? 'Edit Camera' : 'Add Camera'}
      />
    </div>
  )
}
