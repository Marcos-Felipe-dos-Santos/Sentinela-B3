"""BUG-2C-25: relatório de ação não declara uma Selic usada pelas lentes."""

from tests.test_rastreabilidade import _acao, _html


def test_relatorio_de_acao_nao_declara_selic_usada():
    assert "Selic usada" not in _html(_acao())
