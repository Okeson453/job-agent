# Phantom Strike — Challenges & Solutions

## The per-trade risk cap contradiction (resolved)
Prior draft claimed Ghost Grid's 1% risk was an absolute, unbreakable
ceiling *and* separately specified an escalating 1.5%-3.0% base-risk
table by campaign day — mutually exclusive claims. Resolved by testing
three scenarios head-to-head via Monte Carlo (10,000 full-campaign runs
each) rather than arguing from the formula:

| Scenario | Per-trade cap | Completion | Ruin | Timeout | Median final equity |
|---|---|---|---|---|---|
| A — 1% enforced | 1.0% | 23.6% | 0.7% | 75.7% | 32,067 USC |
| B — cap ignored, 1.5-3.0% escalation runs unclipped | up to 3.0% | 48.4% | 51.6% | 0.0% | 12,568 USC |
| C — flat compromise (adopted) | 2.0% | 96.4% | 3.6% | 0.0% | 50,722 USC |

Adopted C as the single, non-escalating, authoritative cap — superseding
both the 1% constant and the escalation table.

## Two other corrected defects
- **Unit-category error** — a USC-denominated global max was compared
  directly against a lot-size value (unit mismatch); renamed and
  re-expressed in lot units.
- **Undefined phase ceilings** — the guard stack and precision sizing
  both referenced `phase_ceiling_lot` without the table ever supplying
  values — a real implementation blocker, now resolved with a Day1-5
  table (0.05 -> 0.12 -> 0.20 -> 0.35 -> 0.50 lot).

## Day-gate logic fix
Days 2-3 originally required an AND of full equity target + a 5-win
streak — workable only if the streak carried forward from the prior
day, needlessly punishing for a trader who cleared Day 1 on equity
alone. Changed to the same OR-logic as Day 1 (lower equity threshold OR
a shorter, more achievable streak requirement).

## Open items (Appendix B, resolved but worth re-confirming)
How an external secondary signal blends with H_c; whether this engine
may ever touch Ghost Grid's exit logic (no — proposal only); whether a
standalone micro-capital layer is needed (no — subsumed by the
preservation-pool mechanics).
