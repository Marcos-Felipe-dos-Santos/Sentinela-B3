"""Proposta de calibração da banda neutra fora da amostra (F3-8d, ficha do backtest §9).

Duas etapas, separadas para que a calibração possa ser refeita sem repetir as análises:

1. ``--executar``: roda o ``BacktestPIT`` sobre o banco real, aberto só para leitura
   (``ATTACH ... mode=ro``), e grava as observações em ``outputs/``. Os resultados das
   análises vão para um banco novo dentro da pasta de saída; o banco real não é escrito.
   O código do backtest só lê as tabelas públicas (preços, proventos, índices, CVM PIT).
2. ``--observacoes``: lê esse JSON e calcula, por lente e por horizonte, a fronteira
   ``ceil(n/2)`` das datas em que a lente formou quintis, a banda na metade inicial e a
   descrição na metade final. Sem datas com quintis, a lente se abstém com o motivo.

A banda é a mediana de |distância ao preço| na metade de calibração: vem da dispersão
das lentes (decisões da 2C, §2), não do retorno. Os retornos só descrevem os três
estados; nada é otimizado. Resultado é proposta para o Marcos, sem efeito em código,
ficha ou apresentação. Saída só em ``outputs/``.

Uso:
    python scripts/banda_neutra_fase3.py --executar --banco sentinela_store.db \
        --saida outputs/f3-8d [--datas 2023-06-30 ...] [--limite-por-classe N] \
        [--classes STOCK UNIT]
    python scripts/banda_neutra_fase3.py --observacoes outputs/f3-8d/observacoes.json \
        --saida outputs/f3-8d
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from collections import Counter, defaultdict
from collections.abc import Iterable, Mapping, Sequence
from datetime import date, datetime
from pathlib import Path
from statistics import fmean, median
from typing import Any
from zoneinfo import ZoneInfo

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

from backtesting.backtest_pit import (
    HORIZONTES,
    _finito,
    formar_quintis,
    fronteira_calibracao,
)

MODO = "estrito"
SEM_QUINTIS = "lente sem data com quintis formados"
LENTE_SEM_ANALISE = "analise"


def _dia(valor: str | date) -> date:
    return valor if isinstance(valor, date) else date.fromisoformat(valor)


def datas_fim_de_mes(pregoes: Iterable[date], inicio: date) -> list[date]:
    """Último pregão de cada mês fechado (há pregão observado num mês posterior)."""
    ultimos: dict[tuple[int, int], date] = {}
    for dia in pregoes:
        chave = (dia.year, dia.month)
        if dia >= inicio and (chave not in ultimos or dia > ultimos[chave]):
            ultimos[chave] = dia
    meses = sorted(ultimos)
    return [ultimos[m] for m in meses[:-1]] if meses else []


def conferir_calibracao(observacoes: Sequence[Mapping[str, Any]], fronteira: date):
    """Decisão 17: nenhuma observação de calibração termina depois da fronteira."""
    for obs in observacoes:
        if _dia(obs["fim"]) > fronteira:
            raise ValueError(
                f"observação de calibração termina depois da fronteira {fronteira}: "
                f"{obs['lente']} {obs['ticker']} D={obs['D']} fim={obs['fim']} "
                f"h={obs['horizonte']}"
            )


def _datas_com_quintis(observacoes: Sequence[Mapping[str, Any]]) -> list[date]:
    por_data = defaultdict(list)
    for obs in observacoes:
        por_data[obs["D"]].append(obs)
    return sorted(
        _dia(d) for d, itens in por_data.items() if formar_quintis(itens)["quintis"]
    )


def _estado(distancia: float, banda: float) -> str:
    if distancia > banda:
        return "sinal positivo"
    if distancia < -banda:
        return "sinal negativo"
    return "neutro"


def _descrever(observacoes: Sequence[Mapping[str, Any]], banda: float) -> dict:
    estados: dict[str, list] = {
        "sinal positivo": [],
        "neutro": [],
        "sinal negativo": [],
    }
    for obs in observacoes:
        estados[_estado(obs["distancia_ao_preco_pct"], banda)].append(obs)
    saida = {}
    for nome, itens in estados.items():
        com_retorno = [o for o in itens if _finito(o.get("retorno_total"))]
        excesso = [
            o["retorno_total"] - o["retorno_cdi"]
            for o in com_retorno
            if _finito(o.get("retorno_cdi"))
        ]
        saida[nome] = {
            "n": len(itens),
            "n_retorno": len(com_retorno),
            "retorno_medio": fmean(o["retorno_total"] for o in com_retorno)
            if com_retorno
            else None,
            "n_excesso_cdi": len(excesso),
            "excesso_cdi_medio": fmean(excesso) if excesso else None,
        }
    return saida


def calibrar_lente(observacoes: Sequence[Mapping[str, Any]], horizonte: int) -> dict:
    """Uma lente, um horizonte, modo estrito; nunca mistura lentes."""
    itens = [
        o for o in observacoes if o["horizonte"] == horizonte and o["modo"] == MODO
    ]
    datas = _datas_com_quintis(itens)
    base = {
        "horizonte": horizonte,
        "observacoes": len(itens),
        "datas_com_quintis": len(datas),
    }
    if not datas:
        abst = Counter(
            o["abstencao"] or "distância ao preço indisponível" for o in itens
        )
        return {**base, "abstencao": SEM_QUINTIS, "motivos": dict(abst.most_common())}
    fronteira = fronteira_calibracao(datas)
    com_quintis = {d.isoformat() for d in datas}
    validas = [
        o
        for o in itens
        if o["D"] in com_quintis
        and not o.get("abstencao")
        and _finito(o.get("distancia_ao_preco_pct"))
    ]
    primeira = [o for o in validas if _dia(o["D"]) <= fronteira]
    calibracao = [o for o in primeira if _dia(o["fim"]) <= fronteira]
    validacao = [o for o in validas if _dia(o["D"]) > fronteira]
    conferir_calibracao(calibracao, fronteira)
    saida = {
        **base,
        "fronteira": fronteira.isoformat(),
        "excluidas_pela_fronteira": len(primeira) - len(calibracao),
        "n_calibracao": len(calibracao),
        "n_validacao": len(validacao),
    }
    if not calibracao:
        return {
            **saida,
            "abstencao": "nenhuma observação de calibração termina até a fronteira",
        }
    banda = median(abs(o["distancia_ao_preco_pct"]) for o in calibracao)
    return {
        **saida,
        "abstencao": None,
        "banda_pct": banda,
        "calibracao": _descrever(calibracao, banda),
        "validacao": _descrever(validacao, banda) if validacao else None,
    }


def cobertura(observacoes: Sequence[Mapping[str, Any]]) -> dict:
    """Por lente e por ano de D: valores, retornos e os motivos de abstenção."""
    blocos = defaultdict(list)
    for obs in observacoes:
        if obs["modo"] == MODO:
            blocos[(obs["lente"], obs["horizonte"], _dia(obs["D"]).year)].append(obs)
    saida = defaultdict(dict)
    for (lente, horizonte, ano), itens in sorted(blocos.items()):
        com_valor = [o for o in itens if not o.get("abstencao")]
        saida[lente].setdefault(str(horizonte), {})[str(ano)] = {
            "observacoes": len(itens),
            "datas": len({o["D"] for o in itens}),
            "com_valor": len(com_valor),
            "com_retorno": sum(_finito(o.get("retorno_total")) for o in itens),
            "com_valor_e_retorno": sum(
                _finito(o.get("retorno_total")) for o in com_valor
            ),
            "motivos": dict(
                Counter(o["abstencao"] for o in itens if o["abstencao"]).most_common()
            ),
            "motivos_retorno": dict(
                Counter(
                    o["abstencao_retorno"] for o in itens if o["abstencao_retorno"]
                ).most_common()
            ),
        }
    return dict(saida)


def propor(
    observacoes: Sequence[Mapping[str, Any]],
    datas_pedidas: Sequence[str],
    sem_lentes: Sequence[Mapping[str, Any]] = (),
) -> dict:
    lentes = sorted({o["lente"] for o in observacoes} - {LENTE_SEM_ANALISE})
    return {
        "aviso": "proposta para o Marcos; sem efeito em código, ficha ou apresentação",
        "modo": MODO,
        "datas_pedidas": list(datas_pedidas),
        "observacoes": len(observacoes),
        # a análise sem lente vem em `sem_lentes` (BUG-3-56); a pseudo-lente "analise"
        # só existe nas observações de execuções anteriores a ele (`--observacoes`)
        "sem_analise": dict(
            Counter(
                o["abstencao"] for o in observacoes if o["lente"] == LENTE_SEM_ANALISE
            )
            + Counter(s["motivo"] for s in sem_lentes)
        ),
        "lentes": {
            lente: [
                calibrar_lente([o for o in observacoes if o["lente"] == lente], h)
                for h in HORIZONTES
            ]
            for lente in lentes
        },
        "cobertura": cobertura(observacoes),
    }


def _saida_em_outputs(caminho: Path) -> Path:
    destino = caminho.resolve()
    if not destino.is_relative_to((RAIZ / "outputs").resolve()):
        raise SystemExit("a saída do F3-8d fica só em outputs/")
    destino.mkdir(parents=True, exist_ok=True)
    return destino


def filtrar_elegiveis(
    elegiveis: list[dict], limite: int | None, classes: list[str] | None
) -> list[dict]:
    """Elegíveis das classes pedidas (todas sem ``classes``), até ``limite`` por classe."""
    por_classe = defaultdict(list)
    for item in elegiveis:
        if not classes or item.get("classe") in classes:
            por_classe[item.get("classe")].append(item)
    return [item for itens in por_classe.values() for item in itens[:limite]]


def _executar(
    banco: Path,
    saida: Path,
    datas: list[date] | None,
    limite: int | None,
    classes: list[str] | None = None,
):
    import pandas as pd

    from backtesting.backtest_pit import BacktestPIT
    from sentinela.data.referencia import universo
    from sentinela.services.historico import CADASTRO

    resultados = saida / "resultados.db"
    if resultados.exists():
        raise SystemExit(f"{resultados} já existe; use outra pasta de saída")
    conn = sqlite3.connect(f"file:{resultados}", uri=True)
    sql = (
        RAIZ / "sentinela/data/store/migrations/002_resultados_analise.sql"
    ).read_text()
    conn.executescript(sql)
    conn.execute("ATTACH DATABASE ? AS pit", (f"file:{banco.resolve()}?mode=ro",))
    pregoes = [
        date.fromisoformat(linha[0])
        for linha in conn.execute(
            "SELECT DISTINCT data FROM precos WHERE tipo_mercado = ? ORDER BY data",
            ("010",),
        )
    ]
    datas = datas or datas_fim_de_mes(pregoes, date(2018, 1, 1))
    if limite is not None or classes:
        original = universo.universo_backtest

        def limitado(*args, **kwargs):
            resposta = original(*args, **kwargs)
            resposta["elegiveis"] = filtrar_elegiveis(
                resposta["elegiveis"], limite, classes
            )
            return resposta

        universo.universo_backtest = limitado
    cadastro = pd.read_csv(CADASTRO, sep=";", encoding="latin-1", dtype=str)
    executor = BacktestPIT(
        conn,
        cadastro,
        hoje=datetime.now(ZoneInfo("America/Sao_Paulo")).date(),
        cache_dir=saida / "cache_pit",
    )
    resposta = executor.executar(datas, modo=MODO)
    conn.close()
    resposta["datas_pedidas"] = [d.isoformat() for d in datas]
    resposta["limite_por_classe"] = limite
    resposta["classes"] = classes
    (saida / "observacoes.json").write_text(
        json.dumps(resposta, ensure_ascii=False, indent=1, default=str)
    )
    return resposta


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--saida", type=Path, required=True)
    parser.add_argument("--executar", action="store_true")
    parser.add_argument("--banco", type=Path)
    parser.add_argument("--datas", nargs="*", type=date.fromisoformat)
    parser.add_argument("--limite-por-classe", type=int)
    parser.add_argument("--classes", nargs="+")  # F3-8j-uni: só as classes pedidas
    parser.add_argument("--observacoes", type=Path)
    args = parser.parse_args(argv)
    saida = _saida_em_outputs(args.saida)
    if args.executar:
        if args.banco is None:
            parser.error("--executar exige --banco")
        resposta = _executar(
            args.banco, saida, args.datas, args.limite_por_classe, args.classes
        )
    elif args.observacoes is not None:
        resposta = json.loads(args.observacoes.read_text())
    else:
        parser.error("use --executar ou --observacoes")
    proposta = propor(
        resposta["observacoes"],
        resposta.get("datas_pedidas", []),
        resposta.get("sem_lentes", []),
    )
    proposta["limite_por_classe"] = resposta.get("limite_por_classe")
    proposta["classes"] = resposta.get("classes")
    (saida / "proposta.json").write_text(
        json.dumps(proposta, ensure_ascii=False, indent=1)
    )
    print(json.dumps(proposta, ensure_ascii=False, indent=1)[:4000])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
