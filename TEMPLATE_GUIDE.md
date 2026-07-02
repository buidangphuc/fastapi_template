# Template Guide — build a new product on this platform

This repo is a **minimal-core template**: a fresh boot serves health + bearer
auth + Swagger and opens **zero** addons. Every capability below is opt-in, so
your product starts simple and grows only where it actually needs to.

Architecture rules live in `.agents/fastapi-template-repo/` (SKILL.md +
references/architecture.md) — read those before wiring anything.

## 0. Fork checklist

1. Clone/fork, then `cp .env.example .env` and set `AUTH_BEARER_TOKEN`.
2. `make dev` → `curl localhost:8000/healthz` — you have a running core.
3. Rename the project in `pyproject.toml` + `PROJECT_NAME` default.
4. Delete what you won't use: `app/modules/ai/` (and the `[ai]` extra) if the
   product has no LLM features; `alembic/` if no Postgres.

## 1. Turn on capabilities as you need them

| Need | Flip in `.env` | Backing service |
|---|---|---|
| Postgres (SQLAlchemy + Alembic) | `DATABASE_ENABLED=true` + `POSTGRES_*` | postgres |
| Redis | `REDIS_ENABLED=true` + `REDIS_*` | redis |
| Async jobs (queue + tasks + worker) | `QUEUE_ENABLED=true TASKS_ENABLED=true` | redis (or memory/sqs/rabbitmq) |
| Rate limiting | `RATE_LIMIT_ENABLED=true` | memory or redis |
| Caching | `CACHE_ENABLED=true` | memory or redis |
| Object storage | `OBJECTS_ENABLED=true` | memory or S3 (`uv sync --extra aws`) |
| MongoDB | `MONGO_ENABLED=true` | mongo (`--extra mongo`) |
| Idempotency keys | `IDEMPOTENCY_ENABLED=true` | postgres |
| Outbox / webhooks | `OUTBOX_ENABLED` / `WEBHOOKS_ENABLED` | postgres |
| Quota | `QUOTA_ENABLED=true` | memory/postgres/mongo |
| LLM + tracing + RAG | `uv sync --extra ai`, then `CHAT_MODEL=...`, `LANGFUSE_ENABLED`, `RAG_ENABLED` | provider keys / langfuse |

The standard stack for a typical service is DATABASE + REDIS + QUEUE + TASKS +
RATE_LIMIT — `docker-compose.local.yaml` is the worked example.

## 2. Add a business domain (the one pattern to copy)

```text
app/modules/business/<domain>/
  schemas.py        # request/result Pydantic models
  types.py          # enums/constants
  services/         # orchestration — keyword-only constructor deps, no Request/app.state
  stores/           # own the table/collection details
  integrations/     # external HTTP APIs — __init__(self, client, settings)
app/api/v1/<domain>/
  dependencies.py   # resolve the service (get_service_resource) — no generic deps.py
  router.py         # mounts leaf routers, attaches Depends(require_principal)
  <leaf>.py         # thin endpoints: parse -> one service call -> response model
app/bootstrap/<domain>.py
  <DOMAIN>_SERVICE_NAME, <Domain>Runtime (async close), build_<domain>_runtime(),
  <Domain>Addon (is_enabled gates on your *_ENABLED flag;
  open() -> resources.services[NAME] = runtime)
app/core/config/<domain>.py
  <Domain>SettingsMixin(BaseModel) — *_ENABLED defaults False; add to Settings
```

Then register the addon in `app/bootstrap/addons.py:default_resource_addons()`
and include your router in `app/api/router.py` gated on your flag. The
`completions` surface is the living reference for the thin-transport shape;
its handler is injected via `create_app(completion_handler=...)`.

Rules that keep the template clean (enforced by review, spelled out in
`.agents/`): endpoints never build clients/stores; business services never
read `Request`/`app.state`; touch bootstrap only for app-lifetime resources.

## 3. Optional installs (extras)

| Extra | Brings | Needed for |
|---|---|---|
| `ai` | langchain, langchain-openai, langgraph, langfuse, llama-index-core, openai | `app/modules/ai/*` (LLM router, tracing, RAG) |
| `aws` | aioboto3 | S3 object storage, SQS queue |
| `mongo` | motor, pymongo | Mongo gateway |
| `rabbitmq` | aio-pika | RabbitMQ queue backend |

Dev installs everything: `uv sync --dev --all-extras` (what `make test` uses).
A missing extra fails with an actionable message at the feature's entry point
(see `app/modules/ai/_deps.py`), never at import/boot time.

## 4. Verify as you go

`make test` (full pytest) · `make lint` + `make typecheck` · `make dev` for
the live server · `make docker-run` for the composed standard stack ·
`make docker-run-langfuse` to layer self-hosted tracing.
