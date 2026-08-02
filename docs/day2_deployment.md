# Day 2 Deployment

> Fill in the actual values after the Railway/Vercel steps. Never include secrets here.

## URLs
- Frontend: _fill after Vercel deploy_
- Backend health: _fill after Railway deploy_`/health`
- Backend docs: _fill after Railway deploy_`/docs`

## Source
- Repository: student's fork (mikechu-2006)
- Deployed branch / merge target: `main`
- Merged commit: _fill after merge_
- Pull Request: _fill after PR created_

## Root Directories
- Railway: `smartlearn-backend`
- Vercel: `smartlearn-frontend`

## Environment variable names
- Railway: `OPENROUTER_API_KEY` (or `DEEPSEEK_API_KEY`), `ALLOWED_ORIGINS`
- Vercel: `VITE_API_URL`

## Acceptance results
- `/health`: pass/fail
- Upload: pass/fail
- Known `/chat` + citations: pass/fail + expected page
- Unknown question: pass/fail
- CORS restart + re-upload recovery: pass/fail

## Known limitations
- Railway restart clears in-memory uploaded/chat state; re-upload is expected.
- Provider note: this build calls DeepSeek directly (`DEEPSEEK_API_KEY`). If `OPENROUTER_API_KEY` is set instead, the service uses OpenRouter (`openrouter/free`).
