"""Contratos independentes para as fronteiras do módulo misto (gate G/F2C-31).

D18/D19/D20 e fichas Gordon/por ação: identidade documental, ações líquidas e
proveniência; dados de terceiros não substituem fechamento do provedor primário.
Esperados aritméticos são declarados nos casos, sem motor como oráculo.
"""

from datetime import date

import pytest

from market_engine import RISCO_FORA_DA_CVM
from tests.test_gordon_motor import Instante
from tests.test_market_engine import FakeBrapi, FakeCache, FakeCVM, _engine
from tests.test_market_engine_acoes_cvm import CNPJ, _composicao, _ind, _motor


@pytest.mark.parametrize(
    "campo,valor",
    [("cnpj", "22.222.222/0001-22"), ("fim", "2024-12-31"), ("versao", "2")],
)
def test_documento_distinto_nao_empresta_acoes_ou_vpa_a_lente(
    monkeypatch, campo, valor
):
    monkeypatch.setattr("market_engine.datetime", Instante)
    motor = _motor(monkeypatch, _ind())
    fato = {
        "cnpj": CNPJ,
        "versao": "1",
        "inicio": "2025-01-01",
        "fim": "2025-12-31",
        campo: valor,
    }
    motor.cvm.gordon_do_documento = lambda *a: dict(fato)
    dados = {
        "cd_cvm": 9999,
        "preco_atual": 20.0,
        "especie": "ON",
        "classe_ativo": "STOCK",
    }
    assert motor._buscar_cvm("TSTA3", dados) is True
    assert dados["gordon_cvm"]["acoes_base"] is None
    assert dados["gordon_cvm"]["vpa"] is None
    assert dados["gordon_cvm"]["base_acionaria_compativel"] is False
    # O VPA próprio do documento válido continua10.000/1.000 =10.
    assert dados["vpa"] == 10


@pytest.mark.parametrize("escala,compativel", [("UNIDADE", True), (None, False)])
def test_documento_e_base_recente_preservam_identidade_e_janela(
    monkeypatch, escala, compativel
):
    monkeypatch.setattr("market_engine.datetime", Instante)
    motor = _motor(monkeypatch, _ind(proveniencia={"documento": "DFP", "versao": "1"}))
    pedidos = []
    fonte_recente = {
        "documento": "ITR sintético",
        "versao": "1",
        "data_entrega": "2026-08-10",
    }

    def anual(codigo, indicador, instante):
        pedidos.append((codigo, instante))
        return {"cnpj": CNPJ, "versao": 1, "inicio": "2025-01-01", "fim": "2025-12-31"}

    def recente(cnpj, instante, ano):
        assert (cnpj, ano) == (CNPJ, 2025)
        assert instante.tzinfo is not None
        return {
            "composicao": _composicao(dt="2026-06-30"),
            "escala": escala,
            "proveniencia": fonte_recente,
        }

    motor.cvm.gordon_do_documento = anual
    motor.cvm.composicao_mais_recente = recente
    motor.cvm.modelo_do_documento = lambda *a: "empresa"
    dados = {
        "cd_cvm": 9999,
        "preco_atual": 20.0,
        "especie": "ON",
        "classe_ativo": "STOCK",
        "_shares_outstanding": 700.0,
    }
    assert motor._buscar_cvm("TSTA3", dados)
    assert pedidos == [(9999, Instante.now())]
    assert dados["gordon_cvm"]["acoes_base"] == 1000
    assert dados["gordon_cvm"]["vpa"] == 10
    assert dados["gordon_cvm"]["fator_unit"] == 1
    assert dados["gordon_cvm"]["direitos_compativeis"] is True
    assert dados["gordon_cvm"]["base_acionaria_compativel"] is compativel
    assert dados["janela_contabil_cvm"] == (date(2025, 1, 1), date(2025, 12, 31))
    assert dados["base_acionaria_gordon"]["proveniencia"] == fonte_recente
    assert dados["modelo_bpp"] == "empresa"
    assert dados["modelo_bpp_proveniencia"] == {"documento": "DFP", "versao": "1"}


def test_abstencao_documental_nao_inventa_fatos_e_preserva_anuais(monkeypatch):
    motor = _motor(monkeypatch, _ind())
    motor.cvm.gordon_do_documento = lambda *a: {
        "abstencao": "DVA indisponível no documento"
    }
    dados = {
        "cd_cvm": 9999,
        "preco_atual": 20.0,
        "especie": "ON",
        "classe_ativo": "STOCK",
    }
    assert motor._buscar_cvm("TSTA3", dados)
    assert dados["gordon_cvm"] == {"abstencao": "DVA indisponível no documento"}
    assert "base_acionaria_gordon" not in dados
    assert dados["lpa"] == 2.1
    assert dados["vpa"] == 10


def test_indicadores_e_motivos_cvm_nao_sao_apagados_por_campos_independentes(
    monkeypatch,
):
    motor = _motor(
        monkeypatch,
        _ind(
            divida_liquida=600.0,
            ebitda=1000.0,
            divida_liq_ebitda=0.6,
            div_liq_patrimonio=0.06,
            alavancagem_regime="DFP anual",
            alavancagem_motivos={"nota": "contexto público"},
            contas_abstidas={"roic": "conta não demonstrada"},
        ),
    )
    dados = {
        "cd_cvm": 9999,
        "preco_atual": 20.0,
        "especie": "ON",
        "classe_ativo": "STOCK",
    }
    assert motor._buscar_cvm("TSTA3", dados)
    assert dados["alavancagem_cvm"] == {
        "regime": "DFP anual",
        "divida_liquida": 600.0,
        "ebitda": 1000.0,
        "motivos": {"nota": "contexto público"},
    }
    assert dados["divida_liq_ebitda"] == 0.6
    assert dados["div_liq_patrimonio"] == 0.06
    assert any("conta não demonstrada" in r for r in dados["riscos_dados"])
    assert any("contexto público" in r for r in dados["riscos_dados"])


@pytest.mark.parametrize(
    "classe,sem_referencia,avisa",
    [("FII", False, False), ("STOCK", False, True), ("STOCK", True, False)],
)
def test_ausencia_de_cvm_distingue_escopo_de_falha_da_referencia(
    monkeypatch, classe, sem_referencia, avisa
):
    motor = _engine(monkeypatch, info={}, cvm=FakeCVM())
    dados = {"classe_ativo": classe, "_sem_referencia": sem_referencia}
    assert motor._buscar_cvm("TSTF11" if classe == "FII" else "TSTA3", dados) is False
    assert dados["cvm_disponivel"] is False
    assert (RISCO_FORA_DA_CVM in dados.get("riscos_dados", [])) is avisa


def test_provedor_cvm_ausente_nao_devolve_sucesso(monkeypatch):
    motor = _engine(monkeypatch, info={})
    assert motor._buscar_cvm("TSTA3", {}) is False


def test_cache_nao_guarda_serie_historico_nem_precos_e_preserva_prejuizo(monkeypatch):
    cache = FakeCache()
    motor = _engine(monkeypatch, info={}, cache=cache)
    fundamentos = {
        "pl": -10.0,
        "pvp": 1.5,
        "roe": -0.2,
        "dy": 0.04,
        "lpa": -2.0,
        "vpa": 20.0,
    }
    dados = {
        **fundamentos,
        "fonte_fundamentos": "CVM",
        "historico": object(),
        "serie_cvm": {"exercicios": [2025]},
        "preco_atual": 20.0,
        "ticker": "TSTA3",
    }
    motor._salvar_cache_se_valido("TSTA3", dados)
    assert len(cache.saved) == 1
    ticker, payload, fonte = cache.saved[0]
    assert (ticker, fonte) == ("TSTA3", "CVM")
    assert payload == fundamentos


@pytest.mark.parametrize("marcador", ["dados_cache", "dados_manual"])
def test_observacao_reutilizada_nao_e_regravada_como_nova(monkeypatch, marcador):
    cache = FakeCache()
    motor = _engine(monkeypatch, info={}, cache=cache)
    dados = {
        "pl": 8.0,
        "pvp": 1.2,
        "roe": 0.1,
        "dy": 0.04,
        "fonte_fundamentos": "CVM",
        marcador: True,
    }
    motor._salvar_cache_se_valido("TSTA3", dados)
    assert cache.saved == []


@pytest.mark.parametrize("campo", ["pl", "pvp", "roe", "dy"])
def test_cache_nao_converte_fundamentos_incompletos_em_snapshot(monkeypatch, campo):
    cache = FakeCache()
    motor = _engine(monkeypatch, info={}, cache=cache)
    dados = {
        "pl": 8.0,
        "pvp": 1.2,
        "roe": 0.1,
        "dy": 0.04,
        "fonte_fundamentos": "CVM",
        campo: None,
    }
    motor._salvar_cache_se_valido("TSTA3", dados)
    assert cache.saved == []


@pytest.mark.parametrize(
    "preco_inicial,fonte_inicial,preco_final,fonte_final",
    [(20.0, "yfinance", 20.0, "yfinance"), (None, None, 30.0, "brapi")],
)
def test_brapi_respeita_preco_primario_e_conserva_proveniencia(
    monkeypatch, preco_inicial, fonte_inicial, preco_final, fonte_final
):
    motor = _engine(
        monkeypatch,
        info={},
        brapi=FakeBrapi(
            {
                "preco_atual": 30.0,
                "pl": 12.0,
                "pvp": 1.4,
                "roe": 0.2,
                "dy": 0.05,
                "divida_liq_ebitda": 99.0,
                "estranho": 123,
            }
        ),
    )
    dados = {"preco_atual": preco_inicial, "fonte_preco": fonte_inicial}
    assert motor._buscar_brapi("TSTA3", dados) is True
    assert dados["preco_atual"] == preco_final
    assert dados["fonte_preco"] == fonte_final
    assert (dados["pl"], dados["pvp"], dados["roe"], dados["dy"]) == (
        12.0,
        1.4,
        0.2,
        0.05,
    )
    assert dados["_field_sources"]["dy"] == "brapi"
    assert "divida_liq_ebitda" not in dados
    assert "estranho" not in dados
    assert dados["fonte_fundamentos"] == "brapi"
    assert dados["proveniencia"]["dy"]["fonte"] == "brapi"


@pytest.mark.parametrize(
    "classe,especie,preferencial,composicao,esperado",
    [
        ("STOCK", "ON", None, None, 2.0),
        ("STOCK", "PN", "PNA", None, 3.0),
        ("UNIT", None, None, {"ON": 1, "PNB": 2}, 8.0),
        ("UNIT", None, None, {"ON": 2, "PNA": 1}, 7.0),
    ],
)
def test_serie_identifica_emissor_classe_e_fator_da_unit(
    monkeypatch, classe, especie, preferencial, composicao, esperado
):
    from tests.test_cvm_series import EXERCICIO_2025, EXERCICIO_2026, _Hoje
    from tests.test_cvm_series import _ind as anual

    class Fonte:
        def indicadores_da_serie(self, codigo, ano, modelo):
            if codigo != 9876:
                return {}
            return {
                a: {**anual(a), "lpa_basico_por_classe": {"ON": [2.0], "PN": [3.0]}}
                for a in range(2021, 2026)
            }

        def acumulados_ttm(self, codigo, referencia, modelo):
            return EXERCICIO_2025 + EXERCICIO_2026 if codigo == 9876 else []

        def calcular_indicadores(self, *a, **k):
            return {}

    monkeypatch.setattr("market_engine.date", _Hoje)
    motor = _engine(monkeypatch, info={}, cvm=Fonte())
    dados = {
        "cd_cvm": 9876,
        "classe_ativo": classe,
        "especie": especie,
        "classe_preferencial": preferencial,
        "classes_preferenciais": ["PNA", "PNB"],
        "acoes_por_unit": composicao,
    }
    motor._buscar_cvm("TSTA11" if classe == "UNIT" else "TSTA3", dados)
    serie = dados["serie_cvm"]
    assert [e["lpa"] for e in serie["exercicios"]] == [esperado] * 5
    assert serie["proventos_base"].startswith("competência:")
    assert "não pela data-ex" in serie["proventos_base"]
    assert dados["ttm_cvm"]["valores"]["lucro_liquido"] == 75.0
    if preferencial:
        assert serie["exercicios"][0]["lpa_origem"]["classe"] == preferencial
        assert any(
            "PN única" in n for n in serie["exercicios"][0]["lpa_origem"]["notas"]
        )
    if composicao:
        origem = serie["exercicios"][0]["lpa_origem"]
        assert origem["origem"] == "unit"
        for componente, quantidade in composicao.items():
            assert origem["componentes"][componente]["quantidade"] == quantidade


def test_dados_anuais_antigos_nao_sao_promovidos_quando_ultimo_exercicio_falta(
    monkeypatch,
):
    class Fonte:
        def calcular_indicadores(self, codigo, anos=5, modelo="empresa"):
            return {2024: _ind()[2025]} if anos > 1 else {}

    motor = _engine(monkeypatch, info={}, cvm=Fonte())
    dados = {"cd_cvm": 9876, "classe_ativo": "STOCK", "especie": "ON"}
    assert motor._buscar_cvm("TSTA3", dados) is False
    assert dados["cvm_disponivel"] is False
    assert "lpa" not in dados
    assert "vpa" not in dados


@pytest.mark.parametrize(
    "composicao,esperado,direitos",
    [({"ON": 3}, 6.3, True), ({"ON": 1, "PN": 2}, 6.1, False)],
)
def test_fato_da_unit_mantem_fator_e_abstem_direitos_nao_demonstrados(
    monkeypatch, composicao, esperado, direitos
):
    motor = _motor(monkeypatch, _ind())
    motor.cvm.gordon_do_documento = lambda *a: {
        "cnpj": CNPJ,
        "versao": "1",
        "inicio": "2025-01-01",
        "fim": "2025-12-31",
    }
    dados = {
        "cd_cvm": 9999,
        "preco_atual": 20.0,
        "classe_ativo": "UNIT",
        "acoes_por_unit": composicao,
    }
    assert motor._buscar_cvm("TSTA11", dados)
    assert dados["gordon_cvm"]["fator_unit"] == 3
    assert dados["gordon_cvm"]["lpa"] == pytest.approx(esperado)
    assert dados["gordon_cvm"]["direitos_compativeis"] is direitos
    assert dados["gordon_cvm"]["vpa"] == 30.0


def test_cache_respeita_classe_oficial_do_classificador_injetado(monkeypatch):
    from sentinela.data.referencia.registro import Indice, Registro
    from sentinela.services.asset_classifier import AssetClassifier

    classificador = AssetClassifier(fiis_conhecidos=[], units_conhecidas=[])
    classificador._indice_lido = True
    classificador._indice = Indice(
        "2026-10-26",
        {},
        registros={"TSTF11": Registro("TSTF11", "FII", "caso sintético", {})},
    )
    cache = FakeCache()
    motor = _engine(monkeypatch, info={}, cache=cache)
    motor.asset_classifier = classificador
    motor._salvar_cache_se_valido(
        "TSTF11",
        {"ticker": "TSTF11", "pvp": 1.2, "dy": 0.06, "fonte_fundamentos": "CVM"},
    )
    assert cache.saved == [("TSTF11", {"pvp": 1.2, "dy": 0.06}, "CVM")]


@pytest.mark.parametrize("falha_bruto", [False, True])
def test_fechamento_bruto_fica_separado_e_falha_nao_apaga_fundamentos(
    monkeypatch, falha_bruto
):
    import pandas as pd

    ajustado = pd.DataFrame(
        {"Close": [10.0, 11.0]}, index=pd.to_datetime(["2026-10-22", "2026-10-23"])
    )
    bruto = pd.DataFrame(
        {"Close": [30.0, float("nan"), -1.0, 0.0, float("inf"), 31.0]},
        index=pd.date_range("2026-10-16", periods=6),
    )

    class Cotacao:
        info = {
            "trailingPE": 12.0,
            "priceToBook": 1.4,
            "returnOnEquity": 0.2,
            "dividendYield": 5.0,
        }

        def history(self, *args, **kwargs):
            if kwargs.get("auto_adjust") is False:
                if falha_bruto:
                    raise OSError("fechamento bruto indisponível")
                return bruto
            return ajustado

    cotacao = Cotacao()

    def por_codigo(codigo):
        assert codigo == "TSTA3.SA"
        return cotacao

    motor = _engine(monkeypatch, info={})
    monkeypatch.setattr("market_engine.yf.Ticker", por_codigo)
    dados = {}
    assert motor._buscar_yfinance("TSTA3", dados)
    pd.testing.assert_frame_equal(dados["historico"], ajustado)
    assert (dados["pl"], dados["pvp"], dados["roe"], dados["dy"]) == (
        12.0,
        1.4,
        0.2,
        0.05,
    )
    assert dados["_field_sources"]["preco_atual"] == "yfinance"
    assert dados["_field_sources"]["dy"] == "yfinance"
    if falha_bruto:
        assert "fechamentos_brutos" not in dados
    else:
        assert dados["fechamentos_brutos"] == {"2026-10-16": 30.0, "2026-10-21": 31.0}


def test_fonte_de_preco_vazia_nao_devolve_sucesso(monkeypatch):
    motor = _engine(monkeypatch, info={})
    dados = {}
    assert motor._buscar_yfinance("TSTA3", dados) is False
    assert "fonte_preco" not in dados


def test_reservas_d20_e_origem_do_lpa_seguem_seus_campos(monkeypatch):
    origem = {
        "documento": "DFP",
        "periodo_referencia": "2025-12-31",
        "versao": "1",
        "cnpj": CNPJ,
    }
    motor = _motor(
        monkeypatch,
        _ind(
            patrimonio_liquido=10000.0,
            lucro_liquido=2000.0,
            lpa_divulgado={"especie": "PN", "conta": "3.99.01.02", "valor": 2.0},
            proveniencia=origem,
            reservas_controladores={
                "lucro_controladores": "reserva de lucro sintética",
                "pl_controladores": "reserva de PL sintética",
            },
        ),
    )
    dados = {
        "cd_cvm": 9999,
        "preco_atual": 20.0,
        "especie": "ON",
        "classe_ativo": "STOCK",
    }
    assert motor._buscar_cvm("TSTA3", dados)
    assert dados["lpa"] == 2.0
    assert dados["vpa"] == 10.0
    assert dados["proveniencia"]["lpa"]["reservas"] == ["reserva de lucro sintética"]
    assert dados["proveniencia"]["vpa"]["reservas"] == ["reserva de PL sintética"]
    assert dados["proveniencia"]["roe"]["reservas"] == [
        "reserva de lucro sintética",
        "reserva de PL sintética",
    ]
    assert dados["proveniencia"]["lpa"]["lpa"]["origem"] == "recalculado"
    for campo in ["lpa", "vpa", "roe"]:
        assert dados["proveniencia"][campo]["periodo_referencia"] == "2025-12-31"
    # Múltiplos também usam preço de outra origem: não podem ganhar só a evidência da DFP.
    assert dados["proveniencia"].get("pl") != origem
    assert dados["proveniencia"].get("pvp") != origem


def test_cache_complementa_so_o_ausente_sem_apagar_prejuizo_oficial(monkeypatch):
    cache = FakeCache(
        {"pl": 12.0, "pvp": 3.0, "roe": 0.2, "dy": 0.05, "lpa": 2.0, "vpa": 20.0}
    )
    motor = _engine(monkeypatch, info={}, cache=cache)
    dados = {
        "pl": -10.0,
        "pvp": 1.5,
        "roe": -0.2,
        "lpa": -2.0,
        "vpa": 10.0,
        "fonte_fundamentos": "CVM",
        "_field_sources": {"pl": "CVM", "pvp": "CVM", "roe": "CVM"},
    }
    assert motor._aplicar_cache_fundamentos("TSTA3", dados) is True
    assert (dados["pl"], dados["pvp"], dados["roe"], dados["lpa"], dados["vpa"]) == (
        -10.0,
        1.5,
        -0.2,
        -2.0,
        10.0,
    )
    assert dados["dy"] == 0.05
    assert dados["dados_cache"] is True
    assert dados["_field_sources"] == {
        "pl": "CVM",
        "pvp": "CVM",
        "roe": "CVM",
        "dy": "fundamentals_cache",
    }


@pytest.mark.parametrize("fonte", [None, "yfinance_partial"])
def test_fonte_incompleta_nao_e_rotulada_como_observacao_nova(monkeypatch, fonte):
    cache = FakeCache()
    motor = _engine(monkeypatch, info={}, cache=cache)
    motor._salvar_cache_se_valido(
        "TSTA3",
        {"pl": 8.0, "pvp": 1.2, "roe": 0.1, "dy": 0.04, "fonte_fundamentos": fonte},
    )
    assert cache.saved == []


def test_erro_de_leitura_do_cache_preserva_campos_existentes(monkeypatch):
    class CacheIndisponivel:
        def buscar_fundamentos_cache(self, ticker):
            raise OSError("cache indisponível")

    motor = _engine(monkeypatch, info={}, cache=CacheIndisponivel())
    dados = {"pl": -10.0, "lpa": -2.0}
    assert motor._aplicar_cache_fundamentos("TSTA3", dados) is False
    assert dados == {"pl": -10.0, "lpa": -2.0}


@pytest.mark.parametrize(
    "campo,valor,fonte,canonica,cache,manual,unidade",
    [
        ("preco_atual", 20.0, "yfinance", "yfinance", False, False, "BRL"),
        ("preco_atual", 20.0, "brapi", "brapi", False, False, "BRL"),
        ("dy", 0.05, "brapi", "brapi", False, False, "ratio"),
        ("pl", -10.0, "CVM", "CVM", False, False, "ratio"),
        ("pvp", 1.5, "cache", "fundamentals_cache", True, False, "ratio"),
        ("roe", -0.2, "CVM", "CVM", False, False, "ratio"),
        ("dy", 0.06, "manual_fii", "manual_fallback", False, True, "ratio"),
        ("pvp", 1.5, "manual_fii", "manual_fallback", False, True, "ratio"),
        ("pl", 12.0, "fundamentals_cache", "fundamentals_cache", True, False, "ratio"),
    ],
)
def test_transporte_de_valor_unidade_e_flags_nao_inventa_origem(
    monkeypatch, campo, valor, fonte, canonica, cache, manual, unidade
):
    # D18: o registro transporta o que recebeu; não testa os pesos heurísticos de confiança.
    motor = _engine(monkeypatch, info={})
    registro = motor._field_value_dict(
        campo, {campo: valor, "_field_sources": {campo: fonte}}
    )
    assert registro["name"] == campo
    assert registro["value"] == valor
    assert registro["unit"] == unidade
    assert registro["provenance"]["source"] == canonica
    assert registro["provenance"]["cached"] is cache
    assert registro["provenance"]["manual"] is manual
    if manual:
        assert "manual_fallback" in registro["provenance"]["warnings"]


def test_origem_agregada_so_e_exposta_com_qualificador_de_inferencia(monkeypatch):
    motor = _engine(monkeypatch, info={})
    registro = motor._field_value_dict(
        "pl", {"pl": 12.0, "fonte_fundamentos": "CVM+cache"}
    )
    assert registro["value"] == 12.0
    assert "source_inferred_from_aggregate_flag" in registro["provenance"]["warnings"]


def test_ausencia_nao_vira_zero_e_tem_aviso_de_parcialidade(monkeypatch):
    motor = _engine(monkeypatch, info={})
    registro = motor._field_value_dict(
        "pl",
        {
            "pl": None,
            "_field_sources": {"pl": "cache"},
            "dados_parciais": True,
            "campos_faltantes": ["pl"],
        },
    )
    assert registro["value"] is None
    assert {"missing_value", "partial_data"}.issubset(
        registro["provenance"]["warnings"]
    )


@pytest.mark.parametrize(
    "campo,recalculado,avisa",
    [
        ("pl", True, True),
        ("pl", False, False),
        ("pvp", True, True),
        ("pvp", False, True),
    ],
)
def test_aviso_da_base_acionaria_distingue_media_divulgada_de_acoes_finais(
    monkeypatch, campo, recalculado, avisa
):
    from market_engine import AVISO_ACOES_FIM_DO_PERIODO
    from sentinela.data.acoes_cvm import NOTA_RECALCULADO

    motor = _engine(monkeypatch, info={})
    dados = {
        campo: 10.0,
        "_field_sources": {campo: "CVM"},
        "acoes_cvm": {"acoes": 1000.0},
        "lpa_cvm": {"notas": [NOTA_RECALCULADO] if recalculado else []},
    }
    registro = motor._field_value_dict(campo, dados)
    assert (AVISO_ACOES_FIM_DO_PERIODO in registro["provenance"]["warnings"]) is avisa


def test_correcao_do_indice_nao_perde_qualificador_na_proveniencia(monkeypatch):
    from market_engine import AVISO_CODIGO_DA_TABELA

    motor = _engine(monkeypatch, info={})
    registro = motor._field_value_dict(
        "pl",
        {
            "pl": 10.0,
            "_field_sources": {"pl": "CVM"},
            "referencia_oficial": {
                "correcao": {"regra": "identidade sintética para contrato"}
            },
        },
    )
    assert AVISO_CODIGO_DA_TABELA in registro["provenance"]["warnings"]


def test_preco_legado_preserva_o_provedor_explicitamente_declarado(monkeypatch):
    motor = _engine(monkeypatch, info={})
    registro = motor._field_value_dict(
        "preco_atual", {"preco_atual": 20.0, "fonte_preco": "yfinance"}
    )
    assert registro["value"] == 20.0
    assert registro["unit"] == "BRL"
    assert registro["provenance"]["source"] == "yfinance"


def test_sem_origem_informada_o_registro_nao_inventa_provedor(monkeypatch):
    motor = _engine(monkeypatch, info={})
    registro = motor._field_value_dict("pl", {"pl": 12.0})
    assert registro["value"] == 12.0
    assert registro["provenance"]["source"] == "unknown"
    assert registro["provenance"]["cached"] is False
    assert registro["provenance"]["manual"] is False
