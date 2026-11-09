"""BUG-2C-63: o motor deve ler a causa que a cascata realmente transporta."""

from apoio_escopo import de_empresa

from market_engine import MarketEngine
from tests.regressao.test_bug_2c_62_qualidade_produtor import AS_OF, fonte_anual
from tests.test_cvm_series import _Hoje
from valuation_engine import ValuationEngine


def test_motivo_cvm_pela_saida_real_da_cascata(tmp_path, monkeypatch):
    p = fonte_anual(tmp_path, monkeypatch)
    dados = de_empresa(
        {
            "ticker": "TST3",
            "preco_atual": 100,
            "cd_cvm": 9999,
            "especie": "ON",
            "pl": 10,
            "pvp": 2,
            "roe": 0.1,
            "dy": 0.05,
        }
    )
    monkeypatch.setattr("market_engine.date", _Hoje)
    motor = MarketEngine.__new__(MarketEngine)
    motor.cvm = p
    assert motor._buscar_cvm("TST3", dados)
    assert "alavancagem_motivos" not in dados
    motivo = dados["alavancagem_cvm"]["motivos"]["divida_liq_ebitda"]
    assert motivo
    r = ValuationEngine().processar(dados, as_of=AS_OF)
    assert motivo in r["aviso_alavancagem"]
