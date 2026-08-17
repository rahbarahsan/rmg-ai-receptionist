# Decisions

Append-only. One entry per non-obvious choice. Keep them short.

Format:

    ## YYYY-MM-DD — Title
    **Decision:** what we chose
    **Because:** the reason
    **Cost:** what this makes harder

---

## 2026-08-13 — Agent drafts, human confirms

**Decision:** The voice agent can only create `DRAFT` orders. A human confirms.
**Because:** A transcription error on a quantity is a real financial loss, and no
wholesaler will hand order entry to an AI on day one. Approval is also the feature
that makes the product sellable, not a limitation.
**Cost:** Not fully autonomous. Adds a dashboard we have to build.

## 2026-08-13 — English before Bangla

**Decision:** Complete the flow in English, then add Bangla behind a locale layer.
**Because:** Bangla ASR is the biggest unknown. Isolating it keeps a bad result from
contaminating the rest of the build.
**Cost:** The demo is less impressive until Phase 5.

## 2026-08-13 — Prompts and agent config live in the repo

**Decision:** `agent/prompts/` and `agent/config/` are the source of truth, pushed
to ElevenLabs by a script. Not configured by hand in their dashboard.
**Because:** Dashboard-only config cannot be diffed, reviewed, or rolled back, and
cannot be redeployed for a second customer.
**Cost:** A sync script to maintain.

## 2026-08-15 — ASR spike measures batch Scribe on recorded files

**Decision:** Phase 1 measures ElevenLabs Scribe (`scribe_v2`, batch, `temperature: 0`
+ fixed `seed`) over ~20 recorded utterances, not the live agent's streaming STT.
Ground truth and accepted surface forms live in `tests/fixtures/asr-spike-manifest.json`;
`scripts/asr-spike.ts` scores whether the **number** and **product** survived by token
match (Bengali digits folded to ascii), flags fractions and misses for human review,
and reports survival rates. The measured-rate entry is appended here by the real run.
**Because:** Batch on files is deterministic, cheap, and repeatable — the right first
cut for the day-one gate ("do numbers survive?"), and it needs no telephony. Verified
the STT endpoint against live ElevenLabs docs per Invariant 7.
**Cost:** Clean recorded files are an optimistic proxy; the live streaming pipeline may
degrade further, so the numbers are a floor, not the call-quality figure. Product
survival is auto-scored on head-noun keywords and needs a human eyeball pass.


## 2026-08-15 — Banglish ASR spike: measured number/product survival on Scribe

**Decision:** Measured ElevenLabs Scribe (`scribe_v2`, batch, temp 0) on 19 recorded
Banglish reorder utterances (whole numbers, no-cognate fractions, unit + product stress, some in noise).
Survival of the intended token in the transcript:
- Number: **83%** exact / **89%** any-form
- Unit:   **76%**
- Product:**44%** exact / **56%** any-form

**Call: PROCEED**, with mitigations. Whole numbers are robust (survived exactly even
buried in a negotiation sentence). The only number failures are no-cognate fractions
fused to a *short* unit (`দেড় পিস → দের পেস`, `আড়াই হালি → আরাইহানি`); the same
fractions with `ডজন` are flawless. Mitigations, all already implied by existing
invariants: (1) read-back of quantity is mandatory and, for fractions/units, must be
explicit — Invariant 5 + the confidence rule; (2) use Scribe's per-word `logprob` as a
live confidence gate (the `polo→polonium` corruption self-reported at -1.22 vs ~0 for
clean tokens); (3) resolve products against the caller's catalog + read-back rather than
trusting the raw transcript (`গ্রোস → গজ`/*yard* is a silent wrong-unit to watch).

**Because:** Bangla ASR on NUMBERS is the project's single largest unknown (ROADMAP Phase 1).
A number that does not survive ships the wrong quantity of goods. This is the day-one gate.

**Cost:** Batch Scribe on clean-ish files is an optimistic proxy — the live agent's streaming STT
may degrade further. Product names and fractions attached to a weak unit are the soft spots
(see tests/fixtures/asr-spike-results.json). Cases flagged for human review: en-plain-dozen, en-plain-hali, bn-number-en-unit, en-number-bn-unit, bn-half-more, bengali-digits, color-red-shirt, ambiguous-bare-number, non-integer-real, arai-hali, bn-char-dozen-panjabi.

## 2026-08-15 — Rewrite the stack from TypeScript/Next.js to Python/FastAPI

**Decision:** At the owner's request the app is Python now: FastAPI · Pydantic v2 ·
SQLModel + Alembic · uv · ruff · mypy(strict) · pytest; Streamlit for the Phase-4
dashboard. `CLAUDE.md` was rewritten to match (domain invariants kept, stack conventions
+ commands swapped). The old TypeScript/Next.js implementation is preserved under
`legacy-ts/` (this is not a git repo, so a folder backup is the only safety net). Phase-2
parity was re-ported: tool webhook contract (`x-agent-secret`, 404/400/200, `x-tool-ms`,
500ms budget), the `elevenlabs-signature` HMAC verification, phone/customer lookup, both
inbound webhooks, and `sync_agent.py`. Phase-1 findings + fixtures are language-agnostic
and reused as-is; the Banglish parser + ASR harness stay in `legacy-ts/` for a Phase-3 port.
**Because:** the owner is a Python expert and will maintain this; a single-language
codebase they are fluent in beats one they are not.
**Cost:** a lateral rewrite with no new features — real re-porting effort, and the
working, verified TS code is retired. Two Python-specific gotchas to remember: SQLModel's
table metaclass needs a relaxed mypy override on `app/models`; and `.env` must carry a
real `AGENT_TOOL_SECRET` (≥16 chars) — it was empty under TS (env was never parsed at
runtime), which now fails fast at startup.

## 2026-08-16 — Prices in USD cents for the demo (was BDT poisha)

**Decision:** Money is stored as integer **US cents** and shown as `$X.XX`. Catalog reset
to realistic wholesale USD (polo $4, tee $2, genji ~$1.20, panjabi $7, shirt $5). Fields
renamed `total_poisha`→`total_cents`, `unit_price_pois`→`unit_price_cents`; `search_catalog`
and `create_draft_order` return a formatted `"$"` string so the agent reads it naturally.
**Because:** on a live call the agent read raw poisha aloud ("thirty-two thousand poisha"),
which sounds absurd; USD is clearer for the current demo audience.
**Cost:** diverges from the original BDT framing — revisit when localizing for the real
Bangladeshi market. The integer-minor-unit discipline (no floats) carries over unchanged.

## 2026-08-17 — Banglish path is a locale layer; Bengali TTS needs eleven_v3 (gated)

**Decision:** Bangla is added as a **locale layer, not a fork** (invariant 6): two agents
(en + bn) share one number, backend, tools, and catalog; only the prompt + TTS/ASR config
differ. `agent.config.json` holds shared fields + a `locales` map; `LANGUAGE_LOCALE` drives
`scripts/sync_agent.py`, which builds that locale's agent and reassigns the number to it
(`PATCH /v1/convai/phone-numbers/{id}`). Quantities stay LLM-interpreted with a mandatory
explicit Banglish read-back (unit + pieces). A deterministic Banglish parser is deferred.
**Because:** the backend is already bilingual (Bengali catalog aliases, Bengali units in
`app/bangla/units.py`, verbatim `spoken_qty`), so only conversation config changes.
**Cost / blocker:** the Bengali agent's TTS must be **`eleven_v3`** — verified via
`GET /v1/models` that it is the *only* model listing `bn` (turbo/flash/multilingual_v2 all
reject `language: bn`). `eleven_v3` is "Expressive TTS", initially gated (`expressive_tts_not_allowed`).
**Resolved 2026-08-17:** after Expressive TTS was enabled, direct v3 TTS worked but the
convai *agent* still rejected `eleven_v3` — the correct **agent** model id is
**`eleven_v3_conversational`**, which is accepted with `language: bn`. The bn agent
(`eleven_v3_conversational`) is live; the number toggles between en/bn via
`LANGUAGE_LOCALE`. (Free-plan note: library voices are blocked on the direct TTS API but
work inside the agent.)
