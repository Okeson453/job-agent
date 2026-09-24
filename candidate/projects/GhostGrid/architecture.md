# Ghost Grid — Architecture

```
MT5 Terminal (Windows VPS)
  Expert Advisor (MQL5): OnTick (capture+indicators), OnTimer (CVD
  delta, 200ms pulse), Named Pipe Server (IPC to Python core)

Python Orchestration Core (same VPS):
  Market Data Processor -> H_c Scoring Engine (HMP+HLCP+MPP) ->
  Regime Fingerprint (simplified 4-state) -> Risk Governor (hardcoded
  constants) -> Execution Commander (order dispatch via pipe -> EA) ->
  Position State Machine -> Exit Warfare Engine (4 layers) -> Nuclear
  Controller (portfolio circuit breaker) -> SQLite WAL (event log) ->
  Watchdog (equity poll every 2s) -> Telegram Bot
```

## H_c confluence score (0-180, three strategies, 0-60 each)
- **HMP** — Smart Money Structure (BOS, CHoCH, FVG, order blocks)
- **HLCP** — Trend + Liquidity Intelligence (EMA ribbon, liquidity
  mapping, momentum decay)
- **MPP** — Institutional Footprint (CVD divergence, session bias,
  absorption)
- Confluence decision gate: Schmitt hysteresis (signal must persist
  across >=2 consecutive scoring cycles — anti-flicker)

## Risk governor (hardcoded, not runtime-adjustable)
Module-level Python constants loaded at import time, never
re-evaluated at runtime — "risk is a hardware constant" principle
carried over from HFT design even though this isn't true HFT.

## Multi-layer exit system (4 layers)
1. Profit trigger + trail arming
2. Trailing stop execution
3. Weakness detection
4. CVD divergence override

## Nuclear portfolio guardian
Fires `asyncio.gather` across all position-close commands
simultaneously (not sequentially) when any single nuclear-trigger
condition fires — atomic portfolio defense, same guarantee HFT circuit
breakers give at hardware speed.

## HFT principles preserved despite not being true HFT
1. Signal must sustain (Schmitt hysteresis, not latency gates)
2. Exit is mechanical, never discretionary (state machine decides)
3. Risk is a hardware constant (module-level, load-time only)
4. Order flow is the primary signal (tick-volume CVD proxy, not raw
   matching-engine order flow)
5. State is immutable and replayable (SQLite event log, full
   reconstruction of any closed position)
6. Portfolio defense is atomic (`asyncio.gather`, not sequential)
