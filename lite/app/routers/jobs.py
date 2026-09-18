"""Poll background conversion job status and collect results."""

import shutil

from fastapi import APIRouter, BackgroundTasks, HTTPException
from fastapi.responses import FileResponse, JSONResponse

from app import jobs

router = APIRouter()


@router.get('/api/v1/jobs/{job_id}')
def get_job(job_id: str):
    """Report a job's status: processing, done, or failed."""
    job = jobs.get(job_id)
    if job is None:
        raise HTTPException(404, 'Job not found')

    if job.status == 'processing':
        return {'job_id': job_id, 'status': 'processing'}

    if job.status == 'failed':
        return JSONResponse(
            status_code=job.error_status,
            content={
                'job_id': job_id,
                'status': 'failed',
                'detail': job.error,
            },
        )

    if 'stored' in job.result:
        jobs.discard(job_id)
        return {
            'job_id': job_id,
            'status': 'done',
            'stored': job.result['stored'],
        }

    return {
        'job_id': job_id,
        'status': 'done',
        'result_url': f'/api/v1/jobs/{job_id}/result',
    }


@router.get('/api/v1/jobs/{job_id}/result')
def get_job_result(job_id: str, background_tasks: BackgroundTasks):
    """Stream a finished job's output file, then discard the job."""
    job = jobs.get(job_id)
    if job is None or job.status != 'done' or 'file' not in job.result:
        raise HTTPException(404, 'Result not available')

    result = job.result
    background_tasks.add_task(
        shutil.rmtree, result['workdir'], ignore_errors=True
    )
    background_tasks.add_task(jobs.discard, job_id)

    return FileResponse(
        result['file'],
        media_type=result['media_type'],
        filename=result['filename'],
        background=background_tasks,
    )
