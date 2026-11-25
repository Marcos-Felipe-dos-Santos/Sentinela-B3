"""BUG-4-04: a janela do Bazin exclui aprovações sem hora em D e eventos alheios."""

from datetime import UTC, date, datetime

import pytest

from sentinela.data import proventos_b3 as pb

AS_OF = datetime(2026, 10, 20, 15, tzinfo=UTC)
ISIN = "BRTESTACNOR0"


def _registro(data_com: str, aprovado: str, valor: str = "1,50") -> dict:
    return {
        "typeStock": "ON",
        "lastDatePriorEx": data_com,
        "dateApproval": aprovado,
        "corporateAction": "DIVIDENDO",
        "quotedPerShares": "1",
        "valueCash": valor,
    }


def _evento(isin: str, aprovado: str) -> dict:
    return {
        "label": "DESDOBRAMENTO",
        "isinCode": isin,
        "approvedOn": aprovado,
        "lastDatePrior": "15/10/2026",
    }


def _entradas(
    *, provento: dict | None = None, evento: dict | None = None
) -> dict | pb.Abstencao:
    registros = [
        _registro("15/09/2025", "01/09/2025"),
        _registro("15/05/2026", "01/05/2026"),
    ]
    if provento is not None:
        registros.append(provento)
    return pb.entradas(
        {
            "classe_ativo": "STOCK",
            "especie": "ON",
            "proventos_b3": {
                "coleta": AS_OF.isoformat(),
                "fechamentos": {"2026-10-19": 10.0},
                "registros": registros,
                "total": len(registros),
                "isins_emissor": [ISIN],
                "eventos_acoes": [evento] if evento is not None else [],
            },
        },
        AS_OF,
    )


def test_provento_aprovado_no_dia_do_corte_fica_fora() -> None:
    resultado = _entradas(provento=_registro("16/10/2026", "20/10/2026", "2,00"))

    assert not isinstance(resultado, pb.Abstencao), resultado
    assert resultado["dy"] == pytest.approx(0.15)


@pytest.mark.parametrize("aprovado", ["20/10/2026", "21/10/2026"])
def test_evento_do_proprio_emissor_aprovado_no_corte_ou_depois_fica_fora(
    aprovado: str,
) -> None:
    resultado = _entradas(evento=_evento(ISIN, aprovado))

    assert not isinstance(resultado, pb.Abstencao), resultado
    assert resultado["dy"] == pytest.approx(0.15)


def test_evento_de_outro_emissor_da_mesma_especie_fica_fora() -> None:
    resultado = _entradas(evento=_evento("BRALHEACNOR9", "01/10/2026"))

    assert not isinstance(resultado, pb.Abstencao), resultado
    assert resultado["dy"] == pytest.approx(0.15)


@pytest.mark.parametrize("isin", [ISIN, ""])
def test_evento_proprio_ou_sem_isin_inequivoco_ainda_abstem(isin: str) -> None:
    resultado = _entradas(evento=_evento(isin, "01/10/2026"))

    assert isinstance(resultado, pb.Abstencao)
    assert resultado.motivo == f"{pb.MOTIVO_EVENTO_ACOES}: DESDOBRAMENTO 15/10/2026"


def test_aprovacao_no_corte_exclui_registro_antes_de_validar_data_com() -> None:
    resultado = _entradas(provento=_registro("ilegível", "20/10/2026", "2,00"))

    assert not isinstance(resultado, pb.Abstencao), resultado
    assert resultado["dy"] == pytest.approx(0.15)


@pytest.mark.parametrize("so_especie", [False, True])
def test_registro_aprovado_no_corte_nao_prova_cobertura(so_especie: bool) -> None:
    futuro = _registro("15/09/2025", "20/10/2026")
    valido = _registro("15/05/2026", "01/05/2026")
    if so_especie:
        valido["lastDatePriorEx"] = "15/09/2025"
        valido["typeStock"] = "PN"
    resultado = pb.serie_12_meses(
        [futuro, valido],
        total=2,
        referencia=date(2026, 10, 19),
        dia_as_of=AS_OF.date(),
        especie="ON",
    )

    assert isinstance(resultado, pb.Abstencao)
    esperado = (
        f"{pb.MOTIVO_ESPECIE_SEM_REGISTRO}: ON" if so_especie else pb.MOTIVO_HISTORICO
    )
    assert resultado.motivo == esperado
