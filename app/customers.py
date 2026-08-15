from dataclasses import dataclass

from sqlmodel import Session, select

from app.models import Customer
from app.phone import normalize_phone


@dataclass
class CustomerLookup:
    is_known: bool
    id: str | None = None
    shop_name: str | None = None
    contact_name: str | None = None
    locale: str | None = None
    is_blocked: bool = False


def lookup_customer_by_phone(session: Session, raw_phone: str) -> CustomerLookup:
    """Resolve a caller's phone number to a known shop. One indexed lookup — safely
    inside the 500ms tool budget. Shared by the conversation-init webhook and the
    lookup_customer tool.
    """
    phone = normalize_phone(raw_phone)
    if len(phone) < 6:
        return CustomerLookup(is_known=False)

    customer = session.exec(select(Customer).where(Customer.phone == phone)).first()
    if customer is None:
        return CustomerLookup(is_known=False)

    return CustomerLookup(
        is_known=True,
        id=customer.id,
        shop_name=customer.shop_name,
        contact_name=customer.contact_name,
        locale=customer.locale,
        is_blocked=customer.is_blocked,
    )
