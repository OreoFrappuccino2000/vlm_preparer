from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
import os
import uuid
import zipfile
import requests
from urllib.parse import urljoin

app = FastAPI()

# Public storage
VLM_ROOT = "/app/vlm_files"
os.makedirs(VLM_ROOT, exist_ok=True)

# Public domain of this service (CHANGE TO YOUR REAL DOMAIN)
BASE_PUBLIC_URL = "https://vlmpreparer-production.up.railway.app"
VIDEO_SERVER_BASE = "https://videoserver-production.up.railway.app"

# Expose files publicly
app.mount("/vlm_files", StaticFiles(directory=VLM_ROOT), name="vlm_files")

MAX_FRAMES = 20


@app.post("/prepare_vlm")
def prepare_vlm(payload: dict):

    if "frame_urls" not in payload:
        raise HTTPException(400, "Missing frame_urls list")

    frame_urls = payload["frame_urls"]

    if not isinstance(frame_urls, list):
        raise HTTPException(400, "frame_urls must be a list")

    if len(frame_urls) > MAX_FRAMES:
        raise HTTPException(400, f"Too many frames. Max allowed is {MAX_FRAMES}")

    job_id = str(uuid.uuid4())
    job_dir = os.path.join(VLM_ROOT, job_id)
    os.makedirs(job_dir, exist_ok=True)

    public_image_urls = []

    for idx, url in enumerate(frame_urls, start=1):
        filename = f"frame_{idx:03d}.jpg"
        save_path = os.path.join(job_dir, filename)

        # ✅ Convert relative frame path into full public URL
        if url.startswith("/"):
            fetch_url = urljoin(VIDEO_SERVER_BASE, url)
        else:
            fetch_url = url

        try:
            with requests.get(fetch_url, stream=True, timeout=90) as r:
                r.raise_for_status()
                with open(save_path, "wb") as f:
                    for chunk in r.iter_content(chunk_size=1024 * 1024):
                        if chunk:
                            f.write(chunk)
        except Exception as e:
            raise HTTPException(400, f"Failed to fetch frame: {fetch_url} | {str(e)}")

        # ✅ Add PUBLIC URL for VLM
        public_url = f"{BASE_PUBLIC_URL}/vlm_files/{job_id}/{filename}"
        public_image_urls.append(public_url)

    # ---------------------------
    # ZIP images
    # ---------------------------
    zip_filename = f"{job_id}.zip"
    zip_path = os.path.join(VLM_ROOT, zip_filename)

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
        for f in os.listdir(job_dir):
            zipf.write(
                os.path.join(job_dir, f),
                arcname=f
            )

    public_zip_url = f"{BASE_PUBLIC_URL}/vlm_files/{zip_filename}"

    return {
        "job_id": job_id,
        "total_files": len(public_image_urls),
        "image_files": public_image_urls,   # ✅ VLM-READY (PUBLIC URLs!)
        "zip_file": public_zip_url          # ✅ PUBLIC ZIP URL
    }
