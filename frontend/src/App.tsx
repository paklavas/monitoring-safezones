import { Routes, Route, Navigate } from 'react-router-dom'
import { useAuth } from './hooks/useAuth'
import Login from './pages/Login'
import Dashboard from './pages/Dashboard'
import CameraDetail from './pages/CameraDetail'
import ManageCameras from './pages/ManageCameras'
import Incidents from './pages/Incidents'

function Protected({ children }: { children: React.ReactNode }) {
  const { username } = useAuth()
  if (!username) return <Navigate to="/login" replace />
  return <>{children}</>
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/" element={<Protected><Dashboard /></Protected>} />
      <Route path="/camera/:cameraId" element={<Protected><CameraDetail /></Protected>} />
      <Route path="/cameras" element={<Protected><ManageCameras /></Protected>} />
      <Route path="/incidents" element={<Protected><Incidents /></Protected>} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}
