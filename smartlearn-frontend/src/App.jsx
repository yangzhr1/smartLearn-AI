import { useState } from "react"
import { askQuestion, uploadPDF } from "./api"

export default function App() {
  const [file, setFile] = useState(null)
  const [upload, setUpload] = useState(null)
  const [message, setMessage] = useState("")
  const [answer, setAnswer] = useState(null)
  const [status, setStatus] = useState("idle")
  const [error, setError] = useState("")

  const busy = status !== "idle"

  async function handleUpload(event) {
    event.preventDefault()
    if (!file || busy) return
    try {
      setStatus("uploading")
      setError("")
      setUpload(await uploadPDF(file))
      setAnswer(null)
    } catch (requestError) {
      setError(requestError.message || "Upload failed.")
    } finally {
      setStatus("idle")
    }
  }

  async function handleAsk(event) {
    event.preventDefault()
    if (!upload || !message.trim() || busy) return
    try {
      setStatus("asking")
      setError("")
      setAnswer(await askQuestion(message.trim()))
    } catch (requestError) {
      setError(requestError.message || "Chat failed.")
    } finally {
      setStatus("idle")
    }
  }

  return (
    <main>
      <h1>SmartLearn Lite</h1>

      <form onSubmit={handleUpload} className="card">
        <label htmlFor="file">Choose a PDF</label>
        <input
          id="file"
          type="file"
          accept="application/pdf"
          onChange={(event) => setFile(event.target.files[0] || null)}
        />
        <button type="submit" disabled={!file || busy}>
          {status === "uploading" ? "Uploading…" : "Upload"}
        </button>
      </form>

      {upload && (
        <p className="receipt">
          Uploaded {upload.filename}: {upload.pages} pages,{" "}
          {upload.characters.toLocaleString()} characters.
        </p>
      )}

      <form onSubmit={handleAsk} className="card">
        <label htmlFor="message">Message</label>
        <textarea
          id="message"
          value={message}
          onChange={(event) => setMessage(event.target.value)}
          placeholder="Ask a question about the PDF…"
        />
        <button type="submit" disabled={!upload || !message.trim() || busy}>
          {status === "asking" ? "Asking…" : "Ask"}
        </button>
      </form>

      {error && (
        <p role="alert" className="error">
          {error}
        </p>
      )}

      {answer && (
        <section className="card answer" aria-label="Answer">
          <p>{answer.answer}</p>
          {answer.citations?.length > 0 && (
            <div className="citations" aria-label="Cited pages">
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
