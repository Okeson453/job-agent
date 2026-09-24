# Echo Pulse — Open Calibration Items (from the doc's own engineering notes)

1. Fusion weights and hysteresis thresholds are placed but numerically
   unvalidated pending the walk-forward protocol
2. Microstructure gate vs. weighted score — resolved in favor of a hard
   gate, a deliberate design decision worth being able to defend
3. ML Fusion Core needs a labeled outcome dataset before it can
   live-influence execution; runs shadow-then-proxy until then
4. Order-flow inputs depend on data availability — LFC's tick-volume
   fallback is the production default without L2 data
5. DEG's default state (opt-in vs. always-on) is unconfirmed
6. DEG's fixed lot premium may itself breach Tier 0-1 risk ceilings at
   low capital — recommendation is to disable DEG below Tier 2 pending
   confirmation
7. DEG's 15-pip floor is a hard reject by design intent, flagged as
   worth revisiting if partial-target scaling is actually wanted
8. The 18% adaptive allocator table and GA genome constraints are v1.0
   defaults awaiting AFL-driven refinement, not validated constants
9. Instrument-specific calibration profiles are explicitly the
   highest-effort, lowest-urgency backlog item
