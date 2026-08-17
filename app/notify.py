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
from app.locale.registry import OfferData, OfferLine, get_locale
from app.models import Customer, Order, OrderItem, Product


class SendResult(NamedTuple):
    ok: bool
    detail: str


def _product_name(product: Product | None, locale_code: str, fallback: str) -> str:
    if product is None:
        return fallback
    if locale_code == "bn" and product.name_bn:
        return product.name_bn
    return product.name_en


def format_offer(session: Session, order: Order, customer: Customer | None) -> str:
    """Render the written offer in the customer's language via the locale registry."""
    locale = get_locale(customer.locale if customer else None)
    offer_lines = [
        OfferLine(
            qty_pcs=it.qty_pcs,
            name=_product_name(session.get(Product, it.product_id), locale.code, it.product_id),
            unit_price_cents=it.unit_price_cents,
        )
        for it in session.exec(select(OrderItem).where(OrderItem.order_id == order.id)).all()
    ]
    data = OfferData(
        shop=customer.shop_name if customer else "your shop",
        lines=offer_lines,
        total_cents=order.total_cents,
        delivery_note=order.delivery_note,
    )
    return locale.render_offer(data)


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
        return SendResult(False, "Gmail SMTP not configured (GMAIL_ADDRESS + GMAIL_APP_PASSWORD)")
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
        locale = get_locale(customer.locale if customer else None)
        shop = customer.shop_name if customer else "RMG"
        return send_email(destination, locale.offer_subject(shop), body)
    return SendResult(False, f"unknown channel '{channel}'")
