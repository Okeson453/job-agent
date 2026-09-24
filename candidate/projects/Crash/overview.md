# Crash — Overview

**Source of truth: https://github.com/Okeson453/Crash (README,
inspected directly)** *This replaces the earlier memory-only version
of this file.*

> **Naming flag, worth resolving directly:** this repository's own
> README and GitHub "About" text identify the project as **CrashWave**
> — *"an end-to-end real-time crash gaming platform... secure backend
> Control Plane, real-time game engine, wallet and betting
> infrastructure... Telegram Mini App."* This is a platform-operator
> system (you'd be running the house), not the player-side Playwright
> automation bot with anti-detection stealth that memory previously
> described under "Crash" / "crash-automation" (700-unit stakes,
> 1.30x cash-out, evading BC.Game's own bot detection). **Those are two
> structurally different things** — one plays a game as a bettor, this
> one operates a crash-game platform for others to bet on. Per your
> instruction to treat the actual repo as source of truth, this file
> now describes what's actually in `github.com/Okeson453/Crash`
> (CrashWave). If the Playwright-stealth bot is a separate, still-live
> project, it isn't at this URL — point me at its repo and I'll
> scaffold it correctly rather than guessing.

**CrashWave — what it actually is:** a full-stack, real-time crash
gaming and platform-operations system. A backend Control Plane
(Fastify) owns identity, authorization, game state, betting, and
balances; a React/Telegram Mini App and a standalone Next.js admin
dashboard both consume that same Control Plane rather than duplicating
business logic; PostgreSQL (+ TimescaleDB-compatible schema) and Redis
provide persistence and coordination; real-time delivery runs over
WebSockets/Socket.IO.
