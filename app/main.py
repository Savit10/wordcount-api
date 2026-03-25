import re
from io import BytesIO
from pathlib import Path

from docx import Document
from fastapi import FastAPI, File, HTTPException, UploadFile
from pydantic import BaseModel
from pypdf import PdfReader

app = FastAPI(title="Word Count API")

MAX_FILE_SIZE_BYTES = 20 * 1024 * 1024
TEXT_EXTENSIONS = {".txt", ".md", ".csv", ".log", ".json", ".xml", ".yaml", ".yml", ".rtf"}


class WordCountResponse(BaseModel):
    filename: str
    extension: str
    size_bytes: int
    word_count: int



def extract_text_from_pdf(file_bytes: bytes) -> str:
    reader = PdfReader(BytesIO(file_bytes))
    pages = []
    for page in reader.pages:
        pages.append(page.extract_text() or "")
    return "\n".join(pages)



def extract_text_from_docx(file_bytes: bytes) -> str:
    document = Document(BytesIO(file_bytes))
    paragraphs = [paragraph.text for paragraph in document.paragraphs]
    return "\n".join(paragraphs)



def extract_text_from_plain_text(file_bytes: bytes) -> str:
    try:
        return file_bytes.decode("utf-8")
    except UnicodeDecodeError:
        return file_bytes.decode("latin-1", errors="ignore")



def count_words(text: str) -> int:
    # Counts words with optional apostrophes (e.g., don't).
    return len(re.findall(r"\b[\w']+\b", text))


def process_upload(file: UploadFile, file_bytes: bytes) -> WordCountResponse:
    extension = Path(file.filename).suffix.lower()

    try:
        if extension == ".pdf":
            text = extract_text_from_pdf(file_bytes)
        elif extension in {".docx"}:
            text = extract_text_from_docx(file_bytes)
        elif extension in TEXT_EXTENSIONS:
            text = extract_text_from_plain_text(file_bytes)
        else:
            raise HTTPException(
                status_code=400,
                detail=(
                    "Unsupported file type. Supported: .pdf, .docx, and text files "
                    "(.txt, .md, .csv, .log, .json, .xml, .yaml, .yml, .rtf)."
                ),
            )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Could not process file: {exc}") from exc

    return WordCountResponse(
        filename=file.filename,
        extension=extension,
        size_bytes=len(file_bytes),
        word_count=count_words(text),
    )


@app.get("/")
async def root() -> dict:
    return {
        "service": "word-count-api",
        "status": "ok",
        "docs": "/docs",
        "openapi": "/openapi.json",
        "word_count_endpoint": "/api/v1/word-count",
        "legacy_word_count_endpoint": "/word-count",
    }


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}


@app.post("/api/v1/word-count", response_model=WordCountResponse, tags=["word-count"])
async def word_count_v1(file: UploadFile = File(...)) -> WordCountResponse:
    if not file.filename:
        raise HTTPException(status_code=400, detail="Uploaded file must have a filename.")

    file_bytes = await file.read()

    if not file_bytes:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    if len(file_bytes) > MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Max allowed size is {MAX_FILE_SIZE_BYTES // (1024 * 1024)} MB.",
        )

    return process_upload(file, file_bytes)


@app.post("/word-count", response_model=WordCountResponse, include_in_schema=False)
async def word_count_legacy(file: UploadFile = File(...)) -> WordCountResponse:
    # Backward-compatible alias for older clients.
    return await word_count_v1(file)
