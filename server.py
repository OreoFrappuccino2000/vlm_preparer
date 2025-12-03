from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
import os
import uuid
import requests

app = FastAPI()

VLM_ROOT = "/app/vlm_files"
os.makedirs(VLM_ROOT, exist_ok=True)

@app.post("/prepare_vlm")
def prepare_vlm(payload: dict):

    # ---------------------------
    # 1. Validate input
    # ---------------------------
    if "frame_urls" not in payload:
        raise HTTPException(status_code=400, detail="Missing frame_urls")

    frame_urls = payload["frame_urls"]

    if not isinstance(frame_urls, list):
        raise HTTPException(status_code=400, detail="frame_urls must be a list")

    if len(frame_urls) == 0:
        raise HTTPException(status_code=400, detail="frame_urls is empty")

    # ---------------------------
    # 2. Prepare job folder
    # ---------------------------
    job_id = str(uuid.uuid4())
    job_dir = os.path.join(VLM_ROOT, job_id)
    os.makedirs(job_dir, exist_ok=True)

    saved_files = []

    # ---------------------------
    # 3. Download each frame as binary
    # ---------------------------
    for idx, url in enumerate(frame_urls, start=1):
        filename = f"frame_{idx:03d}.jpg"
        save_path = os.path.join(job_dir, filename)

        try:
            with requests.get(url, stream=True, timeout=60) as r:
                r.raise_for_status()
                with open(save_path, "wb") as f:
                    for chunk in r.iter_content(chunk_size=1024 * 1024):
                        f.write(chunk)
        except Exception as e:
            raise HTTPException(
                status_code=400,
                detail=f"Failed to fetch frame {url}: {str(e)}"
            )

        saved_files.append(save_path)

    # ---------------------------
    # 4. RETURN AS TRUE Array[File]
    # ---------------------------
    return {
        "job_id": job_id,
        "total_files": len(saved_files),
        "files": [FileResponse(path) for path in saved_files]   # ✅ REAL FILES
    }
