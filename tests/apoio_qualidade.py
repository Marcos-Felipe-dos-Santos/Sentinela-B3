"""Insumos sintéticos do quadro de Qualidade para o golden (F4-C10, P1 = opção B).

Completa a `serie_cvm` do `enriquecer_janelas` (2021 a 2025) com os seis números por exercício,
a identidade do documento e o perímetro; acrescenta à relação da B3 um provento por ano, fora
da janela de 12 meses do Bazin, e o calendário anual de pregões. Plano e casos em
`docs/decisoes/golden-qualidade-4.md`. Valores redondos, sem dado de mercado.
"""

from __future__ import annotations

from datetime import date, timedelta

CNPJ = "00.000.000/0001-00"
ANOS = range(2021, 2026)
# Números por exercício (milhares de reais sintéticos)
LUCRO = {2021: 100.0, 2022: 110.0, 2023: 120.0, 2024: 130.0, 2025: 140.0}
PL_INICIAL = 1000.0
RECEITA = 1000.0
DIVIDA = 200.0
EBITDA = 400.0
# Um provento por ano em 10/06 (2024 já vem do `enriquecer_bazin`, com 1,0); o de 2020
# demonstra o histórico anterior à janela de 12 meses do exercício de 2021.
PROVENTO = {2020: 1.0, 2021: 1.1, 2022: 1.2, 2023: 1.3, 2025: 1.5}
COLETA = "2026-10-20T12:00:00+00:00"


def _br(valor: float) -> str:
    return f"{valor:.2f}".replace(".", ",")


def _pregoes(inicio: date, fim: date) -> list[str]:
    dias = []
    dia = inicio
    while dia <= fim:
        if dia.weekday() < 5:
            dias.append(dia.isoformat())
        dia += timedelta(days=1)
    return dias


def _registro(ano: int, especie: str, valor: float) -> dict:
    return {
        "typeStock": especie,
        "corporateAction": "DIVIDENDO",
        "valueCash": _br(valor),
        "lastDatePriorEx": f"10/06/{ano}",
        "dateApproval": f"01/06/{ano}",
        "quotedPerShares": "1",
    }


def enriquecer_qualidade(dados: dict, variante: str) -> dict:
    """`dados` já passados por `enriquecer_gordon` e `enriquecer_bazin`; uma variante do §4."""
    dados = dict(dados)
    modelo = "banco" if variante == "banco-completo" else "empresa"
    serie = dict(dados["serie_cvm"])
    exercicios = []
    for item in serie["exercicios"]:
        e = dict(item)
        ano = e["exercicio"]
        e.update(
            cnpj=CNPJ,
            modelo=modelo,
            lucro_controladores=LUCRO[ano],
            pl_inicial_controladores=PL_INICIAL,
            lucro_liquido=LUCRO[ano] + 20.0,
            receita_liquida=RECEITA,
            divida_liquida=DIVIDA,
            ebitda=EBITDA,
            proveniencia=dict(e["proveniencia"]),
        )
        exercicios.append(e)
    por_ano = {e["exercicio"]: e for e in exercicios}
    if variante == "sem-lucro":
        por_ano[2023]["lucro_controladores"] = None
    elif variante == "pl-inicial-zero":
        por_ano[2022]["pl_inicial_controladores"] = 0.0
    elif variante == "sem-ebitda":
        por_ano[2024]["ebitda"] = None
    elif variante == "receita-zero":
        por_ano[2021]["receita_liquida"] = 0.0
    elif variante == "entrega-depois-do-as_of":
        por_ano[2025]["proveniencia"]["data_entrega"] = "2026-10-21"
    elif variante == "por-publicacao":
        for e in exercicios:
            e["proveniencia"]["data_coleta"] = "2026-10-25T12:00:00+00:00"
        dados["disponibilidade_por_publicacao"] = True
    elif variante == "perimetro-misto":
        por_ano[2022]["perimetro"] = "consolidado com controlada adquirida"
    serie["exercicios"] = exercicios
    dados["serie_cvm"] = serie
    if modelo == "banco":
        dados["modelo_bpp"] = "banco"

    relacao = dados.get("proventos_b3")
    if variante == "relacao-abstida" or not isinstance(relacao, dict):
        dados["proventos_b3"] = {"abstencao": "relação B3 sintética abstida"}
    elif "registros" in relacao:
        relacao = dict(relacao)
        especies = (
            list(dados.get("acoes_por_unit") or {})
            if dados.get("classe_ativo") == "UNIT"
            else [dados.get("especie", "ON")]
        )
        anos = dict(PROVENTO)
        if dados.get("classe_ativo") == "UNIT":
            anos[2024] = 1.0  # o registro de 2024 do Bazin é da UNT, só conferência
        novos = [
            _registro(ano, especie, valor)
            for ano, valor in sorted(anos.items())
            for especie in especies
        ]
        relacao["registros"] = [*relacao["registros"], *novos]
        relacao["total"] = len(relacao["registros"])
        dados["proventos_b3"] = relacao

    fim_calendario = (
        date(2026, 1, 5) if variante == "calendario-curto" else date(2026, 10, 19)
    )
    dados["calendario_proventos_b3"] = {
        "fonte": "calendário de pregões B3 sintético de teste",
        "coleta": COLETA,
        "inicio": "2020-01-01",
        "fim": fim_calendario.isoformat(),
        "pregoes": _pregoes(date(2020, 1, 1), fim_calendario),
    }
    return dados
