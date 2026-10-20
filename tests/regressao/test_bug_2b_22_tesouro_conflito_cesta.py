"""Gemini: conflito fora da cesta escolhida não a invalida (F2B-30)."""

from datetime import UTC, date, datetime

from sentinela.data import taxas

AS_OF = datetime(2026, 10, 20, 15, tzinfo=UTC)


def _calendario():
    return taxas.Calendario(
        date(2026, 1, 1), date(2026, 12, 31), frozenset(), {"fonte": "ANBIMA"}
    )


def test_conflito_em_outra_referencia_nao_invalida_a_cesta_escolhida():
    from sentinela.data.providers import tesouro

    cabecalho = "Tipo Titulo;Data Vencimento;Data Base;Taxa Compra Manha;Taxa Venda Manha;PU Compra Manha;PU Venda Manha\n"
    linha = "Tesouro IPCA+;15/05/2035;14/10/2026;6;6;100;100\n"
    texto = (
        cabecalho
        + linha
        + linha.replace(";6;6;", ";8;6;")
        + linha.replace("14/10", "15/10")
    )
    titulos = tesouro.ler_csv(texto, as_of=date(2026, 10, 20), validar_aplicacao=False)
    atual = taxas.calcular(
        tesouro.selecionar_ofertas(titulos),
        as_of=AS_OF,
        calendario=_calendario(),
        proveniencia={"fonte": "Tesouro"},
    )
    assert atual["ntnb"] == 0.06
    antiga = taxas.calcular(
        tesouro.selecionar_ofertas(titulos[:1]),
        as_of=AS_OF,
        calendario=_calendario(),
        proveniencia={"fonte": "Tesouro"},
    )
    assert isinstance(antiga, taxas.Abstencao)
    assert "conflitantes" in antiga.motivo


def test_conflito_de_resgate_so_abstem_a_informacao_de_resgate():
    from sentinela.data.providers import tesouro

    texto = (
        "Tipo Titulo;Data Vencimento;Data Base;Taxa Compra Manha;Taxa Venda Manha;PU Compra Manha;PU Venda Manha\n"
        "Tesouro IPCA+;15/05/2035;15/10/2026;6;6;100;100\n"
        "Tesouro IPCA+;15/05/2035;15/10/2026;6;7;100;99\n"
    )
    titulos = tesouro.ler_csv(texto, as_of=date(2026, 10, 20), validar_aplicacao=False)
    cesta = tesouro.selecionar_ofertas(titulos)
    assert cesta.motivo is None and len(cesta.titulos) == 1
    assert cesta.titulos[0].taxa_aplicacao.valor == 0.06
    assert cesta.titulos[0].taxa_resgate is None
    assert (
        cesta.proveniencia["resgate_ausente"][0]["motivo"]
        == "linhas conflitantes no par de resgate"
    )
