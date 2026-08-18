# Extending

The system is built so the common changes — a new language, new products, a new market —
are **data edits, not code forks** (CLAUDE.md invariant 6). The tools, the database, the
call route, and the dashboard are all language- and catalog-agnostic.

## Add a language (3 steps)

Say you want Hindi (`hi`). The backend already speaks in canonical units and cents; only the
spoken aliases and the written offer differ per language.

1. **Write the prompt** — `agent/prompts/system.hi.md`. Copy `system.en.md` and translate the
   flow. Keep the two non-negotiables: the **mandatory quantity read-back** (restate the
   unit and, for dozen/hali/gross, the exact piece equivalent) and *never invent a
   SKU/price/stock*.

2. **Add a locale block** — in `agent/config/agent.config.json` under `locales`:
   ```json
   "hi": {
     "prompt_file": "agent/prompts/system.hi.md",
     "language": "hi",
     "tts_model": "eleven_v3_conversational",
     "first_message": "<greeting in Hindi>"
   }
   ```
   Pick a TTS model that supports the language — verify against the ElevenLabs `GET /v1/models`
   list (only some models speak non-English; Bengali needed `eleven_v3_conversational`).

3. **Register the locale** — add one `Locale` entry in `app/locale/registry.py`:
   ```python
   "hi": Locale("hi", "Hindi", _HI_UNIT_ALIASES, _render_offer_hi, _subject_hi),
   ```
   with the spoken unit aliases (Hindi words → `piece`/`hali`/`dozen`/`gross`) and an offer
   template + email subject in Hindi. That's the *only* code touched.

Then bring it up: `uv run python scripts/serve.py hi`. The number now answers in Hindi, using
the same tools, catalog, DB, dashboard, and offer pipeline. `tests/test_locale.py` guards that
every registered locale renders correctly.

> The agent passes its `locale` to `create_draft_order`, which is stored on the customer, so
> the written offer (SMS/email) comes out in the caller's language automatically.

## Add or change products

Edit the catalog and reseed (`scripts/seed.py`), or insert `Product` rows. Each product has a
`name_en`, an optional `name_bn` (used in that language's offer), `aliases` (spoken forms in
any language — this is what `search_catalog` matches against), a `category`, `color`, `size`,
an integer `unit_price` (US cents), and `stock_pcs`. No code changes — search and drafting are
catalog-driven.

## Add an offer channel

`app/notify.py` dispatches on `order.offer_channel`. Add a `send_<channel>` function and a
branch in `send_offer`. The body already renders per locale via the registry.

## What is intentionally *not* pluggable yet

- **Per-locale product names at scale** — today a product carries `name_en` + optional
  `name_bn`. A third display language would want a `name_localized` JSON or a translations
  table (a small migration). The offer already selects the name by locale, so the seam is
  there.
- **Currency** — money is US cents throughout (demo choice, see `DECISIONS.md`). A second
  currency would generalize `usd()` in `app/locale/registry.py`.
