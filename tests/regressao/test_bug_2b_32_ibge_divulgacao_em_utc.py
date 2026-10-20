"""BUG-2B-32: a `data_divulgacao` do calendário do IBGE era lida como UTC.

Auditoria do F2B-48/F2B-30, ressalva 3. O horário é o de Brasília. Defeito latente: só a
data é usada, e a mesma hora de relógio dá o mesmo dia nos dois fusos; a regressão confere
o instante pelo leitor da data.
"""

from datetime import datetime
from zoneinfo import ZoneInfo

from sentinela.data.providers import macro


def test_divulgacao_do_ibge_no_fuso_de_sao_paulo():
    instante = macro.divulgacao_ibge("09/10/2026 09:00:00")
    assert instante == datetime(2026, 10, 9, 9, tzinfo=ZoneInfo("America/Sao_Paulo"))
    assert instante.utcoffset().total_seconds() == -3 * 3600
