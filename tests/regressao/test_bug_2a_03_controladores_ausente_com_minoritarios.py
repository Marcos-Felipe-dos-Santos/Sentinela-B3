"""BUG-2A-03: linha dos controladores ausente devolve o lucro consolidado com minoritários.

`controladores.lucro_dos_controladores` devolve o lucro total quando 3.11.01 falta, antes de
olhar a participação dos não controladores no balanço (2.03.09). Pela decisão 7.2 da ficha
(`docs/metodologia/por-acao.md`), o total só entra sem minoritários na DRE nem no balanço.
Origem: auditoria externa da Fase 2A (Codex reproduziu: 100 aceito com 50 de minoritários;
Gemini 2ª passada, 15/10/2026).
"""

from sentinela.data.contas_cvm import MOTIVO_LINHA_AUSENTE, Abstencao, Leitura
from sentinela.data.controladores import lucro_dos_controladores


def _l(valor):
    return Leitura(valor, "x", "x")


def test_linha_ausente_com_minoritarios_no_balanco_se_abstem():
    ausente = Abstencao(MOTIVO_LINHA_AUSENTE)
    resultado = lucro_dos_controladores(ausente, ausente, _l(100.0), _l(50.0))
    assert resultado.valor is None
    assert resultado.reserva is None
    assert resultado.motivo
