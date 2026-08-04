import { useState } from "react"
import { uploadPDF } from "./api"
import ChatPanel from "./ChatPanel"
import PdfPreview from "./PdfPreview"

export default function App() {
  const [file, setFile] = useState(null)
  const [upload, setUpload] = useState(null)
  const [uploadKey, setUploadKey] = useState(0)
  const [activePage, setActivePage] = useState(1)
  const [status, setStatus] = useState("idle")
  const [error, setError] = useState("")

  const busy = status !== "idle"

  async function handleUpload(event) {
    event.preventDefault()
    if (!file || busy) return
    try {
      setStatus("uploading")
      setError("")
      const result = await uploadPDF(file)
      setUpload(result)
      setActivePage(1)
      // Remount ChatPanel so the old message list disappears.
      setUploadKey((key) => key + 1)
    } catch (requestError) {
      setError(requestError.message || "Upload failed.")
    } finally {
      setStatus("idle")
    }
  }

  function handleJumpToPage(page) {
    setActivePage(page)
  }

  return (
    <main>
      <h1>SmartLearn Lite</h1>

      <form onSubmit={handleUpload} className="card uploader">
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

      {error && (
        <p role="alert" className="error">
          {error}
        </p>
      )}

      <div className="workspace">
        <PdfPreview upload={upload} activePage={activePage} previewKey={uploadKey} />
        <ChatPanel
          key={uploadKey}
          enabled={Boolean(upload)}
          disabled={!upload}
          onJumpToPage={handleJumpToPage}
        />
      </div>
    </main>
  )
}
