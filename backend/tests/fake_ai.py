"""Deterministic stand-in for Gemini used by the test-suite (never used in production).

It deliberately mixes good suggestions with fabricated ones so tests can prove the
anti-fabrication layer blocks them.
"""
from __future__ import annotations

import json
import re

from app.ai.base import AIProvider, AIResponseError


def _blocks_after(prompt: str, marker: str) -> list[tuple[str, str]]:
    part = prompt.split(marker, 1)[1]
    out = []
    for line in part.splitlines():
        m = re.match(r"^(B\d{3}) \[[^\]]*\] (.*)$", line)
        if m:
            out.append((m.group(1), m.group(2)))
        elif out and line.startswith("Return JSON"):
            break
    return out


class FakeProvider(AIProvider):
    name = "fake"

    def __init__(self, malformed_first: int = 0, fail_tasks: set[str] | None = None) -> None:
        self.calls: list[str] = []
        self.malformed_first = malformed_first
        self.fail_tasks = fail_tasks or set()

    @property
    def available(self) -> bool:
        return True

    def generate_json(self, system: str, prompt: str, *, task: str, temperature: float = 0.2) -> dict:
        self.calls.append(task)
        if task in self.fail_tasks:
            raise AIResponseError("simulated failure")
        if self.malformed_first > 0:
            self.malformed_first -= 1
            return {"unexpected": True}
        return getattr(self, f"_{task}")(prompt)

    def _structure(self, prompt: str) -> dict:
        blocks = _blocks_after(prompt, "RESUME BLOCKS:")
        claims = []
        for bid, text in blocks:
            if "Redis caching" in text:
                claims.append({"claim": "Used Redis caching to improve API performance", "blocks": [bid],
                               "quote": "adding Redis caching and query optimisation"})
            if "Built backend applications" in text:
                claims.append({"claim": "Built Django backend applications", "blocks": [bid],
                               "quote": "Built backend applications in Django"})
        claims.append({"claim": "Led a Kubernetes migration", "blocks": [blocks[0][0]], "quote": "led Kubernetes migration"})
        return {"experience": [], "projects": [], "education": [], "certifications": [], "skills": [], "claims": claims}

    def _jd(self, prompt: str) -> dict:
        return {
            "job_title": "Senior Python Backend Engineer", "company": "Example Corp", "years_experience": 5,
            "education_requirements": ["Bachelor's degree in Computer Science or related field"],
            "certifications": ["AWS certification"],
            "required_skills": ["Python", "FastAPI", "PostgreSQL", "Redis", "AWS", "Docker", "Kubernetes", "Terraform"],
            "preferred_skills": ["Kafka", "GraphQL"],
            "responsibilities": [
                "Design, build and maintain REST APIs and microservices using Python and FastAPI",
                "Deploy and operate services on Amazon Web Services using Docker and Kubernetes",
                "Optimize PostgreSQL database performance and caching with Redis",
                "Build CI/CD pipelines and infrastructure as code with Terraform",
                "Mentor engineers and participate in code reviews",
            ],
            "keywords": [
                {"term": "REST APIs", "category": "technical_skill", "importance": "required"},
                {"term": "database performance", "category": "domain", "importance": "required"},
                {"term": "Haskell", "category": "programming_language", "importance": "required"},  # not in JD
            ],
            "evidence": [
                {"term": "Microservices", "quote": "Containerised 12 services with Docker"},
                {"term": "Kafka", "quote": "built Kafka streaming pipelines"},  # not in resume -> rejected
            ],
        }

    def _tailor(self, prompt: str) -> dict:
        out = []
        for bid, text in _blocks_after(prompt, "EDITABLE PARAGRAPHS"):
            new = text
            reason = "Aligns wording with the JD."
            if text.startswith("Software engineer with 6 years"):
                new = ("Python backend engineer with 6 years of experience building REST APIs and backend services. "
                       "Experienced with Django, FastAPI and PostgreSQL, deploying services on AWS with Docker. "
                       "Comfortable working in agile teams and mentoring junior developers.")
                reason = "Emphasizes Python, REST APIs and backend development from the JD."
            elif text.startswith("Developed RESTful services"):
                new = "Developed Python REST APIs with FastAPI for the customer analytics platform."
            elif text.startswith("Containerised 12 services"):
                new = "Containerised 12 services with Docker and Kubernetes, deploying to AWS ECS via GitHub Actions."
            elif text.startswith("Designed PostgreSQL schemas"):
                new = "Designed PostgreSQL schemas and wrote data migration scripts, improving query speed by 50%."
            elif text.startswith("Built backend applications in Django"):
                new = "Built Django backend applications and REST APIs to manage shipment tracking for 200+ clients."
            elif text.startswith("Cloud & DevOps:"):
                new = "Cloud & DevOps: Docker, AWS (EC2, S3, Lambda), GitHub Actions, Linux"
            out.append({"id": bid, "text": new, "reason": reason, "source_claims": ["SRC001", "SRC999"],
                        "keywords": ["Python", "REST API"]})
        return {"blocks": out}

    def _repair(self, prompt: str) -> dict:
        items = json.loads(prompt.split("ITEMS:\n", 1)[1].split("\n\nReturn JSON", 1)[0])
        out = []
        for it in items:
            if it["original"].startswith("Containerised 12 services"):  # stubborn: fabricates again -> stays blocked
                text = "Containerised 12 services with Docker and Kubernetes."
            elif it["original"].startswith("Designed PostgreSQL schemas"):  # genuine fix: drops the invented 50%
                text = "Designed PostgreSQL schemas and wrote data migration scripts for the analytics platform."
            else:
                text = it["original"]
            out.append({"id": it["id"], "text": text, "reason": "Fixed after fact-check.", "keywords": []})
        return {"blocks": out}

    def _condense(self, prompt: str) -> dict:
        return {"blocks": []}
