"""BUG-2B-47: composição de outra versão do Informe autoriza a lente de FII.

Auditoria de fechamento da 2B (Codex, 25/10/2026): com o complemento do mês final na versão
2 e a composição só na versão 1, a lente classifica o fundo pela composição antiga. A ficha
FII 1.3 (§3c) exige a composição da mesma versão do complemento selecionado.
"""

from sentinela.data import rendimento_fii as rf
from tests.test_fii_rendimento_elegivel import _avaliar, _composicao, _registros


def test_composicao_de_outra_versao_nao_autoriza_a_lente():
    registros = _registros()
    revisado = {**registros[-1], "Versao": "2"}
    r = _avaliar([*registros, revisado], _composicao())  # composição só na versão 1
    assert r == rf.Abstencao(rf.MOTIVO_SEM_COMPOSICAO)


def test_composicao_da_versao_selecionada_autoriza():
    registros = _registros()
    revisado = {**registros[-1], "Versao": "2"}
    composicao = [{**_composicao()[0], "Versao": "2"}]
    assert not isinstance(_avaliar([*registros, revisado], composicao), rf.Abstencao)


def test_composicao_toda_vazia_e_tipo_desconhecido():
    # Ficha 1.3, §3c: registro todo vazio não vale como zero; é tipo desconhecido.
    vazia = {c: "" for c in _composicao()[0] if c not in ("Data_Referencia", "Versao")}
    r = _avaliar(composicoes=[{**_composicao()[0], **vazia}])
    assert isinstance(r, rf.Abstencao)
    assert r.motivo.startswith("classificação de FII desconhecida")


def test_vazio_ao_lado_de_posicao_preenchida_vale_zero():
    r = _avaliar(composicoes=[{**_composicao()[0], "CRI": ""}])
    assert not isinstance(r, rf.Abstencao)
    assert r["tipo"] == "tijolo"
