"""Operator dashboard — review and approve DRAFT orders. Run:

    uv run streamlit run dashboard/app.py

Reads/writes the same Postgres via the app's SQLModel models. A human turns a DRAFT
into CONFIRMED here — the agent never does (CLAUDE.md invariant 1).
"""

from datetime import UTC, datetime

import streamlit as st
from sqlmodel import Session, col, select

from app.db import engine
from app.models import Customer, Order, OrderItem, OrderStatus, Product

st.set_page_config(page_title="Order desk", layout="wide")
st.title("Order desk")


def taka(poisha: int) -> str:
    return f"BDT {poisha / 100:,.2f}"


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
        header = (
            f"{o.status.value} · {shop} · {taka(o.total_poisha)} · {o.created_at:%Y-%m-%d %H:%M}"
        )
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
                        "unit price": taka(it.unit_price_pois),
                        "line total": taka(it.qty_pcs * it.unit_price_pois),
                    }
                )
            st.table(rows)
            if o.delivery_note:
                st.write("**Delivery:**", o.delivery_note)
            if o.agent_notes:
                st.write("**Agent notes:**", o.agent_notes)

            if o.status == OrderStatus.DRAFT:
                approve, reject = st.columns(2)
                if approve.button("✅ Approve", key=f"approve-{o.id}"):
                    o.status = OrderStatus.CONFIRMED
                    o.reviewed_at = datetime.now(UTC)
                    session.add(o)
                    session.commit()
                    st.rerun()
                if reject.button("✖ Reject", key=f"reject-{o.id}"):
                    o.status = OrderStatus.REJECTED
                    o.reviewed_at = datetime.now(UTC)
                    session.add(o)
                    session.commit()
                    st.rerun()
