# CLAUDE.md

Voice reorder agent for a Bangladeshi garments wholesaler. Shop owners phone in,
the agent takes a reorder, a human approves it, the system emails a final offer.

**Stack: Python 3.13 · FastAPI · Pydantic v2 · SQLModel + Alembic · Postgres ·
uv · ruff · mypy (strict) · pytest.** Operator dashboard: Streamlit (Phase 4).
The previous TypeScript/Next.js implementation is preserved under `legacy-ts/`.

Read `docs/CONTEXT.md` at the start of any session that touches product behaviour.
Read `docs/ROADMAP.md` before starting a new phase.

## Invariants — never violate without asking

1. **The agent never confirms an order.** Every call produces a `DRAFT` order.
   Only a human moving it to `CONFIRMED` in the dashboard makes it real.
2. **The agent never negotiates price and never extends credit.** Both escalate.
3. **Never invent a SKU, price, or stock level.** If a tool returns nothing, say so.
4. **Every tool endpoint responds in under 500ms.** Slow tools break the call.
   No N+1 queries, no external API calls inside a tool handler.
5. **Quantities are always read back to the caller before the order is drafted.**
6. **English first, Bangla second.** Build and test the English path fully, then
   add Bangla via the locale layer. Never fork the codebase per language.
7. **Verify external APIs against live docs.** ElevenLabs and Twilio APIs change.
   Fetch current docs before writing integration code; do not trust memory or
   any pseudocode in this repo.
8. **Secrets never leave `.env`.** No keys in code, tests, fixtures, or logs.

## Conventions

- Python 3.13, fully type-annotated. `mypy` runs in strict mode and must pass.
  No `Any` — use precise types, `object` + narrowing, or `typing.cast` sparingly.
- Every tool input/output is a **Pydantic v2 model** in `app/schemas.py`.
  Schema first, then handler, then test.
- Money is integer poisha (`BDT * 100`). Never floats.
- Quantities are stored as pieces. Dozen/hali conversion happens at the edge,
  in `app/bangla/units.py` (Phase 3/5), never in business logic.
- Agent prompts live in `agent/prompts/*.md` and are versioned. Never configure
  agent behaviour only in the ElevenLabs dashboard — the repo is the source of
  truth, pushed by `scripts/sync_agent.py`.
- Tests colocate fixtures in `tests/fixtures/`. Add a fixture before fixing a bug.
- Async FastAPI routes; keep DB work inside the 500ms budget (one indexed query).

## Commit conventions

- Imperative mood, lowercase, no trailing period: `add stock check to draft flow`.
- Body explains **what changed and why**, never how it was produced.
- Never add `Co-Authored-By` trailers or tool attribution to commits or PRs.
- One logical change per commit. Do not bundle a refactor with a feature.
- Never commit `.env`, call recordings, or transcripts containing phone numbers.

## Commands

- `uv run uvicorn app.main:app --reload` — FastAPI dev server
- `uv run pytest` — tests
- `uv run pytest tests/test_utterances.py` — golden-set check on the Banglish normalizer (Phase 3)
- `uv run ruff check` / `uv run ruff format` — lint / format
- `uv run mypy app` — type check (strict)
- `uv run alembic upgrade head` — apply migrations; `uv run alembic revision --autogenerate -m "…"` to create one
- `uv run python scripts/seed.py` — seed the database
- `uv run python scripts/sync_agent.py` — push agent prompt + config to ElevenLabs
- `cloudflared tunnel --url http://localhost:8000` — expose localhost for ElevenLabs/Twilio webhooks

## Definition of done

A change is done when: `mypy` passes, `pytest` passes, the golden utterance set does
not regress, and `docs/DECISIONS.md` records any non-obvious choice.

## Compact instructions

When summarizing this conversation, always preserve:
- The list of modified files
- Any ElevenLabs/Twilio API details fetched from live docs this session
- Failing test names and their causes
- Decisions not yet written to `docs/DECISIONS.md`
Summarize file exploration briefly; drop it entirely once the relevant file is open.

## Working agreement

- Use plan mode for anything touching the call flow or the data model.
- Delegate codebase research to subagents so the main context stays clean.
- Ask before adding a dependency.
- Do not refactor the working demo path (`app/api/tools.py`, `app/api/webhooks.py`)
  as a side effect of another task. It is the demo, and the demo is the product.
