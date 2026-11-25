"""BUG-4-15: a DFP comprovada no corte é uma versão, e a leitura de hoje pode consumir outra.

O F4-A08 fez `exercicio_anual_mais_recente` exigir `DT_RECEB < D`, mas o seletor devolvia só o
ano. Na análise de hoje, o snapshot (`calcular_indicadores`) e a série (`indicadores_da_serie`)
escolhiam a maior `VERSAO` do ZIP: com V1 entregue em 15/06 e V2 entregue em D (16/06), o ano
2026 era comprovado pela V1 e os números vinham da V2 (bloqueador 1 da auditoria R2 do bloco 0,
`docs/loop/auditorias/bloco0-codex.md`).

DFP sintética com V1 e V2 de lucros distintos no mesmo ZIP; índice de entregas com as duas.
"""

import zipfile
from datetime import UTC, date, datetime

import pytest

import market_engine
from cvm_provider import CVMProvider
from tests.test_cvm_series import CD_CVM, CNPJ, COLUNAS, _zip
from tests.test_market_engine import _engine

D = date(2026, 6, 16)
AS_OF = datetime(2026, 6, 16, 15, tzinfo=UTC)
LUCRO = {"1": 100, "2": 900}  # escala MIL


def _provedor(tmp_path, monkeypatch) -> CVMProvider:
    dre = [
        (
            "2026-02-28",
            versao,
            "ÚLTIMO",
            "2025-03-01",
            "2026-02-28",
            "3.11",
            "Lucro/Prejuízo Consolidado do Período",
            lucro,
        )
        for versao, lucro in LUCRO.items()
    ]
    caminho = _zip(tmp_path / "dfp.zip", "dfp", 2026, dre, [])
    with zipfile.ZipFile(caminho, "a") as z:
        for tipo in ("BPA_con", "BPP_con"):
            z.writestr(f"dfp_cia_aberta_{tipo}_2026.csv", ";".join(COLUNAS) + "\n")
        z.writestr(
            "dfp_cia_aberta_2026.csv",
            "CNPJ_CIA;DT_REFER;VERSAO;CD_CVM;CATEG_DOC;DT_RECEB\n"
            f"{CNPJ};2026-02-28;1;{CD_CVM};DFP;2026-06-15\n"
            f"{CNPJ};2026-02-28;2;{CD_CVM};DFP;2026-06-16\n",
        )
    provedor = CVMProvider(cache_dir=str(tmp_path / "cache"))
    monkeypatch.setattr(provedor, "baixar_dfp", lambda ano: caminho)

    def sem_itr(ano):
        raise OSError("ITR fora do teste")

    monkeypatch.setattr(provedor, "baixar_itr", sem_itr)
    return provedor


def test_seletor_devolve_o_ano_e_a_versao_entregue_antes_do_corte(
    tmp_path, monkeypatch
):
    provedor = _provedor(tmp_path, monkeypatch)

    assert provedor.exercicio_e_versao_mais_recente(CD_CVM, D) == (2026, "1")
    assert provedor.exercicio_anual_mais_recente(CD_CVM, D) == 2026


def test_snapshot_e_serie_consomem_a_versao_comprovada(tmp_path, monkeypatch):
    provedor = _provedor(tmp_path, monkeypatch)

    snapshot = provedor.calcular_indicadores(
        CD_CVM, anos=1, ano_final=2026, versao_final="1"
    )
    serie = provedor.indicadores_da_serie(CD_CVM, 2026, versao_final="1")

    assert snapshot[2026]["cvm_versao"] == "1"
    assert snapshot[2026]["lucro_liquido"] == pytest.approx(LUCRO["1"] * 1_000)
    assert serie[2026]["cvm_versao"] == "1"
    assert serie[2026]["lucro_liquido"] == pytest.approx(LUCRO["1"] * 1_000)


def test_cascata_de_hoje_nao_le_a_versao_entregue_em_d(tmp_path, monkeypatch):
    monkeypatch.setattr(market_engine, "_hoje_sp", lambda: D)  # a análise é de hoje
    engine = _engine(monkeypatch, info={}, cvm=_provedor(tmp_path, monkeypatch))
    dados = {"cd_cvm": CD_CVM, "preco_atual": 10.0}

    engine._buscar_cvm("TSTA3", dados, as_of=AS_OF)

    assert dados.get("lucro_liquido") == pytest.approx(LUCRO["1"] * 1_000)


def test_sem_versao_final_o_snapshot_segue_a_maior_versao(tmp_path, monkeypatch):
    """Controle: a API antiga, sem versão, continua lendo a maior VERSAO do ZIP."""
    provedor = _provedor(tmp_path, monkeypatch)

    snapshot = provedor.calcular_indicadores(CD_CVM, anos=1, ano_final=2026)

    assert snapshot[2026]["cvm_versao"] == "2"


def test_versao_comprovada_ausente_do_arquivo_abstem_o_exercicio(tmp_path, monkeypatch):
    """Revisão 1: se a versão comprovada sumiu (novo download), não lê as outras."""
    provedor = _provedor(tmp_path, monkeypatch)

    snapshot = provedor.calcular_indicadores(
        CD_CVM, anos=1, ano_final=2026, versao_final="3"
    )

    assert 2026 not in snapshot


def test_cascata_retira_a_chave_interna_da_versao(tmp_path, monkeypatch):
    monkeypatch.setattr(market_engine, "_hoje_sp", lambda: D)
    engine = _engine(monkeypatch, info={}, cvm=_provedor(tmp_path, monkeypatch))
    dados = {"cd_cvm": CD_CVM, "preco_atual": 10.0}

    engine._buscar_cvm("TSTA3", dados, as_of=AS_OF)

    assert "_versao_dfp_final" not in dados
