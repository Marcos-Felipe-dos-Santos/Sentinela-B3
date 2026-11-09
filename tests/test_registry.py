import dataclasses
import importlib
import inspect
from pathlib import Path

import pytest

import sentinela.methods as pacote
from config import MACRO
from sentinela.domain.enums import AssetType, ModeloDemonstracao, Regime
from sentinela.methods import registry
from sentinela.methods.bancos import BancosParams
from sentinela.methods.base import ValuationMethod
from sentinela.methods.bazin import BazinParams
from sentinela.methods.fii_nav import FiiNavParams
from sentinela.methods.fii_yield import FiiYieldParams
from sentinela.methods.gordon import GordonParams
from sentinela.methods.graham import FATOR_GRAHAM, GrahamParams
from sentinela.methods.lynch import LynchParams

NOMES = [
    "Graham",
    "Bazin",
    "Lynch",
    "Gordon",
    "Rendimento do FII",
    "P/VP do FII",
    "Bancos",
]

# Valores da 1.0.0, lidos hoje do MacroContext: mudar uma constante sem criar versão
# nova do método quebra este teste. campo do método -> (constante do MacroContext, valor)
PARAMETROS_VIGENTES = {
    "Bancos": (BancosParams, {}),
    "Graham": (GrahamParams, {}),
    "Bazin": (
        BazinParams,
        {
            "dy_min": ("BAZIN_DY_MIN", 0.05),
            "dy_armadilha": ("BAZIN_DY_ARMADILHA", 0.15),
        },
    ),
    "Lynch": (LynchParams, {}),
    "Gordon": (GordonParams, {}),
    "Rendimento do FII": (
        FiiYieldParams,
        {"spread": ("FII_SPREAD_TIJOLO", 0.03505842448151178)},
    ),
    "P/VP do FII": (
        FiiNavParams,
        {
            "premio_alto": ("FII_PVP_PREMIO_ALTO", 1.15),
            "premio_moderado": ("FII_PVP_PREMIO_MODERADO", 1.05),
            "desconto": ("FII_PVP_DESCONTO", 0.85),
        },
    ),
}


def test_registro_tem_os_seis_metodos():
    assert [e.nome for e in registry.entradas()] == NOMES
    for e in registry.entradas():
        assert e.version == registry.CHANGELOG[e.nome][-1].version
        assert isinstance(e.regime, Regime)
        assert e.requires
        assert e.assumptions
        assert e.applies_to
    assert len(registry.METODOS) == 7


def test_entrada_reflete_o_metodo():
    por_nome = {m.nome: m for m in registry.METODOS}
    for e in registry.entradas():
        m = por_nome[e.nome]
        assert (e.version, e.regime, e.requires, e.assumptions, e.applies_to) == (
            m.version,
            m.regime,
            m.requires,
            m.assumptions,
            m.applies_to,
        )


def test_buscar_pelo_nome():
    assert registry.obter("Graham").nome == "Graham"
    with pytest.raises(KeyError, match="Inexistente"):
        registry.obter("Inexistente")


def test_todo_modulo_de_metodo_esta_registrado():
    pasta = Path(pacote.__file__).parent
    classes = set()
    for arquivo in sorted(pasta.glob("*.py")):
        if arquivo.stem in {"__init__", "base", "registry"}:
            continue
        modulo = importlib.import_module(f"sentinela.methods.{arquivo.stem}")
        for _, obj in inspect.getmembers(modulo, inspect.isclass):
            if (
                issubclass(obj, ValuationMethod)
                and obj is not ValuationMethod
                and obj.__module__ == modulo.__name__
            ):
                classes.add(obj)
    registradas = {type(m) for m in registry.METODOS}
    assert classes == registradas
    assert len(classes) == 7


def test_regime_coerente_com_a_taxa():
    regimes = {e.nome: e.regime for e in registry.entradas()}
    assert regimes == {
        "Bancos": Regime.REAL,
        "Graham": Regime.SEM_TAXA,
        "Bazin": Regime.NOMINAL,
        "Lynch": Regime.NOMINAL,
        "Gordon": Regime.REAL,
        "Rendimento do FII": Regime.REAL,
        "P/VP do FII": Regime.SEM_TAXA,
    }
    for e in registry.entradas():
        if "selic" in e.requires:
            assert e.regime is Regime.NOMINAL
        if e.regime is Regime.SEM_TAXA:
            assert "selic" not in e.requires
    assert regimes["Gordon"] is Regime.REAL


def test_applies_to_descreve_o_escopo_aplicado():
    acoes = frozenset({AssetType.STOCK, AssetType.UNIT})
    esperado = {
        "Bancos": acoes,
        "Graham": acoes,
        "Bazin": acoes,
        "Lynch": acoes,
        "Gordon": acoes,
        "Rendimento do FII": frozenset({AssetType.FII}),
        "P/VP do FII": frozenset({AssetType.FII}),
    }
    assert {e.nome: e.applies_to for e in registry.entradas()} == esperado
    # F2B-4: o escopo de companhia exige o modelo do BPP consolidado.
    assert {m.nome: m.modelos for m in registry.METODOS} == {
        "Bancos": frozenset({ModeloDemonstracao.BANCO}),
        **{
            nome: frozenset({ModeloDemonstracao.EMPRESA})
            for nome in ("Graham", "Bazin", "Lynch", "Gordon")
        },
        "Rendimento do FII": frozenset(),
        "P/VP do FII": frozenset(),
    }
    todos = set().union(*esperado.values())
    assert AssetType.ETF not in todos
    assert AssetType.BDR not in todos


def test_parametros_vigentes_fixados():
    assert set(PARAMETROS_VIGENTES) == set(NOMES)
    for nome, (tipo, campos) in PARAMETROS_VIGENTES.items():
        assert registry.obter(nome).params_type is tipo
        assert {f.name for f in dataclasses.fields(tipo)} == set(campos)
        for campo, (constante, valor) in campos.items():
            assert getattr(MACRO, constante) == valor, f"{nome}.{campo} ({constante})"
    # constantes de fórmula que moram no módulo do método
    assert FATOR_GRAHAM == 22.5


def test_changelog_tem_a_1_0_0():
    assert set(registry.CHANGELOG) == set(NOMES)
    for nome in NOMES:
        mudancas = registry.CHANGELOG[nome]
        esperado = {
            "Graham": ["1.0.0", "1.1.0", "1.2.0", "2.0.0", "2.1.0"],
            "Bazin": ["1.0.0", "1.0.1", "2.0.0", "2.1.0"],
            "Lynch": ["1.0.0", "1.1.0", "2.0.0", "2.1.0"],
            "Gordon": ["1.0.0", "1.1.0", "2.0.0", "2.1.0"],
            "P/VP do FII": ["1.0.0", "1.1.0", "1.2.0"],
            "Rendimento do FII": ["1.0.0", "2.0.0", "2.1.0"],
            "Bancos": ["1.0.0", "1.1.0"],
        }[nome]  # F2A-21, F2A-25 e F2B-4
        assert [m.version for m in mudancas] == esperado
        assert mudancas[0].descricao == (
            "ficha bancos1.1: lente nova de P/VP justificado em regime real; sem consumidor no motor"
            if nome == "Bancos"
            else "comportamento da V1, extraído na Fase 1, sem mudança de número"
        )
        assert registry.obter(nome).version == mudancas[-1].version


def test_nomes_sao_unicos():
    nomes = [m.nome for m in registry.METODOS]
    assert len(nomes) == len(set(nomes))


def test_validar_rejeita_registro_inconsistente():
    g = registry.obter("Graham")
    ok = {"Graham": (registry.Mudanca("2.1.0", "x"),)}
    registry.validar((g,), ok)
    with pytest.raises(ValueError, match="repetido"):
        registry.validar((g, g), ok)
    with pytest.raises(ValueError, match="não termina na versão"):
        registry.validar((g,), {"Graham": (registry.Mudanca("0.9.0", "x"),)})
    with pytest.raises(ValueError, match="não termina na versão"):
        registry.validar((g,), {})
    with pytest.raises(ValueError, match="não está no registro"):
        registry.validar((g,), {**ok, "Outro": (registry.Mudanca("1.0.0", "x"),)})
