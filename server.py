from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
import requests
import zipfile
import uuid
import os
import shutil

app = FastAPI()

BASE_DIR = os.getcwd()
FRAME_ROOT = os.path.join(BASE_DIR, "frames")
os.makedirs(FRAME_ROOT, exist_ok=True)

MAX_FRAMES_FOR_VLM = 20   # how many frames you want to send to the VLM


# ============================
# DOWNLOAD + UNZIP + PREPARE
# ============================
@app.post("/prepare_vlm")
def prepare_vlm(zip_url: str):

    job_id = str(uuid.uuid4())
    job_dir = os.path.join(FRAME_ROOT, job_id)
    os.makedirs(job_dir, exist_ok=True)

    zip_path = os.path.join(job_dir, "input.zip")

    # 1. DOWNLOAD ZIP
    try:
        r = requests.get(zip_url, timeout=60)
        with open(zip_path, "wb") as f:
            f.write(r.content)
    except Exception:
        shutil.rmtree(job_dir, ignore_errors=True)
        raise HTTPException(status_code=400, detail="Failed to download ZIP")

    # 2. UNZIP
    try:
        with zipfile.ZipFile(zip_path, "r") as zipf:
            zipf.extractall(job_dir)
    except Exception:
        shutil.rmtree(job_dir, ignore_errors=True)
        raise HTTPException(status_code=400, detail="Invalid ZIP file")

    # 3. SELECT FRAMES FOR VLM
    frames = sorted([
        f for f in os.listdir(job_dir)
        if f.lower().endswith(".jpg")
    ])

    if not frames:
        shutil.rmtree(job_dir, ignore_errors=True)
        raise HTTPException(status_code=400, detail="No frames found in ZIP")

    selected = frames[:MAX_FRAMES_FOR_VLM]

    # 4. BUILD PUBLIC URLS
    public_urls = [
        f"/frames/{job_id}/{f}" for f in selected
    ]

    return {
        "job_id": job_id,
        "total_frames": len(frames),
        "vlm_frames": public_urls
    }


# ============================
# PUBLIC FRAME ACCESS
# ============================
@app.get("/frames/{job_id}/{filename}")
def get_frame(job_id: str, filename: str):

    frame_path = os.path.join(FRAME_ROOT, job_id, filename)

    if not os.path.exists(frame_path):
        raise HTTPException(status_code=404, detail="Frame not found")

    return FileResponse(frame_path, media_type="image/jpeg")
