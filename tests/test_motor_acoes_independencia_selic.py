"""F2C-42: fronteira do motor sem dependência do coletor da Selic (F2B-5)."""

import ast
from pathlib import Path

import pytest

COLETOR = "get_selic_atual"


def _exigir_independencia(arvore: ast.AST) -> None:
    """Não importar/acessar o coletor, ainda que a fixture o tenha fixado."""
    for no in ast.walk(arvore):
        if isinstance(no, ast.ImportFrom):
            assert all(nome.name != COLETOR for nome in no.names)
        elif isinstance(no, ast.Name):
            assert no.id != COLETOR
        elif isinstance(no, ast.Attribute):
            assert no.attr != COLETOR
        elif (
            isinstance(no, ast.Call)
            and isinstance(no.func, ast.Name)
            and no.func.id == "getattr"
            and len(no.args) >= 2
        ):
            atributo = no.args[1]
            assert not (
                isinstance(atributo, ast.Constant) and atributo.value == COLETOR
            )


def _motor() -> ast.Module:
    caminho = Path(__file__).resolve().parents[1] / "valuation_engine.py"
    fonte = caminho.read_text(encoding="utf-8")
    # Sem o nome da API não há dependência nominal; evita analisar as milhares
    # de cópias de funções geradas pelo mutmut quando nenhuma contém o nome.
    if COLETOR not in fonte:
        return ast.Module(body=[], type_ignores=[])
    return ast.parse(fonte)


def test_motor_de_acoes_independe_do_coletor_da_selic():
    _exigir_independencia(_motor())


@pytest.mark.parametrize(
    "regressao",
    [
        "from config import get_selic_atual",
        "from config import get_selic_atual as taxa_atual",
        "taxa = get_selic_atual()",
        "import config; taxa = config.get_selic_atual()",
        "import config; taxa = getattr(config, 'get_selic_atual')()",
    ],
)
def test_guarda_falha_se_coletor_for_reintroduzido(regressao, tmp_path, monkeypatch):
    # Módulo sintético com a regressão nominal: percorre a mesma leitura e a
    # mesma asserção do teste real, sem editar o motor nem importar config.
    (tmp_path / "valuation_engine.py").write_text(regressao, encoding="utf-8")
    monkeypatch.setitem(globals(), "__file__", str(tmp_path / "tests" / "contrato.py"))
    with pytest.raises(AssertionError):
        test_motor_de_acoes_independe_do_coletor_da_selic()


def test_mencao_textual_nao_e_dependencia_executavel():
    arvore = _motor()
    arvore.body.extend(ast.parse('nota = "get_selic_atual não é insumo do motor"').body)
    _exigir_independencia(arvore)
