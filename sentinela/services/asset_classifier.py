"""Pure asset classification service for B3 tickers.

A classe vem de dado oficial, nunca do sufixo (F2A-20, armadilha 14). Ordem de consulta:
1. `dados['classe_ativo']`, que a cascata preenche a partir do índice oficial;
2. o índice local (`<pasta de dados>/referencia/indice.json`), lido sem rede na primeira consulta;
3. `FIIS_CONHECIDOS` e `UNITS_CONHECIDAS`;
4. ticker terminado em 11 sem dado oficial fica `UNKNOWN` (pode ser FII, unit, ETF ou BDR);
   os demais seguem como ação, como antes.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from config import FIIS_CONHECIDOS, UNITS_CONHECIDAS
from sentinela.data.referencia.carga import pasta_de_dados
from sentinela.data.referencia.indice import carregar_indice
from sentinela.data.referencia.registro import Indice
from sentinela.domain.enums import AssetType

logger = logging.getLogger(__name__)


def _classe(valor: Any) -> AssetType | None:
    try:
        return AssetType(str(valor).upper().strip()) if valor else None
    except ValueError:
        return None


class AssetClassifier:
    """Classifies assets from official data, with the known lists as fallback."""

    def __init__(
        self,
        fiis_conhecidos: set[str] | list[str] | None = None,
        units_conhecidas: set[str] | list[str] | None = None,
        pasta_dados: Path | None = None,
    ) -> None:
        self.pasta_dados = pasta_dados
        self._indice: Indice | None = None
        self._indice_lido = False
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

        oficial = _classe((dados or {}).get("classe_ativo"))
        if oficial is not None:
            return oficial

        indice = self._indice_local()
        registro = indice.buscar(ticker_norm) if indice is not None else None
        if registro is not None and (classe := _classe(registro.classe)) is not None:
            return classe

        if self.is_unit(ticker_norm):
            return AssetType.UNIT
        if ticker_norm in self.fiis_conhecidos:
            return AssetType.FII
        if ticker_norm.endswith("11"):
            return AssetType.UNKNOWN

        return AssetType.STOCK

    def _indice_local(self) -> Indice | None:
        """O índice salvo, lido uma vez e sem rede; `None` se não existe ou está ilegível."""
        if not self._indice_lido:
            self._indice_lido = True
            pasta = (self.pasta_dados or pasta_de_dados()) / "referencia"
            try:
                self._indice = carregar_indice(pasta)
            except (OSError, ValueError, KeyError, TypeError) as erro:
                logger.warning("Índice oficial ilegível em %s: %s", pasta, erro)
        return self._indice

    def is_fii(self, ticker: str | None, dados: dict | None = None) -> bool:
        return self.classify(ticker, dados) == AssetType.FII

    def is_unit(self, ticker: str | None) -> bool:
        return self.normalize_ticker(ticker) in self.units_conhecidas

    def normalize_ticker(self, ticker: str | None) -> str:
        ticker_norm = str(ticker or "").upper().strip()
        ticker_norm = ticker_norm.removesuffix(".SA")
        return ticker_norm.strip()

    def _normalize_collection(self, tickers: Any) -> set[str]:
        return {
            ticker_norm
            for ticker in (tickers or [])
            if (ticker_norm := self.normalize_ticker(ticker))
        }
