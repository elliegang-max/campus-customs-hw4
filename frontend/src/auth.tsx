import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from 'react'

export interface User {
  id: number
  name: string
  first_name: string | null
  last_name: string | null
  email: string
  created_at: string
}

export interface SignUpInput {
  first_name: string
  last_name: string
  email: string
  password: string
}

interface AuthContextValue {
  user: User | null
  /** True until the first /me check finishes, so the nav does not flicker. */
  loading: boolean
  logIn: (email: string, password: string) => Promise<void>
  signUp: (input: SignUpInput) => Promise<void>
  logOut: () => Promise<void>
}

const AuthContext = createContext<AuthContextValue | null>(null)

/**
 * The session is an HttpOnly cookie, so there is nothing to read here — every
 * request just needs `credentials: 'include'` and the browser attaches it.
 */
async function post<T>(path: string, body?: unknown): Promise<T> {
  const response = await fetch(path, {
    method: 'POST',
    credentials: 'include',
    headers: body ? { 'Content-Type': 'application/json' } : undefined,
    body: body ? JSON.stringify(body) : undefined,
  })

  if (!response.ok) {
    throw new Error(await readError(response))
  }

  return response.status === 204 ? (undefined as T) : ((await response.json()) as T)
}

/** FastAPI returns `detail` as a string, or as a list for validation errors. */
async function readError(response: Response): Promise<string> {
  try {
    const data = await response.json()
    const detail = data?.detail
    if (typeof detail === 'string') return detail
    if (Array.isArray(detail) && detail[0]?.msg) {
      return String(detail[0].msg).replace(/^Value error, /, '')
    }
  } catch {
    // fall through to the status text
  }
  return `${response.status} ${response.statusText}`
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(true)

  // Ask the server who we are on load; the cookie may already be valid.
  useEffect(() => {
    let cancelled = false

    fetch('/api/auth/me', { credentials: 'include' })
      .then((response) => (response.ok ? response.json() : null))
      .then((data: User | null) => {
        if (!cancelled) setUser(data)
      })
      .catch(() => {
        if (!cancelled) setUser(null)
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })

    return () => {
      cancelled = true
    }
  }, [])

  const logIn = useCallback(async (email: string, password: string) => {
    setUser(await post<User>('/api/auth/login', { email, password }))
  }, [])

  const signUp = useCallback(async (input: SignUpInput) => {
    setUser(await post<User>('/api/auth/signup', input))
  }, [])

  const logOut = useCallback(async () => {
    await post<void>('/api/auth/logout')
    setUser(null)
  }, [])

  const value = useMemo(
    () => ({ user, loading, logIn, signUp, logOut }),
    [user, loading, logIn, signUp, logOut],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuth must be used inside <AuthProvider>')
  }
  return context
}
