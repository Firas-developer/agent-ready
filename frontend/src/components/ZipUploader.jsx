import { useRef, useState } from 'react'

export default function ZipUploader({ onFile, disabled }) {
  const inputRef = useRef()
  const [dragging, setDragging] = useState(false)
  const [fileName, setFileName] = useState(null)

  function handleFile(file) {
    if (!file) return
    if (!file.name.endsWith('.zip')) {
      alert('Please upload a .zip file')
      return
    }
    setFileName(file.name)
    onFile(file)
  }

  return (
    <div
      onClick={() => !disabled && inputRef.current.click()}
      onDragOver={e => { e.preventDefault(); setDragging(true) }}
      onDragLeave={() => setDragging(false)}
      onDrop={e => {
        e.preventDefault()
        setDragging(false)
        if (!disabled) handleFile(e.dataTransfer.files[0])
      }}
      style={{
        border: `2px dashed ${dragging ? '#7B68EE' : '#30363d'}`,
        borderRadius: 10,
        padding: '32px 24px',
        textAlign: 'center',
        cursor: disabled ? 'not-allowed' : 'pointer',
        background: dragging ? 'rgba(123,104,238,0.05)' : '#161b22',
        transition: 'all 0.2s',
        opacity: disabled ? 0.5 : 1,
      }}
    >
      <input
        ref={inputRef}
        type="file"
        accept=".zip"
        style={{ display: 'none' }}
        onChange={e => handleFile(e.target.files[0])}
      />
      <div style={{ fontSize: 36, marginBottom: 8 }}>📦</div>
      {fileName ? (
        <>
          <div style={{ color: '#3fb950', fontWeight: 600, fontSize: 14 }}>
            ✓ {fileName}
          </div>
          <div style={{ color: '#484f58', fontSize: 12, marginTop: 4 }}>
            Click to change file
          </div>
        </>
      ) : (
        <>
          <div style={{ color: '#e6edf3', fontWeight: 600, fontSize: 14 }}>
            Drop your project ZIP here
          </div>
          <div style={{ color: '#484f58', fontSize: 12, marginTop: 4 }}>
            or click to browse
          </div>
        </>
      )}
    </div>
  )
}
