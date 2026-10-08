"""Application configuration, loaded from environment variables (.env supported)."""
from __future__ import annotations

import os
import shutil
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parents[2]
ROOT_DIR = BACKEND_DIR.parent
load_dotenv(ROOT_DIR / ".env")
load_dotenv(BACKEND_DIR / ".env")


def _int(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, default))
    except ValueError:
        return default


def _find_libreoffice() -> str | None:
    configured = os.environ.get("LIBREOFFICE_PATH")
    if configured and Path(configured).exists():
        return configured
    for name in ("soffice", "libreoffice"):
        found = shutil.which(name)
        if found:
            return found
    for candidate in (
        r"C:\Program Files\LibreOffice\program\soffice.exe",
        r"C:\Program Files (x86)\LibreOffice\program\soffice.exe",
        "/usr/bin/soffice",
        "/usr/lib/libreoffice/program/soffice",
        "/Applications/LibreOffice.app/Contents/MacOS/soffice",
    ):
        if Path(candidate).exists():
            return candidate
    return None


def _find_tesseract() -> str | None:
    configured = os.environ.get("TESSERACT_PATH")
    if configured and Path(configured).exists():
        return configured
    found = shutil.which("tesseract")
    if found:
        return found
    candidate = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
    return candidate if Path(candidate).exists() else None


@dataclass
class Settings:
    gemini_api_key: str = field(default_factory=lambda: os.environ.get("GEMINI_API_KEY", "").strip())
    gemini_model: str = field(default_factory=lambda: os.environ.get("GEMINI_MODEL", "").strip() or "gemini-3.8-flash")
    # Tried in order when the primary model is overloaded, rate-limited or retired.
    gemini_fallback_models: list[str] = field(default_factory=lambda: [
        m.strip() for m in os.environ.get(
            "GEMINI_FALLBACK_MODELS", "gemini-3.5-flash,gemini-3.8-flash,gemini-3.5-flash-lite").split(",")
        if m.strip()])
    gemini_timeout_s: int = field(default_factory=lambda: _int("GEMINI_TIMEOUT_SECONDS", 120))
    gemini_max_retries: int = field(default_factory=lambda: _int("GEMINI_MAX_RETRIES", 2))
    max_upload_mb: int = field(default_factory=lambda: _int("MAX_UPLOAD_MB", 10))
    session_ttl_minutes: int = field(default_factory=lambda: _int("SESSION_TTL_MINUTES", 120))
    workspace_dir: Path = field(
        default_factory=lambda: Path(os.environ.get("WORKSPACE_DIR") or Path(tempfile.gettempdir()) / "ai_resume_tailor")
    )
    # auto | libreoffice | word
    pdf_converter: str = field(default_factory=lambda: os.environ.get("PDF_CONVERTER", "auto").strip().lower())
    libreoffice_path: str | None = field(default_factory=_find_libreoffice)
    tesseract_path: str | None = field(default_factory=_find_tesseract)
    cors_origins: list[str] = field(
        default_factory=lambda: [o.strip() for o in os.environ.get("CORS_ORIGINS", "http://localhost:3000").split(",") if o.strip()]
    )

    @property
    def max_upload_bytes(self) -> int:
        return self.max_upload_mb * 1024 * 1024


settings = Settings()
settings.workspace_dir.mkdir(parents=True, exist_ok=True)
