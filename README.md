# Autonomous Job Agent

24/7 autonomous job discovery, match scoring, evidence verification, and application pipeline control center.

## Governing Principle

The system may describe what the candidate designed or researched. It must never imply deployment or production operation unless that is separately, explicitly verified in the candidate knowledge base.

```
VERIFIED → IMPLEMENTED → PARTIALLY_IMPLEMENTED → DESIGNED → RESEARCH → CONCEPT
```

`can_support(claimed, actual)` enforces this. The Truth/Evidence Engine sits between every generated claim and external submission.

## Architecture

This project is a React TypeScript SPA running on Vite + Tailwind CSS, featuring:

- **Pipeline & Stats Dashboard**: Real-time supervision funnel tracking applications from `DISCOVERED` to `INTERVIEW`/`OFFER`, daily 24h metrics, and active worker loop health.
- **Jobs & Matcher**: Multi-source job discovery (live Greenhouse public board scanner for Stripe, Discord, etc., plus simulated Lever/RemoteOK feeds), deterministic 8-criteria scoring, and hard filtering.
- **Applications & Approvals**: Complete state machine transition management (`READY` → `SUBMISSION` → `SUBMITTED` → `INTERVIEW` / `OFFER`), cover letter inspector with inline truth validation, and candidate answer review.
- **Truth & Evidence Engine**: Interactive sandbox testing `can_support(claimed, actual)` rules, demonstrating that `DESIGNED` cannot support `IMPLEMENTED` claims, with claim extraction and fact grounding.
- **Candidate Knowledge Base**: Comprehensive profile for Komolafe Eniola Samuel (`eolamide453@gmail.com`), verified evidence registry, projects, skills matrix, and categorized QA answer bank.
- **Telegram Bot Terminal**: Interactive command terminal supporting `/jobs`, `/pending`, `/applied`, `/stats`, `/apply <id>`, `/skip <id>`, `/pause`, `/resume`, `/profile`, `/answers`, and `/preferences`.

## Quick Start

```bash
npm install
npm run dev
```

The dev server listens on `http://0.0.0.0:3000`.

## Build & Verify

```bash
npm run build
```
