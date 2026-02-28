import { useState, useEffect } from 'react'

const CAMERA_TYPES = [
  { value: 'webcam', label: 'USB Webcam' },
  { value: 'rtsp', label: 'RTSP Camera' },
  { value: 'http', label: 'HTTP / MJPEG IP Camera' },
  { value: 'hls', label: 'HLS Stream' },
] as const

type CameraType = (typeof CAMERA_TYPES)[number]['value']

export type CameraFormData = {
  name: string
  type: CameraType
  config: Record<string, string | number>
  is_active: boolean
}

type Props = {
  open: boolean
  onClose: () => void
  onSave: (data: CameraFormData) => Promise<void>
  initial?: { name: string; type: string; config: Record<string, string | number>; is_active: boolean }
  title?: string
}

export default function AddCameraModal({ open, onClose, onSave, initial, title }: Props) {
  const [name, setName] = useState('')
  const [camType, setCamType] = useState<CameraType>('rtsp')
  const [isActive, setIsActive] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  // Type-specific fields
  const [deviceIndex, setDeviceIndex] = useState('0')
  const [host, setHost] = useState('')
  const [port, setPort] = useState('554')
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [streamPath, setStreamPath] = useState('')
  const [streamUrl, setStreamUrl] = useState('')

  useEffect(() => {
    if (!open) return
    if (initial) {
      setName(initial.name)
      setCamType(initial.type as CameraType)
      setIsActive(initial.is_active)
      const c = initial.config || {}
      setDeviceIndex(String(c.device_index ?? '0'))
      setHost(String(c.host ?? ''))
      setPort(String(c.port ?? '554'))
      setUsername(String(c.username ?? ''))
      setPassword(String(c.password ?? ''))
      setStreamPath(String(c.path ?? ''))
      setStreamUrl(String(c.url ?? ''))
    } else {
      setName(''); setCamType('rtsp'); setIsActive(true)
      setDeviceIndex('0'); setHost(''); setPort('554')
      setUsername(''); setPassword(''); setStreamPath('')
      setStreamUrl('')
    }
    setError('')
  }, [open, initial])

  if (!open) return null

  const buildConfig = (): Record<string, string | number> => {
    switch (camType) {
      case 'webcam':
        return { device_index: parseInt(deviceIndex) || 0 }
      case 'rtsp':
        return {
          host, port: parseInt(port) || 554,
          username, password, path: streamPath,
        }
      case 'http':
        return { url: streamUrl, username, password }
      case 'hls':
        return { url: streamUrl }
    }
  }

  const handleSubmit = async () => {
    if (!name.trim()) { setError('Camera name is required'); return }
    if (camType === 'rtsp' && !host.trim()) { setError('Host is required for RTSP'); return }
    if ((camType === 'http' || camType === 'hls') && !streamUrl.trim()) { setError('Stream URL is required'); return }

    setSaving(true)
    setError('')
    try {
      await onSave({ name: name.trim(), type: camType, config: buildConfig(), is_active: isActive })
      onClose()
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Failed to save')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4" onClick={onClose}>
      <div
        className="bg-card border border-border rounded-xl w-full max-w-lg max-h-[90vh] overflow-y-auto shadow-2xl"
        onClick={e => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-border">
          <h2 className="text-base font-semibold text-white">{title ?? 'Add Camera'}</h2>
          <button onClick={onClose} className="text-text-dim hover:text-white transition-colors text-lg leading-none">&times;</button>
        </div>

        <div className="px-5 py-4 space-y-4">
          {error && (
            <div className="bg-danger/10 border border-danger/30 text-danger px-3 py-2 rounded text-sm">{error}</div>
          )}

          {/* Name */}
          <div>
            <label className="block text-xs text-text-muted uppercase tracking-wide mb-1">Camera Name</label>
            <input
              value={name} onChange={e => setName(e.target.value)}
              placeholder="e.g. Warehouse Entrance"
              className="w-full bg-surface border border-border rounded-lg px-3 py-2 text-sm text-white placeholder:text-text-dim focus:outline-none focus:border-accent"
            />
          </div>

          {/* Type */}
          <div>
            <label className="block text-xs text-text-muted uppercase tracking-wide mb-1">Camera Type</label>
            <select
              value={camType} onChange={e => setCamType(e.target.value as CameraType)}
              className="w-full bg-surface border border-border rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-accent"
            >
              {CAMERA_TYPES.map(t => <option key={t.value} value={t.value}>{t.label}</option>)}
            </select>
          </div>

          {/* Dynamic config fields */}
          <div className="border-t border-border/50 pt-4 space-y-3">
            <p className="text-xs text-text-dim uppercase tracking-wide">Connection Details</p>

            {camType === 'webcam' && (
              <Field label="Device Index" hint="0 = first webcam, 1 = second, etc."
                value={deviceIndex} onChange={setDeviceIndex} type="number" />
            )}

            {camType === 'rtsp' && (
              <>
                <Field label="Host / IP Address" value={host} onChange={setHost} placeholder="192.168.0.90" />
                <Field label="Port" value={port} onChange={setPort} type="number" placeholder="554" />
                <Field label="Username" value={username} onChange={setUsername} placeholder="admin" />
                <Field label="Password" value={password} onChange={setPassword} type="password" placeholder="••••••" />
                <Field label="Stream Path" value={streamPath} onChange={setStreamPath} placeholder="/axis-media/media.amp" hint="Path after host:port" />
              </>
            )}

            {camType === 'http' && (
              <>
                <Field label="Stream URL" value={streamUrl} onChange={setStreamUrl} placeholder="http://192.168.1.100:8080/video" />
                <Field label="Username (optional)" value={username} onChange={setUsername} />
                <Field label="Password (optional)" value={password} onChange={setPassword} type="password" />
              </>
            )}

            {camType === 'hls' && (
              <Field label="HLS Stream URL" value={streamUrl} onChange={setStreamUrl} placeholder="http://host/stream.m3u8" />
            )}
          </div>

          {/* Active toggle */}
          <label className="flex items-center gap-2 cursor-pointer">
            <input type="checkbox" checked={isActive} onChange={e => setIsActive(e.target.checked)}
              className="w-4 h-4 accent-accent" />
            <span className="text-sm text-text-muted">Camera is active</span>
          </label>
        </div>

        {/* Footer */}
        <div className="flex items-center justify-end gap-3 px-5 py-4 border-t border-border">
          <button onClick={onClose} className="px-4 py-2 text-sm text-text-muted hover:text-white transition-colors">
            Cancel
          </button>
          <button
            onClick={handleSubmit} disabled={saving}
            className="px-5 py-2 bg-accent text-black rounded-lg text-sm font-medium hover:bg-accent-soft transition-colors disabled:opacity-50"
          >
            {saving ? 'Saving...' : (initial ? 'Update Camera' : 'Add Camera')}
          </button>
        </div>
      </div>
    </div>
  )
}


function Field({ label, value, onChange, placeholder, type, hint }: {
  label: string; value: string; onChange: (v: string) => void
  placeholder?: string; type?: string; hint?: string
}) {
  return (
    <div>
      <label className="block text-xs text-text-muted mb-1">{label}</label>
      <input
        type={type ?? 'text'} value={value} onChange={e => onChange(e.target.value)}
        placeholder={placeholder}
        className="w-full bg-surface border border-border rounded-lg px-3 py-2 text-sm text-white placeholder:text-text-dim focus:outline-none focus:border-accent"
      />
      {hint && <p className="text-[11px] text-text-dim mt-0.5">{hint}</p>}
    </div>
  )
}
