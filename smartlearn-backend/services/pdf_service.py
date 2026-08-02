from io import BytesIO

from fastapi import HTTPException, UploadFile
from pypdf import PdfReader
from pypdf.errors import PdfReadError

MAX_PAGES = 30
PDF_MAGIC = b"%PDF"


def extract_text(file: UploadFile) -> str:
    content = file.file.read()
    if not content or not content.strip():
        raise HTTPException(status_code=400, detail="Empty file")
    if not content.startswith(PDF_MAGIC):
        raise HTTPException(status_code=400, detail="File is not a valid PDF")

    try:
        reader = PdfReader(BytesIO(content))
    except PdfReadError:
        raise HTTPException(status_code=400, detail="File is not a valid PDF")

    if len(reader.pages) > MAX_PAGES:
        raise HTTPException(status_code=400, detail=f"PDF exceeds {MAX_PAGES} pages")

    pages = [
        f"[Page {i + 1}]\n{page.extract_text() or ''}"
        for i, page in enumerate(reader.pages)
    ]
    text = "\n".join(pages).strip()
    if not text:
        raise HTTPException(status_code=422, detail="No extractable text — OCR is not supported")
    return text, len(reader.pages)
