"""Buyer and offer management."""

from __future__ import annotations

from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import NotFoundError
from app.models.buyer import Buyer, BuyerOffer
from app.models.user import User
from app.schemas.buyer import BuyerCreate, BuyerUpdate, OfferCreate, OfferUpdate
from app.schemas.common import validate_patch


def list_buyers(db: Session, user: User, crop: str | None = None) -> list[Buyer]:
    query = select(Buyer).where(Buyer.user_id == user.id).order_by(Buyer.name)
    buyers = list(db.scalars(query))
    if crop:
        crop_ids = {
            buyer.id
            for buyer in buyers
            if any(
                offer.crop == crop and offer.is_active and offer.expiry_date >= date.today()
                for offer in buyer.offers
            )
        }
        buyers = [buyer for buyer in buyers if buyer.id in crop_ids]
    return buyers


def create_buyer(db: Session, user: User, payload: BuyerCreate) -> Buyer:
    buyer = Buyer(user_id=user.id, **payload.model_dump(), is_demo=False)
    db.add(buyer)
    db.commit()
    db.refresh(buyer)
    return buyer


def update_buyer(db: Session, buyer: Buyer, payload: BuyerUpdate) -> Buyer:
    updates = payload.model_dump(exclude_unset=True)
    validate_patch(BuyerCreate, buyer, updates)
    for key, value in updates.items():
        setattr(buyer, key, value)
    db.commit()
    db.refresh(buyer)
    return buyer


def delete_buyer(db: Session, buyer: Buyer) -> None:
    db.delete(buyer)
    db.commit()


def get_buyer(db: Session, user: User, buyer_id: int) -> Buyer:
    buyer = db.get(Buyer, buyer_id)
    if buyer is None or buyer.user_id != user.id:
        raise NotFoundError("Buyer not found")
    return buyer


def list_offers(db: Session, buyer: Buyer) -> list[BuyerOffer]:
    return list(
        db.scalars(
            select(BuyerOffer)
            .where(BuyerOffer.buyer_id == buyer.id)
            .order_by(BuyerOffer.created_at.desc())
        )
    )


def create_offer(db: Session, buyer: Buyer, payload: OfferCreate) -> BuyerOffer:
    offer = BuyerOffer(buyer_id=buyer.id, **payload.model_dump(), is_demo=False)
    db.add(offer)
    db.commit()
    db.refresh(offer)
    return offer


def get_offer(db: Session, user: User, offer_id: int) -> BuyerOffer:
    offer = db.get(BuyerOffer, offer_id)
    if offer is None:
        raise NotFoundError("Offer not found")
    buyer = db.get(Buyer, offer.buyer_id)
    if buyer is None or buyer.user_id != user.id:
        raise NotFoundError("Offer not found")
    return offer


def update_offer(db: Session, offer: BuyerOffer, payload: OfferUpdate) -> BuyerOffer:
    updates = payload.model_dump(exclude_unset=True)
    validate_patch(OfferCreate, offer, updates)
    for key, value in updates.items():
        setattr(offer, key, value)
    db.commit()
    db.refresh(offer)
    return offer


def delete_offer(db: Session, offer: BuyerOffer) -> None:
    db.delete(offer)
    db.commit()


def active_offers_for_crop(
    db: Session, user: User, crop: str, today: date | None = None
) -> list[tuple[Buyer, BuyerOffer]]:
    today = today or date.today()
    rows = db.execute(
        select(Buyer, BuyerOffer)
        .join(BuyerOffer, BuyerOffer.buyer_id == Buyer.id)
        .where(
            Buyer.user_id == user.id,
            BuyerOffer.crop == crop,
            BuyerOffer.is_active.is_(True),
            BuyerOffer.expiry_date >= today,
        )
        .order_by(BuyerOffer.offered_price_per_quintal.desc())
    ).all()
    return [(row[0], row[1]) for row in rows]


def best_offer_price(db: Session, user: User, crop: str) -> float | None:
    offers = active_offers_for_crop(db, user, crop)
    return max((offer.offered_price_per_quintal for _, offer in offers), default=None)
