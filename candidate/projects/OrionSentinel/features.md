# OrionSentinel — Key Features

- Basket-as-unit-of-risk model — 2-5 identically-parameterized
  positions open/manage/close together, never as independent legs
- Conviction-proportional exposure via a lookup table, not a formula:
  basket size is a direct function of signal score, nothing else scales
- Zero external dependency, enforced structurally (no DLLs, sockets, or
  WebRequest calls anywhere in the trading path — verified by code
  review, not just convention)
- Two-terminal-folder deployment model: code in the per-terminal MQL5
  folder, config in the shared `Common\MQL5\Files` folder via
  `FILE_COMMON` — lets multiple chart instances share one config set
- Operational tooling: `TODMatrixBuilder`, `AttributionReview`,
  `OutcomeTagger`, `SupplyCapReport` scripts for weekly/monthly review
  cadence, plus 5 dedicated validation-protocol test scripts
