import os
import re

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from .services.llm import answer_from_pages
from .services.pdf import extract_pages

app = FastAPI(title="SmartLearn Lite API")

allowed_origins = [
    origin.strip()
    for origin in os.getenv(
        "ALLOWED_ORIGINS",
        "http://localhost:5173",
    ).split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

documents: dict[str, list[dict]] = {}


class ChatRequest(BaseModel):
    chat_id: str = Field(default="day2-demo", min_length=1)
    message: str = Field(min_length=2, max_length=2000)


@app.get("/")
def root():
    return {"message": "SmartLearn Lite API is running"}


@app.get("/health")
def health():
    return {"ok": True}


@app.post("/upload")
async def upload(chat_id: str, file: UploadFile = File(...)):
    # Reject non-PDF
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted")

    # Reject empty
    contents = await file.read()
    if not contents:
        raise HTTPException(status_code=400, detail="File is empty")

    # Extract pages
    try:
        pages = extract_pages(contents)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Reject PDF with no readable text
    total_chars = sum(len(p["text"]) for p in pages)
    if total_chars == 0:
        raise HTTPException(
            status_code=422,
            detail="No readable text found in this PDF. OCR is not supported.",
        )

    # Store and respond
    documents[chat_id] = pages

    return {
        "status": "ok",
        "filename": file.filename,
        "pages": len(pages),
        "characters": total_chars,
    }


@app.post("/chat")
def chat(request: ChatRequest):
    # Look up stored pages
    pages = documents.get(request.chat_id)
    if pages is None:
        raise HTTPException(
            status_code=404,
            detail=f"No document found for chat_id '{request.chat_id}'. "
                   f"Upload a PDF via POST /upload?chat_id={request.chat_id} first.",
        )

    # Call the LLM
    try:
        answer = answer_from_pages(pages, request.message)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Upstream AI service failed: {e}")

    # Extract [Page X] citations that actually exist in the pages
    all_page_nums = {p["page"] for p in pages}
    cited = set()
    for match in re.finditer(r"\[Page\s+(\d+)\]", answer):
        page_num = int(match.group(1))
        if page_num in all_page_nums:
            cited.add(page_num)

    return {
        "answer": answer,
        "citations": sorted(cited),
    }
