import dataclasses
import importlib
import inspect
from pathlib import Path

import pytest

import sentinela.methods as pacote
from config import MACRO
from sentinela.domain.enums import AssetType, Regime
from sentinela.methods import registry
from sentinela.methods.base import ValuationMethod
from sentinela.methods.bazin import BazinParams
from sentinela.methods.fii_nav import FiiNavParams
from sentinela.methods.fii_yield import FiiYieldParams
from sentinela.methods.gordon import PAYOUT_SEM_LPA, GordonParams
from sentinela.methods.graham import FATOR_GRAHAM, GrahamParams
from sentinela.methods.lynch import LynchParams

NOMES = ["Graham", "Bazin", "Lynch", "Gordon", "Bazin FII", "P/VP do FII"]

# Valores da 1.0.0, lidos hoje do MacroContext: mudar uma constante sem criar versão
# nova do método quebra este teste. campo do método -> (constante do MacroContext, valor)
PARAMETROS_1_0_0 = {
    "Graham": (
        GrahamParams,
        {
            "pl_limite": ("GRAHAM_PL_LIMITE", 25.0),
            "pl_piso": ("GRAHAM_PL_FLOOR", 7.0),
            "pvp_limite_renda": ("GRAHAM_PVP_LIMITE_RENDA", 2.5),
            "pvp_limite_crescimento": ("GRAHAM_PVP_LIMITE_CRESCIMENTO", 3.0),
        },
    ),
    "Bazin": (
        BazinParams,
        {
            "dy_min": ("BAZIN_DY_MIN", 0.05),
            "dy_armadilha": ("BAZIN_DY_ARMADILHA", 0.15),
            "taxa_min": ("BAZIN_TAXA_MIN", 0.05),
        },
    ),
    "Lynch": (
        LynchParams,
        {
            "payout_max": ("LYNCH_PAYOUT_MAX", 0.95),
            "g_max": ("LYNCH_G_MAX", 0.25),
            "pl_multiplicador": ("LYNCH_PL_MULTIPLICADOR", 1.5),
            "pl_max": ("LYNCH_PL_MAX", 35.0),
        },
    ),
    "Gordon": (
        GordonParams,
        {
            "dy_min": ("GORDON_DY_MIN", 0.04),
            "roe_min": ("GORDON_ROE_MIN", 0.10),
            "g_max": ("GORDON_G_MAX", 0.08),
            "premio_risco": ("GORDON_PREMIO_RISCO", 0.07),
            "payout_max": ("GORDON_PAYOUT_MAX", 0.95),
        },
    ),
    "Bazin FII": (FiiYieldParams, {"fator_ir": ("FII_FATOR_IR", 0.85)}),
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
        assert e.version == "1.0.0"
        assert isinstance(e.regime, Regime)
        assert e.requires
        assert e.assumptions
        assert e.applies_to
    assert len(registry.METODOS) == 6


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
    assert len(classes) == 6


def test_regime_coerente_com_a_taxa():
    regimes = {e.nome: e.regime for e in registry.entradas()}
    assert regimes == {
        "Graham": Regime.SEM_TAXA,
        "Bazin": Regime.NOMINAL,
        "Lynch": Regime.NOMINAL,
        "Gordon": Regime.NOMINAL,
        "Bazin FII": Regime.NOMINAL,
        "P/VP do FII": Regime.SEM_TAXA,
    }
    for e in registry.entradas():
        if "selic" in e.requires:
            assert e.regime is Regime.NOMINAL
        if e.regime is Regime.SEM_TAXA:
            assert "selic" not in e.requires
    assert Regime.REAL not in set(regimes.values())


def test_applies_to_descreve_o_roteamento_da_v1_sem_aplicar():
    acoes = frozenset({AssetType.STOCK, AssetType.UNIT})
    esperado = {
        "Graham": acoes,
        "Bazin": acoes,
        "Lynch": acoes,
        "Gordon": acoes,
        "Bazin FII": frozenset({AssetType.FII}),
        "P/VP do FII": frozenset({AssetType.FII}),
    }
    assert {e.nome: e.applies_to for e in registry.entradas()} == esperado
    todos = set().union(*esperado.values())
    assert AssetType.ETF not in todos
    assert AssetType.BDR not in todos


def test_parametros_da_1_0_0_fixados():
    assert set(PARAMETROS_1_0_0) == set(NOMES)
    for nome, (tipo, campos) in PARAMETROS_1_0_0.items():
        assert registry.obter(nome).params_type is tipo
        assert {f.name for f in dataclasses.fields(tipo)} == set(campos)
        for campo, (constante, valor) in campos.items():
            assert getattr(MACRO, constante) == valor, f"{nome}.{campo} ({constante})"
    # constantes de fórmula que moram no módulo do método
    assert FATOR_GRAHAM == 22.5
    assert PAYOUT_SEM_LPA == 0.5


def test_changelog_tem_a_1_0_0():
    assert set(registry.CHANGELOG) == set(NOMES)
    for nome in NOMES:
        mudancas = registry.CHANGELOG[nome]
        assert [m.version for m in mudancas] == ["1.0.0"]
        assert mudancas[0].descricao == (
            "comportamento da V1, extraído na Fase 1, sem mudança de número"
        )
        assert registry.obter(nome).version == mudancas[-1].version


def test_nomes_sao_unicos():
    nomes = [m.nome for m in registry.METODOS]
    assert len(nomes) == len(set(nomes))


def test_validar_rejeita_registro_inconsistente():
    g = registry.obter("Graham")
    ok = {"Graham": (registry.Mudanca("1.0.0", "x"),)}
    registry.validar((g,), ok)
    with pytest.raises(ValueError, match="repetido"):
        registry.validar((g, g), ok)
    with pytest.raises(ValueError, match="não termina na versão"):
        registry.validar((g,), {"Graham": (registry.Mudanca("0.9.0", "x"),)})
    with pytest.raises(ValueError, match="não termina na versão"):
        registry.validar((g,), {})
    with pytest.raises(ValueError, match="não está no registro"):
        registry.validar((g,), {**ok, "Outro": (registry.Mudanca("1.0.0", "x"),)})
