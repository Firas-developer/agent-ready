import { useState } from 'react'
import ZipUploader from '../components/ZipUploader'
import LogViewer from '../components/LogViewer'
import { streamTesting } from '../services/api'

const PROVIDERS = [
  { value: 'azure_foundry_claude', label: '☁️ Azure Foundry Claude (default)' },
  { value: 'azure_openai',         label: '☁️ Azure OpenAI' },
  { value: 'claude',               label: '🤖 Claude (direct)' },
  { value: 'openai',               label: '🤖 OpenAI (direct)' },
]

export default function Testing() {
  const [file, setFile] = useState(null)
  const [appUrl, setAppUrl] = useState('')
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [provider, setProvider] = useState('azure_foundry_claude')
  const [logs, setLogs] = useState([])
  const [status, setStatus] = useState('idle')
  const [features, setFeatures] = useState([])
  const [report, setReport] = useState(null)
  const [activeTab, setActiveTab] = useState('logs')
  
  // JSON parsing states
  const [collectingFeatures, setCollectingFeatures] = useState(false)
  const [collectingReport, setCollectingReport] = useState(false)
  const [featuresBuffer, setFeaturesBuffer] = useState('')
  const [reportBuffer, setReportBuffer] = useState('')

  function addLog(line) {
    setLogs(prev => [...prev, line])
    
    // Detect features JSON marker
    if (line.includes('__FEATURES_JSON__')) {
      setCollectingFeatures(true)
      setFeaturesBuffer('')
      return
    }
    
    // Detect report JSON marker
    if (line.includes('__REPORT_JSON__')) {
      setCollectingReport(true)
      setReportBuffer('')
      return
    }
    
    // Collect features JSON
    if (collectingFeatures) {
      const jsonLine = line.replace('data: ', '').trim()
      if (jsonLine && jsonLine !== '[DONE]') {
        setFeaturesBuffer(prev => prev + jsonLine)
        
        // Try to parse when we have complete JSON
        if (jsonLine.includes(']')) {
          try {
            const parsed = JSON.parse(featuresBuffer + jsonLine)
            if (Array.isArray(parsed) && parsed.length > 0) {
              setFeatures(parsed)
              setActiveTab('features')
              setCollectingFeatures(false)
            }
          } catch (e) {
            // Continue collecting
          }
        }
      }
    }
    
    // Collect report JSON
    if (collectingReport) {
      const jsonLine = line.replace('data: ', '').trim()
      if (jsonLine && jsonLine !== '[DONE]') {
        setReportBuffer(prev => prev + jsonLine)
        
        // Try to parse when we have complete JSON
        if (jsonLine.includes('}') && reportBuffer.includes('"session_id"')) {
          try {
            const parsed = JSON.parse(reportBuffer + jsonLine)
            if (parsed.total_features !== undefined) {
              setReport(parsed)
              setActiveTab('results')
              setCollectingReport(false)
            }
          } catch (e) {
            // Continue collecting
          }
        }
      }
    }
  }

  async function handleRun() {
    if (!file) { alert('Please upload a ZIP file first'); return }
    if (!appUrl) { alert('Please enter application URL'); return }
    
    setLogs([])
    setFeatures([])
    setReport(null)
    setStatus('running')
    setActiveTab('logs')
    setCollectingFeatures(false)
    setCollectingReport(false)
    setFeaturesBuffer('')
    setReportBuffer('')

    await streamTesting(
      file,
      appUrl,
      username,
      password,
      provider,
      (line) => addLog(line),
      () => setStatus('success'),
      (err) => { addLog(`✗ Error: ${err}`); setStatus('failed') }
    )
  }

  // Get feature status from report
  function getFeatureStatus(featureId) {
    if (!report || !report.test_results) return 'pending'
    const result = report.test_results[featureId]
    return result?.status || 'pending'
  }

  return (
    <div style={{ maxWidth: 1400, margin: '0 auto' }}>
      {/* Header */}
      <div style={{ marginBottom: 24 }}>
        <h1 style={{ fontSize: 24, fontWeight: 700, color: '#e6edf3', marginBottom: 6 }}>
          🧪 Automated Testing
        </h1>
        <p style={{ color: '#8b949e', fontSize: 14 }}>
          Upload project ZIP, provide target URL, and run automated feature detection + test execution.
        </p>
      </div>

      {/* Configuration Panel */}
      <div style={{
        background: '#161b22',
        border: '1px solid #21262d',
        borderRadius: 10,
        padding: 20,
        marginBottom: 20,
      }}>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 20, marginBottom: 16 }}>
          <div>
            <label style={{ display: 'block', fontSize: 12, color: '#8b949e', marginBottom: 8, fontWeight: 600 }}>
              PROJECT ZIP
            </label>
            <ZipUploader onFile={setFile} disabled={status === 'running'} />
          </div>

          <div>
            <label style={{ display: 'block', fontSize: 12, color: '#8b949e', marginBottom: 8, fontWeight: 600 }}>
              LLM PROVIDER
            </label>
            <select
              value={provider}
              onChange={e => setProvider(e.target.value)}
              disabled={status === 'running'}
              style={{
                width: '100%',
                background: '#0d1117',
                border: '1px solid #30363d',
                borderRadius: 8,
                padding: '10px 12px',
                color: '#e6edf3',
                fontSize: 13,
                cursor: 'pointer',
              }}
            >
              {PROVIDERS.map(p => (
                <option key={p.value} value={p.value}>{p.label}</option>
              ))}
            </select>
          </div>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr 1fr', gap: 12 }}>
          <div>
            <label style={{ display: 'block', fontSize: 12, color: '#8b949e', marginBottom: 6, fontWeight: 600 }}>
              APPLICATION URL *
            </label>
            <input
              type="text"
              value={appUrl}
              onChange={e => setAppUrl(e.target.value)}
              placeholder="http://localhost:3000"
              disabled={status === 'running'}
              style={{
                width: '100%',
                background: '#0d1117',
                border: '1px solid #30363d',
                borderRadius: 6,
                padding: '8px 12px',
                color: '#e6edf3',
                fontSize: 13,
                outline: 'none',
              }}
            />
          </div>
          <div>
            <label style={{ display: 'block', fontSize: 12, color: '#8b949e', marginBottom: 6, fontWeight: 600 }}>
              USERNAME (Optional)
            </label>
            <input
              type="text"
              value={username}
              onChange={e => setUsername(e.target.value)}
              placeholder="admin"
              disabled={status === 'running'}
              style={{
                width: '100%',
                background: '#0d1117',
                border: '1px solid #30363d',
                borderRadius: 6,
                padding: '8px 12px',
                color: '#e6edf3',
                fontSize: 13,
                outline: 'none',
              }}
            />
          </div>
          <div>
            <label style={{ display: 'block', fontSize: 12, color: '#8b949e', marginBottom: 6, fontWeight: 600 }}>
              PASSWORD (Optional)
            </label>
            <input
              type="password"
              value={password}
              onChange={e => setPassword(e.target.value)}
              placeholder="••••••"
              disabled={status === 'running'}
              style={{
                width: '100%',
                background: '#0d1117',
                border: '1px solid #30363d',
                borderRadius: 6,
                padding: '8px 12px',
                color: '#e6edf3',
                fontSize: 13,
                outline: 'none',
              }}
            />
          </div>
        </div>

        <button
          onClick={handleRun}
          disabled={!file || !appUrl || status === 'running'}
          style={{
            width: '100%',
            marginTop: 16,
            padding: '12px',
            background: (!file || !appUrl || status === 'running') ? '#21262d' : '#00CED1',
            border: 'none',
            borderRadius: 8,
            color: (!file || !appUrl || status === 'running') ? '#484f58' : '#0d1117',
            fontSize: 14,
            fontWeight: 600,
            cursor: (!file || !appUrl || status === 'running') ? 'not-allowed' : 'pointer',
          }}
        >
          {status === 'running' ? '⚙ Running Tests...' : '▶ Start Testing Workflow'}
        </button>
      </div>

      {/* Summary Cards - Show when report exists */}
      {report && (
        <>
          <div style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(4, 1fr)',
            gap: 16,
            marginBottom: 20,
          }}>
            <div style={{
              background: '#161b22',
              border: '1px solid #30363d',
              borderRadius: 10,
              padding: '20px',
              textAlign: 'center',
            }}>
              <div style={{ fontSize: 36, fontWeight: 700, color: '#00CED1', marginBottom: 6 }}>
                {report.total_features}
              </div>
              <div style={{ fontSize: 11, color: '#8b949e', textTransform: 'uppercase', letterSpacing: '.08em', fontWeight: 600 }}>
                Features
              </div>
            </div>
            <div style={{
              background: '#1a472a',
              border: '1px solid #3fb950',
              borderRadius: 10,
              padding: '20px',
              textAlign: 'center',
            }}>
              <div style={{ fontSize: 36, fontWeight: 700, color: '#3fb950', marginBottom: 6 }}>
                {report.passed}
              </div>
              <div style={{ fontSize: 11, color: '#8b949e', textTransform: 'uppercase', letterSpacing: '.08em', fontWeight: 600 }}>
                Passed
              </div>
            </div>
            <div style={{
              background: '#4c1d1d',
              border: '1px solid #f85149',
              borderRadius: 10,
              padding: '20px',
              textAlign: 'center',
            }}>
              <div style={{ fontSize: 36, fontWeight: 700, color: '#f85149', marginBottom: 6 }}>
                {report.failed}
              </div>
              <div style={{ fontSize: 11, color: '#8b949e', textTransform: 'uppercase', letterSpacing: '.08em', fontWeight: 600 }}>
                Failed
              </div>
            </div>
            <div style={{
              background: '#4d4018',
              border: '1px solid #d29922',
              borderRadius: 10,
              padding: '20px',
              textAlign: 'center',
            }}>
              <div style={{ fontSize: 36, fontWeight: 700, color: '#d29922', marginBottom: 6 }}>
                {report.skipped}
              </div>
              <div style={{ fontSize: 11, color: '#8b949e', textTransform: 'uppercase', letterSpacing: '.08em', fontWeight: 600 }}>
                Skipped
              </div>
            </div>
          </div>

          {/* Pass Rate Bar */}
          <div style={{
            background: '#161b22',
            border: '1px solid #21262d',
            borderRadius: 10,
            padding: '20px 24px',
            marginBottom: 20,
          }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 12 }}>
              <span style={{ fontSize: 13, fontWeight: 600, color: '#8b949e', textTransform: 'uppercase', letterSpacing: '.05em' }}>
                Pass Rate
              </span>
              <span style={{ fontSize: 32, fontWeight: 700, color: '#00CED1' }}>
                {report.pass_rate.toFixed(1)}%
              </span>
            </div>
            
            <div style={{
              position: 'relative',
              height: 14,
              background: '#0d1117',
              borderRadius: 7,
              overflow: 'hidden',
              border: '1px solid #21262d',
            }}>
              <div style={{
                position: 'absolute',
                left: 0,
                top: 0,
                bottom: 0,
                width: `${report.pass_rate}%`,
                background: report.pass_rate >= 80 
                  ? 'linear-gradient(90deg, #3fb950 0%, #4ade80 100%)' 
                  : report.pass_rate >= 50 
                  ? 'linear-gradient(90deg, #d29922 0%, #f59e0b 100%)' 
                  : 'linear-gradient(90deg, #f85149 0%, #ef4444 100%)',
                transition: 'width 0.8s ease-out',
                boxShadow: report.pass_rate >= 80 
                  ? '0 0 10px rgba(63,185,80,0.4)' 
                  : report.pass_rate >= 50 
                  ? '0 0 10px rgba(210,153,34,0.4)' 
                  : '0 0 10px rgba(248,81,73,0.4)',
              }} />
              
              <div style={{
                position: 'absolute',
                left: `${Math.min(report.pass_rate, 95)}%`,
                top: '50%',
                transform: 'translate(-50%, -50%)',
                fontSize: 10,
                fontWeight: 700,
                color: report.pass_rate > 10 ? '#fff' : '#8b949e',
                textShadow: report.pass_rate > 10 ? '0 1px 2px rgba(0,0,0,0.8)' : 'none',
                zIndex: 1,
              }}>
                {report.pass_rate.toFixed(0)}%
              </div>
            </div>
            
            <div style={{
              display: 'flex',
              justifyContent: 'space-between',
              marginTop: 8,
              fontSize: 10,
              color: '#484f58',
              fontWeight: 600,
            }}>
              <span>0%</span>
              <span>25%</span>
              <span>50%</span>
              <span>75%</span>
              <span>100%</span>
            </div>
          </div>
        </>
      )}

      {/* Tabs */}
      <div style={{
        display: 'flex',
        gap: 8,
        marginBottom: 16,
        borderBottom: '1px solid #21262d',
        paddingBottom: 0,
      }}>
        {['logs', 'features', 'results'].map(tab => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            style={{
              padding: '10px 20px',
              background: activeTab === tab ? '#161b22' : 'transparent',
              border: 'none',
              borderBottom: activeTab === tab ? '2px solid #00CED1' : '2px solid transparent',
              color: activeTab === tab ? '#00CED1' : '#8b949e',
              fontSize: 13,
              fontWeight: 600,
              cursor: 'pointer',
              transition: 'all 0.2s',
            }}
          >
            {tab === 'logs' && `📝 Logs (${logs.length})`}
            {tab === 'features' && `📊 Features (${features.length})`}
            {tab === 'results' && `🧪 Results ${report ? `(${report.total_features})` : ''}`}
          </button>
        ))}
      </div>

      {/* Tab Content */}
      {activeTab === 'logs' && (
        <LogViewer logs={logs} status={status} />
      )}

      {activeTab === 'features' && (
        <div style={{
          background: '#161b22',
          border: '1px solid #21262d',
          borderRadius: 8,
          padding: 16,
          minHeight: 400,
        }}>
          {features.length === 0 ? (
            <div style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              height: 400,
              color: '#484f58',
              fontSize: 14,
            }}>
              No features detected yet. Run the workflow to detect features.
            </div>
          ) : (
            <div style={{ display: 'grid', gap: 12, maxHeight: 600, overflowY: 'auto', paddingRight: 8 }}>
              {features.map((feature, i) => {
                const featureStatus = getFeatureStatus(feature.id)
                const statusColors = {
                  passed: { bg: '#1a472a', border: '#3fb950', text: '#3fb950', icon: '✅' },
                  failed: { bg: '#4c1d1d', border: '#f85149', text: '#f85149', icon: '❌' },
                  skipped: { bg: '#4d4018', border: '#d29922', text: '#d29922', icon: '⏩' },
                  pending: { bg: '#161b22', border: '#30363d', text: '#8b949e', icon: '⏸️' },
                }
                const colors = statusColors[featureStatus] || statusColors.pending
                
                return (
                  <div
                    key={i}
                    style={{
                      background: colors.bg,
                      border: `1px solid ${colors.border}`,
                      borderRadius: 8,
                      padding: 16,
                      transition: 'all 0.3s',
                    }}
                  >
                    <div style={{ display: 'flex', alignItems: 'start', gap: 12, marginBottom: 8 }}>
                      <div style={{
                        width: 32,
                        height: 32,
                        borderRadius: 6,
                        background: 'rgba(0,0,0,0.2)',
                        border: `1px solid ${colors.border}`,
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        fontSize: 14,
                        flexShrink: 0,
                        fontWeight: 700,
                        color: colors.text,
                      }}>
                        {i + 1}
                      </div>
                      <div style={{ flex: 1 }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
                          <h3 style={{ fontSize: 15, fontWeight: 600, color: '#e6edf3' }}>
                            {feature.name}
                          </h3>
                          <span style={{
                            fontSize: 10,
                            fontWeight: 600,
                            background: 'rgba(0,0,0,0.3)',
                            color: colors.text,
                            padding: '2px 8px',
                            borderRadius: 12,
                            textTransform: 'uppercase',
                          }}>
                            {feature.type}
                          </span>
                          {feature.priority && (
                            <span style={{
                              fontSize: 10,
                              fontWeight: 600,
                              background: feature.priority === 'high' ? '#f8514920' : '#d2992220',
                              color: feature.priority === 'high' ? '#f85149' : '#d29922',
                              padding: '2px 8px',
                              borderRadius: 12,
                              textTransform: 'uppercase',
                            }}>
                              {feature.priority}
                            </span>
                          )}
                          {featureStatus !== 'pending' && (
                            <span style={{ fontSize: 18, marginLeft: 'auto' }}>
                              {colors.icon}
                            </span>
                          )}
                        </div>
                        <p style={{ fontSize: 13, color: '#8b949e', marginBottom: 8, lineHeight: 1.6 }}>
                          {feature.description}
                        </p>
                        {feature.entry_point && (
                          <div style={{
                            fontSize: 11,
                            color: '#484f58',
                            fontFamily: "'Cascadia Code', monospace",
                          }}>
                            🔗 Entry: {feature.entry_point}
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                )
              })}
            </div>
          )}
        </div>
      )}

      {activeTab === 'results' && (
        <div style={{
          background: '#161b22',
          border: '1px solid #21262d',
          borderRadius: 8,
          padding: 16,
          minHeight: 400,
        }}>
          {!report ? (
            <div style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              height: 400,
              color: '#484f58',
              fontSize: 14,
            }}>
              No test results yet. Run the workflow to execute tests.
            </div>
          ) : (
            <div style={{ maxHeight: 600, overflowY: 'auto', paddingRight: 8 }}>
              <div style={{ display: 'grid', gap: 12 }}>
                {report.features && report.features.map((feature, i) => {
                  const testResult = report.test_results?.[feature.id]
                  const statusColors = {
                    passed: { bg: '#1a472a', border: '#3fb950', text: '#3fb950', emoji: '✅' },
                    failed: { bg: '#4c1d1d', border: '#f85149', text: '#f85149', emoji: '❌' },
                    skipped: { bg: '#4d4018', border: '#d29922', text: '#d29922', emoji: '⏩' },
                  }
                  const statusInfo = statusColors[testResult?.status || 'skipped']
                  
                  return (
                    <div
                      key={i}
                      style={{
                        background: statusInfo.bg,
                        border: `1px solid ${statusInfo.border}`,
                        borderRadius: 8,
                        padding: 16,
                      }}
                    >
                      <div style={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: 12,
                        marginBottom: 12,
                      }}>
                        <span style={{ fontSize: 28 }}>{statusInfo.emoji}</span>
                        <div style={{ flex: 1 }}>
                          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 2 }}>
                            <h4 style={{ fontSize: 15, fontWeight: 600, color: '#e6edf3' }}>
                              {feature.name}
                            </h4>
                            <span style={{
                              fontSize: 10,
                              fontWeight: 600,
                              background: 'rgba(0,0,0,0.3)',
                              color: statusInfo.text,
                              padding: '2px 8px',
                              borderRadius: 12,
                              textTransform: 'uppercase',
                            }}>
                              {testResult?.status || 'not run'}
                            </span>
                          </div>
                          <div style={{ fontSize: 11, color: '#8b949e' }}>
                            {feature.type} · {feature.priority} priority
                            {testResult?.duration_ms && ` · ${testResult.duration_ms}ms`}
                          </div>
                        </div>
                      </div>

                      {testResult?.commands && testResult.commands.length > 0 && (
                        <div style={{ marginBottom: 8 }}>
                          <div style={{ fontSize: 11, color: '#484f58', marginBottom: 6 }}>
                            {testResult.commands.length} commands executed:
                          </div>
                          <div style={{ display: 'grid', gap: 4 }}>
                            {testResult.commands.map((cmd, idx) => (
                              <div
                                key={idx}
                                style={{
                                  fontSize: 11,
                                  color: cmd.success ? '#3fb950' : '#f85149',
                                  fontFamily: "'Cascadia Code', monospace",
                                  padding: '6px 10px',
                                  background: 'rgba(0,0,0,0.2)',
                                  borderRadius: 4,
                                  borderLeft: `2px solid ${cmd.success ? '#3fb950' : '#f85149'}`,
                                }}
                              >
                                {cmd.success ? '✓' : '✗'} {cmd.description}
                              </div>
                            ))}
                          </div>
                        </div>
                      )}

                      {testResult?.error && (
                        <div style={{
                          background: 'rgba(248,81,73,.15)',
                          border: '1px solid rgba(248,81,73,.4)',
                          borderRadius: 6,
                          padding: '10px 12px',
                          fontSize: 12,
                          color: '#f85149',
                          fontFamily: "'Cascadia Code', monospace",
                        }}>
                          <strong>Error:</strong> {testResult.error}
                        </div>
                      )}
                    </div>
                  )
                })}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
