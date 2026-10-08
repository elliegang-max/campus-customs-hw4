import { useEffect } from 'react'
import { useLocation } from 'react-router-dom'

/**
 * Fade-and-rise elements in as they scroll into view.
 *
 * Any element with a `data-reveal` attribute starts hidden (see index.css) and
 * gets `.is-visible` when it first enters the viewport. One IntersectionObserver
 * is created per page view and re-scans whenever the route changes, so freshly
 * rendered content on a new page is picked up too.
 *
 * Elements already on screen at mount are revealed immediately, so nothing that
 * is above the fold sits invisible waiting for a scroll.
 */
export function useReveal() {
  const { pathname } = useLocation()

  useEffect(() => {
    const nodes = Array.from(
      document.querySelectorAll<HTMLElement>('[data-reveal]:not(.is-visible)'),
    )
    if (nodes.length === 0) return

    const observer = new IntersectionObserver(
      (entries, obs) => {
        for (const entry of entries) {
          if (entry.isIntersecting) {
            entry.target.classList.add('is-visible')
            obs.unobserve(entry.target)
          }
        }
      },
      { threshold: 0.12, rootMargin: '0px 0px -40px 0px' },
    )

    for (const node of nodes) {
      // Reveal immediately if it is already within the viewport at mount.
      const rect = node.getBoundingClientRect()
      if (rect.top < window.innerHeight && rect.bottom > 0) {
        node.classList.add('is-visible')
      } else {
        observer.observe(node)
      }
    }

    return () => observer.disconnect()
    // Re-run after each navigation, once the new page's DOM is in place.
  }, [pathname])
}
