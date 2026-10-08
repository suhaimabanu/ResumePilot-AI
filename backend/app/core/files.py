"""Upload validation: extension, MIME, file signature, size and document integrity."""
from __future__ import annotations

import io
import re
import zipfile

import pymupdf as fitz

from .config import settings
from .jobs import UserFacingError

RESUME_TYPES = {"docx", "pdf"}
JD_TYPES = {"docx", "pdf", "txt"}
MAX_UNCOMPRESSED = 200 * 1024 * 1024  # zip-bomb guard
ALLOWED_MIME = {
    "docx": {"application/vnd.openxmlformats-officedocument.wordprocessingml.document", "application/octet-stream", "application/zip", ""},
    "pdf": {"application/pdf", "application/x-pdf", "application/octet-stream", ""},
    "txt": {"text/plain", "application/octet-stream", ""},
}


def sanitize_display_name(name: str) -> str:
    base = re.split(r"[\\/]", name or "")[-1]
    base = re.sub(r"[^\w.\- ()]+", "_", base).strip(" .")
    return base[:120] or "upload"


def detect_type(filename: str, data: bytes) -> str:
    ext = (filename.rsplit(".", 1)[-1] if "." in filename else "").lower()
    if data.startswith(b"%PDF-"):
        sig = "pdf"
    elif data.startswith(b"PK\x03\x04"):
        sig = "docx"
    else:
        sig = "txt"
    if ext in ("docx", "pdf", "txt") and ext != sig:
        raise UserFacingError(f"The file content does not match its .{ext} extension. Please upload a valid file.")
    if ext not in ("docx", "pdf", "txt"):
        raise UserFacingError("Unsupported file type. Please upload a DOCX or PDF file.")
    return sig


def validate_upload(filename: str, content_type: str | None, data: bytes, allowed: set[str]) -> str:
    if not data:
        raise UserFacingError("The uploaded file is empty.")
    if len(data) > settings.max_upload_bytes:
        raise UserFacingError(f"The file is too large. Maximum size is {settings.max_upload_mb} MB.")
    if data[:2] == b"MZ" or data[:4] == b"\x7fELF" or data[:2] == b"#!":
        raise UserFacingError("Executable files and scripts are not allowed.")
    ftype = detect_type(filename, data)
    if ftype not in allowed:
        names = ", ".join(sorted(t.upper() for t in allowed))
        raise UserFacingError(f"Unsupported file type. Supported formats: {names}.")
    mime = (content_type or "").split(";")[0].strip().lower()
    if mime and mime not in ALLOWED_MIME[ftype]:
        raise UserFacingError("The file type reported by your browser is not supported.")
    if ftype == "docx":
        _check_docx(data)
    elif ftype == "pdf":
        _check_pdf(data)
    else:
        _check_txt(data)
    return ftype


def _check_docx(data: bytes) -> None:
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as zf:
            names = set(zf.namelist())
            if "word/document.xml" not in names or "[Content_Types].xml" not in names:
                raise UserFacingError("This does not look like a valid Word (.docx) document.")
            if any(n.lower().endswith("vbaproject.bin") for n in names):
                raise UserFacingError("Macro-enabled documents are not supported. Please save as a regular .docx.")
            total = sum(i.file_size for i in zf.infolist())
            if total > MAX_UNCOMPRESSED:
                raise UserFacingError("The document is too large to process.")
            if zf.testzip() is not None:
                raise UserFacingError("The DOCX file appears to be corrupted.")
            ct = zf.read("[Content_Types].xml").decode("utf-8", "ignore")
            if "macroEnabled" in ct:
                raise UserFacingError("Macro-enabled documents are not supported. Please save as a regular .docx.")
    except zipfile.BadZipFile as exc:
        raise UserFacingError("The DOCX file appears to be corrupted.") from exc


def _check_pdf(data: bytes) -> None:
    try:
        doc = fitz.open(stream=data, filetype="pdf")
    except Exception as exc:
        raise UserFacingError("The PDF file appears to be corrupted.") from exc
    try:
        if doc.needs_pass and not doc.authenticate(""):
            raise UserFacingError("Password-protected PDFs are not supported.")
        if doc.page_count == 0:
            raise UserFacingError("The PDF has no pages.")
    finally:
        doc.close()


def _check_txt(data: bytes) -> None:
    if b"\x00" in data[:4096]:
        raise UserFacingError("The text file appears to be binary. Please upload plain text.")


def decode_text(data: bytes) -> str:
    for enc in ("utf-8-sig", "utf-16", "cp1252", "latin-1"):
        try:
            text = data.decode(enc)
            if enc == "utf-16" and not data.startswith((b"\xff\xfe", b"\xfe\xff")):
                continue
            return text
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", "replace")
