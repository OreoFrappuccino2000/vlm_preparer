from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
import os
import uuid
import zipfile
import requests

app = FastAPI()

# Where images & zips are stored inside the Railway container
VLM_ROOT = "/app/vlm_files"
os.makedirs(VLM_ROOT, exist_ok=True)

# Public base URL for these files (adjust if your domain changes)
PUBLIC_BASE = "https://vlmpreparer-production.up.railway.app/vlm_files"

# Serve files so they’re reachable by URL
app.mount("/vlm_files", StaticFiles(directory=VLM_ROOT), name="vlm_files")


@app.post("/prepare_vlm")
def prepare_vlm(payload: dict):
    """
    Expects:
    {
      "frame_urls": [
        "https://videoserver-production.up.railway.app/files/.../scene_001.jpg",
        ...
      ]
    }

    Returns:
    {
      "job_id": "...",
      "total_files": 20,
      "image_files": ["https://vlmpreparer.../vlm_files/<job_id>/frame_001.jpg", ...],
      "zip_file": "https://vlmpreparer.../vlm_files/<job_id>.zip"
    }
    """
    frame_urls = payload.get("frame_urls")
    if not isinstance(frame_urls, list) or not frame_urls:
        raise HTTPException(status_code=400, detail="frame_urls must be a non-empty list")

    job_id = str(uuid.uuid4())
    job_dir = os.path.join(VLM_ROOT, job_id)
    os.makedirs(job_dir, exist_ok=True)

    local_paths = []
    public_urls = []

    for idx, url in enumerate(frame_urls, start=1):
        # keep jpg by default
        _, ext = os.path.splitext(url)
        if not ext:
            ext = ".jpg"
        filename = f"frame_{idx:03d}{ext}"
        local_path = os.path.join(job_dir, filename)

        try:
            with requests.get(url, stream=True, timeout=60) as r:
                r.raise_for_status()
                with open(local_path, "wb") as f:
                    for chunk in r.iter_content(chunk_size=512 * 1024):
                        if chunk:
                            f.write(chunk)
        except Exception:
            raise HTTPException(status_code=400, detail=f"Failed to fetch frame: {url}")

        local_paths.append(local_path)
        public_urls.append(f"{PUBLIC_BASE}/{job_id}/{filename}")

    # Make a ZIP of all frames (optional but nice)
    zip_path = os.path.join(VLM_ROOT, f"{job_id}.zip")
    with zipfile.ZipFile(zip_path, "w") as zipf:
        for path in local_paths:
            zipf.write(path, arcname=os.path.basename(path))

    zip_public = f"{PUBLIC_BASE}/{job_id}.zip"

    return {
        "job_id": job_id,
        "total_files": len(public_urls),
        # ⬇⬇ THIS field should be mapped as Array[File] in Dify
        "image_files": public_urls,
        "zip_file": zip_public
    }
