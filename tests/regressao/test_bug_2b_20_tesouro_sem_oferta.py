"""F2B-48: taxa e PU de aplicação zerados são sentinela sem oferta."""

from datetime import date

from sentinela.data.providers import tesouro


def test_sem_oferta_nao_vira_taxa_zero():
    csv = (
        "Tipo Titulo;Data Vencimento;Data Base;Taxa Compra Manha;Taxa Venda Manha;PU Compra Manha;PU Venda Manha\n"
        "Tesouro Prefixado com Juros Semestrais;01/01/2021;04/03/2010;0,00;0,06;0,00;0,00\n"
    )
    (titulo,) = tesouro.ler_csv(csv, as_of=date(2010, 3, 5))
    assert titulo.taxa_aplicacao is None
    assert titulo.motivo_aplicacao == "sem oferta de aplicação na data-base"
    assert titulo.pu_aplicacao == 0.0 and titulo.pu_resgate == 0.0
