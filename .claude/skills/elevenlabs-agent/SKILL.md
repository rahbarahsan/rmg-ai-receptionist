---
name: elevenlabs-agent
description: How this repo defines, syncs, and debugs its ElevenLabs voice agent — prompt structure, tool webhook contract, latency budget, and the docs-first rule. Use when editing anything under agent/, wiring a new agent tool, or debugging a live call.
---

# ElevenLabs agent conventions

## Docs first, always

Fetch the current ElevenLabs Agents documentation before writing or changing
integration code. The API surface moves faster than this file. Anything written
here about *their* API is a map, not the territory — the repo conventions below
are what you should treat as authoritative.

## Source of truth

- `agent/prompts/system.<locale>.md` — the system prompt, one per locale
- `agent/config/agent.config.json` — voice, model, tool list, latency settings
- `scripts/sync-agent.ts` — pushes both to ElevenLabs

Never change agent behaviour only in the ElevenLabs web dashboard. If you do,
the next sync silently reverts it and nobody can review the diff.

## Prompt structure

Keep the system prompt in this order. It is easier to diff and easier to debug
when a call goes wrong.

1. Role and business identity
2. Hard boundaries (no price negotiation, no credit, no order confirmation)
3. Call flow, numbered
4. Tool usage rules — when to call each, what to do when one returns empty
5. Read-back script
6. Escalation triggers
7. Style: pacing, formality, how to handle interruption

## Tool webhook contract

Every tool is one POST to `/api/agent/tools/{name}`.

- Auth: shared secret in the `x-agent-secret` header, checked in `src/lib/auth.ts`
- Body: JSON, parsed by the tool's Zod schema. Reject unparseable input with 400.
- Response: `{ ok: true, data }` or `{ ok: false, reason }` — never a bare error.
  `reason` is written for the *agent* to read aloud-adjacent, so keep it short and
  factual: "no matching product", not a stack trace.
- **Budget: 500ms.** No external HTTP inside a handler. No unindexed queries.
  If something genuinely needs longer, return `{ ok: false, reason: "pending" }`
  and handle it out of band.

## Debugging a bad call

1. Pull the transcript first. Read what the caller actually said, not what you
   assume they said.
2. Check whether the failure was ASR (wrong words in) or reasoning (right words,
   wrong action). These have completely different fixes and are constantly confused.
3. If ASR: add the utterance to `tests/fixtures/banglish-utterances.json`.
4. If reasoning: reproduce it as a tool-level test before touching the prompt.
5. Only then edit the prompt, and change one thing.

## Cost note

Billing is per minute of call duration. Set an auto-hangup on silence, or a caller
who walks away with the line open bills until the timeout.
