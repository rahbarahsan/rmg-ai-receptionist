"""Seed minimal fixture data. Run: uv run python scripts/seed.py

Creates tables via create_all for dev convenience; production uses Alembic.
"""

from sqlmodel import Session, SQLModel, select

from app.config import settings
from app.db import engine
from app.models import Customer, Product
from app.phone import normalize_phone

_PRODUCTS = [
    {
        "sku": "PLO-BLK-M",
        "name_en": "Black polo shirt (M)",
        "name_bn": "কালো পোলো শার্ট (M)",
        "category": "polo",
        "color": "black",
        "size": "M",
        "aliases": ["black polo", "কালো পোলো"],
        "unit_price": 32000,
        "stock_pcs": 480,
    },
    {
        "sku": "PLO-BLK-L",
        "name_en": "Black polo shirt (L)",
        "name_bn": "কালো পোলো শার্ট (L)",
        "category": "polo",
        "color": "black",
        "size": "L",
        "aliases": ["black polo large"],
        "unit_price": 33000,
        "stock_pcs": 360,
    },
    {
        "sku": "TEE-WHT-M",
        "name_en": "White tee (M)",
        "name_bn": "সাদা টি-শার্ট (M)",
        "category": "tee",
        "color": "white",
        "size": "M",
        "aliases": ["white tee", "সাদা গেঞ্জি"],
        "unit_price": 18000,
        "stock_pcs": 1200,
    },
]


def _upsert_customer(
    session: Session,
    *,
    phone: str,
    shop_name: str,
    contact_name: str | None = None,
    market: str | None = None,
) -> None:
    existing = session.exec(select(Customer).where(Customer.phone == phone)).first()
    if existing is None:
        session.add(
            Customer(
                phone=phone,
                shop_name=shop_name,
                contact_name=contact_name,
                market=market,
                locale="en",
            )
        )
    else:
        existing.shop_name = shop_name
        session.add(existing)


def main() -> None:
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        _upsert_customer(
            session,
            phone="+8801700000000",
            shop_name="Rahman Garments",
            contact_name="Karim Rahman",
            market="Islampur",
        )
        # Your real phone -> your shop, so a live demo call is recognized. From .env
        # (never committed) because a real phone number is PII.
        if settings.demo_caller_phone and settings.demo_shop_name:
            _upsert_customer(
                session,
                phone=normalize_phone(settings.demo_caller_phone),
                shop_name=settings.demo_shop_name,
            )
            print(f"Seeded demo caller -> {settings.demo_shop_name}")

        for p in _PRODUCTS:
            if session.exec(select(Product).where(Product.sku == p["sku"])).first() is None:
                session.add(Product(**p))  # type: ignore[arg-type]
        session.commit()
    print("Seed complete.")


if __name__ == "__main__":
    main()
