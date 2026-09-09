from __future__ import annotations

import io
import tempfile
from pathlib import Path

from fastapi.testclient import TestClient
from PIL import Image

from app.config import Settings
from app.main import create_app


def main() -> None:
    with tempfile.TemporaryDirectory() as directory:
        app = create_app(Settings(data_dir=Path(directory), poll_interval=0, max_poll_attempts=5))
        with TestClient(app) as client:
            session = client.post(
                "/sessions", json={"purpose": "Local portfolio demonstration", "consent_confirmed": True}
            ).json()
            buffer = io.BytesIO()
            Image.new("RGB", (600, 800), (92, 126, 163)).save(buffer, "JPEG")
            client.post(
                f"/sessions/{session['id']}/references",
                files={"file": ("synthetic-reference.jpg", buffer.getvalue(), "image/jpeg")},
            ).raise_for_status()
            generation = client.post(
                f"/sessions/{session['id']}/generations",
                json={
                    "scene": "A restrained editorial portrait with soft window light",
                    "style": "documentary editorial photography",
                    "idempotency_key": "local-demo-001",
                },
            )
            generation.raise_for_status()
            result = client.get(f"/generations/{generation.json()['id']}").json()
            assert result["status"] == "succeeded", result
            print("Demo completed:", result["id"], result["status"])


if __name__ == "__main__":
    main()
