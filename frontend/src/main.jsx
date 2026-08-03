import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import './index.css'
import Layout from './Layout.jsx'
import HomePage from './pages/HomePage.jsx'
import HearingsPage from './pages/HearingsPage.jsx'
import CasesPage from './pages/CasesPage.jsx'
import BucketPage from './pages/BucketPage.jsx'
import MessagesView from './components/MessagesView'
import StaffView from './components/StaffView'

// Every page has its own URL, so a case can be bookmarked and sent to a
// colleague. React Router ranks static segments above dynamic ones, so
// /messages and /staff win over /:bucket without needing an explicit order.
createRoot(document.getElementById('root')).render(
  <StrictMode>
    <BrowserRouter>
      <Routes>
        <Route element={<Layout />}>
          <Route index element={<HomePage />} />
          <Route path="hearings" element={<HearingsPage />} />
          <Route path="messages" element={<MessagesView />} />
          <Route path="staff" element={<StaffView />} />
          <Route path="cases" element={<CasesPage />} />
          <Route path="cases/:area" element={<CasesPage />} />
          <Route path="cases/:area/:callId" element={<CasesPage />} />
          <Route path=":bucket" element={<BucketPage />} />
          <Route path=":bucket/:callId" element={<BucketPage />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Route>
      </Routes>
    </BrowserRouter>
  </StrictMode>,
)
