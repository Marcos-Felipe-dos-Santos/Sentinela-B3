"""Backtest PIT educacional por lente (ficha aprovada, decisões41/42).

A aritmética de retorno é separada da obtenção dos insumos. Preços e proventos
posteriores à análise medem o resultado realizado; não entram na ordenação em D.
O caminho legado continua separado e indisponível, conforme a decisão11.
"""

from __future__ import annotations

import hashlib
import json
import math
import sqlite3
from collections import Counter, defaultdict
from collections.abc import Mapping, Sequence
from datetime import date, datetime, time
from numbers import Real
from pathlib import Path
from statistics import median
from typing import Any
from zoneinfo import ZoneInfo

from sentinela.data.pit.serie_ajustada import ajustar

AVISO_EXPLORATORIO = "possível reapresentação posterior não observável"
HORIZONTES = (12, 24, 36)


def _finito(valor: object) -> bool:
    try:
        return (
            isinstance(valor, Real)
            and not isinstance(valor, bool)
            and math.isfinite(valor)
        )
    except OverflowError:
        return False


def formar_quintis(observacoes: Sequence[Mapping[str, Any]]) -> dict:
    """Ordenação aprovada: distância decrescente, código crescente, ceil(5i/n)."""
    validas, abstencoes = [], Counter()
    vistos = set()
    for obs in observacoes:
        ticker = obs["ticker"]
        if ticker in vistos:
            raise ValueError(f"ativo repetido no mesmo grupo: {ticker}")
        vistos.add(ticker)
        distancia = obs.get("distancia_ao_preco_pct")
        if obs.get("abstencao") or not _finito(distancia):
            abstencoes[obs.get("abstencao") or "distância ao preço indisponível"] += 1
        else:
            validas.append(obs)
    validas.sort(key=lambda o: (-o["distancia_ao_preco_pct"], o["ticker"]))
    n = len(validas)
    retornos = [o["retorno_total"] for o in validas if _finito(o.get("retorno_total"))]
    saida = {
        "quintis": {},
        "elegiveis": n,
        "abstencoes": dict(abstencoes),
        "mediana_retorno": median(retornos) if retornos else None,
        "motivo": "menos de 25 ativos elegíveis" if n < 25 else None,
        "empates_nos_cortes": 0,
    }
    if n < 25:
        return saida
    grupos = {q: [] for q in range(1, 6)}
    anterior = None
    for i, obs in enumerate(validas, 1):
        q = math.ceil(5 * i / n)
        grupos[q].append(obs["ticker"])
        if anterior is not None:
            q_anterior, distancia_anterior = anterior
            if q != q_anterior and obs["distancia_ao_preco_pct"] == distancia_anterior:
                saida["empates_nos_cortes"] += 1
        anterior = q, obs["distancia_ao_preco_pct"]
    saida["quintis"] = grupos
    return saida


def quintis_por_modo(observacoes: Sequence[Mapping[str, Any]]) -> dict:
    """Uma lente/data por chamada; estrito e exploratório nunca formam um grupo comum."""
    grupos = defaultdict(list)
    for obs in observacoes:
        modo = obs["modo"]
        if modo not in ("estrito", "exploratorio"):
            raise ValueError(f"modo histórico desconhecido: {modo}")
        grupos[modo].append(obs)
    return {
        modo: {
            **formar_quintis(grupo),
            "aviso": AVISO_EXPLORATORIO if modo == "exploratorio" else None,
        }
        for modo, grupo in sorted(grupos.items())
    }


def selecionar_horizonte(
    observacoes: Sequence[Mapping[str, Any]], horizonte: int, *, limite: date
) -> dict:
    """O mesmo corte por fim atende janela final e fronteira de calibração."""
    if horizonte not in HORIZONTES:
        raise ValueError("horizonte deve ser 12, 24 ou 36 meses")
    candidatas = [o for o in observacoes if o["horizonte"] == horizonte]
    completas = [dict(o) for o in candidatas if o["fim"] <= limite]
    return {"observacoes": completas, "incompletas": len(candidatas) - len(completas)}


def fronteira_calibracao(datas: Sequence[date]) -> date | None:
    """Só recebe datas em que a lente formou quintis; fronteira ceil(n/2), inclusiva."""
    ordenadas = sorted(set(datas))
    return ordenadas[math.ceil(len(ordenadas) / 2) - 1] if ordenadas else None


def _abstencao(motivo: str) -> dict:
    return {
        "retorno": None,
        "abstencao": motivo,
        "suspensao": False,
        "deslistada": False,
    }


def _preco_mantido(
    precos: Sequence[tuple[date, float]], alvo: date, eventos: Sequence[Mapping]
) -> tuple[float | None, str | None]:
    """Conserva o último preço na base posterior aos eventos, sem criar riqueza."""
    anteriores = [(dia, valor) for dia, valor in precos if dia < alvo]
    if not anteriores:
        return None, f"sem preço para manter em {alvo}"
    dia, bruto = anteriores[-1]
    registro = ajustar([(dia, bruto), (alvo, bruto)], eventos)[0]
    valor = registro.get("ajustado")
    if not _finito(valor) or valor <= 0:
        return None, registro.get("motivo") or "preço mantido não representável"
    return valor, None


def retorno_total(
    precos: Mapping[date, float],
    proventos: Sequence[Mapping[str, Any]] = (),
    eventos: Sequence[Mapping[str, Any]] = (),
    *,
    inicio: date,
    fim: date,
    deslistagem: date | None = None,
    suspensao_confirmada: bool = False,
    cdi: Mapping[date, float] | None = None,
    pregoes: Sequence[date] | None = None,
) -> dict:
    """Retorno bruto entre fechamentos, caixa reinvestido em (D,T] na mesma base.

    Insumos de mercado já identificados: proventos por ação da data ex; eventos
    reconciliados do papel. CDI em % ao dia (SGS12), fator DI em [L,T).
    Sem preço inicial ou dado necessário, abstenção; nunca cotação padrão favorável.
    Calendário explícito demonstra a cobertura para preço mantido e CDI faltante.
    """
    if inicio > fim:
        return _abstencao("intervalo de retorno invertido")
    if inicio not in precos:
        return _abstencao("fechamento de entrada indisponível")
    if deslistagem is not None and deslistagem > fim:
        deslistagem = None
    limite = min(deslistagem, fim) if deslistagem is not None else fim
    if limite < inicio:
        return _abstencao("último pregão negociado anterior à entrada")
    dentro = sorted((dia, p) for dia, p in precos.items() if inicio <= dia <= limite)
    if any(not _finito(p) or p <= 0 for _, p in dentro):
        return _abstencao("preço não positivo ou não finito no intervalo")
    if deslistagem is not None and limite not in precos:
        return _abstencao("último fechamento da deslistagem indisponível")
    suspensao = deslistagem is None and fim not in precos
    if suspensao:
        if not suspensao_confirmada:
            return _abstencao("estado terminal sem prova de suspensão ou deslistagem")
        if pregoes is None or fim not in pregoes:
            return _abstencao("cobertura do pregão final indisponível")
        mantido, motivo = _preco_mantido(dentro, fim, eventos)
        if motivo:
            return _abstencao(motivo)
        dentro.append((fim, mantido))
    serie = ajustar(dentro, eventos)
    for o in serie:
        if not _finito(o.get("ajustado")) or o["ajustado"] <= 0:
            return _abstencao(
                o.get("motivo") or "preço ajustado não representável no intervalo"
            )
    por_dia = {date.fromisoformat(o["data"]): o for o in serie}
    reinvestimento = 1.0
    caixas = defaultdict(list)
    for prov in proventos:
        ex = prov["data_ex"]
        if not inicio < ex <= limite:
            continue
        valor = prov.get("valor")
        if not _finito(valor) or valor < 0:
            return _abstencao("provento bruto inválido no intervalo")
        caixas[ex].append(valor)
    # Todos os direitos da mesma ex pertencem à quantidade anterior ao fechamento.
    for ex, parcelas in sorted(caixas.items()):
        valor = sum(parcelas)
        if not _finito(valor):
            return _abstencao("soma dos proventos não representável")
        if ex not in por_dia:
            if pregoes is None or ex not in pregoes:
                return _abstencao(f"fechamento da data ex indisponível: {ex}")
            bruto, motivo = _preco_mantido(dentro, ex, eventos)
            if motivo:
                return _abstencao(motivo)
            ajustada_ex = ajustar(sorted([*dentro, (ex, bruto)]), eventos)
            registro_ex = next(o for o in ajustada_ex if o["data"] == ex.isoformat())
            if registro_ex.get("ajustado") is None:
                return _abstencao(registro_ex["motivo"])
        else:
            registro_ex = por_dia[ex]
        ajustado = valor / registro_ex["fator"]
        reinvestimento *= 1 + ajustado / registro_ex["ajustado"]
    fator_caixa = 1.0
    if deslistagem is not None and limite < fim:
        if pregoes is None or limite not in pregoes or fim not in pregoes:
            return _abstencao("calendário do CDI indisponível no horizonte")
        taxas = cdi or {}
        for dia in sorted({p for p in pregoes if limite <= p < fim}):
            if dia not in taxas:
                return _abstencao(f"CDI indisponível no pregão {dia}")
        # A SGS12 também remunera dias bancários sem pregão na B3 (Fator DI).
        for dia, taxa in sorted(taxas.items()):
            if not limite <= dia < fim:
                continue
            if not _finito(taxa) or taxa <= -100:
                return _abstencao(f"CDI indisponível no dia {dia}")
            fator_caixa *= 1 + taxa / 100
    retorno = (
        serie[-1]["ajustado"] / serie[0]["ajustado"] * reinvestimento * fator_caixa - 1
    )
    if not math.isfinite(retorno):
        return _abstencao("retorno não finito")
    return {
        "retorno": retorno,
        "abstencao": None,
        "suspensao": suspensao,
        "deslistada": deslistagem is not None,
    }


class BacktestPIT:
    """Orquestra dados históricos, lentes, retornos e relatório sem usar o legado."""

    def __init__(
        self,
        conn: sqlite3.Connection,
        cadastro,
        *,
        hoje: date,
        cache_dir: str | Path,
    ) -> None:
        self.conn = conn
        self.cadastro = cadastro
        self.hoje = hoje
        self.cache_dir = Path(cache_dir)
        self._fca_tickers = None
        self._motivos_cancelamento = None

    def executar(
        self,
        datas: Sequence[date],
        *,
        horizontes: Sequence[int] = HORIZONTES,
        modo: str = "estrito",
    ) -> dict:
        from config import MACRO
        from fii_engine import FIIEngine
        from sentinela.data.pit import leitura
        from sentinela.data.providers import b3_indices, b3_proventos
        from sentinela.data.referencia import universo
        from sentinela.data.store import resultados
        from sentinela.services import historico
        from sentinela.services.analyze_asset import AnalysisService
        from technical_engine import TechnicalEngine
        from valuation_engine import ValuationEngine

        if modo not in leitura.MODOS:
            raise ValueError(f"modo histórico desconhecido: {modo!r}")
        if not datas or any(
            not isinstance(d, date) or isinstance(d, datetime) for d in datas
        ):
            raise ValueError("datas deve conter datas locais de análise")
        if any(h not in HORIZONTES for h in horizontes):
            raise ValueError("horizontes deve conter 12, 24 ou 36 meses")

        fuso = ZoneInfo("America/Sao_Paulo")
        fontes, observacoes, incompletas = [], [], Counter()
        datas_pregao = [
            date.fromisoformat(linha[0])
            for linha in self.conn.execute(
                "SELECT DISTINCT data FROM precos WHERE tipo_mercado = ? ORDER BY data",
                ("010",),
            )
        ]
        benchmarks = {
            serie: b3_indices.benchmarks_ate(self.conn, serie, date.max)
            for serie in ("IBOV", "CDI")
        }
        for dia in sorted(set(datas)):
            if dia >= self.hoje:
                raise ValueError("data de análise precisa ser anterior a hoje")
            if dia not in datas_pregao:
                raise ValueError(f"D precisa ser pregão carregado: {dia}")
            as_of = datetime.combine(dia, time.max, tzinfo=fuso)
            elegibilidade = universo.universo_backtest(
                self.conn,
                dia,
                self.cadastro,
                presenca_min=MACRO.LIQUIDEZ_PRESENCA_MIN,
                volume_acoes_min=MACRO.LIQUIDEZ_VOLUME_ACOES_MIN,
                volume_fii_min=MACRO.LIQUIDEZ_VOLUME_FII_MIN,
            )
            ativos = elegibilidade["elegiveis"]
            fontes.append({"D": dia.isoformat(), "universo": elegibilidade})
            servico = AnalysisService(
                None,
                ValuationEngine(),
                FIIEngine(),
                TechnicalEngine(),
                hoje=self.hoje,
                conexao_resultados=self.conn,
                motor_historico=lambda instante: historico.MotorHistorico(
                    self.conn,
                    instante,
                    self.cache_dir / instante.astimezone(fuso).date().isoformat(),
                    self.cadastro,
                    modo=modo,
                ),
            )
            for ativo in ativos:
                ticker = ativo["ticker"]
                resultado = servico.analisar(ticker, as_of, use_ai=False)
                registros = resultados.buscar(self.conn, ticker, as_of=as_of)
                atuais = [
                    r for r in registros if r.execucao_id == resultado.execucao_id
                ]
                lentes = {
                    registro.metodo: (
                        registro.resultado
                        if registro.resultado is not None
                        else {
                            "versao": registro.versao,
                            "abstencao": registro.motivo_abstencao,
                        }
                    )
                    for registro in atuais
                }
                dados_analise = dict(resultado.raw)
                dados_analise.pop("historico", None)
                dados_analise.pop("fontes", None)
                dados_analise = self._sem_proveniencia_instavel(dados_analise)
                hashes_fontes_pit = self._hashes_fontes_pit(
                    resultado.raw.get("cnpj"), dia
                )
                fontes.append(
                    {
                        "tipo": "analise_por_as_of",
                        "ticker": ticker,
                        "D": dia.isoformat(),
                        "dados": dados_analise,
                        "hashes_fontes_pit": hashes_fontes_pit,
                        "hashes_resultado_lente": sorted(
                            (
                                r.metodo,
                                r.versao,
                                self._hash(self._sem_proveniencia_instavel(r.resultado))
                                if r.resultado is not None
                                else self._hash({"abstencao": r.motivo_abstencao}),
                            )
                            for r in atuais
                        ),
                    }
                )
                preco_lente = resultado.raw.get("preco_atual")
                if not atuais and not lentes:
                    lentes = {
                        "analise": {
                            "abstencao": resultado.error or "análise sem lentes"
                        }
                    }
                for horizonte in horizontes:
                    fim, motivo_fim = self._fim_horizonte(dia, horizonte, datas_pregao)
                    if fim is None:
                        incompletas[horizonte] += len(lentes)
                        continue
                    retorno, entrada, retorno_ibov, retorno_cdi, evidencias = (
                        self._retornos(
                            ticker,
                            ativo.get("cnpj"),
                            dia,
                            fim,
                            datas_pregao,
                            benchmarks,
                            b3_proventos,
                        )
                    )
                    fontes.append(evidencias)
                    for nome, lente in sorted(lentes.items()):
                        valor = lente.get("valor")
                        abstencao = lente.get("abstencao")
                        distancia = lente.get("distancia_ao_preco_pct")
                        if abstencao is None and (not _finito(valor) or valor <= 0):
                            abstencao = "lente sem valor finito e positivo"
                        abstencao_retorno = retorno.get("abstencao")
                        observacoes.append(
                            {
                                "ticker": ticker,
                                "lente": nome,
                                "versao": lente.get("versao"),
                                "D": dia.isoformat(),
                                "fim": fim.isoformat(),
                                "horizonte": horizonte,
                                "modo": modo,
                                "preco_lente": preco_lente,
                                "preco_entrada": entrada,
                                "valor": valor if not abstencao else None,
                                "distancia_ao_preco_pct": distancia
                                if not abstencao
                                else None,
                                "abstencao": abstencao or motivo_fim,
                                "retorno_total": retorno.get("retorno"),
                                "abstencao_retorno": abstencao_retorno,
                                "retorno_ibov": retorno_ibov,
                                "retorno_cdi": retorno_cdi,
                                "suspensao": retorno.get("suspensao", False),
                                "deslistada": retorno.get("deslistada", False),
                                "motivo_deslistagem": evidencias["estado_terminal"].get(
                                    "motivo_deslistagem"
                                ),
                            }
                        )

        grupos = self._grupos(observacoes)
        resumo = self._resumir(observacoes, grupos, incompletas)
        hash_insumos = self._hash(fontes)
        sem_hash = {"observacoes": observacoes, "grupos": grupos, "resumo": resumo}
        hash_resultado = self._hash(sem_hash)
        return {
            "hash_insumos": hash_insumos,
            "hash_resultado": hash_resultado,
            "observacoes": observacoes,
            "grupos": grupos,
            "resumo": resumo,
        }

    @staticmethod
    def _fim_horizonte(dia: date, horizonte: int, datas: Sequence[date]):
        indice = dia.year * 12 + dia.month - 1 + horizonte
        ano, mes = divmod(indice, 12)
        mes += 1
        candidatos = [d for d in datas if d.year == ano and d.month == mes]
        if not candidatos:
            return None, "horizonte sem pregão final carregado"
        # Ficha §8: o mês só fecha com pregão observado depois dele (pendência F3-7a).
        if not any((d.year, d.month) > (ano, mes) for d in datas):
            return None, "horizonte sem mês final fechado"
        return max(candidatos), None

    def _retornos(
        self,
        ticker,
        cnpj,
        inicio,
        fim,
        datas,
        benchmarks,
        b3_proventos,
    ):
        linhas = self.conn.execute(
            "SELECT data, fechamento_centavos, fator_cotacao FROM precos "
            "WHERE codigo_negociacao = ? AND tipo_mercado = ? AND data >= ? AND data <= ? "
            "ORDER BY data",
            (ticker, "010", inicio.isoformat(), fim.isoformat()),
        ).fetchall()
        precos = {
            date.fromisoformat(d): fechamento / 100 / fator
            for d, fechamento, fator in linhas
        }
        ativo_linha = self.conn.execute(
            "SELECT isin FROM precos WHERE codigo_negociacao = ? AND tipo_mercado = ? "
            "AND data < ? ORDER BY data DESC LIMIT 1",
            (ticker, "010", inicio.isoformat()),
        ).fetchone()
        isin = ativo_linha[0] if ativo_linha else None
        if not precos or inicio not in precos:
            retorno = _abstencao("fechamento de entrada indisponível")
            # Sem entrada não há horizonte a classificar; a deslistagem fica sem efeito.
            estado = {
                "deslistagem": None,
                "suspensao_confirmada": False,
                "motivo_deslistagem": None,
            }
            evidencia = {"ticker": ticker, "precos": linhas, "estado_terminal": estado}
            return retorno, None, None, None, evidencia
        estado = self._estado_terminal(cnpj, ticker, fim, fim in precos)

        emissor = ticker[:4]
        relacao = b3_proventos.proventos_ate(
            self.conn,
            emissor,
            date.fromordinal(fim.toordinal() + 1),
            por_publicacao=True,
        )
        proventos = []
        motivo = relacao.get("abstencao")
        if motivo is None:
            sufixo = ticker[-1:]
            especie_esperada = {"3": "ON", "4": "PN"}.get(sufixo)
            if especie_esperada is None:
                motivo = "espécie do ticker não mapeada para proventos brutos"
            else:
                for item in relacao["proventos"]:
                    if item.get("especie") != especie_esperada:
                        continue
                    try:
                        valor = float(
                            item["valor_bruto"].replace(".", "").replace(",", ".")
                        )
                        cotado = float(
                            item["cotado_por"].replace(".", "").replace(",", ".")
                        )
                        ex = date.fromisoformat(item["data_ex"])
                    except (AttributeError, KeyError, TypeError, ValueError):
                        motivo = "provento sem valor, unidade ou data ex demonstrados"
                        break
                    if cotado <= 0 or valor < 0:
                        motivo = "provento bruto ou unidade inválidos"
                        break
                    if inicio < ex <= fim:
                        proventos.append({"data_ex": ex, "valor": valor / cotado})
                for item in relacao.get("sem_prova", []):
                    data_com = item.get("data_com")
                    try:
                        data_com = date.fromisoformat(data_com) if data_com else None
                    except ValueError:
                        data_com = None
                    if data_com is None or inicio <= data_com <= fim:
                        motivo = "relação de proventos contém registros sem prova no horizonte"
                        break
        if motivo:
            retorno = _abstencao(motivo)
        else:
            eventos_lidos = b3_proventos.eventos_ate(
                self.conn, emissor, date.fromordinal(fim.toordinal() + 1)
            )
            eventos, motivo_evento = [], None
            for evento in eventos_lidos["sem_prova"]:
                try:
                    data_com = date.fromisoformat(evento["data_com"])
                except (KeyError, TypeError, ValueError):
                    data_com = None
                if data_com is None or inicio <= data_com <= fim:
                    motivo_evento = "evento em ações sem prova no horizonte"
                    break
            for evento in eventos_lidos["eventos"]:
                ex = evento.get("data_ex")
                if ex is None:
                    try:
                        data_com = date.fromisoformat(evento["data_com"])
                    except (KeyError, TypeError, ValueError):
                        data_com = None
                    if data_com is not None and inicio <= data_com <= fim:
                        motivo_evento = (
                            evento.get("motivo_data_ex")
                            or "evento em ações sem data ex demonstrada no horizonte"
                        )
                        break
                    continue
                data_ex = date.fromisoformat(ex)
                if not inicio < data_ex <= fim:
                    continue
                if isin is None:
                    # sem o ISIN do ticker, o evento do emissor pode ser do papel
                    motivo_evento = (
                        "ISIN do ticker não demonstrado para associar eventos em ações"
                    )
                    break
                if evento.get("isin") != isin:
                    if evento.get("isin") is None:
                        motivo_evento = (
                            "evento em ações sem ISIN para associar ao ticker"
                        )
                    continue
                if evento.get("fator") is None or evento.get("motivo_sem_fator"):
                    motivo_evento = (
                        evento.get("motivo_sem_fator") or "fator do evento ausente"
                    )
                    break
                eventos.append(
                    {
                        "data_com": date.fromisoformat(evento["data_com"]),
                        "data_ex": data_ex,
                        "fator": evento["fator"],
                    }
                )
            if motivo_evento:
                retorno = _abstencao(motivo_evento)
            else:
                taxas = {
                    date.fromisoformat(item["data"]): item["valor"]
                    for item in benchmarks["CDI"]
                    if inicio <= date.fromisoformat(item["data"]) < fim
                }
                retorno = retorno_total(
                    precos,
                    proventos,
                    eventos,
                    inicio=inicio,
                    fim=fim,
                    deslistagem=estado["deslistagem"],
                    suspensao_confirmada=estado["suspensao_confirmada"],
                    cdi=taxas,
                    pregoes=datas,
                )
        serie_ibov = {r["data"]: r["valor"] for r in benchmarks["IBOV"]}
        retorno_ibov = (
            serie_ibov[fim.isoformat()] / serie_ibov[inicio.isoformat()] - 1
            if inicio.isoformat() in serie_ibov and fim.isoformat() in serie_ibov
            else None
        )
        taxas = [
            r["valor"]
            for r in benchmarks["CDI"]
            if inicio.isoformat() <= r["data"] < fim.isoformat()
        ]
        dias = [
            r["data"]
            for r in benchmarks["CDI"]
            if inicio.isoformat() <= r["data"] < fim.isoformat()
        ]
        preg_b3 = {d.isoformat() for d in datas if inicio <= d < fim}
        retorno_cdi = None
        if preg_b3.issubset(set(dias)) and len(dias) == len(set(dias)):
            retorno_cdi = math.prod(1 + taxa / 100 for taxa in taxas) - 1
        evidencia = {
            "ticker": ticker,
            "precos": linhas,
            "proventos": relacao,
            "eventos": eventos_lidos if motivo is None else [],
            "ibov": [
                r
                for r in benchmarks["IBOV"]
                if r["data"] in (inicio.isoformat(), fim.isoformat())
            ],
            "cdi": [
                r
                for r in benchmarks["CDI"]
                if inicio.isoformat() <= r["data"] < fim.isoformat()
            ],
            "isin": isin,
            "motivo": motivo,
            "estado_terminal": estado,
        }
        return retorno, precos.get(inicio), retorno_ibov, retorno_cdi, evidencia

    def _estado_terminal(self, cnpj, ticker, fim, preco_final_disponivel):
        if not cnpj:
            return {
                "deslistagem": None,
                "suspensao_confirmada": False,
                "motivo_deslistagem": None,
            }
        from sentinela.data.referencia import universo

        if self._fca_tickers is None:
            referencias = universo._fca_por_referencia(self.conn, date.max.isoformat())
            self._fca_tickers = {}
            for (cnpj_linha, referencia), linhas in referencias.items():
                for linha in linhas or ():
                    codigo = (linha.get("Codigo_Negociacao") or "").strip().upper()
                    if not codigo:
                        continue
                    chave = (cnpj_linha, codigo)
                    anterior = self._fca_tickers.get(chave)
                    if anterior is None or referencia > anterior[0]:
                        self._fca_tickers[chave] = (referencia, linha)
        registro = self._fca_tickers.get((cnpj, ticker.upper()))
        if registro is None:
            return {
                "deslistagem": None,
                "suspensao_confirmada": False,
                "motivo_deslistagem": None,
            }
        _, linha = registro
        fim_negociacao = linha.get("Data_Fim_Negociacao") or ""
        try:
            data_fim = date.fromisoformat(fim_negociacao) if fim_negociacao else None
        except ValueError:
            data_fim = None
        if fim_negociacao and data_fim is None:
            return {
                "deslistagem": None,
                "suspensao_confirmada": False,
                "motivo_deslistagem": None,
            }
        if data_fim is not None and data_fim <= fim:
            return {
                "deslistagem": data_fim,
                "suspensao_confirmada": False,
                "motivo_deslistagem": self._motivo_cancelamento(cnpj),
            }
        try:
            referencia_atual = date.fromisoformat(registro[0])
        except ValueError:
            return {
                "deslistagem": None,
                "suspensao_confirmada": False,
                "motivo_deslistagem": None,
            }
        return {
            "deslistagem": None,
            "motivo_deslistagem": None,
            "suspensao_confirmada": (
                not preco_final_disponivel
                and (data_fim is not None or referencia_atual >= fim)
            ),
        }

    def _motivo_cancelamento(self, cnpj):
        if self._motivos_cancelamento is None:
            self._motivos_cancelamento = {}
            colunas = set(getattr(self.cadastro, "columns", ()))
            if {"CNPJ_CIA", "MOTIVO_CANCEL"} <= colunas:
                for linha in self.cadastro.to_dict("records"):
                    chave = "".join(
                        caractere
                        for caractere in str(linha.get("CNPJ_CIA") or "")
                        if caractere.isdigit()
                    )
                    motivo = str(linha.get("MOTIVO_CANCEL") or "").strip()
                    if chave and motivo:
                        self._motivos_cancelamento[chave] = motivo
        chave = "".join(caractere for caractere in str(cnpj) if caractere.isdigit())
        return self._motivos_cancelamento.get(chave)

    @staticmethod
    def _grupos(observacoes):
        blocos = defaultdict(list)
        for obs in observacoes:
            blocos[(obs["lente"], obs["D"], obs["fim"], obs["horizonte"])].append(obs)
        resultado = []
        for (lente, dia, fim, horizonte), itens in sorted(blocos.items()):
            validas = [o for o in itens if o.get("abstencao") is None]
            modos = quintis_por_modo(validas) if validas else {}
            for modo, grupo in modos.items():
                por_ticker = {o["ticker"]: o for o in validas if o["modo"] == modo}
                retornos_quintis = {}
                for quintil, tickers in grupo["quintis"].items():
                    ativos = [por_ticker[t] for t in tickers]
                    retornos = [
                        o["retorno_total"]
                        for o in ativos
                        if _finito(o.get("retorno_total"))
                    ]
                    retornos_sem_deslistadas = [
                        o["retorno_total"]
                        for o in ativos
                        if not o.get("deslistada") and _finito(o.get("retorno_total"))
                    ]
                    retornos_quintis[f"Q{quintil}"] = {
                        "retorno_medio": sum(retornos) / len(retornos)
                        if retornos
                        else None,
                        "retorno_medio_sem_deslistadas": (
                            sum(retornos_sem_deslistadas)
                            / len(retornos_sem_deslistadas)
                            if retornos_sem_deslistadas
                            else None
                        ),
                        "n_retorno_sem_deslistadas": len(retornos_sem_deslistadas),
                        "n_retorno": len(retornos),
                        "n_sem_retorno": len(ativos) - len(retornos),
                        "retornos_ativos": retornos,
                        "retorno_ibov": next(
                            (
                                o["retorno_ibov"]
                                for o in ativos
                                if _finito(o.get("retorno_ibov"))
                            ),
                            None,
                        ),
                        "retorno_cdi": next(
                            (
                                o["retorno_cdi"]
                                for o in ativos
                                if _finito(o.get("retorno_cdi"))
                            ),
                            None,
                        ),
                        "n_deslistadas": sum(bool(o.get("deslistada")) for o in ativos),
                        "n_suspensas": sum(bool(o.get("suspensao")) for o in ativos),
                    }
                resultado.append(
                    {
                        "lente": lente,
                        "D": dia,
                        "fim": fim,
                        "horizonte": horizonte,
                        "modo": modo,
                        **grupo,
                        "retornos_quintis": retornos_quintis,
                    }
                )
        return resultado

    @staticmethod
    def _resumir(observacoes, grupos, incompletas):
        resumo = {"horizontes_incompletos": dict(incompletas), "lentes": []}
        chaves = sorted({(o["lente"], o["horizonte"], o["modo"]) for o in observacoes})
        for lente, horizonte, modo in chaves:
            itens = [
                o
                for o in observacoes
                if (o["lente"], o["horizonte"], o["modo"]) == (lente, horizonte, modo)
            ]
            grupos_lente = [
                g
                for g in grupos
                if (g["lente"], g["horizonte"], g["modo"]) == (lente, horizonte, modo)
            ]
            abstencoes = Counter(o["abstencao"] for o in itens if o["abstencao"])
            abstencoes_retorno = Counter(
                o["abstencao_retorno"] for o in itens if o["abstencao_retorno"]
            )
            quintis = {}
            for numero in range(1, 6):
                nome = f"Q{numero}"
                por_data = [
                    (g, g["retornos_quintis"].get(nome))
                    for g in grupos_lente
                    if nome in g["retornos_quintis"]
                ]
                retornos = [
                    dados["retorno_medio"]
                    for _, dados in por_data
                    if dados and _finito(dados.get("retorno_medio"))
                ]
                retornos_sem_deslistadas = [
                    dados["retorno_medio_sem_deslistadas"]
                    for _, dados in por_data
                    if dados and _finito(dados.get("retorno_medio_sem_deslistadas"))
                ]
                retornos_intra = [
                    _iqr(dados["retornos_ativos"])
                    for _, dados in por_data
                    if dados and len(dados["retornos_ativos"]) > 1
                ]
                comparacoes = {
                    "ibov": [
                        (dados["retorno_medio"], dados["retorno_ibov"])
                        for _, dados in por_data
                        if dados
                        and _finito(dados.get("retorno_medio"))
                        and _finito(dados.get("retorno_ibov"))
                    ],
                    "cdi": [
                        (dados["retorno_medio"], dados["retorno_cdi"])
                        for _, dados in por_data
                        if dados
                        and _finito(dados.get("retorno_medio"))
                        and _finito(dados.get("retorno_cdi"))
                    ],
                }
                tamanhos = [len(g["quintis"].get(numero, [])) for g, _ in por_data]
                quintis[nome] = {
                    "mediana_retorno": median(retornos) if retornos else None,
                    "mediana_retorno_sem_deslistadas": (
                        median(retornos_sem_deslistadas)
                        if retornos_sem_deslistadas
                        else None
                    ),
                    "primeiro_quartil_retorno_sem_deslistadas": _quartil(
                        retornos_sem_deslistadas, 0.25
                    ),
                    "terceiro_quartil_retorno_sem_deslistadas": _quartil(
                        retornos_sem_deslistadas, 0.75
                    ),
                    "media_retorno_sem_deslistadas": (
                        sum(retornos_sem_deslistadas) / len(retornos_sem_deslistadas)
                        if retornos_sem_deslistadas
                        else None
                    ),
                    "n_datas_com_retorno_sem_deslistadas": len(
                        retornos_sem_deslistadas
                    ),
                    "primeiro_quartil_retorno": _quartil(retornos, 0.25),
                    "terceiro_quartil_retorno": _quartil(retornos, 0.75),
                    "media_retorno": sum(retornos) / len(retornos)
                    if retornos
                    else None,
                    "n_datas_com_retorno": len(retornos),
                    "n_datas_sem_ibov": sum(
                        dados
                        and _finito(dados.get("retorno_medio"))
                        and not _finito(dados.get("retorno_ibov"))
                        for _, dados in por_data
                    ),
                    "n_datas_sem_cdi": sum(
                        dados
                        and _finito(dados.get("retorno_medio"))
                        and not _finito(dados.get("retorno_cdi"))
                        for _, dados in por_data
                    ),
                    "fracao_supera_ibov": _fracao_supera(comparacoes["ibov"]),
                    "fracao_supera_cdi": _fracao_supera(comparacoes["cdi"]),
                    "n_datas_com_ibov": len(comparacoes["ibov"]),
                    "n_datas_com_cdi": len(comparacoes["cdi"]),
                    "n_ativos_por_data": {
                        "minimo": min(tamanhos) if tamanhos else None,
                        "mediana": median(tamanhos) if tamanhos else None,
                        "maximo": max(tamanhos) if tamanhos else None,
                    },
                    "dispersao_iqr_mediana": median(retornos_intra)
                    if retornos_intra
                    else None,
                    "n_deslistadas": sum(
                        dados["n_deslistadas"] for _, dados in por_data if dados
                    ),
                    "n_suspensas": sum(
                        dados["n_suspensas"] for _, dados in por_data if dados
                    ),
                }
            formados = [g for g in grupos_lente if g["quintis"]]
            q1 = {
                g["D"]: g["retornos_quintis"].get("Q1", {}).get("retorno_medio")
                for g in formados
            }
            q5 = {
                g["D"]: g["retornos_quintis"].get("Q5", {}).get("retorno_medio")
                for g in formados
            }
            diferencas = [
                q1[d] - q5[d]
                for d in q1.keys() & q5.keys()
                if _finito(q1[d]) and _finito(q5[d])
            ]
            motivos_deslistagem = Counter(
                o.get("motivo_deslistagem") or "motivo não informado"
                for o in itens
                if o.get("deslistada")
            )
            resumo["lentes"].append(
                {
                    "lente": lente,
                    "horizonte": horizonte,
                    "modo": modo,
                    "universo_elegivel": len(itens),
                    "com_valor": sum(o["abstencao"] is None for o in itens),
                    "cobertura": (
                        sum(o["abstencao"] is None for o in itens) / len(itens)
                        if itens
                        else None
                    ),
                    "abstencoes": dict(abstencoes),
                    "abstencoes_retorno": dict(abstencoes_retorno),
                    "contagem_motivo_deslistagem": dict(motivos_deslistagem),
                    "datas_com_quintis": len(formados),
                    "ultima_data_D_horizonte_completo": max(
                        (o["D"] for o in itens), default=None
                    ),
                    "quintis": quintis,
                    "q1_menos_q5": {
                        "mediana": median(diferencas) if diferencas else None,
                        "n_datas": len(diferencas),
                    },
                }
            )
        return resumo

    @staticmethod
    def _hash(valor):
        texto = json.dumps(
            _normalizar_hash(valor),
            ensure_ascii=False,
            sort_keys=True,
            allow_nan=False,
        )
        return hashlib.sha256(texto.encode("utf-8")).hexdigest()

    def _hashes_fontes_pit(self, cnpj, dia):
        if not cnpj:
            return {"abstencao": "CNPJ não demonstrado na análise"}
        texto = dia.isoformat()
        consultas = {
            "demonstracoes": (
                (
                    "SELECT DISTINCT d.hash_sha256 FROM demonstracoes d "
                    "JOIN entregas e ON e.cnpj = d.cnpj AND e.documento = d.documento "
                    "AND e.dt_refer = d.dt_refer AND e.versao = d.versao "
                    "WHERE d.cnpj = ? AND e.dt_receb < ? AND d.dt_fim_exerc < ? "
                    "ORDER BY d.hash_sha256"
                ),
                (cnpj, texto, texto),
            ),
            "composicao": (
                (
                    "SELECT DISTINCT c.hash_sha256 FROM composicao_capital c "
                    "JOIN entregas e ON e.cnpj = c.cnpj AND e.documento = c.documento "
                    "AND e.dt_refer = c.dt_refer AND e.versao = c.versao "
                    "WHERE c.cnpj = ? AND e.dt_receb < ? AND c.dt_refer < ? "
                    "ORDER BY c.hash_sha256"
                ),
                (cnpj, texto, texto),
            ),
            "fca": (
                (
                    "SELECT DISTINCT l.hash_sha256 FROM fca_linhas l "
                    "JOIN fca_entregas e ON e.cnpj = l.cnpj AND e.dt_refer = l.dt_refer "
                    "AND e.versao = CAST(l.versao AS INTEGER) "
                    "WHERE l.cnpj = ? AND e.dt_receb < ? AND l.dt_refer < ? "
                    "ORDER BY l.hash_sha256"
                ),
                (cnpj, texto, texto),
            ),
            "informe_fii": (
                (
                    "SELECT DISTINCT hash_sha256 FROM fii_informe_linhas "
                    "WHERE cnpj = ? AND data_entrega < ? AND dt_refer < ? "
                    "ORDER BY hash_sha256"
                ),
                (cnpj, texto, texto),
            ),
            "series_macro": (
                (
                    "SELECT DISTINCT hash_sha256 FROM series_macro "
                    "WHERE data < ? AND (divulgacao IS NULL OR divulgacao = '' "
                    "OR divulgacao < ?) ORDER BY hash_sha256"
                ),
                (texto, texto),
            ),
        }
        return {
            nome: [linha[0] for linha in self.conn.execute(sql, parametros)]
            for nome, (sql, parametros) in consultas.items()
        }

    @classmethod
    def _sem_proveniencia_instavel(cls, valor):
        if isinstance(valor, Mapping):
            return {
                str(chave): cls._sem_proveniencia_instavel(item)
                for chave, item in valor.items()
                if str(chave).lower()
                not in {
                    "fontes",
                    "proveniencia",
                    "coleta",
                    "data_coleta",
                    "hash_sha256",
                }
            }
        if isinstance(valor, (list, tuple)):
            return [cls._sem_proveniencia_instavel(item) for item in valor]
        return valor


def _quartil(valores: Sequence[float], fracao: float) -> float | None:
    ordenados = sorted(valores)
    if not ordenados:
        return None
    posicao = (len(ordenados) - 1) * fracao
    baixo = math.floor(posicao)
    alto = math.ceil(posicao)
    return ordenados[baixo] + (ordenados[alto] - ordenados[baixo]) * (posicao - baixo)


def _iqr(valores: Sequence[float]) -> float:
    return _quartil(valores, 0.75) - _quartil(valores, 0.25)


def _fracao_supera(pares: Sequence[tuple[float, float]]) -> float | None:
    if not pares:
        return None
    return sum(a > b for a, b in pares) / len(pares)


def _normalizar_hash(valor):
    if isinstance(valor, (date, datetime)):
        return valor.isoformat()
    if isinstance(valor, Mapping):
        return {
            str(chave): _normalizar_hash(item)
            for chave, item in valor.items()
            if str(chave).lower() not in {"coleta", "data_coleta"}
        }
    if isinstance(valor, (list, tuple)):
        return [_normalizar_hash(item) for item in valor]
    if isinstance(valor, float) and not math.isfinite(valor):
        return {"numero_nao_finito": "nan" if math.isnan(valor) else str(valor)}
    if isinstance(valor, (str, int, float, bool)) or valor is None:
        return valor
    escalar = getattr(valor, "item", None)
    if callable(escalar):
        return _normalizar_hash(escalar())
    return str(valor)
