"""Import every ORM model so that ``Base.metadata`` is complete."""

from app.models.buyer import Buyer, BuyerOffer
from app.models.crop_health import (
    CropHealthPrediction,
    DiseaseClass,
    ModelVersion,
    Recommendation,
)
from app.models.decision import DecisionFactor, DecisionResult
from app.models.farm import Crop, Farm, UploadedFile
from app.models.market import MarketForecast, MarketPriceRecord
from app.models.report import Report
from app.models.transport import TransportationEstimate
from app.models.user import Notification, RevokedToken, User
from app.models.yield_ import HistoricalYieldRecord, WeatherRecord, YieldPrediction

__all__ = [
    "Buyer",
    "BuyerOffer",
    "Crop",
    "CropHealthPrediction",
    "DecisionFactor",
    "DecisionResult",
    "DiseaseClass",
    "Farm",
    "HistoricalYieldRecord",
    "MarketForecast",
    "MarketPriceRecord",
    "ModelVersion",
    "Notification",
    "Recommendation",
    "Report",
    "RevokedToken",
    "TransportationEstimate",
    "UploadedFile",
    "User",
    "WeatherRecord",
    "YieldPrediction",
]
