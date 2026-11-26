"""BUG-4-23: quando o seletor recua um exercício, a versão da DFP entregue em D volta a valer.

O F4-C01 (BUG-4-15) fez o seletor devolver a versão comprovada só quando promove o exercício do
ano corrente. Ao recuar para o anterior, ele devolvia `(ano anterior, None)`, e o snapshot e a
série voltavam a escolher a maior `VERSAO` do ZIP, inclusive a entregue em D (bloqueio 1 da
segunda rodada da R2 do bloco 0, `docs/loop/auditorias/bloco0-codex-2.md`).

Corte em 16/06/2026; exercício de 2025 com V1 entregue em 15/06 (lucro de R$ 100 mil) e V2 em
16/06 (R$ 900 mil); o ZIP de 2026 não tem DFP anual encerrada. DFPs sintéticas.
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


def _dfp(caminho, ano: int, linhas: list[tuple], indice: str):
    dre = [
        (
            fim,
            versao,
            "ÚLTIMO",
            inicio,
            fim,
            "3.11",
            "Lucro/Prejuízo Consolidado do Período",
            v,
        )
        for fim, versao, inicio, v in linhas
    ]
    _zip(caminho, "dfp", ano, dre, [])
    with zipfile.ZipFile(caminho, "a") as z:
        for tipo in ("BPA_con", "BPP_con"):
            z.writestr(f"dfp_cia_aberta_{tipo}_{ano}.csv", ";".join(COLUNAS) + "\n")
        z.writestr(
            f"dfp_cia_aberta_{ano}.csv",
            "CNPJ_CIA;DT_REFER;VERSAO;CD_CVM;CATEG_DOC;DT_RECEB\n" + indice,
        )
    return caminho


def _provedor(tmp_path, monkeypatch, *, entrega_v1="2026-06-15") -> CVMProvider:
    arquivos = {
        2025: _dfp(
            tmp_path / "dfp_2025.zip",
            2025,
            [("2025-12-31", v, "2025-01-01", lucro) for v, lucro in LUCRO.items()],
            f"{CNPJ};2025-12-31;1;{CD_CVM};DFP;{entrega_v1}\n"
            f"{CNPJ};2025-12-31;2;{CD_CVM};DFP;2026-06-16\n",
        ),
        2026: _dfp(tmp_path / "dfp_2026.zip", 2026, [], ""),
    }
    provedor = CVMProvider(cache_dir=str(tmp_path / "cache"))
    monkeypatch.setattr(provedor, "baixar_dfp", lambda ano: arquivos[ano])

    def sem_itr(ano):
        raise OSError("ITR fora do teste")

    monkeypatch.setattr(provedor, "baixar_itr", sem_itr)
    return provedor


def test_seletor_recua_e_devolve_a_versao_entregue_antes_do_corte(
    tmp_path, monkeypatch
):
    provedor = _provedor(tmp_path, monkeypatch)

    assert provedor.exercicio_e_versao_mais_recente(CD_CVM, D) == (2025, "1")


def test_cascata_de_hoje_le_a_v1_no_snapshot_e_na_serie(tmp_path, monkeypatch):
    monkeypatch.setattr(market_engine, "_hoje_sp", lambda: D)
    engine = _engine(monkeypatch, info={}, cvm=_provedor(tmp_path, monkeypatch))
    dados = {"cd_cvm": CD_CVM, "preco_atual": 10.0}

    engine._buscar_cvm("TSTA3", dados, as_of=AS_OF)

    assert dados.get("lucro_liquido") == pytest.approx(LUCRO["1"] * 1_000)
    (ultimo,) = [e for e in dados["serie_cvm"]["exercicios"] if e["exercicio"] == 2025]
    assert ultimo["versao"] == "1"
    assert ultimo["lucro_liquido"] == pytest.approx(LUCRO["1"] * 1_000)


def test_sem_versao_comprovada_no_exercicio_anterior_abstem(tmp_path, monkeypatch):
    provedor = _provedor(tmp_path, monkeypatch, entrega_v1="2026-06-16")

    with pytest.raises(ValueError, match="exercício anterior"):
        provedor.exercicio_e_versao_mais_recente(CD_CVM, D)


def test_api_so_do_ano_continua_recuando_sem_exigir_versao(tmp_path, monkeypatch):
    """Controle: a API antiga, usada nas datas passadas pelo recorte, devolve só o ano."""
    provedor = _provedor(tmp_path, monkeypatch, entrega_v1="2026-06-16")

    assert provedor.exercicio_anual_mais_recente(CD_CVM, D) == 2025


def test_sem_versao_comprovada_a_cascata_de_hoje_fica_sem_cvm(tmp_path, monkeypatch):
    monkeypatch.setattr(market_engine, "_hoje_sp", lambda: D)
    provedor = _provedor(tmp_path, monkeypatch, entrega_v1="2026-06-16")
    engine = _engine(monkeypatch, info={}, cvm=provedor)
    dados = {"cd_cvm": CD_CVM, "preco_atual": 10.0}

    engine._buscar_cvm("TSTA3", dados, as_of=AS_OF)

    assert dados["cvm_disponivel"] is False
    assert "exercício anterior" in dados["serie_cvm"]["abstencao"]
    assert "lucro_liquido" not in dados


def test_ano_corrente_ausente_404_recua_com_a_versao_comprovada(tmp_path, monkeypatch):
    provedor = _provedor(tmp_path, monkeypatch)
    anteriores = provedor.baixar_dfp

    def sem_2026(ano):
        if ano == 2026:
            erro = OSError("404 no teste")
            erro.response = type("R", (), {"status_code": 404})()
            raise erro
        return anteriores(ano)

    monkeypatch.setattr(provedor, "baixar_dfp", sem_2026)

    assert provedor.exercicio_e_versao_mais_recente(CD_CVM, D) == (2025, "1")
