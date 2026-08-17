"""Send the final offer to the shop owner by SMS (Twilio) or email (Gmail SMTP).

SMS via the Twilio REST API; email via Gmail SMTP with an App Password. Called when a
human approves an order. Never raises for a provider error; returns a SendResult.
"""

import base64
import smtplib
from email.message import EmailMessage
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
    # Gmail SMTP with a Google App Password (base64-encoded in .env). Sends from your
    # Gmail to any recipient — no domain needed.
    user = settings.gmail_address
    pw_b64 = settings.gmail_app_password
    if not (user and pw_b64):
        return SendResult(
            False, "Gmail SMTP not configured (GMAIL_ADDRESS + GMAIL_APP_PASSWORD)"
        )
    try:
        password = base64.b64decode(pw_b64).decode().strip()
    except (ValueError, UnicodeDecodeError):
        return SendResult(False, "GMAIL_APP_PASSWORD_B64 is not valid base64")

    message = EmailMessage()
    message["From"] = user
    message["To"] = to
    message["Subject"] = subject
    message.set_content(body)
    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=20) as server:
            server.login(user, password)
            server.send_message(message)
    except (smtplib.SMTPException, OSError) as exc:
        return SendResult(False, f"Gmail SMTP error: {exc}")
    return SendResult(True, f"email sent to {to} via Gmail")


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
