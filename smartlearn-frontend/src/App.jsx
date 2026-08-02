import { useState } from "react"
import { uploadPDF, askQuestion } from "./api.js"

export default function App() {
  const [file, setFile] = useState(null)
  const [upload, setUpload] = useState(null)
  const [message, setMessage] = useState("")
  const [answer, setAnswer] = useState(null)
  const [status, setStatus] = useState("idle")
  const [error, setError] = useState("")

  const busy = status !== "idle"

  async function handleUpload() {
    if (!file) return
    try {
      setStatus("uploading")
      setError("")
      const result = await uploadPDF(file)
      setUpload(result)
      setAnswer(null)
    } catch (e) {
      setError(e.message)
    } finally {
      setStatus("idle")
    }
  }

  async function handleAsk(event) {
    event.preventDefault()
    if (!message.trim()) return
    try {
      setStatus("asking")
      setError("")
      const result = await askQuestion(message.trim())
      setAnswer(result)
    } catch (e) {
      setError(e.message)
    } finally {
      setStatus("idle")
    }
  }

  return (
    <main>
      <h1>SmartLearn Lite</h1>

      {/* Upload section */}
      <section>
        <label htmlFor="pdf-file">PDF file</label>
        <input
          id="pdf-file"
          type="file"
          accept=".pdf"
          onChange={(e) => setFile(e.target.files[0])}
        />
        <button onClick={handleUpload} disabled={!file || busy}>
          {status === "uploading" ? "Uploading…" : "Upload"}
        </button>
      </section>

      {upload && (
        <p>
          Uploaded: {upload.filename} ({upload.pages} pages, {upload.characters}{" "}
          characters)
        </p>
      )}

      {/* Error display */}
      {error && <p role="alert" className="error">{error}</p>}

      {/* Chat section */}
      {upload && (
        <form onSubmit={handleAsk}>
          <label htmlFor="message">Message</label>
          <textarea
            id="message"
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            disabled={busy}
          />
          <button
            type="submit"
            disabled={!message.trim() || busy}
          >
            {status === "asking" ? "Asking…" : "Ask"}
          </button>
        </form>
      )}

      {/* Answer display */}
      {answer && (
        <section>
          <p>{answer.answer}</p>
          {answer.citations.length > 0 && (
            <div>
              {answer.citations.map((page) => (
                <span key={page} className="chip">Page {page}</span>
              ))}
            </div>
          )}
        </section>
      )}
    </main>
  )
}
