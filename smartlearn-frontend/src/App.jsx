import { useState, useRef } from "react";
import { uploadPDF, askQuestion } from "./api";

export default function App() {
  const [file, setFile] = useState(null);
  const [upload, setUpload] = useState(null);
  const [message, setMessage] = useState("");
  const [answer, setAnswer] = useState(null);
  const [status, setStatus] = useState("idle");
  const [error, setError] = useState(null);
  const fileRef = useRef(null);

  async function handleUpload(e) {
    e.preventDefault();
    if (!file) return;
    setStatus("uploading");
    setError(null);
    try {
      const data = await uploadPDF(file);
      setUpload(data);
      setAnswer(null);
    } catch (err) {
      setError(err.message);
    } finally {
      setStatus("idle");
    }
  }

  async function handleAsk(e) {
    e.preventDefault();
    if (!message.trim()) return;
    setStatus("asking");
    setError(null);
    try {
      const data = await askQuestion(message.trim());
      setAnswer(data);
      setMessage("");
    } catch (err) {
      setError(err.message);
    } finally {
      setStatus("idle");
    }
  }

  return (
    <div className="container">
      <h1>SmartLearn</h1>

      <form className="upload-form" onSubmit={handleUpload}>
        <input
          type="file"
          accept=".pdf"
          ref={fileRef}
          onChange={(e) => setFile(e.target.files?.[0] ?? null)}
        />
        <button type="submit" disabled={status === "uploading" || !file}>
          {status === "uploading" ? "Uploading..." : "Upload PDF"}
        </button>
      </form>

      {upload && (
        <p className="info">
          Uploaded <span className="chip">{upload.pages} pages</span> ({upload.chars} chars)
        </p>
      )}

      {error && <p className="err">{error}</p>}

      {upload && (
        <form className="chat-form" onSubmit={handleAsk}>
          <input
            type="text"
            placeholder="Ask a question about the slides..."
            value={message}
            onChange={(e) => setMessage(e.target.value)}
          />
          <button type="submit" disabled={status === "asking"}>
            {status === "asking" ? "Asking..." : "Ask"}
          </button>
        </form>
      )}

      {answer && (
        <div className="msg">
          {answer.answer ? (
            <>
              <p className="a">{answer.answer}</p>
              {answer.citations.length > 0 && (
                <p className="cites">
                  Citations:{" "}
                  {answer.citations.map((p) => (
                    <span key={p} className="chip">Page {p}</span>
                  ))}
                </p>
              )}
            </>
          ) : (
            <p className="err">The model returned an empty response — try rephrasing your question.</p>
          )}
        </div>
      )}

    </div>
  );
}
