"""BUG-2C-62: cinco DFP contíguas devem demonstrar qualidade comparável.

Decisão do Marcos09/11: prova emitida pelo produtor, com reserva D20 válida.
"""

import io
import os
import zipfile
from datetime import UTC, datetime

import pandas as pd
import pytest
import requests
from apoio_escopo import de_empresa

from cvm_provider import CVMProvider
from market_engine import MarketEngine
from tests.regressao.test_bug_2c_61_ttm_produtor import CNPJ, arquivo
from tests.test_cvm_series import _Hoje
from valuation_engine import ValuationEngine

AS_OF = datetime(2026, 10, 13, 12, tzinfo=UTC)


def fonte_anual(tmp_path, monkeypatch):
    brutos = tmp_path / "brutos"
    brutos.mkdir()
    caminhos = {}
    for ano, lucro in zip(range(2021, 2026), (10, 12, -2, 15, 15), strict=True):
        bruto = arquivo(brutos, "dfp", ano, [(f"{ano}-12-31", lucro)])
        destino = tmp_path / f"dfp_{ano}.zip"
        with zipfile.ZipFile(bruto) as fonte, zipfile.ZipFile(destino, "w") as z:
            for nome in fonte.namelist():
                conteudo = fonte.read(nome)
                if "BPP_con" in nome:
                    bpp = pd.read_csv(io.BytesIO(conteudo), sep=";", encoding="latin-1")
                    abertura = bpp.copy()
                    abertura["ORDEM_EXERC"] = "PENÚLTIMO"
                    abertura["DT_FIM_EXERC"] = f"{ano - 1}-12-31"
                    conteudo = (
                        pd.concat([bpp, abertura])
                        .to_csv(sep=";", index=False)
                        .encode("latin-1")
                    )
                z.writestr(nome, conteudo)
            z.writestr(
                f"dfp_cia_aberta_{ano}.csv",
                f"CNPJ_CIA;DT_REFER;VERSAO;DT_RECEB\n{CNPJ};{ano}-12-31;1;{ano + 1}-03-01\n",
            )
        instante = datetime(2026, 10, 1, tzinfo=UTC).timestamp()
        os.utime(destino, (instante, instante))
        caminhos[ano] = destino
    p = CVMProvider(tmp_path / "cache")

    def baixar(ano):
        if ano in caminhos:
            return caminhos[ano]
        resposta = requests.Response()
        resposta.status_code = 404
        raise requests.HTTPError("arquivo não publicado", response=resposta)

    monkeypatch.setattr(p, "baixar_dfp", baixar)
    monkeypatch.setattr(p, "baixar_itr", baixar)
    return p


def test_cinco_dfps_produtor_market_motor_sem_prova_artificial(tmp_path, monkeypatch):
    p = fonte_anual(tmp_path, monkeypatch)
    dados = de_empresa(
        {
            "ticker": "TST3",
            "preco_atual": 100,
            "especie": "ON",
            "pl": 10,
            "pvp": 2,
            "roe": 0.1,
            "dy": 0.05,
        }
    )
    monkeypatch.setattr("market_engine.date", _Hoje)
    MarketEngine.__new__(MarketEngine)._serie_cvm("TST3", dados, p, 9999, "empresa")
    resultado = ValuationEngine().processar(dados, as_of=AS_OF)
    q = resultado["qualidade"]
    assert q["comparavel"] is True
    assert q["roe"]["media"] == pytest.approx(0.1)
    assert q["roe"]["observados"] == 5
    for e in dados["serie_cvm"]["exercicios"]:
        assert "controladores" in e["perimetro"]
        assert e["dt_refer"] in e["evidencia_comparabilidade"]
        assert (
            e["aviso_comparabilidade"]
            == "reorganização societária no período não é detectada"
        )
    assert "reorganização societária no período não é detectada" in q["avisos"]


def test_lacuna_anual_nao_certifica_comparabilidade(tmp_path, monkeypatch):
    p = fonte_anual(tmp_path, monkeypatch)
    baixar = p.baixar_dfp

    def sem_2023(ano):
        if ano == 2023:
            raise OSError("DFP ausente")
        return baixar(ano)

    monkeypatch.setattr(p, "baixar_dfp", sem_2023)
    dados = de_empresa({"ticker": "TST3", "preco_atual": 100, "especie": "ON"})
    monkeypatch.setattr("market_engine.date", _Hoje)
    MarketEngine.__new__(MarketEngine)._serie_cvm("TST3", dados, p, 9999, "empresa")
    q = ValuationEngine().processar(dados, as_of=AS_OF)["qualidade"]
    assert q["comparavel"] is False
    assert q["roe"]["media"] is None
    assert q["roe"]["observados"] == 4
