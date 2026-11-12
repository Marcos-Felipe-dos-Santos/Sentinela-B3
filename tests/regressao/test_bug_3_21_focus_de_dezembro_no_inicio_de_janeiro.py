"""BUG-3-21: no começo de janeiro, a edição Focus de dezembro não é encontrada.

Auditoria externa do Gemini sobre 284165f..419f010, achado 4 (11/11/2026): o `pib` do
`MacroProvider` só lê a agenda do Focus do ano de D, e o `_pib_do_banco` só aceita edições
divulgadas no ano de D. Num D anterior ao primeiro Focus do ano (02/01/2026, com o primeiro
Focus de 2026 em 05/01), a edição devida é a de 29/12/2025, e a taxa se abstém com "edição
Focus devida ausente". Corrige: F3-A-F9.
"""

import json
import sqlite3
from contextlib import closing
from datetime import UTC, datetime

import pytest

from sentinela.data.providers import macro
from sentinela.data.store import migracoes

D = datetime(
    2026, 1, 2, 15, tzinfo=UTC
)  # meio-dia em São Paulo, antes do primeiro Focus
AGENDAS = {
    "2025": "2025-12-29T08:25:00-03:00",
    "2026": "2026-01-05T08:25:00-03:00",
}


class _PedidoDaSerie(Exception):
    pass


def test_pib_no_comeco_de_janeiro_usa_a_edicao_de_dezembro(tmp_path, monkeypatch):
    provedor = macro.MacroProvider(cache_dir=tmp_path)

    def baixar(url, instante):
        if "sitebcb/calendario" in url:
            ano = next(a for a in AGENDAS if f"{a}-01-01" in url)
            conteudo = {
                "conteudo": [{"evento": "Relatório Focus", "dataEvento": AGENDAS[ano]}]
            }
            return macro.SnapshotMacro(
                json.dumps(conteudo), url, instante.isoformat(), "c" * 64
            )
        raise _PedidoDaSerie(url)

    monkeypatch.setattr(provedor, "baixar", baixar)
    with pytest.raises(_PedidoDaSerie) as pedido:
        provedor.pib(D)
    assert "2025-12-26" in str(pedido.value)  # a sexta anterior à edição de 29/12


def test_banco_no_comeco_de_janeiro_aceita_a_edicao_de_dezembro():
    with closing(sqlite3.connect(":memory:")) as conn:
        migracoes.aplicar(conn)
        conn.execute(
            "INSERT INTO series_macro VALUES ('focus_edicao', '2025-12-26', NULL, ?, '{}', 'f', "
            "'2026-01-03T00:00:00+00:00', 'h')",
            (AGENDAS["2025"],),
        )
        resultado = macro._pib_do_banco(conn, D)
    assert resultado != {"abstencao": "edição Focus devida ausente no banco"}
