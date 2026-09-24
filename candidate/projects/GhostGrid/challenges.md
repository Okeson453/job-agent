# Ghost Grid — Challenges & Solutions

## Known issues from GitHub repo audit (verify current status before citing)
- Linux/Windows Dockerfile incompatibility with `pywin32` — **now
  explained by the design doc:** the Python core's Named Pipe IPC
  depends on `pywin32`, a Windows-only package, while CI/Docker likely
  ran on a Linux base image. This is a deployment-target mismatch, not
  a logic bug.
- Dataclass schema drift causing ~23% test failures
- Empty backtesting/scripts stubs
- Missing `asyncio` import in `fill_handler.py`
- 168 ruff lint issues

## Deliberate design trade-offs (the "what was removed and why" table)
The doc is explicit about 16 institutional-grade components that were
removed or replaced and why (AF_XDP/DPDK kernel bypass -> unneeded for
<5ms local named-pipe IPC; Disruptor ring buffer -> asyncio.Queue is
sufficient for single-symbol fan-out; 16 CPU-pinned actors -> asyncio
coroutines handle <10 instruments fine; Kubernetes -> Docker Compose,
no horizontal-scaling requirement solo; ML outcome predictor and HMM
regime classifier -> deferred/simplified, need 500+ live trades to
train first). This is strong "why did you choose X over Y" interview
material — each row has an explicit reasoning column in the source doc.

## Realistic build timeline (solo, part-time 20h/week)
~31-44 weeks (8-11 months) end to end, phased: IPC bridge -> HMP scoring
-> HLCP+MPP scoring -> fusion+regime+alerts -> risk/exits -> nuclear
controller+paper trading -> phased live (0.1%->0.5%->1% risk, 14-day
gate per stage) -> metrics dashboard.
