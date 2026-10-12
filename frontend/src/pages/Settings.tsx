import { useState, useEffect } from 'react'
import { useAuth } from '../hooks/useAuth'
import PageHeader from '../components/PageHeader'

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="bg-card border border-border rounded-xl p-6 space-y-4">
      <h2 className="text-sm font-semibold text-white uppercase tracking-wider">{title}</h2>
      {children}
    </div>
  )
}

function Field({
  label,
  id,
  type = 'text',
  value,
  onChange,
  placeholder,
  autoComplete,
}: {
  label: string
  id?: string
  type?: string
  value: string
  onChange: (v: string) => void
  placeholder?: string
  autoComplete?: string
}) {
  const fieldId = id ?? label.toLowerCase().replace(/\s+/g, '-').replace(/[^a-z0-9-]/g, '')
  return (
    <div className="space-y-1">
      <label htmlFor={fieldId} className="text-xs text-text-muted uppercase tracking-wider">{label}</label>
      <input
        id={fieldId}
        type={type}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        autoComplete={autoComplete}
        className="w-full bg-sidebar border border-border rounded-lg px-3 py-2 text-sm text-white placeholder-text-dim focus:outline-none focus:border-accent transition-colors"
      />
    </div>
  )
}

function SaveButton({
  onClick,
  loading,
  label = 'Save changes',
}: {
  onClick: () => void
  loading: boolean
  label?: string
}) {
  return (
    <button
      onClick={onClick}
      disabled={loading}
      className="px-4 py-2 rounded-lg bg-accent text-black text-sm font-semibold hover:bg-accent/80 disabled:opacity-50 transition-colors"
    >
      {loading ? 'Saving…' : label}
    </button>
  )
}

function StatusMsg({ msg }: { msg: { type: 'success' | 'error'; text: string } | null }) {
  if (!msg) return null
  return (
    <p
      className={`text-sm mt-1 ${msg.type === 'success' ? 'text-green-400' : 'text-red-400'}`}
    >
      {msg.text}
    </p>
  )
}

// ---------------------------------------------------------------------------
// Settings page
// ---------------------------------------------------------------------------

export default function Settings() {
  const { user, login, cameras } = useAuth()

  // --- Account info state ---
  const [acctUsername, setAcctUsername] = useState(user?.username ?? '')
  const [acctEmail, setAcctEmail] = useState(user?.email ?? '')
  const [acctPassword, setAcctPassword] = useState('')
  const [acctLoading, setAcctLoading] = useState(false)
  const [acctMsg, setAcctMsg] = useState<{ type: 'success' | 'error'; text: string } | null>(null)

  // --- Change password state ---
  const [pwdCurrent, setPwdCurrent] = useState('')
  const [pwdNew, setPwdNew] = useState('')
  const [pwdConfirm, setPwdConfirm] = useState('')
  const [pwdLoading, setPwdLoading] = useState(false)
  const [pwdMsg, setPwdMsg] = useState<{ type: 'success' | 'error'; text: string } | null>(null)

  // --- Retention state ---
  const [retention, setRetention] = useState('none')
  const [retentionLoading, setRetentionLoading] = useState(false)
  const [retentionMsg, setRetentionMsg] = useState<{ type: 'success' | 'error'; text: string } | null>(null)

  // Load current retention setting on mount
  useEffect(() => {
    if (!user?.id) return
    fetch(`/api/users/${user.id}/settings`)
      .then((r) => {
        if (!r.ok) return null
        return r.json()
      })
      .then((d) => { if (d) setRetention(d.violation_auto_delete ?? 'none') })
      .catch(() => {})
  }, [user?.id])

  // --- Handlers ---

  const handleSaveAccount = async () => {
    if (!user?.id) return
    if (!acctPassword) {
      setAcctMsg({ type: 'error', text: 'Enter your current password to save changes.' })
      return
    }
    setAcctLoading(true)
    setAcctMsg(null)
    try {
      const res = await fetch(`/api/users/${user.id}/profile`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          current_password: acctPassword,
          username: acctUsername !== user.username ? acctUsername : undefined,
          email: acctEmail !== user.email ? acctEmail : undefined,
        }),
      })
      const data = await res.json()
      if (!res.ok) {
        setAcctMsg({ type: 'error', text: data.error ?? 'Failed to update.' })
      } else {
        setAcctMsg({ type: 'success', text: 'Account updated successfully.' })
        setAcctPassword('')
        // Refresh auth context so sidebar shows new username immediately
        login(data.user, cameras)
      }
    } catch {
      setAcctMsg({ type: 'error', text: 'Network error. Is the backend running?' })
    } finally {
      setAcctLoading(false)
    }
  }

  const handleChangePassword = async () => {
    if (!user?.id) return
    if (!pwdCurrent) {
      setPwdMsg({ type: 'error', text: 'Enter your current password.' })
      return
    }
    if (!pwdNew) {
      setPwdMsg({ type: 'error', text: 'Enter a new password.' })
      return
    }
    if (pwdNew !== pwdConfirm) {
      setPwdMsg({ type: 'error', text: 'New passwords do not match.' })
      return
    }
    if (pwdNew.length < 4) {
      setPwdMsg({ type: 'error', text: 'New password must be at least 4 characters.' })
      return
    }
    setPwdLoading(true)
    setPwdMsg(null)
    try {
      const res = await fetch(`/api/users/${user.id}/profile`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ current_password: pwdCurrent, new_password: pwdNew }),
      })
      const data = await res.json()
      if (!res.ok) {
        setPwdMsg({ type: 'error', text: data.error ?? 'Failed to update password.' })
      } else {
        setPwdMsg({ type: 'success', text: 'Password changed successfully.' })
        setPwdCurrent('')
        setPwdNew('')
        setPwdConfirm('')
      }
    } catch {
      setPwdMsg({ type: 'error', text: 'Network error. Is the backend running?' })
    } finally {
      setPwdLoading(false)
    }
  }

  const handleSaveRetention = async () => {
    if (!user?.id) return
    setRetentionLoading(true)
    setRetentionMsg(null)
    try {
      const res = await fetch(`/api/users/${user.id}/settings`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ violation_auto_delete: retention }),
      })
      const data = await res.json()
      if (!res.ok) {
        setRetentionMsg({ type: 'error', text: data.error ?? 'Failed to update.' })
      } else {
        setRetentionMsg({ type: 'success', text: 'Retention policy saved.' })
      }
    } catch {
      setRetentionMsg({ type: 'error', text: 'Network error. Is the backend running?' })
    } finally {
      setRetentionLoading(false)
    }
  }

  return (
    <div className="p-6 max-w-2xl mx-auto space-y-6">
      <PageHeader title="Settings" subtitle="Manage your account and preferences" />

      {/* ── Account Info ─────────────────────────────────────────── */}
      <Section title="Account Info">
        <Field
          label="Username"
          value={acctUsername}
          onChange={setAcctUsername}
          placeholder="New username"
          autoComplete="username"
        />
        <Field
          label="Email"
          type="email"
          value={acctEmail}
          onChange={setAcctEmail}
          placeholder="New email"
          autoComplete="email"
        />
        <Field
          label="Current password (required to save)"
          type="password"
          value={acctPassword}
          onChange={setAcctPassword}
          placeholder="Enter current password"
          autoComplete="current-password"
        />
        <div className="flex items-center gap-3 pt-1">
          <SaveButton onClick={handleSaveAccount} loading={acctLoading} />
          <StatusMsg msg={acctMsg} />
        </div>
        <p className="text-xs text-text-dim">User ID: {user?.id ?? '—'}</p>
      </Section>

      {/* ── Change Password ──────────────────────────────────────── */}
      <Section title="Change Password">
        <Field
          label="Current password"
          type="password"
          value={pwdCurrent}
          onChange={setPwdCurrent}
          placeholder="Current password"
          autoComplete="current-password"
        />
        <Field
          label="New password"
          type="password"
          value={pwdNew}
          onChange={setPwdNew}
          placeholder="New password"
          autoComplete="new-password"
        />
        <Field
          label="Confirm new password"
          type="password"
          value={pwdConfirm}
          onChange={setPwdConfirm}
          placeholder="Repeat new password"
          autoComplete="new-password"
        />
        <div className="flex items-center gap-3 pt-1">
          <SaveButton onClick={handleChangePassword} loading={pwdLoading} label="Change password" />
          <StatusMsg msg={pwdMsg} />
        </div>
      </Section>

      {/* ── Violation Retention ──────────────────────────────────── */}
      <Section title="Violation Retention">
        <p className="text-xs text-text-muted">
          Automatically delete violation records older than the selected period. Snapshots on disk
          are removed at the same time.
        </p>
        <div className="space-y-1">
          <label htmlFor="retention-policy" className="text-xs text-text-muted uppercase tracking-wider">Auto-delete after</label>
          <select
            id="retention-policy"
            value={retention}
            onChange={(e) => setRetention(e.target.value)}
            className="w-full bg-sidebar border border-border rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-accent transition-colors"
          >
            <option value="none">Never (keep all)</option>
            <option value="day">1 day</option>
            <option value="week">1 week</option>
            <option value="month">1 month</option>
            <option value="year">1 year</option>
          </select>
        </div>
        <div className="flex items-center gap-3 pt-1">
          <SaveButton onClick={handleSaveRetention} loading={retentionLoading} label="Save policy" />
          <StatusMsg msg={retentionMsg} />
        </div>
      </Section>
    </div>
  )
}
