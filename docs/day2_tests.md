# Day 2 — End-to-End Test Log

## Setup

| Terminal | Command |
|----------|---------|
| Backend (venv) | `cd C:\Users\gianl\Desktop\projects\smartlearn-agent\smartLearn-AI` → `smartlearn-backend\venv\Scripts\activate` → `uvicorn smartlearn-backend.main:app --reload` |
| Frontend (plain) | `cd C:\Users\gianl\Desktop\projects\smartlearn-agent\smartLearn-AI\smartlearn-frontend` → `npm run dev` |
| Browser | `http://localhost:5173` — DevTools → Network tab open |

## Tests

| # | Action | Expected | Actual |
|---|---|---|---|
| 1 | Fresh reload — observe Upload button | Disabled until a file is selected | |
| 2 | Select `test_files\sample.pdf` → click Upload | `200` from `/upload?chat_id=day2-demo`, filename/pages/chars appear | |
| 3 | Before upload, observe Ask button | Disabled before upload and for blank message | |
| 4 | Type "What is the main conclusion of the document?" → click Ask | Answer includes `[Page X]`, page chips appear below answer | |
| 5 | Clear message, type "What is the capital of France?" → click Ask | Answer says the document does not provide this information, no invented evidence | |
| 6 | Stop Uvicorn (`Ctrl+C`), try Upload | Red error box with `role="alert"` appears, no crash | |
| 7 | Restart Uvicorn, reload frontend page, try Upload | Works again — confirms in-memory state was cleared on restart | |

## Screenshot

[Screenshot of the working cited answer]
