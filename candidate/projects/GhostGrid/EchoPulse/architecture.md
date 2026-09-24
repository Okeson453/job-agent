# Echo Pulse — Architecture (Full Pipeline)

```
RAW MARKET DATA / TICK STREAM
  -> Ingestion & Buffer Fabric (ring buffers, dual worker loops)
  -> CONTEXT TIER: Regime Core (RC) -> Volatility Topology Core (VTC)
       -> Session Context Core (SCC) -> Macro Risk Gate (MRG)
  -> SIGNAL TIER: Vector Alignment Layer (VAL) -> Momentum Vector Core
       (MVC) -> Liquidity & Flow Core (LFC) -> Pattern Confluence Core (PCC)
  -> VALIDATION TIER: Microstructure Gate (MSG) -> Statistical
       Normalization Core (SNC) -> ML Fusion Core (MFC)
  -> Confluence Fusion Engine (CFE) -> State Transition Governor (STG,
       hysteresis FSM)
  -> Pip Projection Core (PPC) -> Trade Quality Index (TQI)
  -> Execution Routing Matrix (ERM)
  -> Risk & Telemetry Shield (RTS) -> ORDER / BROKER API
  -> Adaptive Feedback Loop (AFL) -- feeds back into every core's weights
```

## Governance & capital extensions
- **Daily Execution Governor (DEG)** — hard trade-count circuit
  breaker; 15-pip triple-redundant minimum profit floor (hard reject,
  not soft target); suspension scope after trade 2; opt-in overlay,
  not yet confirmed as always-on
- **Capital-Tier Adapter (CTA)** — equity-tier router for sub-$500 accounts
- **Compounding Velocity Monitor (CVM)** — target-pacing monitor

## Inter-module data contract (the framework's own integration-layer
invention — none of the 7 source docs specified this)
Every module emits a typed envelope: `score`/`state` **and** a
`confidence_interval` (point estimates without uncertainty bounds are
rejected by CFE at fusion time), declared `upstream_dependencies` (so
the pipeline is representable as a DAG and parallelized where
independent — e.g. VTC and SCC compute concurrently), and a
`latency_budget_ms` — a module exceeding budget is flagged `stale=true`
and CFE treats it as **not present**, never as a cached fallback, since
a stale regime read can invert an entire trade decision.
