# Job Agent

Job discovery and application-preparation pipeline for IT/tech roles.

It finds openings, qualifies them against a written knowledge base, produces a
tailored ATS CV for each one, and delivers everything to Telegram for manual
review. It does not apply to jobs, create accounts, or send email.

## What it does

```
Discovery → Extraction → Dedup → Qualification → Tailored CV → Email draft → Telegram
```

| Stage | What happens | Code |
| --- | --- | --- |
| Discovery | Polls four primary IT/tech sources | `src/discovery/` |
| Extraction | Source-specific parsers → one normalized `Job` | `src/discovery/*/`, `src/jobs/normalizer/` |
| Dedup | Canonical URL + company/title/location fingerprints | `src/jobs/dedup/` |
| Qualification | Deterministic score, then LLM assessment and skill matching | `apps/worker/matching_worker.py`, `apps/worker/llm_worker.py` |
| CV | Model selects KB bullets by ID; PDF + DOCX rendered locally | `src/documents/` |
| Email draft | Only when the posting publishes a recruitment address | `src/documents/email.py` |
| Delivery | Card, CV files, email draft — with per-part retry tracking | `apps/worker/notification_worker.py` |

## Safety guarantees

- No code path submits an application, clicks an apply button, or sends email.
  The pipeline ends at "delivered to Telegram".
- CVs are assembled from knowledge-base bullets selected by ID. The model writes
  only the headline and summary, and those are checked against KB vocabulary
  (`src/documents/grounding.py`). Unknown technologies, numbers, or seniority
  claims cause a fallback to a deterministic summary.
- Scraped pages are untrusted input. Instructions embedded in job descriptions
  are data, never executed.
- The system never authenticates to a source, solves a challenge, or bypasses a
  gate. micro1's gated listing yields no jobs rather than a login attempt.

## Sources

| Source | Method | Notes |
| --- | --- | --- |
| `ioassociates.co.uk` | Playwright | Paginated search results + detail pages |
| `work.turing.com/jobs` | Playwright | Category tabs and "load more"; detail pages require login, so the listing URL is kept |
| `expertwoka.com/opportunities` | HTTP | Server-rendered cards with employer apply links |
| `micro1.ai/experts/opportunities` | Playwright | Public page is gated; returns nothing unless the roles render |

Legacy broad-board adapters (Greenhouse, Lever, LinkedIn, Indeed, Wellfound,
RemoteOK, and others) remain in the registry but are disabled by default. See
`src/discovery/registry.py`.

## Configuration

All policy is environment-driven; see `.env.example` for the full list.

**Matching**

| Variable | Default | Effect |
| --- | --- | --- |
| `MATCH_THRESHOLD` | `40` | Minimum deterministic score to reach LLM qualification |
| `TARGET_SENIORITY` | `mid,senior` | Levels to favour. Score signal only — no role is rejected for its title |
| `JOB_CATEGORIES` | `all` | Restrict categories (`backend,security,data,…`); unclear titles are never dropped by this |
| `PREFERRED_COUNTRIES` | `nigeria` | Geographic score boost, not a block |
| `ALLOW_WORLDWIDE_REMOTE` | `1` | Treat worldwide-remote roles as geographically eligible |
| `REMOTE_MODE` | `remote_only` | `remote_only` rejects office roles; `prefer` allows them at lower score; `any` ignores location |
| `MIN_SALARY` | unset | Fallback compensation floor when the profile has none |

**Scheduling**

| Variable | Default | Effect |
| --- | --- | --- |
| `DISCOVERY_<SOURCE>_POLL_INTERVAL_MINUTES` | per adapter | Poll frequency per source, minimum 1 |
| `DISCOVERY_MAX_NEW_PER_TICK` | `25` | Caps detail fetches per poll |

**Documents and notifications**

| Variable | Default | Effect |
| --- | --- | --- |
| `DOCUMENT_OUTPUT_DIR` | `data/generated_documents` | Where CVs are written; mount a volume in production |
| `CV_INCLUDE_PHONE` | `1` | Include the phone number in generated CVs |
| `APPLICATION_EMAIL_ENABLED` | `1` | Generate email drafts when a recruitment address exists |
| `NOTIFY_MIN_SCORE` | `0` | Suppress cards below this score |
| `NOTIFY_MAX_PER_DAY` | `0` | Daily card cap (`0` = unlimited) |
| `NOTIFY_ATTACHMENTS` | `1` | Upload CV files with the card |
| `NOTIFY_EMAIL_DRAFTS` | `1` | Send the email draft message |

## Candidate knowledge base

`candidate/` is the single source of truth. The CV generator reads identity,
employment, projects, education, certifications, skills, achievements, and
portfolio. Empty or TODO fields are omitted from generated documents rather than
invented; if you want a certifications section or quantified achievements, add
them there.

## Running it

```bash
cp .env.example .env        # DATABASE_URL, REDIS_URL, TELEGRAM_*, ENCRYPTION_KEY, DEEPSEEK_API_KEY
docker compose -f docker/docker-compose.yml up -d postgres redis
alembic upgrade head        # required: migrations 006 and 007 add document/delivery tables

python -m apps.worker.main  # discovery, matching, llm, documents, notification loops
uvicorn apps.api.main:app --port 8000
python -m apps.telegram.bot # /applied, /dismiss, /pending, /stats
```

## Telegram commands

| Command | Effect |
| --- | --- |
| `/pending` | Opportunities delivered and awaiting review |
| `/applied <id>` | Mark as applied manually (after you apply yourself) |
| `/dismiss <id>` | Dismiss an opportunity |
| `/stats` | Pipeline counters |

## Tests

```bash
pytest tests/ -q --ignore=tests/integration/test_live_greenhouse.py
```

Unit tests run without Postgres, Redis, or network. Discovery parsers are
exercised against HTML captured from the live pages (`tests/fixtures/discovery/`),
so selector drift shows up as a failure instead of a silent empty run.

## Layout

```
apps/api          FastAPI control surface
apps/worker       Discovery → matching → LLM → documents → notification loops
apps/telegram     Telegram bot
src/discovery     Source adapters, browser fetch, salary parsing
src/jobs          Normalization, dedup, taxonomy, deterministic matcher
src/documents     KB loader, tailoring, grounding, PDF/DOCX rendering, email drafts
src/llm           DeepSeek client, prompts, evidence validation
src/telegram      Bot API client, delivery tracking
candidate/        Knowledge base (YAML + Markdown)
tests/            Unit and integration tests
docker/           Three process images (worker, api, telegram)
```
