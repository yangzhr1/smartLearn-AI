from fastapi import FastAPI, File, HTTPException, UploadFile

from services.pdf import extract_pages

from pypdf.errors import PdfReadError

import os
import re

from dotenv import load_dotenv
from pydantic import BaseModel, Field
from openai import APIError
from fastapi.middleware.cors import CORSMiddleware

from services.llm import answer_from_pages

load_dotenv()

ALLOWED_ORIGINS = [
    origin.strip()
    for origin in os.getenv("ALLOWED_ORIGINS", "http://localhost:5173").split(",")
    if origin.strip()
]

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)

documents: dict = {}


class ChatRequest(BaseModel):
    chat_id: str = "day2-demo"
    message: str = Field(..., min_length=2, max_length=2000)


CITATION_RE = re.compile(r"\[Page\s+(\d+)\]", re.IGNORECASE)


@app.get("/")
def root():
    return {"message": "SmartLearn Lite backend"}


@app.get("/health")
def health():
    return {"ok": True}


@app.post("/upload")
async def upload(chat_id: str, file: UploadFile = File(...)):
    if file.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="Only PDF files are accepted")

    pdf_bytes = await file.read()

    if len(pdf_bytes) == 0:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")

    try:
        pages = extract_pages(pdf_bytes)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except PdfReadError:
        raise HTTPException(status_code=400, detail="Failed to parse PDF")

    total_chars = sum(len(p["text"]) for p in pages)
    if total_chars == 0:
        raise HTTPException(
            status_code=422,
            detail="No readable text found. OCR is not supported.",
        )

    documents[chat_id] = pages

    return {
        "status": "ok",
        "filename": file.filename,
        "pages": len(pages),
        "characters": total_chars,
    }


@app.post("/chat")
def chat(request: ChatRequest):
    if request.chat_id not in documents:
        raise HTTPException(
            status_code=404,
            detail=f"No PDF found for chat_id '{request.chat_id}'. Please upload the PDF again.",
        )

    pages = documents[request.chat_id]

    try:
        answer = answer_from_pages(pages, request.message)
    except (RuntimeError, APIError):
        raise HTTPException(status_code=502, detail="Upstream AI service unavailable")

    stored_pages = {p["page"] for p in pages}
    found = {int(m.group(1)) for m in CITATION_RE.finditer(answer)}
    citations = sorted(found & stored_pages)

    citation_set = set(citations)

    def keep_valid(m):
        return f"[Page {m.group(1)}]" if int(m.group(1)) in citation_set else ""

    answer = CITATION_RE.sub(keep_valid, answer)
    answer = re.sub(r"  +", " ", answer).strip()

    return {"answer": answer, "citations": citations}
