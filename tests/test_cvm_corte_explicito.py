"""F3-P13 e F3-3d: um só corte local para a seleção anual, snapshot e TTM.

Arquivos sintéticos usam o layout CVM já documentado nos testes de produtor, com o índice de
entregas. Desde o F3-3d (DD-61), o corte é pela entrega: entra o documento com `DT_RECEB`
anterior ao dia local de D (decisão 3 de 09/11). No corte de 30/06/2025, o ITR do segundo
trimestre de 2025 (entregue em agosto) ainda não existe: o TTM vai até 31/03/2025,
15 - 10 + 12 = 17 (até o F3-P13 era 30/06, 15 - 25 + 30 = 20, com o ITR entregue depois).
"""

import io
import zipfile
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import Mock

import pandas as pd
import pytest
from apoio_escopo import de_empresa

from market_engine import MarketEngine
from tests.regressao.test_bug_2c_61_ttm_produtor import arquivo
from tests.regressao.test_bug_2c_62_qualidade_produtor import CNPJ, fonte_anual
from tests.test_cvm_series import _Hoje
from valuation_engine import ValuationEngine


def test_dfp_itr_cascata_motor_compartilham_o_corte(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    p = fonte_anual(tmp_path, monkeypatch)
    itr = {
        ano: arquivo(
            tmp_path,
            "itr",
            ano,
            [(f"{ano}-03-31", a), (f"{ano}-06-30", b), (f"{ano}-09-30", c)],
        )
        for ano, a, b, c in [(2024, 10, 25, 45), (2025, 12, 30, 50)]
    }
    for ano, caminho in itr.items():  # trimestre entregue no mês e meio seguinte
        _com_indice(caminho, "itr", ano, [(f"{ano}-03-31", f"{ano}-05-10"),
                                          (f"{ano}-06-30", f"{ano}-08-10"),
                                          (f"{ano}-09-30", f"{ano}-11-10")])  # fmt: skip

    def baixar(ano: int) -> Path:
        if ano not in itr:
            raise OSError("ITR ausente no cenário")
        return itr[ano]

    monkeypatch.setattr(p, "baixar_itr", baixar)
    monkeypatch.setattr("market_engine.date", _Hoje)
    m = MarketEngine.__new__(MarketEngine)
    m.cvm = p
    m._aplicar_referencia = lambda t, d: d.update(
        cd_cvm=9999, especie="ON", classe_ativo="STOCK"
    )
    m._buscar_yfinance = lambda t, d: d.update(preco_atual=100, fonte_preco="yfinance")
    for nome in (
        "_buscar_brapi",
        "_buscar_ifdata",
        "_buscar_cvm_fii",
        "_buscar_rendimento_fii",
        "_buscar_proventos_b3",
        "_buscar_liquidez",
        "_buscar_taxa_real",
        "_contexto_janelas",
        "_aplicar_cache_fundamentos",
        "_salvar_cache_se_valido",
    ):
        monkeypatch.setattr(m, nome, Mock())
    corte = datetime(2025, 7, 1, 2, tzinfo=UTC)  # 30/06 em São Paulo
    dados = m.buscar_dados_ticker_em("TSTA3", corte)
    assert dados["serie_cvm"]["exercicios"][-1]["exercicio"] == 2024
    assert dados["modelo_bpp_proveniencia"]["periodo_referencia"] == "2024-12-31"
    assert dados["ttm_cvm"]["fim"] == "2025-03-31"
    assert dados["ttm_cvm"]["valores"]["lucro_controladores"] == 17
    resultado = ValuationEngine().processar(dados, as_of=corte)
    assert resultado["qualidade"]["exercicios"][-1]["fim"] == "2024-12-31"


def _com_indice(
    caminho: Path, doc: str, ano: int, entregas: list[tuple[str, str]]
) -> None:
    """Acrescenta ao ZIP sintético o índice de entregas (referência, `DT_RECEB`), versão 1."""
    linhas = "".join(f"{CNPJ};{ref};1;{receb}\n" for ref, receb in entregas)
    with zipfile.ZipFile(caminho, "a") as z:
        z.writestr(
            f"{doc}_cia_aberta_{ano}.csv",
            "CNPJ_CIA;DT_REFER;VERSAO;DT_RECEB\n" + linhas,
        )


@pytest.mark.parametrize(
    "dia,hora,minuto,esperado",
    [(20, 15, 0, 2023), (21, 2, 59, 2023), (21, 3, 0, 2024)],
)  # DFP do exercício não civil entregue em 20/05/2024; a de 2023, em 01/03/2024
def test_exercicio_nao_civil_entra_no_dia_local_seguinte_a_entrega(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    dia: int,
    hora: int,
    minuto: int,
    esperado: int,
) -> None:
    p = fonte_anual(tmp_path, monkeypatch)
    pasta = tmp_path / "nao_civil"
    pasta.mkdir()
    bruto = arquivo(pasta, "dfp", 2024, [("2024-02-29", 77)])
    destino = tmp_path / "nao_civil_2024.zip"
    with zipfile.ZipFile(bruto) as entrada, zipfile.ZipFile(destino, "w") as saida:
        for nome in entrada.namelist():
            frame = pd.read_csv(
                io.BytesIO(entrada.read(nome)), sep=";", encoding="latin-1"
            )
            frame["DT_INI_EXERC"] = "2023-03-01"
            saida.writestr(nome, frame.to_csv(sep=";", index=False).encode("latin-1"))
    _com_indice(destino, "dfp", 2024, [("2024-02-29", "2024-05-20")])
    baixar = p.baixar_dfp
    monkeypatch.setattr(
        p, "baixar_dfp", lambda ano: destino if ano == 2024 else baixar(ano)
    )
    monkeypatch.setattr("market_engine.date", _Hoje)
    m = MarketEngine.__new__(MarketEngine)
    m.cvm = p
    dados = de_empresa(
        {"ticker": "TSTA3", "cd_cvm": 9999, "preco_atual": 100, "especie": "ON"}
    )
    assert m._buscar_cvm(
        "TSTA3", dados, as_of=datetime(2024, 5, dia, hora, minuto, tzinfo=UTC)
    )
    assert dados["serie_cvm"]["exercicios"][-1]["exercicio"] == esperado
    assert dados["modelo_bpp_proveniencia"]["periodo_referencia"] == (
        "2023-12-31" if esperado == 2023 else "2024-02-29"
    )
