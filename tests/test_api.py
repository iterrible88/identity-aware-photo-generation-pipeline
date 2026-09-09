import io
import time
from pathlib import Path

from fastapi.testclient import TestClient
from PIL import Image

from app.config import Settings
from app.main import create_app


def image_bytes() -> bytes:
    output = io.BytesIO()
    Image.new("RGB", (320, 400), (105, 135, 170)).save(output, "JPEG")
    return output.getvalue()


def test_complete_mock_workflow(tmp_path: Path):
    app = create_app(Settings(data_dir=tmp_path, poll_interval=0, max_poll_attempts=5))
    with TestClient(app) as client:
        session = client.post("/sessions", json={"purpose": "Portfolio test", "consent_confirmed": True})
        assert session.status_code == 201
        session_id = session.json()["id"]
        upload = client.post(
            f"/sessions/{session_id}/references",
            files={"file": ("portrait.jpg", image_bytes(), "image/jpeg")},
        )
        assert upload.status_code == 201
        generation = client.post(
            f"/sessions/{session_id}/generations",
            json={"scene": "A professional studio portrait", "idempotency_key": "test-request-01"},
        )
        assert generation.status_code == 202
        generation_id = generation.json()["id"]
        current = client.get(f"/generations/{generation_id}").json()
        assert current["status"] == "succeeded"
        assert client.get(f"/generations/{generation_id}/result").status_code == 200


def test_consent_is_required(tmp_path: Path):
    client = TestClient(create_app(Settings(data_dir=tmp_path)))
    response = client.post("/sessions", json={"purpose": "Portfolio test", "consent_confirmed": False})
    assert response.status_code == 422

