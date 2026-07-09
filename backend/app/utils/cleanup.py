import json
import shutil
from datetime import datetime, timezone, timedelta
from pathlib import Path

from ..config import settings


def cleanup_expired_sessions():
    """Remove sessions older than the configured TTL."""
    ttl = timedelta(hours=settings.session_ttl_hours)
    now = datetime.now(timezone.utc)

    for base_dir in [settings.upload_dir, settings.parsed_dir, settings.results_dir]:
        if not base_dir.exists():
            continue
        for session_dir in base_dir.iterdir():
            if not session_dir.is_dir():
                continue

            meta_path = session_dir / "metadata.json"
            if meta_path.exists():
                try:
                    meta = json.loads(meta_path.read_text())
                    created = datetime.fromisoformat(meta.get("created_at", ""))
                    if now - created > ttl:
                        shutil.rmtree(session_dir, ignore_errors=True)
                except (json.JSONDecodeError, ValueError, KeyError):
                    # If metadata is corrupt, check file modification time
                    mtime = datetime.fromtimestamp(meta_path.stat().st_mtime, tz=timezone.utc)
                    if now - mtime > ttl:
                        shutil.rmtree(session_dir, ignore_errors=True)
            else:
                # No metadata — check directory modification time
                try:
                    mtime = datetime.fromtimestamp(session_dir.stat().st_mtime, tz=timezone.utc)
                    if now - mtime > ttl:
                        shutil.rmtree(session_dir, ignore_errors=True)
                except OSError:
                    pass
