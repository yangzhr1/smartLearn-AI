import { useState } from "react";
import { uploadPDF } from "./api.js";

export default function PdfUploader({ disabled, onUpload, onBusyChange, onError }) {
  const [file, setFile] = useState(null);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);

  const isDisabled = disabled || loading;

  async function handleUpload() {
    if (!file) return;
    setResult(null);
    setLoading(true);
    onBusyChange(true);

    try {
      const data = await uploadPDF(file);
      setResult(data);
      onUpload(data);
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
      <h2>Upload PDF</h2>
      <label htmlFor="file-input">Select a PDF file:</label>
      <input
        id="file-input"
        type="file"
        accept=".pdf,application/pdf"
        disabled={isDisabled}
        onChange={(e) => setFile(e.target.files[0])}
      />
      <button disabled={isDisabled || !file} onClick={handleUpload}>
        Upload
        {loading && <span className="loading-text">Uploading...</span>}
      </button>

      {result && (
        <div className="upload-result">
          Uploaded: {result.filename} — {result.pages} pages,{" "}
          {result.characters.toLocaleString()} characters
        </div>
      )}
    </section>
  );
}
