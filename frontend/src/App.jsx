import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { SessionProvider } from './context/SessionContext'
import Layout from './components/Layout'
import Dashboard from './pages/Dashboard'
import AgentReady from './pages/AgentReady'
import Visualizer from './pages/Visualizer'
import Impact from './pages/Impact'
// import Testing from './pages/Testing'

export default function App() {
  return (
    <SessionProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<Layout />}>
            <Route index element={<Dashboard />} />
            <Route path="agent-ready" element={<AgentReady />} />
            <Route path="visualizer" element={<Visualizer />} />
            <Route path="impact" element={<Impact />} />
            {/* <Route path="testing" element={<Testing />} /> */}
            <Route path="*" element={<Navigate to="/" replace />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </SessionProvider>
  )
}
