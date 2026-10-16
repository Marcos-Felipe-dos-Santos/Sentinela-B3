"""BUG-2A-08: o relatório de rastreabilidade diz que o FII sem P/VP usa 1,0.

`sentinela/reports/rastreabilidade.py` escreve "o motor usa P/VP = 1,0 (sem CVMFIIProvider
injetado)"; desde o F2A-11 a lente se abstém, e o F2A-13 tirou o provedor do motor. Origem:
auditoria externa da Fase 2A (Gemini 2ª passada, 15/10/2026).
"""

from tests.test_rastreabilidade import _fii, _html


def test_fii_sem_pvp_nao_e_descrito_com_pvp_um():
    html = _html(_fii(pvp=None), eh_fii=True)
    assert "P/VP = 1,0" not in html
    assert "CVMFIIProvider" not in html
