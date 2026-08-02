import { useState } from "react";
import { uploadPDF, askQuestion } from "./api";

export default function App() {
  const [file, setFile] = useState(null);
  const [upload, setUpload] = useState(null);
  const [message, setMessage] = useState("");
  const [answer, setAnswer] = useState(null);
  const [status, setStatus] = useState("idle");
  const [error, setError] = useState(null);

  async function handleUpload() {
    if (!file) return;

    setAnswer(null);
    setError(null);
    setStatus("uploading");

    try {
      const result = await uploadPDF(file);
      setUpload(result);
    } catch (err) {
      setError(err.message || "Failed to upload PDF");
    } finally {
      setStatus("idle");
    }
  }

  async function handleAsk() {
    if (!upload || !message.trim()) return;

    setAnswer(null);
    setError(null);
    setStatus("asking");

    try {
      const result = await askQuestion(message.trim());
      setAnswer(result);
    } catch (err) {
      setError(err.message || "Failed to get answer");
    } finally {
      setStatus("idle");
    }
  }

  const isBusy = status !== "idle";

  return (
    <div className="app">
      <h1>SmartLearn Lite</h1>
      <p>Your AI-powered learning assistant.</p>

      <form onSubmit={(e) => e.preventDefault()}>
        <div>
          <label htmlFor="pdf">PDF file</label>
          <input
            id="pdf"
            type="file"
            accept=".pdf"
            onChange={(e) => setFile(e.target.files[0] || null)}
          />
        </div>

        <button type="button" disabled={!file || isBusy} onClick={handleUpload}>
          Upload
        </button>
      </form>

      {status === "uploading" && <p>Uploading...</p>}

      {upload && (
        <p>
          Uploaded: {upload.filename} ({upload.pages} pages, {upload.characters}{" "}
          characters)
        </p>
      )}

      <form onSubmit={(e) => e.preventDefault()}>
        <div>
          <label htmlFor="message">Question</label>
          <textarea
            id="message"
            rows={4}
            value={message}
            onChange={(e) => setMessage(e.target.value)}
          />
        </div>

        <button
          type="button"
          disabled={!upload || !message.trim() || isBusy}
          onClick={handleAsk}
        >
          Ask
        </button>
      </form>

      {status === "asking" && <p>Asking...</p>}

      {error && <p role="alert">{error}</p>}

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
    </div>
  );
}
