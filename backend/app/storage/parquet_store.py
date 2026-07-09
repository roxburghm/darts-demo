import logging

import pandas as pd
import pyarrow.parquet as pq
from pathlib import Path
from ..config import settings

logger = logging.getLogger(__name__)


class ParquetStore:
    """Read/write parsed datasets as Parquet files."""

    def write(self, session_id: str, df: pd.DataFrame):
        """Write a DataFrame as a Parquet file."""
        output_dir = settings.parsed_dir / session_id
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / "data.parquet"
        df.to_parquet(output_path, engine="pyarrow", compression="snappy", index=False)

    def read(
        self,
        session_id: str,
        columns: list[str] | None = None,
        limit: int | None = None,
    ) -> pd.DataFrame:
        """Read a dataset from Parquet, optionally selecting specific columns."""
        parquet_path = settings.parsed_dir / session_id / "data.parquet"
        if not parquet_path.exists():
            raise FileNotFoundError(f"No parsed data for session {session_id}")

        # Validate requested columns against actual schema to handle stale client data
        if columns:
            schema = pq.read_schema(parquet_path)
            valid_cols = set(schema.names)
            invalid = [c for c in columns if c not in valid_cols]
            if invalid:
                logger.warning("Requested columns not in Parquet: %s (available: %s)", invalid, list(valid_cols)[:20])
                columns = [c for c in columns if c in valid_cols]
                if not columns:
                    raise FileNotFoundError(f"None of the requested columns exist in the dataset")

        df = pd.read_parquet(parquet_path, engine="pyarrow", columns=columns)

        if limit is not None:
            df = df.head(limit)

        return df

    def exists(self, session_id: str) -> bool:
        parquet_path = settings.parsed_dir / session_id / "data.parquet"
        return parquet_path.exists()


parquet_store = ParquetStore()
