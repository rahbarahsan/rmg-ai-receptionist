"""Tool handlers. Latency budget per handler: 500ms. No external HTTP calls in here.

Every handler takes a DB session + a validated Pydantic input and returns a ToolResult
dict ({ok, data} | {ok, reason}). Invariants: never invent a SKU/price/stock; the agent
only drafts; quantity→pieces conversion goes through app.bangla.units.
"""

import logging
import re

from pydantic import BaseModel
from sqlmodel import Session, col, select

from app.bangla.units import normalize_unit, to_pieces
from app.customers import lookup_customer_by_phone
from app.models import Customer, Order, OrderItem, OrderStatus, Product
from app.phone import normalize_phone
from app.schemas import (
    CheckStockInput,
    CreateDraftOrderInput,
    EscalateInput,
    LookupCustomerInput,
    SearchCatalogInput,
)

logger = logging.getLogger("reorder.tools")

ToolResult = dict[str, object]

_SIZE_SYNONYMS = {"s": "small", "m": "medium", "l": "large", "xl": "extra large", "xxl": "double"}


def _tokens(text: str) -> list[str]:
    return [t for t in re.split(r"[^a-z0-9]+", text.lower()) if t]


def lookup_customer(session: Session, data: BaseModel) -> ToolResult:
    assert isinstance(data, LookupCustomerInput)
    result = lookup_customer_by_phone(session, data.phone)
    if not result.is_known:
        return {"ok": False, "reason": "unknown_caller"}
    return {
        "ok": True,
        "data": {
            "customer_id": result.id,
            "shop_name": result.shop_name,
            "contact_name": result.contact_name,
            "locale": result.locale,
        },
    }


def search_catalog(session: Session, data: BaseModel) -> ToolResult:
    assert isinstance(data, SearchCatalogInput)
    query_tokens = _tokens(data.query)
    if not query_tokens:
        return {"ok": False, "reason": "empty query"}

    products = session.exec(select(Product).where(col(Product.is_active).is_(True))).all()
    scored: list[tuple[int, Product]] = []
    for p in products:
        size_syn = _SIZE_SYNONYMS.get(p.size.lower(), "")
        hay = " ".join([p.name_en, p.category, p.color, p.size, size_syn, *p.aliases]).lower()
        score = sum(1 for t in query_tokens if t in hay)
        if score > 0:
            scored.append((score, p))

    scored.sort(key=lambda sp: (sp[0], sp[1].stock_pcs), reverse=True)
    top = scored[: data.limit]
    if not top:
        return {"ok": False, "reason": "no matching product"}
    return {
        "ok": True,
        "data": {
            "candidates": [
                {
                    "sku": p.sku,
                    "name": p.name_en,
                    "color": p.color,
                    "size": p.size,
                    "unit_price_poisha": p.unit_price,
                    "stock_pcs": p.stock_pcs,
                }
                for _, p in top
            ]
        },
    }


def check_stock(session: Session, data: BaseModel) -> ToolResult:
    assert isinstance(data, CheckStockInput)
    product = session.exec(select(Product).where(Product.sku == data.sku)).first()
    if product is None:
        return {"ok": False, "reason": "unknown sku"}
    return {
        "ok": True,
        "data": {
            "sku": product.sku,
            "stock_pcs": product.stock_pcs,
            "is_active": product.is_active,
        },
    }


def create_draft_order(session: Session, data: BaseModel) -> ToolResult:
    assert isinstance(data, CreateDraftOrderInput)

    customer = _find_or_create_customer(session, data.shop_name, data.contact_name, data.phone)
    order = Order(
        customer_id=customer.id,
        status=OrderStatus.DRAFT,
        delivery_note=data.delivery_note,
        call_id=data.call_id,
    )
    session.add(order)

    total = 0
    summary: list[dict[str, object]] = []
    for item in data.items:
        product = session.exec(select(Product).where(Product.sku == item.sku)).first()
        if product is None:
            session.rollback()
            return {"ok": False, "reason": f"unknown sku {item.sku}"}
        unit = normalize_unit(item.unit)
        if unit is None:
            session.rollback()
            return {"ok": False, "reason": f"unknown unit '{item.unit}'"}
        qty_pcs = to_pieces(item.amount, unit)
        if qty_pcs is None:
            session.rollback()
            return {"ok": False, "reason": f"{item.amount} {item.unit} is not a whole piece count"}

        session.add(
            OrderItem(
                order_id=order.id,
                product_id=product.id,
                qty_pcs=qty_pcs,
                spoken_qty=item.spoken_qty,
                spoken_unit=unit,
                unit_price_pois=product.unit_price,
                confidence=item.confidence,
            )
        )
        total += qty_pcs * product.unit_price
        summary.append(
            {
                "sku": product.sku,
                "name": product.name_en,
                "qty_pcs": qty_pcs,
                "spoken": item.spoken_qty,
            }
        )

    order.total_poisha = total
    session.add(order)
    session.commit()
    return {
        "ok": True,
        "data": {
            "order_id": order.id,
            "status": "DRAFT",
            "shop_name": customer.shop_name,
            "total_poisha": total,
            "items": summary,
        },
    }


def escalate_to_human(session: Session, data: BaseModel) -> ToolResult:
    assert isinstance(data, EscalateInput)
    logger.warning(
        "ESCALATION reason=%s detail=%s call_id=%s", data.reason, data.detail, data.call_id
    )
    return {"ok": True, "data": {"escalated": True, "reason": data.reason}}


def not_implemented(session: Session, data: BaseModel) -> ToolResult:
    return {"ok": False, "reason": "not implemented"}


def _find_or_create_customer(
    session: Session, shop_name: str, contact_name: str | None, phone: str | None
) -> Customer:
    if phone:
        normalized = normalize_phone(phone)
        by_phone = session.exec(select(Customer).where(Customer.phone == normalized)).first()
        if by_phone is not None:
            return by_phone

    by_shop = session.exec(select(Customer).where(Customer.shop_name == shop_name)).first()
    if by_shop is not None:
        return by_shop

    customer = Customer(
        # phone is unique + required; use a deterministic sentinel when the caller
        # gave no number (repeat-caller recognition is a later milestone).
        phone=normalize_phone(phone) if phone else f"unknown:{shop_name}",
        shop_name=shop_name,
        contact_name=contact_name,
    )
    session.add(customer)
    session.flush()
    return customer
