import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth'

type HeaderProps = {
  title?: string
  subtitle?: string
  showBack?: boolean
  onBack?: () => void
}

export default function Header({ title = 'Workplace Safety Monitor', subtitle = 'Real-time helmet detection', showBack, onBack }: HeaderProps) {
  const { username, logout } = useAuth()
  const navigate = useNavigate()
  const now = new Date().toLocaleString(undefined, { dateStyle: 'short', timeStyle: 'medium' })
  const [menuOpen, setMenuOpen] = useState(false)

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  return (
    <header className="relative bg-header border-b border-border">
      <div className="absolute top-0 left-0 right-0 h-0.5 bg-accent" />

      <div className="flex items-center justify-between px-4 sm:px-6 h-14">
        {/* Left: back + title */}
        <div className="flex items-center gap-3 min-w-0">
          {showBack && onBack && (
            <button onClick={onBack} className="text-text-muted hover:text-white transition-colors text-sm shrink-0">
              ← Back
            </button>
          )}
          <div className="min-w-0">
            <h1 className="text-sm sm:text-base font-semibold text-white truncate">{title}</h1>
            {subtitle && <p className="text-xs text-text-muted truncate hidden sm:block">{subtitle}</p>}
          </div>
        </div>

        {/* Right: desktop nav */}
        <div className="hidden md:flex items-center gap-4 text-sm">
          <span className="text-text-muted">{now}</span>
          <button
            onClick={() => navigate('/cameras')}
            className="text-text-muted hover:text-accent transition-colors"
          >
            Cameras
          </button>
          <button
            onClick={() => navigate('/incidents')}
            className="text-text-muted hover:text-accent transition-colors"
          >
            Incidents
          </button>
          <span className="text-accent font-medium">{username}</span>
          <button onClick={handleLogout} className="text-text-muted hover:text-danger transition-colors">
            Sign out
          </button>
        </div>

        {/* Right: mobile hamburger */}
        <button
          onClick={() => setMenuOpen(o => !o)}
          className="md:hidden p-2 text-text-muted hover:text-white transition-colors"
          aria-label="Menu"
        >
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            {menuOpen
              ? <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              : <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />}
          </svg>
        </button>
      </div>

      {/* Mobile dropdown menu */}
      {menuOpen && (
        <div className="md:hidden border-t border-border bg-header px-4 py-3 space-y-3 text-sm">
          <p className="text-text-muted text-xs">{now}</p>
          <p className="text-accent font-medium">{username}</p>
          <button
            onClick={() => { navigate('/cameras'); setMenuOpen(false) }}
            className="block w-full text-left text-text-muted hover:text-accent transition-colors"
          >
            Manage Cameras
          </button>
          <button
            onClick={() => { navigate('/incidents'); setMenuOpen(false) }}
            className="block w-full text-left text-text-muted hover:text-accent transition-colors"
          >
            Incident Review
          </button>
          <button
            onClick={() => { handleLogout(); setMenuOpen(false) }}
            className="block w-full text-left text-text-muted hover:text-danger transition-colors"
          >
            Sign out
          </button>
        </div>
      )}
    </header>
  )
}
