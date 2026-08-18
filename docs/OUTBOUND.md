# Outbound calls

Place a call **from** the agent **to** any number, so a tester hears the agent without
paying. The Twilio + ElevenLabs cost lands on *your* account.

> This is a **demo / test convenience, not the product.** The caller-facing product is
> inbound only — shop owners phone *in* (`docs/CONTEXT.md` lists product outbound calling
> as a non-goal). Use this to let an overseas tester experience the agent, or to smoke-test
> a change without dialing in yourself.

## Command
```bash
uv run python scripts/outbound_call.py +14155551234     # destination in E.164 (+countrycode…)
```
On success it prints:
```
Calling +1415… from +12362054231 (agent agent_6501…)...
success conversation_id=conv_… callSid=CA…
```
The callee's phone rings; when they answer, the agent greets with its `first_message` and
runs the **same flow and tools as an inbound call** (identify → search catalog → stock →
read-back → draft). The draft lands in the dashboard exactly like an inbound order.

## Prerequisites
1. **The stack is live** — run `uv run python scripts/serve.py` first. Outbound uses the
   same order tools, so they must point at a running tunnel; if `serve.py` isn't up, the
   agent will greet but fail at the first tool ("having trouble…"). Any locale's `serve.py`
   run refreshes the shared tools' URL, so whichever one is running is fine.
2. **A Twilio number imported into ElevenLabs** (the script picks it automatically).
3. **`.env`** has `ELEVENLABS_API_KEY` and `ELEVENLABS_AGENT_ID`.
4. **Twilio geographic permissions** allow the destination country. International dialing is
   **off by default** — enable the country in the Twilio Console under
   *Voice → Settings → Geographic Permissions*, or the call returns `success=false` with a
   geo-permission message. (Bangladesh, +880, had to be enabled this way.)

## Language of the outbound call
The script always calls with **`ELEVENLABS_AGENT_ID`** — the **English** agent — regardless
of which agent currently answers the inbound number. To place a **Bangla** outbound call,
point it at the bn agent, e.g. temporarily set `ELEVENLABS_AGENT_ID` to the bn id for the
run:
```bash
ELEVENLABS_AGENT_ID=agent_2901m06r30q4f94bfdmjfg7bamqv uv run python scripts/outbound_call.py +14155551234
```
(The `agent_id` passed to the call — not the number's inbound assignment — decides which
agent, prompt, and language the tester hears.)

## How it works
`scripts/outbound_call.py`:
1. lists your ElevenLabs phone numbers, prefers the Twilio one assigned to
   `ELEVENLABS_AGENT_ID` (else the first Twilio number),
2. calls `POST /v1/convai/twilio/outbound-call` with `agent_id`,
   `agent_phone_number_id`, and `to_number`,
3. prints the `conversation_id` and Twilio `callSid`.

ElevenLabs then drives Twilio to dial out and bridges the answered call to the agent — the
agent speaks first, as if it had answered, which is why an outbound call *feels* inverted
compared to inbound even though the conversation logic is identical.

## After the call
- **Transcript:** find it by the printed `conversation_id` in the ElevenLabs dashboard, or
  `GET /v1/convai/conversations/{conversation_id}`.
- **Order:** any draft appears in the operator dashboard (`dashboard/main.py`) like any other.

## Troubleshooting
| Symptom | Cause / fix |
|---|---|
| `success=false`, geo message | Destination country not permitted — enable it in Twilio *Geographic Permissions*. |
| `No Twilio number imported` | Import your Twilio number into ElevenLabs first. |
| Agent answers but tools fail mid-call | `serve.py` not running, or tools point at a dead tunnel — start/re-run `serve.py`. |
| `ELEVENLABS_API_KEY and ELEVENLABS_AGENT_ID must be set` | Fill both in `.env`. |
| Wrong language on the call | It uses `ELEVENLABS_AGENT_ID`; override it to the bn agent id for a Bangla call. |

## Cost & etiquette
Every outbound call bills your Twilio + ElevenLabs accounts. Only dial numbers whose owner
expects the call — this is for consenting testers, not cold outreach.
