import os
import re

from fastapi import FastAPI, File, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from .services.llm import answer_from_pages
from .services.pdf import extract_pages

app = FastAPI(title="SmartLearn Lite API")

# Temporary in-memory document store. Cleared whenever the server restarts.
documents: dict[str, list[dict]] = {}

# Environment-driven CORS allowlist (comma-separated). No hard-coded origins.
allowed_origins = [
    origin.strip()
    for origin in os.getenv("ALLOWED_ORIGINS", "http://localhost:5173").split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


@app.get("/")
def root():
    return {"message": "SmartLearn Lite API is running"}


@app.get("/health")
def health():
    return {"ok": True}


class ChatRequest(BaseModel):
    chat_id: str = "day2-demo"
    message: str = Field(..., min_length=2, max_length=2000)


@app.post("/upload")
async def upload(
    chat_id: str = Query(..., description="Chat/document id"),
    file: UploadFile = File(...),
):
    filename = file.filename or ""
    if not filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=400, detail="Only PDF files are accepted."
        )

    pdf_bytes = await file.read()
    if not pdf_bytes:
        raise HTTPException(status_code=400, detail="The uploaded file is empty.")

    try:
        pages = extract_pages(pdf_bytes)
    except ValueError as exc:
        # Includes the > MAX_PAGES case.
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception:
        raise HTTPException(
            status_code=400, detail="Could not parse this file as a PDF."
        )

    readable = [page for page in pages if page["text"]]
    if not readable:
        raise HTTPException(
            status_code=422,
            detail=(
                "No readable text was found in this PDF. It is likely scanned "
                "or image-only; OCR is not supported."
            ),
        )

    documents[chat_id] = pages
    return {
        "status": "ok",
        "filename": filename,
        "chat_id": chat_id,
        "pages": len(pages),
        "characters": sum(len(page["text"]) for page in pages),
    }


@app.post("/chat")
def chat(request: ChatRequest):
    pages = documents.get(request.chat_id)
    if pages is None:
        raise HTTPException(
            status_code=404,
            detail=(
                f"No document is stored for chat_id '{request.chat_id}'. "
                "Upload a PDF with this chat_id first."
            ),
        )

    try:
        answer = answer_from_pages(pages, request.message)
    except Exception as exc:
        raise HTTPException(
            status_code=502, detail=f"AI service failed: {exc}"
        )

    citations = extract_citations(answer, pages)
    return {"answer": answer, "citations": citations}


def extract_citations(answer: str, pages: list[dict]) -> list[int]:
    """Return [Page X] numbers mentioned in the answer, restricted to pages
    that actually exist in the stored document, sorted ascending."""
    known = {page["page"] for page in pages}
    cited = {int(number) for number in re.findall(r"\[Page\s+(\d+)\]", answer)}
    return sorted(number for number in cited if number in known)
