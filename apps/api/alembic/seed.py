"""
Idempotent seed script for development and demo data.

Creates sample properties (ChromaDB), users, saved searches, and notification
preferences (PostgreSQL) for local development and demo purposes.
Safe to run multiple times.

Usage:
    python -m alembic.seed
    python -m alembic.seed --clear   # Clear existing data first
"""

import hashlib
import logging
import uuid

from sqlalchemy import select

from data.schemas import Property
from db.database import get_session_factory
from db.models import (
    NotificationPreferenceDB,
    SavedSearchDB,
    User,
)
from vector_store.chroma_store import ChromaPropertyStore

logger = logging.getLogger(__name__)


# ── Sample Data ──

SAMPLE_PROPERTIES: list[dict] = [
    {
        "id": "prop-001",
        "title": "Modern Apartment in Krakow",
        "address": "ul. Grodzka 15, Krakow, Poland",
        "city": "Krakow",
        "district": "Old Town",
        "price": 450000,
        "currency": "PLN",
        "rooms": 3,
        "area_sqm": 90,
        "property_type": "apartment",
        "listing_type": "sale",
        "source_url": "https://example.com/krakow/modern-apt",
        "description": (
            "Beautiful modern apartment in the heart of Krakow's Old Town. "
            "Recently renovated with high-quality finishes."
        ),
        "has_parking": True,
        "has_elevator": True,
        "has_balcony": True,
        "year_built": 2018,
        "floor": 3,
        "total_floors": 5,
    },
    {
        "id": "prop-002",
        "title": "Cozy Studio in Krakow",
        "address": "ul. Długa 42, Krakow, Poland",
        "city": "Krakow",
        "district": "Kazimierz",
        "price": 280000,
        "currency": "PLN",
        "rooms": 1,
        "area_sqm": 60,
        "property_type": "apartment",
        "listing_type": "sale",
        "source_url": "https://example.com/krakow/cozy-studio",
        "description": "Cozy studio in trendy Kazimierz district. Perfect for investment or first-time buyer.",
        "has_parking": False,
        "year_built": 2005,
        "floor": 2,
        "total_floors": 4,
    },
    {
        "id": "prop-003",
        "title": "Spacious Apartment in Warsaw",
        "address": "ul. Nowy Świat 25, Warsaw, Poland",
        "city": "Warsaw",
        "district": "Śródmieście",
        "price": 750000,
        "currency": "PLN",
        "rooms": 3,
        "area_sqm": 88,
        "property_type": "apartment",
        "listing_type": "sale",
        "source_url": "https://example.com/warsaw/spacious-apt",
        "description": "Spacious apartment in central Warsaw near public transport. Ideal for families.",
        "has_parking": True,
        "has_elevator": True,
        "year_built": 2015,
        "floor": 4,
        "total_floors": 6,
    },
    {
        "id": "prop-004",
        "title": "Family House in Warsaw",
        "address": "ul. Green Street 15, Warsaw, Poland",
        "city": "Warsaw",
        "district": "Mokotów",
        "price": 1200000,
        "currency": "PLN",
        "rooms": 5,
        "area_sqm": 200,
        "property_type": "house",
        "listing_type": "sale",
        "source_url": "https://example.com/warsaw/family-house",
        "description": "Beautiful family house with garden in quiet Mokotów district. Great schools nearby.",
        "has_parking": True,
        "has_garden": True,
        "year_built": 2010,
    },
    {
        "id": "prop-005",
        "title": "Luxury Penthouse in Warsaw",
        "address": "ul. Marszałkowska 1, Warsaw, Poland",
        "city": "Warsaw",
        "district": "Śródmieście",
        "price": 1500000,
        "currency": "PLN",
        "rooms": 4,
        "area_sqm": 125,
        "property_type": "apartment",
        "listing_type": "sale",
        "source_url": "https://example.com/warsaw/luxury-penthouse",
        "description": "Exclusive penthouse with panoramic city views. Premium finishes throughout.",
        "has_parking": True,
        "has_elevator": True,
        "has_balcony": True,
        "year_built": 2022,
        "floor": 10,
        "total_floors": 10,
    },
    {
        "id": "prop-006",
        "title": "Modern Apartment in Munich",
        "address": "Schwabinger Straße 10, Munich, Germany",
        "city": "Munich",
        "district": "Schwabing",
        "price": 500000,
        "currency": "EUR",
        "rooms": 2,
        "area_sqm": 71,
        "property_type": "apartment",
        "listing_type": "sale",
        "source_url": "https://example.com/munich/modern-apt",
        "description": "Modern apartment in desirable Schwabing area. Close to Englischer Garten.",
        "has_parking": False,
        "has_elevator": True,
        "has_balcony": True,
        "year_built": 2019,
        "floor": 3,
        "total_floors": 5,
    },
    {
        "id": "prop-007",
        "title": "Family Apartment in Munich",
        "address": "Leopoldstraße 50, Munich, Germany",
        "city": "Munich",
        "district": "Maxvorstadt",
        "price": 650000,
        "currency": "EUR",
        "rooms": 4,
        "area_sqm": 100,
        "property_type": "apartment",
        "listing_type": "sale",
        "source_url": "https://example.com/munich/family-apt",
        "description": "Spacious family apartment near city center. Good transport connections.",
        "has_parking": True,
        "has_elevator": True,
        "year_built": 2016,
        "floor": 2,
        "total_floors": 6,
    },
    {
        "id": "prop-008",
        "title": "Renovated Apartment in Krakow",
        "address": "ul. Starowiślna 30, Krakow, Poland",
        "city": "Krakow",
        "district": "Old Town",
        "price": 380000,
        "currency": "PLN",
        "rooms": 2,
        "area_sqm": 79,
        "property_type": "apartment",
        "listing_type": "sale",
        "source_url": "https://example.com/krakow/renovated-apt",
        "description": "Recently renovated apartment in historic Old Town. Original features preserved.",
        "has_parking": False,
        "year_built": 1930,
        "floor": 1,
        "total_floors": 3,
    },
    {
        "id": "prop-009",
        "title": "New Apartment in Warsaw",
        "address": "ul. Gagarina 8, Warsaw, Poland",
        "city": "Warsaw",
        "district": "Mokotów",
        "price": 550000,
        "currency": "PLN",
        "rooms": 3,
        "area_sqm": 73,
        "property_type": "apartment",
        "listing_type": "sale",
        "source_url": "https://example.com/warsaw/new-apt",
        "description": "Brand new apartment in developer complex. Energy-efficient with smart home features.",
        "has_parking": True,
        "has_balcony": True,
        "year_built": 2024,
        "floor": 5,
        "total_floors": 8,
    },
    {
        "id": "prop-010",
        "title": "Studio Apartment in Krakow",
        "address": "ul. Dietla 5, Krakow, Poland",
        "city": "Krakow",
        "district": "Kazimierz",
        "price": 250000,
        "currency": "PLN",
        "rooms": 1,
        "area_sqm": 50,
        "property_type": "apartment",
        "listing_type": "sale",
        "source_url": "https://example.com/krakow/studio",
        "description": "Compact studio in vibrant Kazimierz. Great rental investment opportunity.",
        "has_parking": False,
        "year_built": 2000,
        "floor": 1,
        "total_floors": 4,
    },
    {
        "id": "prop-011",
        "title": "Townhouse in Krakow",
        "address": "ul. Augustianska 12, Krakow, Poland",
        "city": "Krakow",
        "district": "Kazimierz",
        "price": 680000,
        "currency": "PLN",
        "rooms": 4,
        "area_sqm": 123,
        "property_type": "townhouse",
        "listing_type": "sale",
        "source_url": "https://example.com/krakow/townhouse",
        "description": "Charming townhouse in Kazimierz with private garden. Needs modernization.",
        "has_parking": False,
        "has_garden": True,
        "has_balcony": True,
        "year_built": 1950,
        "total_floors": 2,
    },
    {
        "id": "prop-012",
        "title": "Elegant Apartment in Krakow",
        "address": "ul. Basztowa 7, Krakow, Poland",
        "city": "Krakow",
        "district": "Old Town",
        "price": 520000,
        "currency": "PLN",
        "rooms": 2,
        "area_sqm": 100,
        "property_type": "apartment",
        "listing_type": "sale",
        "source_url": "https://example.com/krakow/elegant-apt",
        "description": "Elegant apartment with view of Wawel Castle. Renovated bathroom.",
        "has_parking": False,
        "has_elevator": True,
        "year_built": 2012,
        "floor": 4,
        "total_floors": 6,
    },
    {
        "id": "prop-013",
        "title": "Family Apartment in Krakow",
        "address": "ul. Karmelicka 18, Krakow, Poland",
        "city": "Krakow",
        "district": "Old Town",
        "price": 420000,
        "currency": "PLN",
        "rooms": 3,
        "area_sqm": 89,
        "property_type": "apartment",
        "listing_type": "rent",
        "source_url": "https://example.com/krakow/family-apt",
        "description": "Family apartment near Karmelicka street. Close to schools and parks.",
        "has_parking": False,
        "has_balcony": True,
        "year_built": 2008,
        "floor": 2,
        "total_floors": 5,
    },
    {
        "id": "prop-014",
        "title": "Cozy Studio in Krakow",
        "address": "ul. Miodowa 22, Krakow, Poland",
        "city": "Krakow",
        "district": "Podgórze",
        "price": 310000,
        "currency": "PLN",
        "rooms": 2,
        "area_sqm": 68,
        "property_type": "apartment",
        "listing_type": "sale",
        "source_url": "https://example.com/krakow/cozy-studio",
        "description": "Cozy apartment in up-and-coming Podgórze district. Good transport links.",
        "has_parking": False,
        "has_balcony": True,
        "year_built": 2015,
        "floor": 3,
        "total_floors": 4,
    },
    {
        "id": "prop-015",
        "title": "Modern Apartment in Krakow",
        "address": "ul. św. Wawrzyńca 5, Krakow, Poland",
        "city": "Krakow",
        "district": "Krowodrza",
        "price": 390000,
        "currency": "PLN",
        "rooms": 2,
        "area_sqm": 79,
        "property_type": "apartment",
        "listing_type": "sale",
        "source_url": "https://example.com/krakow/modern-apt-2",
        "description": "Modern apartment in Krowodrza with good public transport. Near shopping centers.",
        "has_parking": True,
        "has_elevator": True,
        "year_built": 2020,
        "floor": 2,
        "total_floors": 5,
    },
    {
        "id": "prop-016",
        "title": "Luxury Apartment in Warsaw",
        "address": "ul. Królewska 30, Warsaw, Poland",
        "city": "Warsaw",
        "district": "Śródmieście",
        "price": 980000,
        "currency": "PLN",
        "rooms": 3,
        "area_sqm": 109,
        "property_type": "apartment",
        "listing_type": "sale",
        "source_url": "https://example.com/warsaw/luxury-apt",
        "description": "Luxury apartment with premium finishes in central Warsaw. Doorman service.",
        "has_parking": True,
        "has_elevator": True,
        "year_built": 2023,
        "floor": 7,
        "total_floors": 12,
    },
    {
        "id": "prop-017",
        "title": "Bright Studio in Krakow",
        "address": "ul. św. Tomasza 11, Krakow, Poland",
        "city": "Krakow",
        "district": "Old Town",
        "price": 295000,
        "currency": "PLN",
        "rooms": 1,
        "area_sqm": 58,
        "property_type": "apartment",
        "listing_type": "sale",
        "source_url": "https://example.com/krakow/bright-studio",
        "description": "Bright studio with excellent location. Walking distance to Main Market.",
        "has_parking": False,
        "year_built": 1998,
        "floor": 4,
        "total_floors": 5,
    },
    {
        "id": "prop-018",
        "title": "Spacious Apartment in Krakow",
        "address": "ul. Wielopole 20, Krakow, Poland",
        "city": "Krakow",
        "district": "Old Town",
        "price": 460000,
        "currency": "PLN",
        "rooms": 3,
        "area_sqm": 96,
        "property_type": "apartment",
        "listing_type": "rent",
        "source_url": "https://example.com/krakow/spacious-apt",
        "description": "Spacious apartment with character in historic building. High ceilings.",
        "has_parking": False,
        "year_built": 1940,
        "floor": 3,
        "total_floors": 4,
    },
    {
        "id": "prop-019",
        "title": "Charming Apartment in Krakow",
        "address": "ul. Poselska 9, Krakow, Poland",
        "city": "Krakow",
        "district": "Kazimierz",
        "price": 350000,
        "currency": "PLN",
        "rooms": 2,
        "area_sqm": 70,
        "property_type": "apartment",
        "listing_type": "sale",
        "source_url": "https://example.com/krakow/charming-apt",
        "description": "Charming apartment in heart of Kazimierz. Near synagogues and galleries.",
        "has_parking": False,
        "has_balcony": True,
        "year_built": 1960,
        "floor": 2,
        "total_floors": 3,
    },
    {
        "id": "prop-020",
        "title": "Elegant Townhouse in Warsaw",
        "address": "ul. Tamka 14, Warsaw, Poland",
        "city": "Warsaw",
        "district": "Powiśle",
        "price": 1400000,
        "currency": "PLN",
        "rooms": 5,
        "area_sqm": 200,
        "property_type": "townhouse",
        "listing_type": "sale",
        "source_url": "https://example.com/warsaw/townhouse",
        "description": "Elegant townhouse in historic Powiśle district. Walking distance to Old Town.",
        "has_parking": True,
        "has_garden": True,
        "year_built": 1920,
        "total_floors": 3,
    },
    {
        "id": "prop-021",
        "title": "Cozy Apartment in Krakow",
        "address": "ul. Limanowskiego 3, Krakow, Poland",
        "city": "Krakow",
        "district": "Grzegórzki",
        "price": 320000,
        "currency": "PLN",
        "rooms": 2,
        "area_sqm": 69,
        "property_type": "apartment",
        "listing_type": "sale",
        "source_url": "https://example.com/krakow/cozy-apt",
        "description": "Cozy apartment in quiet Grzegórzki district. Near Błonia park.",
        "has_parking": False,
        "has_balcony": True,
        "year_built": 2010,
        "floor": 1,
        "total_floors": 3,
    },
    {
        "id": "prop-022",
        "title": "Modern Loft in Warsaw",
        "address": "ul. Mińowa 25, Warsaw, Poland",
        "city": "Warsaw",
        "district": "Wola",
        "price": 480000,
        "currency": "PLN",
        "rooms": 2,
        "area_sqm": 70,
        "property_type": "apartment",
        "listing_type": "sale",
        "source_url": "https://example.com/warsaw/modern-loft",
        "description": "Industrial-style loft in modern Wola district. Open plan living area.",
        "has_parking": True,
        "year_built": 2021,
        "floor": 3,
        "total_floors": 6,
    },
    {
        "id": "prop-023",
        "title": "Premium Apartment in Munich",
        "address": "Maximilianstraße 35, Munich, Germany",
        "city": "Munich",
        "district": "Altstadt-Lehel",
        "price": 800000,
        "currency": "EUR",
        "rooms": 3,
        "area_sqm": 84,
        "property_type": "apartment",
        "listing_type": "sale",
        "source_url": "https://example.com/munich/premium-apt",
        "description": (
            "Premium apartment in Munich's most prestigious district. "
            "Walking distance to Marienplatz."
        ),
        "has_parking": True,
        "has_elevator": True,
        "year_built": 2017,
        "floor": 5,
        "total_floors": 7,
    },
    {
        "id": "prop-024",
        "title": "Family Home in Munich",
        "address": "Isarstraße 20, Munich, Germany",
        "city": "Munich",
        "district": "Thalkirchen",
        "price": 1200000,
        "currency": "EUR",
        "rooms": 5,
        "area_sqm": 200,
        "property_type": "house",
        "listing_type": "sale",
        "source_url": "https://example.com/munich/family-home",
        "description": "Beautiful family home near Isar river. Large garden with old trees.",
        "has_parking": True,
        "has_garden": True,
        "has_balcony": True,
        "year_built": 2005,
        "total_floors": 2,
    },
    {
        "id": "prop-025",
        "title": "Student Studio in Munich",
        "address": "Leopoldstraße 80, Munich, Germany",
        "city": "Munich",
        "district": "Schwabing",
        "price": 250000,
        "currency": "EUR",
        "rooms": 1,
        "area_sqm": 45,
        "property_type": "apartment",
        "listing_type": "sale",
        "source_url": "https://example.com/munich/student-studio",
        "description": "Compact studio near LMU university. Ideal for students or young professionals.",
        "has_parking": False,
        "is_furnished": True,
        "year_built": 2008,
        "floor": 2,
        "total_floors": 5,
    },
]

SAMPLE_USERS: list[dict] = [
    {
        "id": "user-seed-001",
        "email": "alice@example.com",
        "full_name": "Alice Demo",
        "role": "user",
        "timezone": "Europe/Warsaw",
        "language": "en",
        "is_active": True,
    },
    {
        "id": "user-seed-002",
        "email": "bob@example.com",
        "full_name": "Bob Agent",
        "role": "agent",
        "timezone": "Europe/Warsaw",
        "language": "en",
        "is_active": True,
    },
]


def _hash_password(password: str) -> str:
    """Hash a password using SHA-256 (placeholder - in production use bcrypt)."""
    return hashlib.sha256(password.encode()).hexdigest()


def _build_pydantic_properties() -> list[Property]:
    """Convert raw sample dicts to validated Property (Pydantic) instances."""
    properties: list[Property] = []
    for raw in SAMPLE_PROPERTIES:
        prop = Property(
            id=raw["id"],
            title=raw.get("title"),
            description=raw.get("description"),
            city=raw["city"],
            district=raw.get("district"),
            address=raw.get("address"),
            property_type=raw.get("property_type", "apartment"),
            listing_type=raw.get("listing_type", "sale"),
            price=raw.get("price"),
            currency=raw.get("currency", "PLN"),
            rooms=raw.get("rooms"),
            area_sqm=raw.get("area_sqm"),
            has_parking=raw.get("has_parking", False),
            has_garden=raw.get("has_garden", False),
            has_elevator=raw.get("has_elevator", False),
            has_balcony=raw.get("has_balcony", False),
            is_furnished=raw.get("is_furnished", False),
            year_built=raw.get("year_built"),
            floor=raw.get("floor"),
            total_floors=raw.get("total_floors"),
            source_url=raw.get("source_url"),
        )
        properties.append(prop)
    return properties


def _seed_properties_chroma() -> int:
    """Seed sample properties into ChromaDB (idempotent via dedup)."""
    store = ChromaPropertyStore()
    properties = _build_pydantic_properties()
    count = store.add_properties(properties)
    logger.info("ChromaDB: seeded %d / %d properties", count, len(properties))
    return count


async def _seed_users(session) -> list[str]:
    """Seed sample users (upsert by id)."""
    seeded_ids = []
    for user_data in SAMPLE_USERS:
        user_id = user_data["id"]
        existing = await session.get(User, user_id)
        if existing:
            logger.debug("User %s already exists, skipping", user_id)
            seeded_ids.append(user_id)
            continue
        user = User(
            id=user_id,
            email=user_data["email"],
            full_name=user_data.get("full_name"),
            hashed_password=_hash_password("demo-password"),
            role=user_data.get("role", "user"),
            timezone=user_data.get("timezone", "UTC"),
            language=user_data.get("language", "en"),
            is_active=user_data.get("is_active", True),
            is_verified=True,
        )
        session.add(user)
        seeded_ids.append(user_id)
    return seeded_ids


async def _seed_saved_searches(session, users) -> None:
    """Create sample saved searches for each user."""
    cities = ["Krakow", "Warsaw", "Munich"]
    for i, user in enumerate(users):
        city = cities[i % len(cities)]
        search_name = f"Properties in {city}"
        existing = await session.execute(
            select(SavedSearchDB).where(
                SavedSearchDB.user_id == user.id,
                SavedSearchDB.name == search_name,
            )
        )
        if existing.scalars().first():
            logger.debug("Saved search '%s' for user %s already exists", search_name, user.id)
            continue
        search = SavedSearchDB(
            id=str(uuid.uuid4()),
            user_id=user.id,
            name=search_name,
            description=f"Saved search for {city} properties",
            filters={"city": city, "price_max": 600000, "rooms": 2},
            alert_frequency="daily",
            is_active=True,
            notify_on_new=True,
            notify_on_price_drop=True,
        )
        session.add(search)


async def _seed_notification_preferences(session, users) -> None:
    """Create notification preferences for each user."""
    for user in users:
        existing = await session.get(NotificationPreferenceDB, user.id)
        if existing:
            logger.debug("Notification prefs for user %s already exist", user.id)
            continue
        prefs = NotificationPreferenceDB(
            id=str(uuid.uuid4()),
            user_id=user.id,
            price_alerts_enabled=True,
            new_listings_enabled=True,
            saved_search_enabled=True,
            market_updates_enabled=False,
            alert_frequency="daily",
            email_enabled=True,
            push_enabled=False,
            in_app_enabled=True,
            price_drop_threshold=5.0,
        )
        session.add(prefs)


async def seed_all(clear: bool = False) -> None:
    """Run all seed operations."""
    logger.info("Starting data seeding (clear=%s)...", clear)

    # 1. Seed properties into ChromaDB (sync operation)
    if clear:
        logger.info("Clearing ChromaDB property store...")
        store = ChromaPropertyStore()
        store.clear()
        logger.info("ChromaDB cleared.")

    prop_count = _seed_properties_chroma()

    # 2. Seed relational data (PostgreSQL)
    factory = get_session_factory()
    async with factory() as session:
        try:
            if clear:
                logger.info("Clearing relational seed data...")
                from sqlalchemy import delete

                for table in [
                    "notification_preferences",
                    "saved_searches",
                    "favorites",
                    "collections",
                    "price_snapshots",
                ]:
                    await session.execute(delete(table))
                # Delete seed users only (preserve real users)
                await session.execute(
                    delete(User).where(User.id.in_(["user-seed-001", "user-seed-002"]))
                )
                await session.commit()
                logger.info("Relational data cleared.")

            user_ids = await _seed_users(session)
            await session.flush()

            users_result = await session.execute(select(User).where(User.id.in_(user_ids)))
            users = list(users_result.scalars().all())

            await _seed_saved_searches(session, users)
            await _seed_notification_preferences(session, users)

            await session.commit()
            logger.info(
                "Seed completed: %d properties (ChromaDB), %d users (PostgreSQL)",
                prop_count,
                len(user_ids),
            )
        except Exception:
            await session.rollback()
            raise


async def main():
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Seed development data")
    parser.add_argument("--clear", action="store_true", help="Clear existing data first")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    await seed_all(clear=args.clear)


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
