import math
from fastapi import APIRouter, UploadFile, HTTPException, BackgroundTasks
from ..models.schemas import UploadInitRequest, UploadInitResponse, UploadStatusResponse
from ..services.session_manager import session_manager
from ..config import settings

router = APIRouter(prefix="/upload", tags=["upload"])


@router.post("/init", response_model=UploadInitResponse)
async def init_upload(request: UploadInitRequest):
    if request.file_size > settings.max_upload_size_mb * 1024 * 1024:
        raise HTTPException(400, f"File exceeds maximum size of {settings.max_upload_size_mb}MB")

    total_chunks = math.ceil(request.file_size / request.chunk_size)
    metadata = session_manager.create_session(
        filename=request.filename,
        file_size=request.file_size,
        total_chunks=total_chunks,
        file_type=request.file_type,
    )

    return UploadInitResponse(
        session_id=metadata["session_id"],
        upload_id=metadata["upload_id"],
        total_chunks=total_chunks,
    )


@router.post("/{session_id}/chunk")
async def upload_chunk(session_id: str, chunk_index: int, file: UploadFile):
    metadata = session_manager.get_metadata(session_id)
    if metadata is None:
        raise HTTPException(404, "Session not found")
    if metadata["status"] not in ("uploading",):
        raise HTTPException(400, f"Session is in '{metadata['status']}' state, not accepting chunks")

    chunk_dir = session_manager.get_chunk_dir(session_id)
    chunk_path = chunk_dir / f"chunk_{chunk_index:06d}"
    content = await file.read()
    chunk_path.write_bytes(content)

    chunks_received = metadata["chunks_received"] + 1
    session_manager.update_metadata(session_id, {"chunks_received": chunks_received})

    return {"chunk_index": chunk_index, "chunks_received": chunks_received}


@router.post("/{session_id}/complete")
async def complete_upload(session_id: str, background_tasks: BackgroundTasks):
    metadata = session_manager.get_metadata(session_id)
    if metadata is None:
        raise HTTPException(404, "Session not found")

    if metadata["chunks_received"] < metadata["total_chunks"]:
        raise HTTPException(
            400,
            f"Only {metadata['chunks_received']}/{metadata['total_chunks']} chunks received",
        )

    session_manager.update_metadata(session_id, {"status": "parsing"})

    # Reassemble chunks into a single file
    file_path = session_manager.reassemble_chunks(session_id)

    # Trigger async parsing — branch on file type
    file_type = metadata.get("file_type", "csv")
    if file_type == "parquet":
        from ..services.csv_parser import process_parquet_background
        background_tasks.add_task(process_parquet_background, session_id, file_path)
    else:
        from ..services.csv_parser import parse_csv_background
        background_tasks.add_task(parse_csv_background, session_id, file_path)

    return {"session_id": session_id, "status": "parsing"}


@router.get("/{session_id}/status", response_model=UploadStatusResponse)
async def get_upload_status(session_id: str):
    metadata = session_manager.get_metadata(session_id)
    if metadata is None:
        raise HTTPException(404, "Session not found")

    return UploadStatusResponse(
        upload_id=metadata["upload_id"],
        status=metadata["status"],
        chunks_received=metadata["chunks_received"],
        total_chunks=metadata["total_chunks"],
        parsing_progress=metadata.get("parsing_progress", 0.0),
        error=metadata.get("error"),
    )
