# RMG AI Receptionist

A voice agent that answers the phone for a garments wholesaler in Bangladesh and
takes reorders from retail shop owners in mixed Bengali–English (Banglish) speech.

The agent prepares orders. A human confirms them. Nothing ships on an AI's say-so.

## Status

- **Phase 0 — scaffold** ✅
- **Phase 1 — ASR spike** ✅ — measured how well ElevenLabs Scribe preserves Banglish
  numbers and product names. Whole numbers survive well (≈83% exact); no-cognate
  fractions fused to a short unit are the weak spot. Call: **proceed with read-back**.
  See `docs/DECISIONS.md`.
- **Phase 2 — one callable number (English)** 🚧 — greet a known caller by shop name and
  hang up. Code built and verified offline; live telephony wiring pending.

> The codebase was rewritten from TypeScript/Next.js to Python (see `docs/DECISIONS.md`).
> The original TS implementation is kept locally in `legacy-ts/` (not in the repo).

## Stack

Python 3.13 · FastAPI · Pydantic v2 · SQLModel + Alembic · Postgres · uv · ruff ·
mypy (strict) · pytest · ElevenLabs Conversational AI + Scribe STT · Twilio.
Operator dashboard: Streamlit (Phase 4).

## Setup

```bash
uv sync
cp .env.example .env            # fill DATABASE_URL, AGENT_TOOL_SECRET, ELEVENLABS_*, TWILIO_*
openssl rand -hex 32            # -> AGENT_TOOL_SECRET (>=16 chars)
uv run alembic revision --autogenerate -m "initial" && uv run alembic upgrade head
uv run python scripts/seed.py
uv run uvicorn app.main:app --reload      # http://localhost:8000
```

Checks: `uv run pytest` · `uv run mypy app` · `uv run ruff check app tests scripts`.
For webhooks you need a public URL: `cloudflared tunnel --url http://localhost:8000`.
Verify Twilio before wiring: `uv run python scripts/verify_twilio.py`.

## Where things live

| Path | What |
|---|---|
| `CLAUDE.md` | Rules Claude Code reads every session |
| `docs/CONTEXT.md` | What this is, who calls, what it must not become |
| `docs/ROADMAP.md` | Phases. One per session. |
| `docs/DECISIONS.md` | Why things are the way they are |
| `agent/prompts/` | System prompts — versioned, not dashboard-configured |
| `agent/config/` | Agent config (voice, model), pushed by `scripts/sync_agent.py` |
| `app/api/` | FastAPI routes: agent tools + ElevenLabs webhooks |
| `app/tools/` | The six agent tools (registry + handlers) |
| `app/models.py` | Data model (Customer, Product, Order, CallLog) |
| `tests/fixtures/` | The golden utterance set + ASR spike results |

## Design invariants

Agent only drafts (a human confirms); never negotiates price or credit; never invents a
SKU, price, or stock level; tool endpoints answer in <500ms; quantities are read back
before drafting; English first, Bangla via the locale layer; secrets stay in `.env`;
raw phone numbers are never logged (hashed). Money is integer poisha; quantity is pieces.

## Limitations

Written before building, so it stays honest:

- Not validated with a real wholesaler yet
- Bangla ASR on numbers is measured but only on a small sample; the live streaming path
  may degrade further than the batch spike
- No payments, no accounting integration, no outbound calling
- Not production-ready
