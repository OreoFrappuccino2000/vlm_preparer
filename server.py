from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
import os
import uuid
import zipfile
import requests

app = FastAPI()

VLM_ROOT = "/app/vlm_files"
os.makedirs(VLM_ROOT, exist_ok=True)

app.mount("/vlm_files", StaticFiles(directory=VLM_ROOT), name="vlm_files")


@app.post("/prepare_vlm")
def prepare_vlm(payload: dict):

    if "frame_urls" not in payload:
        raise HTTPException(400, "Missing frame_urls list")

    frame_urls = payload["frame_urls"]

    if not isinstance(frame_urls, list):
        raise HTTPException(400, "frame_urls must be a list")

    job_id = str(uuid.uuid4())
    job_dir = os.path.join(VLM_ROOT, job_id)
    os.makedirs(job_dir, exist_ok=True)

    image_files = []

    for idx, url in enumerate(frame_urls, start=1):
        filename = f"frame_{idx:03d}.jpg"
        path = os.path.join(job_dir, filename)

        try:
            with requests.get(url, stream=True, timeout=60) as r:
                r.raise_for_status()
                with open(path, "wb") as f:
                    for chunk in r.iter_content(chunk_size=512 * 1024):
                        f.write(chunk)
        except Exception:
            raise HTTPException(400, f"Failed to fetch frame: {url}")

        image_files.append(path)

    # ---------------------------
    # ZIP images
    # ---------------------------
    zip_path = os.path.join(VLM_ROOT, f"{job_id}.zip")

    with zipfile.ZipFile(zip_path, "w") as zipf:
        for f in image_files:
            zipf.write(f, arcname=os.path.basename(f))

    return {
        "job_id": job_id,
        "total_files": len(image_files),
        "image_files": image_files,      # ✅ THIS is Array[File] for VLM
        "zip_file": f"/vlm_files/{job_id}.zip"
    }
