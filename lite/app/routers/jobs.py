"""Poll background conversion job status and collect results."""

import shutil

from fastapi import APIRouter, BackgroundTasks, HTTPException
from fastapi.responses import FileResponse, JSONResponse

from app import jobs

router = APIRouter()


@router.get("/api/v1/jobs/{job_id}")
def get_job(job_id: str):
    """Report a job's status: processing, done, or failed."""
    job = jobs.get(job_id)
    if job is None:
        raise HTTPException(404, "Job not found")

    if job.status == "processing":
        return {
            "job_id": job_id,
            "status": "processing",
            "detail": job.detail,
            "detailProgress": job.detail_progress,
        }

    if job.status == "failed":
        return JSONResponse(
            status_code=job.error_status,
            content={
                "job_id": job_id,
                "status": "failed",
                "detail": job.error,
            },
        )

    return {
        "job_id": job_id,
        "status": "done",
        "results": [
            {
                "name": file["name"],
                "result_url": f'/api/v1/jobs/{job_id}/result/{file["name"]}',
            }
            for file in job.result.get("files", [])
        ],
        # Layers/tables skipped rather than failing the whole job.
        "errors": job.result.get("errors", []),
    }


@router.get("/api/v1/jobs/{job_id}/result/{filename}")
def get_job_result(
    job_id: str, filename: str, background_tasks: BackgroundTasks
):
    """Stream one of a finished job's output files.

    Once every file the job produced has been streamed at least once, the
    job and its workdir are discarded.
    """
    job = jobs.get(job_id)
    if job is None or job.status != "done":
        raise HTTPException(404, "Result not available")

    files = {file["name"]: file for file in job.result.get("files", [])}
    file_info = files.get(filename)
    if not file_info:
        raise HTTPException(404, "Result not available")

    if jobs.mark_collected(job_id, filename):
        background_tasks.add_task(
            shutil.rmtree, job.result["workdir"], ignore_errors=True
        )
        background_tasks.add_task(jobs.discard, job_id)

    return FileResponse(
        file_info["path"],
        media_type=file_info["media_type"],
        filename=file_info["name"],
        background=background_tasks,
    )
