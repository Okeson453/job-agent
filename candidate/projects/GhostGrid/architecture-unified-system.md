# The Unified System — How the Seven Engines Connect

**Confirmed structure (stated directly, supersedes the earlier
"which framing is true" open question in this file):**

The system has a **core** and a **support tier**:

- **Core:** Ghost Grid (signal authority, entry point) + Phantom Strike
  (capital velocity engine). This is "the main design."
- **Support tier:** Arbiter-Sigma, Echo Pulse, and Kairos Sovereign are
  **independent design systems built to support the core** — their job
  is to feed additional direction and intelligence into Ghost Grid +
  Phantom Strike, not to operate as peers with equal standing or as an
  alternative entry point.

**Because the support tier was designed independently, expect real
integration conflicts, not just documentation gaps.** Each of the
three has its own risk-management logic, its own features, its own
architectural approach — none of it was co-designed against Ghost
Grid's or Phantom Strike's own risk governor. Per direction: these
differences (competing risk rules, mismatched state models, conflicting
thresholds) get resolved **during actual implementation and
integration**, not before. Don't treat any support-tier risk rule as
authoritative over Ghost Grid's or Phantom Strike's own guard stack
until that reconciliation happens — Ghost Grid's 1% cap / Phantom
Strike's resolved 2.0% cap remain the governing constraints for the
core until stated otherwise.

## Core <-> support tier, what's actually written down per engine

**Void Engine** — the tightest-coupled of everything here, effectively
part of the core's own evolution rather than a separate support system:
its own diagram puts Ghost Grid at Layer 0 and Phantom Strike at Layer
1 directly beneath its own Layer 2/3, and several of its modules patch
named functions inside Ghost Grid's actual code. Kept as its own
sub-project here since it's separately specified, but architecturally
it reads as "the next version of the core," not a support system.

**POLM** — also feeds the core directly (`POLM -> Ghost Grid` for bias,
`POLM -> Phantom Strike` for VAVE/FRG/ACE-LSIE) per its own doc, but
that integration is a stated **future roadmap phase (v2.0)**, not built
yet. Today POLM runs as a manual Pine Script suite, independent of
everything else here.

**Arbiter-Sigma** — support tier. A self-contained 10-layer SMC/ICT
execution pipeline with its own risk/capital model (AuM-based sizing,
its own stop-cascade, its own TP cascade). No stated data flow into
Ghost Grid anywhere in its doc — the intelligence it's meant to
contribute to the core isn't wired up in writing yet, per direction
that this happens at integration time.

**Echo Pulse** — support tier. A standalone 22-module pip-movement
detection framework with its own risk/telemetry shield and its own
daily execution governor. It explicitly absorbs "VECTOR PULSE ENGINE,"
which earlier Phantom Strike notes named as a SIGMA FILTER feeder — the
most plausible concrete integration path once reconciliation happens,
but still not stated as built.

**Kairos Sovereign** — support tier, per direction. Worth flagging
honestly: Kairos's *own* doctrine text describes itself as the master
synthesis unifying Ghost Grid, Phantom Strike, Void Engine, POLM, and
Arbiter-Sigma — i.e. its own document claims a broader role than
"support system feeding intelligence to the core." Treating it as
support tier (per direction) rather than as the top-level orchestrator
is a deliberate choice that overrides what Kairos's own text says about
itself — worth remembering if you ever go back to that source doc,
since the doc and the actual intended architecture now disagree on
this point.

## Bottom line
Core = Ghost Grid + Phantom Strike. Void Engine is essentially core
evolution. POLM, Arbiter-Sigma, Echo Pulse, and Kairos Sovereign are
independently-designed support systems feeding direction/intelligence
into the core — expect risk-management and architectural conflicts
between them, deliberately unresolved until real implementation.
