---

### Enhanced Python + FastAPI Scalable API Development Instructions

---

### Key Principles

* Write concise, technical Python examples.
* Use functional, declarative style; avoid classes unless necessary.
* Prefer iteration and modularization over duplication.
* Use descriptive, auxiliary-verb variable names (`is_active`, `has_permission`).
* Use `snake_case` for files and folders.
* Favor named exports for routers/utilities.
* Follow the RORO pattern (Receive an Object, Return an Object).

---

### Python/FastAPI Guidelines

* Use `def` for pure functions, `async def` for I/O.
* Use type hints and Pydantic v2 for validation.
* Use `Annotated[]` for dependency injection.
* Use absolute imports.
* Write concise conditionals; omit unnecessary braces and `else` after returns.

---

### Error Handling

* Use guard clauses and handle errors early.
* Use FastAPI’s `HTTPException` and custom exceptions.
* Log errors properly and normalize error responses.

---

### Dependencies

* FastAPI, Pydantic v2, SQLAlchemy 2.0 (optional), async DB clients (`asyncpg`, `aiomysql`), Uvicorn, Alembic, httpx.

---

### FastAPI Patterns

* Use clear route decorators with return types.
* Prefer lifespan context managers over startup/shutdown events.
* Use `Depends()` and `Annotated[]`.
* Middleware for logging, error monitoring, tracing, metrics, and rate limiting.
* Separate domain logic from routes.

---

### Performance

* Use async for all I/O.
* Avoid blocking calls.
* Implement caching (in-memory, Redis) with proper invalidation and cache key design.
* Use streaming responses and paginate large queries.
* Optimize JSON serialization with `orjson` or `ujson`.

---

### Security & Reliability

* Sanitize inputs and use parameterized queries or ORM.
* Validate inputs via Pydantic at route boundaries.
* Use a global exception handler.
* Implement security headers (CORS, CSP, HSTS) via middleware or proxy.
* Use rate limiting/throttling middleware or external gateway.
* Manage secrets securely (env vars, Vault).
* Support API versioning with clear deprecation and backward compatibility policy.

---

### Logging & Monitoring

* Use structured (JSON) logging with correlation/request IDs for traceability.
* Expose metrics endpoint (e.g., `/metrics`) for Prometheus integration.
* Track latency, throughput, error rates.

---

### Testing & CI/CD

* Use pytest with isolated tests per layer.

### Documentation

* Document APIs fully with OpenAPI (request/response models, examples, security schemes).
* Version APIs clearly (e.g., `/v1/users`).
* Generate or maintain API client libraries if relevant.

---

### Repo Structure Example

```plaintext
backend/
├── app/                   # Feature-based modules with versioned API routers
│   ├── admin/api/v1/
│   ├── task/api/v1/
│   └── router.py          # Central router aggregating all feature routers
├── common/                # Shared resources (constants, exceptions, responses, security)
│   ├── log/
│   ├── exception/
│   ├── response/
│   └── security/
├── core/                  # Core setup: configuration, DI, app registration
│   ├── conf/
│   ├── conf_path/
│   └── registrar/
├── database/              # Database and cache layers
│   ├── db/                # ORM models, sessions, migrations
│   └── redis/             # Redis client and caching utilities
├── middleware/            # Custom FastAPI middleware (logging, error handling, rate limiting, etc.)
├── utils/                 # Generic helpers and utility functions
└── tests/                 # Unit and integration tests
```

---

### Naming & Style Conventions

* Use `snake_case` throughout.
* Group related files per feature/domain.
* Use `__init__.py` to define packages.

