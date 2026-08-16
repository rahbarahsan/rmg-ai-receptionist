from collections.abc import Iterator

import pytest
from sqlmodel import Session, SQLModel, create_engine

from app.models import Product
from app.schemas import (
    CheckStockInput,
    CreateDraftOrderInput,
    DraftItem,
    EscalateInput,
    SearchCatalogInput,
)
from app.tools import handlers


@pytest.fixture
def session() -> Iterator[Session]:
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False})
    SQLModel.metadata.create_all(engine)
    with Session(engine) as s:
        s.add(
            Product(
                sku="PLO-BLK-M",
                name_en="Black polo shirt (M)",
                category="polo",
                color="black",
                size="M",
                aliases=["black polo"],
                unit_price=400,
                stock_pcs=480,
            )
        )
        s.add(
            Product(
                sku="TEE-WHT-M",
                name_en="White tee (M)",
                category="tee",
                color="white",
                size="M",
                aliases=["white tee"],
                unit_price=200,
                stock_pcs=1200,
            )
        )
        s.commit()
        yield s


def test_search_ranks_black_polo(session: Session) -> None:
    r = handlers.search_catalog(session, SearchCatalogInput(query="black polo medium"))
    assert r["ok"] is True
    assert r["data"]["candidates"][0]["sku"] == "PLO-BLK-M"  # type: ignore[index]


def test_search_no_match(session: Session) -> None:
    r = handlers.search_catalog(session, SearchCatalogInput(query="green jacket"))
    assert r == {"ok": False, "reason": "no matching product"}


def test_check_stock(session: Session) -> None:
    r = handlers.check_stock(session, CheckStockInput(sku="PLO-BLK-M"))
    assert r["ok"] is True
    assert r["data"]["stock_pcs"] == 480  # type: ignore[index]


def test_check_stock_unknown(session: Session) -> None:
    r = handlers.check_stock(session, CheckStockInput(sku="NOPE"))
    assert r["ok"] is False


def test_create_draft_order(session: Session) -> None:
    data = CreateDraftOrderInput(
        shop_name="AK&M",
        contact_name="Lila",
        items=[DraftItem(sku="PLO-BLK-M", amount=3, unit="dozen", spoken_qty="three dozen")],
    )
    r = handlers.create_draft_order(session, data)
    assert r["ok"] is True
    assert r["data"]["total_cents"] == 36 * 400  # type: ignore[index]
    assert r["data"]["total"] == "$144.00"  # type: ignore[index]
    assert r["data"]["items"][0]["qty_pcs"] == 36  # type: ignore[index]


def test_create_draft_unknown_sku(session: Session) -> None:
    data = CreateDraftOrderInput(
        shop_name="X",
        items=[DraftItem(sku="NOPE", amount=1, unit="dozen", spoken_qty="one dozen")],
    )
    r = handlers.create_draft_order(session, data)
    assert r["ok"] is False and "unknown sku" in str(r["reason"])


def test_create_draft_bad_unit(session: Session) -> None:
    data = CreateDraftOrderInput(
        shop_name="X",
        items=[DraftItem(sku="PLO-BLK-M", amount=1, unit="widgets", spoken_qty="one widget")],
    )
    r = handlers.create_draft_order(session, data)
    assert r["ok"] is False and "unknown unit" in str(r["reason"])


def test_escalate(session: Session) -> None:
    r = handlers.escalate_to_human(session, EscalateInput(reason="price_negotiation"))
    assert r["ok"] is True
