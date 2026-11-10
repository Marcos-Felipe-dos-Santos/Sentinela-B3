"""BUG-3-02: com o Informe fora do ar, o provedor real devolvia rendimento vazio sem risco.

`CVMFIIProvider.obter_rendimentos_fii` engolia a falha de cada ano e devolvia um dicionário
vazio com cara de sucesso; a falha não chega a `riscos_dados` (sintoma do BUG-2C-12 pelo
provedor real). Achado na revisão do F3-P04, 10/11/2026.
"""

from cvm_fii_provider import CVMFIIProvider
from market_engine import MarketEngine


def test_informe_real_fora_do_ar_entra_nos_riscos(tmp_path, monkeypatch):
    provedor = CVMFIIProvider.__new__(CVMFIIProvider)

    def fora_do_ar(ano):
        raise OSError(f"Informe {ano} indisponível")

    monkeypatch.setattr(provedor, "baixar_informe", fora_do_ar)
    motor = object.__new__(MarketEngine)
    motor._is_fii_ticker = lambda *args: True
    motor.cvm_fii = provedor
    dados = {"cnpj": "11.111.111/0001-11", "classe_ativo": "FII"}
    motor._buscar_rendimento_fii("TSTF11", dados)
    assert "abstencao" in dados["informe_fii"]
    assert any("Informe" in risco for risco in dados.get("riscos_dados", []))
