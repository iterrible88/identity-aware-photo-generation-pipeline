from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    data_dir: Path = Path(os.getenv("APP_DATA_DIR", "runtime"))
    provider: str = os.getenv("AI_PROVIDER", "mock")
    api_base_url: str = os.getenv("AI_API_BASE_URL", "https://api.example.com/v1")
    api_key: str = os.getenv("AI_API_KEY", "")
    poll_interval: float = float(os.getenv("AI_POLL_INTERVAL_SECONDS", "1"))
    max_poll_attempts: int = int(os.getenv("AI_MAX_POLL_ATTEMPTS", "60"))
    max_references: int = int(os.getenv("MAX_REFERENCES", "4"))
    max_generations: int = int(os.getenv("MAX_GENERATIONS_PER_SESSION", "4"))

