import { Link } from 'react-router-dom'
import './Home.css'

/**
 * Collections mirror how the catalogue actually divides up: residential
 * colleges, varsity sports, the graduate and professional schools, and the
 * family lineup (Yale Dad, Yale Grandma, and so on).
 */
const COLLECTIONS = [
  {
    title: 'Residential Colleges',
    blurb:
      'Crewnecks and quarter-zips for all fourteen houses — Branford to Timothy Dwight. Wear the one you got sorted into.',
  },
  {
    title: 'Varsity Sports',
    blurb:
      'Left-chest marks for every team on the field, the ice, the water and the court. Baseball through volleyball.',
  },
  {
    title: 'Graduate & Professional',
    blurb:
      'Law, Medicine, Music, Architecture, Nursing, Public Health and the rest, in fleece and quarter-zip.',
  },
  {
    title: 'For the Family',
    blurb:
      'Yale Mom, Yale Dad, and the whole extended roster — aunts, uncles, grandparents, siblings and cousins.',
  },
]

const STATS = [
  { figure: '100+', label: 'styles in stock' },
  { figure: '14', label: 'residential colleges' },
  { figure: 'XS–XXL', label: 'every size' },
  { figure: 'New Haven', label: 'made to order' },
]

export default function Home() {
  return (
    <>
      <section className="hero">
        <div className="hero-glow" aria-hidden="true" />
        <div className="hero-inner">
          <p className="hero-eyebrow">New Haven, Connecticut · Est. on campus</p>
          <h1 className="hero-title">
            Bulldog blue,
            <br />
            <span className="hero-accent">made to order.</span>
          </h1>
          <p className="hero-lede">
            Campus Customs outfits Yale students, teams, families and alumni in gear
            that looks like it belongs here — because it does. Browse the racks, or
            tell our assistant what you need.
          </p>
          <div className="hero-actions">
            <Link to="/products" className="btn btn-accent">
              Shop the catalogue
            </Link>
            <Link to="/about" className="btn btn-outline hero-ghost">
              Our story
            </Link>
          </div>

          <ul className="hero-stats">
            {STATS.map(({ figure, label }) => (
              <li key={label}>
                <span className="stat-figure">{figure}</span>
                <span className="stat-label">{label}</span>
              </li>
            ))}
          </ul>
        </div>
      </section>

      <div className="page">
        <section>
          <div className="section-head" data-reveal>
            <p className="eyebrow">The racks</p>
            <h2>Shop by collection</h2>
            <p className="section-sub">
              A hundred-plus styles, sized XS through XXL, in the blues and heather
              grays that have been on this campus for a century and a half.
            </p>
          </div>

          <ul className="collection-grid">
            {COLLECTIONS.map(({ title, blurb }, i) => (
              <li
                key={title}
                className="collection-card"
                data-reveal
                style={{ transitionDelay: `${i * 80}ms` }}
              >
                <span className="collection-index">0{i + 1}</span>
                <h3>{title}</h3>
                <p>{blurb}</p>
                <Link to="/products" className="collection-link">
                  Browse <span aria-hidden="true">→</span>
                </Link>
              </li>
            ))}
          </ul>
        </section>

        <section className="pitch" data-reveal>
          <div className="pitch-body">
            <p className="eyebrow">Custom work</p>
            <h2>Your name on it, start to finish</h2>
            <p>
              Screen printing and embroidery for suites, teams, clubs, reunions and
              anyone who wants their own spin. Bring a sketch or a rough idea — we
              handle the artwork, the sizing run and the turnaround.
            </p>
            <Link to="/about" className="btn btn-outline">
              How it works
            </Link>
          </div>
          <div className="pitch-art" aria-hidden="true">
            <span>CC</span>
          </div>
        </section>
      </div>
    </>
  )
}
