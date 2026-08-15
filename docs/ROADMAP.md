# Roadmap

> Edit freely. This is your plan, not a contract. One phase per Claude Code session;
> finish a phase's acceptance test before starting the next.

## Phase 0 — Scaffold ✅

Repo, CLAUDE.md, context docs, schema, tool skeleton, empty tests.

**Acceptance:** `pnpm typecheck && pnpm test` passes on an empty implementation.

---

## Phase 1 — The ASR spike ✅

Record 20 realistic Banglish reorder utterances. Run them through ElevenLabs agent
STT. Measure how badly **numbers** and **product names** degrade.

**Acceptance:** `tests/fixtures/banglish-utterances.json` filled with real
transcriptions and a measured error rate written into `docs/DECISIONS.md`.

**Result (2026-08-15):** 19/20 clips measured on Scribe `scribe_v2`. Number survival
83% exact / 89% any-form, unit 76%, product 44% exact. **Call: PROCEED with mitigations**
(see DECISIONS). Whole numbers robust; only failures are no-cognate fractions fused to a
short unit (পিস/হালি). Harness: `pnpm asr:spike` (`scripts/asr-spike.ts`), raw data in
`tests/fixtures/asr-spike-results.json`. Follow-ups: re-record missing clip 09; the
mandatory quantity read-back must be explicit for fractions/units.

Why first: if Bangla ASR cannot hold numbers, every later phase is built on sand.
Finding that out on day one is a good outcome, not a failure.

---

## Phase 2 — One callable number, English

A real phone number that answers, identifies a known caller, and hangs up politely.
No ordering yet.

**Acceptance:** you can call it from your phone and hear your own shop name.

**Status (2026-08-15):** Stack re-ported to Python/FastAPI (see DECISIONS); old TS app
in `legacy-ts/`. Phase-2 code is built + verified offline — the conversation-init webhook
(greet by shop name), post-call `CallLog` (hashed phone), `lookup_customer` tool, and
`sync_agent.py`; ruff/mypy/pytest all green. **Not yet live**: needs voice_id/model/llm in
`agent.config.json`, a valid `AGENT_TOOL_SECRET` in `.env`, the Alembic migration run
against Postgres, and the Twilio number + two webhook URLs wired in the dashboard.

---

## Phase 3 — Tools and the draft order

`lookup_customer`, `search_catalog`, `check_stock`, `create_draft_order`,
`get_order_status`, `escalate_to_human`. Read-back before drafting.

**Acceptance:** a call produces a `DRAFT` row with correct items and quantities.

---

## Phase 4 — Human approval and the final offer email

Dashboard list of drafts. Approve → status `CONFIRMED` → email the final offer
(itemised, priced, with delivery terms) to the shop owner.

**Acceptance:** end-to-end call → draft → approve → email received.

---

## Phase 5 — Bangla

Bangla system prompt, numeral normalization, unit handling, Bangla read-back.
Golden utterance set must pass.

**Acceptance:** the Phase 4 flow completes entirely in Bangla.

---

## Phase 6 — The write-up

Demo video, README with architecture, honest limitations section, measured latency
and ASR numbers. This is the deliverable that gets read.

**Acceptance:** a stranger can understand what you built and what it cannot do.
