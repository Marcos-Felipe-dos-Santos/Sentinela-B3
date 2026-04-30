"""Brapi Provider — fonte opcional de dados de mercado.

Usa a API gratuita da Brapi (brapi.dev) como fonte complementar.
Requer BRAPI_TOKEN no ambiente. Se ausente, retorna None silenciosamente.

Uso:
    from brapi_provider import BrapiProvider
    brapi = BrapiProvider()
    quote = brapi.get_quote("PETR4")       # dict ou None
    fundamentos = brapi.get_fundamentals("PETR4")  # dict ou None
"""

import logging
import os
from typing import Any, Dict, Optional

import requests

logger = logging.getLogger("BrapiProvider")

_BASE_URL = "https://brapi.dev/api"
_TIMEOUT = 10


class BrapiProvider:
    """Provider opcional de dados via Brapi API."""

    def __init__(self) -> None:
        self._token: Optional[str] = os.environ.get("BRAPI_TOKEN")
        if not self._token:
            logger.info(
                "[Brapi] BRAPI_TOKEN não encontrado no ambiente — "
                "provider desabilitado (sem impacto)"
            )

    @property
    def disponivel(self) -> bool:
        """Retorna True se o token está configurado."""
        return self._token is not None

    def _get(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        """Faz GET seguro na API Brapi.

        Args:
            endpoint: Caminho relativo da API (ex: "/quote/PETR4").
            params: Parâmetros de query adicionais.

        Returns:
            Dict com resposta JSON ou None em caso de falha.
        """
        if not self._token:
            return None

        params = params or {}
        params["token"] = self._token

        try:
            resp = requests.get(
                f"{_BASE_URL}{endpoint}",
                params=params,
                timeout=_TIMEOUT,
            )
            if resp.status_code != 200:
                logger.warning(
                    f"[Brapi] HTTP {resp.status_code} para {endpoint}"
                )
                return None

            data = resp.json()
            if "error" in data:
                logger.warning(f"[Brapi] Erro API: {data['error']}")
                return None

            return data

        except requests.RequestException as e:
            logger.warning(f"[Brapi] Request falhou para {endpoint}: {e}")
            return None

    def get_quote(self, ticker: str) -> Optional[Dict[str, Any]]:
        """Busca cotação atual de um ticker.

        Args:
            ticker: Código do ativo (ex: "PETR4").

        Returns:
            Dict com dados da cotação ou None se indisponível.
        """
        ticker = ticker.upper().replace(".SA", "")
        data = self._get(f"/quote/{ticker}")
        if not data:
            return None

        results = data.get("results", [])
        if not results:
            return None

        quote = results[0]
        logger.info(f"[Brapi] ✓ Cotação {ticker}: R${quote.get('regularMarketPrice', '?')}")
        return quote

    def get_fundamentals(self, ticker: str) -> Optional[Dict[str, Any]]:
        """Busca dados fundamentalistas de um ticker.

        Args:
            ticker: Código do ativo (ex: "PETR4").

        Returns:
            Dict com indicadores fundamentalistas ou None se indisponível.
        """
        ticker = ticker.upper().replace(".SA", "")
        data = self._get(f"/quote/{ticker}", params={"fundamental": "true"})
        if not data:
            return None

        results = data.get("results", [])
        if not results:
            return None

        fundamentals = results[0]
        logger.info(
            f"[Brapi] ✓ Fundamentos {ticker}: "
            f"P/L={fundamentals.get('priceEarnings', 'N/A')}"
        )
        return fundamentals
