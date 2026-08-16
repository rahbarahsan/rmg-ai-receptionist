"""Tool input schemas — Pydantic v2 port of src/lib/tools/schemas.ts.

Schema first, then handler, then test. Money is poisha, quantity is pieces.
"""

from typing import Literal

from pydantic import BaseModel, Field


class LookupCustomerInput(BaseModel):
    phone: str = Field(min_length=6)


class SearchCatalogInput(BaseModel):
    query: str = Field(min_length=1)
    customer_id: str | None = None
    limit: int = Field(default=3, ge=1, le=5)


class CheckStockInput(BaseModel):
    sku: str = Field(min_length=1)


class DraftItem(BaseModel):
    sku: str
    amount: float = Field(gt=0)  # numeric quantity the caller said (e.g. 3, 2.5)
    unit: str = Field(min_length=1)  # spoken unit: dozen | hali | piece | gross (or Bangla)
    spoken_qty: str  # verbatim, e.g. "three dozen"
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)


class CreateDraftOrderInput(BaseModel):
    # New-order flow: the caller is identified by the shop + contact name they speak,
    # not a pre-known customer id. The handler finds-or-creates the customer.
    shop_name: str = Field(min_length=1)
    contact_name: str | None = None
    phone: str | None = None
    # How the caller wants the final offer sent, collected + confirmed on the call.
    offer_channel: str | None = None  # "email" or "sms"
    offer_destination: str | None = None  # the confirmed email address or phone number
    call_id: str | None = None
    delivery_note: str | None = Field(default=None, max_length=500)
    items: list[DraftItem] = Field(min_length=1)


class GetOrderStatusInput(BaseModel):
    order_id: str


class EscalateInput(BaseModel):
    call_id: str | None = None
    customer_id: str | None = None
    reason: Literal[
        "price_negotiation",
        "credit_request",
        "unknown_caller",
        "product_not_found",
        "complaint",
        "other",
    ]
    detail: str | None = Field(default=None, max_length=500)


TOOL_SCHEMAS: dict[str, type[BaseModel]] = {
    "lookup_customer": LookupCustomerInput,
    "search_catalog": SearchCatalogInput,
    "check_stock": CheckStockInput,
    "create_draft_order": CreateDraftOrderInput,
    "get_order_status": GetOrderStatusInput,
    "escalate_to_human": EscalateInput,
}
