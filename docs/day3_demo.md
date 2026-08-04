# Day 3 Demo — Deployment Guide (GitHub Pages + Railway)

Vercel is unavailable for this workshop, so the frontend is served from
**GitHub Pages** and the backend from **Railway**. The app is a single page
with no client-side routing, so GitHub Pages (static `dist/`) works as-is.

## Architecture

```text
Learner opens  https://mikechu-2006.github.io/smartLearn-AI/
      │  frontend reads VITE_API_URL
      ▼
Railway backend  https://<your-service>.up.railway.app
      │  checks ALLOWED_ORIGINS
      ▼
DeepSeek API (DEEPSEEK_API_KEY) — answers from retrieved chunks
```

## Configuration triangle (all three must agree)

| Variable | Platform | Value |
|---|---|---|
| `VITE_API_URL` | GitHub Pages (build-time) | Railway backend URL, e.g. `https://xxx.up.railway.app` |
| `ALLOWED_ORIGINS` | Railway | `http://localhost:5173, https://mikechu-2006.github.io` |
| `DEEPSEEK_API_KEY` | Railway | your DeepSeek key (secret) |

`ALLOWED_ORIGINS` uses the origin (scheme + host) — not the `/smartLearn-AI/`
path. The GitHub Pages origin is `https://mikechu-2006.github.io`.

## 1. Deploy the backend to Railway

The Dockerfile now downloads the MiniLM model at build time, so the RAG upload
route works without touching Hugging Face.

1. Create a Railway account and link GitHub.
2. **Deploy from GitHub Repo** → select the `smartLearn-AI` fork.
3. Production branch: `main` (after merging the Day 3 PR).
4. Settings → **Root Directory**: `smartlearn-backend`.
5. Variables: `DEEPSEEK_API_KEY` (secret), `ALLOWED_ORIGINS` (above).
   Do not set `PORT`; Railway supplies it.
6. Deploy and copy the generated domain as `BACKEND_URL`.
7. Verify in `/docs`:
   - `GET /health` → `200 {"ok": true}`
   - `POST /upload?chat_id=day3-demo` with `Day3/pdf1.pdf` → `200`
   - `POST /chat` known question → `answer + citations + sources`
   - `GET /documents/day3-demo/file` → the PDF

Note: Railway free tier runs the CPU-only embedder; uploading a large PDF can
take tens of seconds. A 28-page PDF is fast.

## 2. Deploy the frontend to GitHub Pages

1. Build (already done with `base: "./"`):
   ```bash
   cd smartlearn-frontend
   npm run build        # produces dist/ with relative asset paths
   ```
2. Publish `dist/` to a `gh-pages` branch (one time):
   ```bash
   git switch --orphan gh-pages
   rm -rf .git          # optional: keep branch in its own history
   ```
   Or the simple repeated approach:
   ```bash
   cd smartlearn-frontend
   npm run build
   npx gh-pages -d dist
   ```
   (`gh-pages` pushes `dist/` to the `gh-pages` branch automatically.)
3. GitHub repo → **Settings → Pages** → Source: `Deploy from a branch`,
   branch `gh-pages`, folder `/ (root)`.
4. Site URL: `https://mikechu-2006.github.io/smartLearn-AI/`
5. Set `VITE_API_URL` for the build:
   ```bash
   cd smartlearn-frontend
   VITE_API_URL=https://<BACKEND_URL> npm run build
   npx gh-pages -d dist
   ```
6. Add the GitHub Pages origin to Railway `ALLOWED_ORIGINS`, then re-upload.

## 3. Local demo (zero accounts — fallback)

```bash
# terminal 1 — backend
cd smartLearn-AI
ALLOWED_ORIGINS="http://localhost:5173" ./venv/bin/uvicorn smartlearn-backend.main:app --reload

# terminal 2 — frontend
cd smartLearn-AI/smartlearn-frontend
npm run dev            # http://localhost:5173
```

## Demo script (under 3 minutes)

1. Upload `Day3/pdf1.pdf` (or a known text PDF).
2. Ask: "Which single-hop datasets are used in the paper?" → cited answer.
3. Click a Page chip → the PDF preview jumps to that page (`#page=N`).
4. Ask a follow-up ("Give one more detail from that page.") → new cited turn.
5. Note: a Railway restart clears uploaded documents — re-upload before chat.

## Known limitations for the demo

- In-memory state: restarting Railway or the local backend clears uploads/history.
- Long PDFs are slow on the Railway free tier (CPU embedding).
- The deployed backend needs the model from ModelScope (now baked into the
  Docker image); never rely on Hugging Face.
