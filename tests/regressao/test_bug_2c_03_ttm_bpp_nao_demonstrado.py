"""BUG-2C-03: ausência do BPP não prova ausência de minoritários (D20/F2C-30).

Contrato externo aprovado em F2C-29: preservar DRE, mas só reservar o lucro total
com balanço legível da mesma companhia, data e versão. CSV sintético pelo layout CVM.
"""

import zipfile

import pytest

from cvm_provider import CVMProvider
from tests.test_cvm_series import CD_CVM, CNPJ, COLUNAS, _zip

DT = "2025-03-31"


def documento(tmp_path, estado: str, controladora: float = 0):
    """Documento trimestral, com lucro consolidado100 e receita200 em milhares."""
    dre = [
        (DT, "1", "ÚLTIMO", "2025-01-01", DT, "3.11", "Lucro/Prejuízo Consolidado do Período", 100),
        (DT, "1", "ÚLTIMO", "2025-01-01", DT, "3.11.01", "Atribuído a Sócios da Empresa Controladora", controladora),
        (DT, "1", "ÚLTIMO", "2025-01-01", DT, "3.11.02", "Atribuído a Sócios Não Controladores", 0),
        (DT, "1", "ÚLTIMO", "2025-01-01", DT, "3.01", "Receita de Venda de Bens e/ou Serviços", 200),
    ]  # fmt: skip
    caminho = _zip(tmp_path / "itr.zip", "itr", 2025, dre, [])
    if estado == "ausente":
        return caminho
    dt = "2024-12-31" if estado == "outra_data" else DT
    versao = "2" if estado == "outra_versao" else "1"
    cnpj = "11.111.111/0001-11" if estado == "outra_companhia" else CNPJ
    codigo = CD_CVM + 1 if estado == "outra_companhia" else CD_CVM
    conta, descricao, valor = "2.03", "Patrimônio Líquido Consolidado", "50"
    if estado == "zero":
        conta, descricao, valor = (
            "2.03.09",
            "Participação dos Acionistas Não Controladores",
            "0",
        )
    linha = [
        cnpj,
        dt,
        versao,
        codigo,
        "DF Consolidado",
        "MIL",
        "ÚLTIMO",
        dt,
        dt,
        conta,
        descricao,
        valor,
    ]
    texto = ";".join(COLUNAS) + "\n"
    if estado != "vazio":
        texto += ";".join(map(str, linha))
    if estado == "ilegivel":
        texto = "coluna_errada\nsem_contrato"
    with zipfile.ZipFile(caminho, "a") as zf:
        zf.writestr("itr_cia_aberta_BPP_con_2025.csv", texto.encode("latin-1"))
    return caminho


@pytest.mark.parametrize(
    "estado",
    ["ausente", "vazio", "ilegivel", "outra_data", "outra_versao", "outra_companhia"],
)
def test_bpp_nao_demonstrado_nao_autoriza_reserva(tmp_path, estado):
    provider = CVMProvider(cache_dir=str(tmp_path / "cache"))
    (a,) = provider._acumulados_do_arquivo(
        documento(tmp_path, estado), "ITR", CD_CVM, "empresa"
    )
    assert a.valores["lucro_controladores"] is None
    assert "BPP" in a.motivos["lucro_controladores"]
    assert a.valores["lucro_liquido"] == 100_000
    assert a.valores["receita_liquida"] == 200_000


@pytest.mark.parametrize("estado", ["rubrica_ausente", "zero"])
def test_bpp_correspondente_preserva_reserva_aprovada(tmp_path, estado):
    provider = CVMProvider(cache_dir=str(tmp_path / "cache"))
    (a,) = provider._acumulados_do_arquivo(
        documento(tmp_path, estado), "ITR", CD_CVM, "empresa"
    )
    assert a.valores["lucro_controladores"] == 100_000


def test_controladora_direta_independe_do_bpp_da_reserva(tmp_path):
    provider = CVMProvider(cache_dir=str(tmp_path / "cache"))
    (a,) = provider._acumulados_do_arquivo(
        documento(tmp_path, "ausente", 80), "ITR", CD_CVM, "empresa"
    )
    assert a.valores["lucro_controladores"] == 80_000


def test_proveniencia_distingue_dre_dva_e_reserva(tmp_path):
    provider = CVMProvider(cache_dir=str(tmp_path / "cache"))
    (a,) = provider._acumulados_do_arquivo(
        documento(tmp_path, "rubrica_ausente"), "ITR", CD_CVM, "empresa"
    )
    p = a.proveniencia
    assert p["lucro_liquido"]["demonstrativo"] == "DRE_con"
    assert p["dividendos"]["demonstrativo"] == "DVA_con"
    assert p["dividendos"]["motivo"] == "DVA indisponível no documento"
    assert p["lucro_controladores"]["bpp_correspondente_lido"] is True
    assert "lucro total" in p["lucro_controladores"]["reserva"]
    assert p["lucro_liquido"]["arquivo"] == "itr.zip"
    assert p["lucro_liquido"]["inicio"] == "2025-01-01"
    assert p["lucro_liquido"]["fim"] == DT
    assert p["lucro_liquido"]["modelo"] == "empresa"
