"""D16/D17: reprocessar fatos não permite transportar evidência futura."""

from datetime import UTC, datetime

import pytest
from apoio_escopo import de_empresa
from apoio_gordon import enriquecer_gordon

from valuation_engine import ValuationEngine


@pytest.mark.parametrize("qual", ["DFP", "composicao"])
def test_reprocessamento_nao_aceita_evidencia_posterior_ao_asof(qual, monkeypatch):
    monkeypatch.setattr("valuation_engine.get_selic_atual", lambda: 0.145)
    d = enriquecer_gordon(
        {
            "ticker": "TSTA3",
            "preco_atual": 100.0,
            "pl": 10.0,
            "pvp": 1.0,
            "roe": 0.12,
            "dy": 0.06,
        }
    )
    d["gordon_cvm"]["proveniencia"] = {
        "periodo_referencia": "2025-12-31",
        "data_entrega": "2026-02-12",
        "data_coleta": "2026-10-13T18:00:00+00:00"
        if qual == "DFP"
        else "2026-02-20T18:00:00+00:00",
    }
    d["base_acionaria_gordon"] = {
        "proveniencia": {
            "periodo_referencia": "2026-06-30"
            if qual == "composicao"
            else "2025-12-31",
            "data_entrega": "2026-08-10" if qual == "composicao" else "2026-02-12",
            "data_coleta": "2026-10-13T18:00:00+00:00"
            if qual == "composicao"
            else "2026-02-20T18:00:00+00:00",
        }
    }
    r = ValuationEngine().processar(
        de_empresa(d), as_of=datetime(2026, 3, 1, 18, tzinfo=UTC)
    )
    assert "Gordon" not in r["metodos_usados"]
    assert "posterior" in d["gordon_diagnostico"]


@pytest.mark.parametrize(
    "instante_macro", ["2026-10-20T18:00:00+00:00", "2026-02-20T18:00:00"]
)
def test_reprocessamento_recusa_contexto_macro_posterior_ou_sem_fuso(
    instante_macro, monkeypatch
):
    monkeypatch.setattr("valuation_engine.get_selic_atual", lambda: 0.145)
    d = enriquecer_gordon(
        {
            "ticker": "TSTA3",
            "preco_atual": 100.0,
            "pl": 10.0,
            "pvp": 1.0,
            "roe": 0.12,
            "dy": 0.06,
        }
    )
    d["taxa_real"]["as_of"] = instante_macro
    r = ValuationEngine().processar(
        de_empresa(d), as_of=datetime(2026, 3, 1, 18, tzinfo=UTC)
    )
    assert "Gordon" not in r["metodos_usados"]
    assert d["gordon_diagnostico"] == (
        "contexto da taxa real posterior ao as_of"
        if instante_macro.endswith("+00:00")
        else "contexto da taxa real sem fuso horário"
    )
