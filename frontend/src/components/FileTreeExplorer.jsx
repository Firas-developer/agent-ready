import { useState } from 'react'

const fileIcon = (ext) => {
  const icons = {
    py: '🐍', js: '📜', jsx: '⚛', ts: '🔷', tsx: '⚛',
    json: '📋', yaml: '⚙', yml: '⚙', md: '📝', css: '🎨',
    html: '🌐', sh: '💻', env: '🔐', toml: '⚙', txt: '📄',
    sql: '🗃', lock: '🔒', ini: '⚙', cfg: '⚙', conf: '⚙',
  }
  return icons[ext] || '📄'
}

function TreeItem({ node, depth, onSelect, selectedPath, allNodes }) {
  const [open, setOpen] = useState(depth < 2)
  const isSelected = selectedPath === node.path

  if (node.type === 'folder') {
    // Find children
    const children = allNodes.filter(n => {
      if (n.path === node.path) return false
      const parentPath = n.path.includes('/') ? n.path.substring(0, n.path.lastIndexOf('/')) : ''
      return parentPath === node.path
    }).sort((a, b) => {
      if (a.type === b.type) return a.label.localeCompare(b.label)
      return a.type === 'folder' ? -1 : 1
    })

    return (
      <div>
        <div
          onClick={() => setOpen(o => !o)}
          style={{
            display: 'flex', alignItems: 'center', gap: 5,
            padding: '3px 6px', paddingLeft: depth * 14 + 4,
            cursor: 'pointer', fontSize: 12, color: '#c9d1d9',
            userSelect: 'none',
            background: isSelected ? '#1f2937' : 'transparent',
          }}
          onMouseEnter={e => e.currentTarget.style.background = isSelected ? '#1f2937' : '#161b22'}
          onMouseLeave={e => e.currentTarget.style.background = isSelected ? '#1f2937' : 'transparent'}
        >
          <span style={{
            fontSize: 10, color: '#484f58', width: 10,
            display: 'inline-block',
            transform: open ? 'rotate(90deg)' : 'none',
            transition: 'transform .15s'
          }}>›</span>
          <span>📁</span>
          <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', flex: 1 }}>
            {node.label}
          </span>
        </div>
        {open && children.map(child => (
          <TreeItem
            key={child.id}
            node={child}
            depth={depth + 1}
            onSelect={onSelect}
            selectedPath={selectedPath}
            allNodes={allNodes}
          />
        ))}
      </div>
    )
  }

  const ext = node.label.split('.').pop().toLowerCase()

  return (
    <div
      onClick={() => onSelect(node)}
      style={{
        display: 'flex', alignItems: 'center', gap: 5,
        padding: '3px 6px', paddingLeft: depth * 14 + 4,
        cursor: 'pointer', fontSize: 12,
        color: isSelected ? '#7B68EE' : '#c9d1d9',
        background: isSelected ? '#1f2937' : 'transparent',
        borderLeft: isSelected ? '2px solid #7B68EE' : '2px solid transparent',
      }}
      onMouseEnter={e => { if (!isSelected) e.currentTarget.style.background = '#161b22' }}
      onMouseLeave={e => { if (!isSelected) e.currentTarget.style.background = 'transparent' }}
    >
      <span>{fileIcon(ext)}</span>
      <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', flex: 1 }}>
        {node.label}
      </span>
    </div>
  )
}

export default function FileTreeExplorer({ nodes, onFileSelect, selectedPath }) {
  const [search, setSearch] = useState('')

  // Build root-level items
  const rootItems = nodes
    .filter(n => !n.path.includes('/'))
    .sort((a, b) => {
      if (a.type === b.type) return a.label.localeCompare(b.label)
      return a.type === 'folder' ? -1 : 1
    })

  // Filter by search
  const filtered = search
    ? nodes.filter(n => n.label.toLowerCase().includes(search.toLowerCase()) || n.path.toLowerCase().includes(search.toLowerCase()))
    : rootItems

  return (
    <div style={{
      width: 280, flexShrink: 0, background: '#161b22',
      borderRight: '1px solid #21262d',
      display: 'flex', flexDirection: 'column',
      overflow: 'hidden',
    }}>
      {/* Header */}
      <div style={{
        padding: '10px 12px',
        borderBottom: '1px solid #21262d',
        fontSize: 11, fontWeight: 700,
        color: '#8b949e', letterSpacing: '.05em',
        textTransform: 'uppercase',
      }}>
        📁 Explorer
      </div>

      {/* Search */}
      <div style={{ padding: '8px 12px', borderBottom: '1px solid #21262d' }}>
        <input
          value={search}
          onChange={e => setSearch(e.target.value)}
          placeholder="Search files..."
          style={{
            width: '100%', background: '#0d1117',
            border: '1px solid #30363d',
            borderRadius: 6, padding: '6px 10px',
            color: '#e6edf3', fontSize: 12,
            outline: 'none',
          }}
        />
      </div>

      {/* Tree */}
      <div style={{ flex: 1, overflow: 'auto', padding: '8px 0' }}>
        {search ? (
          // Flat filtered list
          filtered.slice(0, 100).map(node => (
            <div
              key={node.id}
              onClick={() => node.type === 'file' && onFileSelect(node)}
              style={{
                display: 'flex', alignItems: 'center', gap: 5,
                padding: '3px 12px', cursor: 'pointer',
                fontSize: 12, color: '#c9d1d9',
              }}
              onMouseEnter={e => e.currentTarget.style.background = '#161b22'}
              onMouseLeave={e => e.currentTarget.style.background = 'transparent'}
            >
              <span>{node.type === 'folder' ? '📁' : fileIcon(node.label.split('.').pop())}</span>
              <span style={{ fontSize: 10, color: '#484f58' }}>{node.path}</span>
            </div>
          ))
        ) : (
          // Hierarchical tree
          rootItems.map(node => (
            <TreeItem
              key={node.id}
              node={node}
              depth={0}
              onSelect={onFileSelect}
              selectedPath={selectedPath}
              allNodes={nodes}
            />
          ))
        )}
      </div>

      {/* Footer stats */}
      <div style={{
        padding: '8px 12px',
        borderTop: '1px solid #21262d',
        fontSize: 10, color: '#484f58',
      }}>
        {nodes.filter(n => n.type === 'file').length} files · {nodes.filter(n => n.type === 'folder').length} folders
      </div>
    </div>
  )
}
