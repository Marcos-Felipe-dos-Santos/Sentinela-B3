"""Recortes literais das fontes públicas, hashes integrais e datas no envelope."""

import json
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path

import pytest

from sentinela.data.providers import macro

FIXTURE = json.loads(
    (Path(__file__).parent / "fixtures/contratos/macro_2026.json").read_text()
)
FIXTURE = FIXTURE["fontes"]
AS_OF = datetime(2026, 10, 20, 16, tzinfo=UTC)


def _provider(monkeypatch):
    provider = macro.MacroProvider()

    def baixar(url, instante):
        if "fer_nacionais" in url:
            nome = "anbima2026"
        elif "calendario/9256" in url:
            nome = "ibge_calendario"
        elif "sitebcb/calendario" in url:
            nome = "bcb_calendar_focus"
        elif "ExpectativasMercadoAnuais" in url:
            assert "2026-10-16" in url
            nome = "focus_pib"
        else:
            assert "/1737/" in url and "/63/" in url and "202501-202609" in url
            nome = "ipca_mensal"
        d = FIXTURE[nome]
        m = d.get("metadados", {})
        return macro.SnapshotMacro(
            d["conteudo"],
            url,
            m.get("coleta", AS_OF.isoformat()),
            m.get("sha256", "a" * 64),
        )

    monkeypatch.setattr(provider, "baixar", baixar)
    return provider


def test_calendario_anbima_real_contem_feriados_moveis_e_nacionais(monkeypatch):
    calendario = _provider(monkeypatch).calendario(2026, AS_OF)
    assert len(calendario.feriados) == 13
    assert date(2026, 10, 12) in calendario.feriados
    assert calendario.dias_uteis(date(2026, 10, 8), date(2026, 10, 20)) == 7
    assert (
        calendario.proveniencia["hash_sha256"]
        == FIXTURE["anbima2026"]["metadados"]["sha256"]
    )


def test_ipca_sidra_real_composto_e_publicacoes(monkeypatch):
    resultado = _provider(monkeypatch).inflacao(
        date(2025, 1, 1), date(2025, 12, 31), AS_OF
    )
    fatores = [
        1 + Decimal(l["V"]) / 100
        for l in json.loads(FIXTURE["ipca_mensal"]["conteudo"])[1:]
        if l["D3C"].startswith("2025")
    ]
    esperado = Decimal(1)
    for fator in fatores:
        esperado *= fator
    assert resultado["valor"] == pytest.approx(float(esperado - 1))
    assert resultado["ultimo_mes_publicado"] == "202609"
    assert resultado["publicacao"] == "2026-01-09"
    assert resultado["proveniencia"]["fonte"].startswith(
        "https://apisidra.ibge.gov.br/"
    )


def test_focus_pib_real_base_zero_2030(monkeypatch):
    resultado = _provider(monkeypatch).pib(AS_OF)
    assert resultado["valor"] == 0.02 and resultado["ano"] == 2030
    assert resultado["publicacao"] == "2026-10-19T11:30:00+00:00"
    assert resultado["proxima_publicacao"] == "2026-10-26T11:30:00+00:00"
    assert resultado["baseCalculo"] == 0 and resultado["estatistica"] == "Mediana"
    assert (
        resultado["calendario"]["hash_sha256"]
        == FIXTURE["bcb_calendar_focus"]["metadados"]["sha256"]
    )
