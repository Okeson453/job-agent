# TestingEngine — Architecture (per repo README)

```
BC.Game native WS / Socket.IO         REST poll (recovery path)
        |                                     |
        v                                     v
  Railway worker (npm run worker)
    ED(N)  -> observe -> predict N+1 -> outbox -> Telegram
    BG(N)  -> started_at + temporal kill of late signals
    Poll   -> recovery when the socket path misses a round
    Feedback -> adaptive edge / ACIE online weight updates
        | writes
        v
  PostgreSQL (Neon / Railway)
        | reads
        v
  Vercel dashboard (TanStack Start SSR) -- read-only: rounds,
  predictions, worker health
```

## Production prediction path (ED-primary)
1. **ED(N)** — crash round N ends -> observe on ACIE -> claim target
   N+1 -> build in-memory history (includes N) -> evaluate -> edge/
   quality gates -> durable `pending_predictions` + `notification_outbox`
   rows written -> `notifyOutbox`
2. **Delivery** — dispatcher claims pending outbox rows (immediate by
   default) -> pre-send temporal authorization check -> Telegram
3. **BG(N+1)** — stamps the next round's start; dead-letters any
   undelivered prediction still targeting the now-started round
4. **Validation** — when N resolves: WIN/LOSS + feedback updates ACIE's
   online state / adaptive edge
5. **Poll** — safety net only, fires if the live socket path missed
   ownership or events entirely

## Design invariants (explicit, from the README)
- One target -> one prediction owner (in-memory claim + a DB unique
  constraint on unmatched `pending_predictions.target_game_id`)
- No outcome leakage — features/history never include the target
  round's own crash result
- Temporal contract — a signal must be generated *and delivered*
  before the target round starts
- Quality over volume — ENTRY only when model probability beats fair
  odds (1/1.30 ~= 76.9%) plus a configurable edge
- Worker authority fencing — only the current lease holder mutates live
  state (prevents split-brain across worker restarts/deploys)

## Repository layout (as of inspection)
```
scripts/worker.mjs          # process entry -> live boot
src/lib/prediction/
  live/                     # boot, predictor, validator, outbox, poll, feedback
  events/game-event-handlers.ts
  acie/                     # shared ACIE engine, PSI, strategy, online state
  models/ features/ ...     # fallback PredictionEngine stack
migrations/                 # ordered SQL (outbox, feedback, fencing, indexes)
docs/                       # deep-dive investigations
```
