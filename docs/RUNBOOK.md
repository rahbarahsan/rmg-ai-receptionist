# Runbook — running the agent (dev)

How to stand the system up, switch between the English and Bangla agents, and recover
after the machine/stack goes down. Ports: app `8000`, dashboard `8501`.

## Quick start — one command

```bash
uv run python scripts/serve.py        # English (default)
uv run python scripts/serve.py bn     # Bangla / Banglish
```

This is the everyday path. It starts the app, opens the tunnel, **reads the tunnel URL
for you**, syncs that language's agent + order tools, and points the phone number at it —
then holds it all open. **Ctrl+C** stops. To **switch languages**, stop it and re-run with
the other locale. You never copy a tunnel URL or set an env var by hand.

The dashboard (order review) is separate — start it once in its own terminal:
```bash
uv run streamlit run dashboard/main.py --server.headless true --server.port 8501
```

Needs `cloudflared` — found on PATH, else `$CLOUDFLARED_PATH`, else `.tools/cloudflared.exe`.
Install once with `winget install --id Cloudflare.cloudflared`.

> First `bn` run: add the printed `ELEVENLABS_AGENT_ID_BN=…` to `.env` so it updates that
> agent in place instead of creating a new one.

The rest of this doc is the **manual breakdown** — useful for debugging, or if you want to
run the pieces yourself. `serve.py` just automates all of it.

## The pieces
| Piece | Command | Notes |
|---|---|---|
| Postgres | (service) | Holds the catalog + orders. Data persists across restarts. |
| App (FastAPI) | `uv run uvicorn app.main:app --port 8000 --reload` | Serves the agent tool webhooks. |
| Tunnel | `cloudflared tunnel --url http://localhost:8000` | Public HTTPS URL ElevenLabs calls. Prints a `https://…trycloudflare.com` URL — that's `PUBLIC_BASE_URL`. Ephemeral: a **new URL each run**. |
| Dashboard | `uv run streamlit run dashboard/main.py --server.headless true --server.port 8501` | Review + approve orders at http://localhost:8501 |

Install the tunnel once: `winget install --id Cloudflare.cloudflared` (or use ngrok).

## First-time setup
```bash
uv sync                                   # install deps
createdb -U postgres reorder_line         # create the DB (set DATABASE_URL in .env to match)
uv run python scripts/seed.py             # tables + 15-SKU catalog
```
Fill `.env` (see `.env.example`). `AGENT_TOOL_SECRET`: `openssl rand -hex 32`.

## Start everything
Run each in its own terminal (or background):
```bash
uv run uvicorn app.main:app --port 8000 --reload
cloudflared tunnel --url http://localhost:8000        # copy the printed https URL
uv run streamlit run dashboard/main.py --server.headless true --server.port 8501
```

## Pick the language (sync the agent)
`LANGUAGE_LOCALE` selects which agent to build **and** which one the phone number answers
with. Whichever you sync **last** owns the number.

> ⚠️ **Always pass `PUBLIC_BASE_URL` on the same line.** The order tools need the public
> webhook URL, so without it a *fresh* sync gives the agent only `end_call` — it can talk
> but can't take an order (nothing reaches the dashboard). Copy the whole line, including
> the `PUBLIC_BASE_URL=…` prefix — don't copy just the `uv run …` part.
> (Safety net: on a sync that *updates* an existing agent, the script now **preserves the
> order tools already attached** even if you forget the URL — but it can't attach them the
> first time, and the URL will be stale until you re-sync after a tunnel restart.)

Single line each — run whichever language you want:
```bash
LANGUAGE_LOCALE=en PUBLIC_BASE_URL=https://<your-tunnel>.trycloudflare.com uv run python scripts/sync_agent.py
LANGUAGE_LOCALE=bn PUBLIC_BASE_URL=https://<your-tunnel>.trycloudflare.com uv run python scripts/sync_agent.py
```
- The **first** `bn` sync prints `ELEVENLABS_AGENT_ID_BN=…` — add it to `.env` so later
  syncs update that agent instead of creating a new one. (`en` uses `ELEVENLABS_AGENT_ID`.)
- **Toggle languages** by re-running with the other `LANGUAGE_LOCALE`. Any sync (even a
  bare one) re-points the number at the locale it ran, so don't run it unless you mean to
  switch the live number.

## When to re-sync
- After editing a prompt (`agent/prompts/system.{en,bn}.md`) or `agent/config/agent.config.json`.
- **After restarting the tunnel** (new URL) — re-sync the active locale **with the new
  `PUBLIC_BASE_URL`** so the tool webhooks point at the live tunnel.

## Verify the agent has its tools (after any sync)
An agent with 0 order tools can greet but never drafts an order. Quick check:
```bash
uv run python scripts/verify_elevenlabs.py     # or GET /v1/convai/agents/{id} and count prompt.tool_ids
```
Expect **4** tools (`search_catalog`, `check_stock`, `create_draft_order`, `escalate_to_human`).
If it's 0, re-sync that locale **with `PUBLIC_BASE_URL`**.

## Recover after the stack goes down
The DB persists; only the processes need restarting:
1. Start app + tunnel + dashboard again (the tunnel gets a **new** URL).
2. Re-sync the language you want with the new `PUBLIC_BASE_URL` (updates the tool URLs +
   re-points the number). Example: `LANGUAGE_LOCALE=bn PUBLIC_BASE_URL=<new-url> uv run python scripts/sync_agent.py`.

## Test
- **Inbound:** call the Twilio number and place an order → it appears in the dashboard as
  DRAFT → **Approve & send offer**.
- **Outbound demo:** `uv run python scripts/outbound_call.py +<E.164 number>`.
- **Pull a transcript:** conversations are in the ElevenLabs dashboard, or via the
  `/v1/convai/conversations` API.

## Credential checks
```bash
uv run python scripts/verify_twilio.py        # Twilio auth + number is voice/SMS capable
uv run python scripts/verify_elevenlabs.py    # ElevenLabs key can manage agents
```

## Quality gate
```bash
uv run ruff check app tests scripts dashboard
uv run ruff format app tests scripts dashboard
uv run mypy app
uv run pytest
```

## Notes / gotchas
- **Bangla TTS** needs `eleven_v3_conversational` (the only convai model that speaks
  Bengali); it requires Expressive TTS enabled on the ElevenLabs account.
- **Email** sends via Gmail SMTP (`GMAIL_ADDRESS` + base64 `GMAIL_APP_PASSWORD`) — works to
  any recipient, no domain needed. **SMS** via Twilio.
- `.env` is gitignored; never commit real secrets. `.env.example` is the committed template.
