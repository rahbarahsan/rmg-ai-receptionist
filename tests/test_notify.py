from collections.abc import Iterator

import pytest
from sqlmodel import Session, SQLModel, create_engine, select

from app.models import Customer, Order, OrderItem, OrderStatus, Product
from app.notify import format_offer, send_offer


@pytest.fixture
def session() -> Iterator[Session]:
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False})
    SQLModel.metadata.create_all(engine)
    with Session(engine) as s:
        product = Product(
            sku="PLO-BLK-M",
            name_en="Black polo shirt (M)",
            category="polo",
            color="black",
            size="M",
            unit_price=400,
            stock_pcs=480,
        )
        customer = Customer(phone="+10000000000", shop_name="Swapno", contact_name="Salman")
        s.add(product)
        s.add(customer)
        s.commit()
        order = Order(
            customer_id=customer.id,
            status=OrderStatus.CONFIRMED,
            total_cents=80000,
            offer_channel="sms",
            offer_destination="+14377762982",
        )
        s.add(order)
        s.commit()
        s.add(
            OrderItem(
                order_id=order.id,
                product_id=product.id,
                qty_pcs=200,
                spoken_qty="two hundred pieces",
                spoken_unit="piece",
                unit_price_cents=400,
            )
        )
        s.commit()
        yield s


def test_format_offer(session: Session) -> None:
    order = session.exec(select(Order)).first()
    assert order is not None
    customer = session.get(Customer, order.customer_id)
    text = format_offer(session, order, customer)
    assert "Swapno" in text
    assert "200 pcs Black polo shirt (M) @ $4.00 = $800.00" in text
    assert "Total: $800.00" in text


def test_send_offer_without_channel_is_a_clean_no_op(session: Session) -> None:
    order = session.exec(select(Order)).first()
    assert order is not None
    order.offer_channel = None
    order.offer_destination = None
    session.add(order)
    session.commit()
    result = send_offer(session, order)  # returns early — never touches a provider
    assert result.ok is False
    assert "no offer channel" in result.detail
