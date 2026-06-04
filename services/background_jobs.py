"""Fila de trabalhos pesados em segundo plano (UI não bloqueia)."""

from __future__ import annotations

import asyncio
import logging
import os
import threading
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import StrEnum
from queue import Empty, Queue
from typing import Any, Protocol, TypeVar

logger = logging.getLogger(__name__)

# Alinhado com services.blog.brief.LONG_FORM_THRESHOLD
LONG_FORM_THRESHOLD = 2600


class _BriefLike(Protocol):
    word_count: int


T = TypeVar("T")

ProgressReporter = Callable[[float, str], None]


class JobStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class JobKind(StrEnum):
    BLOG = "blog"
    TEXT = "text"
    BATCH = "batch"
    URLS = "urls"


@dataclass
class BackgroundJob:
    """Estado de um trabalho na fila."""

    id: str
    label: str
    kind: JobKind
    status: JobStatus = JobStatus.PENDING
    progress: float = 0.0
    message: str = ""
    result: Any = None
    error: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except ValueError:
        return default


def queue_min_blog_words() -> int:
    return _env_int("GEO_QUEUE_MIN_BLOG_WORDS", LONG_FORM_THRESHOLD)


def queue_min_text_chars() -> int:
    return _env_int("GEO_QUEUE_MIN_TEXT_CHARS", 12_000)


def queue_min_batch_rows() -> int:
    return _env_int("GEO_QUEUE_MIN_BATCH_ROWS", 2)


def queue_min_url_count() -> int:
    return _env_int("GEO_QUEUE_MIN_URL_COUNT", 3)


def should_queue_blog(brief: _BriefLike, *, use_llm: bool) -> bool:
    """Artigos longos ou geração com IA acima do limiar vão para a fila."""
    if brief.word_count >= queue_min_blog_words():
        return True
    return use_llm and brief.word_count >= 2000


def should_queue_text(text: str) -> bool:
    """Textos colados muito grandes vão para a fila."""
    return len((text or "").strip()) >= queue_min_text_chars()


def should_queue_batch(row_count: int, specs: list) -> bool:
    if row_count >= queue_min_batch_rows():
        return True
    return any(s.brief.word_count >= queue_min_blog_words() for s in specs)


def should_queue_urls(url_count: int, *, use_llm: bool) -> bool:
    """Várias URLs ou geração com IA em lote vão para a fila."""
    if url_count >= queue_min_url_count():
        return True
    return use_llm and url_count >= 2


def count_words(text: str) -> int:
    return len((text or "").split())


class BackgroundJobService:
    """Fila FIFO com worker dedicado (thread daemon)."""

    def __init__(self) -> None:
        self._jobs: dict[str, BackgroundJob] = {}
        self._lock = threading.Lock()
        self._queue: Queue[tuple[str, Callable[[ProgressReporter], Any]]] = Queue()
        self._worker = threading.Thread(target=self._worker_loop, daemon=True)
        self._worker.start()

    def submit(
        self,
        runner: Callable[[ProgressReporter], T],
        *,
        label: str,
        kind: JobKind | str,
    ) -> str:
        job_id = uuid.uuid4().hex[:10]
        kind_val = JobKind(kind) if isinstance(kind, str) else kind
        with self._lock:
            self._jobs[job_id] = BackgroundJob(
                id=job_id,
                label=label[:120],
                kind=kind_val,
                message="Na fila…",
            )
        self._queue.put((job_id, runner))
        return job_id

    def get(self, job_id: str) -> BackgroundJob | None:
        with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                return None
            return BackgroundJob(
                id=job.id,
                label=job.label,
                kind=job.kind,
                status=job.status,
                progress=job.progress,
                message=job.message,
                result=job.result,
                error=job.error,
                created_at=job.created_at,
            )

    def list_active(self) -> list[BackgroundJob]:
        with self._lock:
            return [
                BackgroundJob(
                    id=j.id,
                    label=j.label,
                    kind=j.kind,
                    status=j.status,
                    progress=j.progress,
                    message=j.message,
                )
                for j in self._jobs.values()
                if j.status in (JobStatus.PENDING, JobStatus.RUNNING)
            ]

    def active_count(self) -> int:
        return len(self.list_active())

    def _update(self, job_id: str, **fields: Any) -> None:
        with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                return
            for key, value in fields.items():
                setattr(job, key, value)

    def _worker_loop(self) -> None:
        while True:
            try:
                job_id, runner = self._queue.get(timeout=0.5)
            except Empty:
                continue
            try:
                self._update(
                    job_id,
                    status=JobStatus.RUNNING,
                    progress=0.02,
                    message="A iniciar…",
                )

                def report(progress: float, message: str = "") -> None:
                    self._update(
                        job_id,
                        progress=max(0.0, min(1.0, progress)),
                        message=message or "A processar…",
                    )

                result = runner(report)
                self._update(
                    job_id,
                    status=JobStatus.COMPLETED,
                    progress=1.0,
                    message="Concluído",
                    result=result,
                    error=None,
                )
            except Exception as exc:
                logger.exception("Trabalho em background falhou (%s): %s", job_id, exc)
                self._update(
                    job_id,
                    status=JobStatus.FAILED,
                    message="Falhou",
                    error=str(exc),
                )
            finally:
                self._queue.task_done()


_service: BackgroundJobService | None = None


def get_background_job_service() -> BackgroundJobService:
    global _service
    if _service is None:
        _service = BackgroundJobService()
    return _service


def run_blog_job(
    report: ProgressReporter,
    *,
    brief: _BriefLike,
    config: Any,
    use_llm: bool,
    provider: str | None,
    article_id: int | None,
    user_id: int | None,
) -> Any:
    from services.blog_pipeline import run_blog_pipeline, run_blog_pipeline_async

    if use_llm:

        def on_progress(event) -> None:
            report(event.progress, event.message)

        return asyncio.run(
            run_blog_pipeline_async(
                brief,
                use_advanced=config.use_advanced,
                use_llm=True,
                provider=provider,
                manager=config.ai_manager,
                on_progress=on_progress,
                article_id=article_id,
                user_id=user_id,
            )
        )

    report(0.15, "Geração local em curso…")
    result = run_blog_pipeline(
        brief,
        use_advanced=config.use_advanced,
        use_llm=False,
        provider=provider,
        manager=config.ai_manager,
        article_id=article_id,
        user_id=user_id,
    )
    report(1.0, "Concluído")
    return result


def run_text_job(
    report: ProgressReporter,
    *,
    body: str,
    title: str,
    config: Any,
    geo_niche: str,
) -> dict[str, Any]:
    from core.insight_extractor import extract_insights_from_text, merge_insights
    from services.url_pipeline import run_url_pipeline

    report(0.08, "A analisar o texto…")
    ins = extract_insights_from_text(
        body,
        title=title,
        use_advanced=config.use_advanced,
    )
    if not ins:
        raise ValueError("Não foi possível extrair insights do texto.")

    merged = merge_insights([ins])
    merged["geo_niche"] = geo_niche
    report(0.35, "A gerar índice e artigo GEO…")
    result = run_url_pipeline(
        [ins],
        merged,
        use_llm=config.use_llm,
        provider=config.provider,
        manager=config.ai_manager,
        geo_niche=geo_niche,
    )
    report(1.0, "Concluído")
    return {
        "insight": ins,
        "merged": merged,
        "result": result,
        "source_text": body,
    }


def run_urls_job(
    report: ProgressReporter,
    *,
    urls: list[str],
    config: Any,
    geo_niche: str,
) -> dict[str, Any]:
    from core.insight_extractor import extract_insights, merge_insights
    from services.article_fetcher import fetch_many_with_stats
    from services.url_pipeline import run_url_pipeline

    report(0.08, "A buscar URLs…")
    fetched, fetch_stats = fetch_many_with_stats(urls)
    warnings = [f"{a.url}: {a.error}" for a in fetched if a.error]
    cache_msg = fetch_stats.summary_message()

    report(0.32, "A extrair insights…")
    insights_list = [
        ins
        for a in fetched
        if (ins := extract_insights(a, use_advanced=config.use_advanced))
    ]
    if not insights_list:
        raise ValueError("Nenhuma matéria processada a partir das URLs.")

    merged = merge_insights(insights_list)
    merged["geo_niche"] = geo_niche

    report(0.55, "A gerar índice e artigo GEO…")
    result = run_url_pipeline(
        insights_list,
        merged,
        use_llm=config.use_llm,
        provider=config.provider,
        manager=config.ai_manager,
        geo_niche=geo_niche,
    )
    report(1.0, "Concluído")
    return {
        "warnings": warnings,
        "cache_msg": cache_msg,
        "fetch_stats": fetch_stats,
        "insights_list": insights_list,
        "merged": merged,
        "result": result,
    }


def run_batch_job(
    report: ProgressReporter,
    *,
    specs: list,
    config: Any,
    use_llm: bool,
    provider: str | None,
    user_id: int | None = None,
    save_to_history: bool = False,
    notify_webhook: bool = False,
) -> Any:
    import asyncio

    from services.batch_csv import run_batch
    from services.webhook_notifier import notify_batch_completed

    total = len(specs)

    def on_progress(current: int, total_rows: int, topic: str) -> None:
        base = (current - 1) / total_rows if total_rows else 0
        report(base + 0.05, f"[{current}/{total_rows}] {topic[:50]}…")

    batch_result = run_batch(
        specs,
        use_llm=use_llm,
        use_advanced=config.use_advanced,
        provider=provider,
        manager=config.ai_manager if use_llm else None,
        on_progress=on_progress,
        user_id=user_id,
        save_to_history=save_to_history,
    )
    if notify_webhook:
        asyncio.run(
            notify_batch_completed(
                output_dir=batch_result.output_dir,
                total=batch_result.total,
                succeeded=batch_result.succeeded,
                failed=batch_result.failed,
            )
        )
    return batch_result
