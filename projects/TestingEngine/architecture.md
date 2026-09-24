# TestingEngine — Architecture

Status: designed (architecture complete; partial implementation exists separately).

## Purpose
Real-time testing and prediction engine for trading systems.

## Design
- Ten-layer execution state machine for order/test lifecycle.
- WebSocket ingestion for live market and test events.
- PostgreSQL-backed prediction pipeline and event store.
- Event-driven boundaries between ingestion, scoring, and dispatch.

## Verified technologies (design + partial implementation)
TypeScript, WebSockets, PostgreSQL.

## Production
Production deployment is not claimed.
