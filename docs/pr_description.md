## What
Adds the SmartLearn Lite vertical slice: upload a PDF, ask questions
about it, and get answers with page-number citations.

- **Backend** (`smartlearn-backend/`): FastAPI service with
  `GET /health`, `POST /upload?chat_id=`, and `POST /chat`
- **Frontend** (`smartlearn-frontend/`): React/Vite single-page app
  with upload → ask → cited answer + Page chips
- **Delivery**: Railway `Dockerfile` + deployment/test evidence docs

## How
- `POST /upload?chat_id=` parses the PDF into per-page records
  (pypdf, capped at 30 pages), validates input, and stores the records
  in a temporary in-memory dictionary — no file is saved to disk.
- `POST /chat` grounds every answer in the stored page text via a
  strict "cite with [Page X], never invent a page number" prompt,
  then returns only citations that point to pages that actually exist.
- The browser calls both routes through `src/api.js` (fixed
  `CHAT_ID="day2-demo"`, `VITE_API_URL` fallback to localhost:8000).
  `App.jsx` owns the six core states: file, upload, message, answer,
  status, error.
- CORS reads comma-separated `ALLOWED_ORIGINS` from the environment —
  no hard-coded localhost list.

## Proof
All run locally on the `sample.pdf` fixture (the Transformer paper):

| Test | Result |
|---|---|
| `GET /health` | 200 `{"ok": true}` |
| Upload `sample.pdf` | 200, 11 pages / 32,613 chars |
| Non-PDF / empty / scanned / >30-page PDFs | 400 / 400 / 422 (OCR not supported) / 400 |
| "dimension of each attention head?" | cited **Page 5** |
| "optimizer and learning-rate schedule?" | cited **Page 7** |
| "regularization methods?" | cited **Pages 7–8** |
| "accuracy on ImageNet benchmark?" | honestly admits it is not reported |
| Fake `chat_id` | 404 with upload-first guidance |
| CORS preflight (env origin) | `access-control-allow-origin` echoed, unlisted origins blocked |
| `npm run build` / `npm run lint` | both pass, 0 errors |

## Limit
- Chat state is **in-memory**: any backend restart clears uploaded
  documents, so re-upload is required (the frontend surfaces this as a
  clear error). No database by design.
- LLM provider is **DeepSeek directly** (`DEEPSEEK_API_KEY`,
  `deepseek-v4-flash`) because no OpenRouter key is available in this
  environment; if `OPENROUTER_API_KEY` is ever set, the same service
  uses OpenRouter (`openrouter/free`).
- Short PDFs only (≤30 pages) — no chunking/RAG yet (Day 3).
