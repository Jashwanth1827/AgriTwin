"""Idempotent demo seed data.

The seed creates a clearly-labelled demo account with representative farms,
crops, buyers and offers, then loads the bundled real public datasets (Agmarknet
market prices and the India crop-production sample) and the PlantVillage class
catalogue.  Demo records are always flagged with ``is_demo=True`` and a visible
notice; real dataset rows are never relabelled as demo.
"""

from __future__ import annotations

import logging
from datetime import date, timedelta

import pandas as pd
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import BACKEND_DIR, settings
from app.core.constants import DEMO_DATA_NOTICE
from app.core.security import hash_password
from app.ml.crop_health.labels import CLASS_INFO
from app.models.buyer import Buyer, BuyerOffer
from app.models.crop_health import DiseaseClass
from app.models.farm import Crop, Farm
from app.models.market import MarketPriceRecord
from app.models.user import Notification, User
from app.models.yield_ import HistoricalYieldRecord

logger = logging.getLogger(__name__)


def _demo_user(db: Session) -> User:
    user = db.scalar(select(User).where(User.email == settings.SEED_DEMO_USER_EMAIL))
    if user is not None:
        return user
    user = User(
        email=settings.SEED_DEMO_USER_EMAIL.lower(),
        full_name="Demo Farmer",
        password_hash=hash_password(settings.SEED_DEMO_USER_PASSWORD),
        phone="+91-90000-00000",
        state="Maharashtra",
        district="Nashik",
        preferred_language="en",
        is_active=True,
        is_demo=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    logger.info("Created demo user %s", user.email)
    return user


def _demo_farms(db: Session, user: User) -> None:
    if db.scalar(select(func.count(Farm.id)).where(Farm.user_id == user.id)):
        return
    farms = [
        Farm(
            user_id=user.id,
            name="Kisan Green Farm",
            village="Pimpalgaon",
            district="Nashik",
            state="Maharashtra",
            latitude=20.0110,
            longitude=73.7900,
            total_area_hectares=8.5,
            soil_type="Black (Regur)",
            soil_ph=7.2,
            nitrogen_kg_per_ha=240,
            phosphorus_kg_per_ha=38,
            potassium_kg_per_ha=210,
            soil_moisture_pct=32,
            notes=f"{DEMO_DATA_NOTICE} Representative horticulture farm.",
            is_demo=True,
        ),
        Farm(
            user_id=user.id,
            name="Yamuna Wheat Fields",
            village="Daurala",
            district="Meerut",
            state="Uttar Pradesh",
            latitude=28.9845,
            longitude=77.7064,
            total_area_hectares=12.0,
            soil_type="Alluvial",
            soil_ph=7.6,
            nitrogen_kg_per_ha=180,
            phosphorus_kg_per_ha=42,
            potassium_kg_per_ha=160,
            soil_moisture_pct=28,
            notes=f"{DEMO_DATA_NOTICE} Representative cereal farm.",
            is_demo=True,
        ),
        Farm(
            user_id=user.id,
            name="Cauvery Paddy Plot",
            village="Thiruvaiyaru",
            district="Thanjavur",
            state="Tamil Nadu",
            latitude=10.7870,
            longitude=79.1378,
            total_area_hectares=6.0,
            soil_type="Clay",
            soil_ph=6.8,
            nitrogen_kg_per_ha=150,
            phosphorus_kg_per_ha=30,
            potassium_kg_per_ha=140,
            soil_moisture_pct=45,
            notes=f"{DEMO_DATA_NOTICE} Representative delta paddy plot.",
            is_demo=True,
        ),
    ]
    db.add_all(farms)
    db.commit()
    logger.info("Created %d demo farms", len(farms))


def _demo_crops(db: Session, user: User) -> None:
    if db.scalar(
        select(func.count(Crop.id)).join(Farm, Crop.farm_id == Farm.id).where(Farm.user_id == user.id)
    ):
        return
    farms = {
        farm.name: farm
        for farm in db.scalars(select(Farm).where(Farm.user_id == user.id))
    }
    today = date.today()
    crops = [
        Crop(
            farm_id=farms["Kisan Green Farm"].id,
            crop_name="Onion",
            variety="Bhima Super",
            season="Kharif",
            sowing_date=today - timedelta(days=118),
            expected_harvest_date=today - timedelta(days=8),
            growth_stage="Harvest ready",
            area_hectares=3.5,
            status="active",
            notes=f"{DEMO_DATA_NOTICE}",
            is_demo=True,
        ),
        Crop(
            farm_id=farms["Kisan Green Farm"].id,
            crop_name="Tomato",
            variety="Pusa Ruby",
            season="Kharif",
            sowing_date=today - timedelta(days=88),
            expected_harvest_date=today + timedelta(days=12),
            growth_stage="Grain/Fruit filling",
            area_hectares=2.0,
            status="active",
            notes=f"{DEMO_DATA_NOTICE}",
            is_demo=True,
        ),
        Crop(
            farm_id=farms["Yamuna Wheat Fields"].id,
            crop_name="Wheat",
            variety="HD-3086",
            season="Rabi",
            sowing_date=today - timedelta(days=2),
            expected_harvest_date=today + timedelta(days=128),
            growth_stage="Sowing/Germination",
            area_hectares=5.0,
            status="active",
            notes=f"{DEMO_DATA_NOTICE}",
            is_demo=True,
        ),
        Crop(
            farm_id=farms["Cauvery Paddy Plot"].id,
            crop_name="Rice",
            variety="ADT-43",
            season="Kharif",
            sowing_date=today - timedelta(days=132),
            expected_harvest_date=today - timedelta(days=2),
            growth_stage="Harvest ready",
            area_hectares=4.0,
            status="active",
            notes=f"{DEMO_DATA_NOTICE}",
            is_demo=True,
        ),
    ]
    db.add_all(crops)
    db.commit()
    logger.info("Created %d demo crops", len(crops))


def _demo_buyers(db: Session, user: User) -> None:
    if db.scalar(select(func.count(Buyer.id)).where(Buyer.user_id == user.id)):
        return
    today = date.today()
    expiry = today + timedelta(days=45)
    buyers = [
        Buyer(
            user_id=user.id,
            name="Nashik Fresh Produce Traders",
            buyer_type="Trader",
            contact_name="Demo contact",
            contact_phone="+91-90000-00001",
            market_name="Pimpalgaon APMC",
            district="Nashik",
            state="Maharashtra",
            latitude=20.1700,
            longitude=73.9200,
            notes=f"{DEMO_DATA_NOTICE} Illustrative onion buyer.",
            is_demo=True,
        ),
        Buyer(
            user_id=user.id,
            name="Sahyadri Farmer Producer Company",
            buyer_type="FPO",
            contact_name="Demo contact",
            contact_phone="+91-90000-00002",
            market_name="Lasalgaon APMC",
            district="Nashik",
            state="Maharashtra",
            latitude=20.1500,
            longitude=74.2300,
            notes=f"{DEMO_DATA_NOTICE} Illustrative FPO buyer.",
            is_demo=True,
        ),
        Buyer(
            user_id=user.id,
            name="Meerut Grain Cooperative",
            buyer_type="Cooperative",
            contact_name="Demo contact",
            contact_phone="+91-90000-00003",
            market_name="Meerut APMC",
            district="Meerut",
            state="Uttar Pradesh",
            latitude=28.9800,
            longitude=77.7000,
            notes=f"{DEMO_DATA_NOTICE} Illustrative wheat buyer.",
            is_demo=True,
        ),
        Buyer(
            user_id=user.id,
            name="Thanjavur Rice Mill",
            buyer_type="Processor",
            contact_name="Demo contact",
            contact_phone="+91-90000-00004",
            market_name="Thanjavur APMC",
            district="Thanjavur",
            state="Tamil Nadu",
            latitude=10.7800,
            longitude=79.1300,
            notes=f"{DEMO_DATA_NOTICE} Illustrative paddy buyer.",
            is_demo=True,
        ),
        Buyer(
            user_id=user.id,
            name="Pune Tomato Wholesaler",
            buyer_type="Trader",
            contact_name="Demo contact",
            contact_phone="+91-90000-00005",
            market_name="Pune Market Yard",
            district="Pune",
            state="Maharashtra",
            latitude=18.4900,
            longitude=73.8700,
            notes=f"{DEMO_DATA_NOTICE} Illustrative tomato buyer.",
            is_demo=True,
        ),
    ]
    db.add_all(buyers)
    db.commit()
    offers = [
        BuyerOffer(
            buyer_id=buyers[0].id,
            crop="Onion",
            variety="Bhima Super",
            offered_price_per_quintal=6150,
            min_quantity_quintals=5,
            max_quantity_quintals=80,
            offer_date=today,
            expiry_date=expiry,
            conditions="Farm-gate pickup; payment within 3 working days.",
            is_active=True,
            is_demo=True,
        ),
        BuyerOffer(
            buyer_id=buyers[1].id,
            crop="Onion",
            variety="Red onion",
            offered_price_per_quintal=6030,
            min_quantity_quintals=10,
            max_quantity_quintals=120,
            offer_date=today,
            expiry_date=expiry,
            conditions="Buyer arranges transport; assaying at collection centre.",
            is_active=True,
            is_demo=True,
        ),
        BuyerOffer(
            buyer_id=buyers[2].id,
            crop="Wheat",
            variety="HD-3086",
            offered_price_per_quintal=2510,
            min_quantity_quintals=20,
            max_quantity_quintals=200,
            offer_date=today,
            expiry_date=expiry,
            conditions="Moisture below 12%; cleaning charges apply.",
            is_active=True,
            is_demo=True,
        ),
        BuyerOffer(
            buyer_id=buyers[3].id,
            crop="Rice",
            variety="ADT-43",
            offered_price_per_quintal=3350,
            min_quantity_quintals=15,
            max_quantity_quintals=150,
            offer_date=today,
            expiry_date=expiry,
            conditions="Mill-gate delivery; quality grading on arrival.",
            is_active=True,
            is_demo=True,
        ),
        BuyerOffer(
            buyer_id=buyers[4].id,
            crop="Tomato",
            variety="Pusa Ruby",
            offered_price_per_quintal=2860,
            min_quantity_quintals=5,
            max_quantity_quintals=60,
            offer_date=today,
            expiry_date=today + timedelta(days=20),
            conditions="Harvest-day dispatch required.",
            is_active=True,
            is_demo=True,
        ),
    ]
    db.add_all(offers)
    db.commit()
    logger.info("Created %d demo buyers and %d offers", len(buyers), len(offers))


def _notifications(db: Session, user: User) -> None:
    if db.scalar(select(func.count(Notification.id)).where(Notification.user_id == user.id)):
        return
    db.add_all(
        [
            Notification(
                user_id=user.id,
                title="Welcome to AgriTwin",
                message=(
                    "Your demo account is ready. All demo farms, buyers and offers are "
                    "clearly labelled. Market prices and historical yields are real public data."
                ),
                category="info",
                is_read=False,
            ),
            Notification(
                user_id=user.id,
                title="Market data freshness",
                message=(
                    "The bundled Agmarknet slice ends in September 2026. Decisions add a "
                    "data-freshness risk penalty when prices are older than 90 days."
                ),
                category="warning",
                is_read=False,
            ),
            Notification(
                user_id=user.id,
                title="Crop-health screening limits",
                message=(
                    "Crop-health results are screening aids, not laboratory diagnoses. "
                    "Check the model mode badge on every result."
                ),
                category="info",
                is_read=True,
            ),
        ]
    )
    db.commit()


def _disease_classes(db: Session) -> None:
    if db.scalar(select(func.count(DiseaseClass.id))):
        return
    rows = [
        DiseaseClass(
            crop=info["crop"],
            name=name,
            display_name=info["display"],
            is_healthy=name.endswith("healthy"),
            description=info["description"],
            severity=info["severity"],
            inspection_steps=info["inspection"],
            preventive_practices=info["prevention"],
            expert_advice=info["expert"],
        )
        for name, info in CLASS_INFO.items()
    ]
    db.add_all(rows)
    db.commit()
    logger.info("Seeded %d crop-health classes", len(rows))


def _market_prices(db: Session) -> None:
    if db.scalar(select(func.count(MarketPriceRecord.id))):
        return
    path = BACKEND_DIR / "app" / "data" / "market_prices.csv"
    if not path.exists():
        logger.warning("Market price CSV not found at %s", path)
        return
    frame = pd.read_csv(path)
    frame["price_date"] = pd.to_datetime(frame["price_date"], format="ISO8601").dt.date
    rows = [
        MarketPriceRecord(
            crop=str(row.crop).strip(),
            market=str(row.market).strip(),
            state=str(row.state).strip(),
            district=str(row.district).strip(),
            variety=str(row.variety).strip() or "Other",
            grade=str(row.grade).strip() or "FAQ",
            price_date=row.price_date,
            min_price=float(row.min_price),
            max_price=float(row.max_price),
            modal_price=float(row.modal_price),
            unit=str(row.unit).strip() or "INR/quintal",
            source=str(row.source).strip() or "agmarknet_archive_2026",
            is_demo=False,
        )
        for row in frame.itertuples()
    ]
    db.add_all(rows)
    db.commit()
    logger.info("Seeded %d real market price observations", len(rows))


def _historical_yields(db: Session) -> None:
    if db.scalar(select(func.count(HistoricalYieldRecord.id))):
        return
    path = BACKEND_DIR / "app" / "data" / "historical_yield_sample.csv"
    if not path.exists():
        logger.warning("Historical yield sample not found at %s", path)
        return
    frame = pd.read_csv(path)
    rows = [
        HistoricalYieldRecord(
            state=str(row.state).strip(),
            district=str(row.district).strip(),
            crop=str(row.crop).strip(),
            season=str(row.season).strip(),
            year=int(row.year),
            area_hectares=float(row.area_hectares),
            production_quintals=float(row.production_tonnes) * 10.0,
            yield_per_hectare=float(row.yield_per_hectare),
            source=str(row.source).strip() or "india_crop_production_1997_2015",
            is_demo=False,
        )
        for row in frame.itertuples()
    ]
    db.add_all(rows)
    db.commit()
    logger.info("Seeded %d real historical yield records", len(rows))


def seed(db: Session) -> None:
    user = _demo_user(db)
    _demo_farms(db, user)
    _demo_crops(db, user)
    _demo_buyers(db, user)
    _notifications(db, user)
    _disease_classes(db)
    _market_prices(db)
    _historical_yields(db)
