from pathlib import Path
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "Darts Anomaly Demo"
    data_dir: Path = Path(__file__).parent.parent / "data"
    upload_dir: Path = Path(__file__).parent.parent / "data" / "uploads"
    parsed_dir: Path = Path(__file__).parent.parent / "data" / "parsed"
    results_dir: Path = Path(__file__).parent.parent / "data" / "results"

    max_upload_size_mb: int = 500
    chunk_size_bytes: int = 2 * 1024 * 1024  # 2MB
    session_ttl_hours: int = 24
    max_chart_points: int = 3000

    cors_origins: list[str] = ["http://localhost:5173", "http://localhost:3000"]

    class Config:
        env_prefix = "DAD_"


settings = Settings()

# Ensure runtime directories exist
for d in [settings.upload_dir, settings.parsed_dir, settings.results_dir]:
    d.mkdir(parents=True, exist_ok=True)
