import os
import re

from fastapi import FastAPI, HTTPException, Query, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware

from pydantic import BaseModel

from services.llm import answer_from_pages
from services.pdf import extract_pages

app = FastAPI(title="SmartLearn Lite API")

ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "http://localhost:5173")
allowed_origins = [
    origin.strip() for origin in ALLOWED_ORIGINS.split(",") if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "Accept"],
)

documents: dict[str, dict] = {}


class ChatRequest(BaseModel):
    chat_id: str
    message: str


@app.post("/chat")
async def chat(request: ChatRequest):
    pages = documents.get(request.chat_id)
    if pages is None:
        raise HTTPException(status_code=404, detail="Chat not found")

    try:
        answer = answer_from_pages(pages, request.message)
    except Exception:
        raise HTTPException(status_code=502, detail="AI service unavailable")

    citations = list(dict.fromkeys(re.findall(r"\[Page (\d+)\]", answer)))

    return {"answer": answer, "citations": citations}


@app.get("/")
def root():
    return {"message": "SmartLearn Lite API is running"}


@app.get("/health")
def health():
    return {"ok": True}


@app.post("/upload")
async def upload(chat_id: str = Query(...), file: UploadFile = File(...)):
    if not (file.filename or "").lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="File must be a PDF")

    pdf_bytes = await file.read()

    if not pdf_bytes:
        raise HTTPException(status_code=400, detail="Empty file")

    try:
        pages = extract_pages(pdf_bytes)
    except ValueError:
        raise HTTPException(status_code=400, detail="PDF exceeds 30 pages")

    characters = sum(len(p["text"]) for p in pages)

    if characters == 0:
        raise HTTPException(status_code=422, detail="OCR is not supported")

    documents[chat_id] = pages

    return {
        "status": "ok",
        "filename": file.filename,
        "pages": len(pages),
        "characters": characters,
    }
