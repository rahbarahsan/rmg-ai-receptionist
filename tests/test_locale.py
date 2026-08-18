from app.locale.registry import (
    LOCALES,
    OfferData,
    OfferLine,
    all_unit_aliases,
    get_locale,
    usd,
)


def test_get_locale_known_and_default() -> None:
    assert get_locale("bn").code == "bn"
    assert get_locale("EN").code == "en"  # case-insensitive
    assert get_locale("xx").code == "en"  # unknown falls back to default
    assert get_locale(None).code == "en"


def test_merged_unit_aliases_span_languages() -> None:
    merged = all_unit_aliases()
    # Bangla and English spoken forms both resolve to the same canonical unit.
    assert merged["ডজন"] == "dozen"
    assert merged["dozen"] == "dozen"
    assert merged["হালি"] == "hali"
    assert merged["গ্রোস"] == "gross"


def test_usd_formats_cents() -> None:
    assert usd(125000) == "$1,250.00"
    assert usd(400) == "$4.00"


def _offer() -> OfferData:
    return OfferData(
        shop="Test Shop",
        lines=[OfferLine(qty_pcs=18, name="Black polo", unit_price_cents=450)],
        total_cents=8100,
        delivery_note=None,
    )


def test_offer_renders_per_locale() -> None:
    en = get_locale("en").render_offer(_offer())
    assert "Total: $81.00" in en
    assert "18 pcs Black polo @ $4.50 = $81.00" in en

    bn = get_locale("bn").render_offer(_offer())
    assert "মোট: $81.00" in bn
    assert "18 পিস" in bn


def test_every_locale_is_well_formed() -> None:
    # Guards the extension point: each registered Locale renders + subjects without error.
    for code, loc in LOCALES.items():
        assert loc.code == code
        assert loc.render_offer(_offer())
        assert loc.offer_subject("Test Shop")
