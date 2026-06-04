"""Testes da fila de trabalhos em segundo plano."""

from __future__ import annotations

import time

import pytest

from services.background_jobs import (
    BackgroundJobService,
    JobKind,
    JobStatus,
    should_queue_batch,
    should_queue_blog,
    should_queue_text,
    should_queue_urls,
)
from dataclasses import dataclass


@dataclass
class _FakeBrief:
    word_count: int = 1000


@dataclass
class _FakeSpec:
    brief: _FakeBrief


def test_should_queue_blog_long_form():
    assert should_queue_blog(_FakeBrief(2600), use_llm=False) is True


def test_should_queue_blog_llm_medium():
    assert should_queue_blog(_FakeBrief(2000), use_llm=True) is True
    assert should_queue_blog(_FakeBrief(1999), use_llm=True) is False


def test_should_queue_text_threshold():
    assert should_queue_text("x" * 12_000) is True
    assert should_queue_text("x" * 11_999) is False


def test_should_queue_urls_count_or_llm() -> None:
    assert should_queue_urls(3, use_llm=False) is True
    assert should_queue_urls(2, use_llm=True) is True
    assert should_queue_urls(1, use_llm=False) is False


def test_should_queue_batch_rows_or_long_brief():
    specs = [_FakeSpec(_FakeBrief(500))]
    assert should_queue_batch(2, specs) is True
    assert should_queue_batch(1, [_FakeSpec(_FakeBrief(2600))]) is True
    assert should_queue_batch(1, [_FakeSpec(_FakeBrief(500))]) is False


def test_background_job_service_runs_and_completes():
    svc = BackgroundJobService()
    done: list[str] = []

    def _runner(report) -> str:
        report(0.5, "meio")
        done.append("ok")
        return "result"

    job_id = svc.submit(_runner, label="Teste", kind=JobKind.BLOG)

    deadline = time.time() + 5
    job = None
    while time.time() < deadline:
        job = svc.get(job_id)
        if job and job.status == JobStatus.COMPLETED:
            break
        time.sleep(0.05)

    assert job is not None
    assert job.status == JobStatus.COMPLETED
    assert job.result == "result"
    assert done == ["ok"]


def test_background_job_service_records_failure():
    svc = BackgroundJobService()

    def _fail(_report):
        raise ValueError("falha simulada")

    job_id = svc.submit(_fail, label="Erro", kind=JobKind.TEXT)

    deadline = time.time() + 5
    job = None
    while time.time() < deadline:
        job = svc.get(job_id)
        if job and job.status == JobStatus.FAILED:
            break
        time.sleep(0.05)

    assert job is not None
    assert job.status == JobStatus.FAILED
    assert "falha simulada" in (job.error or "")
