import { useNavigate } from 'react-router-dom'
import { useSession } from '../context/SessionContext'

const tools = [
  {
    path: '/agent-ready',
    icon: '🔍',
    title: 'Agent Ready',
    description: 'Upload your project ZIP once. Get L1-L5 maturity scoring across 20 criteria — then automatically flow into Visualizer and Impact analysis.',
    color: '#7B68EE',
    badge: 'Start Here',
  },
  {
    path: '/visualizer',
    icon: '🕸️',
    title: 'Code Visualizer',
    description: 'Interactive D3.js force graph of your codebase. Explore file structure, class hierarchies, function definitions, and import relationships.',
    color: '#00CED1',
    badge: 'D3 Graph',
  },
  {
    path: '/impact',
    icon: '⚡',
    title: 'Impact',
    description: 'Live blast-radius from the Ripple VS Code extension. See which functions and files are affected every time you save — streamed in real time.',
    color: '#ff8c00',
    badge: 'Live · Ripple',
  },
  // {
  //   path: '/testing',
  //   icon: '🧪',
  //   title: 'Automated Testing',
  //   description: 'Upload your project and target URL to automatically detect features and execute end-to-end tests.',
  //   color: '#3fb950',
  //   badge: 'E2E Testing',
  // },
]

export default function Dashboard() {
  const navigate = useNavigate()
  const { sharedFile } = useSession()

  return (
    <div style={{ maxWidth: 900, margin: '0 auto' }}>
      {/* Header */}
      <div style={{ marginBottom: 40 }}>
        <h1 style={{ fontSize: 28, fontWeight: 700, color: '#e6edf3', marginBottom: 8 }}>
          ⚡ Agent Code Chain
        </h1>
        <p style={{ color: '#8b949e', fontSize: 15, lineHeight: 1.6 }}>
          Upload your project ZIP once in Agent Ready — analysis flows automatically through Visualizer and Impact.
        </p>
      </div>

      {/* Flow indicator */}
      <div style={{
        background: '#161b22',
        border: '1px solid #21262d',
        borderRadius: 10,
        padding: '16px 20px',
        marginBottom: 32,
        display: 'flex',
        gap: 12,
        alignItems: 'center',
        flexWrap: 'wrap',
      }}>
        {[
          { icon: '📦', text: 'Upload ZIP',        color: '#7B68EE' },
          { icon: '→',  text: null,                color: '#484f58' },
          { icon: '🔍', text: 'Agent Ready',        color: '#7B68EE' },
          { icon: '→',  text: null,                color: '#484f58' },
          { icon: '🕸️', text: 'Visualizer',         color: '#00CED1' },
          { icon: '→',  text: null,                color: '#484f58' },
          { icon: '⚡', text: 'Impact (live)',       color: '#ff8c00' },
        ].map(({ icon, text, color }, i) => (
          text === null
            ? <span key={i} style={{ color: '#484f58', fontSize: 18 }}>{icon}</span>
            : (
              <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                <span style={{ fontSize: 16 }}>{icon}</span>
                <span style={{ fontSize: 13, color, fontWeight: 500 }}>{text}</span>
              </div>
            )
        ))}

        {sharedFile && (
          <div style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: 8 }}>
            <div style={{ width: 7, height: 7, borderRadius: '50%', background: '#3fb950', boxShadow: '0 0 6px #3fb950' }} />
            <span style={{ fontSize: 12, color: '#3fb950' }}>{sharedFile.name} loaded</span>
          </div>
        )}
      </div>

      {/* Tool Cards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: 20 }}>
        {tools.map(({ path, icon, title, description, color, badge }) => (
          <div
            key={path}
            onClick={() => navigate(path)}
            style={{
              background: '#161b22',
              border: `1px solid #21262d`,
              borderRadius: 12,
              padding: 24,
              cursor: 'pointer',
              transition: 'all 0.2s',
              position: 'relative',
              overflow: 'hidden',
            }}
            onMouseEnter={e => {
              e.currentTarget.style.borderColor = color
              e.currentTarget.style.transform = 'translateY(-2px)'
              e.currentTarget.style.boxShadow = `0 8px 24px rgba(0,0,0,0.3)`
            }}
            onMouseLeave={e => {
              e.currentTarget.style.borderColor = '#21262d'
              e.currentTarget.style.transform = 'translateY(0)'
              e.currentTarget.style.boxShadow = 'none'
            }}
          >
            <div style={{ position: 'absolute', top: 0, left: 0, right: 0, height: 3, background: color, borderRadius: '12px 12px 0 0' }} />

            <div style={{ display: 'flex', alignItems: 'flex-start', gap: 14, marginBottom: 14 }}>
              <div style={{ fontSize: 32, lineHeight: 1, background: `${color}20`, padding: 10, borderRadius: 10 }}>
                {icon}
              </div>
              <div>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
                  <h2 style={{ fontSize: 18, fontWeight: 700, color: '#e6edf3' }}>{title}</h2>
                  <span style={{ fontSize: 10, fontWeight: 600, background: `${color}20`, color, padding: '2px 8px', borderRadius: 20, border: `1px solid ${color}40` }}>
                    {badge}
                  </span>
                </div>
              </div>
            </div>

            <p style={{ color: '#8b949e', fontSize: 13, lineHeight: 1.7, marginBottom: 16 }}>
              {description}
            </p>

            <div style={{ display: 'inline-flex', alignItems: 'center', gap: 6, color, fontSize: 13, fontWeight: 600 }}>
              Open →
            </div>
          </div>
        ))}
      </div>

      {/* Provider info */}
      <div style={{ marginTop: 32, background: '#161b22', border: '1px solid #21262d', borderRadius: 10, padding: '14px 20px', display: 'flex', alignItems: 'center', gap: 12 }}>
        <span style={{ fontSize: 20 }}>🤖</span>
        <div>
          <div style={{ fontSize: 13, fontWeight: 600, color: '#e6edf3' }}>Azure AI Foundry — Claude Haiku 4.5</div>
          <div style={{ fontSize: 12, color: '#484f58' }}>Default LLM provider · Azure OpenAI available as fallback</div>
        </div>
        <div style={{ marginLeft: 'auto', width: 8, height: 8, borderRadius: '50%', background: '#3fb950', boxShadow: '0 0 6px #3fb950' }} />
      </div>
    </div>
  )
}
