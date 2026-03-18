# Stage 0b — Railway Deployment and AWS Migration Path

This file supplements Stage 0. Complete the tooling and environment setup in Stage 0 first, then work through this before writing any application code. Deployment infrastructure should be in place before the first commit to `main`.

---

## Why Railway

- Deploys directly from GitHub — push to `main` and it ships
- Native managed Postgres and Redis with automatic backups
- Environment variables managed in the Railway dashboard (replacing Doppler for MVP)
- Built-in metrics and log viewer
- SSL certificates automatic via Let's Encrypt
- Roughly £15-25/month at MVP scale
- Zero infrastructure management — no VMs to patch, no Nginx to configure

When you outgrow it (thousands of users, complex scaling requirements), you migrate to AWS by pointing the same Docker image at ECS. Nothing in your application changes.

---

## Railway Project Setup

### 1. Create the Railway Project

```bash
# Install Railway CLI
npm install -g @railway/cli

# Login
railway login

# Initialise from your repo root
railway init
```

Create three Railway environments from the dashboard:
- `production` — deploys from `main` branch
- `staging` — deploys from `develop` branch
- `preview` — deploys from pull requests (optional but useful)

### 2. Add Postgres and Redis Services

From the Railway dashboard, click **New Service** → **Database** for each:

- PostgreSQL 16
- Redis 7

Railway automatically injects `DATABASE_URL` and `REDIS_URL` into your service environment. Reference these in your settings rather than defining them manually.

### 3. Service Configuration

```toml
# railway.toml — place at repo root
[build]
builder = "dockerfile"
dockerfilePath = "Dockerfile"

[deploy]
startCommand = "uvicorn backend.app.main:app --host 0.0.0.0 --port $PORT"
healthcheckPath = "/health/ready"
healthcheckTimeout = 30
restartPolicyType = "on_failure"
restartPolicyMaxRetries = 3

[[deploy.environmentVariables]]
# Railway injects PORT automatically — do not hardcode 8000
```

### 4. Environment Variables in Railway Dashboard

Set these in the Railway environment variables panel for each environment. Railway encrypts them at rest.

**Production:**
```
APP_ENV=production
DEBUG=false
SECRET_KEY=<generate: python -c "import secrets; print(secrets.token_hex(32))">
JWT_SECRET_KEY=<generate separately>
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=60
CORS_ALLOWED_ORIGINS=https://yourdomain.com
RESEND_API_KEY=<from Resend dashboard>
EMAIL_FROM_ADDRESS=noreply@yourdomain.com
EMAIL_FROM_NAME=Zima
STRIPE_SECRET_KEY=<from Stripe dashboard>
STRIPE_WEBHOOK_SECRET=<from Stripe webhook config>
STRIPE_PRICE_SHIELD_MONTHLY=<Stripe price ID>
STRIPE_PRICE_PRO_MONTHLY=<Stripe price ID>
HIBP_API_KEY=<from HIBP>
```

Note: `DATABASE_URL` and `REDIS_URL` are injected automatically by Railway — do not add these manually.

**Staging:**
Same as production but with:
```
APP_ENV=staging
DEBUG=false
STRIPE_SECRET_KEY=<Stripe test key — sk_test_...>
CORS_ALLOWED_ORIGINS=https://staging.yourdomain.com
```

Always use Stripe test keys in staging. Never real payment keys outside production.

### 5. Custom Domain

In the Railway dashboard, go to **Settings → Domains** and add your custom domain. Railway handles the SSL certificate automatically. Update your DNS to point at the Railway-provided CNAME.

---

## CI/CD — GitHub Actions Wired to Railway

The Railway deployment happens automatically on push to `main`. The GitHub Actions CI pipeline runs first — Railway only deploys if CI passes. Configure this with Railway's GitHub integration (enabled in the Railway dashboard).

Update the CI pipeline from Stage 0 to add a migration step before deployment:

```yaml
# .github/workflows/ci.yml — updated
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
      - run: uv run bandit -r backend/ -ll  # Security linting

  test:
    runs-on: ubuntu-latest
    needs: lint
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
      JWT_SECRET_KEY: test-secret-not-for-production
      SECRET_KEY: test-secret-not-for-production
      CORS_ALLOWED_ORIGINS: http://localhost:3000
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: pip install uv
      - run: uv sync
      - run: uv run pip-audit  # Zero known vulnerabilities required
      - run: uv run pytest --cov=backend --cov-report=xml --cov-fail-under=70 -v
      - uses: codecov/codecov-action@v4  # Optional but useful

  migrate-and-deploy:
    runs-on: ubuntu-latest
    needs: test
    if: github.ref == 'refs/heads/main' && github.event_name == 'push'
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: pip install uv
      - run: uv sync
      # Run migrations before deploying new code
      # Railway CLI runs the migration against the production database
      - name: Run migrations
        run: railway run --environment production uv run alembic upgrade head
        env:
          RAILWAY_TOKEN: ${{ secrets.RAILWAY_TOKEN }}
      # Railway auto-deploys after CI passes — no explicit deploy step needed
      # The migration step above is the only manual action required
```

Add `RAILWAY_TOKEN` to your GitHub repository secrets. Generate it from the Railway dashboard under **Account Settings → Tokens**.

### Migration Safety Rule

The migration step runs before new application code is deployed. This order is non-negotiable:

```
migrations run (old code still serving) → new code deployed → old code replaced
```

Never reverse this order. New code against an old schema produces unpredictable errors.

---

## AWS Migration Path

When you outgrow Railway, migration to AWS takes roughly a day and requires zero application code changes. Here is the full path:

### What Stays the Same
- Your Docker image — identical, pushed to ECR instead of Railway's registry
- Your environment variables — same names, different values pointing at AWS services
- Your application code — unchanged
- Your CI/CD pipeline — updated to push to ECR and trigger ECS deployment

### What Changes

| Component | Railway | AWS Equivalent |
|---|---|---|
| Application hosting | Railway service | ECS Fargate |
| Container registry | Railway internal | ECR |
| Postgres | Railway managed | RDS PostgreSQL |
| Redis | Railway managed | ElastiCache Redis |
| SSL / load balancing | Railway automatic | Application Load Balancer + ACM |
| Environment variables | Railway dashboard | AWS Secrets Manager |
| Logs | Railway log viewer | CloudWatch Logs |
| Metrics | Railway metrics | CloudWatch Metrics |

### AWS Migration Checklist (When You're Ready)

```
1. Create RDS PostgreSQL 16 instance (db.t3.micro for MVP scale)
2. Create ElastiCache Redis 7 (cache.t3.micro)
3. Create ECR repository
4. Create ECS cluster (Fargate)
5. Create ECS task definition pointing at your Docker image
6. Create ECS service with ALB
7. Request SSL certificate in ACM
8. Update DATABASE_URL and REDIS_URL to point at RDS and ElastiCache
9. Run: pg_dump (Railway) | psql (RDS)  — migrate data
10. Update DNS to point at ALB
11. Verify /health/ready returns 200
12. Update GitHub Actions to push to ECR and deploy to ECS
13. Decommission Railway
```

Total estimated time for the migration: 4-8 hours for someone familiar with AWS. 1-2 days if you're learning as you go.

The containerisation is the portability layer. Everything else is just configuration.

---

## Local Development With Railway Services

You do not need to change your local development workflow. Continue using `docker-compose up` locally for Postgres and Redis. Railway is only used for staging and production deployments.

The only local change is installing the Railway CLI for the migration step:

```bash
npm install -g @railway/cli
railway login
```

---

## Staging Environment Workflow

Before anything goes to production, it goes to staging:

```
feature branch → develop → staging (auto-deploy) → manual testing → main → production (auto-deploy after CI)
```

Staging uses the same Docker image as production. If it works on staging, it will work on production. Test every significant change on staging before merging to `main`.
