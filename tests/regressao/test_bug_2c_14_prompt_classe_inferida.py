"""F2C-32: classe obtida sem identidade oficial deve ser identificada no prompt."""

from ai_core import SentinelaAI
from market_engine import RISCO_SEM_REFERENCIA
from sentinela.services.asset_classifier import AssetClassifier


def test_prompt_distingue_classe_sem_fonte_oficial(tmp_path) -> None:
    classificador = AssetClassifier(
        fiis_conhecidos=[], units_conhecidas=[], pasta_dados=tmp_path
    )
    classe = classificador.classify("TSTA3").value
    assert classe == "STOCK"
    dados = {"classe_ativo": classe, "riscos_dados": [RISCO_SEM_REFERENCIA]}
    # Não inicializa clientes, credenciais ou rede.
    ia = object.__new__(SentinelaAI)
    prompt = ia._montar_prompt("TSTA3", dados)
    assert "inferida" in prompt.lower()
