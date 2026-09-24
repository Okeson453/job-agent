# TestingEngine — Overview

**Source of truth: https://github.com/Okeson453/TestingEngine (README,
inspected directly — repo is publicly described as "BcTracker project")**
*This replaces the earlier memory-only version of this file.*

**BcTracker** — an autonomous live prediction engine for BC.Game Crash
rounds, targeting a 1.30x cash-out threshold. A long-lived **Railway
worker** ingests live crash events, generates round-ahead (N+1)
predictions, validates outcomes after the fact, and delivers signals
via Telegram. A separate **Vercel dashboard** is strictly read-only
against the same PostgreSQL database — it never polls BC.Game or
generates predictions itself.

Public dashboard: https://testing-engine.vercel.app
Status per repo license note: *"Private application workspace... the
production worker is the source of truth for predictions; the
dashboard only observes."*
