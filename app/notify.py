"""Send the final offer to the shop owner by SMS (Twilio) or email (Resend).

Plain httpx REST, no SDKs. Called when a human approves an order. Never raises for a
provider error; returns a SendResult the caller can surface.
"""

from typing import NamedTuple

import httpx
from sqlmodel import Session, select

from app.config import settings
from app.models import Customer, Order, OrderItem, Product


class SendResult(NamedTuple):
    ok: bool
    detail: str


def _usd(cents: int) -> str:
    return f"${cents / 100:,.2f}"


def format_offer(session: Session, order: Order, customer: Customer | None) -> str:
    shop = customer.shop_name if customer else "your shop"
    lines = [f"RMG Wholesale — order for {shop}", ""]
    for it in session.exec(select(OrderItem).where(OrderItem.order_id == order.id)).all():
        product = session.get(Product, it.product_id)
        name = product.name_en if product else it.product_id
        line_total = it.qty_pcs * it.unit_price_cents
        lines.append(
            f"- {it.qty_pcs} pcs {name} @ {_usd(it.unit_price_cents)} = {_usd(line_total)}"
        )
    lines.append("")
    lines.append(f"Total: {_usd(order.total_cents)}")
    if order.delivery_note:
        lines.append(f"Delivery: {order.delivery_note}")
    lines.append("The sales desk will confirm delivery and payment terms shortly.")
    return "\n".join(lines)


def send_sms(to: str, body: str) -> SendResult:
    sid = settings.twilio_account_sid
    token = settings.twilio_auth_token
    sender = settings.twilio_phone_number
    if not (sid and token and sender):
        return SendResult(
            False, "Twilio SMS not configured (TWILIO_ACCOUNT_SID/AUTH_TOKEN/PHONE_NUMBER)"
        )
    resp = httpx.post(
        f"https://api.twilio.com/2010-04-01/Accounts/{sid}/Messages.json",
        auth=(sid, token),
        data={"From": sender, "To": to, "Body": body},
        timeout=20,
    )
    if resp.status_code >= 400:
        return SendResult(False, f"Twilio {resp.status_code}: {resp.text[:200]}")
    message_sid = resp.json().get("sid", "?")
    return SendResult(True, f"SMS queued to {to} (sid {message_sid})")


def send_email(to: str, subject: str, body: str) -> SendResult:
    # Resend. from = offer_from_email, else onboarding@resend.dev (Resend's no-domain test
    # sender — in that mode you can only send to your own Resend account email).
    key = settings.resend_api_key
    sender = settings.offer_from_email or "onboarding@resend.dev"
    if not key:
        return SendResult(False, "Resend not configured (RESEND_API_KEY)")
    resp = httpx.post(
        "https://api.resend.com/emails",
        headers={"Authorization": f"Bearer {key}", "content-type": "application/json"},
        json={"from": sender, "to": [to], "subject": subject, "text": body},
        timeout=20,
    )
    if resp.status_code >= 400:
        return SendResult(False, f"Resend {resp.status_code}: {resp.text[:200]}")
    return SendResult(True, f"email sent to {to} (id {resp.json().get('id', '?')})")


def send_offer(session: Session, order: Order) -> SendResult:
    channel = (order.offer_channel or "").strip().lower()
    destination = (order.offer_destination or "").strip()
    if not channel or not destination:
        return SendResult(False, "no offer channel/destination on this order")

    customer = session.get(Customer, order.customer_id)
    body = format_offer(session, order, customer)
    if channel == "sms":
        return send_sms(destination, body)
    if channel == "email":
        shop = customer.shop_name if customer else "RMG"
        return send_email(destination, f"Your order — {shop}", body)
    return SendResult(False, f"unknown channel '{channel}'")
