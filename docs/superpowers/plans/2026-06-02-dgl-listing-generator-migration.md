# Plan — Migrate `bds-genai-dgl` listing generator onto the AI platform

- **Date:** 2026-06-02
- **Decisions:** see [ADR 0001](../../adr/0001-dgl-listing-generator-migration.md)
  (preserve legacy API · keep MongoDB · route LLM through `ai/llm`+Langfuse ·
  strangler, plan-first)
- **Source:** `/Users/phuc.buidang/Documents/GitHub/bds-genai-dgl`
- **Target:** this repo (`/Users/phuc.buidang/Documents/work/backend`)

## 1. Source domain inventory

What we are moving, from the legacy `core/` + `common/`:

| Domain | Legacy location | Endpoints | Storage / IO |
|---|---|---|---|
| Generator (description) | `core/generator/service/description.py`, `api/v1/description.py` | `POST /description` | OpenAI, Google Maps, BDS project API |
| Generator (pair address) | `core/generator/service/pair_address.py` (~1k lines), `api/v1/pair_address.py` | `POST /pair_address` | same as above |
| Template selection | `api/v1/description.py::select_template/_calculate_weight` | — | reads recent listings (Mongo) |
| Nearby search | `core/generator/service/nearby.py` | — | Google Maps (`Referer` header required) |
| Project lookup | `core/generator/service/project.py` | — | BDS API + OpenAI summary, cached in Mongo |
| Usage limiter | `core/limiter/service/usage.py`, `api/v1/usage.py` | `GET /usage_limit/{user_id}`, `/reset/{user_id}`, `/reset_all`, `PUT /day_limit` | Mongo `users` (30-day reset) |
| Listing submit | `core/submit/service/listing.py`, `api/v1/listing.py` | `POST /listing/submit`, `GET /listing` | Mongo `submit` |
| Shared infra | `common/` (response envelope, settings, mongo, request, middleware, utils) | — | — |

Config/enums to port: `core/generator/config.py` (`StyleType`, `ToneType`,
`ProfessionalTemplateType`, `SimpleTemplateType`, `AddressVersionType`,
`LanguageType`, `TemplateResponse`) and `core/generator/schema/*`
(`AllParams`, `PairAddressParams`, `DescriptionResponse`, etc.).

> **Dropped — do NOT migrate: location mapping.** The new→old VN address
> mapping (`core/generator/service/location_mapping.py`,
> `schema/location_mapping.py`, the `LOCATION_MAPPING_*` settings, and the
> `address_version=NEW` → old-address branch in `description.py::get_nearby`)
> is dropped in legacy. We carry forward only nearby search on the address as
> supplied; no `LocationMapper` port, service, schema, config, or tests.

## 2. Target layout (new code in `backend`)

A **new business module** — not `business/completions` (that's chat-shaped;
the generator is structured-params→`{title, description}`).

```text
app/
  modules/
    business/
      listing/
        __init__.py
        config.py            # ported enums (StyleType, ToneType, *TemplateType, AddressVersionType, LanguageType)
        schemas.py           # AllParams, PairAddressParams, DescriptionResponse, PairAddressDescriptionResponse
        ports.py             # Protocols: DescriptionGenerator, NearbyProvider, ProjectProvider,
                             #            UsageQuota, ListingStore
        pipeline.py          # orchestration: template→context(gather)→prompt→LLM→parse→persist→quota
        prompts.py           # prompt builders (later: Langfuse prompt management)
        templates.py         # weighted template selection (_calculate_weight etc.)
        handlers/
          description.py     # DescriptionGenerator on ai/llm (Langfuse deferred)
          pair_address.py    # pair-address generator (refactored into units, not 1k lines)
        services/
          nearby.py          # Google Maps client (keep Referer header)
          project.py         # BDS project lookup + AI summary (summary call via ai/llm)
          usage.py           # 30-day quota service (Mongo adapter, lifespan-injected)
          listing_store.py   # listing persistence (Mongo adapter)
    platform/
      mongo/                 # NEW shared adapter
        __init__.py
        gateway.py           # thin async wrapper over motor client/db/collection
        factory.py           # build_mongo_client(settings)
        addon.py             # MongoAddon: open/close in lifespan, set resources.mongo
  api/
    legacy/                  # NEW: legacy-compat surface (paths under /api/v1, legacy envelope)
      __init__.py
      router.py              # includes the routers below; mounted under /api/v1
      response.py            # ported response_base + CustomResponseCode (byte-compatible envelope)
      description.py         # POST /description     -> business/listing pipeline
      pair_address.py        # POST /pair_address    -> business/listing pipeline
      usage.py               # GET /usage_limit/... etc -> services/usage
      listing.py             # POST /listing/submit, GET /listing -> services/listing_store
  core/
    config/
      infra.py (or new mongo mixin)  # MONGO_ENABLED, MONGODB_URL, MONGODB_DATABASE, *_COLLECTION
      ...                            # GMAP_*, BDS_PROJECT_URL, LOCATION_MAPPING_API_URL, model name
```

### Wiring notes
- **Resources:** add `mongo` (+ derived per-collection handles as needed) to
  `ApplicationResources`; open/close via a `MongoAddon` registered like
  `RagAddon` in `app/bootstrap/addons.py`. Legacy handlers resolve it through
  `get_app_resources(request.app)` — **never** an import-time singleton.
- **Router:** `build_api_router` (in `app/api/router.py`) additionally
  `include_router(legacy_router, prefix=settings.API_V1_PREFIX)` (legacy is also
  under `/api/v1`) without `require_principal` (matches today's public posture),
  gated on `MONGO_ENABLED`. Platform `/api/v1/*` (completions) keeps bearer auth.
- **LLM:** handlers receive an `LLMInstance` from
  `build_llm_instance(settings, instance_id="listing", service_name="...")` and
  pass `instance.trace_config(LLMTraceContext(user_id=..., request_id=..., tags=...))`
  into each call. Map langchain usage metadata → legacy `tokens.usage.*`.
- **Errors:** business code raises typed `AppError`s; `api/legacy/response.py`
  translates them into the legacy envelope at the edge only.

## 3. Legacy → new file mapping

| Legacy | New |
|---|---|
| `common/response/response_schema.py`, `response_code.py` | `app/api/legacy/response.py` |
| `common/database/db_mongo.py` (import-time singleton) | `app/modules/platform/mongo/` (lifespan-managed) |
| `common/setting.py` (god object) | fields folded into `app/core/config/*` mixins |
| `common/request.py` (`arequest`, `AsyncHttpClient`) | reuse platform HTTP/resilience (`app/core/resilience.py`) or a small client in `services/` |
| `core/generator/config.py` | `app/modules/business/listing/config.py` |
| `core/generator/schema/*` | `app/modules/business/listing/schemas.py` |
| `core/generator/service/description.py` | `handlers/description.py` + `pipeline.py` |
| `core/generator/service/pair_address.py` | `handlers/pair_address.py` (split into units) |
| `core/generator/service/nearby.py` | `services/nearby.py` |
| `core/generator/service/project.py` | `services/project.py` |
| `core/generator/service/location_mapping.py` | **dropped — not migrated** |
| `core/generator/utils/openai_client.py` | **deleted** — replaced by `ai/llm` |
| `core/limiter/service/usage.py` | `services/usage.py` |
| `core/submit/service/listing.py` | `services/listing_store.py` |
| `core/*/api/v1/*.py` | `app/api/legacy/*.py` (thin) |

## 4. Phased delivery (strangler)

Each phase is independently shippable; the legacy repo keeps serving traffic
until the corresponding phase reaches parity.

- **Phase 0 — Foundations (no behavior change)**
  - Add `motor` optional dep + `MongoAddon` + config fields + resources wiring.
  - Port `response_base`/`CustomResponseCode` envelope into `api/legacy/response.py`.
  - Scaffold empty `business/listing/` (ports, schemas, config enums) — no logic.
  - Confirm + bump FastAPI pin (see §8).
  - **Adopt-for-free platform capabilities — items 1–10, zero parity risk:**
    - *Ambient / observability (response unchanged):* (1) structured logging +
      `request_id` correlation; (2) log redaction (`core/redaction`) — kills the
      legacy debug-logging of raw request bodies; (3) access-log middleware;
      (4) `/healthz` + `/readyz` probes (additive — keep legacy `/health`,
      `/info`, `/`); (5) OTel collector wiring (Langfuse-independent);
      (6) graceful shutdown + lifespan resource management; (7) typed errors
      internally, mapped to the legacy envelope only at the edge.
    - *Tooling / quality (zero runtime impact):* (8) pyright + ruff + pre-commit
      + detect-secrets; (9) pytest-xdist + `conftest`/`factories` to host the
      ported tests; (10) Dockerfile / `docker-compose.local` + Makefile +
      Alembic golden path.
  - **Parked (out of scope per decision — "làm đến 10"):** eval harness (#11)
    and the additive/opt-in set (async tasks, idempotency, cache, resilience
    wrap, audit), plus pagination / RAG / gzip-timeout which would alter output.

- **Phase 1 — Simple domains first**
  - Usage limiter (`/usage_limit/{user_id}`, `/reset`, `/reset_all`, `/day_limit`)
    on the Mongo adapter.
  - Listing submit/get (`/listing/submit`, `/listing`).
  - Integration tests against Mongo (testcontainers or `mongomock`).

- **Phase 2 — `POST /description`**
  - Port enums/schemas/template selection; port nearby/project HTTP services
    (location mapping is dropped — see §1).
  - Build `DescriptionGenerator` on `ai/llm` (langchain), **keeping the legacy
    prompt + regex parsing and pinning model params** for byte-parity;
    `LANGFUSE_ENABLED=false` (deferred). Background listing submit + usage
    increment unchanged.
  - **Golden-output tests**: legacy vs new over a fixture param set (parity gate).

- **Phase 3 — `POST /pair_address`**
  - Port the large generator, refactored into focused units; reuse Phase 2
    services. Golden-output parity gate.

- **Phase 4 — Hardening & upgrades (post-parity)**
  - **Switch the LLM call to structured output** (`with_structured_output`),
    replacing the regex parsing — parity-gated. (Agreed: better design, done
    after the transport swap proves parity.)
  - Durable listing writes via outbox/tasks (replace `BackgroundTasks`).
  - When Langfuse is approved: enable tracing, move prompts to Langfuse prompt
    management, add eval scores.
  - Cut traffic over; decommission `bds-genai-dgl`.

## 5. Parity & verification strategy

- **Golden tests** comparing legacy and new outputs on a frozen fixture set
  (mock LLM + external APIs for determinism; assert structure, contact
  insertion, title casing, address normalization).
- **Shadow run** (optional): mirror a slice of prod params to the new endpoint
  and diff in Langfuse before cutover.
- **Contract tests** asserting the legacy response envelope is byte-identical.
- Preserve Google Maps **`Referer` header** behavior (see `GMAP.md`) — it is
  load-bearing for that API.

## 6. Modernizations applied during the move (the "upgrade")

- Import-time Mongo singletons → lifespan-managed, injected resources.
- Broad `try/except → fail()` → typed `AppError` hierarchy (mapped to the
  legacy envelope only at the edge).
- 1k-line service files → small, single-responsibility modules + ports.
- Raw OpenAI + `tiktoken` → `ai/llm` (langchain); Langfuse tracing/eval
  deferred until approved (OTel interim). Structured output replaces regex
  parsing as a parity-gated fast-follow (Phase 4).
- Python 3.10/Poetry idioms → 3.12/uv; Pydantic 2.7 → 2.11.
- Add the test discipline the platform already follows (unit + integration).

## 7. Risks

| Risk | Mitigation |
|---|---|
| LLM output drift (prompt/model differences) | Golden tests + shadow + Langfuse eval; pin model in config |
| Mongo lifecycle in tests/CI | `mongomock`/testcontainers; addon disabled when `MONGO_ENABLED=false` |
| External APIs (GMaps Referer, BDS) undocumented quirks | Carry headers/timeouts verbatim; contract tests with recorded fixtures |
| Hidden coupling in `common/` | Port only what legacy endpoints actually call; leave the rest behind |
| FastAPI version skew (0.135 → 0.115) | Bump platform pin before porting (§8) |

## 8. Open items to confirm before Phase 0

1. **FastAPI pin** — target is `<0.116`, legacy is `0.135.1`. Bump target pin
   to ≥ legacy before porting? (Recommended.)
2. **External config values** — Google Maps base URL + `Referer`, `BDS_PROJECT_URL`,
   Mongo URI/DB/collection names, chat model id + provider keys. Source from
   legacy `.env` / `common/setting.py`. (Location-mapping config is dropped.)
3. **Listing writes** — keep `BackgroundTasks` initially (parity) and upgrade to
   durable outbox/tasks in Phase 4, or do it in Phase 2? (Recommended: Phase 4.)
4. **Auth posture for legacy routes** — confirm legacy endpoints remain public
   (no bearer), matching today.
