← [[MVP Master|Stage Progress]]

# Stage 0 — Environment, Tooling, and AI Context

**Exit condition:** CI is green. Pre-commit hooks pass. Import direction checker runs. `docker-compose up` starts Postgres and Redis successfully. `.env` is populated from `.env.example`. The project imports cleanly with zero errors.

---

## 0.1 Python and Runtime Pinning

Pin Python 3.12 at the repo root. Use `pyenv` to manage the version locally and in CI.

```
# .python-version
3.12.3
```

All contributors and all CI runners must use this version without exception.

---

## 0.2 Dependencies

Use `uv` as the package manager. Do not use pip or Poetry.

**Celery is explicitly excluded from the MVP.** Background tasks are handled by FastAPI `BackgroundTasks` throughout the MVP. Celery is the correct long-term choice for job persistence, retries, and monitoring, and should be introduced as a migration after MVP when scan volume justifies it. Having both in the dependency tree creates confusion about which is authoritative.

```toml
# pyproject.toml
[project]
name = "zima"
version = "0.1.0"
requires-python = ">=3.12"

[project.dependencies]
fastapi = ">=0.111.0"
uvicorn = {extras = ["standard"], version = ">=0.29.0"}
sqlalchemy = {extras = ["asyncio"], version = ">=2.0.0"}
alembic = ">=1.13.0"
asyncpg = ">=0.29.0"
aiosqlite = ">=0.20.0"
pydantic = ">=2.7.0"
pydantic-settings = ">=2.2.0"
httpx = ">=0.27.0"
python-jose = {extras = ["cryptography"], version = ">=3.3.0"}
redis = {extras = ["hiredis"], version = ">=5.0.0"}
tenacity = ">=8.3.0"
structlog = ">=24.1.0"
python-dotenv = ">=1.0.0"
slowapi = ">=0.1.9"
secure = ">=0.3.0"
resend = ">=2.0.0"
stripe = ">=9.0.0"
pyyaml = ">=6.0.1"

[project.optional-dependencies]
dev = [
    "pytest>=8.0.0",
    "pytest-asyncio>=0.23.0",
    "pytest-cov>=5.0.0",
    "httpx>=0.27.0",
    "factory-boy>=3.3.0",
    "respx>=0.21.0",
    "ruff>=0.4.0",
    "mypy>=1.10.0",
    "pre-commit>=3.7.0",
]

[tool.ruff]
target-version = "py312"
line-length = 88

[tool.ruff.lint]
select = ["E", "F", "I", "N", "UP", "ANN", "S", "B", "A", "C4", "T20"]
ignore = ["ANN101", "ANN102"]

[tool.mypy]
python_version = "3.12"
strict = true
ignore_missing_imports = false

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests", "backend"]
```

---

## 0.3 Pre-commit Hooks

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.4.0
    hooks:
      - id: ruff
        args: [--fix]
      - id: ruff-format

  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.6.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-toml
      - id: check-merge-conflict
      - id: no-commit-to-branch
        args: [--branch, main]
      - id: detect-private-key

  - repo: local
    hooks:
      - id: check-imports
        name: Enforce dependency direction
        entry: python scripts/check_imports.py
        language: python
        pass_filenames: false
      - id: no-env-files
        name: Prevent .env commit
        entry: bash -c 'git diff --cached --name-only | grep -q "^\.env$" && echo ".env must not be committed" && exit 1 || exit 0'
        language: system
        pass_filenames: false
```

Note `detect-private-key` and the `.env` guard — both prevent accidental credential commits, which is a real risk when working with AI-assisted development where generated code sometimes includes placeholder secrets.

---

## 0.4 Import Direction Checker

Write this before any application code. It is your most important automated guardrail. Run it in pre-commit and in CI.

```python
# scripts/check_imports.py
"""
Enforces the one-directional dependency rule:
core → db → auth → assets → signals → providers → modules
     → correlation → scoring → remediation → automation → api

Any violation exits non-zero and fails the build.
"""
import ast
import sys
from pathlib import Path

FORBIDDEN_UPWARD_IMPORTS: dict[str, list[str]] = {
    "providers": ["modules", "correlation", "scoring", "remediation", "automation", "api"],
    "modules":   ["correlation", "scoring", "remediation", "automation", "api"],
    "correlation": ["scoring", "remediation", "automation", "api"],
    "scoring":   ["remediation", "automation", "api"],
    "remediation": ["automation", "api"],
    "automation": ["api"],
}

BASE = Path("backend/app")
violations: list[str] = []

for source_layer, forbidden_layers in FORBIDDEN_UPWARD_IMPORTS.items():
    layer_path = BASE / source_layer
    if not layer_path.exists():
        continue
    for py_file in layer_path.rglob("*.py"):
        tree = ast.parse(py_file.read_text())
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                for forbidden in forbidden_layers:
                    if f"backend.app.{forbidden}" in node.module:
                        violations.append(
                            f"VIOLATION in {py_file}: "
                            f"layer '{source_layer}' must not import from '{forbidden}'"
                        )

if violations:
    print("\n".join(violations))
    sys.exit(1)

print("Import direction check passed.")
sys.exit(0)
```

---

## 0.5 Docker Setup

Backing services run in Docker. Application code runs locally for fast iteration.

```yaml
# docker-compose.yml
services:
  postgres:
    image: postgres:16-alpine
    environment:
      POSTGRES_DB: zima_dev
      POSTGRES_USER: zima
      POSTGRES_PASSWORD: zima_dev_password
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U zima"]
      interval: 5s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 5s
      retries: 5

volumes:
  postgres_data:
```

```dockerfile
# Dockerfile
FROM python:3.12-slim

WORKDIR /app

RUN pip install uv

COPY pyproject.toml .
RUN uv sync --no-dev

COPY . .

EXPOSE 8000
CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

## 0.6 Environment Configuration

```bash
# .env.example

# Application
APP_ENV=development
DEBUG=true

# Security — generate with: python -c "import secrets; print(secrets.token_hex(32))"
SECRET_KEY=REPLACE_WITH_SECURE_RANDOM_STRING

# Database
DATABASE_URL=postgresql+asyncpg://zima:zima_dev_password@localhost:5432/zima_dev
DATABASE_URL_SYNC=postgresql+psycopg2://zima:zima_dev_password@localhost:5432/zima_dev

# Redis
REDIS_URL=redis://localhost:6379/0

# JWT
JWT_SECRET_KEY=REPLACE_WITH_SECURE_RANDOM_STRING
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=60

# CORS — comma-separated list of allowed origins
# Development: http://localhost:3000
# Production: https://yourdomain.com
CORS_ALLOWED_ORIGINS=http://localhost:3000

# Email (Resend)
RESEND_API_KEY=
EMAIL_FROM_ADDRESS=noreply@yourdomain.com
EMAIL_FROM_NAME=Zima

# Stripe
STRIPE_SECRET_KEY=
STRIPE_WEBHOOK_SECRET=
STRIPE_PRICE_SHIELD_MONTHLY=
STRIPE_PRICE_PRO_MONTHLY=

# Providers
HIBP_API_KEY=

# Tier
DEFAULT_TIER=core
```

Add `.env` to `.gitignore` immediately. The `detect-private-key` pre-commit hook and the `.env` guard are the belt-and-braces protection here.

For production, use **Doppler** to manage secrets. It replaces environment variables entirely, integrates with any deployment platform, and provides audit logs of who accessed which secret and when. Free at small scale.

---

## 0.7 CI/CD Pipeline

```yaml
# .github/workflows/ci.yml
name: CI

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main, develop]

jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: pip install uv
      - run: uv sync
      - run: uv run ruff check .
      - run: uv run ruff format --check .
      - run: uv run mypy backend/
      - run: uv run python scripts/check_imports.py

  test:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:16-alpine
        env:
          POSTGRES_DB: zima_test
          POSTGRES_USER: zima
          POSTGRES_PASSWORD: zima_test
        ports: ["5432:5432"]
        options: >-
          --health-cmd pg_isready
          --health-interval 5s
          --health-timeout 5s
          --health-retries 5
      redis:
        image: redis:7-alpine
        ports: ["6379:6379"]
    env:
      APP_ENV: testing
      DATABASE_URL: postgresql+asyncpg://zima:zima_test@localhost:5432/zima_test
      DATABASE_URL_SYNC: postgresql+psycopg2://zima:zima_test@localhost:5432/zima_test
      REDIS_URL: redis://localhost:6379/0
      JWT_SECRET_KEY: test-secret-key-not-for-production
      SECRET_KEY: test-secret-key-not-for-production
      CORS_ALLOWED_ORIGINS: http://localhost:3000
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: pip install uv
      - run: uv sync
      - run: uv run pytest --cov=backend --cov-report=xml -v
```

---

## 0.8 CLAUDE.md — AI Context File

Claude Code reads this file automatically at the start of every session. Keep it current as the project evolves. This file is as important as any source file.

```markdown
# Zima — AI Development Context

## What This Project Is
Zima is a modular cybersecurity platform. Architecture documented in docs/.
Target: personal and small-business security monitoring.
Revenue model: freemium SaaS, target £500/month.

## Authentication Model
Passwordless OTP only. No passwords stored anywhere.
User enters email → receives 6-digit code → submits code → session created.
The sign-in email is automatically a verified, scannable asset.
Users can only trigger scans against emails they have verified ownership of.

## The One Rule You Must Never Violate
Providers answer HOW to get data.
Modules answer WHAT the data means.
Never mix these responsibilities.

## Dependency Direction (enforced by CI — do not break)
core → db → auth → assets → signals → providers → modules
     → correlation → scoring → remediation → automation → api

Lower layers NEVER import higher layers.
If you need data from a higher layer, the responsibility is in the wrong place.
Stop and ask before restructuring.

## What Providers Must Never Do
- Assign severity or confidence
- Emit Zima signals
- Know about tiers
- Produce user-facing messages
- Implement remediation

## What Modules Must Never Do
- Manage authentication or raw HTTP
- Call other modules directly
- Import from correlation, scoring, remediation, or automation

## Background Tasks
Use FastAPI BackgroundTasks for MVP.
Every background task MUST create its own database session.
Never pass a request-scoped session into a background task — it will be closed.
Pattern:
  async def my_task(user_id: uuid.UUID) -> None:
      async with AsyncSessionLocal() as session:
          repo = MyRepository(session)
          await repo.do_work()

## Database Rules
- All DB access through repository classes in db/repositories/
- No raw queries anywhere else
- All models inherit from Base and TimestampMixin
- Soft-delete users with deleted_at — hard-delete their personal data on GDPR erasure request

## Scan Constraint
Users may only scan assets where is_verified=True.
is_verified is only set to True by the auth service after OTP verification.
Never set is_verified=True directly in application logic outside auth/service.py.

## Celery
NOT used in the MVP. Do not add Celery. Use BackgroundTasks.
Note this in any task implementation for future migration.

## Code Style
- Python 3.12, strict Mypy, Ruff
- Async throughout — no sync DB calls
- Pydantic v2 for all schemas
- SQLAlchemy 2.0 async style
- SecretStr for all credentials in Settings

## When You Are Unsure
Stop and ask. Reference docs/section-02-design-principles.md first.
Do not make architectural assumptions — the cost of unpicking them is high.
```
