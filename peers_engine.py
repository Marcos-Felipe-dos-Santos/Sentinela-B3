"""Comparações descritivas por identidade e setor oficiais (F2C-7)."""

from __future__ import annotations

import logging
import math
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import UTC, datetime

from config import MAX_WORKERS

logger = logging.getLogger("Peers")


def _numero(valor: object) -> bool:
    return (
        isinstance(valor, (int, float))
        and not isinstance(valor, bool)
        and math.isfinite(valor)
    )


class PeersEngine:
    def __init__(self, market_engine) -> None:
        self.market = market_engine

    def comparar(self, ticker: str, setor: str | None = None) -> dict:
        """O argumento legado setor não substitui a referência oficial."""
        ticker = ticker.strip().upper()
        referencia = getattr(self.market, "referencia", None)
        indice = (
            referencia.indice(datetime.now(UTC)) if referencia is not None else None
        )
        base = {
            "Setor": None,
            "PL_Media_Peers": None,
            "PVP_Media_Peers": None,
            "DY_Media_Peers": None,
            "Peers_Utilizados": [],
        }
        if indice is None:
            return {
                **base,
                "erro": "Referência oficial indisponível; comparação indisponível.",
            }
        registro = indice.buscar(ticker)
        if (
            registro is None
            or registro.classe not in {"STOCK", "UNIT"}
            or not registro.setor
        ):
            return {
                **base,
                "erro": "Identidade, classe ou setor oficial não demonstrados.",
            }
        base["Setor"] = registro.setor
        alvos = sorted(
            r.ticker
            for r in indice.registros.values()
            if (
                r.ticker != ticker
                and r.classe == registro.classe
                and r.especie == registro.especie
                and r.setor == registro.setor
                and (not registro.cnpj or r.cnpj != registro.cnpj)
            )
        )
        if not alvos:
            return {
                **base,
                "erro": "Setor oficial sem pares de classe e espécie compatíveis.",
            }
        alvo = self.market.buscar_dados_ticker(ticker)
        modelo = (alvo or {}).get("modelo_bpp")
        if modelo not in {"empresa", "banco", "seguradora"}:
            return {**base, "erro": "modelo documental do ativo não demonstrado."}
        dados = []
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            futures = {
                executor.submit(self.market.buscar_dados_ticker, p): p for p in alvos
            }
            try:
                for future in as_completed(futures, timeout=10):
                    try:
                        d = future.result(timeout=2)
                        if (
                            isinstance(d, dict)
                            and d.get("ticker") == futures[future]
                            and _numero(d.get("preco_atual"))
                            and d["preco_atual"] > 0
                            and d.get("modelo_bpp") == modelo
                            and any(d.get(k) is not None for k in ("pl", "pvp", "roe"))
                        ):
                            dados.append(d)
                    except Exception:
                        logger.exception("Peer %s ignorado", futures[future])
            except TimeoutError:
                logger.warning("Timeout global na busca de peers (10s).")
        dados.sort(key=lambda d: d["ticker"])
        cobertura = {"esperados": len(alvos), "utilizados": len(dados)}
        avisos = (
            ["Cobertura curta: comparação parcial dos pares oficiais."]
            if len(dados) < len(alvos) or len(dados) < 2
            else []
        )
        if not dados:
            return {
                **base,
                "erro": "Não foi possível coletar pares com dados e modelo compatíveis.",
                "Cobertura": cobertura,
                "Avisos": avisos,
            }

        def media(campo: str) -> float | None:
            valores = [d.get(campo) for d in dados]
            # Sem política aprovada para misturar prejuízo/ausência: não selecionar
            # silenciosamente apenas as observações que tornariam a média favorável.
            if not all(_numero(v) and (campo != "pl" or v > 0) for v in valores):
                return None
            return round(sum(valores) / len(valores), 4)

        pl = media("pl")
        return {
            **base,
            "PL_Media_Peers": pl,
            "PVP_Media_Peers": media("pvp"),
            "DY_Media_Peers": media("dy"),
            "Peers_Utilizados": [d["ticker"] for d in dados],
            "Motivo_PL": "P/L não positivo, ausente ou inválido; comparação indisponível."
            if pl is None
            else None,
            "Cobertura": cobertura,
            "Avisos": avisos,
        }
