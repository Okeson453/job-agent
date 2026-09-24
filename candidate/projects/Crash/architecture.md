# Crash (CrashWave) — Architecture (per repo README)

```
Telegram Bot / Mini App
        |
        v
PLAYER INTERFACES — React Mini App (Home / Play / Wallet / History / Profile)
        |
        v
CONTROL PLANE — Fastify API: Authentication, RBAC, Game Services,
                Betting, Wallet, Admin, Audit
        |                              |
        v                              v
  PostgreSQL + TimescaleDB       Redis (coordination, cache, locks)
        |
        v
  Real-Time Layer — WebSocket/WS
        |
        v
  Game / Browser Integration
```

**Explicit design stance:** the Control Plane is the sole authority for
identity, authorization, game state, betting, balances, configuration,
and admin operations — *"the frontend, including the Telegram Mini
App, is treated as an interface, not a security boundary."* Client-
provided role information is never treated as authoritative; RBAC is
resolved server-side on every request.

## Security chain (admin operations)
`Telegram initData -> signature verification -> identity resolution ->
tenant resolution -> RBAC -> admin API authorization -> operation ->
audit event`

## Repository structure (`src/`, abbreviated)
`analytics/ api/ app/ background-workers/ betting/ browser/ capital/
config/ core/ decision/ execution/ game/ ledger/ mini-app/ network/
notifications/ observability/ opportunity/ persistence/ platform/
prediction/ protocol/ risk/ risk-engine/ security/`

Notably, `src/` also contains `prediction/`, `risk-engine/`,
`opportunity/`, `decision/`, and `execution/` directories — naming that
overlaps with a trading/betting-signal system, not just a game
platform. <!-- TODO: worth clarifying what these specifically do; the
README doesn't expand on them beyond the directory list. -->
