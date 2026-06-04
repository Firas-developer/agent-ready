import { useState, useMemo, useRef } from 'react'
import LogViewer from '../components/LogViewer'
import { streamAgentReady } from '../services/api'
import { useSession } from '../context/SessionContext'

const PROVIDERS = [
  { value: 'azure_foundry_claude', label: '☁️ Azure Foundry Claude (default)' },
  { value: 'azure_openai',         label: '☁️ Azure OpenAI'                   },
  { value: 'claude',               label: '🤖 Claude (direct)'                },
  { value: 'openai',               label: '🤖 OpenAI (direct)'                },
]

const STATUS_COLOR = {
  PASS: '#3fb950',
  WARN: '#d29922',
  FAIL: '#f85149',
}
const STATUS_BG = {
  PASS: 'rgba(63,185,80,0.10)',
  WARN: 'rgba(210,153,34,0.10)',
  FAIL: 'rgba(248,81,73,0.10)',
}

function parseReport(text) {
  const out = {
    title: null,
    maturity: null,        // { level, name }
    score: null,           // { pass, total }
    pillars: [],           // [{ num, name, criteria: [{ id, status, name?, description }] }]
    improvements: { quickWins: [], humanDecision: [] },
  }

  // Pass 1: strip bold + headings + trailing whitespace
  let lines = (text || '').split('\n').map(raw =>
    raw.replace(/\*\*/g, '').replace(/^#+\s*/, '').trimEnd()
  )

  // Pass 2: re-join markdown-table row continuations
  // A table row starts with `|`. If a row doesn't end with `|`, the next
  // non-empty non-`|` non-`---` line is its continuation.
  const joined = []
  for (const line of lines) {
    if (joined.length > 0) {
      const prev = joined[joined.length - 1]
      const isTableRow = prev.startsWith('|')
      const incomplete = isTableRow && !prev.endsWith('|')
      const startsNewSection = line.startsWith('|')
        || /^[-=]{3,}/.test(line)
        || /^PILLAR\s+\d+/i.test(line)
        || /^IMPROVEMENT\s+PLAN/i.test(line)
        || /^MATURITY/i.test(line)
        || /^Score:/i.test(line)
      if (incomplete && !startsNewSection && line.length > 0) {
        joined[joined.length - 1] = prev + ' ' + line.trim()
        continue
      }
    }
    joined.push(line)
  }
  lines = joined

  let currentPillar = null
  let inImprovement = false
  let improvementSection = null  // 'quick' | 'human'

  const startPillar = (num, name) => {
    currentPillar = { num: +num, name: (name || `Pillar ${num}`).trim(), criteria: [] }
    out.pillars.push(currentPillar)
    inImprovement = false
  }

  for (const line of lines) {
    if (!line) continue

    if (!out.title) {
      const t = line.match(/^FASTAPI[^:]*REPORT:\s*(.+)$/i) || line.match(/^AGENT\s+READINESS\s+REPORT:?\s*(.+)$/i)
      if (t) { out.title = t[1].trim(); continue }
    }

    const m = line.match(/MATURITY:?\s*(?:Level\s*)?(\d+)\s*[—\-:]\s*(.+)/i)
    if (m) { out.maturity = { level: +m[1], name: m[2].trim() }; continue }

    const s = line.match(/Score:?\s*(\d+)\s*\/\s*(\d+)/i)
    if (s) { out.score = { pass: +s[1], total: +s[2] }; continue }

    if (/^IMPROVEMENT\s+PLAN/i.test(line)) {
      inImprovement = true
      currentPillar = null
      improvementSection = null
      continue
    }

    if (inImprovement) {
      if (/Quick\s+Wins/i.test(line)) { improvementSection = 'quick'; continue }
      if (/Human\s+Decision/i.test(line) || /Requires\s+Human/i.test(line)) { improvementSection = 'human'; continue }
      // Bullet "- item" or markdown table cell "| - item |"
      let bullet = line.match(/^\s*[-*•]\s+(.+)/)
      if (!bullet) {
        const cells = line.split('|').map(c => c.trim()).filter(Boolean)
        if (cells.length === 1 && cells[0] && !/^\s*[-=]+\s*$/.test(cells[0])) {
          bullet = [null, cells[0].replace(/^[-*•]\s*/, '')]
        }
      }
      if (bullet) {
        if (improvementSection === 'quick')   out.improvements.quickWins.push(bullet[1].trim())
        else if (improvementSection === 'human') out.improvements.humanDecision.push(bullet[1].trim())
      }
      continue
    }

    const p = line.match(/^PILLAR\s+(\d+)[\s—\-:]*(.*)$/i)
    if (p) { startPillar(p[1], p[2]); continue }

    // Markdown table row: "| 3.1 Three-layer structure | WARN | finding |"
    if (line.startsWith('|')) {
      const cells = line.split('|').map(c => c.trim())
      // first/last entries are usually empty (leading/trailing `|`)
      const inner = cells.filter((c, i) => !(i === 0 && c === '') && !(i === cells.length - 1 && c === ''))
      if (inner.length >= 2 && inner.every(c => /^[-=:\s]+$/.test(c))) continue // separator row
      // Find the column that contains "N.N ..."
      const idIdx = inner.findIndex(c => /^\d+\.\d+/.test(c))
      const statusIdx = inner.findIndex(c => /^(PASS|WARN|FAIL)\b/i.test(c))
      if (idIdx >= 0 && statusIdx > idIdx && currentPillar) {
        const idCell = inner[idIdx]
        const idMatch = idCell.match(/^(\d+)\.(\d+)\s*(.*)$/)
        if (idMatch) {
          const id = `${idMatch[1]}.${idMatch[2]}`
          const name = (idMatch[3] || '').trim()
          const status = inner[statusIdx].match(/PASS|WARN|FAIL/i)[0].toUpperCase()
          const findingCells = inner.slice(statusIdx + 1).filter(Boolean)
          const description = findingCells.join(' ').replace(/\s+/g, ' ').trim()
          currentPillar.criteria.push({ id, status, name, description })
          continue
        }
      }
    }

    // Indented format: "1.1 PASS finding..."
    const c = line.match(/^\s*(\d+)\.(\d+)[\s:.\-—\[\]]+(PASS|WARN|FAIL)[\s:.\-—\[\]]*(.*)/i)
    if (c && currentPillar) {
      currentPillar.criteria.push({
        id: `${c[1]}.${c[2]}`,
        status: c[3].toUpperCase(),
        name: '',
        description: (c[4] || '').trim(),
      })
    }
  }

  const allCriteria = out.pillars.flatMap(p => p.criteria)
  if (!out.score && allCriteria.length) {
    out.score = {
      pass: allCriteria.filter(c => c.status === 'PASS').length,
      total: allCriteria.length,
    }
  }

  return { ...out, allCriteria }
}

function DonutChart({ pass, warn, fail, total, size = 130 }) {
  const stroke = 12
  const radius = size / 2 - stroke / 2 - 2
  const cx = size / 2
  const cy = size / 2
  const circ = 2 * Math.PI * radius
  const passLen = total ? (pass / total) * circ : 0
  const warnLen = total ? (warn / total) * circ : 0
  const failLen = total ? (fail / total) * circ : 0
  const pct = total ? Math.round((pass / total) * 100) : 0

  return (
    <svg width={size} height={size} style={{ display: 'block' }}>
      <circle cx={cx} cy={cy} r={radius} fill="none" stroke="#21262d" strokeWidth={stroke} />
      {pass > 0 && (
        <circle cx={cx} cy={cy} r={radius} fill="none"
          stroke={STATUS_COLOR.PASS} strokeWidth={stroke}
          strokeDasharray={`${passLen} ${circ - passLen}`}
          transform={`rotate(-90 ${cx} ${cy})`} strokeLinecap="butt" />
      )}
      {warn > 0 && (
        <circle cx={cx} cy={cy} r={radius} fill="none"
          stroke={STATUS_COLOR.WARN} strokeWidth={stroke}
          strokeDasharray={`${warnLen} ${circ - warnLen}`}
          strokeDashoffset={-passLen}
          transform={`rotate(-90 ${cx} ${cy})`} strokeLinecap="butt" />
      )}
      {fail > 0 && (
        <circle cx={cx} cy={cy} r={radius} fill="none"
          stroke={STATUS_COLOR.FAIL} strokeWidth={stroke}
          strokeDasharray={`${failLen} ${circ - failLen}`}
          strokeDashoffset={-(passLen + warnLen)}
          transform={`rotate(-90 ${cx} ${cy})`} strokeLinecap="butt" />
      )}
      <text x={cx} y={cy - 2} textAnchor="middle" fill="#e6edf3" fontSize="22" fontWeight="700">
        {pct}%
      </text>
      <text x={cx} y={cy + 16} textAnchor="middle" fill="#8b949e" fontSize="10">
        {pass}/{total} pass
      </text>
    </svg>
  )
}

function CriterionRow({ criterion, isLast }) {
  const color = STATUS_COLOR[criterion.status] || '#484f58'
  return (
    <div style={{ position: 'relative', display: 'flex', gap: 14, paddingBottom: isLast ? 0 : 14 }}>
      {!isLast && (
        <div style={{
          position: 'absolute', left: 19, top: 38, bottom: 0,
          width: 2, background: '#21262d',
        }} />
      )}

      <div style={{
        flexShrink: 0, width: 38, height: 38, borderRadius: '50%',
        background: STATUS_BG[criterion.status] || 'transparent',
        border: `2px solid ${color}`,
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        fontSize: 12, fontWeight: 700, color,
        zIndex: 1,
      }}>
        {criterion.id}
      </div>

      <div style={{ flex: 1, paddingTop: 2 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4, flexWrap: 'wrap' }}>
          <span style={{
            fontSize: 10, fontWeight: 700, letterSpacing: '.04em',
            padding: '2px 8px', borderRadius: 4,
            color, background: STATUS_BG[criterion.status] || 'transparent',
            border: `1px solid ${color}40`,
          }}>
            {criterion.status}
          </span>
          {criterion.name && (
            <span style={{ fontSize: 12, fontWeight: 600, color: '#e6edf3' }}>
              {criterion.name}
            </span>
          )}
        </div>
        <div style={{ fontSize: 12, color: '#c9d1d9', lineHeight: 1.55 }}>
          {criterion.description || <span style={{ color: '#484f58', fontStyle: 'italic' }}>No description</span>}
        </div>
      </div>
    </div>
  )
}

function ReportView({ parsed, onDownload, onShowRaw }) {
  const all = parsed.allCriteria
  const pass = all.filter(c => c.status === 'PASS').length
  const warn = all.filter(c => c.status === 'WARN').length
  const fail = all.filter(c => c.status === 'FAIL').length
  const total = all.length
  const hasImprovements =
    parsed.improvements.quickWins.length > 0 || parsed.improvements.humanDecision.length > 0

  return (
    <div style={{
      flex: 1, minHeight: 0,
      display: 'grid', gridTemplateColumns: '1fr 260px', gap: 16,
      overflow: 'hidden',
    }}>

      {/* LEFT — criteria chain with its own scroll */}
      <div style={{
        minHeight: 0, overflowY: 'auto',
        paddingRight: 10, paddingBottom: 8,
      }}>
        {parsed.pillars.map(pillar => {
          const p = pillar.criteria.filter(c => c.status === 'PASS').length
          const w = pillar.criteria.filter(c => c.status === 'WARN').length
          const f = pillar.criteria.filter(c => c.status === 'FAIL').length
          return (
            <div key={pillar.num} style={{ marginBottom: 22 }}>
              <div style={{
                display: 'flex', alignItems: 'center', gap: 10,
                padding: '8px 12px', marginBottom: 12,
                background: 'rgba(123,104,238,0.08)',
                border: '1px solid rgba(123,104,238,0.25)',
                borderRadius: 8,
              }}>
                <div style={{
                  width: 24, height: 24, borderRadius: '50%',
                  background: '#7B68EE', color: '#fff',
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                  fontSize: 11, fontWeight: 700,
                }}>{pillar.num}</div>
                <div>
                  <div style={{ fontSize: 12, fontWeight: 700, color: '#e6edf3', letterSpacing: '.02em' }}>
                    PILLAR {pillar.num}
                  </div>
                  <div style={{ fontSize: 10, color: '#8b949e', textTransform: 'uppercase', letterSpacing: '.05em' }}>
                    {pillar.name}
                  </div>
                </div>
                <div style={{ marginLeft: 'auto', display: 'flex', gap: 8, fontSize: 10 }}>
                  {p > 0 && <span style={{ color: STATUS_COLOR.PASS }}>{p} pass</span>}
                  {w > 0 && <span style={{ color: STATUS_COLOR.WARN }}>{w} warn</span>}
                  {f > 0 && <span style={{ color: STATUS_COLOR.FAIL }}>{f} fail</span>}
                </div>
              </div>

              <div style={{ paddingLeft: 4 }}>
                {pillar.criteria.length === 0 ? (
                  <div style={{ fontSize: 11, color: '#484f58', fontStyle: 'italic', padding: '8px 0' }}>
                    No criteria parsed for this pillar
                  </div>
                ) : (
                  pillar.criteria.map((c, i) => (
                    <CriterionRow key={c.id + i} criterion={c} isLast={i === pillar.criteria.length - 1} />
                  ))
                )}
              </div>
            </div>
          )
        })}
      </div>

      {/* RIGHT — summary column, flex with internal scroll on improvements */}
      <div style={{
        display: 'flex', flexDirection: 'column', gap: 10,
        minHeight: 0, overflow: 'hidden',
      }}>
        {/* Maturity + Donut combined into one compact card */}
        <div style={{
          flexShrink: 0,
          background: '#161b22', border: '1px solid #21262d', borderRadius: 10,
          padding: '12px 14px',
          display: 'flex', alignItems: 'center', gap: 12,
        }}>
          {parsed.maturity && (
            <div style={{ flex: 1 }}>
              <div style={{ fontSize: 9, fontWeight: 700, color: '#484f58', textTransform: 'uppercase', letterSpacing: '.08em' }}>
                Maturity
              </div>
              <div style={{ fontSize: 16, fontWeight: 700, color: '#7B68EE', marginTop: 2 }}>
                L{parsed.maturity.level}
              </div>
              <div style={{ fontSize: 11, color: '#c9d1d9' }}>
                {parsed.maturity.name}
              </div>
            </div>
          )}
          <DonutChart pass={pass} warn={warn} fail={fail} total={total} size={110} />
        </div>

        {/* Legend chips */}
        <div style={{
          flexShrink: 0, display: 'flex', justifyContent: 'center',
          gap: 12, fontSize: 10,
        }}>
          <span style={{ display: 'flex', alignItems: 'center', gap: 4, color: STATUS_COLOR.PASS }}>
            <span style={{ width: 7, height: 7, borderRadius: '50%', background: STATUS_COLOR.PASS }} /> {pass}
          </span>
          <span style={{ display: 'flex', alignItems: 'center', gap: 4, color: STATUS_COLOR.WARN }}>
            <span style={{ width: 7, height: 7, borderRadius: '50%', background: STATUS_COLOR.WARN }} /> {warn}
          </span>
          <span style={{ display: 'flex', alignItems: 'center', gap: 4, color: STATUS_COLOR.FAIL }}>
            <span style={{ width: 7, height: 7, borderRadius: '50%', background: STATUS_COLOR.FAIL }} /> {fail}
          </span>
        </div>

        {/* Improvements with internal scroll */}
        <div style={{
          flex: 1, minHeight: 0,
          display: 'flex', flexDirection: 'column',
          background: '#161b22', border: '1px solid #21262d', borderRadius: 10,
          overflow: 'hidden',
        }}>
          <div style={{
            flexShrink: 0,
            padding: '10px 14px 6px',
            fontSize: 10, fontWeight: 700, color: '#484f58',
            textTransform: 'uppercase', letterSpacing: '.08em',
            borderBottom: '1px solid #21262d',
          }}>
            Improvements
          </div>
          <div style={{ flex: 1, overflowY: 'auto', padding: '10px 14px' }}>
            {parsed.improvements.quickWins.length > 0 && (
              <div style={{ marginBottom: 12 }}>
                <div style={{ fontSize: 11, fontWeight: 700, color: STATUS_COLOR.PASS, marginBottom: 6 }}>
                  ⚡ Quick Wins
                </div>
                <ul style={{ margin: 0, padding: 0, listStyle: 'none' }}>
                  {parsed.improvements.quickWins.map((item, i) => (
                    <li key={i} style={{
                      fontSize: 11, color: '#c9d1d9', lineHeight: 1.5,
                      paddingLeft: 12, position: 'relative', marginBottom: 6,
                    }}>
                      <span style={{ position: 'absolute', left: 0, top: 0, color: STATUS_COLOR.PASS }}>•</span>
                      {item}
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {parsed.improvements.humanDecision.length > 0 && (
              <div>
                <div style={{ fontSize: 11, fontWeight: 700, color: STATUS_COLOR.WARN, marginBottom: 6 }}>
                  🧭 Requires Human Decision
                </div>
                <ul style={{ margin: 0, padding: 0, listStyle: 'none' }}>
                  {parsed.improvements.humanDecision.map((item, i) => (
                    <li key={i} style={{
                      fontSize: 11, color: '#c9d1d9', lineHeight: 1.5,
                      paddingLeft: 12, position: 'relative', marginBottom: 6,
                    }}>
                      <span style={{ position: 'absolute', left: 0, top: 0, color: STATUS_COLOR.WARN }}>•</span>
                      {item}
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {!hasImprovements && (
              <div style={{ fontSize: 11, color: '#484f58', fontStyle: 'italic' }}>
                No improvement items parsed.
              </div>
            )}
          </div>
        </div>

        {/* Action buttons */}
        <div style={{ flexShrink: 0, display: 'flex', gap: 8 }}>
          <button
            onClick={onDownload}
            style={{
              flex: 1, padding: '8px',
              background: 'transparent', border: '1px solid #30363d',
              borderRadius: 8, color: '#8b949e', fontSize: 11, cursor: 'pointer',
            }}
          >
            ⬇ Download .md
          </button>
          {onShowRaw && (
            <button
              onClick={onShowRaw}
              style={{
                flex: 1, padding: '8px',
                background: 'transparent', border: '1px solid #30363d',
                borderRadius: 8, color: '#8b949e', fontSize: 11, cursor: 'pointer',
              }}
            >
              View raw
            </button>
          )}
        </div>
      </div>
    </div>
  )
}

export default function AgentReady() {
  const { sharedFile, setSharedFile } = useSession()

  const [provider, setProvider] = useState('azure_foundry_claude')
  const [logs, setLogs]         = useState([])
  const [status, setStatus]     = useState('idle')
  const [report, setReport]     = useState('')
  const [showRaw, setShowRaw]   = useState(false)

  function addLog(line) {
    setLogs(prev => [...prev, line])
    setReport(prev => prev + line + '\n')
  }

  async function handleRun() {
    if (!sharedFile) { alert('Please upload a ZIP file first'); return }
    setLogs([])
    setReport('')
    setShowRaw(false)
    setStatus('running')

    await streamAgentReady(
      sharedFile,
      provider,
      addLog,
      () => setStatus('success'),
      (err) => { addLog(`✗ Error: ${err}`); setStatus('failed') }
    )
  }

  function handleDownload() {
    const blob = new Blob([report], { type: 'text/markdown' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = 'agent-ready-report.md'
    a.click()
    URL.revokeObjectURL(url)
  }

  const parsed = useMemo(() => {
    if (status !== 'success' || !report) return null
    const p = parseReport(report)
    return p.allCriteria.length > 0 ? p : null
  }, [status, report])

  return (
    <div style={{
      maxWidth: 1280, margin: '0 auto',
      height: 'calc(100vh - 48px)',
      display: 'flex', flexDirection: 'column',
      padding: '14px 4px 12px',
      minHeight: 0,
    }}>
      {/* Top row — title left, provider right */}
      <div style={{
        display: 'flex', alignItems: 'center', gap: 14,
        marginBottom: 10, flexShrink: 0,
      }}>
        <div style={{ flex: 1 }}>
          <h1 style={{ fontSize: 20, fontWeight: 700, color: '#e6edf3', margin: 0 }}>
            🔍 Agent Ready
          </h1>
          <p style={{ color: '#8b949e', fontSize: 12, margin: '2px 0 0' }}>
            Upload your project ZIP — analysis flows automatically to Visualizer and Impact.
          </p>
        </div>
        <select
          value={provider}
          onChange={e => setProvider(e.target.value)}
          disabled={status === 'running'}
          title="LLM provider"
          style={{
            background: '#161b22', border: '1px solid #30363d',
            borderRadius: 8, padding: '7px 10px', color: '#e6edf3',
            fontSize: 12, cursor: 'pointer', minWidth: 240,
          }}
        >
          {PROVIDERS.map(p => (
            <option key={p.value} value={p.value}>{p.label}</option>
          ))}
        </select>
      </div>

      {/* Compact ZIP bar + Run button */}
      <div style={{
        display: 'flex', alignItems: 'center', gap: 10,
        marginBottom: 14, flexShrink: 0,
      }}>
        <CompactZipBar
          file={sharedFile}
          onFile={setSharedFile}
          disabled={status === 'running'}
        />
        <button
          onClick={handleRun}
          disabled={!sharedFile || status === 'running'}
          style={{
            padding: '8px 18px',
            background: status === 'running' ? '#21262d' : '#7B68EE',
            border: 'none', borderRadius: 8, color: '#fff',
            fontSize: 12, fontWeight: 700,
            cursor: !sharedFile || status === 'running' ? 'not-allowed' : 'pointer',
            whiteSpace: 'nowrap', flexShrink: 0,
          }}
        >
          {status === 'running' ? '⏳ Analyzing…' : '▶ Run Analysis'}
        </button>
      </div>

      {/* Body */}
      {status === 'idle' && (
        <div style={{
          flex: 1, minHeight: 0,
          background: '#161b22', border: '1px dashed #30363d', borderRadius: 10,
          display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center',
          color: '#484f58', textAlign: 'center', padding: 24,
        }}>
          <div style={{ fontSize: 40, marginBottom: 10 }}>📋</div>
          <div style={{ fontSize: 13, color: '#8b949e', fontWeight: 600, marginBottom: 4 }}>
            Upload a ZIP and click Run Analysis
          </div>
          <div style={{ fontSize: 11 }}>
            You'll get a maturity rating, pillar-by-pillar criteria, and an improvement plan.
          </div>
        </div>
      )}

      {status === 'running' && (
        <div style={{ flex: 1, minHeight: 0, display: 'flex', flexDirection: 'column' }}>
          <label style={{ display: 'block', fontSize: 10, color: '#8b949e', marginBottom: 6, fontWeight: 600, letterSpacing: '.04em', flexShrink: 0 }}>
            STREAMING OUTPUT
          </label>
          <div style={{ flex: 1, minHeight: 0 }}>
            <LogViewer logs={logs} status={status} />
          </div>
        </div>
      )}

      {status === 'failed' && (
        <div style={{ flex: 1, minHeight: 0, display: 'flex', flexDirection: 'column' }}>
          <div style={{
            background: 'rgba(248,81,73,.1)', border: '1px solid rgba(248,81,73,.3)',
            borderRadius: 8, padding: '8px 14px', marginBottom: 8,
            color: '#f85149', fontSize: 12, flexShrink: 0,
          }}>
            ✗ Analysis failed — see raw output below
          </div>
          <div style={{ flex: 1, minHeight: 0 }}>
            <LogViewer logs={logs} status={status} />
          </div>
        </div>
      )}

      {status === 'success' && parsed && !showRaw && (
        <ReportView
          parsed={parsed}
          onDownload={handleDownload}
          onShowRaw={() => setShowRaw(true)}
        />
      )}

      {status === 'success' && (showRaw || !parsed) && (
        <div style={{ flex: 1, minHeight: 0, display: 'flex', flexDirection: 'column' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 8, flexShrink: 0 }}>
            {parsed && (
              <button
                onClick={() => setShowRaw(false)}
                style={{
                  padding: '6px 12px', background: 'transparent',
                  border: '1px solid #30363d', borderRadius: 6,
                  color: '#8b949e', fontSize: 11, cursor: 'pointer',
                }}
              >
                ← Back to structured view
              </button>
            )}
            {!parsed && (
              <div style={{ fontSize: 11, color: '#d29922' }}>
                ⚠ Couldn't parse the report into structured criteria — showing raw output.
              </div>
            )}
            <button
              onClick={handleDownload}
              style={{
                marginLeft: 'auto', padding: '6px 12px', background: 'transparent',
                border: '1px solid #30363d', borderRadius: 6,
                color: '#8b949e', fontSize: 11, cursor: 'pointer',
              }}
            >
              ⬇ Download .md
            </button>
          </div>
          <div style={{ flex: 1, minHeight: 0 }}>
            <LogViewer logs={logs} status={status} />
          </div>
        </div>
      )}
    </div>
  )
}

function CompactZipBar({ file, onFile, disabled }) {
  const inputRef = useRef()
  const [dragging, setDragging] = useState(false)

  function handle(f) {
    if (!f) return
    if (!f.name.toLowerCase().endsWith('.zip')) { alert('Please upload a .zip file'); return }
    onFile(f)
  }

  return (
    <div
      onClick={() => !disabled && inputRef.current?.click()}
      onDragOver={e => { e.preventDefault(); if (!disabled) setDragging(true) }}
      onDragLeave={() => setDragging(false)}
      onDrop={e => { e.preventDefault(); setDragging(false); if (!disabled) handle(e.dataTransfer.files[0]) }}
      style={{
        flex: 1, display: 'flex', alignItems: 'center', gap: 10,
        padding: '6px 12px', minHeight: 36,
        background: dragging ? 'rgba(123,104,238,0.06)' : '#161b22',
        border: `1px ${dragging ? 'solid' : 'dashed'} ${dragging ? '#7B68EE' : '#30363d'}`,
        borderRadius: 8,
        cursor: disabled ? 'not-allowed' : 'pointer',
        opacity: disabled ? 0.5 : 1,
        transition: 'all 0.15s',
      }}
    >
      <input
        ref={inputRef} type="file" accept=".zip" style={{ display: 'none' }}
        onChange={e => handle(e.target.files[0])}
      />
      <span style={{ fontSize: 16 }}>📦</span>
      {file ? (
        <>
          <span style={{
            color: '#e6edf3', fontSize: 12, flex: 1,
            overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
          }}>{file.name}</span>
          <span style={{ color: '#484f58', fontSize: 10 }}>click to change</span>
        </>
      ) : (
        <span style={{ color: '#8b949e', fontSize: 12, flex: 1 }}>
          Drop ZIP here or click to browse
        </span>
      )}
    </div>
  )
}
