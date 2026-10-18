"""BUG-2A-16: ZIP vazio do COTAHIST levanta `IndexError` fora das exceções tratadas.

`b3_cotahist.ler_zip` faz `namelist()[0]`; num ZIP sem arquivo, o `IndexError` escapa do
`except` de `HistoricoRecente.coletar`, e a coleta inteira falha em vez de marcar só aquele
mês como ausente. Origem: auditoria externa da Fase 2A (Gemini 2ª passada e Codex,
15/10/2026).
"""

import zipfile
from datetime import UTC, datetime

import pytest

from sentinela.data.providers import b3_cotahist


@pytest.mark.xfail(
    strict=True,
    reason=(
        "BUG-2A-16 · ZIP vazio do COTAHIST levanta IndexError fora das exceções tratadas "
        "· corrige: F2B-40"
    ),
)
def test_zip_vazio_vira_mes_ausente(tmp_path, monkeypatch):
    vazio = tmp_path / "COTAHIST_M092026.ZIP"
    with zipfile.ZipFile(vazio, "w"):
        pass
    monkeypatch.setattr(b3_cotahist, "baixar_mes", lambda ano, mes, agora, pasta: vazio)
    historico = b3_cotahist.HistoricoRecente(cache_dir=tmp_path / "cache", meses=1)
    coleta = historico.coletar(datetime(2026, 10, 15, 12, tzinfo=UTC))
    assert coleta.cotacoes == []
    assert coleta.meses_ausentes == ("10/2026",)
