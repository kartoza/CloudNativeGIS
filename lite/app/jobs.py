"""In-memory background job registry (no Celery/broker required).

Each job runs a conversion in a thread pool and records its outcome
in a process-local dict. This only works with a single API process —
job state is lost on restart and isn't shared across workers, which
is an accepted tradeoff for this database-free "lite" service.
"""

import logging
import shutil
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from typing import Callable, Optional

from app.config import JOB_MAX_WORKERS, JOB_RESULT_TTL
from app.errors import ConversionError

logger = logging.getLogger(__name__)


@dataclass
class Job:
    """Tracks the status and outcome of one background conversion."""

    id: str
    status: str = "processing"  # processing | done | failed
    result: Optional[dict] = None
    error: Optional[str] = None
    error_status: int = 502
    detail: Optional[str] = None
    detail_progress: Optional[float] = None
    created_at: float = field(default_factory=time.time)
    finished_at: Optional[float] = None
    collected: set = field(default_factory=set)


_jobs: dict[str, Job] = {}
_lock = threading.Lock()
_executor = ThreadPoolExecutor(max_workers=JOB_MAX_WORKERS)


def submit(work: Callable[[str], dict]) -> str:
    """Run work(job_id) in a worker thread and return a job id to poll.

    work() must return a result dict (see routers for the expected
    shape) or raise ConversionError on failure.
    """
    job_id = str(uuid.uuid4())
    with _lock:
        _jobs[job_id] = Job(id=job_id)
    logger.info("Job %s submitted", job_id)
    _executor.submit(_run, job_id, work)
    _reap_expired()
    return job_id


def update_detail(
    job_id: str, detail: str, progress: Optional[float] = None
) -> None:
    """Report progress text (and optionally a 0..1 fraction) for a job.

    A no-op once the job has finished.
    """
    with _lock:
        job = _jobs.get(job_id)
        if job and job.status == "processing":
            job.detail = detail
            if progress is not None:
                job.detail_progress = progress


def _run(job_id: str, work: Callable[[str], dict]) -> None:
    try:
        result = work(job_id)
        with _lock:
            job = _jobs[job_id]
            job.status = "done"
            job.result = result
            job.finished_at = time.time()
        errors = result.get("errors") or []
        if errors:
            logger.warning(
                "Job %s completed with %d skipped item(s): %s",
                job_id,
                len(errors),
                errors,
            )
        else:
            logger.info(
                "Job %s completed: %d file(s) produced",
                job_id,
                len(result.get("files", [])),
            )
    except ConversionError as e:
        logger.error("Job %s failed: %s", job_id, e.message)
        with _lock:
            job = _jobs[job_id]
            job.status = "failed"
            job.error = e.message
            job.error_status = e.status_code
            job.finished_at = time.time()
    except Exception as e:  # noqa: BLE001 - surface unexpected errors
        logger.exception("Job %s failed with an unexpected error", job_id)
        with _lock:
            job = _jobs[job_id]
            job.status = "failed"
            job.error = str(e)
            job.error_status = 500
            job.finished_at = time.time()


def mark_collected(job_id: str, filename: str) -> bool:
    """Record a streamed result file; returns True once all have been."""
    with _lock:
        job = _jobs.get(job_id)
        if not job:
            return False
        job.collected.add(filename)
        expected = {f["name"] for f in (job.result or {}).get("files", [])}
        return bool(expected) and job.collected >= expected


def get(job_id: str) -> Optional[Job]:
    """Look up a job by id, or None if it doesn't exist (or expired)."""
    _reap_expired()
    return _jobs.get(job_id)


def discard(job_id: str) -> None:
    """Drop a job's record once its result has been collected."""
    with _lock:
        _jobs.pop(job_id, None)


def _reap_expired() -> None:
    """Drop finished jobs whose result was never collected in time.

    Also removes the workdir of any unclaimed file result, so an
    abandoned job doesn't leak disk space.
    """
    cutoff = time.time() - JOB_RESULT_TTL
    with _lock:
        stale = [
            job_id
            for job_id, job in _jobs.items()
            if job.finished_at is not None and job.finished_at < cutoff
        ]
        stale_jobs = [_jobs.pop(job_id) for job_id in stale]

    for job in stale_jobs:
        workdir = (job.result or {}).get("workdir")
        if workdir:
            shutil.rmtree(workdir, ignore_errors=True)
