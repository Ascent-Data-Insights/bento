import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { AuthProvider } from './contexts/AuthContext'
import { TenantProvider } from './contexts/TenantContext'
import { TourProvider } from './contexts/TourContext'
import { TourTooltip } from './components/TourTooltip'
import { ProtectedRoute } from './components/ProtectedRoute'
import { AppLayout } from './layouts/AppLayout'
import { LoginPage } from './pages/LoginPage'
import { DashboardPage } from './pages/DashboardPage'
import { CrewSchedulePage } from './pages/CrewSchedulePage'
import { ProfileBuilderPage } from './pages/ProfileBuilderPage'
import { AdminPage } from './pages/AdminPage'
import { DataEntryPage } from './pages/DataEntryPage'

export default function App() {
  return (
    <AuthProvider>
      <TenantProvider>
        <TourProvider>
          <BrowserRouter>
            <Routes>
              <Route path="/login" element={<LoginPage />} />
              <Route element={<ProtectedRoute />}>
                <Route element={<AppLayout />}>
                  <Route path="/" element={<DashboardPage />} />
                  <Route path="/crew" element={<CrewSchedulePage />} />
                  <Route path="/onboard" element={<ProfileBuilderPage />} />
                  <Route path="/admin" element={<AdminPage />} />
                  <Route path="/data" element={<DataEntryPage />} />
                </Route>
              </Route>
            </Routes>
            <TourTooltip />
          </BrowserRouter>
        </TourProvider>
      </TenantProvider>
    </AuthProvider>
  )
}
