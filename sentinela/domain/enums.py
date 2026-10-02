"""Domain enums for Sentinela B3."""

from enum import Enum


class AssetType(str, Enum):
    STOCK = "STOCK"
    FII = "FII"
    UNIT = "UNIT"
    ETF = "ETF"
    BDR = "BDR"
    UNKNOWN = "UNKNOWN"


class Regime(str, Enum):
    """Regime de taxa de um método de valuation (armadilha 1: real e nominal não se misturam)."""

    REAL = "REAL"
    NOMINAL = "NOMINAL"
    SEM_TAXA = "SEM_TAXA"


class Perfil(str, Enum):
    """Perfil da empresa na V1: renda (dividendos) ou crescimento (reinveste lucros)."""

    RENDA = "RENDA"
    CRESCIMENTO = "CRESCIMENTO"
