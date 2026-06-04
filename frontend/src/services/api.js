const BASE = '/api'

/**
 * Stream Agent Ready analysis via SSE.
 * Returns an EventSource-like object.
 * Uses fetch + ReadableStream for POST with file.
 */
export async function streamAgentReady(file, provider, onChunk, onDone, onError) {
  const formData = new FormData()
  formData.append('file', file)
  formData.append('provider', provider)

  try {
    const res = await fetch(`${BASE}/agent-ready/analyze`, {
      method: 'POST',
      body: formData,
    })

    if (!res.ok) {
      const text = await res.text()
      onError(`Server error ${res.status}: ${text}`)
      return
    }

    const reader = res.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ''

    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split('\n')
      buffer = lines.pop()

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          const data = line.slice(6)
          if (data === '[DONE]') {
            onDone()
            return
          }
          if (data.trim()) onChunk(data)
        }
      }
    }
    onDone()
  } catch (err) {
    onError(err.message)
  }
}

/**
 * Upload ZIP and get graph JSON for visualizer.
 */
export async function analyzeVisualizer(file) {
  const formData = new FormData()
  formData.append('file', file)

  const res = await fetch(`${BASE}/visualizer/analyze`, {
    method: 'POST',
    body: formData,
  })

  if (!res.ok) {
    const text = await res.text()
    throw new Error(`Server error ${res.status}: ${text}`)
  }

  return res.json()
}


/**
 * Stream Testing workflow via SSE.
 */
export async function streamTesting(file, appUrl, username, password, provider, onChunk, onDone, onError) {
  const formData = new FormData()
  formData.append('file', file)
  formData.append('app_url', appUrl)
  if (username) formData.append('username', username)
  if (password) formData.append('password', password)
  formData.append('provider', provider)

  try {
    const res = await fetch(`${BASE}/testing/unified-workflow`, {
      method: 'POST',
      body: formData,
    })

    if (!res.ok) {
      const text = await res.text()
      onError(`Server error ${res.status}: ${text}`)
      return
    }

    const reader = res.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ''

    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      buffer += decoder.decode(value, { stream: true})
      const lines = buffer.split('\n')
      buffer = lines.pop()

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          const data = line.slice(6)
          if (data === '[DONE]') {
            onDone()
            return
          }
          if (data.trim()) onChunk(data)
        }
      }
    }
    onDone()
  } catch (err) {
    onError(err.message)
  }
}
