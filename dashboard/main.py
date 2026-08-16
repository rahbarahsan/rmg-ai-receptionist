"""Operator dashboard — review and approve DRAFT orders. Run:

    uv run streamlit run dashboard/main.py

Reads/writes the same Postgres via the app's SQLModel models. A human turns a DRAFT
into CONFIRMED here — the agent never does (CLAUDE.md invariant 1).
"""

import sys
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # make `app` importable

import streamlit as st  # noqa: E402
from sqlmodel import Session, col, select  # noqa: E402

from app.db import engine  # noqa: E402
from app.models import Customer, Order, OrderItem, OrderStatus, Product  # noqa: E402
from app.notify import send_offer  # noqa: E402

st.set_page_config(page_title="Order desk", layout="wide")
st.title("Order desk")

_flash = st.session_state.pop("flash", None)
if _flash:
    (st.success if _flash[0] == "success" else st.error)(_flash[1])


def usd(cents: int) -> str:
    return f"${cents / 100:,.2f}"


all_statuses = [s.value for s in OrderStatus]
default = [OrderStatus.DRAFT.value, OrderStatus.NEEDS_REVIEW.value]
wanted = st.sidebar.multiselect("Status", all_statuses, default=default)
if st.sidebar.button("Refresh"):
    st.rerun()

with Session(engine) as session:
    orders = [
        o
        for o in session.exec(select(Order).order_by(col(Order.created_at).desc())).all()
        if o.status.value in wanted
    ]
    st.caption(f"{len(orders)} order(s)")

    for o in orders:
        customer = session.get(Customer, o.customer_id)
        shop = customer.shop_name if customer else "(unknown)"
        header = f"{o.status.value} · {shop} · {usd(o.total_cents)} · {o.created_at:%Y-%m-%d %H:%M}"
        with st.expander(header):
            contact = customer.contact_name if customer else "-"
            st.caption(f"Order {o.id} · call {o.call_id or '-'} · contact {contact}")
            rows = []
            for it in session.exec(select(OrderItem).where(OrderItem.order_id == o.id)).all():
                product = session.get(Product, it.product_id)
                rows.append(
                    {
                        "product": product.name_en if product else it.product_id,
                        "qty (pcs)": it.qty_pcs,
                        "as said": it.spoken_qty,
                        "unit price": usd(it.unit_price_cents),
                        "line total": usd(it.qty_pcs * it.unit_price_cents),
                    }
                )
            st.table(rows)
            if o.delivery_note:
                st.write("**Delivery:**", o.delivery_note)
            if o.agent_notes:
                st.write("**Agent notes:**", o.agent_notes)
            if o.offer_channel:
                st.write(f"**Send offer via:** {o.offer_channel} → {o.offer_destination or '-'}")
            if o.reviewed_at:
                st.write("**Reviewed:**", o.reviewed_at.strftime("%Y-%m-%d %H:%M UTC"))
            if o.offer_sent_at:
                st.write("**Offer sent:**", o.offer_sent_at.strftime("%Y-%m-%d %H:%M UTC"))

            if o.status in (OrderStatus.DRAFT, OrderStatus.NEEDS_REVIEW):
                approve, reject = st.columns(2)
                if approve.button("✅ Approve & send offer", key=f"approve-{o.id}"):
                    o.status = OrderStatus.CONFIRMED
                    o.reviewed_at = datetime.now(UTC)
                    session.add(o)
                    session.commit()
                    result = send_offer(session, o)
                    if result.ok:
                        o.offer_sent_at = datetime.now(UTC)
                        session.add(o)
                        session.commit()
                    st.session_state["flash"] = ("success" if result.ok else "error", result.detail)
                    st.rerun()
                if reject.button("✖ Reject", key=f"reject-{o.id}"):
                    o.status = OrderStatus.REJECTED
                    o.reviewed_at = datetime.now(UTC)
                    session.add(o)
                    session.commit()
                    st.rerun()
