"""Domain enums for Sentinela B3."""

from enum import Enum


class AssetType(str, Enum):
    STOCK = "STOCK"
    FII = "FII"
    UNIT = "UNIT"
    ETF = "ETF"
    BDR = "BDR"
    UNKNOWN = "UNKNOWN"

