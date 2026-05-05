"""Thin analysis service over the existing dict-based engines."""

from __future__ import annotations

from typing import Any, Optional

import pandas as pd

from config import FIIS_CONHECIDOS, UNITS_CONHECIDAS
from sentinela.domain.models import AnalysisResult


class AnalysisService:
    """Orchestrates the current engines without changing their dict contracts."""

    def __init__(
        self,
        market_engine: Any,
        valuation_engine: Any,
        fii_engine: Any,
        technical_engine: Any,
        peers_engine: Optional[Any] = None,
        ai_engine: Optional[Any] = None,
        repository: Optional[Any] = None,
    ) -> None:
        self.market_engine = market_engine
        self.valuation_engine = valuation_engine
        self.fii_engine = fii_engine
        self.technical_engine = technical_engine
        self.peers_engine = peers_engine
        self.ai_engine = ai_engine
        self.repository = repository

    def analyze(self, ticker: str, use_ai: bool = True, persist: bool = True) -> AnalysisResult:
        """Analyze one asset through the same current engine sequence used by the UI."""
        ticker_norm = str(ticker or "").upper().strip()
        dados = self.market_engine.buscar_dados_ticker(ticker_norm)
        if not dados or "erro" in dados:
            return AnalysisResult(
                ticker=ticker_norm,
                success=False,
                error="DADOS INSUFICIENTES",
                data_quality={
                    "dados_parciais": True,
                    "campos_faltantes": ["market_data"],
                    "warnings": ["Market data unavailable"],
                },
                raw={},
            )

        is_fii = self._is_fii(ticker_norm, dados)
        if is_fii:
            analise = self.fii_engine.analisar(dados)
            peers_data: dict[str, Any] = {}
        else:
            analise = self.valuation_engine.processar(dados)
            peers_data = (
                self.peers_engine.comparar(ticker_norm)
                if self.peers_engine is not None
                else {}
            )

        if analise is None:
            return AnalysisResult(
                ticker=ticker_norm,
                is_fii=is_fii,
                success=False,
                error="DADOS INSUFICIENTES",
                market=dados,
                fundamentals=dados,
                data_quality=dados,
                raw=dados,
            )

        hist = dados.get("historico", pd.DataFrame())
        tech_data = self.technical_engine.calcular_indicadores(hist)

        dados.update(analise)
        dados["tech"] = tech_data

        ai_content = None
        if self.ai_engine is not None and use_ai:
            ia_resp = self.ai_engine.analisar(ticker_norm, dados)
            ai_content = ia_resp.get("content") if isinstance(ia_resp, dict) else ia_resp
            dados["analise_ia"] = ai_content

        if self.repository is not None and persist:
            dados_salvar = {key: value for key, value in dados.items() if key != "historico"}
            self.repository.salvar_analise(dados_salvar)

        return AnalysisResult(
            ticker=ticker_norm,
            is_fii=is_fii,
            success=True,
            market=dados,
            fundamentals=dados,
            data_quality=dados,
            valuation=analise,
            technical=tech_data,
            peers=peers_data,
            ai_analysis=ai_content,
            raw=dados,
        )

    @staticmethod
    def _is_fii(ticker: str, dados: dict[str, Any]) -> bool:
        return (
            ticker in FIIS_CONHECIDOS
            or (
                dados.get("quote_type") == "MUTUALFUND"
                or (
                    "11" in ticker
                    and "SA" not in ticker
                    and ticker not in UNITS_CONHECIDAS
                )
            )
        )
