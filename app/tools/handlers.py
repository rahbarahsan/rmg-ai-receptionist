"""Tool handlers. Phase 3 fills in the ordering tools.

Latency budget per handler: 500ms. No external HTTP calls in here.
"""

from pydantic import BaseModel
from sqlmodel import Session

from app.customers import lookup_customer_by_phone
from app.schemas import LookupCustomerInput

ToolResult = dict[str, object]


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


def not_implemented(session: Session, data: BaseModel) -> ToolResult:
    return {"ok": False, "reason": "not implemented"}
