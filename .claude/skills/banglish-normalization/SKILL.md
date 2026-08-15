---
name: banglish-normalization
description: Rules for parsing quantities, numbers, and units out of mixed Bengali-English speech, and the golden-set testing workflow. Use when editing src/lib/bangla/, adding utterance fixtures, or debugging a wrong quantity on an order.
---

# Banglish normalization

Quantity errors cost real money. This is the highest-risk module in the repo.
Treat every change as a correctness change, not a parsing convenience.

## What callers actually say

Bengali grammar with English nouns and freely mixed numerals:

- "তিন dozen black polo" — Bangla number, English unit and product
- "3 হালি medium size" — English numeral, Bangla unit
- "সাড়ে তিন ডজন" — "three and a half dozen" = 42 pieces
- "দেড় ডজন" — 1.5 dozen = 18 pieces. `দেড়` has no English cognate; hardcode it.
- "আড়াই" — 2.5. Same problem.
- Bengali digits ০১২৩৪৫৬৭৮৯ appear in typed input and sometimes in ASR output.

## Rules

1. **Normalize to pieces.** Always. Dozen ×12, hali ×4, gross ×144.
   Store pieces; display in the unit the caller used.
2. **Fractional multipliers are a closed set.** `দেড়` (1.5), `আড়াই` (2.5),
   `সাড়ে N` (N + 0.5). Anything else fractional → do not guess, ask.
3. **Never round silently.** If normalization yields a non-integer piece count,
   that is an error, not a rounding opportunity. Return a parse failure.
4. **Ambiguous bare numbers are not quantities.** "black polo, ten" — ten what?
   Ask. Do not default to pieces, and do not default to dozens.
5. **Return confidence.** The parser returns `{ pieces, unit, confidence }`.
   Low confidence must force a read-back, not a silent accept.

## Golden set workflow

`tests/fixtures/banglish-utterances.json` is the regression suite.

- Every real call that parses wrong gets added as a fixture **before** the fix.
- Fixtures record the *actual ASR output*, not the idealised transcription.
  The parser has to survive what the ASR really produces, including its errors.
- `pnpm test:utterances` must never regress. If a change improves one case and
  breaks another, that is not an improvement.

## What not to do

Do not "fix" quantity parsing by making the prompt ask more clarifying questions.
That trades a correctness bug for a call the shop owner hangs up on. Fix the parser.
