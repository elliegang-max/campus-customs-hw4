import { NavLink, useNavigate } from 'react-router-dom'
import { useAuth } from '../auth'
import './NavBar.css'

/** Links that sit on the left, next to the wordmark. */
const BROWSE_LINKS = [
  { to: '/', label: 'Home', end: true },
  { to: '/products', label: 'Products' },
  { to: '/about', label: 'About Us' },
]

export default function NavBar() {
  const { user, loading, logOut } = useAuth()
  const navigate = useNavigate()

  async function handleLogOut() {
    await logOut()
    navigate('/')
  }

  return (
    <header className="nav">
      <nav className="nav-inner" aria-label="Main">
        <NavLink to="/" className="nav-brand">
          Campus&nbsp;<span className="brand-mark">Customs</span>
        </NavLink>

        <ul className="nav-links">
          {BROWSE_LINKS.map(({ to, label, end }) => (
            <li key={to}>
              <NavLink to={to} end={end} className="nav-link">
                {label}
              </NavLink>
            </li>
          ))}
        </ul>

        {/* Hold the slot while the session check runs, so the bar does not
            flash "Log in" at someone who is already signed in. */}
        <div className="nav-auth">
          {loading ? null : user ? (
            <>
              <span className="nav-user">
                Hi, <strong>{user.first_name || user.name}</strong>
              </span>
              <button type="button" className="nav-link nav-logout" onClick={handleLogOut}>
                Log out
              </button>
            </>
          ) : (
            <>
              <NavLink to="/login" className="nav-link">
                Log in
              </NavLink>
              <NavLink to="/signup" className="btn btn-sm">
                Create account
              </NavLink>
            </>
          )}
        </div>
      </nav>
    </header>
  )
}
