import os
import re

from fastapi import FastAPI, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from services.llm import answer_from_pages
from services.pdf import extract_pages

app = FastAPI(title="SmartLearn Lite API")

ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "http://localhost:5173")
origins = [origin.strip() for origin in ALLOWED_ORIGINS.split(",") if origin.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

documents: dict[str, list] = {}


class ChatRequest(BaseModel):
    chat_id: str = "day2-demo"
    message: str = Field(..., min_length=2, max_length=2000)


@app.get("/")
def root():
    return {"message": "SmartLearn Lite API is running"}


@app.get("/health")
def health():
    return {"ok": True}


@app.post("/upload")
async def upload(chat_id: str, file: UploadFile):
    # Validate file is a PDF
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted")

    # Read into memory (no disk write)
    pdf_bytes = await file.read()

    # Reject empty file
    if not pdf_bytes:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")

    # Parse with the shared PDF service
    try:
        pages = extract_pages(pdf_bytes)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid or unreadable PDF file")

    # Enforce page limit
    if len(pages) > 30:
        raise HTTPException(status_code=400, detail="PDF exceeds the 30-page limit")

    # Count readable characters across all pages
    character_count = sum(
        len(page.get("text", ""))
        for page in pages
    )

    # Reject scanned/image-only PDFs
    if character_count == 0:
        raise HTTPException(
            status_code=422,
            detail="No readable text found in the PDF. OCR is not supported.",
        )

    # Store in-memory keyed by chat session
    documents[chat_id] = pages

    return {
        "status": "ok",
        "filename": file.filename,
        "page_count": len(pages),
        "character_count": character_count,
    }


def _extract_citations(answer: str, pages: list[dict]) -> tuple[str, list[int]]:
    """Keep only [Page X] citations present in the uploaded PDF, sort them,
    and strip hallucinated page tags from the answer text."""
    valid_pages = {p["page"] for p in pages}

    mentioned = {int(m) for m in re.findall(r"\[Page (\d+)\]", answer)}
    citations = sorted(p for p in mentioned if p in valid_pages)

    def _keep_valid(match: re.Match) -> str:
        return match.group(0) if int(match.group(1)) in valid_pages else ""

    cleaned = re.sub(r"\[Page (\d+)\]", _keep_valid, answer)
    cleaned = re.sub(r" {2,}", " ", cleaned).strip()
    return cleaned, citations


@app.post("/chat")
def chat(request: ChatRequest):
    if request.chat_id not in documents:
        raise HTTPException(
            status_code=404,
            detail="Chat session not found. Upload the PDF again before chatting.",
        )

    pages = documents[request.chat_id]

    try:
        raw = answer_from_pages(pages, request.message)
    except Exception:
        raise HTTPException(
            status_code=502,
            detail="AI service is currently unavailable. Please try again later.",
        )

    answer, citations = _extract_citations(raw, pages)
    return {"answer": answer, "citations": citations}
