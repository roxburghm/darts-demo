import json
from pathlib import Path
from ..config import settings
from ..models.schemas import DartsAnomalyResult


class ResultCache:
    """Cache anomaly detection results as JSON files."""

    def save(self, session_id: str, run_id: str, result: DartsAnomalyResult):
        result_dir = settings.results_dir / session_id
        result_dir.mkdir(parents=True, exist_ok=True)
        result_path = result_dir / f"{run_id}.json"
        result_path.write_text(result.model_dump_json(indent=2))

    def load(self, session_id: str, run_id: str) -> DartsAnomalyResult | None:
        result_path = settings.results_dir / session_id / f"{run_id}.json"
        if not result_path.exists():
            return None
        data = json.loads(result_path.read_text())
        return DartsAnomalyResult(**data)

    def exists(self, session_id: str, run_id: str) -> bool:
        result_path = settings.results_dir / session_id / f"{run_id}.json"
        return result_path.exists()


result_cache = ResultCache()
