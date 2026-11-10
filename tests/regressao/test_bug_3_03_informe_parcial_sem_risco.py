"""BUG-3-03: Informe do ano corrente sem o fundo e os dois anos anteriores ilegíveis, sem risco.

Sem linhas do fundo no ano corrente, a janela de 12 meses depende dos Informes dos anos
anteriores. Se esses dois falham, `obter_rendimentos_fii` devolve rendimento vazio com cara
de sucesso, porque o ano corrente foi lido; a falha não chega a `riscos_dados`. Borda
registrada na revisão do F3-P04 (10/11/2026); decisão do Marcos de 10/11/2026: destino F3-3c-fix (decisão 36).
"""

from pathlib import Path

import pytest

from cvm_fii_provider import CVMFIIProvider
from market_engine import MarketEngine


@pytest.mark.xfail(strict=True, reason="BUG-3-03, corrige F3-3c-fix")
def test_anos_da_janela_ilegiveis_entram_nos_riscos(monkeypatch):
    provedor = CVMFIIProvider.__new__(CVMFIIProvider)
    lidos = []

    def linhas(cnpj, ano):
        lidos.append(ano)
        if ano == lidos[0]:  # o primeiro ano lido é o corrente
            return Path("inf_mensal_fii.zip"), [], []
        return None

    monkeypatch.setattr(provedor, "_linhas_do_fundo", linhas)
    motor = object.__new__(MarketEngine)
    motor._is_fii_ticker = lambda *args: True
    motor.cvm_fii = provedor
    dados = {"cnpj": "11.111.111/0001-11", "classe_ativo": "FII"}
    motor._buscar_rendimento_fii("TSTF11", dados)
    assert any("Informe" in risco for risco in dados.get("riscos_dados", []))
