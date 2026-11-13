"""Thin analysis service over the existing dict-based engines."""

from __future__ import annotations

import sqlite3
from collections.abc import Callable
from contextlib import closing
from datetime import date, datetime
from typing import Any
from uuid import uuid4
from zoneinfo import ZoneInfo

import pandas as pd

from sentinela.data.store import resultados, unico
from sentinela.domain.apresentacao import mesclar_analise
from sentinela.domain.enums import AssetType
from sentinela.domain.models import AnalysisResult
from sentinela.services.asset_classifier import AssetClassifier


def contexto_classe_ia(dados: dict[str, Any]) -> str:
    """Descreve a prova da classe sem transformar inferência em elegibilidade."""
    valor = dados.get("classe_ativo")
    try:
        classe = AssetType(str(valor or "UNKNOWN").upper().strip()).value
    except ValueError:
        classe = "UNKNOWN"
    if classe == "UNKNOWN":
        return (
            "Classe do ativo: UNKNOWN; origem: indisponível; motivo: classe não demonstrada; "
            "não presumir tipo nem elegibilidade."
        )
    referencia = dados.get("referencia_oficial")
    fonte = referencia.get("fonte") if isinstance(referencia, dict) else None
    if isinstance(fonte, dict):
        fonte = fonte.get("arquivo")
    if isinstance(fonte, str) and fonte.strip():
        return (
            f"Classe do ativo: {classe}; origem: oficial ({fonte.strip()}); "
            "motivo: registro da referência oficial fornecido com a classe."
        )
    riscos = dados.get("riscos_dados")
    motivos = (
        [
            r
            for r in riscos
            if isinstance(r, str)
            and ("referência" in r.lower() or "índice" in r.lower())
        ]
        if isinstance(riscos, list)
        else []
    )
    motivo = (
        "; ".join(motivos)
        or "referência oficial não demonstrada para a classe fornecida"
    )
    return (
        f"Classe do ativo: {classe}; origem: inferida a partir da classe fornecida, "
        f"sem fonte oficial comprovada; motivo: {motivo}. "
        "A inferência não comprova elegibilidade para métodos."
    )


# F3-3d, decisão 15: com as_of passado, o serviço não chama `peers_engine`.
MOTIVO_PARES = "comparação de pares indisponível para data passada"
MOTIVO_SEM_BANCO = "análise para data passada indisponível: banco único histórico não abriu"


class AnalysisService:
    """Orchestrates the current engines without changing their dict contracts."""

    def __init__(
        self,
        market_engine: Any,
        valuation_engine: Any,
        fii_engine: Any,
        technical_engine: Any,
        peers_engine: Any | None = None,
        ai_engine: Any | None = None,
        repository: Any | None = None,
        asset_classifier: Any | None = None,
        *,
        hoje: date | None = None,
        conexao_resultados: sqlite3.Connection | None = None,
        motor_historico: Callable[[datetime], Any] | None = None,
    ) -> None:
        self.hoje = hoje
        # F3-3d: fábrica do motor da cascata numa data passada (banco único, sem fonte corrente).
        self.motor_historico = motor_historico
        self.conexao_resultados = conexao_resultados
        self.market_engine = market_engine
        self.valuation_engine = valuation_engine
        self.fii_engine = fii_engine
        self.technical_engine = technical_engine
        self.peers_engine = peers_engine
        self.ai_engine = ai_engine
        self.repository = repository
        self.asset_classifier = (
            asset_classifier if asset_classifier is not None else AssetClassifier()
        )

    def analisar(
        self, ticker: str, as_of: datetime, *, use_ai: bool = True
    ) -> AnalysisResult:
        """Orquestra a análise atual; a borda fornece o instante e a referência de hoje.

        Com `as_of` de um dia anterior a hoje (São Paulo), a cascata é a do banco único em D
        (`motor_historico`, F3-3d): nenhuma fonte corrente e nenhum par (decisão 15). A
        compatibilidade `analyze` mantém seus chamadores antigos; esta entrada usa o mesmo
        fluxo sem a persistência legada.
        """
        if self.hoje is None:
            raise ValueError("referência de hoje deve ser fornecida pela borda")
        if not isinstance(as_of, datetime) or as_of.utcoffset() is None:
            raise ValueError("as_of exige datetime com fuso horário")
        dia = as_of.astimezone(ZoneInfo("America/Sao_Paulo")).date()
        ticker = str(ticker or "").upper().strip()
        if dia < self.hoje:
            from sentinela.services import historico

            # DD-63: a IA conhece fatos posteriores a D; na análise retroativa ela fica de fora
            use_ai = False

            if self.motor_historico is not None:
                motor = self.motor_historico(as_of)
                result = self._executar(
                    ticker, use_ai=use_ai, persist=False, as_of=as_of,
                    market_engine=motor, pares=False,
                )  # fmt: skip
            else:
                import config

                # o mesmo acesso ao banco único da série macro (desligado nos testes)
                banco = config._conexao_series_macro()
                if banco is None:
                    result = AnalysisResult(
                        ticker=ticker, success=False, error=MOTIVO_SEM_BANCO,
                        raw={"abstencao": MOTIVO_SEM_BANCO, "lentes": {}},
                    )  # fmt: skip
                else:
                    with closing(banco):
                        result = self._executar(
                            ticker, use_ai=use_ai, persist=False, as_of=as_of,
                            market_engine=historico.motor_do_banco(banco, as_of),
                            pares=False,
                        )  # fmt: skip
        elif dia != self.hoje:
            motivo = "análise para data futura indisponível"
            result = AnalysisResult(
                ticker=ticker,
                success=False,
                error=motivo,
                raw={"abstencao": motivo, "lentes": {}},
            )
        else:
            result = self._executar(ticker, use_ai=use_ai, persist=False, as_of=as_of)
        result.as_of = as_of.isoformat()
        result.execucao_id = str(uuid4())
        if self.conexao_resultados is not None:
            self._gravar_resultados(self.conexao_resultados, result, as_of)
        else:
            with closing(sqlite3.connect(unico.caminho_padrao())) as conn:
                self._gravar_resultados(conn, result, as_of)
        return result

    @staticmethod
    def _gravar_resultados(
        conn: sqlite3.Connection, result: AnalysisResult, as_of: datetime
    ) -> None:
        """Cada lente conserva versão, valor ou motivo, sem sobrescrever execução."""
        lentes = result.raw.get("lentes") or {}
        proveniencia = {
            campo: result.raw.get(campo)
            for campo in (
                "fonte_preco",
                "data_preco",
                "motivo_data_preco",
                "fonte_fundamentos",
            )
        }
        if not proveniencia["data_preco"] and not proveniencia["motivo_data_preco"]:
            # F3-A-F3 (BUG-3-16): nunca `None` silencioso no registro imutável.
            proveniencia["motivo_data_preco"] = "data do preço não informada"
        proveniencia["fontes"] = {
            nome: bloco["proveniencia"]
            for nome, bloco in result.raw.items()
            if isinstance(bloco, dict) and "proveniencia" in bloco
        }
        if not lentes:
            motivo = (
                result.error
                or result.raw.get("abstencao")
                or "análise sem lentes e sem motivo"
            )
            resultados.gravar(
                conn,
                ticker=result.ticker,
                as_of=as_of,
                metodo="analise",
                versao="1.0",
                execucao_id=result.execucao_id,
                proveniencia=proveniencia,
                motivo_abstencao=motivo,
            )
            return
        for nome, lente in lentes.items():
            motivo = lente.get("abstencao")
            resultados.gravar(
                conn,
                ticker=result.ticker,
                as_of=as_of,
                metodo=nome,
                versao=lente["versao"],
                execucao_id=result.execucao_id,
                proveniencia={**proveniencia, "lente": lente},
                resultado=None if motivo else lente,
                motivo_abstencao=motivo,
            )

    def analyze(
        self, ticker: str, use_ai: bool = True, persist: bool = True
    ) -> AnalysisResult:
        """Compatibilidade da API antiga, sem expor corte temporal não validado."""
        return self._executar(ticker, use_ai=use_ai, persist=persist)

    def _executar(
        self,
        ticker: str,
        use_ai: bool = True,
        persist: bool = True,
        *,
        as_of: datetime | None = None,
        market_engine: Any | None = None,
        pares: bool = True,
    ) -> AnalysisResult:
        """Executa a sequência atual de motores compartilhada pelas entradas do serviço."""
        ticker_norm = str(ticker or "").upper().strip()
        mercado = self.market_engine if market_engine is None else market_engine
        if as_of is not None and self._has_explicit_method(mercado, "buscar_dados_ticker_em"):
            dados = mercado.buscar_dados_ticker_em(ticker_norm, as_of)
        else:
            dados = mercado.buscar_dados_ticker(ticker_norm)
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

        is_fii = self.asset_classifier.is_fii(ticker_norm, dados)
        if is_fii:
            analise = (
                self.fii_engine.analisar(dados)
                if as_of is None
                else self.fii_engine.analisar(dados, as_of=as_of)
            )
            peers_data: dict[str, Any] = {}
        else:
            analise = (
                self.valuation_engine.processar(dados)
                if as_of is None
                else self.valuation_engine.processar(dados, as_of=as_of)
            )
            peers_data = (
                {"abstencao": MOTIVO_PARES}
                if not pares
                else self.peers_engine.comparar(ticker_norm)
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

        dados = mesclar_analise(dados, analise)
        dados["tech"] = tech_data

        ai_content = None
        ia_resp = None
        if self.ai_engine is not None and use_ai:
            ia_resp = self.ai_engine.analisar(ticker_norm, dados)
            ai_content = (
                ia_resp.get("content") if isinstance(ia_resp, dict) else ia_resp
            )
            dados["analise_ia"] = ai_content

        result = AnalysisResult(
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
            extra={
                "analise_motor": analise,
                **({"resposta_ia": ia_resp} if ia_resp is not None else {}),
            },
        )
        if self.repository is not None and persist:
            dados_salvar = {
                key: value for key, value in dados.items() if key != "historico"
            }
            if self._has_explicit_method(self.repository, "save_run"):
                self.repository.save_run(result)
            else:
                self.repository.salvar_analise(dados_salvar)

        return result

    @staticmethod
    def _has_explicit_method(obj: Any, method_name: str) -> bool:
        if method_name in getattr(obj, "__dict__", {}):
            return callable(getattr(obj, method_name))
        if any(method_name in vars(cls) for cls in type(obj).__mro__):
            return callable(getattr(obj, method_name))
        return False
