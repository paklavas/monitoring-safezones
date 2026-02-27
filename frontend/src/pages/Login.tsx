import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth'

export default function Login() {
  const { username, login } = useAuth()
  const navigate = useNavigate()
  useEffect(() => {
    if (username) navigate('/', { replace: true })
  }, [username, navigate])

  const [mode, setMode] = useState<'login' | 'create'>('login')
  const [inputUsername, setInputUsername] = useState('')
  const [password, setPassword] = useState('')
  const [email, setEmail] = useState('')
  const [error, setError] = useState('')

  const reset = () => {
    setInputUsername('')
    setPassword('')
    setEmail('')
    setError('')
  }

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    if (!inputUsername || !password) {
      setError('Username and password required.')
      return
    }
    
    try {
      const response = await fetch('/api/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username: inputUsername, password }),
      })
      const data = await response.json()
      
      if (response.ok && data.success) {
        // Pass full user object and assigned cameras from backend
        login(data.user, data.cameras ?? [])
        navigate('/')
      } else {
        setError(data.error || 'Login failed')
      }
    } catch (err) {
      setError('Connection error. Is the backend server running?')
    }
  }

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    if (!inputUsername || !password || !email) {
      setError('All fields required.')
      return
    }
    
    try {
      const response = await fetch('/api/register', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username: inputUsername, password, email }),
      })
      const data = await response.json()
      
      if (response.ok && data.success) {
        // After registration, log in to get cameras
        const loginResp = await fetch('/api/login', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ username: inputUsername, password }),
        })
        const loginData = await loginResp.json()
        if (loginResp.ok && loginData.success) {
          login(loginData.user, loginData.cameras ?? [])
        } else {
          // Fallback: use register response data
          login(data.user, [])
        }
        navigate('/')
      } else {
        setError(data.error || 'Registration failed')
      }
    } catch (err) {
      setError('Connection error. Is the backend server running?')
    }
  }

  const switchMode = () => {
    setMode((m) => (m === 'login' ? 'create' : 'login'))
    reset()
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-surface px-4 py-8">
      <div className="w-full max-w-sm">
        {/* Card – minimalist: thin accent line, soft border */}
        <div className="bg-card border border-border rounded-lg overflow-hidden">
          <div className="h-0.5 bg-accent" />
          <form
            onSubmit={mode === 'login' ? handleLogin : handleCreate}
            className="p-6 sm:p-8 space-y-5"
          >
            <div>
              <h1 className="text-lg sm:text-xl font-semibold text-white">Workplace Safety Monitor</h1>
              <p className="text-sm text-text-muted mt-1">Sign in to continue</p>
            </div>

            <div>
              <label className="block text-xs font-medium text-text-muted mb-1.5">Username</label>
              <input
                type="text"
                value={inputUsername}
                onChange={(e) => setInputUsername(e.target.value)}
                className="w-full px-3 py-2 bg-[#1a1a1a] border border-border rounded text-white placeholder-text-dim focus:outline-none focus:border-accent/60 transition-colors"
                placeholder="Username"
                autoComplete="username"
              />
            </div>

            <div>
              <label className="block text-xs font-medium text-text-muted mb-1.5">Password</label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full px-3 py-2 bg-[#1a1a1a] border border-border rounded text-white placeholder-text-dim focus:outline-none focus:border-accent/60 transition-colors"
                placeholder="••••••••"
                autoComplete={mode === 'login' ? 'current-password' : 'new-password'}
              />
            </div>

            {mode === 'create' && (
              <div>
                <label className="block text-xs font-medium text-text-muted mb-1.5">Email</label>
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="w-full px-3 py-2 bg-[#1a1a1a] border border-border rounded text-white placeholder-text-dim focus:outline-none focus:border-accent/60 transition-colors"
                  placeholder="you@example.com"
                  autoComplete="email"
                />
              </div>
            )}

            {error && <p className="text-sm text-danger">{error}</p>}

            <div className="space-y-2 pt-1">
              <button
                type="submit"
                className="w-full py-2.5 bg-accent hover:bg-accent-soft text-black font-medium rounded transition-colors"
              >
                {mode === 'login' ? 'Sign in' : 'Create account'}
              </button>
              <button
                type="button"
                onClick={switchMode}
                className="w-full py-2 text-sm text-text-muted hover:text-white transition-colors"
              >
                {mode === 'login' ? 'Create new account' : 'Back to sign in'}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  )
}
