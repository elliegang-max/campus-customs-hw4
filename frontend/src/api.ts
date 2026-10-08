/** Shapes returned by the FastAPI backend in `backend/main.py`. */

export interface InventoryItem {
  size: string
  quantity: number
}

export interface Product {
  product_id: string
  name: string
  garment_type: string
  description: string
  colors: string[]
  search_tags: string[]
  image_file_path: string
  image_url: string
  price: number
  inventory: InventoryItem[]
  total_stock: number
}

async function getJson<T>(path: string): Promise<T> {
  const response = await fetch(path)
  if (!response.ok) {
    throw new Error(`${response.status} ${response.statusText}`)
  }
  return (await response.json()) as T
}

export function fetchProducts(): Promise<Product[]> {
  return getJson<Product[]>('/api/products')
}

export function fetchProduct(productId: string): Promise<Product> {
  return getJson<Product>(`/api/products/${encodeURIComponent(productId)}`)
}

export function formatPrice(price: number): string {
  return `$${price.toFixed(2)}`
}

export interface ChatResponse {
  reply: string
  products: Product[]
}

export async function sendChatMessage(
  message: string,
  currentProductId: string | null = null,
): Promise<ChatResponse> {
  const response = await fetch('/api/chat', {
    method: 'POST',
    credentials: 'include',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      message,
      current_product_id: currentProductId,
    }),
  })
  if (!response.ok) {
    throw new Error(`${response.status} ${response.statusText}`)
  }
  return (await response.json()) as ChatResponse
}

export interface ChatHistoryMessage {
  role: 'user' | 'assistant'
  content: string
  products: Product[]
  created_at: string
}

/** The signed-in shopper's saved conversation; [] when nobody is signed in. */
export async function fetchChatHistory(): Promise<ChatHistoryMessage[]> {
  const response = await fetch('/api/chat/history', { credentials: 'include' })
  if (!response.ok) {
    throw new Error(`${response.status} ${response.statusText}`)
  }
  return (await response.json()) as ChatHistoryMessage[]
}
