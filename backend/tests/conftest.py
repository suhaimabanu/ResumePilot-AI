from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parents[1]
ROOT = BACKEND.parent
FIXTURES = ROOT / "fixtures"
sys.path.insert(0, str(BACKEND))
os.environ["GEMINI_API_KEY"] = ""  # tests never call the real API

from app.ai import service as ai_service  # noqa: E402
from app.documents.converter import converter_name  # noqa: E402

from .fake_ai import FakeProvider  # noqa: E402


def _ensure_fixtures() -> None:
    if not (FIXTURES / "sample_resume.docx").exists() or not (FIXTURES / "sample_jd.txt").exists():
        subprocess.run([sys.executable, str(FIXTURES / "make_fixtures.py")], check=True)


_ensure_fixtures()

needs_converter = pytest.mark.skipif(converter_name() is None, reason="No DOCX->PDF converter (LibreOffice/Word)")


@pytest.fixture
def sample_docx(tmp_path) -> Path:
    dst = tmp_path / "resume.docx"
    shutil.copy(FIXTURES / "sample_resume.docx", dst)
    return dst


@pytest.fixture
def sample_jd() -> str:
    return (FIXTURES / "sample_jd.txt").read_text(encoding="utf-8")


@pytest.fixture
def fake_ai():
    provider = FakeProvider()
    ai_service.set_provider(provider)
    yield provider
    ai_service.set_provider(None)


@pytest.fixture
def no_ai():
    from app.ai.gemini import GeminiProvider

    ai_service.set_provider(GeminiProvider(api_key=""))
    yield
    ai_service.set_provider(None)
