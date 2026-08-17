# Context

> Living document. Update it when reality changes. Claude reads this before
> touching product behaviour, so stale content here becomes wrong code.

## What this is

A voice agent that answers the phone for a garments **wholesaler** in Bangladesh
and takes reorders from retail shop owners.

Not a chatbot demo. The target is a system a real wholesaler could run on a real
phone line, and a portfolio artifact for an ElevenLabs Forward Deployed Engineer
application.

## Who is on the phone

Retail shop owners and their buyers reordering known stock. Characteristics:

- They are **repeat callers**. The system usually knows them by phone number.
- They order by **description and memory**, not SKU: "the black polo from last month".
- They speak **Banglish** — Bengali grammar, English nouns and numbers mixed in.
- They order in **dozens** (ডজন), sometimes hali (হালি, = 4), rarely single pieces.
- They will try to **negotiate price** and ask for **credit** (বাকি). Both escalate.

## Who is not on the phone

Export buyers placing tech-pack orders on a factory. That is a different business
with a months-long, document-driven process, and voice is the wrong interface for it.
If the scope drifts back toward export manufacturing, stop and re-read this section.

## Order lifecycle

    call → identify → resolve items → quantity → stock check → delivery
      → read back → DRAFT order → human review → CONFIRMED
      → email final offer → fulfilment

The agent owns everything up to `DRAFT`. A human owns the rest.

## Current status

The end-to-end flow works in English **and** Banglish: call → draft → human approval →
offer by SMS/email in the caller's language. See `docs/ROADMAP.md` for phase detail and
what's next.

## Language plan

English first. The whole flow must work end to end in English before any Bangla
work starts. Bangla is added through the locale layer, not by forking the flow.

Rationale: Bangla ASR quality is the single largest unknown in the project. Keeping
it isolated behind one boundary means a bad ASR result costs us one module, not the
whole build.

## Open questions

- [ ] Does the target wholesaler have digital inventory, or a paper khata?
      If paper, `check_stock` cannot exist and the flow changes.
- [ ] Telephony route for Bangladesh — Twilio number availability is poor.
      Demo on a US/UK number; real deployment may need local SIP or WhatsApp.
- [ ] Measured Banglish ASR accuracy on numbers. **Blocking.** See Phase 1.
- [ ] Who is the design partner? Named wholesaler > imagined one.

## Non-goals

- Payments and accounting integration
- Outbound calling
- Any claim that this is production-ready or clinically/financially validated
