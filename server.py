from fastapi import FastAPI, HTTPException, Body
from fastapi.responses import Response
import os
import json
import zipfile
import uuid

app = FastAPI()

@app.post("/prepare_vlm")
def prepare_vlm(payload: dict = Body(...)):
    """
    Expected payload from /run:

    {
      "job_id": "...",
      "frame_paths": ["/tmp/xxx/early/scene_001.jpg", ...]
    }
    """

    job_id = payload.get("job_id")
    frame_paths = payload.get("frame_paths")

    if not job_id or not frame_paths:
        raise HTTPException(status_code=400, detail="Missing job_id or frame_paths")

    # Verify all files exist
    missing = [p for p in frame_paths if not os.path.exists(p)]
    if missing:
        raise HTTPException(
            status_code=400,
            detail=f"Missing frame files: {missing}"
        )

    # Create a temporary zip to return as files
    zip_name = f"{job_id}_vlm_frames.zip"
    zip_path = f"/tmp/{zip_name}"

    with zipfile.ZipFile(zip_path, "w") as zipf:
        for path in frame_paths:
            arcname = os.path.basename(path)
            zipf.write(path, arcname)

    # Return ZIP as binary file (Dify will receive it as File)
    with open(zip_path, "rb") as f:
        data = f.read()

    headers = {
        "Content-Disposition": f'attachment; filename="{zip_name}"'
    }

    return Response(
        content=data,
        media_type="application/zip",
        headers=headers
    )
