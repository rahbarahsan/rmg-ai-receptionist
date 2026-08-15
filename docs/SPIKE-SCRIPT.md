# Phase 1 — ASR spike recording script

Twenty utterances. Read them aloud, save twenty audio files, run one command.
The whole thing takes about 40 minutes and decides whether this project is real.

**What you are measuring:** does the transcription preserve the *number*?
Product names are secondary — a fuzzy resolver can recover "black polo" from
"black polo shirt". Nothing recovers 3 from 30.

---

## How to record

**Device.** Your phone, held normally at your ear. Not a USB mic, not AirPods
close-miked. The demo is a phone call, so the spike has to sound like a phone call.

**Format.** Whatever your recorder produces (.m4a, .wav, .mp3 all work). Do not
clean, normalise, or noise-reduce anything. Artifacts are the point.

**Delivery.** Say each line at the speed a busy shop owner would say it into a
phone — faster than you think, slightly clipped. Do **not** dictate. If you catch
yourself over-enunciating the numbers, delete the take and do it again; that is
exactly the bias that makes a spike lie to you.

**Conditions.** Record 15 in a quiet room. Record the last 5 (marked `noisy`) with
a fan on, a TV playing, or standing near traffic. Real calls come from shop floors.

**Ideally, not your voice.** If you can get a native Bangladeshi speaker to read
these, do that instead. You know what the sentences are supposed to say, and that
leaks into your pronunciation in ways ASR does not forgive in real callers.

**Naming.** One file per utterance, named exactly by its ID:

    recordings/spike/01-en-baseline.m4a
    recordings/spike/02-bn-num-en-unit.m4a
    ...

The runner matches files to expected values by that leading ID. If a name is
wrong the case is reported as missing, not as a failure.

---

## The script

Read the **Bangla/Banglish** column. The romanisation is a pronunciation aid only.

### Quiet room (1–15)

| ID | Say this | Roman | Means | Expect |
|---|---|---|---|---|
| `01-en-baseline` | three dozen black polo, medium | — | 3 dz | **36** |
| `02-bn-num-en-unit` | তিন dozen black polo দেন | tin dozen black polo den | 3 dz | **36** |
| `03-en-num-bn-unit` | 5 হালি medium size | five hali medium size | 5 hali | **20** |
| `04-full-bangla` | চার ডজন কালো পোলো লাগবে | char dozen kalo polo lagbe | 4 dz | **48** |
| `05-share` | সাড়ে তিন ডজন সাদা গেঞ্জি | shaŗe tin dozen shada genji | 3.5 dz | **42** |
| `06-der` | দেড় ডজন পাঞ্জাবি দেন | deŗ dozen panjabi den | 1.5 dz | **18** |
| `07-arai` | আড়াই ডজন লার্জ সাইজ | aŗai dozen large size | 2.5 dz | **30** |
| `08-teen-number` | বারো ডজন white tee | baro dozen white tee | 12 dz | **144** |
| `09-larger` | পঁচিশ ডজন কালো পোলো | pochish dozen kalo polo | 25 dz | **300** |
| `10-mixed-order` | black polo তিন ডজন আর white tee দুই ডজন | black polo tin dozen ar white tee dui dozen | 3 dz + 2 dz | **36 + 24** |
| `11-correction` | তিন ডজন... না না, চার ডজন | tin dozen... na na, char dozen | corrects to 4 dz | **48** |
| `12-ambiguous-unit` | কালো পোলো দশটা | kalo polo doshta | "ten" of what? | **ask** |
| `13-no-quantity` | black polo লাগবে | black polo lagbe | no number | **ask** |
| `14-price-push` | দাম একটু কমান না ভাই | dam ektu koman na bhai | haggling | **escalate** |
| `15-credit` | এবারের টা বাকিতে দেন | ebarer ta bakite den | credit request | **escalate** |

### Noisy (16–20)

| ID | Say this | Roman | Means | Expect |
|---|---|---|---|---|
| `16-noisy-simple` | ছয় ডজন কালো পোলো | choy dozen kalo polo | 6 dz | **72** |
| `17-noisy-share` | সাড়ে পাঁচ ডজন | shaŗe pañch dozen | 5.5 dz | **66** |
| `18-noisy-fast` | দশ ডজন লার্জ, তাড়াতাড়ি পাঠান | dosh dozen large, taŗataŗi pathan | 10 dz | **120** |
| `19-noisy-mixed` | 8 ডজন white tee, medium | eight dozen white tee medium | 8 dz | **96** |
| `20-noisy-hali` | সাত হালি দিলেই হবে | shat hali dilei hobe | 7 hali | **28** |

---

## A note on Bengali digits

You will see `৫` vs `5` discussed in the code. That distinction does **not** exist
in speech — it only appears in how the ASR chooses to write the number down.
Record naturally and let the transcript show you which it produces. That answer
is itself a finding worth recording in `docs/DECISIONS.md`.

---

## Running it

    cp .env.example .env         # add ELEVENLABS_API_KEY (Speech to Text scope only)
    pnpm install
    pnpm spike

Output: a per-utterance table, a **number accuracy** figure, and a written report
at `docs/spike-report.md`.

## Reading the result

Number accuracy is the only figure that matters.

- **Above 90%** — proceed to Phase 2 as planned.
- **70–90%** — proceed, but the parser needs a confidence threshold and the agent
  must read back every quantity. It already does; now you know why.
- **Below 70%** — stop and reconsider. Options: constrain callers to English
  numbers, add a digit-confirmation step ("that's three-six pieces, correct?"),
  or move the product to WhatsApp voice notes where you can re-listen.

A bad result here is a good outcome. It costs you one afternoon instead of three
weeks, and "I measured it, it failed, here's what I changed" is a stronger story
than a demo that works on rehearsed input.
