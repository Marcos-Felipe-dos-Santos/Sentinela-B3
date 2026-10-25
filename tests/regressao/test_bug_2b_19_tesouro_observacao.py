"""F2B-48: o instante explícito observa download e datas completas elegíveis."""

from datetime import UTC, date, datetime

import pytest

from sentinela.data.providers import tesouro as t
from tests.test_tesouro import CSV


def test_download_lido_no_mesmo_instante(tmp_path, monkeypatch):
    class Resposta:
        content = CSV.encode()

        def raise_for_status(self):
            pass

    monkeypatch.setattr(t.requests, "get", lambda *a, **k: Resposta())
    instante = datetime(2026, 10, 20, 18, tzinfo=UTC)
    snapshot = t.TesouroProvider(tmp_path).baixar(instante)
    assert len(t.ler_snapshot(snapshot, as_of=instante)) == 1
    assert snapshot.proveniencia.data_coleta == instante.isoformat(timespec="seconds")


@pytest.mark.parametrize("base", ["20/10/2026", "21/10/2026"])
def test_cumulativo_preserva_so_datas_elegiveis(base):
    texto = CSV + f"Tesouro IPCA+;15/05/2040;{base};7,00;7,12\n"
    titulos = t.ler_csv(texto, as_of=date(2026, 10, 20))
    assert len(titulos) == 1 and titulos[0].data_base == date(2026, 10, 15)
