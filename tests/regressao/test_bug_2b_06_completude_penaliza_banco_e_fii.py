"""BUG-2B-06: a completude penaliza banco e FII por campos que o modelo deles não tem.

`DataQualityReport.completude` conta `receita_liquida`, `margem_liquida` e
`divida_liq_ebitda` para todo ativo; o modelo de banco não preenche os três (F2A-8 e F2A-9),
e o FII também não, como P/L, ROE e LPA. Um banco com tudo o mais fica em 70%; um FII com
preço, DY, P/VP e VPA, em 40%. Origem: F2B-21, pergunta 8
(auditoria externa da 2A, correção 6).
"""

import pytest

from data_quality import _CAMPOS_ESPERADOS, DataQualityReport

INAPLICAVEIS = ("receita_liquida", "margem_liquida", "divida_liq_ebitda")


BUG = pytest.mark.xfail(
    strict=True,
    reason="BUG-2B-06 · completude penaliza banco e FII por campos inaplicáveis · corrige: "
    "a decidir no marcador",
)


@BUG
def test_banco_sem_os_campos_do_modelo_de_empresa():
    # Banco pelo setor do índice (o critério da correção, setor ou modelo, é do marcador).
    dados = {c: 1.0 for c in _CAMPOS_ESPERADOS if c not in INAPLICAVEIS}
    completude = DataQualityReport({**dados, "setor": "Bancos"}).completude()
    assert completude["completude_pct"] == 100


@BUG
def test_fii_so_com_os_campos_de_fii():
    # FII com preço, DY, P/VP e VPA: P/L, ROE, LPA e os três campos de empresa não se aplicam.
    dados = {
        "classe_ativo": "FII",
        "preco_atual": 100.0,
        "dy": 0.1,
        "pvp": 1.0,
        "vpa": 100.0,
    }
    assert DataQualityReport(dados).completude()["completude_pct"] == 100
