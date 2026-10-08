"""DOCX -> PDF conversion. Prefers LibreOffice headless; falls back to Microsoft Word (Windows COM).

The PDF produced here is the authoritative source for page count, preview and visual validation.
"""
from __future__ import annotations

import atexit
import logging
import os
import queue
import shutil
import subprocess
import sys
import tempfile
import threading
from concurrent.futures import Future
from pathlib import Path

from ..core.config import settings
from ..core.jobs import UserFacingError

log = logging.getLogger("converter")
_lo_lock = threading.Lock()


def word_available() -> bool:
    if sys.platform != "win32":
        return False
    try:
        import winreg

        with winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, r"Word.Application\CLSID"):
            return True
    except Exception:
        return False


def converter_name() -> str | None:
    pref = settings.pdf_converter
    if pref in ("auto", "libreoffice") and settings.libreoffice_path:
        return "libreoffice"
    if pref in ("auto", "word") and word_available():
        return "word"
    return None


def _convert_libreoffice(src: Path, out_dir: Path) -> Path:
    profile = Path(tempfile.mkdtemp(prefix="lo_profile_"))
    try:
        cmd = [settings.libreoffice_path, f"-env:UserInstallation={profile.as_uri()}", "--headless", "--norestore",
               "--nolockcheck", "--convert-to", "pdf", "--outdir", str(out_dir), str(src)]
        with _lo_lock:
            proc = subprocess.run(cmd, capture_output=True, timeout=180)
        pdf = out_dir / (src.stem + ".pdf")
        if proc.returncode != 0 or not pdf.exists():
            log.error("LibreOffice conversion failed rc=%s stderr=%s", proc.returncode, proc.stderr[-500:])
            raise RuntimeError("LibreOffice conversion failed")
        return pdf
    finally:
        shutil.rmtree(profile, ignore_errors=True)


class _WordWorker:
    """One long-lived Word instance on its own COM thread (faster and more stable than one per file)."""

    def __init__(self) -> None:
        self._queue: "queue.Queue[tuple[Path, Path, Future]]" = queue.Queue()
        self._thread: threading.Thread | None = None
        self._start_lock = threading.Lock()

    def convert(self, src: Path, pdf: Path, timeout: float = 180) -> Path:
        with self._start_lock:
            if self._thread is None or not self._thread.is_alive():
                self._thread = threading.Thread(target=self._run, name="word-com", daemon=True)
                self._thread.start()
        fut: Future = Future()
        self._queue.put((src, pdf, fut))
        return fut.result(timeout=timeout)

    def _run(self) -> None:
        import pythoncom
        import win32com.client

        pythoncom.CoInitialize()
        word = None
        try:
            while True:
                src, pdf, fut = self._queue.get()
                if fut is None:
                    break
                for attempt in range(2):
                    try:
                        if word is None:
                            word = win32com.client.DispatchEx("Word.Application")
                            word.Visible = False
                            word.DisplayAlerts = 0
                            try:
                                word.AutomationSecurity = 3  # never run macros
                            except Exception:
                                pass
                        doc = word.Documents.Open(str(src.resolve()), ConfirmConversions=False, ReadOnly=True,
                                                  AddToRecentFiles=False, Visible=False, OpenAndRepair=False,
                                                  NoEncodingDialog=True)
                        try:
                            doc.ExportAsFixedFormat(OutputFileName=str(pdf.resolve()), ExportFormat=17,
                                                    OpenAfterExport=False, OptimizeFor=0, CreateBookmarks=0,
                                                    DocStructureTags=True)
                        finally:
                            doc.Close(SaveChanges=0)
                        fut.set_result(pdf)
                        break
                    except Exception as exc:  # Word crashed or was closed: restart it once
                        word = None
                        if attempt == 1:
                            fut.set_exception(exc)
        finally:
            if word is not None:
                try:
                    word.Quit(SaveChanges=0)
                except Exception:
                    pass
            pythoncom.CoUninitialize()

    def shutdown(self) -> None:
        if self._thread is not None and self._thread.is_alive():
            self._queue.put((Path(), Path(), None))  # type: ignore[arg-type]
            self._thread.join(timeout=15)


_word = _WordWorker()
atexit.register(_word.shutdown)


def _convert_word(src: Path, out_dir: Path) -> Path:
    pdf = out_dir / (src.stem + ".pdf")
    _word.convert(src, pdf)
    if not pdf.exists():
        raise RuntimeError("Word conversion produced no file")
    return pdf


def docx_to_pdf(src: Path, out_dir: Path) -> tuple[Path, str]:
    out_dir.mkdir(parents=True, exist_ok=True)
    name = converter_name()
    if name is None:
        raise UserFacingError(
            "PDF generation is unavailable on this server (LibreOffice is not installed). "
            "Please contact the administrator."
        )
    try:
        if name == "libreoffice":
            return _convert_libreoffice(src, out_dir), name
        return _convert_word(src, out_dir), name
    except UserFacingError:
        raise
    except Exception as exc:
        log.error("PDF conversion via %s failed: %s", name, exc)
        # Try the other engine before giving up.
        if name == "libreoffice" and word_available():
            try:
                return _convert_word(src, out_dir), "word"
            except Exception:
                pass
        raise UserFacingError("We couldn't create the PDF version of your resume. Please try again.") from exc


def converter_status() -> dict:
    return {
        "active": converter_name(),
        "libreoffice": bool(settings.libreoffice_path),
        "word": word_available(),
        "preference": settings.pdf_converter,
    }


if __name__ == "__main__":  # manual check: python -m app.documents.converter file.docx
    p, used = docx_to_pdf(Path(sys.argv[1]), Path(os.getcwd()))
    print(used, p)
