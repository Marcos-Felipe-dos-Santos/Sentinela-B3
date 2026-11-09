"""BUG-2C-01: o complemento FII não pode ignorar CODBDI conflitante no mesmo ticker.

Revisão interna do F2C-21, 26/10/2026. O grupo inteiro precisa demonstrar a categoria12;
a ordem dos registros não é evidência para resolver o conflito. Fonte: aceite F2C-21.
"""

from dataclasses import replace

from sentinela.data.referencia.correcoes import ler_identidades_fii
from sentinela.data.referencia.montagem import montar_outros
from sentinela.services.asset_classifier import AssetClassifier
from tests.regressao.test_bug_2b_21_fiis_fora_do_informe import _cotacao


def test_codbdi_conflitante_nao_e_resolvido_pela_ordem() -> None:
    correta = _cotacao()
    conflitante = replace(correta, codbdi="14")
    classificador = AssetClassifier(
        fiis_conhecidos=["BTCI11"], units_conhecidas=["BTCI11"]
    )
    for cotacoes in ([correta, conflitante], [conflitante, correta]):
        (registro,) = montar_outros(
            cotacoes, set(), {}, identidades_fii=ler_identidades_fii()
        )
        assert registro.classe == "UNKNOWN"
        assert "conflitante" in registro.motivo
        assert (
            classificador.classify("BTCI11", {"classe_ativo": registro.classe}).value
            == "UNKNOWN"
        )
