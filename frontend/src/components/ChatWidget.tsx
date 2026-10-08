import { useEffect, useRef, useState, type FormEvent } from 'react'
import Markdown from 'react-markdown'
import { Link, useLocation } from 'react-router-dom'
import {
  fetchChatHistory,
  formatPrice,
  sendChatMessage,
  type Product,
} from '../api'
import { useAuth } from '../auth'
import './ChatWidget.css'

interface Message {
  id: number
  role: 'user' | 'assistant'
  content: string
  products?: Product[]
}

const GREETING: Message = {
  id: 0,
  role: 'assistant',
  content:
    "Hi! I'm the Campus Customs shop assistant. Ask me about sizes, colors or what we have in stock.",
}

/** Pull the product id out of the path when on a detail page, else null. */
function productIdFromPath(pathname: string): string | null {
  const match = pathname.match(/^\/products\/([^/]+)$/)
  return match ? decodeURIComponent(match[1]) : null
}

/** One-tap prompts to get a shopper started. */
const QUICK_REPLIES = [
  'What hoodies do you have?',
  'Show me crewnecks under $60',
  'Anything for the residential colleges?',
  'What sizes come in navy?',
]

export default function ChatWidget() {
  const { user } = useAuth()
  const location = useLocation()

  const [open, setOpen] = useState(false)
  const [messages, setMessages] = useState<Message[]>([GREETING])
  const [draft, setDraft] = useState('')
  const [pending, setPending] = useState(false)
  const nextId = useRef(1)
  const scrollRef = useRef<HTMLDivElement>(null)

  // When the signed-in shopper changes (login/logout/return), reload their saved
  // conversation. Logging out resets to the greeting.
  useEffect(() => {
    let cancelled = false

    if (!user) {
      setMessages([GREETING])
      return
    }

    fetchChatHistory()
      .then((history) => {
        if (cancelled) return
        if (history.length === 0) {
          setMessages([GREETING])
          return
        }
        setMessages([
          GREETING,
          ...history.map((turn) => ({
            id: nextId.current++,
            role: turn.role,
            content: turn.content,
            products: turn.products,
          })),
        ])
      })
      .catch(() => {
        if (!cancelled) setMessages([GREETING])
      })

    return () => {
      cancelled = true
    }
  }, [user])

  // Keep the newest message in view as the thread grows.
  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight })
  }, [messages, open])

  async function send(text: string) {
    const trimmed = text.trim()
    if (!trimmed || pending) return

    setMessages((prev) => [
      ...prev,
      { id: nextId.current++, role: 'user', content: trimmed },
    ])
    setDraft('')
    setPending(true)

    try {
      // Tell the agent which product page we're on, so "this" resolves.
      const { reply, products } = await sendChatMessage(
        trimmed,
        productIdFromPath(location.pathname),
      )
      setMessages((prev) => [
        ...prev,
        { id: nextId.current++, role: 'assistant', content: reply, products },
      ])
    } catch (err: unknown) {
      setMessages((prev) => [
        ...prev,
        {
          id: nextId.current++,
          role: 'assistant',
          content:
            err instanceof Error
              ? `Sorry — I could not reach the shop assistant (${err.message}).`
              : 'Sorry — something went wrong.',
        },
      ])
    } finally {
      setPending(false)
    }
  }

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    void send(draft)
  }

  // Quick replies show until the shopper has sent their first message.
  const showQuickReplies =
    !pending && messages.filter((m) => m.role === 'user').length === 0

  return (
    <div className="chat">
      {open && (
        <section className="chat-panel" aria-label="Shop assistant">
          <header className="chat-header">
            <div className="chat-avatar" aria-hidden="true">
              CC
            </div>
            <div className="chat-ident">
              <strong>Campus Customs Assistant</strong>
              <span className="chat-status">
                <span className="chat-dot" /> Online · asks the catalogue
              </span>
            </div>
            <button
              type="button"
              className="chat-close"
              onClick={() => setOpen(false)}
              aria-label="Close chat"
            >
              ×
            </button>
          </header>

          <div className="chat-log" ref={scrollRef}>
            {messages.map((message) => (
              <div key={message.id} className={`msg msg-${message.role}`}>
                <div className={`bubble bubble-${message.role}`}>
                  {message.role === 'assistant' ? (
                    // The agent replies in markdown (bold, bullet lists); render
                    // it so "$68" and lists display properly instead of as raw
                    // ** and - characters. react-markdown emits no raw HTML.
                    <Markdown>{message.content}</Markdown>
                  ) : (
                    message.content
                  )}
                </div>

                {message.products && message.products.length > 0 && (
                  <div className="chat-cards">
                    {message.products.map((product) => (
                      <Link
                        key={product.product_id}
                        to={`/products/${product.product_id}`}
                        className="chat-card"
                        onClick={() => setOpen(false)}
                      >
                        <img src={product.image_url} alt={product.name} />
                        <div className="chat-card-body">
                          <span className="chat-card-name">{product.name}</span>
                          <span className="chat-card-price">
                            {formatPrice(product.price)}
                          </span>
                          <span className="chat-card-info">
                            {product.description}
                          </span>
                        </div>
                      </Link>
                    ))}
                  </div>
                )}
              </div>
            ))}
            {pending && (
              <div className="msg msg-assistant">
                <div className="bubble bubble-assistant typing" aria-label="Typing">
                  <span className="typing-dot" />
                  <span className="typing-dot" />
                  <span className="typing-dot" />
                </div>
              </div>
            )}

            {showQuickReplies && (
              <div className="quick-replies" aria-label="Suggested questions">
                {QUICK_REPLIES.map((q) => (
                  <button
                    key={q}
                    type="button"
                    className="quick-chip"
                    onClick={() => void send(q)}
                  >
                    {q}
                  </button>
                ))}
              </div>
            )}
          </div>

          <form className="chat-input" onSubmit={handleSubmit}>
            <input
              type="text"
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
              placeholder="Ask about a product…"
              aria-label="Message"
            />
            <button
              type="submit"
              className="btn btn-accent chat-send"
              disabled={!draft.trim() || pending}
            >
              Send
            </button>
          </form>
        </section>
      )}

      <button
        type="button"
        className={`chat-toggle${open ? ' is-open' : ''}`}
        onClick={() => setOpen((prev) => !prev)}
        aria-expanded={open}
        aria-label={open ? 'Close shop assistant' : 'Open shop assistant'}
      >
        {open ? (
          '×'
        ) : (
          <>
            <span className="chat-toggle-pulse" aria-hidden="true" />
            <span className="chat-toggle-label">Ask us</span>
          </>
        )}
      </button>
    </div>
  )
}
