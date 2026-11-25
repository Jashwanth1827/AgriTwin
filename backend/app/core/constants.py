"""Domain constants shared by API validation, seeding and ML metadata."""

from __future__ import annotations

INDIAN_STATES: list[str] = [
    "Andaman and Nicobar Islands",
    "Andhra Pradesh",
    "Arunachal Pradesh",
    "Assam",
    "Bihar",
    "Chandigarh",
    "Chhattisgarh",
    "Dadra and Nagar Haveli and Daman and Diu",
    "Delhi",
    "Goa",
    "Gujarat",
    "Haryana",
    "Himachal Pradesh",
    "Jammu and Kashmir",
    "Jharkhand",
    "Karnataka",
    "Kerala",
    "Ladakh",
    "Lakshadweep",
    "Madhya Pradesh",
    "Maharashtra",
    "Manipur",
    "Meghalaya",
    "Mizoram",
    "Nagaland",
    "Odisha",
    "Puducherry",
    "Punjab",
    "Rajasthan",
    "Sikkim",
    "Tamil Nadu",
    "Telangana",
    "Tripura",
    "Uttar Pradesh",
    "Uttarakhand",
    "West Bengal",
]

SEASONS: list[str] = ["Kharif", "Rabi", "Summer", "Whole Year", "Late Kharif"]

GROWTH_STAGES: list[str] = [
    "Sowing/Germination",
    "Vegetative",
    "Flowering",
    "Grain/Fruit filling",
    "Maturity",
    "Harvest ready",
]

CROPS: list[str] = [
    "Rice",
    "Wheat",
    "Maize",
    "Cotton",
    "Soyabean",
    "Groundnut",
    "Onion",
    "Tomato",
    "Potato",
    "Sugarcane",
    "Chickpea",
    "Mustard",
    "Chilli",
    "Banana",
]

SOIL_TYPES: list[str] = [
    "Alluvial",
    "Black (Regur)",
    "Red",
    "Laterite",
    "Sandy",
    "Loamy",
    "Clay",
    "Sandy loam",
    "Silt",
    "Other",
]

BUYER_TYPES: list[str] = [
    "Trader",
    "Commission agent",
    "Processor",
    "Cooperative",
    "FPO",
    "Exporter",
    "Retailer",
    "Government procurement",
]

VEHICLE_TYPES: list[str] = ["tempo", "mini_truck", "truck", "large_truck", "tractor_trolley"]

TRANSPORT_MODES: list[str] = ["road"]

RISK_PREFERENCES: list[str] = ["low", "medium", "high"]

UNITS = {
    "price": "INR/quintal",
    "quantity": "quintal",
    "area": "hectare",
    "yield": "quintal/hectare",
    "distance": "km",
}

DEMO_DATA_NOTICE = (
    "Demo data: this record was generated for product demonstration and does not "
    "represent a real buyer, offer, farm or person."
)

AGMARKNET_SOURCE = "agmarknet_archive_2026"
CROP_PRODUCTION_SOURCE = "india_crop_production_1997_2015"
