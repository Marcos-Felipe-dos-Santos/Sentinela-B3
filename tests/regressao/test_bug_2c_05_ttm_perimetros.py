"""BUG-2C-05: a subtração TTM ignora a evidência de perímetros (F2C-29/30).

Aritmética só vale entre bases comparáveis. Duas bases explicitamente distintas,
ou base sem demonstração, não autorizam 50-20 nem soma anual como se homogêneas.
"""

from dataclasses import replace
from datetime import date

import pytest

from sentinela.data import series_cvm as s
from tests.test_cvm_series import EXERCICIO_2025


def evidencia(perimetro: str) -> dict:
    return {
        c: {
            "perimetro": perimetro,
            "evidencia_comparabilidade": "hipótese explícita do caso sintético CVM, mesmo perímetro",
        }
        for c in s.CAMPOS_TTM
    }


@pytest.mark.parametrize("outro", ["outro_perimetro", None])
def test_ttm_nao_combina_perimetros_sem_demonstracao(outro):
    acumulados = [
        replace(a, proveniencia=evidencia("mesmo_perimetro")) for a in EXERCICIO_2025
    ]
    acumulados[1] = replace(
        acumulados[1], proveniencia=evidencia(outro) if outro else {}
    )
    resultado = s.ttm(acumulados, date(2025, 12, 31))
    assert resultado["valores"]["lucro_liquido"] is None
    assert "perímetro" in resultado["motivos"]["lucro_liquido"]


def test_perimetro_igual_com_evidencia_permite_a_aritmetica():
    acumulados = [
        replace(a, proveniencia=evidencia("mesmo_perimetro")) for a in EXERCICIO_2025
    ]
    resultado = s.ttm(acumulados, date(2025, 12, 31))
    assert resultado["valores"]["lucro_liquido"] == 70


@pytest.mark.parametrize("valor", [None, "", "  ", 123])
def test_id_igual_sem_evidencia_nao_prova_comparabilidade(valor):
    acumulados = [
        replace(a, proveniencia=evidencia("mesmo_perimetro")) for a in EXERCICIO_2025
    ]
    ultimo = acumulados[-1]
    fontes = {
        c: {**p, "evidencia_comparabilidade": valor}
        for c, p in ultimo.proveniencia.items()
    }
    acumulados[-1] = replace(ultimo, proveniencia=fontes)
    resultado = s.ttm(acumulados, date(2025, 12, 31))
    assert resultado["valores"]["lucro_liquido"] is None
    assert "perímetro" in resultado["motivos"]["lucro_liquido"]
