import dataclasses
from datetime import UTC, date, datetime

import pytest

from sentinela.domain.enums import AssetType, ModeloDemonstracao, Perfil, Regime
from sentinela.domain.units import BRL, Percent, RateNominal, RateReal, Ratio
from sentinela.methods.base import (
    TIPO_TAXA,
    Abstention,
    Intermediario,
    MethodInputs,
    MethodResult,
    ValuationMethod,
)

HOJE = date(2026, 10, 2)
# F2B-4: os métodos de teste valem para STOCK com modelo empresa (BPP consolidado).
ESCOPO = {"classe_ativo": AssetType.STOCK, "modelo": ModeloDemonstracao.EMPRESA}


@dataclasses.dataclass(frozen=True)
class _Params:
    fator: float


@dataclasses.dataclass(frozen=True)
class _ParamsComPadrao:
    fator: float = 2.0


class _Dobro(ValuationMethod):
    nome = "Dobro"
    version = "1.0.0"
    regime = Regime.SEM_TAXA
    requires = ("preco", "lpa")
    assumptions = ("o dobro do preço",)
    applies_to = frozenset({AssetType.STOCK})
    modelos = frozenset({ModeloDemonstracao.EMPRESA})
    params_type = _Params

    def _calcular(self, inputs, params):
        return MethodResult(
            metodo=self.nome,
            versao=self.version,
            valor=BRL(inputs.preco.valor * params.fator),
            intermediarios=(Intermediario("fator", Ratio(params.fator)),),
            alertas=("alerta",),
        )


def _inputs(**kw):
    return MethodInputs(as_of=HOJE, **{**ESCOPO, **kw})


# ── MethodInputs ──────────────────────────────────────────────────────────────


def test_inputs_sao_congelados():
    i = _inputs(preco=BRL(10.0))
    with pytest.raises(dataclasses.FrozenInstanceError):
        i.preco = BRL(11.0)
    with pytest.raises(dataclasses.FrozenInstanceError):
        i.as_of = date(2026, 1, 1)
    with pytest.raises(AttributeError):
        i.novo = 1
    assert hash(i) == hash(_inputs(preco=BRL(10.0)))


def test_inputs_exigem_as_of():
    with pytest.raises(TypeError):
        MethodInputs()
    with pytest.raises(TypeError):
        MethodInputs(preco=BRL(1.0))
    with pytest.raises(TypeError, match="as_of deve ser date"):
        MethodInputs(as_of="2026-10-02")
    with pytest.raises(TypeError, match="as_of deve ser date"):
        MethodInputs(as_of=None)
    with pytest.raises(TypeError, match="as_of deve ser date"):
        MethodInputs(as_of=datetime(2026, 10, 2, 12, 0, tzinfo=UTC))
    assert MethodInputs(as_of=HOJE).as_of == HOJE


def test_inputs_comecam_vazios_e_com_flags_da_v1():
    i = _inputs()
    for campo in (
        "preco",
        "lpa",
        "vpa",
        "pl",
        "pvp",
        "dy",
        "roe",
        "selic",
        "vacancia",
        "perfil",
    ):
        assert getattr(i, campo) is None
    assert i.pl_confiavel is True
    assert i.dy_confiavel is True


def test_inputs_checam_o_tipo_de_cada_campo():
    ok = _inputs(
        preco=BRL(1.0),
        lpa=BRL(1.0),
        vpa=BRL(1.0),
        pl=Ratio(1.0),
        pvp=Ratio(1.0),
        dy=Ratio(0.05),
        roe=Ratio(0.1),
        selic=RateNominal(0.1),
        vacancia=Ratio(0.1),
        perfil=Perfil.RENDA,
    )
    assert ok.perfil is Perfil.RENDA
    ruins = {
        "preco": 10.0,
        "lpa": Ratio(1.0),
        "vpa": Percent(1.0),
        "pl": 10.0,
        "pvp": BRL(1.0),
        "dy": Percent(5.0),
        "roe": 0.1,
        "selic": RateReal(0.1),
        "vacancia": Percent(10.0),
        "perfil": "renda",
    }
    for campo, valor in ruins.items():
        with pytest.raises(TypeError, match=f"{campo} deve ser"):
            _inputs(**{campo: valor})


def test_flags_precisam_ser_booleanas():
    for campo in ("pl_confiavel", "dy_confiavel"):
        with pytest.raises(TypeError, match=f"{campo} deve ser bool"):
            _inputs(**{campo: 1})


# ── MethodResult e Abstention ─────────────────────────────────────────────────


def test_resultado_tem_valor_com_unidade_e_intermediarios_nomeados():
    r = MethodResult("M", "1.0.0", BRL(5.0), (Intermediario("a", Ratio(1.0)),), ("x",))
    assert r.valor == BRL(5.0)
    assert r.obter("a") == Ratio(1.0)
    with pytest.raises(KeyError, match="b"):
        r.obter("b")
    with pytest.raises(dataclasses.FrozenInstanceError):
        r.valor = BRL(6.0)
    assert MethodResult("M", "1.0.0", BRL(5.0)).intermediarios == ()
    assert MethodResult("M", "1.0.0", BRL(5.0)).alertas == ()


def test_resultado_converte_listas_em_tuplas_e_valida_o_valor():
    r = MethodResult("M", "1.0.0", BRL(1.0), [Intermediario("a", BRL(1.0))], ["x"])
    assert isinstance(r.intermediarios, tuple)
    assert isinstance(r.alertas, tuple)
    with pytest.raises(TypeError, match="valor deve ter unidade"):
        MethodResult("M", "1.0.0", 5.0)
    with pytest.raises(TypeError, match="intermediarios devem ser Intermediario"):
        MethodResult("M", "1.0.0", BRL(1.0), ("a",))


def test_intermediario_valida_nome_e_valor():
    assert Intermediario("a", 1.5).valor == 1.5
    with pytest.raises(ValueError, match="nome"):
        Intermediario("", BRL(1.0))
    with pytest.raises(TypeError, match="valor do intermediário"):
        Intermediario("a", "1")
    with pytest.raises(TypeError, match="valor do intermediário"):
        Intermediario("a", True)


def test_abstencao_exige_motivo_e_e_congelada():
    a = Abstention("M", "1.0.0", "sem LPA")
    assert a.motivo == "sem LPA"
    with pytest.raises(ValueError, match="motivo"):
        Abstention("M", "1.0.0", "")
    with pytest.raises(ValueError, match="motivo"):
        Abstention("M", "1.0.0", "   ")
    with pytest.raises(dataclasses.FrozenInstanceError):
        a.motivo = "outro"


# ── ValuationMethod ───────────────────────────────────────────────────────────


def test_insumo_ausente_vira_abstencao():
    m = _Dobro()
    r = m.calcular(_inputs(preco=BRL(10.0)), _Params(2.0))
    assert isinstance(r, Abstention)
    assert (r.metodo, r.versao) == ("Dobro", "1.0.0")
    assert r.motivo == "insumo ausente: lpa"
    r2 = m.calcular(_inputs(), _Params(2.0))
    assert r2.motivo == "insumo ausente: preco, lpa"


def test_insumos_presentes_calculam_com_os_parametros():
    r = _Dobro().calcular(_inputs(preco=BRL(10.0), lpa=BRL(1.0)), _Params(3.0))
    assert isinstance(r, MethodResult)
    assert r.valor == BRL(30.0)
    assert r.obter("fator") == Ratio(3.0)
    assert r.alertas == ("alerta",)


def test_parametros_precisam_ser_do_tipo_declarado():
    i = _inputs(preco=BRL(10.0), lpa=BRL(1.0))
    with pytest.raises(TypeError, match="parâmetros devem ser _Params"):
        _Dobro().calcular(i, {"fator": 2.0})
    with pytest.raises(TypeError, match="parâmetros devem ser _Params"):
        _Dobro().calcular(i, None)


def test_inputs_precisam_ser_method_inputs():
    with pytest.raises(TypeError, match="MethodInputs"):
        _Dobro().calcular({"preco": 1}, _Params(1.0))


def test_regime_bate_com_o_tipo_da_taxa():
    assert TIPO_TAXA[Regime.REAL] is RateReal
    assert TIPO_TAXA[Regime.NOMINAL] is RateNominal
    assert TIPO_TAXA[Regime.SEM_TAXA] is None
    assert set(TIPO_TAXA) == set(Regime)
    # a Selic é nominal: só método NOMINAL pode exigi-la
    for regime in (Regime.REAL, Regime.SEM_TAXA):
        with pytest.raises(TypeError, match="selic"):
            _metodo(regime=regime, requires=("selic",))
    ok = _metodo(regime=Regime.NOMINAL, requires=("selic",))
    assert ok.regime is Regime.NOMINAL
    with pytest.raises(TypeError, match="RateReal"):
        _inputs(selic=RateReal(0.06))


def _metodo(**sobrescreve):
    attrs = {
        "nome": "X",
        "version": "1.0.0",
        "regime": Regime.SEM_TAXA,
        "requires": ("preco",),
        "assumptions": (),
        "applies_to": frozenset({AssetType.STOCK}),
        "modelos": frozenset({ModeloDemonstracao.EMPRESA}),
        "params_type": _Params,
        "_calcular": lambda self, inputs, params: Abstention("X", "1.0.0", "n/a"),
    }
    attrs.update(sobrescreve)
    return type("X", (ValuationMethod,), attrs)


def test_metadados_obrigatorios_na_declaracao():
    assert _metodo().nome == "X"
    for campo in (
        "nome",
        "version",
        "regime",
        "requires",
        "assumptions",
        "applies_to",
        "params_type",
    ):
        attrs = {campo: None}
        with pytest.raises(TypeError, match=campo):
            _metodo(**attrs)


def test_metadado_ausente_na_declaracao_e_rejeitado():
    for campo in (
        "nome",
        "version",
        "regime",
        "requires",
        "assumptions",
        "applies_to",
        "params_type",
    ):
        attrs = {
            "nome": "X",
            "version": "1.0.0",
            "regime": Regime.SEM_TAXA,
            "requires": (),
            "assumptions": (),
            "applies_to": frozenset({AssetType.STOCK}),
            "params_type": _Params,
            "_calcular": lambda self, inputs, params: None,
        }
        del attrs[campo]
        with pytest.raises(TypeError, match=f"{campo} é obrigatório"):
            type("Z", (ValuationMethod,), attrs)


def test_metadados_invalidos_sao_rejeitados():
    with pytest.raises(TypeError, match="version"):
        _metodo(version="1.0")
    with pytest.raises(TypeError, match="version"):
        _metodo(version="v1.0.0")
    with pytest.raises(TypeError, match="regime"):
        _metodo(regime="NOMINAL")
    with pytest.raises(TypeError, match="requires"):
        _metodo(requires=("inexistente",))
    with pytest.raises(TypeError, match="requires"):
        _metodo(requires=("as_of",))
    with pytest.raises(TypeError, match="requires"):
        _metodo(requires=("pl_confiavel",))
    with pytest.raises(TypeError, match="requires"):
        _metodo(requires=["preco"])
    with pytest.raises(TypeError, match="applies_to"):
        _metodo(applies_to=frozenset())
    with pytest.raises(TypeError, match="applies_to"):
        _metodo(applies_to=frozenset({"STOCK"}))
    with pytest.raises(TypeError, match="assumptions"):
        _metodo(assumptions=["lista"])
    with pytest.raises(TypeError, match="nome"):
        _metodo(nome="")


def test_parametros_sao_dataclass_congelada_sem_padrao():
    with pytest.raises(TypeError, match="params_type"):
        _metodo(params_type=dict)
    with pytest.raises(TypeError, match="congelada"):
        _metodo(params_type=dataclasses.make_dataclass("P", [("a", float)]))
    with pytest.raises(TypeError, match="sem valor padrão"):
        _metodo(params_type=_ParamsComPadrao)


def test_metodo_sem_calcular_nao_instancia():
    attrs = {
        k: v
        for k, v in {
            "nome": "Y",
            "version": "1.0.0",
            "regime": Regime.SEM_TAXA,
            "requires": (),
            "assumptions": (),
            "applies_to": frozenset({AssetType.FII}),
            "params_type": _Params,
        }.items()
    }
    Y = type("Y", (ValuationMethod,), attrs)
    with pytest.raises(TypeError):
        Y()


def test_calcular_nao_pode_ser_sobrescrito_para_pular_a_checagem():
    with pytest.raises(TypeError, match="calcular"):
        _metodo(calcular=lambda self, i, p: None)


def test_calcular_devolve_so_resultado_ou_abstencao():
    ruim = _metodo(_calcular=lambda self, inputs, params: 42)
    with pytest.raises(TypeError, match="MethodResult ou Abstention"):
        ruim().calcular(_inputs(preco=BRL(1.0)), _Params(1.0))


def test_regime_e_perfil_enums():
    assert {r.name for r in Regime} == {"REAL", "NOMINAL", "SEM_TAXA"}
    assert {p.name for p in Perfil} == {"RENDA", "CRESCIMENTO"}


def test_custo_de_capital_real_so_em_metodo_real():
    for regime in (Regime.NOMINAL, Regime.SEM_TAXA):
        with pytest.raises(TypeError, match="custo_capital_real"):
            _metodo(regime=regime, requires=("custo_capital_real",))
    tipo = _metodo(regime=Regime.REAL, requires=("custo_capital_real",))
    assert tipo.requires == ("custo_capital_real",)
    assert isinstance(tipo().calcular(_inputs(), _Params(1.0)), Abstention)
    assert (
        tipo().calcular(_inputs(), _Params(1.0)).motivo
        == "insumo ausente: custo_capital_real"
    )


def test_inputs_reais_aditivos_tipificados_e_congelados():
    from sentinela.domain.units import Inflacao

    vazio = _inputs()
    assert vazio.custo_capital_real is None
    assert vazio.inflacao is None
    real = _inputs(custo_capital_real=RateReal(0.1), inflacao=Inflacao(-0.01))
    assert real.custo_capital_real == RateReal(0.1)
    assert real.inflacao == Inflacao(-0.01)
    with pytest.raises(dataclasses.FrozenInstanceError):
        real.inflacao = Inflacao(0)
    with pytest.raises(TypeError, match="custo_capital_real"):
        _inputs(custo_capital_real=RateNominal(0.1))
    with pytest.raises(TypeError, match="inflacao"):
        _inputs(inflacao=Ratio(0.04))


def test_contrato_real_recebe_insumos_e_inflacao_com_unidade():
    from sentinela.domain.units import Inflacao

    def calcular(self, inputs, params):
        return MethodResult(
            self.nome,
            self.version,
            inputs.custo_capital_real,
            intermediarios=(Intermediario("inflacao", inputs.inflacao),),
        )

    tipo = _metodo(
        regime=Regime.REAL,
        requires=("custo_capital_real", "inflacao"),
        _calcular=calcular,
    )
    resultado = tipo().calcular(
        _inputs(custo_capital_real=RateReal(0.1), inflacao=Inflacao(0.04)), _Params(1)
    )
    assert resultado.valor == RateReal(0.1)
    assert resultado.obter("inflacao") == Inflacao(0.04)


# ── escopo por classe e modelo (F2B-4) ────────────────────────────────────────

_METODOS_DE_EMPRESA = ("Graham", "Bazin", "Lynch", "Gordon")
_METODOS_DE_FII = ("Rendimento do FII", "P/VP do FII")


def _metodo_do_registro(nome):
    from sentinela.methods import registry

    return registry.obter(nome)


def _params_do_registro(metodo):
    # Parâmetros quaisquer: o escopo vem antes de qualquer conta.
    campos = dataclasses.fields(metodo.params_type)
    return metodo.params_type(**{f.name: None for f in campos})


def test_escopo_e_aplicado():
    for nome in _METODOS_DE_EMPRESA:
        m = _metodo_do_registro(nome)
        r = m.calcular(
            _inputs(classe_ativo=AssetType.FII, modelo=None), _params_do_registro(m)
        )
        assert r == Abstention(m.nome, m.version, "classe FII fora do escopo do método")
        for modelo in (ModeloDemonstracao.BANCO, ModeloDemonstracao.SEGURADORA):
            r = m.calcular(
                _inputs(classe_ativo=AssetType.UNIT, modelo=modelo),
                _params_do_registro(m),
            )
            assert r == Abstention(
                m.nome, m.version, f"modelo {modelo.value} fora do escopo do método"
            )
    for nome in _METODOS_DE_FII:
        m = _metodo_do_registro(nome)
        r = m.calcular(
            _inputs(classe_ativo=AssetType.STOCK, modelo=None, pvp=Ratio(1.0)),
            _params_do_registro(m),
        )
        assert r == Abstention(
            m.nome, m.version, "classe STOCK fora do escopo do método"
        )


@pytest.mark.parametrize("classe", [AssetType.STOCK, AssetType.UNIT])
def test_stock_unit_sem_modelo_abstem(classe):
    for nome in _METODOS_DE_EMPRESA:
        m = _metodo_do_registro(nome)
        r = m.calcular(
            _inputs(classe_ativo=classe, modelo=None), _params_do_registro(m)
        )
        assert r == Abstention(
            m.nome,
            m.version,
            "modelo da demonstração não demonstrado no BPP consolidado",
        )


def test_sem_classe_abstem():
    from sentinela.methods import registry

    for m in registry.METODOS:
        r = m.calcular(
            _inputs(classe_ativo=None, modelo=None, pvp=Ratio(1.0)),
            _params_do_registro(m),
        )
        assert r == Abstention(m.nome, m.version, "classe do ativo ausente")


def test_fii_com_classe_oficial_nao_exige_bpp():
    from sentinela.methods.fii_nav import FiiNav, FiiNavParams

    r = FiiNav().calcular(
        _inputs(classe_ativo=AssetType.FII, modelo=None, pvp=Ratio(1.0)),
        FiiNavParams(premio_alto=1.3, premio_moderado=1.1, desconto=0.9),
    )
    assert isinstance(r, MethodResult)
