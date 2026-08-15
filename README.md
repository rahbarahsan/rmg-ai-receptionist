# Reorder Line

A voice agent that answers the phone for a garments wholesaler in Bangladesh and
takes reorders from retail shop owners in mixed Bengali–English speech.

The agent prepares orders. A human confirms them. Nothing ships on an AI's say-so.

## Status

Phase 0 — scaffold. Nothing works yet. See `docs/ROADMAP.md`.

## Stack

Next.js 15 · TypeScript · Postgres + Prisma · Zod · Vitest · ElevenLabs Agents · Twilio

## Setup

```bash
pnpm install
cp .env.example .env          # fill in DATABASE_URL and AGENT_TOOL_SECRET
openssl rand -hex 32          # -> AGENT_TOOL_SECRET
pnpm db:push && pnpm db:seed
pnpm dev
```

For webhooks you need a public URL: `pnpm tunnel`, then point the agent at it.

## Where things live

| Path | What |
|---|---|
| `CLAUDE.md` | Rules Claude Code reads every session |
| `docs/CONTEXT.md` | What this is, who calls, what it must not become |
| `docs/ROADMAP.md` | Phases. One per session. |
| `docs/DECISIONS.md` | Why things are the way they are |
| `agent/prompts/` | System prompts — versioned, not dashboard-configured |
| `src/lib/bangla/` | Quantity parsing. Highest-risk code in the repo. |
| `src/lib/tools/` | The six agent tools |
| `tests/fixtures/` | The golden utterance set |

## Limitations

Written before building, so it stays honest:

- Not validated with a real wholesaler yet
- Bangla ASR accuracy on numbers is unmeasured and may not be good enough
- No payments, no accounting integration, no outbound calling
- Not production-ready
