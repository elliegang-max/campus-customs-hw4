import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { fetchProducts, formatPrice, type Product } from '../api'
import './Products.css'

/** Cards show a trimmed description; the full text lives on the detail page. */
function shorten(text: string, limit = 110): string {
  if (text.length <= limit) return text
  const cut = text.slice(0, limit)
  const lastSpace = cut.lastIndexOf(' ')
  return `${cut.slice(0, lastSpace > 0 ? lastSpace : limit)}…`
}

type SortKey = 'name' | 'price-asc' | 'price-desc'

export default function Products() {
  const [products, setProducts] = useState<Product[]>([])
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  // Controls
  const [query, setQuery] = useState('')
  const [sort, setSort] = useState<SortKey>('name')
  const [inStockOnly, setInStockOnly] = useState(false)

  useEffect(() => {
    let cancelled = false

    fetchProducts()
      .then((data) => {
        if (!cancelled) setProducts(data)
      })
      .catch((err: unknown) => {
        if (!cancelled) setError(err instanceof Error ? err.message : String(err))
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })

    return () => {
      cancelled = true
    }
  }, [])

  // Filter + sort happen on the client: all 102 products are already loaded, so
  // typing filters instantly with no extra requests.
  const visible = useMemo(() => {
    const needle = query.trim().toLowerCase()
    let result = products

    if (needle) {
      result = result.filter(
        (p) =>
          p.name.toLowerCase().includes(needle) ||
          p.description.toLowerCase().includes(needle) ||
          p.garment_type.toLowerCase().includes(needle) ||
          p.search_tags.some((t) => t.toLowerCase().includes(needle)) ||
          p.colors.some((c) => c.toLowerCase().includes(needle)),
      )
    }

    if (inStockOnly) {
      result = result.filter((p) => p.total_stock > 0)
    }

    const sorted = [...result]
    if (sort === 'price-asc') sorted.sort((a, b) => a.price - b.price)
    else if (sort === 'price-desc') sorted.sort((a, b) => b.price - a.price)
    else sorted.sort((a, b) => a.name.localeCompare(b.name))

    return sorted
  }, [products, query, sort, inStockOnly])

  return (
    <div className="page">
      <div className="page-header">
        <h1>Products</h1>
        <p>
          Everything we stock, sized XS through XXL. Click any piece for sizes,
          stock and the full description.
        </p>
      </div>

      {loading && <div className="placeholder">Loading the catalogue…</div>}

      {error && (
        <div className="placeholder">
          <p>
            <strong>Could not load the catalogue.</strong>
          </p>
          <p>
            {error} — check that the API is running on <code>:8000</code>.
          </p>
        </div>
      )}

      {!loading && !error && (
        <>
          <div className="product-controls">
            <input
              type="search"
              className="product-search"
              placeholder="Search products, colors, teams…"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              aria-label="Search products"
            />

            <label className="control-inline">
              Sort
              <select
                value={sort}
                onChange={(e) => setSort(e.target.value as SortKey)}
                aria-label="Sort products"
              >
                <option value="name">Name (A–Z)</option>
                <option value="price-asc">Price (low to high)</option>
                <option value="price-desc">Price (high to low)</option>
              </select>
            </label>

            <label className="control-inline control-checkbox">
              <input
                type="checkbox"
                checked={inStockOnly}
                onChange={(e) => setInStockOnly(e.target.checked)}
              />
              In stock only
            </label>
          </div>

          <p className="result-count">
            {visible.length === products.length
              ? `${products.length} products`
              : `${visible.length} of ${products.length} products`}
          </p>

          {visible.length === 0 ? (
            <div className="placeholder">
              <p>
                <strong>No products match “{query}”.</strong>
              </p>
              <p>Try a different search, or clear the filters.</p>
            </div>
          ) : (
            <ul className="product-grid">
              {visible.map((product) => (
                // No scroll-reveal here: the grid re-renders on every search/sort,
                // and a reveal that only re-scans on route change would leave
                // filtered cards invisible. Cards keep their hover motion instead.
                <li key={product.product_id}>
                  <Link
                    to={`/products/${product.product_id}`}
                    className="product-card"
                  >
                    <div className="product-card-image">
                      <img
                        src={product.image_url}
                        alt={product.name}
                        loading="lazy"
                      />
                      {product.total_stock === 0 ? (
                        <span className="badge badge-soldout">Sold out</span>
                      ) : product.total_stock <= 8 ? (
                        <span className="badge badge-low">Low stock</span>
                      ) : null}
                    </div>

                    <div className="product-card-body">
                      <span className="product-card-type">
                        {product.garment_type}
                      </span>
                      <h3>{product.name}</h3>
                      <p className="product-card-desc">
                        {shorten(product.description)}
                      </p>
                      <p className="product-card-price">
                        {formatPrice(product.price)}
                      </p>
                    </div>
                  </Link>
                </li>
              ))}
            </ul>
          )}
        </>
      )}
    </div>
  )
}
