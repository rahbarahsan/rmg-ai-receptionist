from collections.abc import Callable

from pydantic import BaseModel, ValidationError
from sqlmodel import Session

from app.db import engine
from app.schemas import TOOL_SCHEMAS
from app.tools import handlers

ToolResult = dict[str, object]
Handler = Callable[[Session, BaseModel], ToolResult]

_HANDLERS: dict[str, Handler] = {
    "lookup_customer": handlers.lookup_customer,
    "search_catalog": handlers.search_catalog,
    "check_stock": handlers.check_stock,
    "create_draft_order": handlers.create_draft_order,
    "get_order_status": handlers.not_implemented,
    "escalate_to_human": handlers.escalate_to_human,
}


def is_tool_name(name: str) -> bool:
    return name in TOOL_SCHEMAS


def run_tool(name: str, raw_input: object) -> ToolResult:
    """Validate against the tool's schema, then dispatch. Opens its own DB session
    so the caller can run it off the event loop via a threadpool.
    """
    schema = TOOL_SCHEMAS[name]
    try:
        parsed = schema.model_validate(raw_input)
    except ValidationError:
        return {"ok": False, "reason": "invalid input"}
    with Session(engine) as session:
        return _HANDLERS[name](session, parsed)
