from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

import pandas as pd


class BaseLoader(ABC):
    @abstractmethod
    def load_table(self, table_name: str) -> pd.DataFrame:
        raise NotImplementedError

    @abstractmethod
    def load_all(self) -> dict[str, pd.DataFrame]:
        raise NotImplementedError

    @staticmethod
    def _ensure_path(path: str | Path) -> Path:
        resolved = Path(path).expanduser().resolve()
        if not resolved.exists():
            raise FileNotFoundError(f"File not found: {resolved}")
        return resolved

