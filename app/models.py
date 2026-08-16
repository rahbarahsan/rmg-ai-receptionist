"""SQLModel tables — port of prisma/schema.prisma.

Money is integer US cents (USD * 100), never floats. Quantities are pieces. `aliases`
uses a JSON column (portable across Postgres and the sqlite used in tests) rather than
a Postgres array.
"""

from datetime import UTC, datetime
from enum import StrEnum
from uuid import uuid4

from sqlalchemy import Column
from sqlalchemy.types import JSON
from sqlmodel import Field, SQLModel


def _id() -> str:
    return uuid4().hex


def _now() -> datetime:
    return datetime.now(UTC)


class OrderStatus(StrEnum):
    DRAFT = "DRAFT"  # created by the agent — not real yet
    NEEDS_REVIEW = "NEEDS_REVIEW"
    CONFIRMED = "CONFIRMED"  # human approved
    REJECTED = "REJECTED"
    FULFILLED = "FULFILLED"


class Customer(SQLModel, table=True):
    id: str = Field(default_factory=_id, primary_key=True)
    phone: str = Field(unique=True, index=True)  # E.164
    shop_name: str
    contact_name: str | None = None
    market: str | None = None  # Islampur, New Market, ...
    locale: str = "en"  # en | bn
    credit_limit: int = 0  # poisha; 0 = cash only
    is_blocked: bool = False
    created_at: datetime = Field(default_factory=_now)


class Product(SQLModel, table=True):
    id: str = Field(default_factory=_id, primary_key=True)
    sku: str = Field(unique=True, index=True)
    name_en: str
    name_bn: str | None = None
    category: str  # polo, tee, panjabi, ...
    color: str
    size: str
    aliases: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    unit_price: int  # US cents per piece
    stock_pcs: int = 0
    is_active: bool = True


class Order(SQLModel, table=True):
    id: str = Field(default_factory=_id, primary_key=True)
    customer_id: str = Field(foreign_key="customer.id", index=True)
    status: OrderStatus = Field(default=OrderStatus.DRAFT)
    total_cents: int = 0
    delivery_note: str | None = None
    offer_channel: str | None = None  # how to send the final offer: email | sms
    offer_destination: str | None = None  # confirmed email address or phone number
    call_id: str | None = None  # ElevenLabs conversation id
    agent_notes: str | None = None
    reviewed_by: str | None = None
    reviewed_at: datetime | None = None
    offer_sent_at: datetime | None = None
    created_at: datetime = Field(default_factory=_now)


class OrderItem(SQLModel, table=True):
    id: str = Field(default_factory=_id, primary_key=True)
    order_id: str = Field(foreign_key="order.id", index=True)
    product_id: str = Field(foreign_key="product.id")
    qty_pcs: int  # canonical
    spoken_qty: str  # exactly what the caller said: "তিন dozen"
    spoken_unit: str  # dozen | hali | piece | gross
    unit_price_cents: int  # snapshot at draft time (US cents)
    confidence: float = 1.0  # from the Banglish parser


class CallLog(SQLModel, table=True):
    id: str = Field(default_factory=_id, primary_key=True)
    call_id: str = Field(unique=True, index=True)
    phone_hash: str  # hashed — never store raw numbers in logs
    transcript: str | None = None
    duration_ms: int | None = None
    outcome: str  # draft_created | escalated | abandoned | info_only
    created_at: datetime = Field(default_factory=_now)
