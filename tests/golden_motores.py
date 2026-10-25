"""Harness do golden dos motores V1 (F1-16): grade de casos, execução e comparador.

Os casos usam tickers genéricos e nenhum dado da carteira. O golden fica em
`tests/fixtures/golden_motores.jsonl`; o gerador roda uma única vez na fase:

    GERAR_GOLDEN=1 python -m pytest tests/test_equivalencia_motores.py::test_gerar_golden
"""

import json
import math
import random
from pathlib import Path
from unittest.mock import patch

from apoio_bancos import INFLACAO, NTNB, PL_INICIAL, VPA, enriquecer_bancos
from apoio_bazin import enriquecer_bazin
from apoio_fii import enriquecer_fii
from apoio_gordon import AS_OF_GORDON, enriquecer_gordon

import fii_engine
import valuation_engine
from config import MACRO
from fii_engine import FIIEngine
from valuation_engine import ValuationEngine

GOLDEN = Path(__file__).parent / "fixtures" / "golden_motores.jsonl"
SELIC_PADRAO = 0.145
DISTRESSED = frozenset({"TSD3"})
ESCOPO_DA_CASCATA = {"classe_ativo": "STOCK", "modelo_bpp": "empresa"}


# ── execução ──────────────────────────────────────────────────────────────────


def executar(caso):
    """Roda o caso no motor certo. Devolve a saída ou {"__erro__": <classe>}."""
    entrada = json.loads(json.dumps(caso["entrada"]))  # cópia, com NaN preservado
    try:
        if caso["motor"] == "acoes":
            # F2B-4: a cascata sempre grava a classe e o modelo do BPP; o caso que precisa
            # de outro valor (ou da ausência, com None) o declara na entrada.
            entrada = {**ESCOPO_DA_CASCATA, **entrada}
            taxa = caso.get("taxa_real") or {"ntnb": 0.07, "inflacao": 0.055}
            if "banco" in caso:
                # F2B-32: DFP sintética de banco (apoio_bancos), com ROE, payout e VPA do caso.
                lucro = caso["banco"]["roe"] * PL_INICIAL
                entrada = enriquecer_bancos(
                    entrada,
                    lucro_controladores=lucro,
                    proventos_controladores=caso["banco"]["payout"] * lucro,
                    vpa=caso["banco"]["vpa"],
                )
            else:
                entrada = enriquecer_bazin(
                    enriquecer_gordon(
                        entrada,
                        ntnb=taxa["ntnb"],
                        inflacao=taxa["inflacao"],
                        teto=caso.get("teto_pib_cenario", 0.02),
                    )
                )
            with (
                patch.object(valuation_engine, "DISTRESSED_TICKERS", DISTRESSED),
            ):
                return ValuationEngine().processar(entrada, as_of=AS_OF_GORDON)
        # F2B-2: Informe, B3 e NTN-B real sintéticos (apoio_fii), no as_of fixo; a chave
        # `sem_informe` deixa o caso sem eles.
        if not caso.get("sem_informe"):
            entrada = enriquecer_fii(
                entrada, ntnb=caso.get("taxa_real", {}).get("ntnb")
            )
        with patch.object(fii_engine, "get_selic_atual", return_value=caso["selic"]):
            return FIIEngine().analisar(entrada, as_of=AS_OF_GORDON)
    except Exception as exc:
        return {"__erro__": type(exc).__name__}


def iguais(a, b):
    """Igualdade exata e recursiva: NaN == NaN, tipos iguais, `==` nos floats.

    Lista e tupla valem o mesmo (o golden volta do JSON como lista).
    """
    if isinstance(a, float) and isinstance(b, float):
        return a == b or (math.isnan(a) and math.isnan(b))
    if isinstance(a, dict) and isinstance(b, dict):
        return a.keys() == b.keys() and all(iguais(a[k], b[k]) for k in a)
    if isinstance(a, (list, tuple)) and isinstance(b, (list, tuple)):
        return len(a) == len(b) and all(iguais(x, y) for x, y in zip(a, b, strict=True))
    return type(a) is type(b) and a == b


def ler_golden():
    with GOLDEN.open(encoding="utf-8") as f:
        return [json.loads(linha) for linha in f]


def gravar_golden(casos):
    with GOLDEN.open("w", encoding="utf-8", newline="\n") as f:
        for caso in casos:
            caso = {**caso, "saida": executar(caso)}
            f.write(json.dumps(caso, ensure_ascii=False, allow_nan=True) + "\n")


# ── grade: ações ──────────────────────────────────────────────────────────────

_RENDA = {
    "ticker": "TST3",
    "preco_atual": 100.0,
    "roe": 0.15,
    "pl": 10.0,
    "pvp": 1.5,
    "dy": 0.08,
}
_CRESC = {
    "ticker": "TST3",
    "preco_atual": 100.0,
    "roe": 0.25,
    "pl": 15.0,
    "pvp": 2.0,
    "dy": 0.02,
}


def _acao(id_, entrada, selic=SELIC_PADRAO):
    return {"id": id_, "motor": "acoes", "selic": selic, "entrada": entrada}


def _em_torno(t, passo=0.001):
    return [t - passo, t, t + passo]


def _acoes_fronteiras():
    m = MACRO
    campos = {
        "dy": [0.0, 0.01]
        + _em_torno(m.DY_PERCENTUAL_THRESHOLD)
        + _em_torno(m.DY_SANIDADE_MAX)
        + _em_torno(m.DY_CRESCIMENTO_MAX)
        + _em_torno(m.BAZIN_DY_MIN)
        + _em_torno(m.BAZIN_DY_ARMADILHA)
        + _em_torno(m.GORDON_DY_MIN)
        + [0.3, 5.0, 12.47, 30.0, -0.05],
        "roe": [0.0, -0.1]
        + _em_torno(m.ROE_CRESCIMENTO_MIN)
        + _em_torno(m.GORDON_ROE_MIN)
        + _em_torno(m.ROE_PENALIDADE_MAX)
        + [0.5],
        "pl": [0.0, -3.0, 3.0]
        + _em_torno(m.GRAHAM_PL_FLOOR, 0.01)
        + _em_torno(m.GRAHAM_PL_LIMITE, 0.01)
        + [80.0],
        "pvp": [0.0, -1.0, 0.5]
        + _em_torno(m.GRAHAM_PVP_LIMITE_RENDA, 0.01)
        + _em_torno(m.GRAHAM_PVP_LIMITE_CRESCIMENTO, 0.01)
        + [10.0],
        "divida_liq_ebitda": [
            None,
            0,
            2.99,
            3.0,
            3.01,
            "3,01",
            "1.234,56",
            "1,234.56",
            "2.5",
            "abc",
            float("nan"),
            float("inf"),
            "",
        ],
        "pl_confiavel": [True, False],
        "fundamentos_incompletos": [True, False],
    }
    casos = []
    for nome_base, base in (("renda", _RENDA), ("cresc", _CRESC)):
        casos.append(_acao(f"base-{nome_base}", dict(base)))
        for campo, valores in campos.items():
            for v in valores:
                casos.append(_acao(f"{nome_base}-{campo}-{v!r}", {**base, campo: v}))
    # gates cruzados do perfil (ROE × DY) e do Gordon (DY × ROE)
    for roe in _em_torno(m.ROE_CRESCIMENTO_MIN):
        for dy in _em_torno(m.DY_CRESCIMENTO_MAX):
            casos.append(
                _acao(f"perfil-roe{roe!r}-dy{dy!r}", {**_CRESC, "roe": roe, "dy": dy})
            )
    for roe in _em_torno(m.GORDON_ROE_MIN):
        for dy in _em_torno(m.GORDON_DY_MIN):
            casos.append(
                _acao(f"gordon-roe{roe!r}-dy{dy!r}", {**_RENDA, "roe": roe, "dy": dy})
            )
    # Lynch: tetos de payout, g e P/L justo
    for dy, pl, roe in [
        (0.03, 2.0, 0.25),
        (0.039, 4.0, 0.9),
        (0.01, 40.0, 0.6),
        (0.039, 1.0, 0.21),
    ]:
        casos.append(
            _acao(f"lynch-{dy}-{pl}-{roe}", {**_CRESC, "dy": dy, "pl": pl, "roe": roe})
        )
    return casos


def _acoes_especiais():
    casos = [
        _acao("vazio", {}),
        _acao("preco-zero", {"ticker": "TST3", "preco_atual": 0}),
        _acao("distressed", {**_RENDA, "ticker": "TSD3"}),
        _acao("distressed-minusculo", {**_RENDA, "ticker": "tsd3"}),
        _acao(
            "campos-nulos",
            {
                "ticker": "TST3",
                "preco_atual": 50.0,
                "roe": None,
                "pl": None,
                "pvp": None,
                "dy": None,
            },
        ),
        _acao("nan-roe", {**_RENDA, "roe": float("nan")}),
        _acao("nan-pl", {**_RENDA, "pl": float("nan")}),
        _acao("nan-dy", {**_RENDA, "dy": float("nan")}),
        _acao(
            "scraper-sem-fundamentos",
            {"ticker": "TST3", "preco_atual": 20.0, "fundamentos_incompletos": True},
        ),
        _acao(
            "tudo-ruim",
            {
                **_RENDA,
                "roe": 0.01,
                "pl": -5.0,
                "pvp": 0.0,
                "dy": 0.3,
                "fundamentos_incompletos": True,
                "pl_confiavel": False,
                "divida_liq_ebitda": 9,
            },
        ),
    ]
    for selic in (0.02, 0.049, 0.05, 0.051, 0.0975, 0.1, 0.1375, 0.2, 0.25):
        for nome, base in (("renda", _RENDA), ("cresc", _CRESC)):
            casos.append(_acao(f"selic{selic}-{nome}", dict(base), selic=selic))
    casos.append(_acao("preco-negativo", {**_RENDA, "preco_atual": -10.0}))
    # Selic em torno de k = g no Gordon (g no teto de 8%, k = Selic + 7%)
    for selic in (0.0099, 0.01, 0.0101, 0.0105):
        casos.append(
            _acao(
                f"gordon-k-perto-de-g-selic{selic}",
                {**_RENDA, "roe": 0.5, "dy": 0.06},
                selic=selic,
            )
        )
    # Selic baixa o bastante para k ≤ g no Gordon (k = selic + prêmio; g até 8%)
    for selic in (-0.0701, -0.07, -0.05, 0.0):  # k ≤ 0
        casos.append(
            _acao(
                f"gordon-k-menor-g-selic{selic}",
                {**_RENDA, "roe": 0.5, "dy": 0.06},
                selic=selic,
            )
        )
    return casos


def _acoes_chaves_e_extremos():
    """Chaves ausentes, preço pequeno (piso do divisor), piso e teto do score, texto de dívida."""
    base = {"ticker": "TST3", "preco_atual": 100.0}
    casos = [
        _acao("sem-pl", {**base, "roe": 0.15, "pvp": 1.5, "dy": 0.08}),
        _acao("sem-pvp", {**base, "roe": 0.15, "pl": 10.0, "dy": 0.08}),
        _acao("sem-roe", {**base, "pl": 10.0, "pvp": 1.5, "dy": 0.08}),
        _acao("sem-dy", {**base, "roe": 0.15, "pl": 10.0, "pvp": 1.5}),
        _acao(
            "sem-ticker",
            {"preco_atual": 100.0, "roe": 0.15, "pl": 10.0, "pvp": 1.5, "dy": 0.08},
        ),
        _acao("distressed-preco-longo", {"ticker": "TSD3", "preco_atual": 12.3456}),
        _acao("preco-longo", {**_RENDA, "preco_atual": 12.3456}),
        # score colado em 0: upside muito negativo mais todas as penalidades
        _acao(
            "score-piso",
            {
                **base,
                "roe": 0.01,
                "pl": 80.0,
                "pvp": 9.0,
                "dy": 0.3,
                "divida_liq_ebitda": 9,
            },
            selic=0.25,
        ),
        _acao(
            "score-piso-bazin",
            {
                **base,
                "roe": 0.01,
                "pl": 80.0,
                "pvp": 9.0,
                "dy": 0.05,
                "divida_liq_ebitda": 9,
            },
            selic=0.9,
        ),
        # score colado em 100: upside enorme mais bônus de ROE
        _acao(
            "score-teto",
            {**base, "roe": 0.3, "pl": 80.0, "pvp": 9.0, "dy": 0.25},
            selic=0.05,
        ),
        _acao(
            "score-teto-2",
            {**base, "roe": 0.3, "pl": 60.0, "pvp": 9.0, "dy": 0.2},
            selic=0.02,
        ),
    ]
    for nome, divida in (
        ("misto-virgula-ponto", "1,234.567,8"),
        ("misto-ponto-virgula", "1.2,3.4"),
        ("milhar-br", "1.234,5"),
        ("milhar-us", "1,234.5"),
        ("virgula-simples", "3,5"),
        ("ponto-multiplo", "1.234.567"),
        ("virgula-multipla", "1,234,567"),
    ):
        casos.append(_acao(f"divida-{nome}", {**_RENDA, "divida_liq_ebitda": divida}))
    # preço pequeno: valores justos abaixo de 1 exercitam o piso de 0,01 na divergência
    for p in (0.5, 1.0, 2.0):
        for dy, pl, pvp in ((0.08, 10.0, 1.5), (0.2, 5.0, 0.5), (0.06, 20.0, 2.4)):
            casos.append(
                _acao(
                    f"preco{p}-dy{dy}",
                    {
                        "ticker": "TST3",
                        "preco_atual": p,
                        "roe": 0.15,
                        "pl": pl,
                        "pvp": pvp,
                        "dy": dy,
                    },
                    selic=0.145,
                )
            )
    return casos


def _acoes_varredura_classificacao():
    """Varre o DY (só Bazin ativo) para cruzar os limites de upside, score e confiança."""
    casos = []
    extras = {
        "": {},
        "scraper": {"fundamentos_incompletos": True},
        "divida": {"divida_liq_ebitda": 4},
        "plsuspeito": {"pl_confiavel": False},
        "incompleto": {"pl": 0.0, "pvp": 0.0},
        "roe-alto": {"roe": 0.3},
        "roe-baixo": {"roe": 0.02},
    }
    for selic in (0.08, 0.1, 0.145):
        for i in range(61):
            dy = round(0.05 + 0.0025 * i, 4)
            for nome, extra in extras.items():
                entrada = {
                    "ticker": "TST3",
                    "preco_atual": 100.0,
                    "roe": 0.12,
                    "pl": 60.0,
                    "pvp": 6.0,
                    "dy": dy,
                    **extra,
                }
                casos.append(
                    _acao(f"varredura-selic{selic}-dy{dy}-{nome}", entrada, selic=selic)
                )
    return casos


def _acoes_aleatorias(n=300):
    rng = random.Random(20261002)
    casos = []
    for i in range(n):
        entrada = {
            "ticker": "TST3",
            "preco_atual": round(rng.uniform(1, 200), 2),
            "roe": round(rng.uniform(-0.1, 0.5), 3),
            "pl": round(
                rng.choice(
                    [rng.uniform(-5, 0), rng.uniform(1, 30), rng.uniform(30, 100)]
                ),
                2,
            ),
            "pvp": round(rng.uniform(0, 5), 2),
            "dy": round(
                rng.choice(
                    [rng.uniform(0, 0.06), rng.uniform(0.06, 0.3), rng.uniform(1, 15)]
                ),
                4,
            ),
        }
        if rng.random() < 0.2:
            entrada["fundamentos_incompletos"] = True
        if rng.random() < 0.2:
            entrada["pl_confiavel"] = False
        if rng.random() < 0.2:
            entrada["divida_liq_ebitda"] = round(rng.uniform(0, 8), 2)
        casos.append(
            _acao(
                f"aleatorio-{i}",
                entrada,
                selic=rng.choice([0.0525, 0.1, 0.1375, 0.145, 0.15]),
            )
        )
    return casos


def _acoes_classe_ativo():
    """F2A-29: ETF, BDR e UNKNOWN se abstêm; STOCK e UNIT são o controle."""
    return [
        _acao(f"classe-{classe}-{nome}", {**base, "classe_ativo": classe})
        for classe in ("ETF", "BDR", "UNKNOWN", "STOCK", "UNIT")
        for nome, base in (("renda", _RENDA), ("cresc", _CRESC))
    ]


def _acoes_preco_nao_finito():
    """F2A-24: preço NaN e infinito devolvem `None`."""
    return [
        _acao(f"preco-nao-finito-{nome}", {**_RENDA, "preco_atual": preco})
        for nome, preco in (("nan", float("nan")), ("inf", float("inf")))
    ]


# ── grade: FII ────────────────────────────────────────────────────────────────

_FII = {
    "ticker": "TST12",
    "preco_atual": 100.0,
    "dy": 0.10,
    "pvp": 1.0,
    "tipo": "Tijolo",
}


def _fii(id_, entrada, selic=SELIC_PADRAO):
    return {"id": id_, "motor": "fii", "selic": selic, "entrada": entrada}


def _fii_fronteiras():
    m = MACRO
    campos = {
        "dy": [0.0, 0.01, 0.05, 0.08, 0.12, 0.15, 0.2]
        + _em_torno(m.DY_PERCENTUAL_THRESHOLD)
        + _em_torno(m.DY_SANIDADE_MAX)
        + [0.3, 9.5, 12.0, float("nan"), None],
        "pvp": [None, 0.0, 0.5]
        + _em_torno(m.FII_PVP_DESCONTO, 0.0001)
        + _em_torno(m.FII_PVP_PREMIO_MODERADO, 0.0001)
        + _em_torno(m.FII_PVP_PREMIO_ALTO, 0.0001)
        + [3.0],
        "tipo": [None, "", "Papel", "Híbrido"],
        "preco_atual": [0, 0.5, 9.99, 1000.0],
    }
    casos = [
        _fii("base", dict(_FII)),
        _fii("vazio", {}),
        _fii("sem-ticker", {"preco_atual": 10, "dy": 0.1}),
    ]
    for campo, valores in campos.items():
        for v in valores:
            casos.append(_fii(f"{campo}-{v!r}", {**_FII, campo: v}))
    return casos


def _fii_selic_e_vacancia():
    casos = []
    for selic in (0.02, 0.049, 0.05, 0.051, 0.0975, 0.1, 0.1375, 0.145, 0.2):
        for dy in (0.04, 0.0595, 0.0599, 0.06, 0.0825, 0.1, 0.12):
            casos.append(_fii(f"selic{selic}-dy{dy}", {**_FII, "dy": dy}, selic=selic))
    # tickers que, até o F2A-13, separavam CNPJ e vacância manual no harness
    for ticker in ("TST11", "TST12", "TST13", "TST14"):
        casos.append(_fii(f"{ticker}-sem-provedor", {**_FII, "ticker": ticker}))
    # DY exatamente na Selic líquida (selic × 0,85): fronteira do bônus de score
    for selic, dy in ((0.06, 0.051), (0.1, 0.085), (0.12, 0.102), (0.15, 0.1275)):
        for d in (dy - 0.0001, dy, dy + 0.0001):
            casos.append(
                _fii(
                    f"dy-na-selic-liquida-{selic}-{d!r}",
                    {**_FII, "ticker": "TST14", "dy": d},
                    selic=selic,
                )
            )
    casos.append(_fii("preco-negativo", {**_FII, "preco_atual": -10.0}))
    casos += [
        _fii("sem-preco", {"ticker": "TST12", "dy": 0.1, "pvp": 1.0}),
        _fii("fallback-preco-longo", {**_FII, "preco_atual": 12.3456, "dy": 0.0}),
    ]
    return casos


def _fii_nao_finitos():
    """F2A-24: preço NaN e infinito devolvem `None`; Selic zero e não finita, o resultado
    sem método calculado."""
    return [
        _fii(f"preco-nao-finito-{nome}", {**_FII, "preco_atual": preco})
        for nome, preco in (("nan", float("nan")), ("inf", float("inf")))
    ] + [
        _fii(f"selic-sem-metodo-{nome}", dict(_FII), selic=selic)
        for nome, selic in (("zero", 0.0), ("nan", float("nan")), ("inf", float("inf")))
    ]


def _fii_aleatorios(n=250):
    rng = random.Random(20261003)
    casos = []
    for i in range(n):
        entrada = {
            "ticker": rng.choice(["TST11", "TST12", "TST13", "TST14"]),
            "preco_atual": round(rng.uniform(5, 200), 2),
            "dy": round(rng.choice([rng.uniform(0, 0.2), rng.uniform(1, 15)]), 4),
            "pvp": round(rng.uniform(0.4, 1.8), 3),
            "tipo": rng.choice(["Tijolo", "Papel", None]),
        }
        # F2A-13: os casos com provedor saíram; os sorteios dele ficam, para a sequência
        # do gerador, e com ela os casos restantes, não mudar.
        com_provedor = rng.random() < 0.5
        if com_provedor:
            rng.uniform(40, 200)
            rng.choice([None, rng.uniform(0, 0.5)])
        selic = rng.choice([0.0525, 0.1, 0.1375, 0.145])
        if not com_provedor:
            casos.append(_fii(f"aleatorio-{i}", entrada, selic=selic))
    return casos


def _fii_ntnb():
    """F2B-2: grade da NTN-B real (com q = NTN-B + spread de positivo a não positivo), sem
    Informe e sem taxa real."""
    casos = []
    for ntnb in (-0.05, -0.04, 0.0, 0.04, 0.06, 0.07, 0.08):
        for dy in (0.06, 0.09, 0.12):
            caso = _fii(f"ntnb{ntnb}-dy{dy}", {**_FII, "dy": dy})
            caso["taxa_real"] = {"ntnb": ntnb}
            casos.append(caso)
    sem = _fii("sem-informe", dict(_FII))
    sem["sem_informe"] = True
    sem_taxa = _fii("sem-taxa-real", dict(_FII))
    sem_taxa["taxa_real"] = {"ntnb": None}
    return [*casos, sem, sem_taxa]


def _acoes_gordon_real():
    """Grade sintética da ficha: teto elevado só para testar k→g, identificado."""
    casos = []
    for ntnb in (0.04, 0.06, 0.08):
        for ipca in (0.02, 0.04, 0.06):
            for diferenca in (-0.001, 0, 0.00001, 0.001):
                g = ntnb + 0.05 - diferenca
                roe = ((1 + g) * (1 + ipca) - 1) / 0.7
                caso = _acao(
                    f"gordon_real_ntnb{ntnb}_ipca{ipca}_margem{diferenca}",
                    {
                        "ticker": "TST3",
                        "preco_atual": 100.0,
                        "pl": 10.0,
                        "pvp": 1.0,
                        "dy": 0.06,
                        "roe": roe,
                    },
                )
                caso["taxa_real"] = {"ntnb": ntnb, "inflacao": ipca}
                caso["teto_pib_cenario"] = 0.15
                casos.append(caso)
    return casos


def _acoes_taxa_bazin():
    """Grade do F2B-31: DY em torno do gate, do critério, do alerta e do limite, por Selic."""
    casos = []
    for selic in (0.02, 0.06, 0.1475, 0.25):
        for dy in (0.0499, 0.05, 0.0599, 0.06, 0.0601, 0.15, 0.1501, 0.25, 0.2501):
            casos.append(
                _acao(
                    f"bazin_taxa_selic{selic}_dy{dy}",
                    {
                        "ticker": "TST3",
                        "preco_atual": 100.0,
                        "pl": 10.0,
                        "pvp": 1.0,
                        "dy": dy,
                        "roe": 0.12,
                    },
                    selic=selic,
                )
            )
    return casos


def _casos_liquidez():
    """F2A-10: só inclusões, com a mesma regra explícita por classe."""
    casos = []
    for classe in ("STOCK", "UNIT", "FII"):
        minimo = 100000 if classe == "FII" else 500000
        for nome, presenca, volume, extra in (
            ("acima", 1.0, 1000000.0, {}),
            ("limite", 0.8, minimo, {}),
            ("presenca-baixa", 0.79, minimo, {}),
            ("volume-baixo", 0.8, minimo - 1, {}),
            ("ambos-baixos", 0.1, 0, {}),
            ("sem-negocio", 0.0, 0.0, {}),
            ("incompleta", 0.1, 0, {"incompleta": True}),
            ("mes-ausente", 0.1, 0, {"meses_ausentes": ["2026-09"]}),
            (
                "sem-dado",
                0.0,
                0.0,
                {"abstencao": "falha de coleta: fonte indisponível"},
            ),
        ):
            bloco = {
                "janelas": {
                    "63": {
                        "pregoes": 63,
                        "incompleta": extra.get("incompleta", False),
                        "presenca": presenca,
                        "volume_mediano": volume,
                    }
                },
                "meses_ausentes": extra.get("meses_ausentes", []),
                "fonte": "COTAHIST sintético",
                "data_final": "2026-10-19",
            }
            if "abstencao" in extra:
                bloco = {"abstencao": extra["abstencao"]}
            entrada = {**_RENDA, "classe_ativo": classe, "liquidez": bloco}
            entrada["ticker"] = "TSTU11" if classe in ("FII", "UNIT") else "TSTC3"
            fabrica = _fii if classe == "FII" else _acao
            casos.append(fabrica(f"liquidez-{classe}-{nome}", entrada))
    return casos


def _acoes_escopo_modelo():
    """F2B-4: escopo pelo modelo do BPP consolidado, não pelo setor, e evidência até o as_of."""
    entrega = {"data_entrega": "2026-02-12", "data_coleta": "2026-02-20T18:00:00+00:00"}
    variantes = (
        ("empresa", {}),
        ("banco", {"modelo_bpp": "banco", "setor": "Bancos"}),
        (
            "seguradora",
            {"modelo_bpp": "seguradora", "setor": "Seguradoras e Corretoras"},
        ),
        ("sem-modelo", {"modelo_bpp": None}),
        ("holding", {"setor": "Holdings Diversificadas"}),
        ("setor-banco-bpp-empresa", {"setor": "Bancos"}),
        ("setor-seguradora-bpp-empresa", {"setor": "Seguradoras e Corretoras"}),
        ("unit-empresa", {"classe_ativo": "UNIT"}),
        ("unit-banco", {"classe_ativo": "UNIT", "modelo_bpp": "banco"}),
        ("sem-classe", {"classe_ativo": None}),
        ("classe-com-espacos", {"classe_ativo": " ETF "}),
        ("stock-com-espacos", {"classe_ativo": " stock "}),
        ("evidencia-anterior", {"modelo_bpp_proveniencia": entrega}),
        (
            "evidencia-posterior",
            {"modelo_bpp_proveniencia": {**entrega, "data_entrega": "2026-10-21"}},
        ),
        ("evidencia-ausente", {"modelo_bpp_proveniencia": None}),
    )
    return [
        _acao(f"escopo-{nome}-{perfil}", {**base, **extra})
        for nome, extra in variantes
        for perfil, base in (("renda", _RENDA), ("cresc", _CRESC))
    ]


def _acoes_bancos():
    """F2B-32: grade da lente de bancos (ROE sobre PL inicial, payout → g, VPA CVM)."""
    casos = []
    base = {"ticker": "TSTB4", "preco_atual": 44.28, "roe": 0.2, "pl": 9.0, "pvp": 2.0,
            "dy": 0.07, "modelo_bpp": "banco", "setor": "Bancos"}  # fmt: skip
    grade = [
        (roe, payout, vpa)
        for roe in (-0.05, 0.05, 0.1, 0.15, 0.2125, 0.3)
        for payout in (0.0, 0.25, 0.5, 0.75, 1.0)
        for vpa in (VPA, 2 * VPA)
    ]
    for roe, payout, vpa in grade:
        caso = _acao(
            f"banco-roe{roe}-payout{payout}-vpa{round(vpa, 4)}", {**base, "roe": roe}
        )
        caso["banco"] = {"roe": roe, "payout": payout, "vpa": vpa}
        # A taxa que a DFP sintética de banco usa (apoio_bancos), registrada no caso.
        caso["taxa_real"] = {"ntnb": NTNB, "inflacao": INFLACAO}
        casos.append(caso)
    return casos


def montar_casos():
    casos = (
        _acoes_fronteiras()
        + _casos_liquidez()
        + _acoes_especiais()
        + _acoes_chaves_e_extremos()
        + _acoes_varredura_classificacao()
        + _acoes_aleatorias()
        + _acoes_classe_ativo()
        + _acoes_escopo_modelo()
        + _acoes_bancos()
        + _acoes_preco_nao_finito()
        + _acoes_gordon_real()
        + _acoes_taxa_bazin()
        + _fii_fronteiras()
        + _fii_selic_e_vacancia()
        + _fii_aleatorios()
        + _fii_nao_finitos()
        + _fii_ntnb()
    )
    for caso in casos:
        if caso["motor"] == "acoes":
            caso.setdefault("taxa_real", {"ntnb": 0.07, "inflacao": 0.055})
        else:
            caso.setdefault("taxa_real", {"ntnb": 0.07})
    vistos, unicos = set(), []
    for c in casos:
        chave = (c["motor"], c["id"])
        if chave not in vistos:
            vistos.add(chave)
            unicos.append(c)
    return unicos
