"""BUG-3-08: booleano do JSON vira taxa observada na leitura do SGS.

`ler_sgs` faz `float(item["valor"])`, e `float(True)` é 1.0: um `true` vira Selic de 1% a.a.
Marcador lógico não demonstra taxa; zero numérico continua legítimo. Auditoria FASE do
Codex, 10/11/2026; destino F3-1d.
"""

import json
from datetime import date

import pytest

from sentinela.data import macro_por_data as mpd


@pytest.mark.parametrize("valor", [True, False])
def test_booleano_nao_vira_observacao(valor):
    with pytest.raises(ValueError, match="SGS"):
        mpd.ler_sgs(json.dumps([{"data": "02/01/2026", "valor": valor}]))


def test_zero_numerico_continua_observacao():
    lidas = mpd.ler_sgs(
        json.dumps(
            [{"data": "02/01/2026", "valor": 0}, {"data": "05/01/2026", "valor": "0"}]
        )
    )
    assert lidas == (
        mpd.Observacao(date(2026, 1, 2), 0.0),
        mpd.Observacao(date(2026, 1, 5), 0.0),
    )
