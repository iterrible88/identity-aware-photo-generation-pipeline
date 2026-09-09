# Identity-Aware Photo Generation Pipeline

A privacy-safe portfolio edition of a production workflow for generating a consistent photo series from several reference images.

The project demonstrates the engineering around an image-to-image model: reference validation, consent checks, structured prompt construction, asynchronous submission, status polling, usage limits, persistent job history, and provider-independent result handling.

> This repository contains no production credentials, private infrastructure, customer data, model weights, or real reference photographs. The built-in mock provider makes the complete workflow runnable without a paid AI account.

## What it demonstrates

- FastAPI service with typed request and response models.
- Multiple reference images per generation job.
- Explicit consent and rights confirmation before processing.
- Prompt composition from scene, identity-preservation and negative constraints.
- Pluggable AI provider interface with a deterministic local mock.
- Background execution and polling of asynchronous AI jobs.
- SQLite persistence for sessions, generations and status events.
- Per-session generation quotas and idempotency keys.
- Isolated artifact directories and downloadable result manifests.
- Automated tests for prompt logic, quotas and API workflow.

## Architecture

```text
Client
  -> FastAPI API
      -> validation + consent gate
      -> SQLite repository
      -> background generation service
          -> prompt builder
          -> provider adapter
              -> Mock provider (included)
              -> HTTP provider (integration template)
          -> polling + artifact persistence
```

## Quick start

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# Linux/macOS: source .venv/bin/activate
pip install -e ".[dev]"
uvicorn app.main:app --reload
```

Open `http://127.0.0.1:8000/docs` for the interactive API documentation.

Run the end-to-end demonstration:

```bash
python -m scripts.demo
```

Run tests:

```bash
pytest
```

## Typical API flow

1. Create a session with a declared purpose and consent confirmation.
2. Upload one to four reference images.
3. Submit a generation request with a scene profile and creative brief.
4. Poll the generation endpoint until it reaches `succeeded` or `failed`.
5. Download the generated preview and inspect `manifest.json`.

## Why the mock provider matters

The provider reproduces the asynchronous lifecycle of an external AI API: `submit -> provider task id -> polling -> result`. It creates a clearly labelled preview from the first reference image, so reviewers can run the orchestration locally without sending biometric data to a third party.

## Production considerations

Before real deployment, replace the in-process background task with a durable queue, store artifacts in object storage, add authenticated users, encrypt sensitive media, define retention/deletion policies, moderate prompts and outputs, and complete a privacy and provider-compliance review.

See [architecture notes](docs/architecture.md) and [security policy](SECURITY.md).

