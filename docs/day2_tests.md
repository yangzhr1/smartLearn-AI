# Day 2 Test Evidence

## Lab A — Backend verification (1.10 / 1.13 / 1.14)

Test files: `test_files/` (sample.pdf: 11 pages; sample-scan.pdf: scanned, no text).

| Case | Input | Status | Response |
|---|---|---|---|
| Health | `GET /health` | 200 | `{"ok": true}` |
| Valid PDF | `POST /upload?chat_id=day2-demo`, sample.pdf | 200 | `{"status": "ok", "filename": "sample.pdf", "pages": 11, "characters": 32613}` |
| Non-PDF | non_pdf.txt | 400 | `{"detail": "Please upload a PDF"}` |
| Empty file | empty.pdf | 400 | `{"detail": "Empty file"}` |
| Scanned PDF | sample-scan.pdf | 422 | `{"detail": "No text; OCR unsupported"}` |
| Over 30 pages | large_file.pdf | 400 | `{"detail": "PDF must contain at most 30 pages"}` |
| Known question | `/chat` "dimension of each attention head" | 200 | answer cites `[Page 4/5]`, `citations: [4] or [5]` |
| Unknown question | `/chat` "ImageNet accuracy" | 200 | admits document provides no information, `citations: []` |
| Fake chat_id | `/chat` with `chat_id: fake` | 404 | `{"detail": "chat_id not found. Upload first."}` |

Invalid page tags are removed from the answer (`[Page 99]` deleted) and filtered from citations.

CORS: preflight `OPTIONS` from `http://localhost:5173` returns
`access-control-allow-origin: http://localhost:5173`; unlisted origins get no header.

## Lab B — End-to-end browser journey (2.7), Playwright + Chrome headless

| # | Step | Result |
|---|---|---|
| 1 | Upload disabled until file selected | PASS |
| 2 | Select sample.pdf, upload, receipt shown | PASS (11 pages, 32613 characters) |
| 3 | Ask enabled after upload | PASS |
| 4 | Known message returns answer + Page chips | PASS (`Page 5`) |
| 5 | Absent-info message: honest answer, no citations | PASS |
| 6 | Backend stopped → visible frontend error | PASS (`Failed to fetch`) |
| 7 | Backend restarted → re-upload required (memory cleared) | PASS |

Screenshots: `docs/day2_cited_answer.png`, `docs/day2_honest_unknown.png`,
`docs/day2_backend_down.png`, `docs/day2_final_flow.png`.

## Lab B — Build and lint (2.9)

- `npm run build` — PASS (Vite production build, dist/ created)
- `npm run lint` — PASS (0 errors)
- `node_modules/` and `dist/` untracked; `package-lock.json` committed
