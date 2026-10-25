"""Modelo de demonstração pelo BPP consolidado (F2B-4; decisões do Marcos de 19 e 25/10/2026).

Banco: PL em 2.07/2.08, com precedência. Seguradora: conta com descrição que contenha
"Provisões Técnicas", "contrato(s) de seguro/resseguro" ou "Atividade Seguradora". Sem elas,
empresa (holdings inclusive). Sem BPP consolidado, sem correspondência ou com conflito: None.
"""

import zipfile

import pytest

from cvm_provider import CVMProvider
from tests.test_market_engine import _engine

IND = {"cvm_dt_refer": "2025-12-31", "cvm_versao": "2"}
PL_EMPRESA = ("2.03", "Patrimônio Líquido Consolidado")
PL_BANCO = ("2.08", "Patrimônio Líquido Consolidado")


def _modelo(tmp_path, monkeypatch, contas):
    cab = "CNPJ_CIA;DT_REFER;VERSAO;CD_CVM;ORDEM_EXERC;CD_CONTA;DS_CONTA;VL_CONTA\n"
    corpo = "".join(
        f"00.000.000/0001-00;2025-12-31;2;9;ÚLTIMO;{conta};{ds};100\n"
        for conta, ds in contas
    )
    caminho = tmp_path / "dfp.zip"
    with zipfile.ZipFile(caminho, "w") as zf:
        zf.writestr("dfp_cia_aberta_BPP_con_2025.csv", (cab + corpo).encode("latin-1"))
    provedor = CVMProvider.__new__(CVMProvider)
    monkeypatch.setattr(provedor, "baixar_dfp", lambda ano: caminho)
    return provedor.modelo_do_documento(9, IND)


@pytest.mark.parametrize(
    "descricao",
    [
        "Provisões Técnicas de Seguros e Previdência",
        "PROVISOES TECNICAS",
        "Provisões técnicas de operações de assistência à saúde",
        "Passivos de contratos de seguros",
        "Passivos do contrato de resseguro",
        "Passivo de contratos de seguro",
        "Passivos da Atividade Seguradora/Resseguradora",
    ],
)
def test_seguradora_pela_descricao(tmp_path, monkeypatch, descricao):
    contas = [("2.01.02", descricao), PL_EMPRESA]
    assert _modelo(tmp_path, monkeypatch, contas) == "seguradora"


def test_holding_sem_contas_de_seguro_e_empresa(tmp_path, monkeypatch):
    contas = [("2.01.05", "Outras Obrigações"), ("2.01.06", "Provisões"), PL_EMPRESA]
    assert _modelo(tmp_path, monkeypatch, contas) == "empresa"


def test_banco_tem_precedencia_sobre_contas_de_seguro(tmp_path, monkeypatch):
    contas = [
        ("2.03", "Provisões Técnicas de Seguros e Previdência"),
        ("2.06.04", "Contratos de Seguro e Previdência Privada"),
        ("2.07", "Patrimônio Líquido Consolidado"),
    ]
    assert _modelo(tmp_path, monkeypatch, contas) == "banco"


def test_banco_com_2_03_nao_patrimonial(tmp_path, monkeypatch):
    contas = [("2.03", "Passivos Financeiros ao Valor Justo"), PL_BANCO]
    assert _modelo(tmp_path, monkeypatch, contas) == "banco"


def test_pl_nos_dois_modelos_e_conflito(tmp_path, monkeypatch):
    assert _modelo(tmp_path, monkeypatch, [PL_EMPRESA, PL_BANCO]) is None


def test_sem_bpp_consolidado_nao_tem_modelo(tmp_path, monkeypatch):
    assert _modelo(tmp_path, monkeypatch, [("2.01", "Passivo Circulante")]) is None


class _CVMComModelo:
    """Cascata até o modelo: um exercício com a proveniência da DFP do próprio documento."""

    def __init__(self, proveniencia):
        self.proveniencia = proveniencia

    def calcular_indicadores(self, cd_cvm, anos=1, **kwargs):
        return {2025: {"cvm_dt_refer": "2025-12-31", "cvm_versao": "2",
                       "cnpj": "00.000.000/0001-00", "proveniencia": self.proveniencia}}  # fmt: skip

    def modelo_do_documento(self, cd_cvm, ind):
        return "empresa"


def test_cascata_grava_a_proveniencia_do_bpp(monkeypatch):
    prov = {"data_entrega": "2026-02-12", "data_coleta": "2026-10-13T18:00:00+00:00"}
    engine = _engine(monkeypatch, info={"currentPrice": 20.0}, cvm=_CVMComModelo(prov))
    dados = {"cd_cvm": 9, "riscos_dados": []}
    engine._buscar_cvm("TSTA3", dados)
    assert dados["modelo_bpp"] == "empresa"
    assert dados["modelo_bpp_proveniencia"] == prov


def test_cascata_sem_proveniencia_grava_nulo(monkeypatch):
    engine = _engine(monkeypatch, info={"currentPrice": 20.0}, cvm=_CVMComModelo(None))
    dados = {"cd_cvm": 9, "riscos_dados": []}
    engine._buscar_cvm("TSTA3", dados)
    assert dados["modelo_bpp_proveniencia"] is None
