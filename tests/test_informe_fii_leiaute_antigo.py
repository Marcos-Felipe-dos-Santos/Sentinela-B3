"""F3-8j-fii (BUG-3-42): o provedor do Informe lê o fundo nos dois leiautes da CVM.

O leiaute anterior à Resolução 175 (2016 a 2020) traz o CNPJ do fundo em `CNPJ_Fundo`; o novo,
em `CNPJ_Fundo_Classe`. `cvm_fii_provider._ler_informe` só troca o nome da coluna no antigo.
A fixture `inf_mensal_fii_2017.zip` é o recorte oficial do BUG-3-25.
"""

import io
import shutil
import zipfile
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd

import cvm_fii_provider
from cvm_fii_provider import CVMFIIProvider

FIXTURES = Path(__file__).parent / "fixtures" / "pit_cvm"
INFORME_2017 = FIXTURES / "inf_mensal_fii_2017.zip"
INFORME_2023 = FIXTURES / "inf_mensal_fii_2023.zip"
CNPJ = "00.332.266/0001-31"


def _zip(pasta: Path, colunas: list[str]) -> Path:
    caminho = pasta / "inf.zip"
    texto = io.StringIO()
    pd.DataFrame([dict.fromkeys(colunas, "x")]).to_csv(texto, sep=";", index=False)
    with zipfile.ZipFile(caminho, "w") as zf:
        zf.writestr("inf_mensal_fii_geral_2017.csv", texto.getvalue().encode("latin-1"))
    return caminho


def test_leiaute_antigo_ganha_o_nome_novo(tmp_path):
    lido = cvm_fii_provider._ler_informe(
        _zip(tmp_path, ["CNPJ_Fundo", "Versao"]), "inf_mensal_fii_geral_2017.csv"
    )
    assert list(lido.columns) == ["CNPJ_Fundo_Classe", "Versao"]


def test_leiaute_novo_sai_como_esta(tmp_path):
    lido = cvm_fii_provider._ler_informe(
        _zip(tmp_path, ["CNPJ_Fundo_Classe", "Versao"]), "inf_mensal_fii_geral_2017.csv"
    )
    assert list(lido.columns) == ["CNPJ_Fundo_Classe", "Versao"]


def test_com_as_duas_colunas_vale_a_nova(tmp_path):
    lido = cvm_fii_provider._ler_informe(
        _zip(tmp_path, ["CNPJ_Fundo_Classe", "CNPJ_Fundo"]),
        "inf_mensal_fii_geral_2017.csv",
    )
    assert list(lido.columns) == ["CNPJ_Fundo_Classe", "CNPJ_Fundo"]


def _provedor(tmp_path, ano, fixture):
    """O provedor com só o Informe do `ano`, copiado para `tmp_path` (a proveniência é gravada
    ao lado do ZIP, nunca nas fixtures); os outros anos não existem."""
    pasta = tmp_path / str(ano)
    pasta.mkdir()
    copia = pasta / f"inf_mensal_fii_{ano}.zip"
    shutil.copy(fixture, copia)
    provedor = CVMFIIProvider(cache_dir=str(tmp_path / "cvm_fii"))

    def baixar(pedido):
        if pedido != ano:
            raise FileNotFoundError(pedido)
        return copia

    provedor.baixar_informe = baixar
    return provedor


def test_vpa_oficial_no_leiaute_antigo(tmp_path):
    """`obter_dados_fii` lê dezembro de 2017 (versão 2) no leiaute antigo, com a entrega do
    `geral` na proveniência (o `geral` também passa por `_ler_informe`)."""
    provedor = _provedor(tmp_path, 2017, INFORME_2017)
    dados = provedor.obter_dados_fii(CNPJ, as_of=datetime(2018, 2, 20, 15, tzinfo=UTC))
    assert dados["dt_referencia"] == "2017-12-01"
    assert dados["patrimonio_liquido"] == 483547882.03
    assert dados["cotas_emitidas"] == 2650403
    assert dados["valor_cota"] == 182.443153750581
    assert dados["proveniencia"]["data_entrega"] == "2018-01-18"


def test_rendimentos_nos_dois_leiautes_tem_a_mesma_forma(tmp_path):
    antigo = _provedor(tmp_path, 2017, INFORME_2017)
    novo = _provedor(tmp_path, 2023, INFORME_2023)
    de_2017 = antigo.obter_rendimentos_fii(
        CNPJ, as_of=datetime(2018, 2, 20, 15, tzinfo=UTC)
    )
    de_2023 = novo.obter_rendimentos_fii(
        CNPJ, as_of=datetime(2024, 2, 20, 15, tzinfo=UTC)
    )
    for informe, ano in ((de_2017, "2017"), (de_2023, "2023")):
        assert {r["CNPJ_Fundo_Classe"] for r in informe["registros"]} == {CNPJ}
        assert {r["Data_Referencia"][:4] for r in informe["registros"]} == {ano}
        assert len({r["Data_Referencia"] for r in informe["registros"]}) == 12
        assert all(r.get("Data_Entrega") for r in informe["registros"])
        assert informe["composicoes"]


def test_por_padrao_a_leitura_nao_e_literal(tmp_path):
    """Como `ler_csv_zip`: sem `literal`, a célula vazia vira NaN; com ele, texto vazio."""
    caminho = tmp_path / "inf.zip"
    with zipfile.ZipFile(caminho, "w") as zf:
        zf.writestr("geral.csv", "CNPJ_Fundo;Versao\nx;\n".encode("latin-1"))
    padrao = cvm_fii_provider._ler_informe(caminho, "geral.csv")
    literal = cvm_fii_provider._ler_informe(caminho, "geral.csv", literal=True)
    assert pd.isna(padrao.loc[0, "Versao"]) and literal.loc[0, "Versao"] == ""
