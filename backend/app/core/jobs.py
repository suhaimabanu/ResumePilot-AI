"""Background job runner with real, step-by-step status reporting.

Progress values come only from steps the pipeline has actually reached; 100% is reported
only when the job function returned successfully.
"""
from __future__ import annotations

import logging
import secrets
import threading
import time
import traceback
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

log = logging.getLogger("jobs")

# Status keys required by the spec (section 62) with user-facing labels.
STEP_LABELS: dict[str, str] = {
    "queued": "Queued",
    "parsing_resume": "Reading Resume",
    "rendering_original": "Measuring Original Layout",
    "parsing_jd": "Understanding Job Description",
    "analyzing": "Matching Skills",
    "generating_suggestions": "Creating Tailoring Suggestions",
    "waiting_for_user": "Waiting for Your Review",
    "applying_changes": "Applying Selected Changes",
    "fact_checking": "Fact Checking",
    "completeness": "Resume Completeness Check",
    "scoring": "ATS Analysis",
    "generating_docx": "Creating DOCX",
    "validating_docx": "Validating DOCX Content",
    "generating_pdf": "Creating PDF",
    "validating_pdf": "Validating PDF Content",
    "visual_validation": "Visual Validation",
    "page_count": "Page Count Check",
    "final_validation": "Final Validation",
    "completed": "Completed",
    "failed": "Failed",
}


class UserFacingError(Exception):
    """An error whose message is safe and helpful to show to the end user."""


@dataclass
class Job:
    job_id: str
    session_id: str
    kind: str
    steps: list[str]
    status: str = "queued"  # queued | processing | waiting_for_user | completed | failed
    step: str = "queued"
    done_steps: list[str] = field(default_factory=list)
    error: Optional[str] = None
    result: Optional[dict[str, Any]] = None
    created: float = field(default_factory=time.time)
    notes: list[str] = field(default_factory=list)

    @property
    def progress(self) -> int:
        if self.status in ("completed", "waiting_for_user"):
            return 100
        if not self.steps:
            return 0
        # Only completed steps count; cap below 100 while running.
        return min(99, int(100 * len(self.done_steps) / len(self.steps)))

    def to_dict(self) -> dict[str, Any]:
        return {
            "job_id": self.job_id,
            "kind": self.kind,
            "status": self.status,
            "step": self.step,
            "step_label": STEP_LABELS.get(self.step, self.step),
            "progress": self.progress,
            "steps": [
                {
                    "key": s,
                    "label": STEP_LABELS.get(s, s),
                    "state": "done" if s in self.done_steps else ("active" if s == self.step and self.status == "processing" else "pending"),
                }
                for s in self.steps
            ],
            "notes": self.notes,
            "error": self.error,
            "result": self.result,
        }


class JobContext:
    def __init__(self, job: Job) -> None:
        self.job = job

    def step(self, key: str) -> None:
        job = self.job
        if job.step in job.steps and job.step not in job.done_steps and job.step != key:
            job.done_steps.append(job.step)
        if key not in job.steps:
            job.steps.append(key)
        job.step = key

    def note(self, message: str) -> None:
        self.job.notes.append(message)


class JobManager:
    def __init__(self, workers: int = 4) -> None:
        self._jobs: dict[str, Job] = {}
        self._lock = threading.Lock()
        self._pool = ThreadPoolExecutor(max_workers=workers, thread_name_prefix="job")

    def submit(self, session_id: str, kind: str, steps: list[str], fn: Callable[[JobContext], dict[str, Any]],
               final_status: str = "completed") -> Job:
        job = Job(job_id=secrets.token_urlsafe(16), session_id=session_id, kind=kind, steps=list(steps))
        with self._lock:
            self._jobs[job.job_id] = job

        def run() -> None:
            ctx = JobContext(job)
            job.status = "processing"
            try:
                result = fn(ctx)
                if job.step in job.steps and job.step not in job.done_steps:
                    job.done_steps.append(job.step)
                job.result = result
                job.step = final_status
                job.status = final_status
            except UserFacingError as exc:
                job.error = str(exc)
                job.status = "failed"
                job.step = "failed"
            except Exception:  # never leak internals to the user
                log.error("Job %s (%s) failed:\n%s", job.job_id, kind, traceback.format_exc())
                job.error = "Something went wrong while processing your resume. Please try again."
                job.status = "failed"
                job.step = "failed"

        self._pool.submit(run)
        return job

    def get(self, job_id: str) -> Job | None:
        with self._lock:
            return self._jobs.get(job_id)


jobs = JobManager()
