# TestingEngine — Challenges & Solutions

The repo itself documents an active investigation/fix history via
several dated root-cause docs sitting at repo root:
`FORENSIC_PREDICTION_ENGINE_REPORT.md`, `LATENCY_BUDGET_DIAGNOSIS.md`,
`LATENCY_FIX_AUDIT.md`, `LATENCY_GATES_2026_09_12.md`,
`LATENCY_OUTBOX_PREDICTION_DIAGNOSIS.md`,
`DELIVERY_LATENCY_FIX_2026_09_12.md`, `DISCONNECTION_DIAGNOSIS.md`,
`DATABASE_AUDIT_REPORT.md`. This is exactly the kind of "found it,
diagnosed it, fixed it" material worth mining for interview answers —
<!-- TODO: pull specifics from those docs if you want them written up
here individually. -->

**A C++23 conversion of this engine was requested and declined**
(per memory). Now that the actual architecture is visible: TestingEngine
is I/O-bound (WebSocket ingestion, DB writes, Telegram delivery), not
CPU-bound — a rewrite target for a systems language would need a
compute-bound hot path to pay for itself, and the README's own ops
table (`ed_to_signal_ms` latency logs, Neon connection-pool tuning)
points at network/DB latency as the actual constraint, not runtime
speed. That's a solid, defensible reason for the decision if it's ever
asked about directly.

**Ops/diagnostic table (from the README, useful as a "how would you
debug X" answer bank):**

| Symptom | Where to look |
|---|---|
| Late / missing Telegram delivery | Outbox status, pre-send temporal-reason logs, `ed_to_signal_ms` |
| No predictions | History READY state, quality skips (`skipped_no_edge`), sheath halt, fencing |
| Worker offline / pool exhaustion | Neon `max_client_conn`, critical vs. general pool logs |
| Socket blocked (WAF) | `socket_status`, browser edge agent (see EDGE_SETUP.md) |
