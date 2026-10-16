"""Classe do ativo por dado oficial, nunca pelo sufixo (F2A-20, armadilha 14, E-9).

Ordem de consulta: `dados['classe_ativo']` (da cascata) → índice local (sem rede) →
listas conhecidas (`FIIS_CONHECIDOS`, `UNITS_CONHECIDAS`) → sem classe definida. Índice falso
gravado em `tmp_path`; os testes nunca leem o índice da máquina.
"""

import os
from pathlib import Path

import pytest

from sentinela.data.referencia import carga, salvar_indice
from sentinela.data.referencia.registro import Indice, Registro
from sentinela.domain.enums import AssetType
from sentinela.services.asset_classifier import AssetClassifier

_FONTE = {"arquivo": "x", "data": "2026-10-08"}
_XFAIL = pytest.mark.xfail(
    strict=True, reason="F2A-20: o classificador ainda deduz a classe do sufixo"
)


def _gravar_indice(pasta: Path, **classes: str) -> Path:
    indice = Indice(
        gerado_em="2026-10-08",
        fontes={},
        registros={
            t: Registro(ticker=t, classe=c, regra="teste", fonte=_FONTE)
            for t, c in classes.items()
        },
    )
    salvar_indice(indice, pasta / "referencia")
    return pasta


def _classificador(pasta: Path | None = None) -> AssetClassifier:
    return AssetClassifier(
        fiis_conhecidos=set(), units_conhecidas=set(), pasta_dados=pasta
    )


# ── aceite ───────────────────────────────────────────────────────────────────


def test_etf_nao_e_fii(tmp_path):
    classificador = _classificador(tmp_path)
    assert classificador.classify("BOVA11", {"classe_ativo": "ETF"}) == AssetType.ETF
    assert classificador.is_fii("BOVA11", {"classe_ativo": "ETF"}) is False
    _gravar_indice(tmp_path, IVVB11="ETF")
    assert _classificador(tmp_path).is_fii("IVVB11") is False


@pytest.mark.parametrize("ticker", ["BRBI11", "IGTI11"])
def test_unit_fora_da_lista_e_unit(tmp_path, ticker):
    assert _classificador(tmp_path).classify(ticker, {"classe_ativo": "UNIT"}) == (
        AssetType.UNIT
    )
    _gravar_indice(tmp_path, **{ticker: "UNIT"})
    assert _classificador(tmp_path).classify(ticker) == AssetType.UNIT
    assert _classificador(tmp_path).is_fii(ticker) is False


def test_fii_fora_da_lista_e_fii_pelo_indice(tmp_path):
    _gravar_indice(tmp_path, TSTF11="FII", TSTF3="FII")
    classificador = _classificador(tmp_path)
    assert classificador.classify("TSTF11") == AssetType.FII
    assert classificador.classify("tstf3.sa") == AssetType.FII


def test_sufixo_sozinho_nao_define_classe(tmp_path):
    classificador = _classificador(tmp_path)
    assert classificador.is_fii("ABCD11") is False
    assert classificador.classify("ABCD11") == AssetType.UNKNOWN
    assert classificador.is_fii("ABCD3", {"quote_type": "MUTUALFUND"}) is False


def test_testes_nao_leem_o_indice_local():
    pasta = carga.pasta_de_dados()
    raiz = Path(__file__).resolve().parents[1]
    assert os.environ.get(carga.VARIAVEL_PASTA_DE_DADOS)
    assert pasta.resolve() != (raiz / "data").resolve()
    assert not (pasta / "referencia" / "indice.json").exists()
    assert AssetClassifier().classify("ABCD11") == AssetType.UNKNOWN


# ── ordem de consulta e casos de borda ───────────────────────────────────────


def test_classe_dos_dados_vale_antes_do_indice_e_das_listas(tmp_path):
    _gravar_indice(tmp_path, HGLG11="FII")
    classificador = AssetClassifier(
        fiis_conhecidos={"HGLG11"}, units_conhecidas=set(), pasta_dados=tmp_path
    )
    assert classificador.classify("HGLG11", {"classe_ativo": "BDR"}) == AssetType.BDR


def test_indice_vale_antes_das_listas(tmp_path):
    _gravar_indice(tmp_path, SANB11="FII")
    classificador = AssetClassifier(
        fiis_conhecidos=set(), units_conhecidas={"SANB11"}, pasta_dados=tmp_path
    )
    assert classificador.classify("SANB11") == AssetType.FII


def test_listas_valem_sem_indice(tmp_path):
    classificador = AssetClassifier(
        fiis_conhecidos={"HGLG11"}, units_conhecidas={"SANB11"}, pasta_dados=tmp_path
    )
    assert classificador.classify("HGLG11") == AssetType.FII
    assert classificador.classify("SANB11") == AssetType.UNIT


def test_listas_valem_para_ticker_fora_do_indice(tmp_path):
    _gravar_indice(tmp_path, PETR4="STOCK")
    classificador = AssetClassifier(
        fiis_conhecidos={"HGLG11"}, units_conhecidas=set(), pasta_dados=tmp_path
    )
    assert classificador.classify("HGLG11") == AssetType.FII


def test_classe_invalida_nos_dados_e_ignorada(tmp_path):
    _gravar_indice(tmp_path, TSTF11="FII")
    classificador = _classificador(tmp_path)
    assert classificador.classify("TSTF11", {"classe_ativo": "COTA"}) == AssetType.FII
    assert classificador.classify("TSTF11", {"classe_ativo": None}) == AssetType.FII


def test_acao_fora_do_indice_e_das_listas_continua_acao(tmp_path):
    assert _classificador(tmp_path).classify("PETR4") == AssetType.STOCK


def test_indice_e_lido_uma_vez(tmp_path, monkeypatch):
    _gravar_indice(tmp_path, TSTF11="FII")
    classificador = _classificador(tmp_path)
    assert classificador.classify("TSTF11") == AssetType.FII
    (tmp_path / "referencia" / "indice.json").unlink()
    assert classificador.classify("TSTF11") == AssetType.FII


def test_indice_ilegivel_cai_nas_listas(tmp_path, caplog):
    arquivo = tmp_path / "referencia" / "indice.json"
    arquivo.parent.mkdir(parents=True)
    arquivo.write_text("{ nao e json", encoding="utf-8")
    classificador = AssetClassifier(
        fiis_conhecidos={"HGLG11"}, units_conhecidas=set(), pasta_dados=tmp_path
    )
    with caplog.at_level("WARNING"):
        assert classificador.classify("HGLG11") == AssetType.FII
    assert "ilegível" in caplog.text


def test_pasta_de_dados_vem_da_variavel_de_ambiente(tmp_path, monkeypatch):
    monkeypatch.setenv(carga.VARIAVEL_PASTA_DE_DADOS, str(tmp_path))
    assert carga.pasta_de_dados() == tmp_path
    _gravar_indice(tmp_path, TSTF11="FII")
    assert AssetClassifier(fiis_conhecidos=set()).classify("TSTF11") == AssetType.FII


def test_pasta_de_dados_padrao_e_data(monkeypatch):
    monkeypatch.delenv(carga.VARIAVEL_PASTA_DE_DADOS)
    assert carga.pasta_de_dados() == Path("data")


def test_carga_da_cascata_usa_a_mesma_pasta(tmp_path, monkeypatch):
    monkeypatch.setenv(carga.VARIAVEL_PASTA_DE_DADOS, str(tmp_path))
    pastas = []
    monkeypatch.setattr(
        carga, "obter_indice", lambda agora, pasta: pastas.append(pasta) or None
    )
    from datetime import UTC, datetime

    carga.ReferenciaOficial().indice(datetime(2026, 10, 8, tzinfo=UTC))
    assert pastas == [tmp_path]
