"""Buyer and offer routes."""

from __future__ import annotations

from fastapi import APIRouter, Query, status

from app.api.deps import CurrentUser, DbSession
from app.schemas.buyer import (
    BuyerCreate,
    BuyerDetail,
    BuyerOut,
    BuyerUpdate,
    OfferCreate,
    OfferOut,
    OfferUpdate,
)
from app.schemas.common import Message
from app.services import buyers as buyer_service

router = APIRouter(tags=["buyers"])


@router.get("/buyers", response_model=list[BuyerOut])
def list_buyers(
    user: CurrentUser,
    db: DbSession,
    crop: str | None = Query(default=None),
) -> list[BuyerOut]:
    return [BuyerOut.model_validate(row) for row in buyer_service.list_buyers(db, user, crop)]


@router.post("/buyers", response_model=BuyerOut, status_code=status.HTTP_201_CREATED)
def create_buyer(payload: BuyerCreate, user: CurrentUser, db: DbSession) -> BuyerOut:
    return BuyerOut.model_validate(buyer_service.create_buyer(db, user, payload))


@router.get("/buyers/{buyer_id}", response_model=BuyerDetail)
def get_buyer(buyer_id: int, user: CurrentUser, db: DbSession) -> BuyerDetail:
    buyer = buyer_service.get_buyer(db, user, buyer_id)
    detail = BuyerDetail.model_validate(buyer)
    detail.offers = [OfferOut.model_validate(offer) for offer in buyer.offers]
    return detail


@router.patch("/buyers/{buyer_id}", response_model=BuyerOut)
def update_buyer(
    buyer_id: int, payload: BuyerUpdate, user: CurrentUser, db: DbSession
) -> BuyerOut:
    buyer = buyer_service.get_buyer(db, user, buyer_id)
    return BuyerOut.model_validate(buyer_service.update_buyer(db, buyer, payload))


@router.delete("/buyers/{buyer_id}", response_model=Message)
def delete_buyer(buyer_id: int, user: CurrentUser, db: DbSession) -> Message:
    buyer = buyer_service.get_buyer(db, user, buyer_id)
    buyer_service.delete_buyer(db, buyer)
    return Message(message="Buyer deleted")


@router.get("/buyers/{buyer_id}/offers", response_model=list[OfferOut])
def list_offers(buyer_id: int, user: CurrentUser, db: DbSession) -> list[OfferOut]:
    buyer = buyer_service.get_buyer(db, user, buyer_id)
    return [OfferOut.model_validate(row) for row in buyer_service.list_offers(db, buyer)]


@router.post(
    "/buyers/{buyer_id}/offers",
    response_model=OfferOut,
    status_code=status.HTTP_201_CREATED,
)
def create_offer(
    buyer_id: int, payload: OfferCreate, user: CurrentUser, db: DbSession
) -> OfferOut:
    buyer = buyer_service.get_buyer(db, user, buyer_id)
    return OfferOut.model_validate(buyer_service.create_offer(db, buyer, payload))


@router.patch("/offers/{offer_id}", response_model=OfferOut)
def update_offer(
    offer_id: int, payload: OfferUpdate, user: CurrentUser, db: DbSession
) -> OfferOut:
    offer = buyer_service.get_offer(db, user, offer_id)
    return OfferOut.model_validate(buyer_service.update_offer(db, offer, payload))


@router.delete("/offers/{offer_id}", response_model=Message)
def delete_offer(offer_id: int, user: CurrentUser, db: DbSession) -> Message:
    offer = buyer_service.get_offer(db, user, offer_id)
    buyer_service.delete_offer(db, offer)
    return Message(message="Offer deleted")
