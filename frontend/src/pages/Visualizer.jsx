import { useState } from 'react'
import ZipUploader from '../components/ZipUploader'
import { analyzeVisualizer } from '../services/api'
import D3CodeGraph from '../components/D3CodeGraph'
import { useSession } from '../context/SessionContext'

export default function Visualizer() {
  const { sharedFile, setSharedFile } = useSession()

  const [status, setStatus] = useState('idle')
  const [error, setError] = useState(null)
  const [sessionId, setSessionId] = useState(null)
  const [graphData, setGraphData] = useState(null)
  const [headerCollapsed, setHeaderCollapsed] = useState(false)

  async function handleAnalyze() {
    if (!sharedFile) {
      alert('Please upload a ZIP file first (or upload one in Agent Ready)')
      return
    }

    setStatus('running')
    setError(null)
    setGraphData(null)
    setHeaderCollapsed(false)

    try {
      const result = await analyzeVisualizer(sharedFile)
      setSessionId(result.session_id)
      setGraphData(result.graph)
      setStatus('success')
    } catch (err) {
      setError(err.message)
      setStatus('failed')
    }
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: 'calc(100vh - 48px)' }}>

      {/* Collapsible Header */}
      {!headerCollapsed && (
        <div style={{
          background: '#161b22',
          borderBottom: '1px solid #21262d',
          padding: '10px 20px',
          display: 'flex',
          alignItems: 'center',
          gap: 16,
          flexShrink: 0,
        }}>
          <div style={{ flex: 1 }}>
            <h1 style={{ fontSize: 18, fontWeight: 700, color: '#e6edf3', margin: 0 }}>
              🕸️ Code Visualizer
            </h1>
            <p style={{ fontSize: 11, color: '#484f58', margin: 0 }}>
              {sharedFile
                ? `Using: ${sharedFile.name} — click Build Graph`
                : 'Upload a ZIP or go to Agent Ready first'}
            </p>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            {/* Show uploader only if no shared file */}
            {!sharedFile ? (
              <div style={{ width: 240 }}>
                <ZipUploader onFile={setSharedFile} disabled={status === 'running'} />
              </div>
            ) : (
              <div style={{
                display: 'flex', alignItems: 'center', gap: 8,
                background: 'rgba(63,185,80,0.08)',
                border: '1px solid rgba(63,185,80,0.25)',
                borderRadius: 8, padding: '6px 12px',
              }}>
                <div style={{ width: 7, height: 7, borderRadius: '50%', background: '#3fb950' }} />
                <span style={{ fontSize: 12, color: '#3fb950' }}>{sharedFile.name}</span>
                <span
                  onClick={() => setSharedFile(null)}
                  style={{ cursor: 'pointer', color: '#484f58', fontSize: 14, lineHeight: 1, marginLeft: 4 }}
                  title="Clear file"
                >×</span>
              </div>
            )}

            <button
              onClick={handleAnalyze}
              disabled={!sharedFile || status === 'running'}
              style={{
                padding: '10px 20px',
                background: !sharedFile || status === 'running' ? '#21262d' : '#00CED1',
                border: 'none',
                borderRadius: 8,
                color: !sharedFile || status === 'running' ? '#484f58' : '#0d1117',
                fontSize: 13,
                fontWeight: 700,
                cursor: !sharedFile || status === 'running' ? 'not-allowed' : 'pointer',
                whiteSpace: 'nowrap',
              }}
            >
              {status === 'running' ? '⏳ Analyzing...' : '▶ Build Graph'}
            </button>
          </div>

          {/* Stats */}
          {graphData?.stats && (
            <div style={{ display: 'flex', gap: 12, flexShrink: 0 }}>
              {Object.entries(graphData.stats.by_type || {}).map(([type, count]) => (
                <div key={type} style={{ textAlign: 'center' }}>
                  <div style={{ fontSize: 16, fontWeight: 700, color: '#00CED1' }}>{count}</div>
                  <div style={{ fontSize: 10, color: '#484f58', textTransform: 'capitalize' }}>{type}s</div>
                </div>
              ))}
            </div>
          )}

          {status === 'success' && (
            <button
              onClick={() => setHeaderCollapsed(true)}
              style={{ background: 'none', border: '1px solid #30363d', borderRadius: 6, padding: '6px 10px', color: '#8b949e', cursor: 'pointer', fontSize: 11, whiteSpace: 'nowrap' }}
            >
              Hide ▲
            </button>
          )}
        </div>
      )}

      {/* Collapsed bar */}
      {headerCollapsed && status === 'success' && (
        <div style={{ background: '#161b22', borderBottom: '1px solid #21262d', padding: '6px 20px', display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexShrink: 0 }}>
          <div style={{ fontSize: 12, color: '#8b949e' }}>
            🕸️ Code Visualizer — {graphData?.nodes?.length || 0} nodes · {sharedFile?.name}
          </div>
          <button
            onClick={() => setHeaderCollapsed(false)}
            style={{ background: 'none', border: '1px solid #30363d', borderRadius: 6, padding: '4px 10px', color: '#8b949e', cursor: 'pointer', fontSize: 11 }}
          >
            Show ▼
          </button>
        </div>
      )}

      {/* Error */}
      {error && (
        <div style={{ background: 'rgba(248,81,73,.1)', border: '1px solid rgba(248,81,73,.3)', borderRadius: 8, padding: '10px 16px', margin: '10px 20px', color: '#f85149', fontSize: 13, flexShrink: 0 }}>
          ✗ {error}
        </div>
      )}

      {/* Main content */}
      {status === 'success' && graphData && sessionId ? (
        <D3CodeGraph graphData={graphData} sessionId={sessionId} />
      ) : (
        <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', flexDirection: 'column', gap: 16, color: '#484f58' }}>
          <div style={{ fontSize: 64 }}>🕸️</div>
          <div style={{ fontSize: 16, fontWeight: 600, color: '#8b949e' }}>
            {sharedFile ? `${sharedFile.name} ready — click Build Graph` : 'Upload a ZIP to visualize your codebase'}
          </div>
          <div style={{ fontSize: 13, textAlign: 'center', maxWidth: 400, lineHeight: 1.6 }}>
            {sharedFile
              ? 'Your ZIP from Agent Ready is loaded. Hit Build Graph to generate the interactive graph.'
              : 'Or go to Agent Ready first — your ZIP will carry over here automatically.'}
          </div>
        </div>
      )}
    </div>
  )
}
