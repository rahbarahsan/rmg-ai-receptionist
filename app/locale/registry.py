"""Per-language configuration — the one place you add a language.

Adding a language is three data edits, no business-logic fork (CLAUDE.md invariant 6):
  1. a prompt file  `agent/prompts/system.<code>.md`
  2. a locale block in `agent/config/agent.config.json`
  3. a `Locale` entry in `LOCALES` below (spoken unit aliases + offer wording)

The tools, catalog, and database are language-agnostic; only the spoken unit aliases
and the written offer vary between languages, and both live here.
"""

from collections.abc import Callable
from dataclasses import dataclass


def usd(cents: int) -> str:
    """Format integer US cents as `$X.XX`. Money is always integer cents, never float."""
    return f"${cents / 100:,.2f}"


@dataclass(frozen=True)
class OfferLine:
    qty_pcs: int
    name: str
    unit_price_cents: int

    @property
    def line_total_cents(self) -> int:
        return self.qty_pcs * self.unit_price_cents


@dataclass(frozen=True)
class OfferData:
    """Everything an offer template needs — assembled from the order, language-agnostic."""

    shop: str
    lines: list[OfferLine]
    total_cents: int
    delivery_note: str | None


@dataclass(frozen=True)
class Locale:
    code: str  # ISO-ish short code used in .env, agent config, and Customer.locale
    name: str  # human name, for docs/dashboards
    unit_aliases: dict[str, str]  # spoken unit -> canonical (piece|hali|dozen|gross)
    render_offer: Callable[[OfferData], str]  # the written offer body in this language
    offer_subject: Callable[[str], str]  # email subject, given the shop name


# --- English -----------------------------------------------------------------

_EN_UNIT_ALIASES = {
    "piece": "piece",
    "pieces": "piece",
    "pcs": "piece",
    "pc": "piece",
    "hali": "hali",
    "dozen": "dozen",
    "dozens": "dozen",
    "doz": "dozen",
    "gross": "gross",
}


def _render_offer_en(d: OfferData) -> str:
    lines = [f"RMG Wholesale — order for {d.shop}", ""]
    for it in d.lines:
        unit, total = usd(it.unit_price_cents), usd(it.line_total_cents)
        lines.append(f"- {it.qty_pcs} pcs {it.name} @ {unit} = {total}")
    lines += ["", f"Total: {usd(d.total_cents)}"]
    if d.delivery_note:
        lines.append(f"Delivery: {d.delivery_note}")
    lines.append("The sales desk will confirm delivery and payment terms shortly.")
    return "\n".join(lines)


def _subject_en(shop: str) -> str:
    return f"Your order — {shop}"


# --- Bangla ------------------------------------------------------------------

_BN_UNIT_ALIASES = {
    "পিস": "piece",
    "পিছ": "piece",
    "piece": "piece",
    "pieces": "piece",
    "pcs": "piece",
    "হালি": "hali",
    "hali": "hali",
    "ডজন": "dozen",
    "ডজ": "dozen",
    "dozen": "dozen",
    "গ্রোস": "gross",
    "gross": "gross",
}


def _render_offer_bn(d: OfferData) -> str:
    lines = [f"RMG Wholesale — {d.shop} এর অর্ডার", ""]
    for it in d.lines:
        unit, total = usd(it.unit_price_cents), usd(it.line_total_cents)
        lines.append(f"- {it.qty_pcs} পিস {it.name} @ {unit} = {total}")
    lines += ["", f"মোট: {usd(d.total_cents)}"]
    if d.delivery_note:
        lines.append(f"ডেলিভারি: {d.delivery_note}")
    lines.append("সেলস ডেস্ক একটু পরে ডেলিভারি আর পেমেন্ট কনফার্ম করে জানাবে।")
    return "\n".join(lines)


def _subject_bn(shop: str) -> str:
    return f"আপনার অর্ডার — {shop}"


# --- Registry ----------------------------------------------------------------

DEFAULT_LOCALE = "en"

LOCALES: dict[str, Locale] = {
    "en": Locale("en", "English", _EN_UNIT_ALIASES, _render_offer_en, _subject_en),
    "bn": Locale("bn", "Bangla", _BN_UNIT_ALIASES, _render_offer_bn, _subject_bn),
}


def get_locale(code: str | None) -> Locale:
    """The Locale for a code, falling back to the default for unknown/empty codes."""
    return LOCALES.get((code or "").strip().lower(), LOCALES[DEFAULT_LOCALE])


def all_unit_aliases() -> dict[str, str]:
    """Every locale's spoken→canonical unit map, merged. A caller who mixes languages
    (English unit words in a Bangla sentence) still resolves against the union."""
    merged: dict[str, str] = {}
    for loc in LOCALES.values():
        merged.update(loc.unit_aliases)
    return merged
