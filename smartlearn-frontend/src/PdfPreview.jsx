import { getDocumentFileURL } from "./api"

export default function PdfPreview({ upload, activePage, previewKey }) {
  if (!upload) {
    return (
      <section className="panel preview" aria-label="PDF preview">
        <p className="placeholder">Upload a PDF to preview it here.</p>
      </section>
    )
  }
  return (
    <section className="panel preview" aria-label="PDF preview">
      <p className="preview-label">
        {upload.filename} — Page {activePage}
      </p>
      <iframe
        key={previewKey}
        title="Uploaded PDF"
        src={getDocumentFileURL(activePage)}
        className="pdf-frame"
      />
    </section>
  )
}
