import { useState } from "react";
import { uploadPDF, askQuestion } from "./api";

export default function App() {
  const [file, setFile] = useState(null);
  const [upload, setUpload] = useState(null);
  const [message, setMessage] = useState("");
  const [answer, setAnswer] = useState(null);
  const [status, setStatus] = useState("idle");
  const [error, setError] = useState("");

  const busy = status === "uploading" || status === "asking";

  function handleFileChange(e) {
    const selected = e.target.files[0];
    if (!selected) return;
    setFile(selected);
    setUpload(null);
    setAnswer(null);
    setError("");
  }

  async function handleUpload(e) {
    e.preventDefault();
    setError("");
    setUpload(null);
    setAnswer(null);
    setStatus("uploading");
    try {
      const data = await uploadPDF(file);
      setUpload(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setStatus("idle");
    }
  }

  async function handleAsk(e) {
    e.preventDefault();
    const trimmed = message.trim();
    if (!trimmed) return;
    setError("");
    setAnswer(null);
    setStatus("asking");
    try {
      const data = await askQuestion(trimmed);
      setAnswer(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setStatus("idle");
    }
  }

  return (
    <main>
      <h1>SmartLearn Lite</h1>
      <p>AI-powered learning assistant — upload a PDF and ask questions.</p>

      <section>
        <h2>Upload</h2>
        <form onSubmit={handleUpload}>
          <label htmlFor="file-input">PDF file</label>
          <input
            id="file-input"
            type="file"
            accept=".pdf"
            onChange={handleFileChange}
          />
          <button type="submit" disabled={!file || busy}>
            Upload
          </button>
        </form>
        {status === "uploading" && <p>Uploading...</p>}
        {upload && (
          <ul>
            <li>File: {upload.filename}</li>
            <li>Pages: {upload.page_count}</li>
            <li>Characters: {upload.character_count}</li>
          </ul>
        )}
      </section>

      <section>
        <h2>Chat</h2>
        <form onSubmit={handleAsk}>
          <label htmlFor="message-input">Your question</label>
          <textarea
            id="message-input"
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            disabled={!upload || busy}
          />
          <button
            type="submit"
            disabled={!upload || !message.trim() || busy}
          >
            Ask
          </button>
        </form>
        {status === "asking" && <p>Asking...</p>}
      </section>

      {error && <div role="alert">{error}</div>}

      {answer && (
        <section>
          <h2>Answer</h2>
          <p>{answer.answer}</p>
          {answer.citations.length > 0 && (
            <ul>
              {answer.citations.map((page) => (
                <li key={page}>Page {page}</li>
              ))}
            </ul>
          )}
        </section>
      )}
    </main>
  );
}
