from __future__ import annotations

import io
import shutil
import uuid
from pathlib import Path

from fastapi import BackgroundTasks, FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from PIL import Image, UnidentifiedImageError

from app.config import Settings
from app.models import GenerationCreate, GenerationView, SessionCreate, Status
from app.prompts import PromptBuilder
from app.providers import HttpImageProvider, MockImageProvider
from app.service import GenerationService
from app.store import Repository


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings()
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    repository = Repository(settings.data_dir / "pipeline.sqlite3")
    provider = (
        MockImageProvider()
        if settings.provider == "mock"
        else HttpImageProvider(settings.api_base_url, settings.api_key)
    )
    service = GenerationService(
        repository, provider, settings.data_dir / "artifacts",
        settings.poll_interval, settings.max_poll_attempts,
    )
    app = FastAPI(title="Identity-Aware Photo Generation Pipeline", version="0.1.0")
    app.state.repository = repository
    app.state.settings = settings
    app.state.service = service

    @app.get("/health")
    def health() -> dict:
        return {"status": "ok", "provider": settings.provider}

    @app.post("/sessions", status_code=201)
    def create_session(payload: SessionCreate) -> dict:
        if not payload.consent_confirmed:
            raise HTTPException(422, "Consent and image rights must be confirmed")
        session_id = uuid.uuid4().hex
        repository.execute(
            "INSERT INTO sessions(id, purpose, consent_confirmed) VALUES (?, ?, ?)",
            (session_id, payload.purpose, 1),
        )
        return {"id": session_id, "remaining_generations": settings.max_generations}

    @app.post("/sessions/{session_id}/references", status_code=201)
    async def upload_reference(session_id: str, file: UploadFile = File(...)) -> dict:
        session = repository.one("SELECT * FROM sessions WHERE id = ?", (session_id,))
        if not session:
            raise HTTPException(404, "Session not found")
        count = repository.one(
            "SELECT COUNT(*) AS count FROM references_ WHERE session_id = ?", (session_id,)
        )["count"]
        if count >= settings.max_references:
            raise HTTPException(409, "Reference limit reached")
        content = await file.read(12 * 1024 * 1024 + 1)
        if len(content) > 12 * 1024 * 1024:
            raise HTTPException(413, "Reference image is too large")
        try:
            with Image.open(io.BytesIO(content)) as image:
                image.verify()
            with Image.open(io.BytesIO(content)) as image:
                width, height = image.size
                normalized = image.convert("RGB")
                reference_id = uuid.uuid4().hex
                path = settings.data_dir / "references" / session_id / f"{reference_id}.jpg"
                path.parent.mkdir(parents=True, exist_ok=True)
                normalized.save(path, "JPEG", quality=92)
        except (UnidentifiedImageError, OSError):
            raise HTTPException(415, "A valid JPEG or PNG image is required")
        repository.execute(
            "INSERT INTO references_(id, session_id, path, width, height) VALUES (?, ?, ?, ?, ?)",
            (reference_id, session_id, str(path), width, height),
        )
        return {"id": reference_id, "width": width, "height": height}

    @app.post("/sessions/{session_id}/generations", response_model=GenerationView, status_code=202)
    def create_generation(session_id: str, payload: GenerationCreate, background: BackgroundTasks):
        session = repository.one("SELECT * FROM sessions WHERE id = ?", (session_id,))
        if not session:
            raise HTTPException(404, "Session not found")
        references = repository.all("SELECT id FROM references_ WHERE session_id = ?", (session_id,))
        if not references:
            raise HTTPException(409, "Upload at least one reference image")
        existing = repository.one(
            "SELECT * FROM generations WHERE session_id = ? AND idempotency_key = ?",
            (session_id, payload.idempotency_key),
        )
        if existing:
            return existing
        used = repository.one(
            "SELECT COUNT(*) AS count FROM generations WHERE session_id = ?", (session_id,)
        )["count"]
        if used >= settings.max_generations:
            raise HTTPException(429, "Generation quota reached")
        generation_id = uuid.uuid4().hex
        prompt = PromptBuilder().build(payload, len(references))
        repository.execute(
            "INSERT INTO generations(id, session_id, status, prompt, idempotency_key) VALUES (?, ?, ?, ?, ?)",
            (generation_id, session_id, Status.QUEUED, prompt, payload.idempotency_key),
        )
        repository.execute(
            "INSERT INTO events(generation_id, status, detail) VALUES (?, ?, ?)",
            (generation_id, Status.QUEUED, "{}"),
        )
        background.add_task(service.run, generation_id)
        return repository.one("SELECT * FROM generations WHERE id = ?", (generation_id,))

    @app.get("/generations/{generation_id}", response_model=GenerationView)
    def get_generation(generation_id: str):
        result = repository.one("SELECT * FROM generations WHERE id = ?", (generation_id,))
        if not result:
            raise HTTPException(404, "Generation not found")
        return result

    @app.get("/generations/{generation_id}/events")
    def get_events(generation_id: str) -> list[dict]:
        return repository.all(
            "SELECT status, detail, created_at FROM events WHERE generation_id = ? ORDER BY id",
            (generation_id,),
        )

    @app.get("/generations/{generation_id}/result")
    def get_result(generation_id: str):
        result = repository.one("SELECT * FROM generations WHERE id = ?", (generation_id,))
        if not result or result["status"] != Status.SUCCEEDED or not result["result_path"]:
            raise HTTPException(404, "Result is not available")
        return FileResponse(result["result_path"], media_type="image/jpeg", filename="result.jpg")

    return app


app = create_app()

