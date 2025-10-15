# 🧠 Copilot Instruction: Python & FastAPI Engineering

You are assisting **Phuc**, a Software AI Engineer building production-grade backend systems using **Python + FastAPI**.

All code you generate must strictly follow the **Zalando RESTful API Guidelines** and the **Python/FastAPI best practices** listed below.

---

## 🧱 1. Coding Principles
- Write **concise, functional, and declarative** Python code.
- Avoid classes unless a stateful/polymorphic design is needed.
- Use the **RORO pattern** (Receive an Object, Return an Object).
- Use **snake_case** for all identifiers (files, functions, variables).
- Prefer iteration, modularization, and composition over duplication.
- Use descriptive variable names (e.g., `is_active`, `has_permission`).
- Always include **type hints**.
- Code must pass **ruff/flake8 lint** and **black formatting**.

## ⚙️ 2. FastAPI & Python Guidelines
- Use `def` for pure logic, `async def` for I/O and HTTP routes.
- Use **Pydantic v2** for request/response validation.
- Use `Annotated[]` + `Depends()` for dependency injection.
- Use **absolute imports** and avoid relative imports.
- Avoid `else` after `return`; prefer **guard clauses**.
- Organize by **feature-based modules** (e.g., `/api/v1/...`).

## 🚦 3. Error Handling
- Validate inputs at route boundaries.
- Use FastAPI’s `HTTPException` or custom exceptions.
- Follow **RFC7807** (`application/problem+json`) for error responses.
- Centralize error handling in middleware.
- Log errors with structured JSON (`request_id`, `path`, `latency`).

## 🧩 4. Dependencies & Stack
Use these core libraries:
```
fastapi
pydantic>=2
uvicorn
sqlalchemy>=2
asyncpg or aiomysql
alembic
redis
httpx
orjson
```

## ⚡️ 5. Performance
- All I/O must be async.
- Avoid blocking calls in the event loop.
- Implement caching (in-memory or Redis) with proper invalidation.
- Use pagination or streaming for large queries.
- Optimize JSON serialization (`orjson`, `ujson`).
- Use async DB sessions (`async_sessionmaker`) with pooling.

## 🔐 6. Security & Reliability
- Sanitize inputs and use parameterized queries.
- Apply CORS, CSP, and HSTS via middleware or proxy.
- Use a **global exception handler** and **rate-limiting** middleware.
- Manage secrets via environment variables or Vault.
- Support clear API versioning (`/v1/...`) and deprecation policy.

## 📊 7. Logging & Monitoring
- Use structured JSON logs (with `request_id`, `trace_id`).
- Expose `/metrics` endpoint for Prometheus.
- Track latency, throughput, and error rates.
- Middleware should handle logging, tracing, and metrics.

## 🧪 8. Testing & CI/CD
- Use **pytest** with async support (`pytest-asyncio`).
- Mock or containerize external deps (DB, Redis, S3) via testcontainers.
- Isolate tests by layer (unit → integration → e2e).
- Enforce lint, typing (`mypy`), and CI pipelines.

## 📘 9. Documentation
- Document all APIs with **OpenAPI 3.x**, include examples and schemas.
- Include auth/security schemes.
- Use explicit versioning (`/v1/resource`).
- Generate SDK clients where relevant.

## 🗂️ 10. Recommended Repo Structure
```
backend/
├── app/
│   ├── admin/api/v1/
│   ├── user/api/v1/
│   └── router.py
├── common/
│   ├── exception/
│   ├── log/
│   ├── response/
│   └── security/
├── core/
│   ├── conf/
│   ├── registrar/
│   └── lifespan.py
├── database/
│   ├── db/
│   └── redis/
├── middleware/
│   ├── logging.py
│   ├── error_handler.py
│   ├── rate_limit.py
│   └── metrics.py
├── utils/
└── tests/
```

## ✅ 11. Response Style
When generating code:
- Show **minimal runnable examples**, not pseudocode.
- Include only **necessary imports**.
- Add **short inline comments** for clarity.
- Avoid placeholders like `foo` or `bar`; use meaningful names.
- If multiple files are implied, show **folder structure + relevant code**.

---

## 🧾 12. Commit Messages — Conventional Commits v1.0.0
**Goal:** All commit messages MUST follow https://www.conventionalcommits.org/en/v1.0.0/

**Format**
```
<type>(optional scope): <subject in imperative>
<blank line>
<body (optional)>
<blank line>
<footer (optional)>
```

**Allowed `<type>`**
- `feat`, `fix`, `docs`, `style`, `refactor`, `perf`, `test`, `build`, `ci`, `chore`, `revert`

**Typical scopes** (suggest first, lowercase)
- `api`, `model`, `data`, `infra`, `deps`, `ci`, `docs`

**Rules**
- Subject ≤ 72 chars, **imperative** (e.g., “add”, “fix”, “refactor”), **no trailing period**.
- Use lowercase type/scope; one space after colon.
- Body explains **what** and **why** (wrap at ~72 chars/line); reference issues in footer.
- For dependency bumps, use `chore(deps): ...`.
- Tests only → `test: ...`; formatting/comments only → `style:` or `chore:`.
- If a breaking API change occurs, add footer:
  ```
  BREAKING CHANGE: <short migration note>
  ```

**Good examples**
- `feat(api): add /predict endpoint for price model`
- `fix(model): correct tensor shape before ONNX export`
- `perf(data): vectorize listing parsing to reduce p95 latency`
- `chore(deps): bump fastapi to 0.115.0`
- `ci: cache pip downloads to speed up workflow`
- `revert: revert "refactor(api): adopt pydantic v2"`

**Bad examples (avoid)**
- `update code`
- `Feat: Add stuff.`
- `fix: this`

**Copilot behavior when generating commits**
- Read staged diff; summarize **impact on user/system**, not file paths.
- Choose **one** clear `type(scope)`; if multiple changes, prioritize the most user-visible.
- Output **only** the commit message text (no code fences, no extra commentary).

---
