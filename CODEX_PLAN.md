# Finmaxxin Backend Plan: Dynamic LLM Advisory (House Decision + Down Payment + Market Context)

## Summary
Replace static template-style recommendation behavior with a backend advisory pipeline that generates dynamic written guidance using a **free open-source LLM** served via **llama.cpp sidecar**, enriched with **weekly-refreshed free public market data**.

This plan keeps simulation math as the quantitative backbone, but adds an advisory orchestration layer that produces a single decisive narrative answer:
- Should buy now vs wait
- Suggested down payment amount/range
- Current market-condition interpretation
- One primary action

It also adds strict output validation and deterministic fallback to avoid brittle or unsafe responses.

## Goals and Success Criteria
1. Generate dynamic advisory text per scenario, not static candidate templates.
2. Include explicit house-buy recommendation and down payment guidance in every response.
3. Include market condition interpretation from free public data (Canada-wide baseline).
4. Return one primary action (not three equal recommendations).
5. Maintain resilience: if LLM or market APIs fail, return deterministic fallback advisory.

Success is achieved when:
- `/advisor-brief` returns valid narrative for >=95% requests under normal conditions.
- Fallback engages gracefully (no hard 5xx) for dependency outages.
- Output always includes required advisory sections (verdict, down payment, market context, risk note, action).

---

## Current State (Grounded Findings)
1. `RecommendationService` is currently deterministic template ranking with fixed candidates.
2. No LLM integration exists in backend service container or routes.
3. No market data ingestion exists.
4. Existing APIs return numeric simulation/recommendation payloads but no dynamic advisory narrative.
5. Existing simulation engine already produces useful quantitative primitives for advisory grounding.

---

## Backend Architecture Additions

### 1) New Services
1. `MarketDataService`
   - Pulls free public Canada-wide indicators weekly.
   - Normalizes into a compact market snapshot used by advisory generation.
   - Caches latest snapshot and age metadata.
2. `LlmClientService` (llama.cpp HTTP client)
   - Calls sidecar model endpoint with prompt + generation parameters.
   - Handles timeout/retry and model availability checks.
3. `AdvisorPromptService`
   - Builds grounded prompt from:
     - Scenario inputs
     - Simulation outputs (baseline vs scenario deltas/probabilities)
     - Market snapshot
     - Policy/risk posture
4. `AdvisoryValidationService`
   - Strictly validates narrative contains required sections:
     - Buy verdict
     - Down payment guidance (absolute CAD amount and/or range)
     - Market condition explanation
     - Risks/assumptions
     - One primary action
   - If invalid: one regeneration attempt, then fallback.
5. `DeterministicFallbackAdvisor`
   - Rule-based narrative generator when LLM/API unavailable or invalid output.
   - Uses existing simulation values + core affordability heuristics.
6. `AdvisoryOrchestratorService`
   - Coordinates market fetch/cached snapshot + prompt + LLM + validation + fallback.
   - Produces final advisory response and trace metadata.

### 2) Data/Cache
1. Add in-memory cache for market snapshot initially (keyed by `geo_scope`, with `fetched_at`).
2. Reuse existing store for advisory trace records in prototype.
3. Record advisory events (`advisor_generated`, `advisor_fallback_used`, `advisor_validation_failed`).

### 3) Infrastructure (Free/Open Source)
1. Add `llama.cpp` sidecar container in `docker-compose.yml`.
2. Mount local GGUF model path into sidecar container.
3. Backend uses sidecar endpoint via env vars.
4. Keep all software open-source and self-hosted (no paid inference API).

---

## Public API Changes

### New Endpoint
1. `POST /v1/scenarios/{scenario_id}/advisor-brief`
   - Auth/ownership checks identical to current scenario endpoints.
   - Requires prior simulation (or internally triggers simulation if absent; recommended: require prior simulation for determinism).
   - Returns narrative advisory text plus minimal metadata.

### Response Contract (narrative-first)
Even with narrative-first design, include minimal machine metadata for reliability/debug:
- `scenario_id`
- `decision_id`
- `advice_text` (primary, user-facing narrative)
- `generated_at`
- `market_snapshot_date`
- `llm_model`
- `fallback_used` (bool)

`advice_text` format requirement (validated):
- “Verdict: Buy now / Wait”
- “Suggested down payment: CAD amount or range (+ rationale)”
- “Market conditions this week: …”
- “Key risks: …”
- “Primary action: …”
- “Note: …” (soft disclaimer)

### Existing Endpoints
- Keep current simulation/recommendation endpoints unchanged for compatibility.
- Existing frontend can consume new endpoint incrementally without breaking current flows.

---

## Market Data Plan (Free Public APIs, Weekly Refresh)

### Scope
Canada-wide baseline (with province-aware references where available later).

### Sources (free/open)
1. Bank of Canada Valet API (policy/benchmark rates and related series).
2. One additional free public macro series source for inflation/housing trend proxy (configured provider abstraction).

### Refresh Policy
1. Weekly scheduled refresh + on-demand stale check.
2. If fetch fails:
   - Keep last good snapshot.
   - Set stale flag in advisory metadata.
   - Allow advisory generation with stale context.

---

## LLM Strategy

### Runtime
- `llama.cpp` server sidecar (Docker).

### Model Class
- 3B instruct model (configurable), GGUF format.
- Defaults controlled via env:
  - `FINMAXXIN_LLM_BASE_URL`
  - `FINMAXXIN_LLM_MODEL_NAME`
  - `FINMAXXIN_LLM_TIMEOUT_MS`
  - `FINMAXXIN_LLM_MAX_TOKENS`
  - `FINMAXXIN_LLM_TEMPERATURE`

### Prompting
1. System prompt with role constraints:
   - Financial planning explainer
   - No fabrication of unknowns
   - Must use provided scenario/simulation/market facts
   - Must output required sections
2. User content includes:
   - Snapshot metrics
   - Scenario assumptions
   - Baseline vs scenario outcomes
   - Market snapshot with timestamps
   - Conservative risk posture and one-action requirement

### Validation Gate
1. Hard checks for required sections and CAD down payment presence.
2. Regenerate once on failure.
3. Fallback to deterministic advisory if still invalid or timed out.

---

## Deterministic Fallback Rules (When Needed)
Fallback narrative should still answer user intent clearly:
1. Buy verdict rule:
   - Prefer “Buy now” only if scenario outperforms baseline above threshold and downside acceptable.
2. Down payment suggestion:
   - Compute recommended CAD amount/range from:
     - user-entered home price (if present)
     - affordability and liquidity guardrails
     - emergency fund sufficiency
3. Market summary:
   - Use latest cached market snapshot with “data age” mention.
4. Output one primary action only.

---

## Security, Safety, and Reliability
1. Keep existing auth and scenario ownership checks.
2. Sanitize prompt inputs and cap lengths to reduce prompt-injection amplification.
3. Add timeout/circuit-breaker around LLM and market fetch calls.
4. Enforce response-size limits.
5. Emit advisories with trace metadata for auditability.
6. Include soft disclaimer in final narrative (per selected preference).

---

## Implementation Steps (Decision-Complete)
1. Add config fields for LLM and market data provider settings.
2. Add new advisory/market contracts in `models/contracts.py`.
3. Implement `MarketDataService` with weekly cache policy and provider abstraction.
4. Implement `LlmClientService` for llama.cpp calls with retries/timeouts.
5. Implement `AdvisorPromptService`.
6. Implement `AdvisoryValidationService`.
7. Implement `DeterministicFallbackAdvisor`.
8. Implement `AdvisoryOrchestratorService`.
9. Extend `ServiceContainer` and app wiring (`deps.py`, `main.py`).
10. Add new route `POST /v1/scenarios/{scenario_id}/advisor-brief`.
11. Add event emissions for advisory lifecycle.
12. Add docker-compose llama.cpp sidecar service and env wiring.
13. Add README section for local model setup (GGUF path and startup).
14. Add tests (unit + API + failure-mode).

---

## Test Cases and Scenarios

### Unit Tests
1. Prompt builder includes all required factual sections.
2. Validator rejects missing verdict/down payment/market/action sections.
3. Market data parser handles API schema and stale-cache fallback.
4. Fallback advisor produces valid narrative from simulation inputs.

### Integration/API Tests
1. Happy path:
   - scenario -> simulate -> advisor-brief returns valid narrative.
2. LLM timeout path:
   - returns deterministic fallback with `fallback_used=true`.
3. Market API failure path:
   - uses cached snapshot and marks stale context.
4. Auth/ownership checks mirror existing behavior.

### Behavioral Tests
1. Home purchase scenario with price/down payment inputs.
2. Scenario without home purchase input still returns explicit “insufficient housing input” guidance.
3. Low-confidence/high-downside scenario yields “wait” verdict and safer action.
4. Narrative always returns one primary action only.

---

## Rollout and Monitoring
1. Feature flag `FINMAXXIN_ENABLE_ADVISOR_BRIEF`.
2. Metrics:
   - advisory latency p50/p95
   - validation failure rate
   - fallback usage rate
   - market snapshot age
3. Logs include advisory id, scenario id, dependency status, fallback reason.

---

## Explicit Assumptions and Defaults Chosen
1. Backend-first change; no mandatory frontend refactor in this phase.
2. LLM runtime: `llama.cpp` sidecar.
3. Model class: 3B instruct GGUF.
4. Market data: free public APIs, weekly refresh.
5. Advisory generation mode: LLM narrative-first with strict output validator.
6. API shape: new endpoint `/v1/scenarios/{scenario_id}/advisor-brief`.
7. Response style: narrative-focused text with minimal technical metadata.
8. Primary action policy: exactly one primary action in advisory response.
9. Failure behavior: deterministic fallback (not hard 503) when dependencies fail.
10. Disclaimer style: soft disclaimer included in narrative output.
