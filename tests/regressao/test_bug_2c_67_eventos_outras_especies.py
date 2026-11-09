"""BUG-2C-67: evento de duas espécies alheias não invalida a base do ticker."""

import pytest

from sentinela.data.fatores_acoes_b3 import fatores_da_relacao
from tests.test_fatores_acoes_b3 import AS_OF, ON, PN, dados, documentos, evento


@pytest.mark.parametrize("emitido", ["BRTESTACNPA0", "BRTESTACNPB0"])
def test_evento_entre_especies_fora_da_on_nao_bloqueia_fator(emitido):
    alheio = evento(isin=PN, assetIssued=emitido)
    r = fatores_da_relacao(dados([evento(), alheio]), documentos(), AS_OF)
    assert "abstencao" not in r
    assert r["fatores"] == {"2021": 2, "2022": 2, "2023": 1, "2024": 1, "2025": 1}
    assert r["evidencias"][1]["eventos"] == [evento()]


@pytest.mark.parametrize("origem,emitido", [(PN, ON), (ON, PN)])
def test_evento_envolvendo_componente_exige_reconciliacao(origem, emitido):
    r = fatores_da_relacao(
        dados([evento(), evento(isin=origem, assetIssued=emitido)]), documentos(), AS_OF
    )
    assert "espécie distinta" in r["abstencao"]
