import { useEffect, useRef } from 'react'

export default function LogViewer({ logs, status }) {
  const bottomRef = useRef()

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [logs])

  const statusColor = {
    idle:    '#484f58',
    running: '#7B68EE',
    success: '#3fb950',
    failed:  '#f85149',
  }[status] || '#484f58'

  return (
    <div style={{
      background: '#010409',
      border: '1px solid #21262d',
      borderRadius: 8,
      padding: 16,
      fontFamily: "'Cascadia Code', 'Fira Code', Consolas, monospace",
      fontSize: 12,
      lineHeight: 1.6,
      height: 420,
      overflowY: 'auto',
      position: 'relative',
    }}>
      {/* Status badge */}
      <div style={{
        position: 'sticky',
        top: 0,
        background: '#010409',
        paddingBottom: 8,
        marginBottom: 4,
        borderBottom: '1px solid #21262d',
        display: 'flex',
        alignItems: 'center',
        gap: 8,
      }}>
        <span style={{
          width: 8, height: 8,
          borderRadius: '50%',
          background: statusColor,
          display: 'inline-block',
          boxShadow: status === 'running' ? `0 0 6px ${statusColor}` : 'none',
          animation: status === 'running' ? 'pulse 1.5s infinite' : 'none',
        }} />
        <span style={{ color: statusColor, fontSize: 11, fontWeight: 600, textTransform: 'uppercase' }}>
          {status}
        </span>
      </div>

      {/* Log lines */}
      {logs.length === 0 ? (
        <div style={{ color: '#484f58', fontStyle: 'italic' }}>
          Waiting for output...
        </div>
      ) : (
        logs.map((line, i) => (
          <div key={i} style={{
            color: line.startsWith('✗') || line.toLowerCase().includes('error')
              ? '#f85149'
              : line.startsWith('✓') || line.startsWith('✅')
              ? '#3fb950'
              : line.startsWith('⚠')
              ? '#d29922'
              : line.startsWith('===') || line.startsWith('---')
              ? '#7B68EE'
              : '#c9d1d9',
            whiteSpace: 'pre-wrap',
            wordBreak: 'break-word',
          }}>
            {line}
          </div>
        ))
      )}
      <div ref={bottomRef} />

      <style>{`
        @keyframes pulse {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.4; }
        }
      `}</style>
    </div>
  )
}
