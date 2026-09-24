# Void Engine — Architecture: 4 Layers, 12 New Modules

```
LAYER 3 — NOVA CORE (12 adaptive modules, Void Engine's own contribution)
LAYER 2 — v1.1 INTELLIGENCE LAYER (5 modules, pre-existing)
LAYER 1 — PHANTOM STRIKE CAPITAL ENGINE (v1.0, unchanged)
LAYER 0 — GHOST GRID SIGNAL AUTHORITY (unchanged) <- foundation
```

## NOVA CORE — the 12 new modules (Layer 3)
| Code | Name | Function |
|---|---|---|
| NC-I | SENF | Shannon Entropy Noise Filter — blocks entry on random-walk conditions (entropy > 1.20 bits); bonus H_c on low-entropy (structured) conditions |
| NC-II | BREX | Bayesian Regime Engine w/ Markov Transitions — replaces Ghost Grid's `classify_regime()`; blocks on high regime ambiguity (entropy_bits > 1.80) |
| NC-III | MOFI | Micro-Order Flow Imbalance Engine — additive boost to the MPP sub-score inside `calculate_mpp()` |
| NC-IV | DKED | Dynamic Kelly with Exponential Edge Decay — replaces static R-dynamic sizing (data-sparse early days still use v1.0 RDynamic) |
| NC-V | DARR | Dynamic Asymmetric Risk-Reward via market geometry — validates R:R against the live liquidity map before authorizing |
| NC-VI | SHLD | Signal Half-Life Decay — decays stale near-threshold signals sitting on the watchlist instead of letting them fire late |
| NC-VII | LSQI | Live Session Quality Index — blocks entries in dead/low-quality sessions; modulates SSM lot output |
| NC-VIII | LSC | Liquidity Sweep Confirmation — bonus to the HMP sub-score on confirmed sweep+reclaim |
| NC-IX | TV-VAVE | Tick-Velocity Adjusted VAVE — compresses lot sizing when tick velocity is slow during a supposed ignition window |
| NC-X | DTC | Dynamic Threshold Calibration — replaces static H_c/C-Score threshold lookups with regime- and day-conditioned dynamic thresholds |
| NC-XI | ENTP | Entropy Decay Cooldown — replaces fixed-duration cooldowns with an entropy/spread/ATR-conditioned re-arm check |
| NC-XII | AFB | Adaptive Friction Budget — replaces the static FRG friction check with a session/regime-adaptive one |

## Master execution sequence (every trade decision cycle)
Pre-scoring gate (SENF, LSQI, ENTP) -> regime classification (BREX,
Pulse Probe) -> Ghost Grid H_c scoring augmented in-line (LSC into HMP,
MOFI into MPP, SENF bonus into composite) -> signal quality gates (SHLD
decay -> Schmitt hysteresis on the *effective*, decayed H_c) -> Echo
Lock (Layer 2) -> DTC dual gate (dynamic thresholds) -> sizing chain
(DKED r_dynamic -> VAULT SHIELD -> TV-VAVE -> VAVE lot_raw) -> SIGMA /
SSM / APEX LENS (Layer 2) -> DARR risk-governor validation -> AFB
friction gate -> order.

Every module declares its integration point as an exact patch location
in the layer beneath it — e.g. "Replaces `classify_regime()` in Ghost
Grid scoring pipeline," "Inside `calculate_mpp()` — Ghost Grid Part III
Section 3.4," "In Step 11 of `process_trade()` (IGNITION mode)." Nothing
is bolted on generically; every module names its exact host function.

## Module dependency map (abbreviated)
```
                    GHOST GRID  <- signal authority (unchanged)
                        |
      +-----------------+-----------------+
      v                 v                 v
    SENF              BREX              LSQI
      |            (-> PULSE PROBE)       |
      +--------> H_c Scoring Pipeline <---+
                 (HMP+LSC, HLCP, MPP+MOFI, +SENF bonus)
                        |
                 SCHMITT HYSTERESIS (on SHLD-decayed effective H_c)
                        |
                    ECHO LOCK (Layer 2)
                        |
                  DTC DUAL GATE (NC-X)
                        |
          +-------------+-------------+
          v             v             v
        DKED         VAULT SHIELD   TV-VAVE
          +-------------+-------------+
                        v
                 VAVE (Layer 1) -> SIGMA / SSM / APEX LENS (Layer 2)
```
