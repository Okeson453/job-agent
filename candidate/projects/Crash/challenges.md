# Crash (CrashWave) — Challenges & Open Items (per the repo's own status note)

The README states plainly: *"Final production sign-off remains
dependent on restoring dependency installation and executing the
remaining live integration, E2E, load, Lighthouse, security, and
compliance verification gates."* Concretely still open, per the repo:
- Live integration + E2E test execution (auth, bet lifecycle, game
  state transitions, WebSocket reconnect, error boundaries, admin
  controls, offline recovery, accessibility)
- Load testing (`load-test-500.ts`) and a soak test (`soak-observe.ts`)
- Multi-instance WebSocket behavior validated under Redis coordination
  at target infrastructure scale — explicitly flagged as unverified
- Lighthouse, security, and compliance gates

**19 migrations** track the platform's evolution including two
back-to-back `018_*` migrations (`018_acie_sol_records.sql` and
`018_production_hardening.sql`) — worth noting the `acie_sol_records`
migration name directly references TestingEngine's ACIE terminology,
suggesting some data-layer connection between the two repos that isn't
explained in either README. <!-- TODO: worth confirming directly
whether/how Crash and TestingEngine share data. -->
