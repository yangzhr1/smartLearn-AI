import { useState } from "react"
import { askQuestion, uploadPDF } from "./api.js"

export default function App() {
  const [file, setFile] = useState(null)
  const [message, setMessage] = useState("")
  const [answer, setAnswer] = useState(null)
  const [status, setStatus] = useState("idle")
  const [error, setError] = useState("")

  const uploading = status === "uploading"
  const asking = status === "asking"

  async function handleUpload() {
    if (!file) return
    setStatus("uploading")
    setError("")
    try {
      const result = await uploadPDF(file)
      setAnswer({ ...result, citations: [] })
    } catch (err) {
      setError(err.message)
    } finally {
      setStatus("idle")
    }
  }

  async function handleAsk() {
    const trimmed = message.trim()
    if (!trimmed || asking) return
    setStatus("asking")
    setError("")
    try {
      const result = await askQuestion(trimmed)
      setAnswer(result)
    } catch (err) {
      setError(err.message)
    } finally {
      setStatus("idle")
    }
  }

  return (
    <main className="app">
      <h1>SmartLearn Lite</h1>

      <section className="card">
        <h2>Upload a PDF</h2>
        <input
          type="file"
          accept="application/pdf"
          onChange={(e) => setFile(e.target.files[0])}
        />
        <button onClick={handleUpload} disabled={!file || uploading}>
          {uploading ? "Uploading..." : "Upload"}
        </button>
        {answer?.pages != null && (
          <p className="upload-result">
            {answer.filename}: {answer.pages} pages, {answer.characters} characters
          </p>
        )}
      </section>

      <section className="card">
        <h2>Ask a question</h2>
        <input
          type="text"
          value={message}
          placeholder="Ask about the PDF..."
          onChange={(e) => setMessage(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter") handleAsk()
          }}
        />
        <button onClick={handleAsk} disabled={asking}>
          {asking ? "Asking..." : "Ask"}
        </button>
      </section>

      {error && <p className="error">{error}</p>}

      {answer?.answer && (
        <section className="card answer">
          <p>{answer.answer}</p>
          {answer.citations?.length > 0 && (
            <div className="chips">
              {answer.citations.map((page) => (
                <span key={page} className="chip">
                  Page {page}
                </span>
              ))}
            </div>
          )}
        </section>
      )}
    </main>
  )
}
