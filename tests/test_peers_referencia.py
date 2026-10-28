"""Contrato F2C-7: identidade e setor oficiais, sem inferência de ticker."""

from unittest.mock import Mock

import pytest

from peers_engine import PeersEngine
from sentinela.data.referencia.registro import Indice, Registro


def indice_teste():
    registros = {}
    for ticker, classe, especie, setor in [
        ("TSTA3", "STOCK", "ON", "Setor oficial"),
        ("TSTB3", "STOCK", "ON", "Setor oficial"),
        ("TSTC3", "STOCK", "ON", "Setor oficial"),
        ("TSTD4", "STOCK", "PN", "Setor oficial"),
        ("TSTE11", "FII", None, "Setor oficial"),
        ("TSTF3", "STOCK", "ON", "Outro"),
    ]:
        registros[ticker] = Registro(
            ticker, classe, "teste", {}, especie=especie, setor=setor, cnpj=ticker
        )
    return Indice("2026-10-27", {}, registros)


def engine(dados=None, indice=None):
    market = Mock()
    market.referencia.indice.return_value = indice or indice_teste()
    market.buscar_dados_ticker.side_effect = lambda ticker: {
        "ticker": ticker,
        "preco_atual": 10,
        "pl": 4 if ticker == "TSTB3" else 8,
        "pvp": 1,
        "dy": 0.05,
        "modelo_bpp": "empresa",
        **(dados or {}),
    }
    return PeersEngine(market)


def test_grupo_oficial_substitui_mapa_manual_e_exemplo_independente():
    resultado = engine().comparar("TSTA3")
    assert sorted(resultado["Peers_Utilizados"]) == ["TSTB3", "TSTC3"]
    assert resultado["PL_Media_Peers"] == 6  # (4 + 8) / 2
    assert resultado["Setor"] == "Setor oficial"


def test_setor_passado_nao_sobrepoe_identidade_oficial():
    assert engine().comparar("TSTA3", "Outro")["PL_Media_Peers"] == 6


@pytest.mark.parametrize("ticker", ["VIIA3", "INEX3", "TSTE11"])
def test_identidade_ausente_ou_classe_inaplicavel_abstem(ticker):
    assert "erro" in engine().comparar(ticker)


def test_indice_indisponivel_nao_volta_a_lista_manual():
    e = engine()
    e.market.referencia.indice.return_value = None
    assert "erro" in e.comparar("PETR4")


def test_modelo_divergente_nao_e_comparavel():
    e = engine()
    e.market.buscar_dados_ticker.side_effect = lambda t: {
        "ticker": t,
        "preco_atual": 10,
        "pl": 4,
        "modelo_bpp": "empresa" if t == "TSTA3" else "banco",
    }
    resultado = e.comparar("TSTA3")
    assert resultado["Peers_Utilizados"] == []
    assert "modelo" in resultado["erro"]


@pytest.mark.parametrize("pl", [-1, 0, float("nan"), float("inf"), None, True])
def test_pl_inadequado_deixa_comparacao_indisponivel_com_motivo(pl):
    resultado = engine({"pl": pl}).comparar("TSTA3")
    assert resultado["PL_Media_Peers"] is None
    assert resultado["Motivo_PL"]


def test_cobertura_curta_e_declarada():
    e = engine()
    e.market.buscar_dados_ticker.side_effect = lambda t: (
        {
            "ticker": t,
            "preco_atual": 10,
            "pl": 4,
            "modelo_bpp": "empresa",
        }
        if t in {"TSTA3", "TSTB3"}
        else None
    )
    resultado = e.comparar("TSTA3")
    assert resultado["Cobertura"] == {"esperados": 2, "utilizados": 1}
    assert resultado["Avisos"]


def test_cli_nao_inventa_alias_para_codigo_antigo():
    from auditar_recomendacoes import tickers_oficiais

    assert tickers_oficiais(indice_teste(), ["VIIA3", "TSTA3", "TSTA3"]) == ["TSTA3"]
    assert tickers_oficiais(None, ["TSTA3"]) == []


def test_sem_fonte_preserva_contrato_de_ausencia_para_ui():
    from types import SimpleNamespace

    resultado = PeersEngine(SimpleNamespace()).comparar("TSTA3")
    for campo in ("Setor", "PL_Media_Peers", "PVP_Media_Peers", "DY_Media_Peers"):
        assert resultado[campo] is None
    assert resultado["Peers_Utilizados"] == []
    assert resultado["erro"]


@pytest.mark.parametrize("classe,especie", [("STOCK", "ON"), ("UNIT", None)])
def test_acao_e_unit_com_modelo_demonstrado_sao_comparaveis(classe, especie):
    from dataclasses import replace

    indice = indice_teste()
    indice.registros = {
        t: replace(r, classe=classe, especie=especie)
        for t, r in indice.registros.items()
        if t in {"TSTA3", "TSTB3", "TSTC3"}
    }
    resultado = engine(indice=indice).comparar(" tsta3 ")
    assert resultado["PL_Media_Peers"] == 6
    assert resultado["PVP_Media_Peers"] == 1
    assert resultado["DY_Media_Peers"] == 0.05
    assert resultado["Motivo_PL"] is None
    assert resultado["Avisos"] == []
    assert resultado["Cobertura"] == {"esperados": 2, "utilizados": 2}


@pytest.mark.parametrize("campo,valor", [("setor", None), ("classe", "ETF")])
def test_dado_de_identidade_incompleto_nao_e_grupo(campo, valor):
    from dataclasses import replace

    indice = indice_teste()
    indice.registros["TSTA3"] = replace(indice.registros["TSTA3"], **{campo: valor})
    e = engine(indice=indice)
    assert "erro" in e.comparar("TSTA3")
    e.market.buscar_dados_ticker.assert_not_called()


def test_sem_par_nao_dispara_coleta_de_fundamentos():
    indice = indice_teste()
    indice.registros = {"TSTA3": indice.registros["TSTA3"]}
    e = engine(indice=indice)
    assert "erro" in e.comparar("TSTA3")
    e.market.buscar_dados_ticker.assert_not_called()


@pytest.mark.parametrize("modelo", [None, "", "inexistente"])
def test_modelo_alvo_ausente_nao_inventa_empresa(modelo):
    assert "modelo" in engine({"modelo_bpp": modelo}).comparar("TSTA3")["erro"]


@pytest.mark.parametrize("modelo", ["banco", "seguradora"])
def test_modelos_validos_separados(modelo):
    assert engine({"modelo_bpp": modelo}).comparar("TSTA3")["PL_Media_Peers"] == 6


@pytest.mark.parametrize(
    "alteracao",
    [
        {"preco_atual": 0},
        {"preco_atual": -1},
        {"preco_atual": float("nan")},
        {"preco_atual": True},
        {"ticker": "ERRD3"},
        {"pl": None, "pvp": None, "roe": None},
    ],
)
def test_pares_sem_identidade_preco_ou_dados_nao_contam(alteracao):
    e = engine()
    e.market.buscar_dados_ticker.side_effect = lambda t: {
        "ticker": t,
        "preco_atual": 10,
        "pl": 4,
        "modelo_bpp": "empresa",
        **(alteracao if t != "TSTA3" else {}),
    }
    resultado = e.comparar("TSTA3")
    assert resultado["Peers_Utilizados"] == []
    assert resultado["Cobertura"] == {"esperados": 2, "utilizados": 0}
    assert resultado["Avisos"]


@pytest.mark.parametrize(
    "campo,chave", [("pvp", "PVP_Media_Peers"), ("dy", "DY_Media_Peers")]
)
@pytest.mark.parametrize("valor", [None, float("nan"), float("inf"), True])
def test_media_incompleta_nao_vira_zero(campo, chave, valor):
    assert engine({campo: valor}).comparar("TSTA3")[chave] is None


def test_outro_papel_do_mesmo_emissor_nao_e_par_independente():
    from dataclasses import replace

    indice = indice_teste()
    indice.registros["TSTB3"] = replace(indice.registros["TSTB3"], cnpj="TSTA3")
    resultado = engine(indice=indice).comparar("TSTA3")
    assert resultado["Peers_Utilizados"] == ["TSTC3"]
    assert resultado["Avisos"]
