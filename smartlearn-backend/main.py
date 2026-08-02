import os
import re

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from pypdf.errors import PdfReadError

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


PAGE_TAG = re.compile(r"\[Page\s+(\d+)\]", re.IGNORECASE)


def valid_citations(answer: str, pages: list[dict]) -> list[int]:
    available = {int(page["page"]) for page in pages}
    mentioned = {int(match.group(1)) for match in PAGE_TAG.finditer(answer)}
    return sorted(mentioned & available)


def remove_invalid_page_tags(answer: str, pages: list[dict]) -> str:
    available = {int(page["page"]) for page in pages}

    def replace(match):
        if int(match.group(1)) in available:
            return match.group(0)
        return ""

    return PAGE_TAG.sub(replace, answer).strip()


@app.get("/")
async def root():
    return {"message": "SmartLearn Lite API is running"}


@app.get("/health")
async def health():
    return {"ok": True}


@app.post("/upload")
async def upload(chat_id: str, file: UploadFile = File(...)):
    if file.content_type != "application/pdf":
        raise HTTPException(400, "Please upload a PDF")
    data = await file.read()
    if not data:
        raise HTTPException(400, "Empty file")
    try:
        pages = extract_pages(data)
    except (ValueError, PdfReadError) as error:
        raise HTTPException(400, str(error)) from error
    characters = sum(len(page["text"]) for page in pages)
    if characters == 0:
        raise HTTPException(422, "No text; OCR unsupported")
    documents[chat_id] = pages
    return {
        "status": "ok",
        "filename": file.filename,
        "pages": len(pages),
        "characters": characters,
    }


@app.post("/chat")
async def chat(request: ChatRequest):
    pages = documents.get(request.chat_id)
    if pages is None:
        raise HTTPException(404, "chat_id not found. Upload first.")
    try:
        answer = answer_from_pages(pages, request.message)
    except Exception as exc:
        raise HTTPException(502, f"AI service failed: {exc}")
    citations = valid_citations(answer, pages)
    answer = remove_invalid_page_tags(answer, pages)
    return {"answer": answer, "citations": citations}
