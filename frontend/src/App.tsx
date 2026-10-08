import { Route, Routes, useLocation } from 'react-router-dom'
import { AuthProvider } from './auth'
import { useReveal } from './useReveal'
import NavBar from './components/NavBar'
import ChatWidget from './components/ChatWidget'
import Home from './pages/Home'
import Products from './pages/Products'
import ProductDetail from './pages/ProductDetail'
import AboutUs from './pages/AboutUs'
import LogIn from './pages/LogIn'
import CreateAccount from './pages/CreateAccount'

function AppRoutes() {
  const location = useLocation()
  // Scroll-reveal is wired here so it re-scans on every navigation.
  useReveal()

  return (
    // `key` on the wrapper restarts the fade-in animation on each route change.
    <main key={location.pathname} className="route-fade">
      <Routes location={location}>
        <Route path="/" element={<Home />} />
        <Route path="/products" element={<Products />} />
        <Route path="/products/:productId" element={<ProductDetail />} />
        <Route path="/about" element={<AboutUs />} />
        <Route path="/login" element={<LogIn />} />
        <Route path="/signup" element={<CreateAccount />} />
        <Route
          path="*"
          element={
            <div className="page">
              <h1>Page not found</h1>
              <p>That link does not go anywhere yet.</p>
            </div>
          }
        />
      </Routes>
    </main>
  )
}

export default function App() {
  return (
    <AuthProvider>
      <NavBar />
      <AppRoutes />
      {/* Floating panel, present on every page. */}
      <ChatWidget />
    </AuthProvider>
  )
}
