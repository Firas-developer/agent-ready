import { NavLink } from 'react-router-dom'

const links = [
  { to: '/',            icon: '🏠', label: 'Dashboard'    },
  { to: '/agent-ready', icon: '🔍', label: 'Agent Ready'  },
  { to: '/visualizer',  icon: '🕸️', label: 'Visualizer'   },
  { to: '/impact',      icon: '⚡', label: 'Impact'       },
  // { to: '/testing',  icon: '🧪', label: 'Testing'      },
]

export default function Sidebar() {
  return (
    <nav style={{
      width: 220,
      background: '#161b22',
      borderRight: '1px solid #21262d',
      display: 'flex',
      flexDirection: 'column',
      padding: '16px 0',
      flexShrink: 0,
    }}>
      {/* Logo */}
      <div style={{
        padding: '0 16px 20px',
        borderBottom: '1px solid #21262d',
        marginBottom: 8,
      }}>
        <div style={{ fontSize: 16, fontWeight: 700, color: '#7B68EE' }}>
          ⚡ Agent Code Chain
        </div>
        <div style={{ fontSize: 11, color: '#484f58', marginTop: 2 }}>
          AI Dev Tools Suite
        </div>
      </div>

      {/* Nav Links */}
      {links.map(({ to, icon, label }) => (
        <NavLink
          key={to}
          to={to}
          end={to === '/'}
          style={({ isActive }) => ({
            display: 'flex',
            alignItems: 'center',
            gap: 10,
            padding: '10px 16px',
            color: isActive ? '#7B68EE' : '#8b949e',
            background: isActive ? 'rgba(123,104,238,0.1)' : 'transparent',
            borderLeft: isActive ? '3px solid #7B68EE' : '3px solid transparent',
            textDecoration: 'none',
            fontSize: 13,
            fontWeight: isActive ? 600 : 400,
            transition: 'all 0.15s',
          })}
        >
          <span style={{ fontSize: 16 }}>{icon}</span>
          {label}
        </NavLink>
      ))}

      {/* Footer */}
      <div style={{
        marginTop: 'auto',
        padding: '12px 16px',
        borderTop: '1px solid #21262d',
        fontSize: 10,
        color: '#484f58',
      }}>
        FastAPI + React
      </div>
    </nav>
  )
}
