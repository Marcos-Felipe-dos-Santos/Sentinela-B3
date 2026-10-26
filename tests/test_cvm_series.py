"""Série de cinco exercícios da DFP e TTM pelo ITR (F2A-7).

Os arquivos sintéticos seguem os metadados da CVM (`meta_dfp_cia_aberta.txt` e
`meta_itr_cia_aberta.txt`): `DT_INI_EXERC` e `DT_FIM_EXERC` por linha; no ITR do 2º e do 3º
trimestre, a DRE traz o acumulado do exercício e o trimestre isolado, e a DVA só o acumulado.
Os valores esperados saem da aritmética do TTM, nunca do código.
"""

import zipfile
from dataclasses import replace
from datetime import date
from unittest.mock import patch

import pytest

from cvm_provider import CVMProvider
from fii_engine import FIIEngine
from sentinela.data import acoes_cvm, series_cvm
from sentinela.data.acoes_cvm import Composicao
from sentinela.data.series_cvm import Acumulado
from sentinela.reports import rastreabilidade
from tests.test_market_engine import _engine, _historico
from valuation_engine import ValuationEngine

CD_CVM = 9999
CNPJ = "00.000.000/0001-00"


def proveniencia_sintetica() -> dict:
    """A construção dos casos assume explicitamente um mesmo perímetro fictício."""
    return {
        campo: {
            "perimetro": "companhia fictícia consolidada, sem mudança de perímetro",
            "evidencia_comparabilidade": "hipótese declarada dos fluxos sintéticos deste teste",
        }
        for campo in series_cvm.CAMPOS_TTM
    }


def com_perimetro_sintetico(acumulados: list[Acumulado]) -> list[Acumulado]:
    """Acrescenta a premissa do caso sintético sem alterar os dados lidos do ZIP."""
    prova = proveniencia_sintetica()
    return [
        replace(
            a,
            proveniencia={
                c: {**a.proveniencia.get(c, {}), **p} for c, p in prova.items()
            },
        )
        for a in acumulados
    ]


def _acumulado(documento, inicio, fim, versao=1, **valores):
    return Acumulado(
        documento=documento,
        dt_refer=fim,
        versao=versao,
        inicio=date.fromisoformat(inicio),
        fim=date.fromisoformat(fim),
        valores=valores,
        proveniencia=proveniencia_sintetica(),
    )


# Exercício 2025: lucro acumulado 10, 25, 45 e 70 (trimestres 10, 15, 20 e 25).
# Exercício 2026: 12 e 30 (trimestres 12 e 18).
EXERCICIO_2025 = [
    _acumulado("ITR", "2025-01-01", "2025-03-31", lucro_liquido=10.0),
    _acumulado("ITR", "2025-01-01", "2025-06-30", lucro_liquido=25.0),
    _acumulado("ITR", "2025-01-01", "2025-09-30", lucro_liquido=45.0),
    _acumulado("DFP", "2025-01-01", "2025-12-31", lucro_liquido=70.0),
]
EXERCICIO_2026 = [
    _acumulado("ITR", "2026-01-01", "2026-03-31", lucro_liquido=12.0),
    _acumulado("ITR", "2026-01-01", "2026-06-30", lucro_liquido=30.0),
]


def _ind(ano, lucro=100.0):
    return {
        "cvm_dt_refer": f"{ano}-12-31",
        "cvm_versao": "1",
        "lucro_liquido": lucro,
        "lucro_controladores": lucro,
        "patrimonio_liquido": 1_000.0,
        "pl_controladores": 1_000.0,
        "receita_liquida": 500.0,
        "ebit": 150.0,
        "lpa_basico_por_classe": {"ON": [1.0]},
        "composicao_capital": None,
        "composicao_motivo": "sem Composição do Capital no documento do lucro",
        "dividendos": 30.0,
        "jcp": 10.0,
    }


# ── série ────────────────────────────────────────────────────────────────────


def test_serie_tem_ate_cinco_exercicios():
    sete = {ano: _ind(ano) for ano in range(2019, 2026)}
    serie = series_cvm.serie_anual(sete, 2025, especie="ON")
    assert [e["exercicio"] for e in serie] == [2021, 2022, 2023, 2024, 2025]

    tres = {ano: _ind(ano) for ano in (2023, 2024, 2025)}
    serie = series_cvm.serie_anual(tres, 2025, especie="ON")
    assert [e["exercicio"] for e in serie] == [2023, 2024, 2025]
    ultimo = serie[-1]
    assert ultimo["dt_refer"] == "2025-12-31"
    assert ultimo["lucro_liquido"] == 100.0
    assert ultimo["patrimonio_liquido"] == 1_000.0
    assert ultimo["receita_liquida"] == 500.0
    assert ultimo["ebit"] == 150.0
    # LPA do próprio documento: o divulgado da espécie (D19); sem Composição, sem ações nem VPA.
    assert ultimo["lpa"] == 1.0
    assert ultimo["lpa_origem"]["origem"] == "divulgado"
    assert ultimo["acoes"] is None and ultimo["vpa"] is None
    assert ultimo["motivos"]["vpa"] == "sem Composição do Capital no documento do lucro"
    assert (
        ultimo["motivos"]["acoes"] == "sem Composição do Capital no documento do lucro"
    )


def test_ttm_soma_quatro_trimestres():
    resultado = series_cvm.ttm(EXERCICIO_2025 + EXERCICIO_2026, date(2026, 10, 13))
    # 3º e 4º trimestres de 2025 (20 + 25) e 1º e 2º de 2026 (12 + 18).
    assert resultado["valores"]["lucro_liquido"] == 75.0
    assert resultado["inicio"] == "2025-07-01"
    assert resultado["fim"] == "2026-06-30"
    assert [t["valores"]["lucro_liquido"] for t in resultado["trimestres"]] == [
        20.0, 25.0, 12.0, 18.0,
    ]  # fmt: skip
    # Cada documento usado aparece com data e versão.
    assert {"documento": "DFP", "dt_refer": "2025-12-31", "versao": 1} in resultado[
        "documentos"
    ]
    assert {"documento": "ITR", "dt_refer": "2026-06-30", "versao": 1} in resultado[
        "documentos"
    ]


def test_quarto_trimestre_e_dfp_menos_nove_meses():
    trimestres = series_cvm.trimestres(EXERCICIO_2025)
    quarto = trimestres[-1]
    assert (quarto.inicio, quarto.fim) == (date(2025, 10, 1), date(2025, 12, 31))
    assert quarto.valores["lucro_liquido"] == 70.0 - 45.0
    assert [d.documento for d in quarto.documentos] == ["ITR", "DFP"]
    # Até o fim de 2025, o TTM é o próprio exercício.
    assert (
        series_cvm.ttm(EXERCICIO_2025, date(2026, 1, 15))["valores"]["lucro_liquido"]
        == 70.0
    )


def test_ttm_usa_a_versao_mais_recente():
    reapresentado = _acumulado(
        "ITR", "2026-01-01", "2026-06-30", versao=2, lucro_liquido=40.0
    )
    resultado = series_cvm.ttm(
        EXERCICIO_2025 + EXERCICIO_2026 + [reapresentado], date(2026, 10, 13)
    )
    assert resultado["valores"]["lucro_liquido"] == 20.0 + 25.0 + 12.0 + 28.0
    assert {"documento": "ITR", "dt_refer": "2026-06-30", "versao": 2} in resultado[
        "documentos"
    ]
    assert {"documento": "ITR", "dt_refer": "2026-06-30", "versao": 1} not in resultado[
        "documentos"
    ]


class _Hoje(date):
    @classmethod
    def today(cls):
        return cls(2026, 10, 13)


class _CVMSemDfpDoUltimoAno:
    """A DFP de 2025 não existe; a série só tem 2023 e 2024."""

    def calcular_indicadores(self, cd_cvm, anos=1, **kwargs):
        return {}

    def indicadores_da_serie(self, cd_cvm, ano_final, modelo="empresa"):
        assert ano_final == 2025
        return {2023: _ind(2023, lucro=80.0), 2024: _ind(2024, lucro=90.0)}

    def acumulados_ttm(self, cd_cvm, data_referencia, modelo="empresa"):
        return EXERCICIO_2025 + EXERCICIO_2026


def test_exercicio_antigo_nao_vira_corrente(monkeypatch):
    # Puro: exercício depois do de referência fica fora da série.
    serie = series_cvm.serie_anual({2025: _ind(2025), 2026: _ind(2026)}, 2025)
    assert [e["exercicio"] for e in serie] == [2025]

    # Cascata: sem a DFP do último ano, a série mostra 2023 e 2024, e nenhum campo dos
    # métodos sai deles.
    monkeypatch.setattr("market_engine.date", _Hoje)
    engine = _engine(
        monkeypatch,
        info={"currentPrice": 20.0},
        historico=_historico(20.0),
        cvm=_CVMSemDfpDoUltimoAno(),
    )
    dados = engine.buscar_dados_ticker("PETR4")  # ticker do mapa público
    assert [e["exercicio"] for e in dados["serie_cvm"]["exercicios"]] == [2023, 2024]
    assert dados["cvm_disponivel"] is False
    for campo in ("lpa", "lucro_liquido", "patrimonio_liquido", "receita_liquida"):
        assert dados.get(campo) is None, campo
    assert dados["ttm_cvm"]["valores"]["lucro_liquido"] == 75.0


def test_proventos_declaram_competencia(monkeypatch):
    serie = series_cvm.serie_anual({2025: _ind(2025)}, 2025)
    exercicio = serie[0]
    assert (exercicio["dividendos"], exercicio["jcp"], exercicio["proventos"]) == (
        30.0, 10.0, 40.0,
    )  # fmt: skip
    assert "competência" in exercicio["proventos_base"]
    assert "data-ex" in exercicio["proventos_base"]

    ttm = series_cvm.ttm(
        [
            _acumulado("ITR", "2025-01-01", "2025-03-31", dividendos=1.0, jcp=0.0),
            _acumulado("ITR", "2025-01-01", "2025-06-30", dividendos=3.0, jcp=1.0),
            _acumulado("ITR", "2025-01-01", "2025-09-30", dividendos=3.0, jcp=2.0),
            _acumulado("DFP", "2025-01-01", "2025-12-31", dividendos=7.0, jcp=3.0),
        ],
        date(2026, 2, 1),
    )
    assert ttm["valores"]["proventos"] == 10.0
    assert ttm["proventos_base"] == series_cvm.COMPETENCIA

    # O relatório do F1-12 declara a competência.
    dados = {
        "ticker": "TST3",
        "preco_atual": 100.0,
        "roe": 0.15,
        "pl": 10.0,
        "pvp": 1.5,
        "dy": 0.08,
        "fonte_preco": "yfinance",
        "fonte_fundamentos": "CVM",
        "serie_cvm": {"exercicios": serie, "proventos_base": series_cvm.COMPETENCIA},
        "ttm_cvm": ttm,
    }
    with (
        patch("fii_engine.get_selic_atual", return_value=0.145),
    ):
        contexto = rastreabilidade.construir_contexto(
            dados, False, date(2026, 10, 13), ValuationEngine(), FIIEngine()
        )
    fontes = dict(contexto["fontes"])
    serie_texto = next(v for k, v in fontes.items() if k.startswith("Série da CVM"))
    assert "2025" in serie_texto and series_cvm.COMPETENCIA in serie_texto
    assert "2025-01-01 a 2025-12-31" in fontes["Últimos doze meses da CVM"]
    assert series_cvm.COMPETENCIA in fontes["Últimos doze meses da CVM"]


# ── casos de borda do módulo puro ────────────────────────────────────────────


def test_ttm_com_menos_de_quatro_trimestres_se_abstem():
    resultado = series_cvm.ttm(EXERCICIO_2025, date(2025, 11, 1))
    assert resultado == series_cvm.Abstencao(series_cvm.MOTIVO_MENOS_DE_QUATRO)


def test_trimestre_faltando_quebra_a_contiguidade():
    # Sem o ITR de 30/06/2025, o intervalo de março a setembro não é trimestre.
    sem_junho = [a for a in EXERCICIO_2025 if a.fim != date(2025, 6, 30)]
    trimestres = series_cvm.trimestres(sem_junho + EXERCICIO_2026)
    assert [(t.inicio.isoformat(), t.fim.isoformat()) for t in trimestres] == [
        ("2025-01-01", "2025-03-31"),
        ("2025-10-01", "2025-12-31"),
        ("2026-01-01", "2026-03-31"),
        ("2026-04-01", "2026-06-30"),
    ]
    resultado = series_cvm.ttm(sem_junho + EXERCICIO_2026, date(2026, 10, 13))
    assert resultado == series_cvm.Abstencao(series_cvm.MOTIVO_NAO_CONTIGUOS)


def test_campo_ausente_num_documento_abstem_so_o_campo():
    acumulados = [
        _acumulado(
            "ITR", "2025-01-01", "2025-03-31", lucro_liquido=1.0, receita_liquida=10.0
        ),
        _acumulado(
            "ITR", "2025-01-01", "2025-06-30", lucro_liquido=2.0, receita_liquida=None
        ),
        _acumulado(
            "ITR", "2025-01-01", "2025-09-30", lucro_liquido=3.0, receita_liquida=30.0
        ),
        _acumulado(
            "DFP", "2025-01-01", "2025-12-31", lucro_liquido=4.0, receita_liquida=40.0
        ),
    ]
    resultado = series_cvm.ttm(acumulados, date(2026, 1, 1))
    assert resultado["valores"]["lucro_liquido"] == 4.0
    assert resultado["valores"]["receita_liquida"] is None
    assert resultado["motivos"]["receita_liquida"] == series_cvm.MOTIVO_CAMPO_AUSENTE
    assert "lucro_liquido" not in resultado["motivos"]
    assert resultado["valores"]["proventos"] is None


def test_ttm_abstem_quando_um_documento_se_abstem():
    # F2B-37 (BUG-2A-10): o lucro dos controladores abstido num documento (decisão 7.2)
    # abstém o TTM do campo, com o motivo daquele documento.
    motivo = "lucro dos controladores não separado no documento, com não controladores no balanço"
    acumulados = [
        _acumulado(
            "ITR",
            "2025-01-01",
            "2025-03-31",
            lucro_liquido=1.0,
            lucro_controladores=1.0,
        ),
        _acumulado(
            "ITR",
            "2025-01-01",
            "2025-06-30",
            lucro_liquido=2.0,
            lucro_controladores=None,
        ),
        _acumulado(
            "ITR",
            "2025-01-01",
            "2025-09-30",
            lucro_liquido=3.0,
            lucro_controladores=3.0,
        ),
        _acumulado(
            "DFP",
            "2025-01-01",
            "2025-12-31",
            lucro_liquido=4.0,
            lucro_controladores=4.0,
        ),
    ]
    acumulados[1] = Acumulado(
        **{**acumulados[1].__dict__, "motivos": {"lucro_controladores": motivo}}
    )
    resultado = series_cvm.ttm(acumulados, date(2026, 1, 1))
    assert resultado["valores"]["lucro_liquido"] == 4.0
    assert resultado["valores"]["lucro_controladores"] is None
    assert motivo in resultado["motivos"]["lucro_controladores"]


def test_trimestre_depois_da_data_de_referencia_fica_de_fora():
    resultado = series_cvm.ttm(EXERCICIO_2025 + EXERCICIO_2026, date(2026, 6, 29))
    assert resultado["fim"] == "2026-03-31"
    assert resultado["valores"]["lucro_liquido"] == 15.0 + 20.0 + 25.0 + 12.0


def test_exercicio_fora_do_ano_civil():
    # Exercício de março a fevereiro: o 1º trimestre termina em maio.
    acumulados = [
        _acumulado("ITR", "2025-03-01", "2025-05-31", lucro_liquido=1.0),
        _acumulado("ITR", "2025-03-01", "2025-08-31", lucro_liquido=3.0),
        _acumulado("ITR", "2025-03-01", "2025-11-30", lucro_liquido=6.0),
        _acumulado("DFP", "2025-03-01", "2026-02-28", lucro_liquido=10.0),
    ]
    resultado = series_cvm.ttm(acumulados, date(2026, 6, 1))
    assert resultado["valores"]["lucro_liquido"] == 10.0
    assert resultado["inicio"] == "2025-03-01"


def test_proventos_com_uma_rubrica_preservam_o_informado():
    assert series_cvm.proventos(1.0, None, motivos={"jcp": "linha ausente no documento"}) == 1.0
    assert series_cvm.proventos(None, 1.0, motivos={"dividendos": "linha ausente no documento"}) == 1.0
    assert series_cvm.proventos(0.0, 0.0) == 0.0


def test_unit_soma_os_lpas_das_especies_no_exercicio():
    ind = {**_ind(2025), "lpa_basico_por_classe": {"ON": [1.0], "PN": [1.5]}}
    serie = series_cvm.serie_anual(
        {2025: ind}, 2025, eh_unit=True, acoes_por_unit={"ON": 1, "PN": 2}
    )
    assert serie[0]["lpa"] == 1.0 + 2 * 1.5
    assert serie[0]["lpa_origem"]["origem"] == "unit"


def test_lpa_incoerente_se_abstem_no_exercicio():
    ind = {**_ind(2025, lucro=-5.0), "lpa_basico_por_classe": {"ON": [1.0]}}
    exercicio = series_cvm.serie_anual({2025: ind}, 2025, especie="ON")[0]
    assert exercicio["lpa"] is None
    assert exercicio["lpa_origem"] is None
    assert "sinal oposto" in exercicio["motivos"]["lpa"]


def test_serie_nao_usa_a_confirmacao_do_yfinance():
    # Ficha 1.1, 7.7: a `sharesOutstanding` é de hoje e não confirma exercícios passados; sem
    # o lucro dos controladores, a escala da série segue indeterminada (D17).
    composicao = Composicao(
        on=1_000.0, pn=0.0, tesouraria_on=0.0, tesouraria_pn=0.0,
        tesouraria_total=0.0, dt_refer="2025-12-31", versao="1",
    )  # fmt: skip
    ind = {
        **_ind(2025),
        "lucro_controladores": None,
        "composicao_capital": composicao,
        "composicao_motivo": None,
    }
    exercicio = series_cvm.serie_anual({2025: ind}, 2025, especie="ON")[0]
    assert exercicio["acoes"] is None
    assert exercicio["vpa"] is None
    assert exercicio["motivos"]["vpa"] == acoes_cvm.MOTIVO_ESCALA


# ── provedor: DVA e ITR sintéticos ───────────────────────────────────────────

COLUNAS = [
    "CNPJ_CIA", "DT_REFER", "VERSAO", "CD_CVM", "GRUPO_DFP", "ESCALA_MOEDA", "ORDEM_EXERC",
    "DT_INI_EXERC", "DT_FIM_EXERC", "CD_CONTA", "DS_CONTA", "VL_CONTA",
]  # fmt: skip


def _zip(caminho, prefixo, ano, dre, dva):
    def csv(linhas):
        corpo = [
            [CNPJ, dt, v, CD_CVM, "DF Consolidado", "MIL", ordem, ini, fim, c, d, x]
            for dt, v, ordem, ini, fim, c, d, x in linhas
        ]
        texto = (
            ";".join(COLUNAS)
            + "\n"
            + "\n".join(";".join(map(str, linha)) for linha in corpo)
        )
        return texto.encode("latin-1")

    with zipfile.ZipFile(caminho, "w") as zf:
        zf.writestr(f"{prefixo}_cia_aberta_DRE_con_{ano}.csv", csv(dre))
        zf.writestr(f"{prefixo}_cia_aberta_DVA_con_{ano}.csv", csv(dva))
    return caminho


def _linhas_itr(dt, ini_acum, ini_tri, lucro_acum, lucro_tri, div_acum, versao="1"):
    return (
        [
            (dt, versao, "ÚLTIMO", ini_acum, dt, "3.11", "Lucro/Prejuízo Consolidado do Período", lucro_acum),
            (dt, versao, "ÚLTIMO", ini_tri, dt, "3.11", "Lucro/Prejuízo Consolidado do Período", lucro_tri),
            (dt, versao, "PENÚLTIMO", "2024-01-01", "2024-06-30", "3.11", "Lucro/Prejuízo Consolidado do Período", 999),
        ],
        [
            (dt, versao, "ÚLTIMO", ini_acum, dt, "7.08.04.01", "Juros sobre o Capital Próprio", 0),
            (dt, versao, "ÚLTIMO", ini_acum, dt, "7.08.04.02", "Dividendos", div_acum),
        ],
    )  # fmt: skip


def test_provedor_separa_o_acumulado_do_trimestre_no_itr(tmp_path):
    provider = CVMProvider(cache_dir=str(tmp_path / "cache"))
    dre_q1, dva_q1 = _linhas_itr("2025-03-31", "2025-01-01", "2025-01-01", 10, 10, 1)
    dre_q2, dva_q2 = _linhas_itr("2025-06-30", "2025-01-01", "2025-04-01", 25, 15, 2)
    caminho = _zip(tmp_path / "itr.zip", "itr", 2025, dre_q1 + dre_q2, dva_q1 + dva_q2)
    acumulados = provider._acumulados_do_arquivo(caminho, "ITR", CD_CVM, "empresa")
    por_fim = {a.fim.isoformat(): a for a in acumulados}
    junho = por_fim["2025-06-30"]
    # O acumulado de seis meses (escala MIL), não o trimestre isolado.
    assert junho.inicio == date(2025, 1, 1)
    assert junho.valores["lucro_liquido"] == 25_000.0
    assert junho.valores["dividendos"] == 2_000.0
    assert junho.valores["jcp"] == 0.0
    assert (junho.documento, junho.dt_refer, junho.versao) == ("ITR", "2025-06-30", 1)


def test_provedor_le_os_proventos_da_dva_pela_tabela(tmp_path):
    provider = CVMProvider(cache_dir=str(tmp_path / "cache"))
    dva = [
        ("2025-12-31", "1", "ÚLTIMO", "2025-01-01", "2025-12-31", "7.08.04.01", "Juros sobre o Capital Próprio", 3),
        ("2025-12-31", "1", "ÚLTIMO", "2025-01-01", "2025-12-31", "7.08.04.02", "Outra Conta", 7),
    ]  # fmt: skip
    caminho = _zip(tmp_path / "dfp.zip", "dfp", 2025, [], dva)
    proventos = provider.proventos_do_documento(caminho, CD_CVM, "2025-12-31", "1")
    assert proventos["jcp"] == 3_000.0
    # Código com outra descrição: abstenção, nunca o valor de outra conta.
    assert proventos["dividendos"] is None
    assert "sem correspondência" in proventos["proventos_motivos"]["dividendos"]


def test_provedor_sem_dva_registra_o_motivo(tmp_path):
    provider = CVMProvider(cache_dir=str(tmp_path / "cache"))
    caminho = tmp_path / "dfp.zip"
    with zipfile.ZipFile(caminho, "w") as zf:
        zf.writestr(
            "dfp_cia_aberta_DRE_con_2025.csv", ";".join(COLUNAS).encode("latin-1")
        )
    proventos = provider.proventos_do_documento(caminho, CD_CVM, "2025-12-31", "1")
    assert proventos["dividendos"] is None and proventos["jcp"] is None
    assert proventos["proventos_motivos"]["dividendos"].startswith("DVA indisponível")


def test_exercicio_com_composicao_traz_o_documento_inteiro():
    composicao = Composicao(
        on=700, pn=400, tesouraria_on=60, tesouraria_pn=40, tesouraria_total=100,
        dt_refer="2025-12-31", versao="2",
    )  # fmt: skip
    ind = {
        **_ind(2025, lucro=2_000_000.0),
        "cvm_versao": "2",
        "lucro_liquido": 2_100_000.0,
        "patrimonio_liquido": 11_000_000.0,
        "pl_controladores": 10_000_000.0,
        "lpa_basico_por_classe": {"ON": [2.0]},
        "composicao_capital": composicao,
        "composicao_motivo": None,
    }
    exercicio = series_cvm.serie_anual({2025: ind}, 2025, especie="ON", classe="ON")[0]
    # 1.000 mil ações (700 + 400 − 100, escala MIL pelo LPA divulgado); VPA = 10 mi ÷ 1 mi.
    assert exercicio == {
        "exercicio": 2025,
        "dt_refer": "2025-12-31",
        "versao": "2",
        "lucro_liquido": 2_100_000.0,
        "lucro_controladores": 2_000_000.0,
        "patrimonio_liquido": 11_000_000.0,
        "pl_controladores": 10_000_000.0,
        "receita_liquida": 500.0,
        "ebit": 150.0,
        "acoes": 1_000_000.0,
        "lpa": 2.0,
        "lpa_origem": {"origem": "divulgado", "classe": "ON", "notas": []},
        "vpa": 10.0,
        "motivos": {},
        "dividendos": 30.0,
        "jcp": 10.0,
        "proventos": 40.0,
        "proventos_base": series_cvm.COMPETENCIA,
    }

    # Sem divulgado da espécie, o recalculado (lucro dos controladores ÷ ações), com a marca.
    pn = series_cvm.serie_anual({2025: ind}, 2025, especie="PN")[0]
    assert pn["lpa"] == 2.0
    assert pn["lpa_origem"]["origem"] == "recalculado"

    # PNA com mais de uma classe preferencial: sem o divulgado da classe, abstém-se.
    pna = series_cvm.serie_anual(
        {2025: ind},
        2025,
        especie="PN",
        classe="PNA",
        classes_preferenciais=["PNA", "PNB"],
    )[0]
    assert pna["lpa"] is None
    assert pna["motivos"]["lpa"] == acoes_cvm.MOTIVO_CLASSES_PREFERENCIAIS

    # Sem PL dos controladores, o VPA se abstém e as ações seguem.
    sem_pl = series_cvm.serie_anual(
        {2025: {**ind, "pl_controladores": None}}, 2025, especie="ON"
    )[0]
    assert sem_pl["acoes"] == 1_000_000.0
    assert sem_pl["vpa"] is None
    assert sem_pl["motivos"] == {"vpa": acoes_cvm.MOTIVO_ROE_SEM_PL}


def test_versao_mais_recente_vale_em_qualquer_ordem():
    v2 = _acumulado("ITR", "2026-01-01", "2026-03-31", versao=2, lucro_liquido=2.0)
    v1 = _acumulado("ITR", "2026-01-01", "2026-03-31", versao=1, lucro_liquido=1.0)
    assert series_cvm.mais_recentes([v2, v1]) == [v2]
    assert series_cvm.mais_recentes([v1, v2]) == [v2]


def test_trimestre_encerrado_na_data_de_referencia_entra():
    resultado = series_cvm.ttm(EXERCICIO_2025 + EXERCICIO_2026, date(2026, 6, 30))
    assert resultado["fim"] == "2026-06-30"
    assert resultado["trimestres"][-1] == {
        "inicio": "2026-04-01",
        "fim": "2026-06-30",
        "valores": {"lucro_liquido": 18.0},
        "documentos": [
            {"documento": "ITR", "dt_refer": "2026-03-31", "versao": 1},
            {"documento": "ITR", "dt_refer": "2026-06-30", "versao": 1},
        ],
    }


def test_unit_com_componente_sem_divulgado_usa_o_recalculado_por_acao():
    composicao = Composicao(
        on=700, pn=400, tesouraria_on=60, tesouraria_pn=40, tesouraria_total=100,
        dt_refer="2025-12-31", versao="1",
    )  # fmt: skip
    ind = {
        **_ind(2025, lucro=2_000_000.0),
        "lpa_basico_por_classe": {"ON": [2.0]},
        "composicao_capital": composicao,
        "composicao_motivo": None,
    }
    exercicio = series_cvm.serie_anual(
        {2025: ind}, 2025, eh_unit=True, acoes_por_unit={"ON": 1, "PN": 2}
    )[0]
    # ON divulgado (2,0) + 2 × PN recalculado por ação (2 mi ÷ 1 mi = 2,0); VPA por unit.
    assert exercicio["lpa"] == 2.0 + 2 * 2.0
    assert exercicio["lpa_origem"]["componentes"]["PN"]["origem"] == "recalculado"
    assert exercicio["vpa"] == 1_000.0 / 1_000_000.0 * 3


def _itr(dt, ini, lucro):
    return (
        [
            (
                dt,
                "1",
                "ÚLTIMO",
                ini,
                dt,
                "3.11",
                "Lucro/Prejuízo Consolidado do Período",
                lucro,
            )
        ],
        [],
    )


def test_ttm_em_fevereiro_usa_o_itr_de_dois_anos_antes(tmp_path):
    # Em 15/02/2027 a DFP 2026 ainda não saiu: o TTM é o 4º trimestre de 2025 (DFP 2025 menos
    # o ITR de nove meses de 2025) e os três primeiros de 2026.
    provider = CVMProvider(cache_dir=str(tmp_path / "cache"))
    itr_2025 = [
        _itr(f"2025-{m}", "2025-01-01", v)
        for m, v in (("03-31", 10), ("06-30", 25), ("09-30", 45))
    ]
    itr_2026 = [
        _itr(f"2026-{m}", "2026-01-01", v)
        for m, v in (("03-31", 12), ("06-30", 30), ("09-30", 50))
    ]
    arquivos = {
        ("itr", 2025): _zip(tmp_path / "itr_2025.zip", "itr", 2025, [x for d, _ in itr_2025 for x in d], []),
        ("itr", 2026): _zip(tmp_path / "itr_2026.zip", "itr", 2026, [x for d, _ in itr_2026 for x in d], []),
        ("dfp", 2025): _zip(
            tmp_path / "dfp_2025.zip", "dfp", 2025,
            [("2025-12-31", "1", "ÚLTIMO", "2025-01-01", "2025-12-31", "3.11",
              "Lucro/Prejuízo Consolidado do Período", 70)],
            [],
        ),
    }  # fmt: skip
    pedidos = []

    def baixar(prefixo):
        def _baixar(ano):
            pedidos.append((prefixo, ano))
            if (prefixo, ano) not in arquivos:
                raise FileNotFoundError(f"{prefixo}_{ano}")
            return arquivos[(prefixo, ano)]

        return _baixar

    provider.baixar_itr = baixar("itr")
    provider.baixar_dfp = baixar("dfp")
    data = date(2027, 2, 15)
    resultado = series_cvm.ttm(com_perimetro_sintetico(provider.acumulados_ttm(CD_CVM, data)), data)
    assert ("itr", 2025) in pedidos
    assert (resultado["inicio"], resultado["fim"]) == ("2025-10-01", "2026-09-30")
    # (70 − 45) + 12 + 18 + 20, em mil.
    assert resultado["valores"]["lucro_liquido"] == (25 + 12 + 18 + 20) * 1_000.0


def test_motivo_dos_proventos_chega_a_serie():
    ind = {
        **_ind(2025),
        "dividendos": None,
        "proventos_motivos": {"dividendos": "DVA indisponível (x)"},
    }
    exercicio = series_cvm.serie_anual({2025: ind}, 2025, especie="ON")[0]
    assert exercicio["dividendos"] is None and exercicio["proventos"] is None
    assert exercicio["motivos"]["dividendos"] == "DVA indisponível (x)"
    assert (
        exercicio["motivos"]["vpa"] == "sem Composição do Capital no documento do lucro"
    )


def test_indicadores_da_serie_juntam_os_proventos_de_cada_exercicio(
    tmp_path, monkeypatch
):
    provider = CVMProvider(cache_dir=str(tmp_path / "cache"))
    dva = [
        ("2025-12-31", "1", "ÚLTIMO", "2025-01-01", "2025-12-31", "7.08.04.01", "Juros sobre o Capital Próprio", 3),
        ("2025-12-31", "1", "ÚLTIMO", "2025-01-01", "2025-12-31", "7.08.04.02", "Dividendos", 7),
    ]  # fmt: skip
    caminho = _zip(tmp_path / "dfp_2025.zip", "dfp", 2025, [], dva)
    chamadas = []

    def calcular(cd_cvm, anos=5, modelo="empresa", ano_final=None):
        chamadas.append((cd_cvm, anos, modelo, ano_final))
        return {2025: {"cvm_dt_refer": "2025-12-31", "cvm_versao": "1"}}

    monkeypatch.setattr(provider, "calcular_indicadores", calcular)
    monkeypatch.setattr(provider, "baixar_dfp", lambda ano: caminho)
    indicadores = provider.indicadores_da_serie(CD_CVM, 2025)
    assert chamadas == [(CD_CVM, 5, "empresa", 2025)]
    assert indicadores[2025]["dividendos"] == 7_000.0
    assert indicadores[2025]["jcp"] == 3_000.0
    assert indicadores[2025]["proventos_motivos"] == {}


def test_ttm_le_o_balanco_do_mesmo_documento_para_a_reserva(tmp_path):
    # F2B-37 (decisão 7.2): 3.11.01 e 3.11.02 zeradas. No ITR de junho, o balanço do mesmo
    # documento tem não controladores: abstenção. No de março (versão 1), não tem: reserva pelo
    # lucro total. A versão 2 do balanço de março, com não controladores, não vale para a 1.
    provider = CVMProvider(cache_dir=str(tmp_path / "cache"))
    consolidado = "Lucro/Prejuízo Consolidado do Período"

    def _dre(dt):
        return [
            (dt, "1", "ÚLTIMO", "2025-01-01", dt, "3.11", consolidado, 100),
            (dt, "1", "ÚLTIMO", "2025-01-01", dt, "3.11.01",
             "Atribuído a Sócios da Empresa Controladora", 0),
            (dt, "1", "ÚLTIMO", "2025-01-01", dt, "3.11.02",
             "Atribuído a Sócios Não Controladores", 0),
        ]  # fmt: skip

    nao_controladores = "Participação dos Acionistas Não Controladores"
    bpp = [
        ("2025-03-31", "1", "ÚLTIMO", "2025-03-31", "2025-03-31", "2.03.09", nao_controladores, 0),
        ("2025-03-31", "2", "ÚLTIMO", "2025-03-31", "2025-03-31", "2.03.09", nao_controladores, 50),
        ("2025-06-30", "1", "ÚLTIMO", "2025-06-30", "2025-06-30", "2.03.09", nao_controladores, 50),
    ]  # fmt: skip
    caminho = _zip(
        tmp_path / "itr.zip", "itr", 2025, _dre("2025-03-31") + _dre("2025-06-30"), []
    )
    corpo = [
        [CNPJ, dt, v, CD_CVM, "DF Consolidado", "MIL", ordem, ini, fim, c, d, x]
        for dt, v, ordem, ini, fim, c, d, x in bpp
    ]
    texto = (
        ";".join(COLUNAS)
        + "\n"
        + "\n".join(";".join(map(str, linha)) for linha in corpo)
    )
    with zipfile.ZipFile(caminho, "a") as zf:
        zf.writestr("itr_cia_aberta_BPP_con_2025.csv", texto.encode("latin-1"))
    marco, junho = provider._acumulados_do_arquivo(caminho, "ITR", CD_CVM, "empresa")
    assert marco.valores["lucro_controladores"] == 100_000.0
    assert marco.motivos == {"dividendos": "DVA indisponível no documento", "jcp": "DVA indisponível no documento"}
    assert junho.valores["lucro_controladores"] is None
    assert "não controladores no balanço" in junho.motivos["lucro_controladores"]


def test_rubrica_ausente_difere_de_dva_indisponivel_ou_conta_invalida():
    assert series_cvm.proventos(5, None, motivos={"jcp": "linha ausente no documento jcp"}) == 5
    for motivo in ("DVA indisponível", "sem correspondência", "valor inválido"):
        assert series_cvm.proventos(5, None, motivos={"jcp": motivo}) is None
    assert series_cvm.proventos(None, None) is None


def test_ttm_preserva_proventos_com_uma_rubrica_no_arquivo_real_sintetico(tmp_path):
    for campo, codigo, descricao in (
        ("jcp", "7.08.04.01", "Juros sobre o Capital Próprio"),
        ("dividendos", "7.08.04.02", "Dividendos"),
    ):
        dre, dva = [], []
        for trimestre, fim in enumerate(("2025-03-31", "2025-06-30", "2025-09-30", "2025-12-31"), 1):
            dre.append((fim, "1", "ÚLTIMO", "2025-01-01", fim, "3.11", "Lucro/Prejuízo Consolidado do Período", 10 * trimestre))
            dva.append((fim, "1", "ÚLTIMO", "2025-01-01", fim, codigo, descricao, trimestre))
        itr = _zip(tmp_path / f"itr_{campo}.zip", "itr", 2025, dre[:3], dva[:3])
        dfp = _zip(tmp_path / f"dfp_{campo}.zip", "dfp", 2025, dre[3:], dva[3:])
        provider = CVMProvider(cache_dir=str(tmp_path / "cache"))
        acumulados = provider._acumulados_do_arquivo(itr, "ITR", CD_CVM, "empresa")
        acumulados += provider._acumulados_do_arquivo(dfp, "DFP", CD_CVM, "empresa")
        resultado = series_cvm.ttm(com_perimetro_sintetico(acumulados), date(2026, 1, 1))
        assert resultado["valores"][campo] == 4000
        assert resultado["valores"]["proventos"] == 4000


@pytest.mark.parametrize(
    "inicio,fim,meses",
    [
        (date(2026, 1, 1), date(2026, 3, 31), 3),
        (date(2024, 1, 1), date(2024, 3, 31), 3),
        (date(2023, 12, 1), date(2024, 2, 29), 3),
        (date(2024, 12, 1), date(2025, 2, 28), 3),
        (date(2024, 1, 1), date(2024, 12, 31), 12),
        (date(2023, 3, 1), date(2024, 2, 29), 12),
        (date(2024, 3, 1), date(2025, 2, 28), 12),
        (date(2026, 1, 31), date(2026, 3, 1), 0),
        (date(2026, 1, 2), date(2026, 3, 31), 0),
        (date(2026, 1, 1), date(2026, 3, 30), 0),
        (date(2023, 12, 1), date(2024, 2, 28), 0),
        (date(2026, 3, 1), date(2026, 2, 28), 0),
        (date(2026, 1, 1), date(2025, 12, 31), 0),
    ],
)
def test_meses_declarados_exigem_limites_de_calendario(
    inicio: date, fim: date, meses: int
) -> None:
    """F2C-17: mês inteiro pelo calendário, inclusive fevereiro bissexto e ano não civil."""
    assert series_cvm._meses(inicio, fim) == meses


def test_periodo_parcial_nao_produz_trimestre() -> None:
    documento = series_cvm.Acumulado(
        "ITR", "2026-03-01", 1, date(2026, 1, 31), date(2026, 3, 1),
        {"lucro_liquido": 30.0},
    )
    assert series_cvm.trimestres([documento]) == []
