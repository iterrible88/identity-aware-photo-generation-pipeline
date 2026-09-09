from __future__ import annotations

import asyncio
import json
from pathlib import Path

from app.models import Status
from app.providers import ImageProvider
from app.store import Repository


class GenerationService:
    def __init__(
        self, repository: Repository, provider: ImageProvider, artifacts: Path,
        poll_interval: float, max_poll_attempts: int,
    ):
        self.repository = repository
        self.provider = provider
        self.artifacts = artifacts
        self.poll_interval = poll_interval
        self.max_poll_attempts = max_poll_attempts

    async def run(self, generation_id: str) -> None:
        generation = self.repository.one("SELECT * FROM generations WHERE id = ?", (generation_id,))
        references = [
            Path(row["path"]) for row in self.repository.all(
                "SELECT path FROM references_ WHERE session_id = ? ORDER BY id", (generation["session_id"],)
            )
        ]
        try:
            self.repository.update_generation(generation_id, Status.SUBMITTING)
            task_id = await self.provider.submit(generation["prompt"], references)
            self.repository.update_generation(generation_id, Status.POLLING, provider_task_id=task_id)
            for _ in range(self.max_poll_attempts):
                result = await self.provider.poll(task_id)
                if result.status == "succeeded":
                    output_dir = self.artifacts / generation_id
                    result_path = output_dir / "result.jpg"
                    await self.provider.download(result, result_path, references)
                    manifest = {
                        "generation_id": generation_id,
                        "provider_task_id": task_id,
                        "reference_count": len(references),
                        "status": "succeeded",
                    }
                    (output_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
                    self.repository.update_generation(
                        generation_id, Status.SUCCEEDED, result_path=str(result_path)
                    )
                    return
                if result.status == "failed":
                    raise RuntimeError(result.error or "Provider generation failed")
                await asyncio.sleep(self.poll_interval)
            raise TimeoutError("Provider polling limit exceeded")
        except Exception as error:
            self.repository.update_generation(generation_id, Status.FAILED, error=str(error))

