import { useEffect, useState, type MouseEvent } from 'react'
import { Link, useParams } from 'react-router-dom'
import { fetchProduct, formatPrice, type Product } from '../api'
import './ProductDetail.css'

/** Stock is per size, so "in stock" is only ever a question about one size. */
function stockLabel(quantity: number): string {
  if (quantity === 0) return 'Out of stock'
  if (quantity <= 3) return `Only ${quantity} left`
  return `${quantity} in stock`
}

export default function ProductDetail() {
  const { productId } = useParams<{ productId: string }>()
  const [product, setProduct] = useState<Product | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [selectedSize, setSelectedSize] = useState<string | null>(null)
  // Cursor-tracked zoom on the main image.
  const [zoom, setZoom] = useState<{ x: number; y: number } | null>(null)

  function handleZoomMove(event: MouseEvent<HTMLDivElement>) {
    const rect = event.currentTarget.getBoundingClientRect()
    const x = ((event.clientX - rect.left) / rect.width) * 100
    const y = ((event.clientY - rect.top) / rect.height) * 100
    setZoom({ x, y })
  }

  useEffect(() => {
    if (!productId) return
    let cancelled = false

    setLoading(true)
    setError(null)
    setSelectedSize(null)

    fetchProduct(productId)
      .then((data) => {
        if (!cancelled) setProduct(data)
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
  }, [productId])

  if (loading) {
    return (
      <div className="page">
        <div className="placeholder">Loading…</div>
      </div>
    )
  }

  if (error || !product) {
    return (
      <div className="page">
        <div className="placeholder">
          <p>
            <strong>We could not find that product.</strong>
          </p>
          <p>{error}</p>
          <p>
            <Link to="/products">Back to all products</Link>
          </p>
        </div>
      </div>
    )
  }

  const selected = product.inventory.find((item) => item.size === selectedSize)

  return (
    <div className="page">
      <nav className="crumbs" aria-label="Breadcrumb">
        <Link to="/products">Products</Link> <span>/</span> {product.name}
      </nav>

      <div className="detail">
        <div className="detail-media">
          <div
            className={`detail-image${zoom ? ' is-zooming' : ''}`}
            onMouseMove={handleZoomMove}
            onMouseLeave={() => setZoom(null)}
          >
            <img
              src={product.image_url}
              alt={product.name}
              style={
                zoom
                  ? { transformOrigin: `${zoom.x}% ${zoom.y}%` }
                  : undefined
              }
            />
            {product.total_stock === 0 && (
              <span className="badge badge-soldout detail-badge">Sold out</span>
            )}
          </div>
          <p className="zoom-hint">Hover the image to zoom</p>
        </div>

        <div className="detail-info">
          <p className="detail-type">{product.garment_type}</p>
          <h1>{product.name}</h1>
          <p className="detail-price">{formatPrice(product.price)}</p>

          <p className="detail-description">{product.description}</p>

          {product.colors.length > 0 && (
            <div className="detail-block">
              <h2>Colors</h2>
              <ul className="chips">
                {product.colors.map((color) => (
                  <li key={color}>{color}</li>
                ))}
              </ul>
            </div>
          )}

          <div className="detail-block">
            <h2>Sizes</h2>
            <ul className="sizes">
              {product.inventory.map((item) => (
                <li key={item.size}>
                  <button
                    type="button"
                    className={`size-button${
                      item.size === selectedSize ? ' selected' : ''
                    }`}
                    disabled={item.quantity === 0}
                    onClick={() => setSelectedSize(item.size)}
                    aria-label={`${item.size} — ${stockLabel(item.quantity)}`}
                  >
                    {item.size}
                  </button>
                </li>
              ))}
            </ul>

            <p className="stock-line">
              {selected
                ? `${selected.size}: ${stockLabel(selected.quantity)}`
                : `${product.total_stock} in stock across all sizes — pick a size for details.`}
            </p>
          </div>

          {product.search_tags.length > 0 && (
            <div className="detail-block">
              <h2>Tags</h2>
              <ul className="chips chips-muted">
                {product.search_tags.map((tag) => (
                  <li key={tag}>{tag}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
