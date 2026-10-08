import hashlib
from pathlib import Path
from typing import Tuple


def compute_file_hash(file_bytes: bytes) -> str:
    return hashlib.sha256(file_bytes).hexdigest()


def extract_text_from_pdf(file_bytes: bytes) -> str:
    from PyPDF2 import PdfReader
    import io

    reader = PdfReader(io.BytesIO(file_bytes))
    pages = []
    for i, page in enumerate(reader.pages, 1):
        text = page.extract_text() or ""
        if text.strip():
            pages.append(f"[Page {i}]\n{text.strip()}")
    return "\n\n".join(pages)


def extract_text_from_docx(file_bytes: bytes) -> str:
    from docx import Document
    import io

    doc = Document(io.BytesIO(file_bytes))
    paragraphs = []
    for para in doc.paragraphs:
        text = para.text.strip()
        if text:
            if para.style and para.style.name and para.style.name.startswith("Heading"):
                paragraphs.append(f"\n[Section: {text}]")
            else:
                paragraphs.append(text)
    return "\n".join(paragraphs)


def extract_text_from_txt(file_bytes: bytes) -> str:
    return file_bytes.decode("utf-8", errors="replace")


def parse_document(filename: str, file_bytes: bytes) -> Tuple[str, str]:
    ext = Path(filename).suffix.lower()
    file_hash = compute_file_hash(file_bytes)

    if ext == ".pdf":
        text = extract_text_from_pdf(file_bytes)
    elif ext in (".docx", ".doc"):
        text = extract_text_from_docx(file_bytes)
    elif ext in (".txt", ".md", ".text"):
        text = extract_text_from_txt(file_bytes)
    else:
        raise ValueError(
            f"Unsupported file type: {ext}. Supported: .pdf, .docx, .txt, .md"
        )

    if not text.strip():
        raise ValueError("Could not extract any text from the document.")

    return text, file_hash
