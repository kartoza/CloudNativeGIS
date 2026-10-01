"""Request fields shared by endpoints that upload their results themselves."""

import shutil
from typing import Dict, List, Optional

from pydantic import BaseModel

from app.utils.upload import upload_outputs


class FileUpload(BaseModel):
    """Where one result file goes: a presigned PUT URL, and its content type.

    The content type is the one the URL was signed with, so it's sent as is.
    """

    url: str
    content_type: str


class LayerUploads(BaseModel):
    """Where one layer's result files go, by role (data, visual, thumbnail).

    `layer` names the layer as requested (a GeoPackage layer or raster
    table); omit it for a single-layer source (a shapefile or a TIFF).
    """

    layer: Optional[str] = None
    files: Dict[str, FileUpload]


def deliver(
    files: list,
    errors: list,
    workdir: str,
    uploads: Optional[List[LayerUploads]],
    job_id: str,
) -> dict:
    """Return a job's result: its files to collect, or - with uploads - sent.

    Uploaded results leave nothing to collect: the workdir goes at once,
    and the job reports each file's size, SHA-256 and info as `outputs`.
    """
    if not uploads:
        return {"files": files, "errors": errors, "workdir": workdir}
    try:
        outputs, missing = upload_outputs(
            files, [spec.model_dump() for spec in uploads], job_id
        )
    finally:
        shutil.rmtree(workdir, ignore_errors=True)
    return {"files": [], "errors": errors + missing, "outputs": outputs}
