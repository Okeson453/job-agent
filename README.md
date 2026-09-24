# Job Agent

24/7 autonomous job discovery, matching, and application system.

## Governing principle

The system may describe what the candidate designed or researched. It must never imply deployment or production operation unless that is separately, explicitly verified in the candidate knowledge base.

```
VERIFIED → IMPLEMENTED → PARTIALLY_IMPLEMENTED → DESIGNED → RESEARCH → CONCEPT
```

`can_support(claimed, actual)` enforces this. The Truth/Evidence Engine sits between every LLM output and any external submission.

```bash
python scripts/verify_evidence_rule.py
# PASS: evidence rule holds at rule level and pipeline level
```

## Layout

```
apps/api          FastAPI control surface
apps/worker       Six asyncio loops (discovery → notification)
apps/telegram     Human-in-the-loop bot
src/              Shared library (discovery, jobs, candidate, llm, applications, …)
candidate/        Seed JSON (profile, skills, projects, experience, answers)
tests/unit        Pure-logic tests (no network/DB)
tests/integration Pipeline-level tests
docker/           Compose + three process Dockerfiles
```

## Quick start

```bash
cp .env.example .env   # fill DATABASE_URL, REDIS_URL, TELEGRAM_*, ENCRYPTION_KEY, DEEPSEEK_API_KEY

docker compose -f docker/docker-compose.yml up -d postgres redis
alembic upgrade head

python -m apps.worker.main
uvicorn apps.api.main:app --port 8000
python -m apps.telegram.bot
```

## Tests

```bash
pytest tests/ -q
# 73 passed
```

Critical tests:

- `test_designed_cannot_support_implemented_claim` — evidence hierarchy
- `test_overstated_deployment_claim_blocked` — end-to-end claim → validator
- `test_commands_and_api_both_call_advance` — Telegram `/apply` and API approve share the same path

## Live discovery (verified)

Greenhouse public board API returns live postings. Example: Stripe board ~670 jobs; Discord board scored 0–80 against the candidate profile with all scores in 0–100.

Adapters return source-native records. Normalization and parsing live only in `src/jobs/normalizer` and per-source parsers.

## What still blocks Final Project Sign-Off

Per `job-worker-completion-criteria.md` Section 6:

- [ ] Postgres + Redis running with `alembic upgrade head` applied
- [ ] Full suite including DB-backed integration tests
- [ ] Measured latency targets (Section 4)
- [ ] Secret scan (`gitleaks`) clean
- [ ] Live allowlist block test under Playwright
- [ ] One full E2E run with observed Telegram notification

No release archive until every item above is green.
