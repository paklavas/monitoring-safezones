import { useState } from 'react'
import { useNavigate, NavLink } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth'

const navItems = [
  { to: '/', label: 'Dashboard', icon: HomeIcon },
  { to: '/cameras', label: 'Cameras', icon: CameraIcon },
  { to: '/incidents', label: 'Incidents', icon: AlertIcon },
  { to: '/analytics', label: 'Analytics', icon: ChartIcon },
]

function HomeIcon({ className }: { className?: string }) {
  return (
    <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6" />
    </svg>
  )
}
function CameraIcon({ className }: { className?: string }) {
  return (
    <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
    </svg>
  )
}
function AlertIcon({ className }: { className?: string }) {
  return (
    <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
    </svg>
  )
}
function ChartIcon({ className }: { className?: string }) {
  return (
    <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
    </svg>
  )
}

type NavContentProps = {
  username: string | null
  initials: string
  mobileOpen: boolean
  setMobileOpen: (v: boolean) => void
  linkClass: ({ isActive }: { isActive: boolean }) => string
  handleOpenSettings: () => void
  handleLogout: () => void
}

function NavContent({
  username, initials, setMobileOpen, linkClass, handleOpenSettings, handleLogout,
}: NavContentProps) {
  return (
    <>
      <div className="h-0.5 bg-accent shrink-0" />
      <div className="px-3 py-4 shrink-0">
        <p className="text-xs font-semibold text-white tracking-wide">Workplace Safety</p>
        <p className="text-[10px] text-text-muted mt-0.5">Helmet detection</p>
      </div>
      <nav className="flex-1 px-2 pt-2 space-y-0.5 overflow-y-auto">
        {navItems.map(({ to, label, icon: Icon }) => (
          <NavLink
            key={to}
            to={to}
            end={to === '/'}
            className={linkClass}
            onClick={() => setMobileOpen(false)}
          >
            <Icon className="w-5 h-5 shrink-0" />
            <span className="truncate">{label}</span>
          </NavLink>
        ))}
      </nav>
      <div className="shrink-0 border-t border-border px-3 py-3 space-y-2">
        <p className="text-[10px] text-text-muted">
          {new Date().toLocaleString(undefined, { dateStyle: 'short', timeStyle: 'short' })}
        </p>
        {/* User avatar — click to open Settings */}
        <div className="flex items-center w-full">
          <button
            onClick={handleOpenSettings}
            title="Open Settings"
            className="w-9 h-9 rounded-full bg-accent/20 border-2 border-accent/50 flex items-center justify-center text-accent font-semibold text-sm shrink-0 ring-2 ring-transparent hover:ring-accent/50 hover:bg-accent/30 transition-[background-color,box-shadow]"
          >
            {initials}
          </button>
          <button
            onClick={handleOpenSettings}
            className="ml-2 text-xs font-medium text-accent truncate hidden sm:block flex-1 text-left hover:text-white transition-colors"
          >
            {username}
          </button>
        </div>
        <button
          onClick={handleLogout}
          className="w-full flex items-center justify-center gap-2 px-3 py-2 mt-4 text-xs font-medium text-text-muted hover:text-danger hover:bg-danger/10 rounded-lg transition-colors "
          style={{border: '1px solid rgb(81, 22, 29)' , borderRadius: '20px', padding: '10px', fontSize:'20px'}}
        >
          <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
          </svg>
          Sign out
        </button>
      </div>
    </>
  )
}

export default function Sidebar() {
  const { username, logout } = useAuth()
  const navigate = useNavigate()
  const [mobileOpen, setMobileOpen] = useState(false)

  const handleLogout = () => {
    setMobileOpen(false)
    logout()
    navigate('/login')
  }

  const handleOpenSettings = () => {
    setMobileOpen(false)
    navigate('/settings')
  }

  const initials = username
    ? username
        .trim()
        .split(/\s+/)
        .map((s) => s[0])
        .join('')
        .toUpperCase()
        .slice(0, 2) || '?'
    : '?'

  const linkClass = ({ isActive }: { isActive: boolean }) =>
    `flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors border-l-2 ${
      isActive
        ? 'bg-accent/15 text-accent border-accent'
        : 'border-transparent text-text-muted hover:text-white hover:bg-white/5'
    }`

  return (
    <>
      {/* Mobile: hamburger */}
      <button
        onClick={() => setMobileOpen(true)}
        className="md:hidden fixed top-3 left-3 z-30 p-2 rounded-lg bg-sidebar border border-border text-text-muted hover:text-white transition-colors"
        aria-label="Open menu"
      >
        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
        </svg>
      </button>

      {/* Mobile overlay */}
      {mobileOpen && (
        <div
          className="md:hidden fixed inset-0 z-40 bg-black/60"
          onClick={() => setMobileOpen(false)}
          aria-hidden
        />
      )}

      {/* Sidebar: desktop fixed + mobile drawer */}
      <aside
        className={`
          fixed top-0 left-0 z-40 h-full w-52 flex flex-col bg-sidebar border-r border-border
          md:translate-x-0
          ${mobileOpen ? 'translate-x-0' : '-translate-x-full'}
          transition-transform duration-200 ease-out
        `}
      >
        <button
          onClick={() => setMobileOpen(false)}
          className="md:hidden absolute top-3 right-3 p-1.5 text-text-muted hover:text-white rounded"
          aria-label="Close menu"
        >
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
        <NavContent
          username={username}
          initials={initials}
          mobileOpen={mobileOpen}
          setMobileOpen={setMobileOpen}
          linkClass={linkClass}
          handleOpenSettings={handleOpenSettings}
          handleLogout={handleLogout}
        />
      </aside>
    </>
  )
}
