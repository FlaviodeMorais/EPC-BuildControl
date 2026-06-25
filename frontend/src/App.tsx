import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import AppShell from './components/layout/AppShell'
import DashboardPage from './pages/DashboardPage'
import SpoolListPage from './pages/SpoolListPage'
import SpoolDetailPage from './pages/SpoolDetailPage'
import JointListPage from './pages/JointListPage'
import MtoPage from './pages/MtoPage'
import ValvesPage from './pages/ValvesPage'
import UploadPage from './pages/UploadPage'
import LoginPage from './pages/LoginPage'

const qc = new QueryClient({ defaultOptions: { queries: { staleTime: 30_000 } } })

export default function App() {
  return (
    <QueryClientProvider client={qc}>
      <BrowserRouter>
        <Routes>
          <Route path="login" element={<LoginPage />} />
          <Route element={<AppShell />}>
            <Route index element={<Navigate to="/dashboard" replace />} />
            <Route path="dashboard"    element={<DashboardPage />} />
            <Route path="spools"       element={<SpoolListPage />} />
            <Route path="spools/:spoolId" element={<SpoolDetailPage />} />
            <Route path="joints"       element={<JointListPage />} />
            <Route path="mto"          element={<MtoPage />} />
            <Route path="valves"       element={<ValvesPage />} />
            <Route path="uploads"      element={<UploadPage />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  )
}
