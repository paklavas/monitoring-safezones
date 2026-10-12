import { createContext, useContext, useState, useCallback, useMemo } from 'react'

const AUTH_KEY = 'safety_monitor_user'
const CAMERAS_KEY = 'safety_monitor_cameras'

export type UserCamera = {
  id: number
  zone_id: number
  name: string
  type: string
  is_active: boolean
}

type UserInfo = {
  id: number
  username: string
  email: string
}

type AuthContextType = {
  user: UserInfo | null
  username: string | null
  cameras: UserCamera[]
  login: (user: UserInfo, cameras: UserCamera[]) => void
  logout: () => void
  setCameras: (cameras: UserCamera[]) => void
}

const AuthContext = createContext<AuthContextType | null>(null)

function loadSession(): { user: UserInfo | null; cameras: UserCamera[] } {
  try {
    const raw = sessionStorage.getItem(AUTH_KEY)
    const camRaw = sessionStorage.getItem(CAMERAS_KEY)
    if (!raw) return { user: null, cameras: [] }
    return {
      user: JSON.parse(raw) as UserInfo,
      cameras: camRaw ? (JSON.parse(camRaw) as UserCamera[]) : [],
    }
  } catch {
    return { user: null, cameras: [] }
  }
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<UserInfo | null>(() => loadSession().user)
  const [cameras, setCamerasState] = useState<UserCamera[]>(() => loadSession().cameras)

  const login = useCallback((u: UserInfo, cams: UserCamera[]) => {
    setUser(u)
    setCamerasState(cams)
    sessionStorage.setItem(AUTH_KEY, JSON.stringify(u))
    sessionStorage.setItem(CAMERAS_KEY, JSON.stringify(cams))
  }, [])

  const logout = useCallback(() => {
    setUser(null)
    setCamerasState([])
    sessionStorage.removeItem(AUTH_KEY)
    sessionStorage.removeItem(CAMERAS_KEY)
  }, [])

  const setCameras = useCallback((cams: UserCamera[]) => {
    setCamerasState(cams)
    sessionStorage.setItem(CAMERAS_KEY, JSON.stringify(cams))
  }, [])

  const value = useMemo(
    () => ({ user, username: user?.username ?? null, cameras, login, logout, setCameras }),
    [user, cameras, login, logout, setCameras]
  )

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within AuthProvider')
  return ctx
}
