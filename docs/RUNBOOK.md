# Runbook — running the agent (dev)

How to stand the system up, switch between the English and Bangla agents, and recover
after the machine/stack goes down. Ports: app `8000`, dashboard `8501`.

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
with. Whichever you sync **last** owns the number. Pass the tunnel URL so the agent's
tools point at your app:

```bash
# English
LANGUAGE_LOCALE=en PUBLIC_BASE_URL=https://<your-tunnel>.trycloudflare.com \
  uv run python scripts/sync_agent.py

# Bangla / Banglish
LANGUAGE_LOCALE=bn PUBLIC_BASE_URL=https://<your-tunnel>.trycloudflare.com \
  uv run python scripts/sync_agent.py
```
- The **first** `bn` sync prints `ELEVENLABS_AGENT_ID_BN=…` — add it to `.env` so later
  syncs update that agent instead of creating a new one. (`en` uses `ELEVENLABS_AGENT_ID`.)
- **Toggle languages** by re-running with the other `LANGUAGE_LOCALE`.

## When to re-sync
- After editing a prompt (`agent/prompts/system.{en,bn}.md`) or `agent/config/agent.config.json`.
- **After restarting the tunnel** (new URL) — re-sync the active locale so the tool
  webhooks point at the new tunnel URL.

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
