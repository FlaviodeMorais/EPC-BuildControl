import { Outlet, Navigate } from 'react-router-dom'
import Sidebar from './Sidebar'

export default function AppShell() {
  const token = localStorage.getItem('token')
  if (!token) return <Navigate to="/login" replace />

  return (
    <div className="flex min-h-screen bg-gray-50">
      <Sidebar />
      <main className="flex-1 overflow-auto p-6">
        <Outlet />
      </main>
    </div>
  )
}
