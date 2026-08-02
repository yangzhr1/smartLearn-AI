import { useState } from "react";
import PdfUploader from "./PdfUploader.jsx";
import ChatPanel from "./ChatPanel.jsx";

export default function App() {
  const [upload, setUpload] = useState(null);
  const [error, setError] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [asking, setAsking] = useState(false);

  return (
    <main>
      <h1>SmartLearn Lite</h1>

      <PdfUploader
        disabled={asking}
        onUpload={setUpload}
        onBusyChange={setUploading}
        onError={setError}
      />

      <ChatPanel
        disabled={uploading}
        hasDocument={upload !== null}
        onBusyChange={setAsking}
        onError={setError}
      />

      {error && (
        <section role="alert" className="error">
          <strong>Error:</strong> {error}
        </section>
      )}
    </main>
  );
}
