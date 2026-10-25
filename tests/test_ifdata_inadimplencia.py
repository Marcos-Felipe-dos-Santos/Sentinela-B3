"""Inadimplência do IF.data, relatório 16, só para leitura (F2B-32; ficha bancos 1.1, §2 e §3).

Linhas no formato do OData, recortadas da resposta do levantamento da 2B (BB, conglomerado
prudencial C0080329, data-base 2026-06; `docs/decisoes/fontes-fase2b.md`, "Inadimplência").
"""

from datetime import date

import pytest

from sentinela.data.providers import ifdata
from tests.test_cvm_bancos import CADASTRO_BB, CAPITAL_BB, _buscar_falso

AUSENTE = "relatório 16 sem as contas 148834 (Inadimplência) e 24454 (Total Geral)"
FORA = "fora do domínio: carteira inadimplida e Total Geral sem razão em [0; 1]"
CARTEIRA_BB = [
    {"Conta": "148833", "NomeColuna": "Ativos problemáticos", "Saldo": 104092086027.33},
    {"Conta": "148834", "NomeColuna": "Inadimplência", "DescricaoColuna": "Carteira ativa inadimplida arrastada", "Saldo": 65383226229.8},
    {"Conta": "24454", "NomeColuna": "Total Geral", "Saldo": 1115404849436.43},
]  # fmt: skip


def _capital(carteira):
    buscar, pedidos = _buscar_falso(
        {
            "@AnoMes=202606&$filter=Cnpj": CADASTRO_BB,
            "@AnoMes=202606&@TipoInstituicao=1&@Relatorio='5'": CAPITAL_BB,
            "@AnoMes=202606&@TipoInstituicao=1&@Relatorio='16'": carteira,
        }
    )
    return ifdata.ler_capital("00.000.000/0001-91", date(2026, 10, 13), buscar), pedidos


def test_inadimplencia_pelo_relatorio_16_do_mesmo_conglomerado_e_data():
    capital, pedidos = _capital(CARTEIRA_BB)
    assert capital.inadimplencia == pytest.approx(65383226229.8 / 1115404849436.43)
    assert capital.inadimplencia == pytest.approx(0.0586, abs=1e-4)
    assert "inadimplencia" not in capital.motivos
    assert pedidos[-1] == ifdata.caminho_carteira("202606", "C0080329")
    assert "@Relatorio='16'" in pedidos[-1] and "CodInst eq 'C0080329'" in pedidos[-1]


@pytest.mark.parametrize(
    ("carteira", "motivo"),
    [
        ([], AUSENTE),
        (CARTEIRA_BB[:2], AUSENTE),
        ([{**CARTEIRA_BB[1], "Saldo": 2e12}, CARTEIRA_BB[2]], FORA),
        ([CARTEIRA_BB[1], {**CARTEIRA_BB[2], "Saldo": 0}], FORA),
        ([{**CARTEIRA_BB[1], "Saldo": -1}, CARTEIRA_BB[2]], FORA),
        ([{**CARTEIRA_BB[1], "Saldo": "x"}, CARTEIRA_BB[2]], FORA),
        ([{**CARTEIRA_BB[1], "Saldo": float("nan")}, CARTEIRA_BB[2]], FORA),
        ([{**CARTEIRA_BB[1], "NomeColuna": "Outra"}, CARTEIRA_BB[2]], AUSENTE),
    ],
)  # fmt: skip
def test_carteira_invalida_fica_sem_valor_com_motivo(carteira, motivo):
    capital, _ = _capital(carteira)
    assert capital.inadimplencia is None
    assert capital.motivos["inadimplencia"] == motivo
    assert capital.basileia == pytest.approx(0.151297835513664)
