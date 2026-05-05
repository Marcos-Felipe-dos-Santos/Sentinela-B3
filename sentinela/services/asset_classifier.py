"""Pure asset classification service for B3 tickers."""

from __future__ import annotations

from typing import Any

from config import FIIS_CONHECIDOS, UNITS_CONHECIDAS
from sentinela.domain.enums import AssetType


class AssetClassifier:
    """Classifies assets using the current intended Sentinela B3 rules."""

    def __init__(
        self,
        fiis_conhecidos: set[str] | list[str] | None = None,
        units_conhecidas: set[str] | list[str] | None = None,
    ) -> None:
        self.fiis_conhecidos = self._normalize_collection(
            FIIS_CONHECIDOS if fiis_conhecidos is None else fiis_conhecidos
        )
        self.units_conhecidas = self._normalize_collection(
            UNITS_CONHECIDAS if units_conhecidas is None else units_conhecidas
        )

    def classify(self, ticker: str | None, dados: dict | None = None) -> AssetType:
        ticker_norm = self.normalize_ticker(ticker)
        if not ticker_norm:
            return AssetType.UNKNOWN

        if self.is_unit(ticker_norm):
            return AssetType.UNIT

        quote_type = str((dados or {}).get("quote_type") or "").upper().strip()
        if ticker_norm in self.fiis_conhecidos:
            return AssetType.FII
        if quote_type == "MUTUALFUND":
            return AssetType.FII
        if ticker_norm.endswith("11"):
            return AssetType.FII

        return AssetType.STOCK

    def is_fii(self, ticker: str | None, dados: dict | None = None) -> bool:
        return self.classify(ticker, dados) == AssetType.FII

    def is_unit(self, ticker: str | None) -> bool:
        return self.normalize_ticker(ticker) in self.units_conhecidas

    def normalize_ticker(self, ticker: str | None) -> str:
        ticker_norm = str(ticker or "").upper().strip()
        if ticker_norm.endswith(".SA"):
            ticker_norm = ticker_norm[:-3]
        return ticker_norm.strip()

    def _normalize_collection(self, tickers: Any) -> set[str]:
        return {
            ticker_norm
            for ticker in (tickers or [])
            if (ticker_norm := self.normalize_ticker(ticker))
        }

