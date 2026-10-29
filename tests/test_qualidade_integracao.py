"""Quadro independente não muda campos legados e aparece com motivos no relatório."""

from copy import deepcopy

import pytest
from apoio_escopo import de_empresa

from sentinela.methods import registry
from sentinela.reports.rastreabilidade import renderizar
from tests.test_qualidade import AS_OF, documentos
from tests.test_rastreabilidade import _contexto
from valuation_engine import ValuationEngine


def dados():
    d = de_empresa(
        {
            "ticker": "TST3",
            "preco_atual": 100.0,
            "pl": 10.0,
            "pvp": 2.0,
            "roe": 0.15,
            "dy": 0.05,
        }
    )
    d["serie_cvm"] = {"exercicios": documentos()}
    return d


def test_catalogo_descritivo_separado_de_valor_br():
    assert len(registry.METODOS) == 7
    assert registry.QUADROS_DESCRITIVOS[0].nome == "Qualidade descritiva"


def test_nenhuma_chave_legada_muda():
    m = ValuationEngine()
    d = dados()
    antes = m._processar_valuation(deepcopy(d), as_of=AS_OF)
    depois = m.processar(deepcopy(d), as_of=AS_OF)
    quadro = depois.pop("qualidade")
    assert depois == antes
    assert quadro["roe"]["media"] == pytest.approx(0.1)
    assert (
        quadro["proventos"]["observados"] == 0
    )  # faltam B3/calendário, não vale bloco artificial da série


def test_guardas_tambem_tem_quadro_com_motivo():
    r = ValuationEngine().processar(
        {"preco_atual": 10.0, "ticker": "TST3"}, as_of=AS_OF
    )
    assert r["qualidade"]["motivo"]
    assert "fair_value" not in r
    assert ValuationEngine().processar(None, as_of=AS_OF) is None


def test_relatorio_descritivo_com_escape():
    d = dados()
    d["serie_cvm"]["exercicios"][0]["proveniencia"]["fonte"] = "<script>FONTE</script>"
    c = _contexto(d)
    assert c["qualidade"]["roe"]["observados"] == 5
    html = renderizar(c)
    assert "Qualidade descritiva" in html and "Margem consolidada" in html
    assert "Sem nota única" in html
    assert "<script>FONTE</script>" not in html
    assert "&lt;script&gt;FONTE&lt;/script&gt;" in html


def test_apresentacao_unidades_cobertura_e_proveniencia_legiveis():
    from sentinela.methods.qualidade import Qualidade
    from sentinela.reports.rastreabilidade import _apresentar_qualidade

    q = Qualidade().calcular(documentos(), as_of=AS_OF, classe="STOCK", modelo="empresa")
    q["roe"].update(minimo=-0.125, maximo=0.25, ultimo=0.15, media=0.1, desvio_populacional_pp=6.29, observados=4, motivo="comparabilidade pendente")
    q["alavancagem"].update(minimo=-1.25, maximo=3.5, ultimo=2.0, observados=3)
    q["lucros"].update(positivos=3, observados=4)
    q["proventos"].update(positivos=None, observados=0)
    e = q["exercicios"][0]
    e.update(pl_inicial_proveniencia={"demonstrativo": "BPP_con PENÚLTIMO", "data_saldo": "2020-12-31"}, fonte_proventos={"fonte": "B3 oficial", "coleta": "2026-01-01"})
    e["documento"] = {"referencia": "2021-12-31", "versao": 3, "proveniencia": {"fonte": "CVM oficial", "data_coleta": "2026-01-02"}}
    e["motivos"] = {"roe": "denominador ausente"}
    p = _apresentar_qualidade(q)
    indicadores = dict(p["indicadores"])
    assert indicadores["ROE sobre PL inicial"] == "faixa -12,50% a 25,00%; último 15,00%; média 10,00%; desvio populacional 6,29 pp; comparabilidade pendente; 4/5 observações"
    assert indicadores["Dívida financeira líquida / EBITDA"] == "faixa -1,25 vezes a 3,50 vezes; último 2,00 vezes; 3/5 observações"
    assert indicadores["Lucros positivos"] == "3,00 positivos entre 4 observados; 4/5 observações"
    assert indicadores["Proventos B3 por data-ex"].startswith("indisponível positivos entre 0 observados;")
    assert p["cobertura"] == "5/5 exercícios"
    linha = p["exercicios"][0]
    assert linha["janela"] == "2021-01-01 a 2021-12-31"
    assert linha["fonte"] == "Fonte: CVM oficial; referência 2021-12-31; versão 3; coleta 2026-01-02"
    assert linha["pl_inicial"] == "PL inicial: BPP_con PENÚLTIMO; data do saldo 2020-12-31"
    assert linha["proventos"] == "B3 data-ex: B3 oficial; coleta 2026-01-01"
    assert linha["motivos"] == ["ROE sobre PL inicial: denominador ausente"]
    assert dict(linha["valores"])["ROE sobre PL inicial"] == "10,00%"
    assert _apresentar_qualidade(None) is None
