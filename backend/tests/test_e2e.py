"""End-to-end API tests: upload -> JD -> analyze -> select changes -> generate -> validate ->
preview -> download -> regenerate -> start over. Uses a fake AI provider and the real
DOCX/PDF pipeline (LibreOffice or MS Word)."""
from __future__ import annotations

import io
import time
import zipfile

import docx
import pymupdf
import pytest
from fastapi.testclient import TestClient

from app.documents.converter import docx_to_pdf
from app.main import app
from app.parsing.docx_xml import enumerate_paragraphs, paragraph_text

from .conftest import needs_converter

client = TestClient(app)


def wait(job_id: str, timeout: float = 240) -> dict:
    deadline = time.time() + timeout
    last_progress = -1
    while time.time() < deadline:
        r = client.get(f"/api/jobs/{job_id}/status")
        assert r.status_code == 200
        data = r.json()
        assert data["progress"] >= last_progress or data["status"] == "failed"  # progress never goes backwards
        last_progress = data["progress"]
        if data["status"] in ("completed", "waiting_for_user", "failed"):
            if data["status"] != "failed":
                assert data["progress"] == 100
            else:
                assert data["progress"] < 100
            return data
        assert data["progress"] < 100
        time.sleep(0.3)
    raise AssertionError("job timed out")


def upload(path, name="resume.docx"):
    with open(path, "rb") as fh:
        r = client.post("/api/resume/upload", files={"file": (name, fh, "application/octet-stream")})
    assert r.status_code == 200, r.text
    body = r.json()
    job = wait(body["job_id"])
    assert job["status"] == "completed", job
    return body["session_id"], job["result"]


def test_health():
    r = client.get("/api/health")
    assert r.status_code == 200 and r.json()["status"] == "ok"


def test_upload_rejects_invalid():
    r = client.post("/api/resume/upload", files={"file": ("evil.exe", b"MZ\x90\x00", "application/octet-stream")})
    assert r.status_code == 400 and "Traceback" not in r.text


@needs_converter
def test_full_workflow_docx(sample_docx, sample_jd, fake_ai):
    sid, up = upload(sample_docx)
    res = up["resume"]
    assert res["name"] == "Jordan Avery"
    assert res["counts"]["experience_entries"] == 3 and res["page_count"] == 1
    assert res["profile_photo"] is True

    r = client.post("/api/jd/analyze", data={"session_id": sid, "jd_text": sample_jd})
    assert r.status_code == 200 and "Kubernetes" in r.json()["keywords_preview"]

    job = wait(client.post("/api/resume/analyze", json={"session_id": sid}).json()["job_id"])
    assert job["status"] == "waiting_for_user", job
    analysis = job["result"]
    changes = analysis["changes"]
    assert changes, "expected suggestions"
    all_suggested = " ".join(c["suggested"] for c in changes)
    assert "Kubernetes" not in all_suggested and "50%" not in all_suggested  # fabrications blocked
    assert analysis["blocked_count"] >= 1  # Kubernetes rewrite stays blocked even after the repair round
    repaired = [c for c in changes if c["original"].startswith("Designed PostgreSQL schemas")]
    assert repaired and "50%" not in repaired[0]["suggested"]  # repair round fixed the invented metric
    assert "repair" in fake_ai.calls
    missing = {e["term"] for e in analysis["keyword_groups"]["missing"]}
    assert {"Kubernetes", "Terraform"} <= missing
    for c in changes:
        assert c["status"] == "suggested" and c["impact"] in ("high", "medium", "low")
        assert c["original"] and c["suggested"] and c["reason"]
    summary_change = next(c for c in changes if c["section"] == "summary")
    assert "SRC999" not in summary_change["source_claims"]  # unknown claim ids dropped

    # Selective application: accept all but one
    rejected = next(c for c in changes if c["change_id"] != summary_change["change_id"])
    decisions = {c["change_id"]: "accepted" for c in changes}
    decisions[rejected["change_id"]] = "rejected"
    r = client.post("/api/resume/apply-changes", json={"session_id": sid, "decisions": decisions})
    assert r.status_code == 200
    proj = r.json()["comparison"]
    assert proj["tailored"] >= proj["original"]

    job = wait(client.post("/api/resume/tailor", json={"session_id": sid, "decisions": decisions}).json()["job_id"])
    assert job["status"] == "completed", job
    result = job["result"]
    assert job["docx_url"] and job["pdf_url"] and job["page_count"] == 1
    assert result["ats"]["comparison"]["tailored"] >= result["ats"]["comparison"]["original"]
    assert all(result["validation"]["summary"].values()), result["validation"]["summary"]
    assert result["template"]["level"] == "High"
    assert result["pages"]["original"] == 1 and result["pages"]["tailored"] == 1
    statuses = {c["change_id"]: c["status"] for c in result["changes"]}
    assert statuses[rejected["change_id"]] == "rejected" and statuses[summary_change["change_id"]] == "applied"

    # Downloads are real files that correspond to the preview
    d = client.get(job["docx_url"])
    assert d.status_code == 200 and d.content[:2] == b"PK"
    text = "\n".join(paragraph_text(h.element) for h in enumerate_paragraphs(docx.Document(io.BytesIO(d.content))))
    assert "Python backend engineer with 6 years" in text  # accepted change applied
    assert rejected["original"].strip() in text  # rejected change not applied
    for company in ("Northwind Analytics", "Bluebird Logistics", "Copperleaf Studio"):
        assert company in text
    assert "Kubernetes" not in text
    p = client.get(job["pdf_url"])
    assert p.status_code == 200 and p.content.startswith(b"%PDF")
    pdf = pymupdf.open(stream=p.content, filetype="pdf")
    assert pdf.page_count == result["page_count"]
    assert "Python backend engineer" in pdf[0].get_text()
    both = client.get(f"/api/download/{result['downloads']['both']['file_id']}?s={sid}")
    assert sorted(zipfile.ZipFile(io.BytesIO(both.content)).namelist()) == sorted(
        [result["downloads"]["docx"]["name"], result["downloads"]["pdf"]["name"]])
    assert result["downloads"]["docx"]["name"] == "Jordan_Avery_Tailored_Resume.docx"
    prev = client.get(f"/api/preview/tailored/1?s={sid}")
    assert prev.status_code == 200 and prev.content[:4] == b"\x89PNG"
    assert client.get(f"/api/preview/tailored/2?s={sid}").status_code == 404
    assert client.get(f"/api/download/{result['downloads']['docx']['file_id']}?s=wrong-session-id-123").status_code == 404
    assert client.get(f"/api/download/nonexistent?s={sid}").status_code == 404

    # Regenerate with current selections keeps decisions
    job = wait(client.post("/api/resume/regenerate", json={"session_id": sid, "mode": "selections"}).json()["job_id"])
    assert job["status"] == "completed", job
    st2 = {c["change_id"]: c["status"] for c in job["result"]["changes"]}
    assert st2[rejected["change_id"]] == "rejected"
    assert job["result"]["generation"] == result["generation"] + 1
    assert client.get(job["docx_url"]).status_code == 200
    assert client.get(f"/api/download/{result['downloads']['docx']['file_id']}?s={sid}").status_code == 404  # old file expired

    # One-click fresh regenerate: re-runs tailoring but preserves accepted/rejected decisions
    job = wait(client.post("/api/resume/regenerate", json={"session_id": sid, "mode": "fresh"}).json()["job_id"])
    assert job["status"] == "completed", job
    st3 = {c["change_id"]: c["status"] for c in job["result"]["changes"]}
    assert st3[rejected["change_id"]] == "rejected" and st3[summary_change["change_id"]] == "applied"

    # Start over deletes everything
    assert client.delete(f"/api/sessions/{sid}").status_code == 200
    assert client.get(f"/api/sessions/{sid}").status_code == 404


@needs_converter
def test_full_workflow_pdf_input(sample_docx, sample_jd, tmp_path, no_ai):
    pdf_path, _ = docx_to_pdf(sample_docx, tmp_path)
    sid, up = upload(pdf_path, "resume.pdf")
    res = up["resume"]
    assert res["file_type"] == "pdf" and res["name"] == "Jordan Avery"
    assert res["counts"]["experience_entries"] == 3
    client.post("/api/jd/analyze", data={"session_id": sid, "jd_text": sample_jd})
    job = wait(client.post("/api/resume/analyze", json={"session_id": sid}).json()["job_id"])
    assert job["status"] == "waiting_for_user"
    decisions = {c["change_id"]: "accepted" for c in job["result"]["changes"]}
    job = wait(client.post("/api/resume/tailor", json={"session_id": sid, "decisions": decisions}).json()["job_id"])
    assert job["status"] == "completed", job
    result = job["result"]
    assert result["validation"]["summary"]["Completeness"] and result["validation"]["summary"]["PDF"]
    assert any("PDF" in lim for lim in result["template"]["limitations"])  # honest limitation reported
    pdf = pymupdf.open(stream=client.get(job["pdf_url"]).content, filetype="pdf")
    text = "".join(pg.get_text() for pg in pdf)
    for company in ("Northwind Analytics", "Bluebird Logistics", "Copperleaf Studio", "Jordan Avery"):
        assert company in text


def test_session_required():
    r = client.post("/api/resume/analyze", json={"session_id": "does-not-exist"})
    assert r.status_code == 404
    assert client.get("/api/jobs/unknown/status").status_code == 404
