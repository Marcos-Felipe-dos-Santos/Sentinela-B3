"""F2B-48: taxa e PU de aplicação zerados são sentinela sem oferta."""

from datetime import date

import pytest

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


CABECALHO = (
    "Tipo Titulo;Data Vencimento;Data Base;Taxa Compra Manha;Taxa Venda Manha;"
    "PU Compra Manha;PU Venda Manha\n"
)


def _linha(taxa="6", pu="100", resgate="6", pu_resgate="100", base="15/10/2026"):
    return f"Tesouro IPCA+;15/05/2035;{base};{taxa};{resgate};{pu};{pu_resgate}\n"


@pytest.mark.parametrize("taxa,pu", [("6", "0"), ("0", "-1")])
def test_par_de_aplicacao_invalido_abstem(taxa, pu):
    with pytest.raises(ValueError):
        tesouro.ler_csv(CABECALHO + _linha(taxa, pu), as_of=date(2026, 10, 16))


@pytest.mark.parametrize("taxa", ["0", "-0,5", "6"])
def test_taxa_com_pu_positivo_e_valida(taxa):
    (titulo,) = tesouro.ler_csv(CABECALHO + _linha(taxa), as_of=date(2026, 10, 16))
    assert titulo.taxa_aplicacao.valor == float(taxa.replace(",", ".")) / 100
    assert titulo.motivo_aplicacao is None


@pytest.mark.parametrize(
    "taxa,pu", [("6", "0"), ("0", "-1"), ("inf", "100"), ("6", "texto"), ("0", "0")]
)
def test_resgate_invalido_ou_sem_oferta_nao_invalida_aplicacao(taxa, pu):
    (titulo,) = tesouro.ler_csv(
        CABECALHO + _linha(resgate=taxa, pu_resgate=pu), as_of=date(2026, 10, 16)
    )
    assert titulo.taxa_aplicacao.valor == 0.06
    assert titulo.taxa_resgate is None
    assert titulo.motivo_resgate


def test_cesta_sem_oferta_nao_retrocede_e_registra_exclusoes():
    titulos = tesouro.ler_csv(
        CABECALHO + _linha(base="14/10/2026") + _linha("0", "0"),
        as_of=date(2026, 10, 16),
    )
    cesta = tesouro.selecionar_ofertas(titulos)
    assert cesta.data_base == date(2026, 10, 15)
    assert cesta.titulos == ()
    assert cesta.proveniencia["excluidos_sem_oferta"] == 1
    assert cesta.motivo == "cesta vazia: todos os títulos elegíveis sem oferta"


def test_cesta_mista_conta_exclusoes_sem_apagar_contexto_resgate():
    texto = (
        CABECALHO
        + _linha(resgate="6", pu_resgate="0")
        + _linha("0", "0").replace("15/05/2035", "15/05/2045")
    )
    cesta = tesouro.selecionar_ofertas(tesouro.ler_csv(texto, as_of=date(2026, 10, 16)))
    assert len(cesta.titulos) == 1
    assert cesta.motivo is None
    assert cesta.proveniencia["excluidos_sem_oferta"] == 1
    assert (
        cesta.proveniencia["resgate_ausente"][0]["motivo"]
        == "par de resgate inválido: taxa não zero com PU zero"
    )


def test_sem_titulos_elegiveis_nao_produz_taxa():
    cesta = tesouro.selecionar_ofertas(())
    assert cesta.data_base is None
    assert cesta.titulos == ()
    assert cesta.motivo == "cesta vazia: nenhum título elegível"
    assert cesta.proveniencia == {
        "data_base": None,
        "excluidos_sem_oferta": 0,
        "resgate_ausente": (),
    }


def test_cesta_filtra_familia_e_vencimento_antes_da_referencia():
    texto = (
        CABECALHO
        + _linha("0", "100", "0", "100")
        + _linha(base="16/10/2026").replace("15/05/2035", "01/01/2034")
        + _linha(base="16/10/2026").replace("Tesouro IPCA+", "Tesouro Prefixado")
    )
    cesta = tesouro.selecionar_ofertas(tesouro.ler_csv(texto, as_of=date(2026, 10, 17)))
    assert cesta.data_base == date(2026, 10, 15)
    assert len(cesta.titulos) == 1
    assert cesta.titulos[0].taxa_aplicacao.valor == 0
    assert cesta.titulos[0].taxa_resgate.valor == 0
    assert cesta.motivo is None
    assert cesta.proveniencia == {
        "data_base": "2026-10-15",
        "excluidos_sem_oferta": 0,
        "resgate_ausente": (),
    }


def test_cesta_exige_pu_ausente_no_layout_antigo():
    texto = "Tipo Titulo;Data Vencimento;Data Base;Taxa Compra Manha;Taxa Venda Manha\nTesouro IPCA+;15/05/2035;15/10/2026;6;6\n"
    cesta = tesouro.selecionar_ofertas(tesouro.ler_csv(texto, as_of=date(2026, 10, 16)))
    assert cesta.motivo == "cesta inválida: par de aplicação ausente"


def test_invalidade_so_abstem_a_cesta_em_que_a_linha_entra():
    texto = CABECALHO + _linha("6", "0", base="14/10/2026") + _linha()
    titulos = tesouro.ler_csv(texto, as_of=date(2026, 10, 16), validar_aplicacao=False)
    assert titulos[0].taxa_aplicacao is None
    assert (
        titulos[0].motivo_aplicacao
        == "par de aplicação inválido: taxa não zero com PU zero"
    )
    assert tesouro.selecionar_ofertas(titulos).motivo is None
    cesta = tesouro.selecionar_ofertas(titulos[:1])
    assert cesta.motivo == titulos[0].motivo_aplicacao
    assert cesta.proveniencia["excluidos_sem_oferta"] == 0


def test_resgate_sem_pu_fica_ausente_com_motivo():
    texto = CABECALHO.replace(";PU Venda Manha", "") + _linha().rsplit(";", 1)[0] + "\n"
    (titulo,) = tesouro.ler_csv(texto, as_of=date(2026, 10, 16))
    assert titulo.taxa_aplicacao.valor == 0.06
    assert titulo.taxa_resgate is None
    assert titulo.motivo_resgate == "par de resgate inválido: PU ausente"
