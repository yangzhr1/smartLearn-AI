import os
import re

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from services.llm import answer_from_pages
from services.pdf import extract_pages

app = FastAPI(title="SmartLearn Lite API")

documents: dict[str, list[dict]] = {}

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
    allow_headers=["Authorization", "Content-Type"],
)


class ChatRequest(BaseModel):
    chat_id: str = "day2-demo"
    message: str = Field(min_length=2, max_length=2000)


@app.get("/")
async def root():
    return {"message": "SmartLearn Lite API is running"}


@app.get("/health")
async def health():
    return {"ok": True}


@app.post("/upload")
async def upload(chat_id: str, file: UploadFile = File(...)):
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(400, "Only PDF files are supported")
    contents = await file.read()
    if not contents:
        raise HTTPException(400, "File is empty")
    pages = extract_pages(contents)
    text = "".join(page["text"] for page in pages)
    if not text.strip():
        raise HTTPException(
            422,
            "No readable text found in PDF. Scanned documents are not supported (no OCR).",
        )
    documents[chat_id] = pages
    return {
        "status": "ok",
        "filename": file.filename,
        "pages": len(pages),
        "characters": len(text),
    }


@app.post("/chat")
async def chat(request: ChatRequest):
    pages = documents.get(request.chat_id)
    if pages is None:
        raise HTTPException(
            404, f"No document for chat_id {request.chat_id!r}. Upload a PDF first."
        )
    try:
        answer = answer_from_pages(pages, request.message)
    except Exception as exc:
        raise HTTPException(502, f"AI service failed: {exc}")
    valid_pages = {page["page"] for page in pages}
    citations = sorted(
        int(p)
        for p in set(re.findall(r"\[Page (\d+)\]", answer))
        if int(p) in valid_pages
    )
    return {"answer": answer, "citations": citations}
