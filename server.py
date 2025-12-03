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

    if "frame_urls" not in payload:
        raise HTTPException(status_code=400, detail="Missing frame_urls")

    frame_urls = payload["frame_urls"]
    if not isinstance(frame_urls, list) or not frame_urls:
        raise HTTPException(status_code=400, detail="frame_urls must be non-empty list")

    job_id = str(uuid.uuid4())
    job_dir = os.path.join(VLM_ROOT, job_id)
    os.makedirs(job_dir, exist_ok=True)

    saved_files = []

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
            raise HTTPException(400, f"Failed to fetch frame {url}: {e}")

        saved_files.append(save_path)

    # ✅ 关键：直接返回“文件列表”，不要包 JSON
    return [FileResponse(p, media_type="image/jpeg") for p in saved_files]
