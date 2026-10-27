"""BUG-2C-07: a seleção por ano civil omite DFP encerrada em fevereiro.

CVM publica DT_INI/DT_FIM/DT_REFER; encerramento anual março-fevereiro de2026
é anterior a outubro2026. Não pode ser adiado automaticamente para janeiro2027.
"""

from datetime import date

from cvm_provider import CVMProvider
from sentinela.data import series_cvm
from tests.test_cvm_series import CD_CVM, _Hoje, _ind, _zip, com_perimetro_sintetico
from tests.test_market_engine import _engine


def test_ttm_inclui_dfp_encerrada_em_fevereiro_do_mesmo_ano(tmp_path, monkeypatch):
    dt = "2026-02-28"
    dre = [
        (
            dt,
            "1",
            "ÚLTIMO",
            "2025-03-01",
            dt,
            "3.11",
            "Lucro/Prejuízo Consolidado do Período",
            70,
        )
    ]
    arquivo_dfp = _zip(tmp_path / "dfp_2026.zip", "dfp", 2026, dre, [])
    trimestres = [("2025-05-31", 10), ("2025-08-31", 25), ("2025-11-30", 45)]
    dre_itr = [
        (
            d,
            "1",
            "ÚLTIMO",
            "2025-03-01",
            d,
            "3.11",
            "Lucro/Prejuízo Consolidado do Período",
            v,
        )
        for d, v in trimestres
    ]
    arquivo_itr = _zip(tmp_path / "itr_2025.zip", "itr", 2025, dre_itr, [])
    provider = CVMProvider(cache_dir=str(tmp_path / "cache"))

    def baixar(prefixo, ano):
        if (prefixo, ano) == ("DFP", 2026):
            return arquivo_dfp
        if (prefixo, ano) == ("ITR", 2025):
            return arquivo_itr
        raise FileNotFoundError(f"{prefixo}{ano}")

    monkeypatch.setattr(provider, "baixar_dfp", lambda ano: baixar("DFP", ano))
    monkeypatch.setattr(provider, "baixar_itr", lambda ano: baixar("ITR", ano))
    instante = date(2026, 10, 26)
    ac = provider.acumulados_ttm(CD_CVM, instante)
    assert any(a.documento == "DFP" and a.dt_refer == dt for a in ac)
    ttm = series_cvm.ttm(com_perimetro_sintetico(ac), instante)
    assert ttm["valores"]["lucro_liquido"] == 70_000


class FonteNaoCivil:
    def exercicio_anual_mais_recente(self, codigo, referencia):
        return 2026

    def indicadores_da_serie(self, codigo, ano, modelo):
        assert ano == 2026
        return {2026: {**_ind(2026), "cvm_dt_refer": "2026-02-28"}}

    def acumulados_ttm(self, *args):
        return []


def test_serie_usa_exercicio_demonstrado_pela_fonte(monkeypatch):
    monkeypatch.setattr("market_engine.date", _Hoje)
    engine = _engine(monkeypatch, info={})
    dados = {}
    engine._serie_cvm("TSTA3", dados, FonteNaoCivil(), CD_CVM, "empresa")
    assert [e["exercicio"] for e in dados["serie_cvm"]["exercicios"]] == [2026]
