import { useState } from "react";
import { askQuestion } from "./api.js";

export default function ChatPanel({ disabled, hasDocument, onBusyChange, onError }) {
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(false);
  const [answer, setAnswer] = useState(null);

  const isDisabled = disabled || loading;

  async function handleAsk() {
    if (!message.trim()) return;
    setAnswer(null);
    setLoading(true);
    onBusyChange(true);

    try {
      const data = await askQuestion(message.trim());
      setAnswer(data);
      onError(null);
    } catch (err) {
      onError(err.message);
    } finally {
      setLoading(false);
      onBusyChange(false);
    }
  }

  return (
    <section className="card">
      <h2>Ask a question</h2>
      <label htmlFor="message-input">Your question:</label>
      <input
        id="message-input"
        type="text"
        placeholder="Ask about the document..."
        value={message}
        disabled={isDisabled}
        onChange={(e) => setMessage(e.target.value)}
      />
      <button
        disabled={isDisabled || !hasDocument || !message.trim()}
        onClick={handleAsk}
      >
        Ask
        {loading && <span className="loading-text">Thinking...</span>}
      </button>

      {answer && (
        <div className="answer-section">
          <h3>Answer</h3>
          <p className="answer-text">{answer.answer}</p>

          {answer.citations && answer.citations.length > 0 && (
            <div className="citations">
              <strong>Cited pages: </strong>
              {answer.citations.map((page) => (
                <span key={page} className="page-chip">
                  Page {page}
                </span>
              ))}
            </div>
          )}
        </div>
      )}
    </section>
  );
}
