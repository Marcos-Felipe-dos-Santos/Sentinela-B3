"""BUG-3-06: a proveniência do SGS some no registro por data do MacroContext.

`MacroProvider.serie_sgs` devolve observações, coleta e a proveniência de cada janela
(fonte, data da coleta, hash e aviso); `MacroContext.registro_por_data` monta o registro só
com `valor` e `data`, e o consumidor não distingue fonte observada de cache com aviso (D16).
Auditoria FASE do Codex, 10/11/2026; destino F3-1d.
"""

from datetime import UTC, date, datetime

import pytest

from config import MacroContext
from sentinela.data.macro_por_data import Observacao

PROVENIENCIA = [
    {
        "fonte": "https://api.bcb.gov.br/dados/serie/bcdata.sgs.432/dados?formato=json",
        "data_coleta": "2026-11-10T00:33:00-03:00",
        "hash_sha256": "0" * 64,
        "aviso": "cache local: fonte indisponível na coleta",
    }
]


class _Provedor:
    def serie_sgs(self, serie, fim, instante):
        return {
            "observacoes": (Observacao(date(2026, 1, 2), 15.0),),
            "coleta": date(2026, 11, 10),
            "proveniencia": PROVENIENCIA,
        }


@pytest.mark.xfail(strict=True, reason="BUG-3-06, corrige F3-1d")
@pytest.mark.parametrize("nome", ["selic", "cdi"])
def test_registro_por_data_preserva_proveniencia(nome):
    macro = MacroContext(
        as_of=date(2026, 6, 1),
        provedor=_Provedor(),
        instante=datetime(2026, 11, 10, 3, 33, tzinfo=UTC),
    )
    registro = macro.registro_por_data(nome)
    assert "valor" in registro
    assert registro["proveniencia"] == PROVENIENCIA
