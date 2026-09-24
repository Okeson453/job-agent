# POLM (Phantom Orb-Liquidity Matrix) — Overview

**Source doc:** POLM_Master_Doctrine_v1_1.md — "Master Systems
Doctrine v1.1," production-hardened successor to a theoretical v1.0.

**Core function:** every trading session resolves into exactly one of
four phases — Expansion, Mean Reversion, False Breakout/Liquidity
Sweep (new in v1.1), or no-trade. Rather than committing to one
outcome before the session opens, POLM's Multi-Factor Regime
Classification Engine (MF-RCE) reads five weighted dimensions of
early-session price behavior in real time and deploys the matching
execution protocol (Alpha = mean reversion, Beta = breakout expansion,
Gamma = liquidity sweep). Fuses three legacy strategy lineages: Box
Theory/Daily Range Reversal, Opening Range Breakout, and Adaptive
Volatility Bracket.

**Current operational reality (important status detail):** POLM today
is a **manual, discretionary system** — a TradingView Pine Script
indicator suite that a human reads and executes by hand. Full
algorithmic execution (Python signal layer -> Rust execution gateway ->
broker API) is on the roadmap but not yet built — see status.yaml.

See `../architecture-unified-system.md` for exactly how POLM is meant
to connect to Ghost Grid and Phantom Strike.
