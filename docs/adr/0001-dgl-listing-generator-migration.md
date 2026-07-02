# ADR 0001 — Migrating the DGL listing generator onto the AI platform

- **Status:** Accepted (planning)
- **Date:** 2026-06-02
- **Deciders:** phuc.buidang
- **Source system:** `bds-genai-dgl` (`/Users/phuc.buidang/Documents/GitHub/bds-genai-dgl`)
- **Target system:** `backend` (this repo — "AI Solution Engineering Platform")

## Context

`bds-genai-dgl` is the live PropertyGuru VN (batdongsan.com.vn) real-estate
description generator. It works, but it carries legacy debt we want to shed:

- Python 3.10 / Poetry, import-time singletons that open MongoDB at import
  (`usage_service = UsageService(mongo_client.get_database(...))`).
- 1,000+ line service files (`core/generator/service/pair_address.py`).
- Broad `try/except → response_base.fail()` instead of typed errors.
- Raw OpenAI SDK with no tracing, prompt management, or eval.
- `BackgroundTasks` used for DB writes (lost on crash).

`backend` is a clean hexagonal FastAPI platform (Python 3.12 / uv, async
SQLAlchemy + Alembic, Redis, langchain/langgraph/langfuse/llama-index,
ports/adapters business layer, durable async tasks, typed `AppError`
hierarchy, lifespan-managed resources). Its business layer is currently only
an `EchoCompletionHandler` placeholder.

The goal is to move the DGL domain logic into `backend` and modernize it,
**without breaking live clients**.

## Decisions

### D1 — Preserve the legacy API contract

Existing PropertyGuru VN clients depend on the current endpoints and the
custom `response_base` success/fail envelope. We keep them **byte-compatible**:
`POST /description`, `POST /pair_address`, `GET /usage_limit/{user_id}`,
`GET /reset/{user_id}`, `GET /reset_all`, `PUT /day_limit`,
`POST /listing/submit`, `GET /listing` — same paths under **`/api/v1`**
(legacy `API_V1_STR="/api/v1"`), same query/body params, same response shape,
and **public** (legacy mounts these without auth).

**Consequence:** A dedicated legacy-compat router and a ported response
envelope live at the edge. The typed `AppError` hierarchy is mapped to the
legacy envelope only at that boundary. New platform features (`/api/v1/...`,
bearer auth, typed errors) coexist but are not forced onto legacy callers.
Beyond the wire contract, the domain's **input/output and core generation logic
are frozen** — only the LLM transport and cross-cutting infrastructure change.

### D2 — Keep MongoDB

Legacy persistence (usage quotas, submitted listings, project-summary cache)
stays in MongoDB. We do **not** migrate this data to Postgres now.

**Consequence:** Add `motor` as an optional dependency and a first-class
Mongo adapter wired through the platform's lifespan/resources pattern
(open/close, injected — **no import-time singletons**). Postgres/Alembic
remain available for future platform tables but are not required by the
migrated domain. Revisit a Mongo→Postgres move as a separate, later decision.

### D3 — Route generation through `ai/llm` + Langfuse

Replace the raw OpenAI SDK calls with the platform's `build_llm_instance(...)`
(langchain `ModelRouter` → `BaseChatModel`) and pass `instance.trace_config(...)`
so every generation is traced in Langfuse with user/request/session metadata.

**Consequence (migration = transport swap, output preserved):** keep the
existing prompt text and the legacy response parsing (regex title/description,
contact insertion, title casing), and pin model params (`model`, `temperature`,
`top_p`, `max_tokens`, `stop`, `response_format`) to match legacy. Token-usage
accounting moves from `tiktoken` to langchain usage metadata, mapped back to the
legacy `tokens.usage.*` shape on listings. Verified by golden/parity tests.

**Langfuse adopted (revised 2026-06-02):** Langfuse IS used for this project —
tracing on + prompt management. Generation is traced via a per-instance Langfuse
tracker (`build_langfuse_tracker`, `trace_config` callbacks), so the exact
rendered prompt + tokens are captured per call. Static prompts (e.g.
`project_summary`) are fetched from Langfuse Prompt Management through a
`PromptProvider` port; a **file fallback** keeps local/test working when
`LANGFUSE_ENABLED=false` (the tracker is a no-op and `get_prompt` raises →
resolved from the packaged `prompts/*.txt`). Dynamic, code-assembled prompts
(description / pair_address) stay code-driven, versioned via a `PROMPT_VERSION`
stamped on each listing and captured by tracing. Set `LANGFUSE_ENABLED=true`
with keys in the DGL deployment.

**Structured output (fast-follow):** moving the LLM call to structured output
(`with_structured_output`) is the better long-term design and is planned right
**after** parity is proven — not in the initial transport swap.

### D4 — Strangler migration, plan/ADR first

Migrate incrementally (simplest domains first, generator last), keeping the
legacy app runnable until parity is proven. This session produces the plan +
this ADR only; no application code is written yet.

**Consequence:** Output parity is verified with golden-output tests and
optional shadow traffic before cutover. See the companion plan for phases.

## Alternatives considered

- **Reuse `business/completions`** for the generator — rejected: the generator
  is structured-params→`{title, description}`, not chat messages→content;
  forcing it through `CompletionRequest`/`CompletionResult` distorts both.
  We add a new `business/listing` module instead.
- **New v2 API / drop legacy** (D1) — rejected for now: breaks live clients.
- **Port data to Postgres** (D2) — deferred: adds data-migration risk for no
  immediate product gain.
- **Lift-and-shift raw OpenAI** (D3) — rejected: misses the observability/eval
  win that is a primary reason for the platform move.

## Open items (need confirmation, see plan §8)

- Target FastAPI pin (`<0.116`) is **older** than legacy's `0.135.1`. Confirm
  bumping the platform pin before porting code written against 0.135.
- External config to carry over: Google Maps base URL + **`Referer` header**
  requirement, `BDS_PROJECT_URL`, Mongo credentials, model name/keys.
- **Location mapping is dropped** (deprecated in legacy): the new→old VN
  address mapping service/schema/config and the `address_version=NEW`
  old-address branch are **not** migrated.
- Whether to upgrade listing writes from `BackgroundTasks` to the durable
  outbox/tasks path during the move or as a follow-up.
