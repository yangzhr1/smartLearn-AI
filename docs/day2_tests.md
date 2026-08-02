# Day 2 Local Test Record

Result codes: PASS / FAIL (with actual status).

## Backend (`/docs` / curl) — Lab A

| Test | Input | Expected | Actual |
|---|---|---|---|
| `GET /` | — | 200, message | PASS — 200, `{"message":"SmartLearn Lite API is running"}` |
| `GET /health` | — | 200, `{"ok": true}` | PASS — 200, `{"ok":true}` |
| Upload text PDF | `test_files/sample.pdf`, `chat_id=day2-demo` | 200, page + char counts | PASS — 200, 11 pages, 32613 chars |
| Non-PDF | `test_files/non_pdf.txt` | 400 | PASS — 400 `Only PDF files are accepted.` |
| Empty file | `test_files/empty.pdf` | 400 | PASS — 400 `The uploaded file is empty.` |
| Scanned PDF | `test_files/sample-scan.pdf` | 422, OCR not supported | PASS — 422, explains OCR not supported |
| Over 30 pages | `test_files/large_file.pdf` | 400 | PASS — 400 `PDF must contain at most 30 pages` |
| Chat known question | "dimension of each attention head?" | answer + citations includes 5 | PASS — answer cites 64, `citations:[5]` |
| Chat unknown question | "accuracy on ImageNet?" | answer admits insufficient evidence | PASS — "does not report any accuracy… on the ImageNet benchmark" |
| Chat fake id | `chat_id=nope` | 404, upload-first guidance | PASS — 404 with upload-first guidance |
| CORS preflight (allowed origin) | `Origin: http://localhost:5173` | allow-origin header | PASS |
| CORS preflight (env origin) | `ALLOWED_ORIGINS=…,https://smartlearn-lite.example` | `access-control-allow-origin: https://smartlearn-lite.example` | PASS |

## Frontend (`npm run build` / `npm run lint`) — Lab B

| Check | Expected | Actual |
|---|---|---|
| `npm run build` | exits 0, creates `dist/` | PASS — vite build OK, dist/ created |
| `npm run lint` | exits 0 | PASS — 0 problems |
| `dist/`, `node_modules/` untracked | yes | PASS — both gitignored |

## End-to-end journey (fresh reload) — Lab B §2.7

Browser click-through with DevTools Network is performed by the student. The request layer was verified programmatically:

| # | Action | Expected | Actual |
|---|---|---|---|
| 1 | Upload disabled until a file is selected | yes | (browser) |
| 2 | Valid PDF uploads via `/upload?chat_id=day2-demo` | success receipt | PASS — 200 with page/char counts |
| 3 | Ask disabled before upload and for blank message | yes | (browser) |
| 4 | Known message → answer + Page chips | yes | PASS — cited answer, `citations:[7,8]` |
| 5 | Absent-information message → no invented evidence | yes | PASS — admits insufficient evidence |
| 6 | Backend shutdown → visible frontend error | yes | (browser) |
| 7 | Backend restart → re-upload required | yes | PASS — 404 after restart until re-upload |

## Homework questions (Transformer paper, `test_files/sample.pdf`)

| # | Question | Expected page | Actual |
|---|---|---|---|
| 1 | What is the dimension of each attention head? | 5 | PASS — `[Page 5]` |
| 2 | What optimizer and learning-rate schedule? | 7 | PASS — `[Page 7]` |
| 3 | What regularization methods? | 7 | PASS — `[Pages 7–8]` |
| 4 | What accuracy on ImageNet? | None (insufficient evidence) | PASS — admits not reported |
