"""BUG-2C-61: decisão Marcos09/11, prova nasce dos documentos, não do teste."""

import zipfile
from datetime import date

import pandas as pd
import pytest

from cvm_provider import CVMProvider
from sentinela.data import series_cvm

CNPJ = "11.111.111/0001-11"


def arquivo(pasta, tipo, ano, periodos, *, cnpj=CNPJ, modelo="empresa", bpp=True):
    """Arquivo CVM sintético com identidade, pares D20 e limites publicados."""
    caminho = pasta / f"{tipo}_{ano}.zip"
    tabelas = {t: [] for t in ("DRE_con", "DVA_con", "BPP_con", "BPA_con")}
    for fim, lucro in periodos:
        inicio = f"{ano}-01-01"
        base = {
            "CNPJ_CIA": cnpj,
            "CD_CVM": 9999,
            "DT_REFER": fim,
            "VERSAO": 1,
            "GRUPO_DFP": "DF Consolidado",
            "ESCALA_MOEDA": "REAL",
            "ORDEM_EXERC": "ÚLTIMO",
            "DT_INI_EXERC": inicio,
            "DT_FIM_EXERC": fim,
        }
        contas = {
            "DRE_con": [
                ("3.11", "Lucro/Prejuízo Consolidado do Período", lucro),
                ("3.01", "Receita de Venda de Bens e/ou Serviços", lucro * 2),
            ],
            "DVA_con": [
                ("7.08.04.02", "Dividendos", lucro / 10),
                ("7.08.04.01", "Juros sobre o Capital Próprio", 0),
            ],
            "BPP_con": [
                (
                    "2.07" if modelo == "banco" else "2.03",
                    "Patrimônio Líquido Consolidado",
                    100,
                )
            ],
            "BPA_con": [("1", "Ativo Total", 200)],
        }
        for tabela, linhas in contas.items():
            for codigo, descricao, valor in linhas:
                tabelas[tabela].append(
                    {
                        **base,
                        "CD_CONTA": codigo,
                        "DS_CONTA": descricao,
                        "VL_CONTA": valor,
                    }
                )
    with zipfile.ZipFile(caminho, "w") as z:
        for tabela, linhas in tabelas.items():
            if tabela == "BPP_con" and not bpp:
                continue
            z.writestr(
                f"{tipo}_cia_aberta_{tabela}_{ano}.csv",
                pd.DataFrame(linhas).to_csv(sep=";", index=False).encode("latin-1"),
            )
    return caminho


def fonte(tmp_path, monkeypatch, **opcoes):
    p = CVMProvider(tmp_path / "cache")
    itr = arquivo(
        tmp_path,
        "itr",
        2025,
        [("2025-03-31", 10), ("2025-06-30", 25), ("2025-09-30", 45)],
        **opcoes,
    )
    dfp = arquivo(tmp_path, "dfp", 2025, [("2025-12-31", 70)], **opcoes)

    def baixar(ano, caminho):
        if ano != 2025:
            raise OSError("sem arquivo neste exercício")
        return caminho

    monkeypatch.setattr(p, "baixar_itr", lambda ano: baixar(ano, itr))
    monkeypatch.setattr(p, "baixar_dfp", lambda ano: baixar(ano, dfp))
    return p


def test_ttm_dos_arquivos_sem_injetar_comparabilidade(tmp_path, monkeypatch):
    p = fonte(tmp_path, monkeypatch)
    acumulados = p.acumulados_ttm(9999, date(2026, 1, 1))
    r = series_cvm.ttm(acumulados, date(2026, 1, 1))
    assert r["valores"]["lucro_controladores"] == 70
    assert r["valores"]["receita_liquida"] == 140
    for a in acumulados:
        prova = a.proveniencia["lucro_controladores"]
        assert "controladores" in prova["perimetro"]
        assert a.dt_refer in prova["evidencia_comparabilidade"]
        assert prova["aviso"] == "reorganização societária no período não é detectada"


@pytest.mark.parametrize("opcoes", [{"bpp": False}, {"modelo": "banco"}])
def test_sem_bpp_compatível_nao_produz_prova(tmp_path, monkeypatch, opcoes):
    p = fonte(tmp_path, monkeypatch, **opcoes)
    a = p.acumulados_ttm(9999, date(2026, 1, 1))
    r = series_cvm.ttm(a, date(2026, 1, 1))
    assert r["valores"]["lucro_controladores"] is None


def test_identidade_diferente_entre_trimestres_nao_combina(tmp_path, monkeypatch):
    p = fonte(tmp_path, monkeypatch)
    outro = tmp_path / "outro"
    outro.mkdir()
    dfp = arquivo(outro, "dfp", 2025, [("2025-12-31", 70)], cnpj="22.222.222/0001-22")
    monkeypatch.setattr(p, "baixar_dfp", lambda ano: dfp)
    r = series_cvm.ttm(p.acumulados_ttm(9999, date(2026, 1, 1)), date(2026, 1, 1))
    assert r["valores"]["lucro_controladores"] is None
