from __future__ import annotations

import asyncio
import hashlib
import uuid
from dataclasses import dataclass
from pathlib import Path

import httpx
from PIL import Image, ImageDraw, ImageOps


@dataclass(frozen=True)
class ProviderResult:
    status: str
    output_url: str | None = None
    error: str | None = None


class ImageProvider:
    async def submit(self, prompt: str, references: list[Path]) -> str:
        raise NotImplementedError

    async def poll(self, task_id: str) -> ProviderResult:
        raise NotImplementedError

    async def download(self, result: ProviderResult, destination: Path, references: list[Path]) -> None:
        raise NotImplementedError


class MockImageProvider(ImageProvider):
    def __init__(self):
        self._polls: dict[str, int] = {}

    async def submit(self, prompt: str, references: list[Path]) -> str:
        digest = hashlib.sha256((prompt + str(references)).encode()).hexdigest()[:12]
        task_id = f"mock-{digest}-{uuid.uuid4().hex[:6]}"
        self._polls[task_id] = 0
        return task_id

    async def poll(self, task_id: str) -> ProviderResult:
        await asyncio.sleep(0)
        self._polls[task_id] += 1
        if self._polls[task_id] < 2:
            return ProviderResult(status="running")
        return ProviderResult(status="succeeded", output_url=f"mock://{task_id}")

    async def download(self, result: ProviderResult, destination: Path, references: list[Path]) -> None:
        with Image.open(references[0]) as source:
            image = ImageOps.exif_transpose(source).convert("RGB")
            image.thumbnail((1200, 1200))
            canvas = Image.new("RGB", image.size, "white")
            canvas.paste(image)
            draw = ImageDraw.Draw(canvas)
            label = "MOCK AI PREVIEW - NO GENERATIVE MODEL CALLED"
            draw.rectangle((0, 0, canvas.width, 42), fill=(20, 28, 45))
            draw.text((14, 13), label, fill="white")
            destination.parent.mkdir(parents=True, exist_ok=True)
            canvas.save(destination, "JPEG", quality=90)


class HttpImageProvider(ImageProvider):
    """Generic adapter template; adapt payload parsing to the selected provider."""

    def __init__(self, base_url: str, api_key: str):
        if not api_key:
            raise ValueError("AI_API_KEY is required for the HTTP provider")
        self.base_url = base_url.rstrip("/")
        self.headers = {"Authorization": f"Bearer {api_key}"}

    async def submit(self, prompt: str, references: list[Path]) -> str:
        files = [("references", (path.name, path.read_bytes(), "image/jpeg")) for path in references]
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(
                f"{self.base_url}/generations", data={"prompt": prompt}, files=files, headers=self.headers
            )
            response.raise_for_status()
            return str(response.json()["id"])

    async def poll(self, task_id: str) -> ProviderResult:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(f"{self.base_url}/generations/{task_id}", headers=self.headers)
            response.raise_for_status()
            payload = response.json()
            return ProviderResult(payload["status"], payload.get("output_url"), payload.get("error"))

    async def download(self, result: ProviderResult, destination: Path, references: list[Path]) -> None:
        if not result.output_url:
            raise ValueError("Provider returned no output URL")
        async with httpx.AsyncClient(timeout=120) as client:
            response = await client.get(result.output_url, headers=self.headers)
            response.raise_for_status()
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(response.content)

