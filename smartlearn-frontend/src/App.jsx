import { useState } from "react";
import { uploadPDF, askQuestion } from "./api.js";

function App() {
  const [file, setFile] = useState(null);
  const [upload, setUpload] = useState(null);
  const [message, setMessage] = useState("");
  const [answer, setAnswer] = useState(null);
  const [status, setStatus] = useState("idle");
  const [error, setError] = useState(null);

  const isBusy = status !== "idle";

  async function handleUpload(e) {
    e.preventDefault();
    setStatus("uploading");
    setError(null);
    setAnswer(null);
    try {
      const result = await uploadPDF(file);
      setUpload(result);
      setStatus("idle");
    } catch (err) {
      setError(err.message);
      setStatus("idle");
    }
  }

  async function handleAsk(e) {
    e.preventDefault();
    setStatus("asking");
    setError(null);
    try {
      const result = await askQuestion(message.trim());
      setAnswer(result);
      setStatus("idle");
    } catch (err) {
      setError(err.message);
      setStatus("idle");
    }
  }

  return (
    <div className="container">
      <h1>SmartLearn AI</h1>

      <form onSubmit={handleUpload}>
        <label htmlFor="pdf-file">PDF file</label>
        <input
          id="pdf-file"
          type="file"
          accept=".pdf,application/pdf"
          onChange={(e) => setFile(e.target.files[0])}
        />
        <button type="submit" disabled={!file || isBusy}>
          {status === "uploading" ? "Uploading…" : "Upload"}
        </button>
      </form>

      {upload && (
        <p>
          Uploaded: {upload.filename} ({upload.pages} pages,{" "}
          {upload.characters} characters)
        </p>
      )}

      {upload && (
        <form onSubmit={handleAsk}>
          <label htmlFor="question">Question</label>
          <textarea
            id="question"
            value={message}
            onChange={(e) => setMessage(e.target.value)}
          />
          <button type="submit" disabled={!message.trim() || isBusy}>
            {status === "asking" ? "Asking…" : "Ask"}
          </button>
        </form>
      )}

      {status !== "idle" && (
        <p>{status === "uploading" ? "Uploading…" : "Asking…"}</p>
      )}

      {error && <p role="alert">{error}</p>}

      {answer && (
        <section>
          <p>{answer.answer}</p>
          <div>
            {answer.citations.map((c) => (
              <span key={c}>{c}</span>
            ))}
          </div>
        </section>
      )}
    </div>
  );
}

export default App;
// 决定页面显示什么内容
