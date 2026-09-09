# Architecture notes

## Design goals

The application separates workflow logic from a specific AI vendor. `GenerationService` owns orchestration, `PromptBuilder` owns prompt policy, `Repository` owns state, and provider adapters translate the neutral request into vendor-specific calls.

## State machine

```text
queued -> submitting -> polling -> succeeded
                              \-> failed
```

Every transition is stored as an event. A generation also has an idempotency key, preventing an accidental duplicate submission within the same session.

## Provider boundary

The included mock is deterministic and offline. `HttpImageProvider` is a deliberately generic integration template because real providers differ in authentication, payload shape and result delivery. Its parsing methods should be adapted and contract-tested against the selected provider.

## Scaling path

The demo uses FastAPI background tasks and SQLite for a zero-infrastructure review experience. A production version should use a durable queue, PostgreSQL, object storage, distributed locks and worker heartbeats. These production components are not claimed as implemented here.

