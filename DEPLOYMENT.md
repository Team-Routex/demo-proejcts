# Production deployment guide — Raft Framework

Raft is **production-ready when configured correctly**. This guide covers the settings and infrastructure choices that matter for real deployments.

---

## 1. Checklist (minimum)

| Item | Production setting |
|------|-------------------|
| **Debug** | `RAFT_DEBUG=false` |
| **Secret key** | Random ≥32-byte `RAFT_SECRET_KEY` (never commit) |
| **HTTPS** | TLS at reverse proxy; HSTS enabled automatically when `DEBUG=false` |
| **Sessions** | `RAFT_SESSION_BACKEND=redis` + `RAFT_REDIS_URL` for multi-worker |
| **OpenAPI docs** | `RAFT_OPENAPI_DOCS_ENABLED=false` or private + credentials |
| **Rate limits** | `RAFT_RATE_LIMIT_ENABLED=true` and/or proxy limits (see §5) |
| **Workers** | Multiple uvicorn workers behind a load balancer |
| **Database** | Parameterised queries / ORM — never rely on SQLi middleware alone |

---

## 2. Process model & workers

### Development
```bash
raft runserver --reload
```

### Production (single host)
```bash
raft runserver --no-reload --workers 4 --host 0.0.0.0 --port 8000
```

Or directly with uvicorn:
```bash
uvicorn app:app --host 0.0.0.0 --port 8000 --workers 4 --proxy-headers
```

**Notes:**
- Use **`--proxy-headers`** (uvicorn) when behind nginx/Caddy/ALB so `X-Forwarded-For` / `X-Forwarded-Proto` are trusted for client IP and HTTPS detection.
- Each worker is a separate process — **in-memory sessions and in-memory rate limits do not share state** across workers. Use Redis for both in production.

### Recommended topology

```text
Internet → TLS terminator (nginx / Caddy / Cloudflare)
         → uvicorn workers (Raft app)
         → PostgreSQL / Redis
```

---

## 3. Environment variables (production `.env`)

```env
# Core
RAFT_DEBUG=false
RAFT_SECRET_KEY=<generate-with-secrets-token-urlsafe-32+>
RAFT_ALLOWED_HOSTS=api.example.com,www.example.com
RAFT_HOST=0.0.0.0
RAFT_PORT=8000
RAFT_LOG_LEVEL=warning

# Sessions (required for multi-worker)
RAFT_SESSION_BACKEND=redis
RAFT_REDIS_URL=redis://redis.internal:6379/0
RAFT_REDIS_PREFIX=raft:prod:
RAFT_SESSION_COOKIE_SECURE=true
RAFT_SESSION_COOKIE_HTTPONLY=true
RAFT_SESSION_COOKIE_SAMESITE=Lax
# RAFT_SESSION_COOKIE_DOMAIN=.example.com

# JWT
RAFT_JWT_SECRET=<optional-separate-secret>
RAFT_JWT_ALGORITHM=HS256
RAFT_JWT_EXPIRE_MINUTES=60

# OpenAPI — disable public docs in production
RAFT_OPENAPI_DOCS_ENABLED=false
# Or keep private:
# RAFT_OPENAPI_DOCS_VISIBILITY=private
# RAFT_OPENAPI_DOCS_USERNAME=docs
# RAFT_OPENAPI_DOCS_PASSWORD=<strong-password>

# Rate limiting (app-level; see also reverse proxy)
RAFT_RATE_LIMIT_ENABLED=true
RAFT_RATE_LIMIT_REQUESTS=120
RAFT_RATE_LIMIT_WINDOW_SECONDS=60
RAFT_RATE_LIMIT_BACKEND=redis

# CORS (never use * in production)
RAFT_CORS_ALLOWED_ORIGINS=https://app.example.com
```

Generate a secret key:
```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

---

## 4. Redis

Redis is a **core dependency** but opt-in via config.

| Use case | Setting |
|----------|---------|
| Sessions | `RAFT_SESSION_BACKEND=redis` |
| Rate limiting | `RAFT_RATE_LIMIT_BACKEND=redis` |
| Custom cache/queues | `get_redis()` from `raft.redis` |

Ensure Redis is reachable from every worker, uses persistence appropriate to your SLA, and is not exposed publicly.

---

## 5. Rate limiting

### Built-in middleware (opt-in)

```env
RAFT_RATE_LIMIT_ENABLED=true
RAFT_RATE_LIMIT_REQUESTS=100
RAFT_RATE_LIMIT_WINDOW_SECONDS=60
RAFT_RATE_LIMIT_BACKEND=memory   # or redis for multi-worker
```

Or enable in code:
```python
app = Raft(enable_rate_limit=True)
```

Returns **429 Too Many Requests** with `X-RateLimit-Limit` / `X-RateLimit-Window` headers.

### Reverse-proxy rate limiting (recommended at scale)

For high traffic, prefer **edge or proxy limits** in addition to (or instead of) app middleware:

**nginx example:**
```nginx
limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;

server {
    location / {
        limit_req zone=api burst=20 nodelay;
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

**Cloudflare:** use WAF rate limiting rules on `/api/*`.

App middleware is best for **consistent 429 JSON envelopes**; proxy limits protect the whole stack including static assets and health checks.

---

## 6. HTTPS & HSTS

When `RAFT_DEBUG=false`, Raft's security-headers middleware sets:

```http
Strict-Transport-Security: max-age=63072000; includeSubDomains; preload
```

Requirements:
- TLS must terminate **before** the client reaches your app (or on the app with valid certs).
- Do not enable HSTS on local HTTP-only dev environments — keep `RAFT_DEBUG=true` locally.

---

## 7. OpenAPI / Swagger

| Mode | Config | Behaviour |
|------|--------|-----------|
| Public docs | default dev | `/docs`, `/redoc`, `/openapi.json` |
| Disabled | `RAFT_OPENAPI_DOCS_ENABLED=false` | All three return **404** |
| Private | `VISIBILITY=private` + username/password | HTTP Basic on doc routes |

**Production recommendation:** disable entirely or protect with Basic auth and network ACLs.

---

## 8. Security layers (defence in depth)

Raft includes CORS, CSRF, security headers, JWT auth, and heuristic XSS/SQLi scanners. Treat scanners as **warnings**, not primary controls:

1. **Output encoding** for HTML
2. **Parameterised SQL** / ORM
3. **Strict CSP** for your asset domains
4. **Secrets rotation** and least-privilege DB users
5. **Dependency updates** (`uv lock --upgrade`)

---

## 9. Health checks & `raft check`

Before deploy:
```bash
raft check
```

Use a simple route or `/` for load-balancer health checks. `raft check` validates imports, secrets, optional PostgreSQL/Redis, route counts, and runs pytest when installed.

---

## 10. Example systemd unit

```ini
[Unit]
Description=Raft API
After=network.target redis.service

[Service]
User=raft
WorkingDirectory=/srv/myapp
EnvironmentFile=/srv/myapp/.env
ExecStart=/srv/myapp/.venv/bin/uvicorn app:app --host 127.0.0.1 --port 8000 --workers 4 --proxy-headers
Restart=always

[Install]
WantedBy=multi-user.target
```

Pair with nginx/Caddy on port 443 forwarding to `127.0.0.1:8000`.

---

## 11. Serializers & validation in production

Use first-party serializers for consistent 422 responses:

```python
from raft import Serializer, StrField, validate_body

class CreateUser(Serializer):
    email = StrField(max_length=254)

@app.post("/users/")
async def create_user(request):
    payload = await validate_body(request, CreateUser)
    ...
```

Multipart uploads use **python-multipart** via `await request.form()` / `await request.files()`.

---

## Quick reference

| Concern | Dev | Production |
|---------|-----|------------|
| DEBUG | `true` | `false` |
| Sessions | `memory` | `redis` |
| Rate limit backend | `memory` | `redis` or proxy |
| OpenAPI | enabled | disabled or private |
| Workers | 1 + reload | 2–4+ no reload |
| HSTS | off | on (via DEBUG=false) |
