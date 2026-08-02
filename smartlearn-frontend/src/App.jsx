import { useState } from "react";
import { uploadPDF, askQuestion } from "./api";

export default function App() {
  const [file, setFile] = useState(null);
  const [upload, setUpload] = useState(null);
  const [message, setMessage] = useState("");
  const [answer, setAnswer] = useState(null);
  const [status, setStatus] = useState("");
  const [error, setError] = useState(null);

  const busy = status !== "";

  async function handleUpload() {
    setUpload(null);
    setError(null);
    setStatus("Uploading…");
    try {
      const data = await uploadPDF(file);
      setUpload(data);
    } catch (e) {
      setError(e.message);
    } finally {
      setStatus("");
    }
  }

  async function handleAsk() {
    setAnswer(null);
    setError(null);
    setStatus("Asking…");
    try {
      const data = await askQuestion(message.trim());
      setAnswer(data);
    } catch (e) {
      setError(e.message);
    } finally {
      setStatus("");
    }
  }

  return (
    <main>
      <h1>SmartLearn Lite</h1>

      <form onSubmit={(e) => e.preventDefault()}>
        <div>
          <label htmlFor="pdf">PDF file</label>
          <input
            id="pdf"
            type="file"
            accept=".pdf"
            onChange={(e) => setFile(e.target.files[0])}
          />
        </div>

        <button type="button" disabled={!file || busy} onClick={handleUpload}>
          Upload
        </button>
      </form>

      {status && <p>{status}</p>}

      {error && <p role="alert">{error}</p>}

      {upload && (
        <p>
          Uploaded: {upload.filename} — {upload.pages} pages, {upload.characters}{" "}
          characters
        </p>
      )}

      <form onSubmit={(e) => e.preventDefault()}>
        <div>
          <label htmlFor="message">Question</label>
          <textarea
            id="message"
            rows={3}
            value={message}
            onChange={(e) => setMessage(e.target.value)}
          />
        </div>

        <button
          type="button"
          disabled={!upload || !message.trim() || busy}
          onClick={handleAsk}
        >
          Ask
        </button>
      </form>

      {answer && (
        <div>
          <p>{answer.answer}</p>
          <div>
            {answer.citations.map((page) => (
              <span key={page}>Page {page}</span>
            ))}
          </div>
        </div>
      )}
    </main>
  );
}
