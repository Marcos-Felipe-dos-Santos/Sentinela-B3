"""F3-8g [e2e]: o DY do FII no motor histórico vem do Informe guardado (ficha FII 1.3).

O Informe Mensal oficial de 2023 (fixture `inf_mensal_fii_2023.zip`, um fundo, 12 meses) é
carregado no banco pelo produtor real (`carga_cvm`), com o mês de dezembro de 2022 montado da
linha oficial de janeiro de 2023 (a janela de 12 meses pede o VP do 13º mês). O motor lê o
Informe remontado em D pelo `CVMFIIProvider` e mede o DY de 12 meses com a conta do
`rendimento_fii.rendimento_12_meses` (DY mensal pela fronteira de `normalizacao.py`), só com
as versões entregues antes do dia de D, sobre o fechamento do COTAHIST antes de D. Sem prova,
o campo fica de fora e o motivo vai a `riscos_dados`. O perfil das ações não muda: o DY dele é
o do bloco da B3 (F3-8h, DD-77).
"""

import io
import sqlite3
import zipfile
from contextlib import closing
from datetime import UTC, date, datetime
from pathlib import Path

import pandas as pd
import pytest
from test_carga_cvm import FII

from fii_engine import FIIEngine
from sentinela.data import rendimento_fii
from sentinela.data.pit import carga_cvm
from sentinela.data.store import migracoes
from sentinela.services import historico

CNPJ = "00.332.266/0001-31"
DEPOIS_DO_INFORME_DE_DEZEMBRO = datetime(
    2024, 1, 20, 15, tzinfo=UTC
)  # entregue 15/01/2024
ANTES_DO_INFORME_DE_DEZEMBRO = datetime(2024, 1, 10, 15, tzinfo=UTC)
PRECO = 80.0


def _informe_de_2022(pasta: Path) -> Path:
    """Dezembro de 2022 com os números oficiais de janeiro de 2023 (só o 13º VP importa)."""
    destino = pasta / "inf_mensal_fii_2022.zip"
    with zipfile.ZipFile(FII) as origem, zipfile.ZipFile(destino, "w") as zf:
        for nome in origem.namelist():
            tabela = pd.read_csv(
                origem.open(nome), sep=";", encoding="latin-1", dtype=str
            )
            linha = tabela[tabela["Data_Referencia"] == "2023-01-01"].copy()
            linha["Data_Referencia"] = "2022-12-01"
            if "Data_Entrega" in linha:
                linha["Data_Entrega"] = "2023-01-16"
            texto = io.StringIO()
            linha.to_csv(texto, sep=";", index=False)
            zf.writestr(
                nome.replace("2023", "2022"), texto.getvalue().encode("latin-1")
            )
    return destino


@pytest.fixture
def conn(tmp_path):
    with closing(sqlite3.connect(":memory:")) as conexao:
        migracoes.aplicar(conexao)
        for arquivo in (FII, _informe_de_2022(tmp_path)):
            carga_cvm.carregar(
                conexao, arquivo, tipo="FII_INFORME", fonte="cvm",
                coleta="2026-11-12T12:00:00+00:00",
            )  # fmt: skip
        yield conexao


def _dados():
    return {
        "ticker": "TSTF11",
        "classe_ativo": "FII",
        "cnpj": CNPJ,
        "preco_atual": PRECO,
        "fonte_preco": historico.FONTE_PRECO,
    }


def _motor(conn, tmp_path, as_of):
    return historico.MotorHistorico(conn, as_of, tmp_path / "pit", pd.DataFrame())


def _esperado():
    """A conta à mão sobre a fixture: Σ DY do mês × VP do mês anterior ÷ preço."""
    with zipfile.ZipFile(FII) as zf:
        c = pd.read_csv(
            zf.open("inf_mensal_fii_complemento_2023.csv"),
            sep=";", encoding="latin-1", dtype=str,
        )  # fmt: skip
    c = c.sort_values("Data_Referencia")
    vp = [float(v) for v in c["Valor_Patrimonial_Cotas"]]
    dy = [float(v) for v in c["Percentual_Dividend_Yield_Mes"]]  # razão no Informe
    anteriores = [vp[0], *vp[:-1]]  # dezembro de 2022 tem o VP de janeiro de 2023
    return sum(d * v for d, v in zip(dy, anteriores, strict=True)) / PRECO


def test_dy_do_fii_pelo_informe_guardado(conn, tmp_path):
    """[e2e] Informe carregado pelo produtor real, remontado em D e lido pelo provedor."""
    dados = _dados()
    _motor(conn, tmp_path, DEPOIS_DO_INFORME_DE_DEZEMBRO)._buscar_rendimento_fii(
        "TSTF11", dados, as_of=DEPOIS_DO_INFORME_DE_DEZEMBRO
    )
    assert dados["dy"] == pytest.approx(_esperado(), rel=1e-12)
    assert 0 < dados["dy"] < rendimento_fii.DY_MAXIMO
    assert dados["proveniencia"]["dy"] == rendimento_fii.normalizacao.proveniencia_dy(
        rendimento_fii.PROVEDOR
    )
    assert dados["_field_sources"] == {"dy": "CVM"}


def test_versao_entregue_depois_de_d_fica_fora(conn, tmp_path):
    """Dezembro de 2023 sai em 15/01/2024: em 10/01 a janela pede novembro de 2022."""
    dados = _dados()
    _motor(conn, tmp_path, ANTES_DO_INFORME_DE_DEZEMBRO)._buscar_rendimento_fii(
        "TSTF11", dados, as_of=ANTES_DO_INFORME_DE_DEZEMBRO
    )
    assert "dy" not in dados
    assert (
        f"DY do FII pelo Informe: {rendimento_fii.MOTIVO_MESES_INCOMPLETOS}"
        in dados["riscos_dados"]
    )


def test_motor_de_fii_passa_do_dy_para_a_lente(conn, tmp_path):
    """Com o DY do Informe, a lente sai pela regra da ficha, não por "DY ausente"."""
    dados = _dados()
    _motor(conn, tmp_path, DEPOIS_DO_INFORME_DE_DEZEMBRO)._buscar_rendimento_fii(
        "TSTF11", dados, as_of=DEPOIS_DO_INFORME_DE_DEZEMBRO
    )
    dados["disponibilidade_por_publicacao"] = (
        True  # como a cascata marca em data passada
    )
    resultado = FIIEngine().analisar(dados, as_of=DEPOIS_DO_INFORME_DE_DEZEMBRO)
    esperado = rendimento_fii.entradas(dados, DEPOIS_DO_INFORME_DE_DEZEMBRO)
    assert isinstance(esperado, rendimento_fii.Abstencao)
    assert esperado.motivo == rendimento_fii.MOTIVO_EVENTOS_INDISPONIVEIS
    assert dados["rendimento_fii_cvm"] == {"abstencao": esperado.motivo}
    assert "DY ausente" not in resultado["metodos_usados"]


def test_preco_fora_do_cotahist_nao_mede(conn, tmp_path):
    dados = {**_dados(), "fonte_preco": "yfinance"}
    _motor(conn, tmp_path, DEPOIS_DO_INFORME_DE_DEZEMBRO)._buscar_rendimento_fii(
        "TSTF11", dados, as_of=DEPOIS_DO_INFORME_DE_DEZEMBRO
    )
    assert "dy" not in dados and "proveniencia" not in dados
    assert dados["riscos_dados"] == [
        f"DY do FII pelo Informe: {rendimento_fii.MOTIVO_PRECO}"
    ]


@pytest.mark.parametrize("preco", [None, 0.0, -1.0])
def test_preco_ausente_ou_nao_positivo_nao_mede(conn, tmp_path, preco):
    dados = {**_dados(), "preco_atual": preco}
    _motor(conn, tmp_path, DEPOIS_DO_INFORME_DE_DEZEMBRO)._buscar_rendimento_fii(
        "TSTF11", dados, as_of=DEPOIS_DO_INFORME_DE_DEZEMBRO
    )
    assert "dy" not in dados
    assert dados["riscos_dados"] == [
        f"DY do FII pelo Informe: {rendimento_fii.MOTIVO_PRECO}"
    ]


def test_informe_abstido_nao_acrescenta_risco(tmp_path):
    with closing(sqlite3.connect(":memory:")) as vazio:
        migracoes.aplicar(vazio)
        motor = _motor(vazio, tmp_path, DEPOIS_DO_INFORME_DE_DEZEMBRO)
        abstido = {**_dados(), "informe_fii": {"abstencao": "x"}}
        motor._dy_do_informe(abstido)
        sem_bloco = _dados()
        motor._dy_do_informe(sem_bloco)
    assert abstido == {**_dados(), "informe_fii": {"abstencao": "x"}}
    assert sem_bloco == _dados()


def test_acao_e_fii_sem_cnpj_ficam_sem_dy(conn, tmp_path):
    motor = _motor(conn, tmp_path, DEPOIS_DO_INFORME_DE_DEZEMBRO)
    acao = {**_dados(), "ticker": "TSTF3", "classe_ativo": "STOCK"}
    sem_cnpj = {k: v for k, v in _dados().items() if k != "cnpj"}
    for dados in (acao, sem_cnpj):
        motor._buscar_rendimento_fii(
            dados["ticker"], dados, as_of=DEPOIS_DO_INFORME_DE_DEZEMBRO
        )
        assert "dy" not in dados and "riscos_dados" not in dados


def _mes(ano, mes, dy="0.01", vp="1"):
    return {
        "Data_Referencia": f"{ano:04d}-{mes:02d}-01",
        "Versao": "1",
        "Data_Entrega": f"{ano + (mes == 12):04d}-{mes % 12 + 1:02d}-10",
        "Percentual_Dividend_Yield_Mes": dy,
        "Valor_Patrimonial_Cotas": vp,
    }


def _ano_ate(ano, mes, **campos):
    """13 meses terminados em (ano, mes), entregues no dia 10 do mês seguinte."""
    meses = []
    for _ in range(13):
        meses.append(_mes(ano, mes, **campos))
        ano, mes = (ano, mes - 1) if mes > 1 else (ano - 1, 12)
    return meses


@pytest.mark.parametrize(
    ("dia", "abstem"),
    [(date(2024, 4, 30), False), (date(2024, 5, 1), True)],
    ids=["tres-meses", "quatro-meses"],
)
def test_idade_do_informe_pela_ficha(dia, abstem):
    medida = rendimento_fii.dy_entregue_ate(_ano_ate(2024, 1), 1.0, dia)
    if abstem:
        assert medida == rendimento_fii.Abstencao(rendimento_fii.MOTIVO_IDADE)
    else:
        assert medida["dy"] == pytest.approx(0.12) and medida["mes_final"] == "2024-01"


@pytest.mark.parametrize(
    ("dy", "preco", "motivo"),
    [
        ("-0.01", 1.0, rendimento_fii.MOTIVO_DY_NEGATIVO),
        ("0.01", 4.0, None),  # 12% / 4 = 3%
        ("0.025", 1.25, None),  # 30% / 1,25 = 24%
        ("0.03125", 1.5, None),  # 37,5% / 1,5 = 25% exatos, no limite
        ("0.025", 1.0, rendimento_fii.MOTIVO_DY_NAO_CONFIAVEL),  # 30%
        ("0", 1.0, None),
    ],
)
def test_faixa_do_dy_do_informe(dy, preco, motivo):
    medida = rendimento_fii.dy_entregue_ate(
        _ano_ate(2024, 1, dy=dy), preco, date(2024, 3, 1)
    )
    if motivo:
        assert medida == rendimento_fii.Abstencao(motivo)
    else:
        assert 0 <= medida["dy"] <= rendimento_fii.DY_MAXIMO


def test_sem_meses_entregues_abstem_sem_idade():
    medida = rendimento_fii.dy_entregue_ate(_ano_ate(2024, 1), 1.0, date(2023, 1, 1))
    assert medida == rendimento_fii.Abstencao(rendimento_fii.MOTIVO_SEM_MESES)
