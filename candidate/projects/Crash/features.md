# Crash (CrashWave) — Key Features

**Player platform:** crash game interface, real-time multiplier
updates, bet placement, cash-out, bet history, balance display,
profile/settings, notifications, reconnection/offline-recovery
handling, full Telegram Mini App integration (MainButton, reactive
theme).

**Platform services:** JWT access/refresh auth with revocation,
Telegram Mini App auth, RBAC, tenant-aware architecture, audit logging,
rate limiting, idempotency handling, risk controls, balance
reconciliation, game-state management.

**Administration:** available from both the standalone dashboard and
the Mini App (same Control Plane APIs, no duplicated backend) —
Dashboard, Users, Instances/Engines, Sessions, Billing, System Health,
Configuration, Audit Logs, Operations.

**Betting/wallet safeguards** (`src/betting/`): idempotency, risk
evaluation, confirmation flow, cash-out, execution-mode gating, balance
consistency, reconciliation — the Mini App itself validates balance
state and generates idempotency IDs before sensitive operations.

**Operational safety principles (explicitly named in the README):**
Safety Over Continuity (stop or observe-only when state is uncertain,
never guess), Deterministic State, Idempotency, Reconciliation,
Auditability, Fail-Safe Recovery.
