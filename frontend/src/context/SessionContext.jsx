import { createContext, useContext, useState } from 'react'

const SessionCtx = createContext(null)

export function SessionProvider({ children }) {
  const [sharedFile, setSharedFile] = useState(null)

  return (
    <SessionCtx.Provider value={{ sharedFile, setSharedFile }}>
      {children}
    </SessionCtx.Provider>
  )
}

export function useSession() {
  return useContext(SessionCtx)
}
