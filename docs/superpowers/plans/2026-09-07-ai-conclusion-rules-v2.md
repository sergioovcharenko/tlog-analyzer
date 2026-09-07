# AI Conclusion Rules v2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the existing AI reconstruction turn rule-derived TLOG facts into a concise evidence-based conclusion about radio loss, pilot response, altitude response, VTX/channel response, RTL/LAND sequence, and possible alternatives.

**Architecture:** Keep `backend/ai_reconstruction.py` deterministic. Existing analyzers remain the source of facts; the reconstruction layer only correlates those facts and writes cautious Ukrainian conclusions. Do not add an external LLM dependency.

**Tech Stack:** Python 3.11, unittest, existing HTML renderer.

**Spec:** `docs/superpowers/specs/2026-09-07-ai-reconstruction-summary-design.md`

## Global Constraints
- Existing diagnostic rules and findings remain unchanged.
- Conclusions must use only facts present in the TLOG-derived structure.
- Never phrase an unverified alternative as a guaranteed fix or pilot fault.
- A VTX/channel change or altitude climb that is actually present must be acknowledged rather than reported as missing.
- Confidence remains evidence-count based: High / Medium / Low.

---

### Task 1: Radio-loss response reasoning

**Files:**
- Modify: `tests/test_ai_reconstruction.py`
- Modify: `backend/ai_reconstruction.py`

**Interfaces:**
- Consumes: `build_ai_reconstruction(facts: dict) -> dict`
- Produces: richer `what_happened`, `likely_sequence`, `pilot_actions`, `possible_alternatives`, `evidence`, and existing `confidence`.

- [ ] **Step 1: Write failing tests** for repeated -128 dBm with stable ~100 m altitude and no VTX change; confirmed VTX change; and confirmed altitude climb.
- [ ] **Step 2: Run the focused tests and verify RED** because the current implementation does not explicitly acknowledge the positive response cases or report radio evidence in detail.
- [ ] **Step 3: Implement minimal deterministic correlation logic** in `backend/ai_reconstruction.py`.
- [ ] **Step 4: Run focused tests and verify GREEN**.
- [ ] **Step 5: Commit** the implementation.

### Task 2: Regression verification

**Files:**
- Test: `tests/test_ai_reconstruction.py`
- Test: `tests/test_ai_reconstruction_integration.py`
- Test: `tests/test_ai_reconstruction_frontend_contract.py`

**Interfaces:**
- Consumes the same JSON contract already rendered by the frontend.
- Produces no frontend schema change.

- [ ] **Step 1: Run all AI reconstruction unit/integration/frontend tests.**
- [ ] **Step 2: Compile `backend/main.py` and `backend/ai_reconstruction.py`.**
- [ ] **Step 3: Verify the existing renderer contract is unchanged.**
- [ ] **Step 4: Commit any test-only corrections if required.**
