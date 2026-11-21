"""BUG-3-07: entrada finita do SGS gera resultado não finito ou exceção aritmética.

O parser recusa valor não finito na entrada, mas não protege o resultado: CDI diário finito
e extremo faz `(1 + v/100) ** 252` lançar `OverflowError`, e doze meses de IPCA extremos
multiplicados dão `inf`. Resultado não representável deve abster com motivo. Auditoria
FASE do Codex, 10/11/2026; destino F3-1d.
"""

import math
from datetime import date

from sentinela.data import macro_por_data as mpd


def test_cdi_extremo_abstem_sem_excecao():
    registro = mpd.cdi([mpd.Observacao(date(2026, 1, 2), 1e10)], date(2026, 1, 5))
    assert "valor" not in registro
    assert registro["abstencao"]


def test_ipca_extremo_abstem_sem_infinito():
    observacoes = [mpd.Observacao(date(2025, mes, 1), 1e300) for mes in range(1, 13)]
    registro = mpd.ipca_12m(observacoes, date(2026, 6, 1), date(2026, 6, 1))
    assert not ("valor" in registro and not math.isfinite(registro["valor"]))
    assert registro.get("abstencao")
