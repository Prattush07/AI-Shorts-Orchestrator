from fastapi import APIRouter, HTTPException, BackgroundTasks, Request, UploadFile, File
from fastapi.responses import FileResponse, StreamingResponse
import os
from pydantic import BaseModel
import uuid
from services.pipeline import process_video_pipeline
from services.database import PROJECTS_DB, save_db

router = APIRouter()

class ProjectCreateRequest(BaseModel):
    url: str

class ProjectCreateResponse(BaseModel):
    project_id: str
    status: str
    message: str

@router.get("/")
async def list_projects():
    return PROJECTS_DB

@router.post("/", response_model=ProjectCreateResponse)
async def create_project(request: ProjectCreateRequest, background_tasks: BackgroundTasks):
    if not request.url:
        raise HTTPException(status_code=400, detail="Video URL is required")

    project_id = str(uuid.uuid4())
    PROJECTS_DB[project_id] = {
        "status": "processing",
        "progress": 0,
        "clips": [],
        "sourceUrl": request.url
    }
    save_db(PROJECTS_DB)
    
    import asyncio
    asyncio.get_event_loop().run_in_executor(None, process_video_pipeline, project_id, request.url, PROJECTS_DB)
    
    return ProjectCreateResponse(
        project_id=project_id,
        status="processing",
        message="Video processing has been queued."
    )

@router.post("/upload")
async def upload_local_file(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    if not file.filename.lower().endswith((".mp4", ".mov", ".mkv", ".avi", ".webm")):
         raise HTTPException(status_code=400, detail="Invalid file type. Please upload a video file.")
         
    project_id = str(uuid.uuid4())
    temp_dir = f"temp/{project_id}"
    os.makedirs(temp_dir, exist_ok=True)
    
    # Keep the original file extension so ffmpeg / moviepy can parse containers correctly
    ext = os.path.splitext(file.filename)[1]
    file_path = f"{temp_dir}/source_video{ext}"
    
    # Save the file synchronously to disk
    with open(file_path, "wb") as buffer:
        import shutil
        shutil.copyfileobj(file.file, buffer)
        
    PROJECTS_DB[project_id] = {
        "id": project_id,
        "status": "processing",
        "progress": 5,
        "clips": [],
        "message": "File uploaded successfully. Preparing AI Engine...",
        "sourceUrl": "Local File"
    }
    save_db(PROJECTS_DB)
    
    # Start local pipeline variant
    import asyncio
    asyncio.get_event_loop().run_in_executor(None, process_video_pipeline, project_id, "", PROJECTS_DB, True, file_path)
    
    return {"project_id": project_id, "status": "processing"}

@router.get("/{project_id}/status")
async def get_project_status(project_id: str):
    if project_id not in PROJECTS_DB:
        raise HTTPException(status_code=404, detail="Project not found")
    return PROJECTS_DB[project_id]

@router.get("/download/{project_id}/clip_{clip_index}.mp4")
async def download_clip_direct(project_id: str, clip_index: int):
    file_path = f"temp/{project_id}/clip_{clip_index}.mp4"
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Clip file not found")
        
    return FileResponse(
        path=file_path, 
        filename=f"Viral_Hook_Clip_{clip_index}.mp4", 
        media_type="application/octet-stream",
        headers={"Content-Disposition": f'attachment; filename="Viral_Hook_Clip_{clip_index}.mp4"'}
    )

def iterfile(path, start, end):
    with open(path, "rb") as f:
        f.seek(start)
        remaining = end - start + 1
        while remaining > 0:
            chunk = f.read(min(1024 * 1024, remaining))
            if not chunk:
                break
            yield chunk
            remaining -= len(chunk)

@router.get("/stream/{project_id}/clip_{clip_index}.mp4")
async def stream_video(request: Request, project_id: str, clip_index: int):
    file_path = f"temp/{project_id}/clip_{clip_index}.mp4"
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Clip not found")

    file_size = os.path.getsize(file_path)
    range_header = request.headers.get("Range")

    if range_header:
        try:
            byte_range = range_header.replace("bytes=", "").split("-")
            start = int(byte_range[0])
            end = int(byte_range[1]) if len(byte_range) > 1 and byte_range[1] else file_size - 1
        except (ValueError, IndexError):
            raise HTTPException(status_code=416, detail="Invalid range header")

        if start >= file_size:
            raise HTTPException(status_code=416, detail="Range not satisfiable")

        end = min(end, file_size - 1)
        content_length = end - start + 1

        return StreamingResponse(
            iterfile(file_path, start, end),
            status_code=206,
            media_type="video/mp4",
            headers={
                "Content-Range": f"bytes {start}-{end}/{file_size}",
                "Accept-Ranges": "bytes",
                "Content-Length": str(content_length),
            },
        )

    return FileResponse(
        file_path,
        media_type="video/mp4",
        headers={
            "Accept-Ranges": "bytes",
            "Content-Length": str(file_size)
        },
    )

@router.get("/{project_id}/export-all")
async def export_all_clips(project_id: str):
    import zipfile
    import io
    
    if project_id not in PROJECTS_DB:
        raise HTTPException(status_code=404, detail="Project not found")
        
    temp_dir = f"temp/{project_id}"
    if not os.path.exists(temp_dir):
        raise HTTPException(status_code=404, detail="Project files not found")
        
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        for file in os.listdir(temp_dir):
            if file.startswith("clip_") and file.endswith(".mp4"):
                zip_file.write(os.path.join(temp_dir, file), file)
    
    zip_buffer.seek(0)
    return StreamingResponse(
        zip_buffer,
        media_type="application/x-zip-compressed",
        headers={
            "Content-Disposition": f'attachment; filename="all_clips_{project_id}.zip"'
        }
    )
