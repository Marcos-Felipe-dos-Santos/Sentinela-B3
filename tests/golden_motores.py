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

import fii_engine
import valuation_engine
from config import MACRO
from fii_engine import FIIEngine
from valuation_engine import ValuationEngine

GOLDEN = Path(__file__).parent / "fixtures" / "golden_motores.jsonl"
SELIC_PADRAO = 0.145
DISTRESSED = frozenset({"TSD3"})
CNPJ_FALSO = "00.000.000/0001-00"
# TST11: CNPJ e vacância manual · TST12: só CNPJ · TST13: só vacância manual · TST14: nenhum
FII_CNPJS = frozenset({"TST11", "TST12"})
FII_VACANCIA_MANUAL = {"TST11": 0.2, "TST13": 0.2}


# ── execução ──────────────────────────────────────────────────────────────────


class _ProvedorFalso:
    def __init__(self, spec):
        self.spec = spec

    def obter_dados_fii(self, cnpj):
        if cnpj != CNPJ_FALSO:
            return None
        if self.spec.get("levanta"):
            raise RuntimeError("falha simulada")
        return self.spec.get("dados")


def executar(caso):
    """Roda o caso no motor certo. Devolve a saída ou {"__erro__": <classe>}."""
    entrada = json.loads(json.dumps(caso["entrada"]))  # cópia, com NaN preservado
    try:
        if caso["motor"] == "acoes":
            with (
                patch.object(
                    valuation_engine, "get_selic_atual", return_value=caso["selic"]
                ),
                patch.object(valuation_engine, "DISTRESSED_TICKERS", DISTRESSED),
            ):
                return ValuationEngine().processar(entrada)
        spec = caso.get("cvm")
        provedor = _ProvedorFalso(spec) if spec is not None else None
        with (
            patch.object(fii_engine, "get_selic_atual", return_value=caso["selic"]),
            patch.object(fii_engine, "VACANCIA_CONHECIDA", dict(FII_VACANCIA_MANUAL)),
            patch.object(
                fii_engine,
                "get_cnpj_fii",
                lambda t: CNPJ_FALSO if t in FII_CNPJS else None,
            ),
        ):
            return FIIEngine(provedor).analisar(entrada)
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
        "erro_scraper": [True, False],
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
            {"ticker": "TST3", "preco_atual": 20.0, "erro_scraper": True},
        ),
        _acao(
            "tudo-ruim",
            {
                **_RENDA,
                "roe": 0.01,
                "pl": -5.0,
                "pvp": 0.0,
                "dy": 0.3,
                "erro_scraper": True,
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
        "scraper": {"erro_scraper": True},
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
            entrada["erro_scraper"] = True
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


# ── grade: FII ────────────────────────────────────────────────────────────────

_FII = {
    "ticker": "TST12",
    "preco_atual": 100.0,
    "dy": 0.10,
    "pvp": 1.0,
    "tipo": "Tijolo",
}


def _fii(id_, entrada, selic=SELIC_PADRAO, cvm=None):
    caso = {"id": id_, "motor": "fii", "selic": selic, "entrada": entrada}
    if cvm is not None:
        caso["cvm"] = cvm
    return caso


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
    # vacância: manual (TST11, TST13), CVM, ausente, nos dois lados do limite de 15%
    for ticker in ("TST11", "TST12", "TST13", "TST14"):
        casos.append(_fii(f"{ticker}-sem-provedor", {**_FII, "ticker": ticker}))
        for vac in (0.0, 0.05, 0.1499, 0.15, 0.1501, 0.3, 0.9, None):
            casos.append(
                _fii(
                    f"{ticker}-cvm-vac{vac}",
                    {**_FII, "ticker": ticker},
                    cvm={"dados": {"valor_cota": 100.0, "vacancia_fisica": vac}},
                )
            )
    # CVM: valor da cota (P/VP oficial) e erros do provedor
    for cota in (None, 0, -1.0, 50.0, 80.0, 100.0, 120.0, 95.2, 87.0):
        casos.append(
            _fii(f"cvm-cota{cota}", dict(_FII), cvm={"dados": {"valor_cota": cota}})
        )
        casos.append(
            _fii(
                f"cvm-cota{cota}-pvp-ausente",
                {**_FII, "pvp": None},
                cvm={"dados": {"valor_cota": cota, "vacancia_fisica": 0.1}},
            )
        )
    for ticker in ("TST11", "TST12", "TST13"):
        casos.append(
            _fii(
                f"{ticker}-provedor-levanta",
                {**_FII, "ticker": ticker},
                cvm={"levanta": True},
            )
        )
        casos.append(
            _fii(
                f"{ticker}-provedor-none",
                {**_FII, "ticker": ticker},
                cvm={"dados": None},
            )
        )
        casos.append(
            _fii(
                f"{ticker}-provedor-dict-vazio",
                {**_FII, "ticker": ticker},
                cvm={"dados": {}},
            )
        )
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
        _fii("cvm-cota-abaixo-de-1", dict(_FII), cvm={"dados": {"valor_cota": 0.5}}),
        _fii("cvm-cota-1", dict(_FII), cvm={"dados": {"valor_cota": 1.0}}),
    ]
    # DY inválido: o provedor não pode ser chamado antes do teste de DY
    casos.append(
        _fii("dy-invalido-provedor-levanta", {**_FII, "dy": 0.3}, cvm={"levanta": True})
    )
    return casos


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
        cvm = None
        if rng.random() < 0.5:
            cvm = {
                "dados": {
                    "valor_cota": round(rng.uniform(40, 200), 2),
                    "vacancia_fisica": rng.choice(
                        [None, round(rng.uniform(0, 0.5), 3)]
                    ),
                }
            }
        casos.append(
            _fii(
                f"aleatorio-{i}",
                entrada,
                selic=rng.choice([0.0525, 0.1, 0.1375, 0.145]),
                cvm=cvm,
            )
        )
    return casos


def montar_casos():
    casos = (
        _acoes_fronteiras()
        + _acoes_especiais()
        + _acoes_chaves_e_extremos()
        + _acoes_varredura_classificacao()
        + _acoes_aleatorias()
        + _fii_fronteiras()
        + _fii_selic_e_vacancia()
        + _fii_aleatorios()
    )
    vistos, unicos = set(), []
    for c in casos:
        chave = (c["motor"], c["id"])
        if chave not in vistos:
            vistos.add(chave)
            unicos.append(c)
    return unicos
