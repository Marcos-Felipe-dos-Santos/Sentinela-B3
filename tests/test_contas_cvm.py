"""Contas da CVM pelo par (código, descrição) (F2A-33; ADR-0003, D20)."""

import json
from io import StringIO
from pathlib import Path

import pandas as pd
import pytest

from sentinela.data import contas_cvm as cc

TABELA = cc.ler_tabela()


def _linhas(*pares):
    return [{"CD_CONTA": c, "DS_CONTA": d, "VL_CONTA": v} for c, d, v in pares]


# Banco no modelo de BBAS3: a 2.03 é "Provisões", o PL está na 2.07.
BANCO = _linhas(
    ("2", "Passivo Total", 2_000.0),
    ("2.03", "Provisões", 50.0),
    ("2.07", "Patrimônio Líquido Consolidado", 190.0),
    ("2.07.02", "Patrimônio Líquido Atribuído aos Não Controladores", 4.0),
)
EMPRESA = _linhas(
    ("2.03", "Patrimônio Líquido Consolidado", 400.0),
    ("2.03.09", "Participação dos Acionistas Não Controladores", 2.0),
    ("3.11", "Lucro/Prejuízo Consolidado do Período", 110.0),
)


# ── aceite ───────────────────────────────────────────────────────────────────


def test_par_reconhecido_devolve_valor_e_linha():
    leitura = cc.ler_conta(EMPRESA, "pl_total", "empresa", TABELA)
    assert leitura == cc.Leitura(400.0, "2.03", "patrimonio liquido consolidado")


def test_mesmo_codigo_com_descricao_de_outra_conta_abstem():
    # Lido como empresa comum (setor desconhecido), o banco não devolve as provisões como PL.
    leitura = cc.ler_conta(BANCO, "pl_total", "empresa", TABELA)
    assert isinstance(leitura, cc.Abstencao)
    assert leitura.motivo == cc.MOTIVO_SEM_CORRESPONDENCIA
    assert "2.03 'provisoes'" in leitura.detalhe
    # No modelo de banco, o PL sai da 2.07.
    assert cc.ler_conta(BANCO, "pl_total", "banco", TABELA) == cc.Leitura(
        190.0, "2.07", "patrimonio liquido consolidado"
    )


def test_descricao_normalizada_ignora_acento_e_caixa():
    assert (
        cc.normalizar_descricao("  PATRIMÔNIO   Líquido\tConsolidado ")
        == "patrimonio liquido consolidado"
    )
    linhas = _linhas(("2.03", "patrimonio LIQUIDO   consolidado", 1.0))
    assert cc.ler_conta(linhas, "pl_total", "empresa", TABELA).valor == 1.0


def test_linha_ausente_e_valor_invalido_tem_motivos_distintos():
    ausente = cc.ler_conta(EMPRESA, "ativo_total", "empresa", TABELA)
    assert ausente == cc.Abstencao(cc.MOTIVO_LINHA_AUSENTE, "ativo_total: 1")
    for invalido in (None, "", "abc", float("nan"), float("inf"), "-inf"):
        linhas = _linhas(("1", "Ativo Total", invalido))
        leitura = cc.ler_conta(linhas, "ativo_total", "empresa", TABELA)
        assert leitura == cc.Abstencao(cc.MOTIVO_VALOR_INVALIDO, "1 'ativo total'"), (
            invalido
        )
    assert cc.MOTIVO_LINHA_AUSENTE != cc.MOTIVO_VALOR_INVALIDO


@pytest.mark.parametrize(
    ("setor", "modelo"),
    [
        ("Bancos", "banco"),
        (" BANCOS ", "banco"),
        ("Seguradoras e Corretoras", "seguradora"),
        ("Emp. Adm. Part. - Seguradoras e Corretoras", "seguradora"),
        ("Emp. Adm. Part. - Bancos", "empresa"),
        ("Intermediação Financeira", "empresa"),
        ("Petróleo e Gás", "empresa"),
        ("", "empresa"),
        (None, "empresa"),
    ],
)
def test_modelo_vem_do_setor(setor, modelo):
    assert cc.modelo_do_setor(setor) == modelo


# ── leitura ──────────────────────────────────────────────────────────────────


def test_codigos_do_campo_sao_tentados_na_ordem_da_tabela():
    # Banco no modelo do ITUB4: PL na 2.08 e lucro na 3.09.
    linhas = _linhas(
        ("2.07", "Passivos sobre Ativos Não Correntes a Venda e Descontinuados", 1.0),
        ("2.08", "Patrimônio Líquido Consolidado", 215.0),
        ("3.09", "Lucro/Prejuízo Consolidado do Período", 45.0),
    )
    assert cc.ler_conta(linhas, "pl_total", "banco", TABELA) == cc.Leitura(
        215.0, "2.08", "patrimonio liquido consolidado"
    )
    assert cc.ler_conta(linhas, "lucro_liquido", "banco", TABELA).codigo == "3.09"


def test_linha_reconhecida_depois_de_divergente_vale():
    linhas = _linhas(
        ("3.11", "Lucro ou Prejuízo antes das Participações", 9.0),
        ("3.09", "Lucro/Prejuízo Consolidado do Período", 45.0),
    )
    assert cc.ler_conta(linhas, "lucro_liquido", "banco", TABELA).valor == 45.0


def test_varias_divergencias_aparecem_no_detalhe():
    linhas = _linhas(("2.07", "Outra coisa", 1.0), ("2.08", "Mais outra", 2.0))
    leitura = cc.ler_conta(linhas, "pl_total", "banco", TABELA)
    assert leitura == cc.Abstencao(
        cc.MOTIVO_SEM_CORRESPONDENCIA, "2.07 'outra coisa'; 2.08 'mais outra'"
    )


def test_numero_em_texto_e_aceito():
    linhas = _linhas(("1", "Ativo Total", " 1223389000.0000000000 "))
    assert (
        cc.ler_conta(linhas, "ativo_total", "empresa", TABELA).valor == 1_223_389_000.0
    )
    linhas = _linhas(("1", "Ativo Total", 0))
    assert cc.ler_conta(linhas, "ativo_total", "empresa", TABELA).valor == 0.0


def test_campo_sem_conta_no_modelo_abstem():
    linhas = _linhas(("3.01", "Receitas de Intermediação Financeira", 1.0))
    leitura = cc.ler_conta(linhas, "receita_liquida", "banco", TABELA)
    assert leitura == cc.Abstencao(
        cc.MOTIVO_CAMPO_FORA_DO_MODELO, "receita_liquida em banco"
    )


def test_modelo_desconhecido_e_erro():
    with pytest.raises(ValueError, match="modelo desconhecido"):
        cc.ler_conta(EMPRESA, "pl_total", "fundo", TABELA)


def test_linha_sem_colunas_nao_quebra():
    leitura = cc.ler_conta([{}], "pl_total", "empresa", TABELA)
    assert leitura.motivo == cc.MOTIVO_LINHA_AUSENTE


# ── tabela ───────────────────────────────────────────────────────────────────

CAMPOS_COMUNS = {
    "ativo_total",
    "passivo_total",
    "pl_total",
    "pl_nao_controladores",
    "lucro_liquido",
    "lucro_controladores",
    "lucro_nao_controladores",
}


def test_tabela_cobre_os_campos_de_cada_modelo():
    por_modelo = {m: {c.campo for c in TABELA if c.modelo == m} for m in cc.MODELOS}
    for modelo in cc.MODELOS:
        assert CAMPOS_COMUNS <= por_modelo[modelo], modelo
    assert {"ativo_circulante", "passivo_circulante", "receita_liquida", "ebit"} <= (
        por_modelo["empresa"] & por_modelo["seguradora"]
    )
    assert "receita_liquida" not in por_modelo["banco"]
    assert "ebit" not in por_modelo["banco"]


def test_tabela_traz_a_evidencia_de_cada_par():
    for conta in TABELA:
        assert conta.arquivo.startswith("dfp_cia_aberta_"), conta
        assert conta.arquivo.endswith(f"_con_{conta.ano}.csv"), conta
        assert 2021 <= conta.ano <= 2025, conta
        assert conta.empresa, conta
        assert conta.descricao == cc.normalizar_descricao(conta.descricao)


def test_2_03_so_e_pl_fora_do_modelo_de_banco():
    pares = {(c.modelo, c.codigo): c.campo for c in TABELA}
    assert pares[("empresa", "2.03")] == "pl_total"
    assert pares[("seguradora", "2.03")] == "pl_total"
    assert ("banco", "2.03") not in pares


def _tabela(tmp_path, linhas):
    caminho = tmp_path / "t.csv"
    caminho.write_text(
        "modelo;campo;codigo;descricao;arquivo;ano;empresa\n"
        + "\n".join(linhas)
        + "\n",
        encoding="utf-8",
    )
    return caminho


def test_tabela_le_os_campos(tmp_path):
    caminho = _tabela(tmp_path, ["banco;pl_total;2.07;patrimonio liquido;a.csv;2025;X"])
    assert cc.ler_tabela(caminho) == (
        cc.Conta("banco", "pl_total", "2.07", "patrimonio liquido", "a.csv", 2025, "X"),
    )


@pytest.mark.parametrize(
    ("linhas", "erro"),
    [
        (
            ["fundo;pl_total;2.07;patrimonio liquido;a.csv;2025;X"],
            "modelo desconhecido",
        ),
        (["banco;pl_total;2.07;Patrimônio Líquido;a.csv;2025;X"], "não normalizada"),
        (
            [
                "banco;pl_total;2.07;patrimonio liquido;a.csv;2025;X",
                "banco;lucro_liquido;2.07;patrimonio liquido;b.csv;2024;Y",
            ],
            "par repetido",
        ),
    ],
)
def test_tabela_invalida_e_recusada(tmp_path, linhas, erro):
    with pytest.raises(ValueError, match=erro):
        cc.ler_tabela(_tabela(tmp_path, linhas))


def test_mesmo_codigo_em_modelos_diferentes_e_permitido(tmp_path):
    caminho = _tabela(
        tmp_path,
        [
            "banco;pl_total;2.07;patrimonio liquido;a.csv;2025;X",
            "empresa;pl_total;2.07;patrimonio liquido;a.csv;2025;X",
        ],
    )
    assert len(cc.ler_tabela(caminho)) == 2


# ── arquivo real (recorte do F2A-32) ─────────────────────────────────────────


def test_recorte_real_da_petrobras_le_pelos_pares():
    fixture = json.loads(
        (
            Path(__file__).parent / "fixtures" / "contratos" / "dfp_2025_petrobras.json"
        ).read_text(encoding="utf-8")
    )
    linhas = []
    for tipo in ("BPA", "BPP", "DRE"):
        df = pd.read_csv(
            StringIO(fixture["membros"][f"dfp_cia_aberta_{tipo}_con_2025.csv"]),
            sep=";",
            dtype=str,
        )
        linhas += df[df["ORDEM_EXERC"] == "ÚLTIMO"].to_dict("records")
    valores = {
        campo: cc.ler_conta(linhas, campo, "empresa", TABELA).valor
        for campo in ("pl_total", "pl_nao_controladores", "lucro_controladores")
    }
    # Valores do arquivo, em milhares de reais (a escala é do chamador).
    assert valores == {
        "pl_total": 417_587_000.0,
        "pl_nao_controladores": 1_801_000.0,
        "lucro_controladores": 110_129_000.0,
    }


def test_mesmo_par_com_valores_diferentes_abstem():
    linhas = _linhas(("1", "Ativo Total", 1.0), ("1", "Ativo Total", 2.0))
    assert cc.ler_conta(linhas, "ativo_total", "empresa", TABELA) == cc.Abstencao(
        cc.MOTIVO_LINHAS_DIVERGENTES, "1 'ativo total'"
    )


def test_mesmo_par_repetido_com_o_mesmo_valor_vale():
    linhas = _linhas(("1", "Ativo Total", 1.0), ("1", "Ativo Total", "1.0"))
    assert cc.ler_conta(linhas, "ativo_total", "empresa", TABELA).valor == 1.0


def test_codigo_com_espacos_e_reconhecido():
    linhas = _linhas((" 1 ", "Ativo Total", 1.0))
    assert cc.ler_conta(linhas, "ativo_total", "empresa", TABELA).valor == 1.0


def test_tabela_do_repositorio_e_lida_uma_vez():
    assert cc.tabela() is cc.tabela()
    assert cc.tabela() == TABELA
