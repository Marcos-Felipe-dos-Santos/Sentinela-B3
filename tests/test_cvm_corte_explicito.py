"""F3-P13: um só corte local para a seleção anual, snapshot e TTM.

Arquivos sintéticos usam o layout CVM já documentado nos testes de produtor.
O TTM esperado é 15 - 25 + 30 = 20, sem prova de perímetro injetada.
"""

import io
import zipfile
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import Mock

import pandas as pd
import pytest
from apoio_escopo import de_empresa

from market_engine import MarketEngine
from tests.regressao.test_bug_2c_61_ttm_produtor import arquivo
from tests.regressao.test_bug_2c_62_qualidade_produtor import fonte_anual
from tests.test_cvm_series import _Hoje
from valuation_engine import ValuationEngine


def test_dfp_itr_cascata_motor_compartilham_o_corte(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    p = fonte_anual(tmp_path, monkeypatch)
    itr = {
        ano: arquivo(
            tmp_path,
            "itr",
            ano,
            [(f"{ano}-03-31", a), (f"{ano}-06-30", b), (f"{ano}-09-30", c)],
        )
        for ano, a, b, c in [(2024, 10, 25, 45), (2025, 12, 30, 50)]
    }

    def baixar(ano: int) -> Path:
        if ano not in itr:
            raise OSError("ITR ausente no cenário")
        return itr[ano]

    monkeypatch.setattr(p, "baixar_itr", baixar)
    monkeypatch.setattr("market_engine.date", _Hoje)
    m = MarketEngine.__new__(MarketEngine)
    m.cvm = p
    m._aplicar_referencia = lambda t, d: d.update(
        cd_cvm=9999, especie="ON", classe_ativo="STOCK"
    )
    m._buscar_yfinance = lambda t, d: d.update(preco_atual=100, fonte_preco="yfinance")
    for nome in (
        "_buscar_brapi",
        "_buscar_ifdata",
        "_buscar_cvm_fii",
        "_buscar_rendimento_fii",
        "_buscar_proventos_b3",
        "_buscar_liquidez",
        "_buscar_taxa_real",
        "_contexto_janelas",
        "_aplicar_cache_fundamentos",
        "_salvar_cache_se_valido",
    ):
        monkeypatch.setattr(m, nome, Mock())
    corte = datetime(2025, 7, 1, 2, tzinfo=UTC)  # 30/06 em São Paulo
    dados = m.buscar_dados_ticker_em("TSTA3", corte)
    assert dados["serie_cvm"]["exercicios"][-1]["exercicio"] == 2024
    assert dados["modelo_bpp_proveniencia"]["periodo_referencia"] == "2024-12-31"
    assert dados["ttm_cvm"]["fim"] == "2025-06-30"
    assert dados["ttm_cvm"]["valores"]["lucro_controladores"] == 20
    resultado = ValuationEngine().processar(dados, as_of=corte)
    assert resultado["qualidade"]["exercicios"][-1]["fim"] == "2024-12-31"


@pytest.mark.parametrize("hora,minuto,esperado", [(2, 59, 2023), (3, 0, 2024)])
def test_exercicio_nao_civil_entra_no_dia_local_do_encerramento(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    hora: int,
    minuto: int,
    esperado: int,
) -> None:
    p = fonte_anual(tmp_path, monkeypatch)
    pasta = tmp_path / "nao_civil"
    pasta.mkdir()
    bruto = arquivo(pasta, "dfp", 2024, [("2024-02-29", 77)])
    destino = tmp_path / "nao_civil_2024.zip"
    with zipfile.ZipFile(bruto) as entrada, zipfile.ZipFile(destino, "w") as saida:
        for nome in entrada.namelist():
            frame = pd.read_csv(
                io.BytesIO(entrada.read(nome)), sep=";", encoding="latin-1"
            )
            frame["DT_INI_EXERC"] = "2023-03-01"
            saida.writestr(nome, frame.to_csv(sep=";", index=False).encode("latin-1"))
    baixar = p.baixar_dfp
    monkeypatch.setattr(
        p, "baixar_dfp", lambda ano: destino if ano == 2024 else baixar(ano)
    )
    monkeypatch.setattr("market_engine.date", _Hoje)
    m = MarketEngine.__new__(MarketEngine)
    m.cvm = p
    dados = de_empresa(
        {"ticker": "TSTA3", "cd_cvm": 9999, "preco_atual": 100, "especie": "ON"}
    )
    assert m._buscar_cvm(
        "TSTA3", dados, as_of=datetime(2024, 2, 29, hora, minuto, tzinfo=UTC)
    )
    assert dados["serie_cvm"]["exercicios"][-1]["exercicio"] == esperado
    assert dados["modelo_bpp_proveniencia"]["periodo_referencia"] == (
        "2023-12-31" if esperado == 2023 else "2024-02-29"
    )
