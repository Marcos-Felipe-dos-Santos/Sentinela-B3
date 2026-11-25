"""BUG-4-09: encerramento da DFP não prova que ela já foi entregue à CVM."""

import zipfile
from datetime import date
from pathlib import Path

import pytest

from cvm_provider import CVMProvider
from tests.test_cvm_series import CD_CVM, CNPJ, _zip


@pytest.mark.parametrize(
    ("referencia", "entrega", "esperado"),
    [
        pytest.param(
            date(2026, 5, 1),
            "2026-06-15",
            2025,
            id="antes_da_entrega",
        ),
        pytest.param(
            date(2026, 6, 15),
            "2026-06-15",
            2025,
            id="no_dia_da_entrega",
        ),
        pytest.param(date(2026, 6, 16), "2026-06-15", 2026, id="depois_da_entrega"),
        pytest.param(
            date(2026, 6, 16),
            None,
            None,
            id="sem_indice",
        ),
    ],
)
def test_exercicio_nao_civil_so_entra_depois_da_entrega_comprovada(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    referencia: date,
    entrega: str | None,
    esperado: int | None,
) -> None:
    dre = [
        (
            "2026-03-31",
            "1",
            "ÚLTIMO",
            "2025-04-01",
            "2026-03-31",
            "3.11",
            "Lucro/Prejuízo Consolidado do Período",
            100,
        )
    ]
    arquivo = _zip(tmp_path / "dfp.zip", "dfp", 2026, dre, [])
    if entrega is not None:
        indice = (
            "CNPJ_CIA;DT_REFER;VERSAO;CD_CVM;CATEG_DOC;DT_RECEB\n"
            f"{CNPJ};2026-03-31;1;{CD_CVM};DFP;{entrega}\n"
        )
        with zipfile.ZipFile(arquivo, "a") as zip_dfp:
            zip_dfp.writestr("dfp_cia_aberta_2026.csv", indice.encode("latin-1"))
    provedor = CVMProvider(cache_dir=str(tmp_path / "cache"))
    monkeypatch.setattr(provedor, "baixar_dfp", lambda ano: arquivo)

    if esperado is None:
        with pytest.raises(OSError, match="^DFP sem índice de entregas$"):
            provedor.exercicio_anual_mais_recente(CD_CVM, referencia)
    else:
        assert provedor.exercicio_anual_mais_recente(CD_CVM, referencia) == esperado


def _provedor_com(tmp_path: Path, monkeypatch, dre, indice_linhas) -> CVMProvider:
    arquivo = _zip(tmp_path / "dfp.zip", "dfp", 2026, dre, [])
    indice = "CNPJ_CIA;DT_REFER;VERSAO;CD_CVM;CATEG_DOC;DT_RECEB\n" + "".join(
        f"{CNPJ};{referencia};{versao};{CD_CVM};DFP;{entrega}\n"
        for referencia, versao, entrega in indice_linhas
    )
    with zipfile.ZipFile(arquivo, "a") as zip_dfp:
        zip_dfp.writestr("dfp_cia_aberta_2026.csv", indice.encode("latin-1"))
    provedor = CVMProvider(cache_dir=str(tmp_path / "cache"))
    monkeypatch.setattr(provedor, "baixar_dfp", lambda ano: arquivo)
    return provedor


def test_periodo_incompleto_entregue_nao_promove_o_exercicio(tmp_path, monkeypatch):
    dre = [
        ("2026-03-31", "1", "ÚLTIMO", "2025-07-01", "2026-03-31", "3.11",
         "Lucro/Prejuízo Consolidado do Período", 100),
    ]  # fmt: skip
    provedor = _provedor_com(
        tmp_path, monkeypatch, dre, [("2026-03-31", "1", "2026-06-15")]
    )

    assert provedor.exercicio_anual_mais_recente(CD_CVM, date(2026, 6, 16)) == 2025


def test_linha_sem_prova_nao_encerra_a_busca_pela_entregue(tmp_path, monkeypatch):
    linha = (
        "ÚLTIMO",
        "2025-04-01",
        "2026-03-31",
        "3.11",
        "Lucro/Prejuízo Consolidado do Período",
        100,
    )
    dre = [
        ("2026-03-31", "1", "ÚLTIMO", "2025-07-01", "2026-03-31", "3.11",
         "Lucro/Prejuízo Consolidado do Período", 100),
        ("2026-03-31", "1", *linha),
        ("2026-03-31", "2", *linha),
        ("2026-03-31", "3", *linha),
    ]  # fmt: skip
    indice = [("2026-03-31", "2", "2026-02-30"), ("2026-03-31", "3", "2026-06-15")]
    provedor = _provedor_com(tmp_path, monkeypatch, dre, indice)

    assert provedor.exercicio_anual_mais_recente(CD_CVM, date(2026, 6, 16)) == 2026
