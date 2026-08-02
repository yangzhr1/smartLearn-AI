import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from services.llm_service import ask_question
from services.pdf_service import extract_text

load_dotenv()

app = FastAPI(title="SmartLearn Agent")

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

# Temporary in-memory state: chat_id → (extracted_text, page_count)
state: dict[str, tuple[str, int]] = {}


class ChatRequest(BaseModel):
    chat_id: str
    message: str


class ChatResponse(BaseModel):
    answer: str
    citations: list[int]


def _extract_citations(answer: str, max_page: int) -> list[int]:
    found = [int(m) for m in re.findall(r"\[Page\s+(\d+)\]", answer)]
    return sorted(set(p for p in found if 1 <= p <= max_page))


@app.post("/upload")
async def upload(chat_id: str, file: UploadFile = File(...)):
    text, page_count = extract_text(file)
    state[chat_id] = (text, page_count)
    return {"chat_id": chat_id, "pages": page_count, "chars": len(text)}


@app.post("/chat", response_model=ChatResponse)
async def chat(body: ChatRequest):
    entry = state.get(body.chat_id)
    if entry is None:
        raise HTTPException(status_code=404, detail="chat_id not found")
    text, page_count = entry
    answer = ask_question(text, body.message)
    citations = _extract_citations(answer, page_count)
    return ChatResponse(answer=answer, citations=citations)


@app.get("/")
async def root():
    return {"message": "SmartLearn Agent API"}


@app.get("/health")
async def health():
    return {"ok": True}
