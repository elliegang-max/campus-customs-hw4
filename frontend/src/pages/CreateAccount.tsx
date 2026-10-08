import { useState, type FormEvent } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../auth'

const MIN_PASSWORD_LENGTH = 8

const EMPTY = {
  firstName: '',
  lastName: '',
  email: '',
  password: '',
  confirmPassword: '',
}

export default function CreateAccount() {
  const { signUp } = useAuth()
  const navigate = useNavigate()

  const [form, setForm] = useState(EMPTY)
  const [error, setError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)

  function update(field: keyof typeof EMPTY, value: string) {
    setForm((prev) => ({ ...prev, [field]: value }))
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()

    // Checked here for a fast, friendly message. The server checks length again
    // and owns the email-uniqueness rule — this is convenience, not security.
    if (form.password.length < MIN_PASSWORD_LENGTH) {
      setError(`Password must be at least ${MIN_PASSWORD_LENGTH} characters.`)
      return
    }
    if (form.password !== form.confirmPassword) {
      setError('Those passwords do not match.')
      return
    }

    setError(null)
    setSubmitting(true)

    try {
      await signUp({
        first_name: form.firstName,
        last_name: form.lastName,
        email: form.email,
        password: form.password,
      })
      navigate('/')
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Could not create the account.')
      setForm((prev) => ({ ...prev, password: '', confirmPassword: '' }))
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="page">
      <div className="page-header" style={{ textAlign: 'center' }}>
        <h1>Create account</h1>
        <p style={{ margin: '0 auto' }}>
          Takes a minute. You will need an account to check out and to keep a
          record of what you have ordered.
        </p>
      </div>

      <form className="form-card" onSubmit={handleSubmit} noValidate>
        {error && (
          <p className="form-error" role="alert">
            {error}
          </p>
        )}

        {/* Split name, matching first_name / last_name on the users table. */}
        <div className="field-row">
          <div className="field">
            <label htmlFor="signup-first">First name</label>
            <input
              id="signup-first"
              type="text"
              name="firstName"
              autoComplete="given-name"
              value={form.firstName}
              onChange={(e) => update('firstName', e.target.value)}
              required
            />
          </div>

          <div className="field">
            <label htmlFor="signup-last">Last name</label>
            <input
              id="signup-last"
              type="text"
              name="lastName"
              autoComplete="family-name"
              value={form.lastName}
              onChange={(e) => update('lastName', e.target.value)}
              required
            />
          </div>
        </div>

        <div className="field">
          <label htmlFor="signup-email">Email</label>
          <input
            id="signup-email"
            type="email"
            name="email"
            autoComplete="email"
            value={form.email}
            onChange={(e) => update('email', e.target.value)}
            required
          />
        </div>

        <div className="field">
          <label htmlFor="signup-password">Password</label>
          <input
            id="signup-password"
            type="password"
            name="password"
            autoComplete="new-password"
            minLength={MIN_PASSWORD_LENGTH}
            value={form.password}
            onChange={(e) => update('password', e.target.value)}
            required
          />
          <p className="field-hint">At least {MIN_PASSWORD_LENGTH} characters.</p>
        </div>

        <div className="field">
          <label htmlFor="signup-confirm">Confirm password</label>
          <input
            id="signup-confirm"
            type="password"
            name="confirmPassword"
            autoComplete="new-password"
            value={form.confirmPassword}
            onChange={(e) => update('confirmPassword', e.target.value)}
            required
          />
        </div>

        <button type="submit" className="btn btn-block" disabled={submitting}>
          {submitting ? 'Creating account…' : 'Create account'}
        </button>

        <p className="form-note">
          Already have one? <Link to="/login">Log in</Link>
        </p>
      </form>
    </div>
  )
}
