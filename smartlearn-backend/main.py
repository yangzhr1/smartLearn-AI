import os

from fastapi import FastAPI, File, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from .services import rag

app = FastAPI(title="SmartLearn Lite API")

# Temporary in-memory document store. Cleared whenever the server restarts.
documents: dict[str, dict] = {}

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
        document = rag.prepare_rag_chat_record(
            chat_id=chat_id,
            filename=filename,
            pdf_bytes=pdf_bytes,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail=(
                "No readable text was found in this PDF. It is likely scanned "
                "or image-only; OCR is not supported."
            ),
        )
    except Exception:
        raise HTTPException(
            status_code=400, detail="Could not parse this file as a PDF."
        )

    # Fail cleanly: never leave a half-written record behind.
    documents[chat_id] = document
    return rag.build_upload_response(document)


@app.get("/documents/{chat_id}/file")
def document_file(chat_id: str):
    """Serve the uploaded PDF so the browser can preview it by chat_id."""
    document = documents.get(chat_id)
    if document is None:
        raise HTTPException(
            status_code=404,
            detail=f"No document is stored for chat_id '{chat_id}'. Upload a PDF first.",
        )
    saved_path = document.get("saved_pdf_path") or document.get("file_path")
    if not saved_path or not os.path.exists(saved_path):
        raise HTTPException(
            status_code=404, detail="The uploaded PDF file is missing."
        )
    return FileResponse(saved_path, media_type="application/pdf")


@app.post("/chat")
def chat(request: ChatRequest):
    document = documents.get(request.chat_id)
    if document is None:
        raise HTTPException(
            status_code=404,
            detail=(
                f"No document is stored for chat_id '{request.chat_id}'. "
                "Upload a PDF with this chat_id first."
            ),
        )

    try:
        result = rag.answer_chat_turn(document, request.message)
    except Exception as exc:
        raise HTTPException(
            status_code=502, detail=f"AI service failed: {exc}"
        )

    return {
        "answer": result["answer"],
        "citations": result["citations"],
        "sources": result["sources"],
    }
