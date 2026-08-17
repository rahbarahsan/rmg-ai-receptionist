# Roadmap

> Edit freely. This is the plan, not a contract. Finish a phase's acceptance test
> before starting the next. Commands are `uv run …` (see CLAUDE.md).

## Phase 0 — Scaffold ✅
Repo, CLAUDE.md, context docs, schema, tool skeleton, tests.

## Phase 1 — The ASR spike ✅
Measure how badly **numbers** and **product names** degrade on ElevenLabs STT before
building on top of them.
**Result (2026-08-15):** 19 Banglish clips on Scribe `scribe_v2` — number survival 83%
exact / 89% any-form, unit 76%, product 44% exact. **PROCEED with mitigations** (see
`DECISIONS.md`): whole numbers are robust; the only failures are no-cognate fractions fused
to a short unit, which the mandatory quantity read-back catches. Raw data:
`tests/fixtures/asr-spike-results.json`.

## Phase 2 — Python stack + one callable number ✅
Rewrote the app from TypeScript/Next.js to Python/FastAPI (see `DECISIONS.md`). A real
Twilio number answers via an ElevenLabs agent; agent config + prompts live in the repo and
are pushed by `scripts/sync_agent.py`.

## Phase 3 — Tools and the draft order ✅
`search_catalog`, `check_stock`, `create_draft_order`, `escalate_to_human` (+ a latent
`lookup_customer` for repeat callers). Mandatory read-back before drafting.
**Acceptance met:** a call produces a `DRAFT` with correct items and quantities.

## Phase 4 — Human approval + the final offer ✅
Streamlit operator dashboard lists drafts. Approve → `CONFIRMED` → send the itemised, priced
offer to the shop owner by **SMS (Twilio)** or **email (Gmail SMTP)**, in the caller's
language.
**Acceptance met:** call → draft → approve → offer delivered.

## Phase 5 — Banglish ✅
Bangla/Banglish agent as a **locale layer, not a fork** (one number toggles languages via
`scripts/serve.py`). Bengali TTS via `eleven_v3_conversational`. Bengali catalog aliases +
units resolve; read-back restated in the caller's unit. Language-varying data lives in
`app/locale/registry.py` — adding a language is three data edits (see `EXTENDING.md`).

---

## Next
- **Deterministic Banglish numeral parser** (`app/locale/` + un-skip the
  `banglish-utterances.json` golden set) — hardens fraction handling beyond LLM + read-back.
- **Data-model localization** — per-locale product names / a translations table, for real
  multi-language catalogs at scale (seams are in place; not yet built).
- **Repeat-caller recognition** — wire the personalization webhook + `lookup_customer` so a
  known number is greeted by shop name.
- **The write-up** — demo video + measured latency/ASR numbers in the README.
