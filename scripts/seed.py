"""Seed minimal fixture data. Run: uv run python scripts/seed.py

Creates tables via create_all for dev convenience; production uses Alembic.
"""

from sqlmodel import Session, SQLModel, select

from app.config import settings
from app.db import engine
from app.models import Customer, Product
from app.phone import normalize_phone

# ruff: noqa: E501  (catalog rows are kept one-per-line for readability)
# fmt: off
_PRODUCTS = [
    {"sku": "PLO-BLK-M", "name_en": "Black polo shirt (M)", "name_bn": "কালো পোলো শার্ট", "category": "polo", "color": "black", "size": "M", "aliases": ["black polo", "কালো পোলো"], "unit_price": 400, "stock_pcs": 480},
    {"sku": "PLO-BLK-L", "name_en": "Black polo shirt (L)", "name_bn": "কালো পোলো শার্ট", "category": "polo", "color": "black", "size": "L", "aliases": ["black polo large"], "unit_price": 450, "stock_pcs": 360},
    {"sku": "PLO-WHT-M", "name_en": "White polo shirt (M)", "name_bn": "সাদা পোলো শার্ট", "category": "polo", "color": "white", "size": "M", "aliases": ["white polo", "সাদা পোলো"], "unit_price": 400, "stock_pcs": 300},
    {"sku": "PLO-NAV-L", "name_en": "Navy polo shirt (L)", "name_bn": "নেভি পোলো শার্ট", "category": "polo", "color": "navy", "size": "L", "aliases": ["navy polo", "blue polo"], "unit_price": 450, "stock_pcs": 220},
    {"sku": "TEE-WHT-M", "name_en": "White t-shirt (M)", "name_bn": "সাদা টি-শার্ট", "category": "tee", "color": "white", "size": "M", "aliases": ["white tee", "white tshirt"], "unit_price": 200, "stock_pcs": 1200},
    {"sku": "TEE-WHT-L", "name_en": "White t-shirt (L)", "name_bn": "সাদা টি-শার্ট", "category": "tee", "color": "white", "size": "L", "aliases": ["white tee large"], "unit_price": 220, "stock_pcs": 900},
    {"sku": "TEE-BLK-M", "name_en": "Black t-shirt (M)", "name_bn": "কালো টি-শার্ট", "category": "tee", "color": "black", "size": "M", "aliases": ["black tee", "black tshirt"], "unit_price": 200, "stock_pcs": 800},
    {"sku": "GNJ-WHT-M", "name_en": "White genji undershirt (M)", "name_bn": "সাদা গেঞ্জি", "category": "genji", "color": "white", "size": "M", "aliases": ["white genji", "সাদা গেঞ্জি", "undershirt"], "unit_price": 120, "stock_pcs": 2000},
    {"sku": "GNJ-GRY-L", "name_en": "Grey genji (L)", "name_bn": "ধূসর গেঞ্জি", "category": "genji", "color": "grey", "size": "L", "aliases": ["grey genji", "gray genji"], "unit_price": 130, "stock_pcs": 1500},
    {"sku": "PAN-WHT-L", "name_en": "White panjabi (L)", "name_bn": "সাদা পাঞ্জাবি", "category": "panjabi", "color": "white", "size": "L", "aliases": ["white panjabi", "সাদা পাঞ্জাবি"], "unit_price": 700, "stock_pcs": 150},
    {"sku": "PAN-BLK-XL", "name_en": "Black panjabi (XL)", "name_bn": "কালো পাঞ্জাবি", "category": "panjabi", "color": "black", "size": "XL", "aliases": ["black panjabi"], "unit_price": 750, "stock_pcs": 90},
    {"sku": "PAN-CRM-L", "name_en": "Cream panjabi (L)", "name_bn": "ক্রিম পাঞ্জাবি", "category": "panjabi", "color": "cream", "size": "L", "aliases": ["cream panjabi", "off white panjabi"], "unit_price": 720, "stock_pcs": 120},
    {"sku": "SHT-BLU-M", "name_en": "Blue formal shirt (M)", "name_bn": "নীল ফরমাল শার্ট", "category": "shirt", "color": "blue", "size": "M", "aliases": ["blue shirt", "formal shirt"], "unit_price": 500, "stock_pcs": 260},
    {"sku": "SHT-WHT-L", "name_en": "White formal shirt (L)", "name_bn": "সাদা ফরমাল শার্ট", "category": "shirt", "color": "white", "size": "L", "aliases": ["white shirt", "সাদা শার্ট"], "unit_price": 520, "stock_pcs": 310},
    {"sku": "SHT-CHK-M", "name_en": "Check casual shirt (M)", "name_bn": "চেক শার্ট", "category": "shirt", "color": "check", "size": "M", "aliases": ["check shirt", "casual shirt"], "unit_price": 550, "stock_pcs": 180},
]
# fmt: on


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
