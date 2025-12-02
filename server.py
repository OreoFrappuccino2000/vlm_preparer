from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
import uuid
import os
import requests
import zipfile

app = FastAPI()

# Public files directory
FILES_ROOT = "/app/vlm_files"
os.makedirs(FILES_ROOT, exist_ok=True)

app.mount("/vlm_files", StaticFiles(directory=FILES_ROOT), name="vlm_files")

DOWNLOAD_TIMEOUT = 60
CHUNK_SIZE = 1024 * 1024


@app.get("/")
def health():
    return {"status": "prepare_vlm_ok"}


@app.post("/prepare_vlm")
def prepare_vlm(frame_urls: list[str]):
    job_id = str(uuid.uuid4())
    job_dir = os.path.join(FILES_ROOT, job_id)
    os.makedirs(job_dir, exist_ok=True)

    local_files = []

    # ---------------------------
    # 1️⃣ Download Each Frame
    # ---------------------------
    for i, url in enumerate(frame_urls):
        filename = f"frame_{i+1:03d}.jpg"
        local_path = os.path.join(job_dir, filename)

        full_url = "https://videoserver-production.up.railway.app" + url

        try:
            with requests.get(full_url, stream=True, timeout=DOWNLOAD_TIMEOUT) as r:
                r.raise_for_status()
                with open(local_path, "wb") as f:
                    for chunk in r.iter_content(chunk_size=CHUNK_SIZE):
                        if chunk:
                            f.write(chunk)
        except Exception as e:
            raise HTTPException(
                status_code=400,
                detail=f"Failed to download frame: {full_url} | {e}"
            )

        local_files.append(local_path)

    # ---------------------------
    # 2️⃣ Zip for VLM Upload
    # ---------------------------
    zip_path = os.path.join(FILES_ROOT, f"{job_id}.zip")
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
        for f in local_files:
            zipf.write(f, os.path.basename(f))

    return {
        "job_id": job_id,
        "total_files": len(local_files),
        "image_files": local_files,   # ✅ Direct VLM Array[File]
        "zip_file": f"/vlm_files/{job_id}.zip"
    }
