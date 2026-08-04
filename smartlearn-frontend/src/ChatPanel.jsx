import { useState } from "react"
import { askQuestion } from "./api"

export default function ChatPanel({ enabled, onBusy, disabled, onJumpToPage }) {
  const [message, setMessage] = useState("")
  const [messages, setMessages] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState("")

  const cannotAsk = disabled || loading || !enabled

  async function handleSubmit(event) {
    event.preventDefault()
    const text = message.trim()
    if (!text || cannotAsk) return
    try {
      setLoading(true)
      setError("")
      onBusy?.(true)
      setMessages((prev) => [...prev, { role: "user", content: text }])
      const result = await askQuestion(text)
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: result.answer,
          citations: result.citations || [],
          sources: result.sources || [],
        },
      ])
      setMessage("")
    } catch (requestError) {
      setError(requestError.message || "Chat failed.")
    } finally {
      setLoading(false)
      onBusy?.(false)
    }
  }

  return (
    <section className="panel chat" aria-label="Chat">
      <h2>Ask about the PDF</h2>
      <div className="messages" role="log" aria-live="polite">
        {messages.length === 0 && (
          <p className="placeholder">Ask a question about the uploaded PDF…</p>
        )}
        {messages.map((msg, index) => (
          <div key={index} className={`message ${msg.role}`}>
            <p>{msg.content}</p>
            {msg.role === "assistant" && msg.citations?.length > 0 && (
              <div className="citation-buttons">
                {msg.citations.map((page) => (
                  <button
                    key={page}
                    type="button"
                    className="chip"
                    onClick={() => onJumpToPage?.(page)}
                  >
                    Page {page}
                  </button>
                ))}
              </div>
            )}
          </div>
        ))}
      </div>
      <form onSubmit={handleSubmit}>
        <label htmlFor="message">Message</label>
        <textarea
          id="message"
          value={message}
          onChange={(event) => setMessage(event.target.value)}
          placeholder="Ask a question about the PDF…"
        />
        <button type="submit" disabled={!message.trim() || cannotAsk}>
          {loading ? "Asking…" : "Ask"}
        </button>
      </form>
      {error && <p role="alert" className="error">{error}</p>}
    </section>
  )
}
