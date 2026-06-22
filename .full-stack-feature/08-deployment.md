# 08 - Deployment Runbook

> Covers Docker Compose deployment, env-var verification, health checks,
> rollback, and known gaps after the v2 refactoring.

---

## 1. Pre-Deployment Verification Checklist

Before deploying, confirm these items pass:

| #  | Check                                       | Status | Notes                                             |
|----|---------------------------------------------|--------|---------------------------------------------------|
| 1  | `docker-compose.yml` defines 4 services      | PASS   | redis, postgres, backend, frontend                |
| 2  | Backend `Dockerfile` exists                  | PASS   | Root `Dockerfile`, Python 3.11-slim, multi-stage  |
| 3  | Frontend `frontend/Dockerfile` exists        | PASS   | Node 20 builder + Nginx alpine                    |
| 4  | `nginx.conf` proxies `/api/` to backend      | PASS   | SSE-aware (proxy_buffering off)                   |
| 5  | `pydantic-settings` in requirements.txt      | PASS   | `pydantic-settings>=2.0.0` on line 41             |
| 6  | `.env.example` covers all AppSettings fields | WARN   | See Section 3 for missing keys                    |
| 7  | Health endpoint `/health` responds           | PASS   | Returns `{"status": "ok"}`                        |
| 8  | `.dockerignore` excludes .env and secrets    | PASS   | `.env`, `.env.local`, `models/` all excluded      |
| 9  | Auth config (JWT/CORS) in AppSettings        | FAIL   | Read via `os.getenv()`, not Pydantic; see Section 4 |
| 10 | No DB migrations needed                      | PASS   | Schema unchanged; pgvector tables auto-created    |

---

## 2. Docker Compose Deployment

### Services

| Service    | Image                          | Port (default) | Purpose                      |
|------------|--------------------------------|----------------|------------------------------|
| `redis`    | `redis:7-alpine`               | 6379           | L2 cache (optional)          |
| `postgres` | `pgvector/pgvector:pg16`       | 5432           | Vector store (optional)      |
| `backend`  | Custom (`Dockerfile`)          | 8000           | FastAPI RAG API              |
| `frontend` | Custom (`frontend/Dockerfile`) | 80             | Nginx static + reverse proxy |

### Startup dependency chain

```
redis (healthy)  -->  backend (healthy)  -->  frontend
postgres (healthy) -^
```

Both `redis` and `postgres` must pass health checks before `backend` starts.
`frontend` waits for `backend` to be healthy.

### Quick start

```bash
# 1. Create .env from template
cp .env.example .env

# 2. Edit .env -- at minimum set these:
#    MIMO_API_KEY       (required -- LLM calls fail without it)
#    JWT_SECRET_KEY     (required for auth -- generate with command below)
#    CORS_ORIGINS       (required for production -- set to your domain)

# Generate a secure JWT secret:
python -c "import secrets; print(secrets.token_urlsafe(64))"

# 3. Build and start
docker compose up -d --build

# 4. Wait for health checks (backend has 30s start_period)
sleep 35

# 5. Verify
curl http://localhost:8000/health
# Expected: {"status":"ok"}

# 6. Open UI
# http://localhost
```

### Stopping

```bash
docker compose down           # stop containers, keep volumes
docker compose down -v        # stop AND delete volumes (data loss!)
```

---

## 3. Environment Variable Setup (.env)

### Required (must set before deployment)

| Variable        | Where read             | Why required                              |
|-----------------|------------------------|-------------------------------------------|
| `MIMO_API_KEY`  | AppSettings            | All LLM/embedding calls fail without it   |
| `JWT_SECRET_KEY`| `os.getenv()` in auth  | Auth tokens use this; default is insecure |
| `CORS_ORIGINS`  | `os.getenv()` in main  | Frontend cannot reach API without it      |

### Important optional

| Variable             | Default           | When to change                            |
|----------------------|-------------------|-------------------------------------------|
| `VECTOR_STORE_PROVIDER` | `chroma`       | Set to `pgvector` to use PostgreSQL       |
| `EMBEDDING_PROVIDER`    | `sentence-transformer` | Set to `siliconflow` for cloud inference |
| `RERANK_STRATEGY`       | `cohere`        | Change if not using Cohere                |
| `USE_REDIS`             | `false`         | Set `true` to enable L2 Redis cache       |
| `USE_VLM`               | `false`         | Set `true` for image/chart understanding  |
| `DEV_RELOAD`            | `false`         | Set `true` in development only            |

### Keys present in .env.example but missing from AppSettings

These are read via `os.getenv()` directly in code (not validated by Pydantic):

| Variable              | Read in                  | Default                          |
|-----------------------|--------------------------|----------------------------------|
| `JWT_SECRET_KEY`      | `backend/core/auth.py`   | `change-me-to-a-random-secret`   |
| `JWT_EXPIRE_HOURS`    | `backend/core/auth.py`   | `24`                             |
| `ALLOW_REGISTRATION`  | `backend/core/auth.py`   | `true`                           |
| `CORS_ORIGINS`        | `backend/main.py`        | `http://localhost:5173,...`       |
| `DEV_RELOAD`          | `backend/main.py`        | `false`                          |

**Impact**: These keys work at runtime but have no Pydantic validation or
type coercion. A future step should add them to `AppSettings`.

### Keys in AppSettings but missing from .env.example

These have sensible defaults in code but should be documented for operators:

| Variable                         | Type  | Default | Purpose                                |
|----------------------------------|-------|---------|----------------------------------------|
| `CHUNK_SIZE`                     | int   | 512     | Characters per text chunk              |
| `CHUNK_OVERLAP`                  | int   | 50      | Overlap between chunks                 |
| `TOP_K`                          | int   | 5       | Vector search result count             |
| `SIMILARITY_THRESHOLD`           | float | 0.5     | Min cosine similarity to keep          |
| `MAX_HISTORY_TURNS`              | int   | 5       | Conversation turns sent to LLM         |
| `BM25_TOP_K`                     | int   | 6       | BM25 keyword retrieval top-K           |
| `RRF_K` / `RRF_WEIGHT_*`        | mixed | 60/0.7  | Reciprocal Rank Fusion params          |
| `SEMANTIC_CHUNK_*`               | mixed | varies  | Semantic chunking tuning               |
| `CHUNKING_STRATEGY`              | str   | semantic| `semantic`/`fixed_size`/`recursive`/`parent_child` |
| `RERANK_GATE_THRESHOLD`          | float | 0.3     | Min rerank score to keep               |
| `CITATION_VERIFY_ENABLED`        | bool  | True    | Citation verification on/off           |
| `CITATION_CONFIDENCE_THRESHOLD`  | float | 0.5     | Min citation confidence                |
| `RETRIEVAL_REFETCH_ENABLED`      | bool  | True    | Refetch on low confidence              |
| `RETRIEVAL_CONFIDENCE_THRESHOLD` | float | 0.5     | Refetch trigger threshold              |
| `SELF_RAG_ENABLED`               | bool  | True    | Self-RAG reflection step               |
| `PC_CHILD_SENTENCES`             | int   | 3       | Parent-child chunking param            |
| `PC_PARENT_GROUPS`               | int   | 4       | Parent-child chunking param            |
| `PC_OVERLAP_SENTENCES`           | int   | 1       | Parent-child chunking param            |

### Default value mismatch

| Variable    | AppSettings default | .env.example value | Impact                                    |
|-------------|--------------------|--------------------|-------------------------------------------|
| `USE_VLM`   | `False`            | `true`             | VLM disabled if .env not created          |
| `RERANK_TOP_K` | `40`           | `20`               | Fewer results if .env not created         |

---

## 4. Known Issues to Fix Before Production

### Issue 1: Auth config not in AppSettings

`JWT_SECRET_KEY`, `JWT_EXPIRE_HOURS`, `ALLOW_REGISTRATION`, and
`CORS_ORIGINS` are read via raw `os.getenv()` instead of through the
unified `AppSettings`. This means:
- No Pydantic type validation
- No single source of truth for all config
- These fields don't appear when introspecting `config`

**Fix**: Add these fields to `AppSettings` in `backend/core/config.py` and
update `auth.py` / `main.py` to read from `config` instead of `os.getenv()`.

### Issue 2: Dockerfile CMD uses wrong module path

The root `Dockerfile` runs:
```
CMD ["uvicorn", "backend.main:app", ...]
```

But `main.py` adds `backend_dir` to `sys.path` and contains its own
`uvicorn.run("main:app", ...)`. The Dockerfile CMD is correct for the
container context (PYTHONPATH=/app:/app/backend), but verify this works
after any further changes to import paths.

### Issue 3: Metrics port not exposed

`METRICS_PORT=9090` is configured but the `docker-compose.yml` does not
expose port 9090 from the backend container. If Prometheus scraping is
needed, add:
```yaml
ports:
  - "${BACKEND_PORT:-8000}:8000"
  - "${METRICS_PORT:-9090}:9090"
```

---

## 5. Health Check Verification

### Endpoints

| Endpoint      | Method | Auth | Response              | Purpose               |
|---------------|--------|------|-----------------------|-----------------------|
| `/health`     | GET    | No   | `{"status": "ok"}`   | Docker / LB check     |
| `/`           | GET    | No   | `{"message": "..."}` | Liveness              |
| `/api/auth/me`| GET    | Yes  | User profile          | Auth subsystem check  |

### Docker health checks (pre-configured)

```
Redis:      redis-cli ping           (10s interval, 3 retries)
PostgreSQL: pg_isready -U rag_user   (10s interval, 5 retries, 10s start)
Backend:    python urllib /health    (30s interval, 3 retries, 30s start)
```

### Manual verification after deploy

```bash
# Check all containers are healthy
docker compose ps

# Check backend logs for startup errors
docker compose logs backend --tail=50

# Test chat endpoint (requires auth token)
TOKEN=$(curl -s -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin"}' | python -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/documents
```

---

## 6. Rollback Steps

### Option A: Roll back code only (keep data)

```bash
# 1. Note the current commit
CURRENT=$(git rev-parse HEAD)

# 2. Check out the previous known-good commit
git log --oneline -5   # find the commit before refactoring
git checkout <previous-commit>

# 3. Rebuild and restart
docker compose down
docker compose up -d --build

# 4. Verify
curl http://localhost:8000/health
```

### Option B: Full restore (code + env)

```bash
# 1. Restore backed-up .env
cp .env.backup .env

# 2. Revert git
git revert HEAD
# or: git checkout <known-good-tag>

# 3. Rebuild
docker compose down
docker compose up -d --build

# 4. Verify
docker compose ps
curl http://localhost:8000/health
```

### Data safety

- **No data loss on rollback.** All persistent data lives in:
  - Docker volumes: `multimodal_rag_redis_data`, `multimodal_rag_postgres_data`, `multimodal_rag_chroma_data`
  - Host bind mounts: `./models/`, `./data/`
- These are untouched by `git checkout` or `docker compose down` (without `-v`).
- Redis and PostgreSQL volumes can remain running during rollback since
  their schemas did not change.
- **Only run `docker compose down -v` if you intentionally want to wipe data.**

---

## 7. What Changed in the Refactoring

### Structural changes (no deployment impact)

| Component         | Before                          | After                                    |
|-------------------|---------------------------------|------------------------------------------|
| Config            | `config.py` + `advanced_config.py` | Single `AppSettings` (pydantic-settings) |
| RAG engine        | Monolithic `RAGEngine`          | Facade over 3 services + `InfraBundle`   |
| DI pattern        | Module-level singletons         | FastAPI lifespan + `Depends()`           |
| Frontend stores   | One Pinia store                 | 5 focused stores (auth, chat, conversation, document, toast) |
| Component layout  | Flat `components/`              | `features/{chat,documents,auth}/`        |
| API routes        | Single `chat.py` router        | Split into `chat.py`, `documents.py`, `conversations.py`, `auth.py` |

### Deployment-relevant changes

| Change                              | Action needed                          |
|-------------------------------------|----------------------------------------|
| New dependency: `pydantic-settings` | Already in `requirements.txt`; Docker rebuild picks it up |
| `advanced_config.py` deleted        | Alias in `config.py` keeps backward compat; no action |
| `init_advanced_config()` is no-op   | Safe to remove calls, but not required |
| New API routes under `/api/auth/`   | Nginx already proxies `/api/` prefix   |
| New API routes `/api/conversations/`| Nginx already proxies `/api/` prefix   |

### What did NOT change

- `docker-compose.yml` -- no edits needed
- `Dockerfile` / `frontend/Dockerfile` -- no edits needed
- `nginx.conf` -- no edits needed (already proxies all `/api/` traffic)
- `.env.example` -- still valid (but see Section 3 for gaps)
- No database schema changes
- No volume mount changes

---

## 8. Production Hardening Checklist

Before going live beyond local/development:

- [ ] Set a real `JWT_SECRET_KEY` (64+ random bytes)
- [ ] Set `CORS_ORIGINS` to your actual domain(s)
- [ ] Set `ALLOW_REGISTRATION=false` after creating admin account
- [ ] Set `VECTOR_STORE_PROVIDER=pgvector` if using PostgreSQL
- [ ] Set `USE_REDIS=true` and verify Redis connection
- [ ] Expose `METRICS_PORT` if using Prometheus
- [ ] Set `LOG_LEVEL=WARNING` for production
- [ ] Review `RERANK_TOP_K` (40 in code vs 20 in .env.example)
- [ ] Add the missing auth keys to `AppSettings` (see Issue 1)
- [ ] Set up TLS termination (reverse proxy or load balancer in front of Nginx)
