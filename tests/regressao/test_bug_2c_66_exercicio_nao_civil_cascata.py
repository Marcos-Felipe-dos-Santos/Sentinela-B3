"""BUG-2C-66: seleção anual corrente deve usar o último exercício encerrado."""

import io
import os
import zipfile

import pandas as pd
from apoio_escopo import de_empresa

from market_engine import MarketEngine
from tests.regressao.test_bug_2c_61_ttm_produtor import arquivo
from tests.regressao.test_bug_2c_62_qualidade_produtor import AS_OF, fonte_anual
from tests.test_cvm_series import _Hoje
from valuation_engine import ValuationEngine


def test_ultimo_exercicio_nao_civil_chega_ao_motor(tmp_path, monkeypatch):
    p = fonte_anual(tmp_path, monkeypatch)
    origem = tmp_path / "nao_civil"
    origem.mkdir()
    bruto = arquivo(origem, "dfp", 2026, [("2026-02-28", 77)])
    destino = tmp_path / "dfp_2026.zip"
    with zipfile.ZipFile(bruto) as entrada, zipfile.ZipFile(destino, "w") as z:
        for nome in entrada.namelist():
            frame = pd.read_csv(
                io.BytesIO(entrada.read(nome)), sep=";", encoding="latin-1"
            )
            frame["DT_INI_EXERC"] = "2025-03-01"
            z.writestr(nome, frame.to_csv(sep=";", index=False).encode("latin-1"))
    os.utime(destino, (AS_OF.timestamp(), AS_OF.timestamp()))
    baixar = p.baixar_dfp
    monkeypatch.setattr(
        p, "baixar_dfp", lambda ano: destino if ano == 2026 else baixar(ano)
    )
    monkeypatch.setattr("market_engine.date", _Hoje)
    monkeypatch.setattr("cvm_provider.date", _Hoje)
    motor = MarketEngine.__new__(MarketEngine)
    motor.cvm = p
    dados = de_empresa(
        {"ticker": "TST3", "cd_cvm": 9999, "preco_atual": 100, "especie": "ON"}
    )
    assert p.exercicio_anual_mais_recente(9999, _Hoje.today()) == 2026
    assert motor._buscar_cvm("TST3", dados)
    assert dados["lucro_liquido"] == 77
    assert dados["modelo_bpp_proveniencia"]["periodo_referencia"] == "2026-02-28"
    r = ValuationEngine().processar(dados, as_of=AS_OF)
    assert r is not None
    assert r["qualidade"]["exercicios"][-1]["fim"] == "2026-02-28"
