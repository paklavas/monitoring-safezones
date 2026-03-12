import { Outlet } from 'react-router-dom'
import Sidebar from './Sidebar'

export default function AppLayout() {
  return (
    <div className="flex h-screen bg-surface">
      <Sidebar />
      {/* Main: offset by sidebar width on desktop; top padding on mobile for hamburger */}
      <main className="flex-1 min-w-0 flex flex-col pt-12 md:pt-0 md:pl-52">
        <Outlet />
      </main>
    </div>
  )
}
