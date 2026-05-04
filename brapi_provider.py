"""Optional Brapi provider for supplemental market fundamentals."""

import logging
import os
from typing import Any, Dict, Optional

import requests

logger = logging.getLogger("BrapiProvider")

_BASE_URL = "https://brapi.dev/api"
_TIMEOUT = 10


def _normalizar_ticker(ticker: str) -> str:
    return str(ticker or "").upper().replace(".SA", "").strip()


def _to_float(value: Any) -> Optional[float]:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _positive_float(value: Any) -> Optional[float]:
    numero = _to_float(value)
    if numero is None or numero <= 0:
        return None
    return numero


def _percent_to_decimal(value: Any, *, assume_subunit_percent: bool = False) -> Optional[float]:
    numero = _to_float(value)
    if numero is None:
        return None
    if numero < 0:
        return None
    if numero > 1 or (assume_subunit_percent and numero > 0.25):
        numero = numero / 100
    return numero


def _first_number(*values: Any) -> Optional[float]:
    for value in values:
        numero = _to_float(value)
        if numero is not None:
            return numero
    return None


def _first_value(raw: Dict[str, Any], *keys: str) -> Any:
    nested = (
        raw.get("fundamentalist")
        or raw.get("fundamentals")
        or raw.get("fundamental")
        or {}
    )
    for key in keys:
        for source in (raw, nested):
            if isinstance(source, dict) and key in source:
                return source.get(key)
    return None


class BrapiProvider:
    """Provider opcional de dados via Brapi API."""

    def __init__(self) -> None:
        self._token: Optional[str] = os.environ.get("BRAPI_TOKEN")
        if not self._token:
            logger.info("[Brapi] BRAPI_TOKEN nao encontrado; provider desabilitado")

    @property
    def disponivel(self) -> bool:
        """Retorna True se o token esta configurado."""
        return bool(self._token)

    def _get(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        """Faz GET seguro na API Brapi."""
        if not self._token:
            return None

        query = dict(params or {})
        query["token"] = self._token

        try:
            resp = requests.get(
                f"{_BASE_URL}{endpoint}",
                params=query,
                timeout=_TIMEOUT,
            )
            if resp.status_code != 200:
                logger.warning(f"[Brapi] HTTP {resp.status_code} para {endpoint}")
                return None

            data = resp.json()
            if "error" in data:
                logger.warning(f"[Brapi] Erro API: {data['error']}")
                return None

            return data

        except (requests.RequestException, ValueError) as e:
            logger.warning(f"[Brapi] Request falhou para {endpoint}: {e}")
            return None

    def _primeiro_resultado(self, ticker: str, params: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        ticker_norm = _normalizar_ticker(ticker)
        if not ticker_norm:
            return None

        data = self._get(f"/quote/{ticker_norm}", params=params)
        if not data:
            return None

        results = data.get("results", [])
        if not results:
            return None

        return results[0]

    def get_quote(self, ticker: str) -> Optional[Dict[str, Any]]:
        """Busca cotacao atual de um ticker."""
        quote = self._primeiro_resultado(ticker)
        if not quote:
            return None

        preco = _to_float(quote.get("regularMarketPrice"))
        if preco is None:
            return None

        return {
            "preco_atual": preco,
            "quote_type": quote.get("quoteType", quote.get("type", "")),
        }

    def get_fundamentals(self, ticker: str) -> Optional[Dict[str, Any]]:
        """Busca e normaliza indicadores fundamentalistas disponiveis."""
        raw = self._primeiro_resultado(ticker, params={"fundamental": "true"})
        if not raw:
            return None

        campos = {
            "preco_atual": _positive_float(_first_value(raw, "regularMarketPrice")),
            "pl": _positive_float(_first_value(raw, "priceEarnings", "trailingPE", "pl")),
            "pvp": _positive_float(_first_value(raw, "priceToBookRatio", "priceToBook", "pvp")),
            "roe": _percent_to_decimal(_first_value(raw, "returnOnEquity", "roe")),
            "dy": _percent_to_decimal(
                _first_value(raw, "dividendYield", "dy"),
                assume_subunit_percent=True,
            ),
            "divida_liq_ebitda": _to_float(_first_number(
                _first_value(raw, "netDebtToEbitda"),
                _first_value(raw, "debtToEbitda"),
                _first_value(raw, "dividaLiquidaEbitda"),
                _first_value(raw, "divida_liq_ebitda"),
            )),
            "lpa": _positive_float(
                _first_value(raw, "earningsPerShare", "eps", "trailingEps", "lpa")
            ),
            "vpa": _positive_float(
                _first_value(raw, "bookValue", "bookValuePerShare", "vpa")
            ),
            "quote_type": _first_value(raw, "quoteType", "type") or "",
        }

        if campos.get("dy") is not None and campos["dy"] > 0.30:
            campos["dy"] = None
        if campos.get("roe") is not None and campos["roe"] > 2:
            campos["roe"] = None
        if campos.get("divida_liq_ebitda") is not None and campos["divida_liq_ebitda"] < 0:
            campos["divida_liq_ebitda"] = None

        normalizado = {
            chave: valor
            for chave, valor in campos.items()
            if valor is not None and valor != ""
        }
        if not normalizado:
            return None

        logger.info(
            f"[Brapi] Fundamentos {_normalizar_ticker(ticker)}: "
            f"P/L={normalizado.get('pl', 'N/A')}"
        )
        return normalizado
