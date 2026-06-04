import { useEffect, useRef, useState } from 'react'
import * as d3 from 'd3'

const NC = {
  folder: '#7B68EE', file: '#00CED1', class: '#FF8C00',
  function: '#FF4500', method: '#FF69B4',
}
const NS = { folder: 16, file: 9, class: 8, function: 6, method: 4 }
const CC_COLOR = {
  'folder-folder': 'rgba(123,104,238,.35)', 'file-file': '#00BFFF',
  'file-symbol': 'rgba(255,140,0,.55)', 'class-method': 'rgba(255,105,180,.6)',
  'class-class': '#DA70D6', 'folder-file': 'rgba(255,255,255,.10)',
}
const CC_WIDTH = {
  'folder-folder': 1.2, 'file-file': 1.4, 'file-symbol': 0.7,
  'class-method': 0.7, 'class-class': 1.8, 'folder-file': 0.5,
}

function connCat(s, t) {
  if (s === 'folder' && t === 'folder') return 'folder-folder'
  if (s === 'file' && t === 'file') return 'file-file'
  if (s === 'file' && (t === 'class' || t === 'function')) return 'file-symbol'
  if (s === 'class' && t === 'method') return 'class-method'
  if (s === 'class' && t === 'class') return 'class-class'
  return 'folder-file'
}

function fileIcon(ext) {
  const icons = {
    py: '🐍', js: '📜', jsx: '⚛', ts: '🔷', tsx: '⚛',
    json: '📋', yaml: '⚙', yml: '⚙', md: '📝', css: '🎨',
    html: '🌐', sh: '💻', env: '🔐', toml: '⚙', txt: '📄',
    sql: '🗃', lock: '🔒', ini: '⚙', cfg: '⚙', conf: '⚙',
  }
  return icons[ext] || '📄'
}

function FileTreeItem({ node, depth, onSelect, selectedPath, allNodes }) {
  const [open, setOpen] = useState(depth < 2)
  const isSelected = selectedPath === node.path

  if (node.type === 'folder') {
    const children = allNodes
      .filter(n => {
        if (n.path === node.path) return false
        if (n.type !== 'folder' && n.type !== 'file') return false
        const lastSlash = n.path.lastIndexOf('/')
        const parentPath = lastSlash === -1 ? '' : n.path.substring(0, lastSlash)
        return parentPath === node.path
      })
      .sort((a, b) => {
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
            userSelect: 'none', background: isSelected ? '#1f2937' : 'transparent',
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
          <FileTreeItem
            key={child.id} node={child} depth={depth + 1}
            onSelect={onSelect} selectedPath={selectedPath} allNodes={allNodes}
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

export default function D3CodeGraph({ graphData, sessionId }) {
  const svgRef = useRef(null)
  const zoomRef = useRef(null)
  const [selectedFile, setSelectedFile] = useState(null)
  const [fileContent, setFileContent] = useState('')
  const [searchQ, setSearchQ] = useState('')
  const [activeN, setActiveN] = useState(new Set(['folder', 'file', 'class', 'function', 'method']))
  const [activeC, setActiveC] = useState(new Set([
    'folder-folder', 'file-file', 'file-symbol', 'class-method', 'class-class'
  ]))
  const [simDone, setSimDone] = useState(false)
  const nodeSelRef = useRef(null)
  const linkSelRef = useRef(null)
  const gRef = useRef(null)

  const nodes = graphData.nodes.map(d => ({ ...d }))
  const edges = graphData.edges.map(d => ({ ...d }))
  const nodeMap = {}
  nodes.forEach(n => { nodeMap[n.id] = n })
  edges.forEach(e => {
    const sn = nodeMap[e.source] || nodeMap[e.source?.id]
    const tn = nodeMap[e.target] || nodeMap[e.target?.id]
    e._cc = connCat(sn?.type, tn?.type)
  })

  const rootItems = nodes
    .filter(n => {
      if (n.type !== 'folder' && n.type !== 'file') return false
      return !n.path.includes('/')
    })
    .sort((a, b) => {
      if (a.type === b.type) return a.label.localeCompare(b.label)
      return a.type === 'folder' ? -1 : 1
    })

  useEffect(() => {
    if (selectedFile && selectedFile.type === 'file') {
      const encodedPath = selectedFile.path.split('/').map(encodeURIComponent).join('/')
      setFileContent('// Loading...')
      
      fetch(`/api/visualizer/source/${sessionId}/${encodedPath}`)
        .then(res => {
          if (!res.ok) throw new Error(`HTTP ${res.status}`)
          return res.text()
        })
        .then(content => setFileContent(content))
        .catch(err => {
          setFileContent(
            `// Error loading file\n` +
            `// Path: ${selectedFile.path}\n` +
            `// Error: ${err.message}`
          )
        })
    }
  }, [selectedFile, sessionId])

  useEffect(() => {
    if (!svgRef.current || !graphData) return

    const svg = d3.select(svgRef.current)
    svg.selectAll('*').remove()

    const W = svgRef.current.clientWidth || 900
    const H = svgRef.current.clientHeight || 600

    const defs = svg.append('defs')
    const fg = defs.append('filter').attr('id', 'glow8')
      .attr('x', '-60%').attr('y', '-60%').attr('width', '220%').attr('height', '220%')
    fg.append('feGaussianBlur').attr('stdDeviation', '2.5').attr('result', 'blur')
    const fgm = fg.append('feMerge')
    fgm.append('feMergeNode').attr('in', 'blur')
    fgm.append('feMergeNode').attr('in', 'SourceGraphic')

    const g = svg.append('g')
    gRef.current = g
    
    const zoom = d3.zoom().scaleExtent([0.02, 12])
      .on('zoom', e => g.attr('transform', e.transform))
    zoomRef.current = zoom
    svg.call(zoom)

    const sim = d3.forceSimulation(nodes)
      .alphaDecay(0.04).velocityDecay(0.35)
      .force('link', d3.forceLink(edges).id(d => d.id)
        .distance(d => d._cc === 'folder-folder' ? 80 : d._cc === 'file-file' ? 160 : 55)
        .strength(d => d._cc === 'file-file' ? 0.2 : 0.7))
      .force('charge', d3.forceManyBody()
        .strength(d => d.type === 'folder' ? -250 : d.type === 'file' ? -100 : -30)
        .distanceMax(400))
      .force('center', d3.forceCenter(W / 2, H / 2))
      .force('collide', d3.forceCollide().radius(d => (NS[d.type] || 6) * 1.8))

    const linkG = g.append('g')
    const nodeG = g.append('g')

    function render() {
      const vis = nodes.filter(d => activeN.has(d.type))
      const visIds = new Set(vis.map(d => d.id))
      const visE = edges.filter(l => {
        const s = l.source.id || l.source
        const t = l.target.id || l.target
        if (!visIds.has(s) || !visIds.has(t)) return false
        if (l._cc === 'folder-file') return activeN.has('folder') && activeN.has('file')
        return activeC.has(l._cc)
      })

      let ls = linkG.selectAll('line').data(visE, d => (d.source.id || d.source) + '|' + (d.target.id || d.target))
      ls.exit().remove()
      ls = ls.enter().append('line')
        .attr('stroke', d => CC_COLOR[d._cc])
        .attr('stroke-width', d => CC_WIDTH[d._cc])
        .merge(ls)
      linkSelRef.current = ls

      let ns = nodeG.selectAll('g').data(vis, d => d.id)
      ns.exit().remove()
      
      const enter = ns.enter().append('g')
        .call(d3.drag()
          .on('start', (e, d) => { if (!e.active) sim.alphaTarget(0.2).restart(); d.fx = d.x; d.fy = d.y })
          .on('drag', (e, d) => { d.fx = e.x; d.fy = e.y })
          .on('end', (e, d) => { if (!e.active) sim.alphaTarget(0); d.fx = null; d.fy = null }))

      enter.append('circle')
        .attr('r', d => NS[d.type] || 6)
        .attr('fill', d => NC[d.type])
        .attr('filter', 'url(#glow8)')
        .attr('cursor', 'pointer')

      enter.filter(d => d.type === 'folder')
        .append('text').text(d => d.label)
        .attr('dy', -18).attr('text-anchor', 'middle')
        .attr('font-size', '10px').attr('fill', '#9988FF')
        .attr('pointer-events', 'none')

      ns = enter.merge(ns)
      nodeSelRef.current = ns

      ns.on('click', (e, d) => {
        if (d.type === 'file') setSelectedFile(d)
      })

      const tip = document.getElementById('viz-tip8')
      ns.on('mouseover', (e, d) => {
        if (tip) {
          tip.style.display = 'block'
          document.getElementById('viz-tname8').textContent = d.label
          document.getElementById('viz-ttype8').textContent = d.type
          document.getElementById('viz-tpath8').textContent = d.path
        }
        
        const conn = new Set([d.id])
        visE.forEach(l => {
          const s = l.source.id || l.source
          const t = l.target.id || l.target
          if (s === d.id) conn.add(t)
          if (t === d.id) conn.add(s)
        })
        
        ns.select('circle').attr('opacity', n => conn.has(n.id) ? 1 : 0.07)
        ls.attr('opacity', l => {
          const s = l.source.id || l.source
          const t = l.target.id || l.target
          return (s === d.id || t === d.id) ? 1 : 0.04
        })
      })
      .on('mousemove', e => {
        if (tip) { tip.style.left = (e.clientX + 14) + 'px'; tip.style.top = (e.clientY - 8) + 'px' }
      })
      .on('mouseout', () => {
        if (tip) tip.style.display = 'none'
        ns.select('circle').attr('opacity', 1)
        ls.attr('opacity', 1)
      })

      sim.nodes(vis)
      const linkForce = sim.force('link')
      linkForce.links(visE)
      sim.alpha(0.5).restart()
    }

    let tc = 0
    sim.on('tick', () => {
      if (++tc % 3 !== 0 || !linkSelRef.current || !nodeSelRef.current) return
      linkSelRef.current
        .attr('x1', d => d.source.x).attr('y1', d => d.source.y)
        .attr('x2', d => d.target.x).attr('y2', d => d.target.y)
      nodeSelRef.current.attr('transform', d => `translate(${d.x},${d.y})`)
    })

    // FIT VIEW function - centers visible nodes
    const fitView = () => {
      if (!gRef.current || !zoomRef.current) return
      const bbox = gRef.current.node().getBBox()
      if (!bbox.width || !bbox.height) return
      
      const width = svgRef.current.clientWidth
      const height = svgRef.current.clientHeight
      const scale = Math.min(width / bbox.width, height / bbox.height) * 0.88
      
      svg.transition().duration(700).call(
        zoomRef.current.transform,
        d3.zoomIdentity
          .translate(width / 2 - scale * (bbox.x + bbox.width / 2), 
                     height / 2 - scale * (bbox.y + bbox.height / 2))
          .scale(scale)
      )
    }

    sim.on('end', () => { setSimDone(true); fitView() })
    setTimeout(() => { sim.stop(); fitView(); setSimDone(true) }, 8000)

    render()
    return () => sim.stop()
  }, [graphData, activeN, activeC])

  // Zoom to selected file when clicked
  useEffect(() => {
    if (!selectedFile || !nodeSelRef.current || !linkSelRef.current) {
      if (nodeSelRef.current) nodeSelRef.current.attr('display', null)
      if (linkSelRef.current) linkSelRef.current.attr('display', null)
      return
    }

    const conn = new Set([selectedFile.id])
    edges.forEach(e => {
      const s = e.source.id || e.source
      const t = e.target.id || e.target
      if (s === selectedFile.id) conn.add(t)
      if (t === selectedFile.id) conn.add(s)
    })

    nodeSelRef.current.attr('display', n => conn.has(n.id) ? null : 'none')
    linkSelRef.current.attr('display', l => {
      const s = l.source.id || l.source
      const t = l.target.id || l.target
      return (conn.has(s) && conn.has(t)) ? null : 'none'
    })

    // Zoom to selected node cluster
    setTimeout(() => {
      if (!gRef.current || !zoomRef.current || !svgRef.current) return
      const bbox = gRef.current.node().getBBox()
      if (!bbox.width || !bbox.height) return
      
      const width = svgRef.current.clientWidth
      const height = svgRef.current.clientHeight
      const scale = Math.min(width / bbox.width, height / bbox.height, 2) * 0.85
      
      d3.select(svgRef.current).transition().duration(500).call(
        zoomRef.current.transform,
        d3.zoomIdentity
          .translate(width / 2 - scale * (bbox.x + bbox.width / 2),
                     height / 2 - scale * (bbox.y + bbox.height / 2))
          .scale(scale)
      )
    }, 120)

    return () => {
      if (nodeSelRef.current) nodeSelRef.current.attr('display', null)
      if (linkSelRef.current) linkSelRef.current.attr('display', null)
    }
  }, [selectedFile, edges])

  const nodeFilters = [
    { type: 'folder', color: '#7B68EE', label: 'Folders' },
    { type: 'file', color: '#00CED1', label: 'Files' },
    { type: 'class', color: '#FF8C00', label: 'Classes' },
    { type: 'function', color: '#FF4500', label: 'Functions' },
    { type: 'method', color: '#FF69B4', label: 'Methods' },
  ]

  const connFilters = [
    { key: 'folder-folder', color: '#7B68EE', label: 'Folder↔Folder' },
    { key: 'file-file', color: '#00BFFF', label: 'File↔File' },
    { key: 'file-symbol', color: '#FF8C00', label: 'File↔Symbol' },
    { key: 'class-method', color: '#FF69B4', label: 'Class↔Method' },
    { key: 'class-class', color: '#DA70D6', label: 'Class↔Class' },
  ]

  return (
    <div style={{ flex: 1, display: 'flex', overflow: 'hidden' }}>
      
      {/* Left: File Explorer */}
      <div style={{
        width: 280, flexShrink: 0, background: '#161b22',
        borderRight: '1px solid #21262d',
        display: 'flex', flexDirection: 'column', overflow: 'hidden',
      }}>
        <div style={{
          padding: '10px 12px', borderBottom: '1px solid #21262d',
          fontSize: 11, fontWeight: 700, color: '#8b949e',
          letterSpacing: '.05em', textTransform: 'uppercase',
        }}>
          📁 EXPLORER
        </div>
        <div style={{ padding: '8px 12px', borderBottom: '1px solid #21262d' }}>
          <input
            value={searchQ}
            onChange={e => setSearchQ(e.target.value)}
            placeholder="Search files..."
            style={{
              width: '100%', background: '#0d1117', border: '1px solid #30363d',
              borderRadius: 6, padding: '6px 10px', color: '#e6edf3',
              fontSize: 12, outline: 'none',
            }}
          />
        </div>
        <div style={{ flex: 1, overflow: 'auto', padding: '8px 0' }}>
          {searchQ ? (
            nodes.filter(n => n.type === 'file' && 
              (n.label.toLowerCase().includes(searchQ.toLowerCase()) || 
               n.path.toLowerCase().includes(searchQ.toLowerCase()))
            ).slice(0, 100).map(node => (
              <div
                key={node.id}
                onClick={() => setSelectedFile(node)}
                style={{
                  display: 'flex', alignItems: 'center', gap: 5,
                  padding: '3px 12px', cursor: 'pointer',
                  fontSize: 12, color: '#c9d1d9',
                }}
                onMouseEnter={e => e.currentTarget.style.background = '#161b22'}
                onMouseLeave={e => e.currentTarget.style.background = 'transparent'}
              >
                <span>{fileIcon(node.label.split('.').pop())}</span>
                <span style={{ fontSize: 10, color: '#484f58' }}>{node.path}</span>
              </div>
            ))
          ) : (
            rootItems.map(node => (
              <FileTreeItem
                key={node.id} node={node} depth={0}
                onSelect={setSelectedFile}
                selectedPath={selectedFile?.path}
                allNodes={nodes}
              />
            ))
          )}
        </div>
        <div style={{
          padding: '8px 12px', borderTop: '1px solid #21262d',
          fontSize: 10, color: '#484f58',
        }}>
          {nodes.filter(n => n.type === 'file').length} files · {nodes.filter(n => n.type === 'folder').length} folders
        </div>
      </div>

      {/* Middle: Code Inspector */}
      {selectedFile && (
        <div style={{
          width: 500, flexShrink: 0, background: '#0d1117',
          borderRight: '1px solid #21262d',
          display: 'flex', flexDirection: 'column', overflow: 'hidden'
        }}>
          <div style={{
            padding: '10px 16px', borderBottom: '1px solid #21262d',
            display: 'flex', alignItems: 'center', gap: 8,
            background: '#161b22',
          }}>
            <span>{fileIcon(selectedFile.label.split('.').pop())}</span>
            <span style={{ fontSize: 13, fontWeight: 600, color: '#e6edf3', flex: 1 }}>
              {selectedFile.label}
            </span>
            <span style={{ fontSize: 10, color: '#484f58' }}>{selectedFile.type}</span>
            <span
              onClick={() => {
                setSelectedFile(null)
                setFileContent('')
              }}
              style={{
                cursor: 'pointer', fontSize: 20, fontWeight: 'bold',
                color: '#8b949e', padding: '4px 12px',
                borderRadius: 4, background: '#21262d',
                lineHeight: 1, userSelect: 'none',
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.color = '#ffffff'
                e.currentTarget.style.background = '#484f58'
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.color = '#8b949e'
                e.currentTarget.style.background = '#21262d'
              }}
            >
              ✕
            </span>
          </div>
          <pre style={{
            flex: 1, overflow: 'auto', margin: 0, padding: 16,
            fontSize: 12, lineHeight: 1.6,
            fontFamily: "'Cascadia Code', 'Fira Code', Consolas, monospace",
            color: '#c9d1d9', background: '#0d1117',
          }}>
            {fileContent || 'Loading...'}
          </pre>
        </div>
      )}

      {/* Right: D3 Graph */}
      <div style={{ flex: 1, position: 'relative' }}>
        <svg ref={svgRef} style={{ width: '100%', height: '100%', display: 'block' }} />

        {/* Filter controls - STACKED VERTICALLY to avoid overlap */}
        <div style={{
          position: 'absolute', top: 12, left: 12,
          display: 'flex', flexDirection: 'column', gap: 8, zIndex: 10,
          background: 'rgba(13,17,23,0.85)', padding: '8px 12px',
          borderRadius: 8, border: '1px solid #21262d',
        }}>
          <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap', maxWidth: 280 }}>
            <span style={{ fontSize: 9, color: '#484f58', textTransform: 'uppercase', width: '100%', marginBottom: 2 }}>Nodes:</span>
            {nodeFilters.map(({ type, color, label }) => (
              <button key={type} onClick={() => setActiveN(prev => {
                const next = new Set(prev)
                next.has(type) ? next.delete(type) : next.add(type)
                return next
              })} style={{
                borderRadius: 12, padding: '3px 8px', fontSize: 9, cursor: 'pointer',
                border: `1px solid ${color}`, color, background: 'transparent',
                opacity: activeN.has(type) ? 1 : 0.28
              }}>{label}</button>
            ))}
          </div>
          <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap', maxWidth: 280 }}>
            <span style={{ fontSize: 9, color: '#484f58', textTransform: 'uppercase', width: '100%', marginBottom: 2 }}>Connections:</span>
            {connFilters.map(({ key, color, label }) => (
              <button key={key} onClick={() => setActiveC(prev => {
                const next = new Set(prev)
                next.has(key) ? next.delete(key) : next.add(key)
                return next
              })} style={{
                borderRadius: 12, padding: '3px 8px', fontSize: 9, cursor: 'pointer',
                border: `1px solid ${color}`, color, background: 'transparent',
                opacity: activeC.has(key) ? 1 : 0.28
              }}>{label}</button>
            ))}
          </div>
        </div>

        {/* Stats */}
        <div style={{
          position: 'absolute', top: 12, right: 12,
          background: 'rgba(13,17,23,.9)', border: '1px solid #21262d',
          borderRadius: 8, padding: '8px 14px', fontSize: 11, color: '#484f58',
          pointerEvents: 'none', zIndex: 10
        }}>
          Nodes <b style={{ color: '#e6edf3' }}>{graphData.nodes.length}</b>
          &nbsp;·&nbsp;
          Edges <b style={{ color: '#e6edf3' }}>{graphData.edges.length}</b>
          {!simDone && <div style={{ fontSize: 10, color: '#7B68EE', marginTop: 2 }}>Simulating…</div>}
        </div>

        {/* Bottom reset */}
        <div style={{
          position: 'absolute', bottom: 18, left: '50%', transform: 'translateX(-50%)',
          zIndex: 10
        }}>
          <button onClick={() => {
            const svg = d3.select(svgRef.current)
            svg.transition().duration(600).call(d3.zoom().transform, d3.zoomIdentity)
          }} style={{
            background: 'rgba(22,27,34,.92)', border: '1px solid #30363d',
            borderRadius: 20, padding: '7px 14px', color: '#8b949e',
            cursor: 'pointer', fontSize: 11
          }}>Reset Zoom</button>
        </div>

        {/* Tooltip */}
        <div id="viz-tip8" style={{
          position: 'fixed', pointerEvents: 'none',
          background: 'rgba(13,17,23,.97)', border: '1px solid #30363d',
          borderRadius: 8, padding: '10px 14px', fontSize: 12,
          maxWidth: 300, display: 'none', zIndex: 99
        }}>
          <div id="viz-tname8" style={{ fontSize: 13, fontWeight: 700, marginBottom: 2 }} />
          <div id="viz-ttype8" style={{ fontSize: 10, color: '#484f58', textTransform: 'uppercase' }} />
          <div id="viz-tpath8" style={{ fontSize: 10, color: '#484f58', marginTop: 4, wordBreak: 'break-all' }} />
        </div>
      </div>
    </div>
  )
}
