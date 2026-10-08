"""In-memory session + file registry with on-disk working directories and TTL cleanup.

Privacy: every session gets its own private directory under the workspace, identifiers are
unguessable random tokens, files are only addressable via file_id (never by path), and expired
sessions are deleted from disk.
"""
from __future__ import annotations

import secrets
import shutil
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

from .config import settings
from .models import Change, JDAnalysis, KeywordEvidence, ResumeSource


@dataclass
class StoredFile:
    file_id: str
    path: Path
    kind: str  # tailored_docx | tailored_pdf | bundle_zip
    download_name: str
    media_type: str


@dataclass
class Session:
    session_id: str
    directory: Path
    created: float = field(default_factory=time.time)
    last_access: float = field(default_factory=time.time)
    resume_path: Optional[Path] = None
    resume_filename: str = ""
    resume: Optional[ResumeSource] = None
    original_pdf_path: Optional[Path] = None  # rendering of the uploaded resume
    jd_text: str = ""
    jd_analysis: Optional[JDAnalysis] = None
    keyword_evidence: list[KeywordEvidence] = field(default_factory=list)
    original_ats: Optional[dict[str, Any]] = None
    changes: list[Change] = field(default_factory=list)
    blocked: list[dict] = field(default_factory=list)
    style: str = "balanced"
    ai_status: str = ""  # ok | weak | failed | disabled — outcome of the last AI tailoring call
    generation: int = 0
    result: Optional[dict[str, Any]] = None
    files: dict[str, StoredFile] = field(default_factory=dict)
    active_job: Optional[str] = None
    lock: threading.RLock = field(default_factory=threading.RLock)

    def touch(self) -> None:
        self.last_access = time.time()

    def register_file(self, path: Path, kind: str, download_name: str, media_type: str) -> StoredFile:
        file_id = secrets.token_urlsafe(24)
        stored = StoredFile(file_id=file_id, path=path, kind=kind, download_name=download_name, media_type=media_type)
        self.files[file_id] = stored
        return stored

    def drop_files(self, kinds: set[str]) -> None:
        for fid in [fid for fid, f in self.files.items() if f.kind in kinds]:
            self.files.pop(fid, None)


class SessionStore:
    def __init__(self, root: Path) -> None:
        self.root = root
        self._sessions: dict[str, Session] = {}
        self._lock = threading.Lock()

    def create(self) -> Session:
        sid = secrets.token_urlsafe(32)
        directory = self.root / f"s_{secrets.token_hex(16)}"
        directory.mkdir(parents=True, exist_ok=False)
        session = Session(session_id=sid, directory=directory)
        with self._lock:
            self._sessions[sid] = session
        return session

    def get(self, sid: str | None) -> Session | None:
        if not sid:
            return None
        with self._lock:
            session = self._sessions.get(sid)
        if session:
            session.touch()
        return session

    def delete(self, sid: str) -> None:
        with self._lock:
            session = self._sessions.pop(sid, None)
        if session:
            shutil.rmtree(session.directory, ignore_errors=True)

    def cleanup_expired(self) -> int:
        cutoff = time.time() - settings.session_ttl_minutes * 60
        with self._lock:
            expired = [sid for sid, s in self._sessions.items() if s.last_access < cutoff]
        for sid in expired:
            self.delete(sid)
        return len(expired)


store = SessionStore(settings.workspace_dir)


def start_cleanup_thread(interval_s: int = 300) -> None:
    def loop() -> None:
        while True:
            time.sleep(interval_s)
            try:
                store.cleanup_expired()
            except Exception:  # pragma: no cover - best effort
                pass

    threading.Thread(target=loop, name="session-cleanup", daemon=True).start()
