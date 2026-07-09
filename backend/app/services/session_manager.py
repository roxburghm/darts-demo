import json
import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path

from ..config import settings


class SessionManager:
    """Manages upload sessions, file storage, and metadata."""

    def create_session(
        self, filename: str, file_size: int, total_chunks: int, file_type: str = "csv"
    ) -> dict:
        session_id = uuid.uuid4().hex[:12]
        upload_id = uuid.uuid4().hex[:12]

        session_dir = settings.upload_dir / session_id
        session_dir.mkdir(parents=True, exist_ok=True)

        metadata = {
            "session_id": session_id,
            "upload_id": upload_id,
            "filename": filename,
            "file_size": file_size,
            "file_type": file_type,
            "total_chunks": total_chunks,
            "chunks_received": 0,
            "status": "uploading",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "parsing_progress": 0.0,
            "error": None,
        }

        self._write_metadata(session_id, metadata)
        return metadata

    def get_metadata(self, session_id: str) -> dict | None:
        meta_path = settings.upload_dir / session_id / "metadata.json"
        if not meta_path.exists():
            # Also check parsed dir
            meta_path = settings.parsed_dir / session_id / "metadata.json"
            if not meta_path.exists():
                return None
        return json.loads(meta_path.read_text())

    def update_metadata(self, session_id: str, updates: dict):
        metadata = self.get_metadata(session_id)
        if metadata is None:
            return
        metadata.update(updates)
        self._write_metadata(session_id, metadata)

    def get_upload_path(self, session_id: str) -> Path:
        return settings.upload_dir / session_id / "raw_upload.csv"

    def get_chunk_dir(self, session_id: str) -> Path:
        chunk_dir = settings.upload_dir / session_id / "chunks"
        chunk_dir.mkdir(parents=True, exist_ok=True)
        return chunk_dir

    def get_parsed_dir(self, session_id: str) -> Path:
        parsed = settings.parsed_dir / session_id
        parsed.mkdir(parents=True, exist_ok=True)
        return parsed

    def get_results_dir(self, session_id: str) -> Path:
        results = settings.results_dir / session_id
        results.mkdir(parents=True, exist_ok=True)
        return results

    def reassemble_chunks(self, session_id: str) -> Path:
        """Reassemble uploaded chunks into a single file."""
        metadata = self.get_metadata(session_id)
        chunk_dir = self.get_chunk_dir(session_id)
        output_path = self.get_upload_path(session_id)

        total_chunks = metadata["total_chunks"]
        with open(output_path, "wb") as out:
            for i in range(total_chunks):
                chunk_path = chunk_dir / f"chunk_{i:06d}"
                with open(chunk_path, "rb") as chunk:
                    out.write(chunk.read())

        # Cleanup chunks
        shutil.rmtree(chunk_dir, ignore_errors=True)
        return output_path

    def cleanup_session(self, session_id: str):
        """Remove all data for a session."""
        for base_dir in [settings.upload_dir, settings.parsed_dir, settings.results_dir]:
            session_dir = base_dir / session_id
            if session_dir.exists():
                shutil.rmtree(session_dir, ignore_errors=True)

    def _write_metadata(self, session_id: str, metadata: dict):
        # Write to upload dir first, then parsed dir if it exists
        upload_meta = settings.upload_dir / session_id / "metadata.json"
        if upload_meta.parent.exists():
            upload_meta.write_text(json.dumps(metadata, indent=2))

        parsed_meta = settings.parsed_dir / session_id / "metadata.json"
        if parsed_meta.parent.exists():
            parsed_meta.write_text(json.dumps(metadata, indent=2))


session_manager = SessionManager()
