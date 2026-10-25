"""Rendimento de 12 meses do FII pelo Informe Mensal da CVM (F2B-28; insumo da [FII], F2B-2).

O motor de FII lê por `entradas` (F2B-2), com as guardas de `avaliar`. O complemento do Informe não tem o valor distribuído por cota; o
rendimento do mês é reconstruído pelo DY do mês × valor patrimonial da cota do fim do mês
anterior, a base que a norma define (Resolução CVM 175, anexo da 184; F2B-21, pergunta 4).
`Percentual_Dividend_Yield_Mes` vem em razão (F2B-21, pergunta 4) e passa pela fronteira de
`sentinela/data/normalizacao.py`, provedor `cvm_fii`.

Doze meses consecutivos terminando no último mês do Informe, cada um com o DY e com o valor
da cota do mês anterior (13 valores de cota); mês com mais de uma versão usa a maior
`Versao` (duas linhas diferentes nela: abstenção). Faltou algum: abstenção, com o
motivo. O DY de 12 meses é a soma dos rendimentos ÷ o preço, que vem de outra fonte.

Função pura: sem rede, sem relógio, sem `config`.
"""

from __future__ import annotations

import math
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import date, datetime
from itertools import pairwise
from zoneinfo import ZoneInfo

from sentinela.data import fii_elegibilidade, normalizacao

PROVEDOR = "cvm_fii"
MESES = 12
BASE = (
    "valor patrimonial da cota do fim do mês anterior (Resolução CVM 175, anexo da 184)"
)
MOTIVO_SEM_MESES = "Informe sem meses do fundo"
MOTIVO_MESES_INCOMPLETOS = "menos de 12 meses com DY e valor da cota do mês anterior"
MOTIVO_PRECO = "preço ausente ou não positivo"
MOTIVO_NAO_FINITO = "resultado não finito: rendimento de 12 meses do FII"
MOTIVO_CONFLITO = "Informe com linhas conflitantes da mesma versão"
# Ficha FII 1.3 (BUG-2B-37, reaberto): todo campo usado do complemento entra no conflito.
_COLUNAS_DA_CONTA = (
    "Percentual_Dividend_Yield_Mes",
    "Valor_Patrimonial_Cotas",
    "Cotas_Emitidas",
    "Percentual_Amortizacao_Cotas_Mes",
)


@dataclass(frozen=True)
class Abstencao:
    motivo: str


def _numero(bruto: object) -> float | None:
    """Número finito do CSV (vírgula ou ponto decimal); `None` sem número.

    Pelo texto: `None` e booleano viram "None", "True" e "False", que não são número.
    """
    try:
        numero = float(str(bruto).replace(",", "."))
    except ValueError:
        return None
    return numero if math.isfinite(numero) else None


def _versao(registro: Mapping) -> float:
    versao = _numero(registro.get("Versao"))
    return versao if versao is not None else float("-inf")


def _mes(registro: Mapping) -> tuple[int, int] | None:
    texto = str(registro.get("Data_Referencia") or "")[:7]
    try:
        ano, mes = texto.split("-")
        chave = (int(ano), int(mes))
    except ValueError:
        return None
    return chave if 1 <= chave[1] <= 12 else None


def _anterior(mes: tuple[int, int]) -> tuple[int, int]:
    ano, m = mes
    return (ano - 1, 12) if m == 1 else (ano, m - 1)


def _por_mes(
    registros: Iterable[Mapping],
) -> tuple[dict[tuple[int, int], Mapping], set[tuple[int, int]]]:
    """Um registro por mês, o de maior `Versao` (versão ilegível perde), e os meses em conflito.

    Duas linhas da maior versão do mês com DY, valor da cota, cotas ou amortização diferentes
    são conflito (F2B-54 e F2B-57, BUG-2B-37): nenhuma vence pela ordem do arquivo. Duplicata
    nessas colunas não é conflito, nem com célula vazia (as duas vazias); vazio contra
    inválido é conflito (`fii_elegibilidade.forma`).
    """
    escolhidos: dict[tuple[int, int], Mapping] = {}
    conflitos: set[tuple[int, int]] = set()
    for registro in registros:
        mes = _mes(registro)
        if mes is None:
            continue
        atual = escolhidos.get(mes)
        if atual is None or _versao(registro) > _versao(atual):
            escolhidos[mes] = registro
            conflitos.discard(mes)
        elif _versao(registro) == _versao(atual) and any(
            fii_elegibilidade.forma(registro.get(c))
            != fii_elegibilidade.forma(atual.get(c))
            for c in _COLUNAS_DA_CONTA
        ):
            conflitos.add(mes)
    return escolhidos, conflitos


def rendimento_12_meses(
    registros: Iterable[Mapping], preco: object
) -> dict | Abstencao:
    """DY de 12 meses sobre o preço, com os meses, a base e a representação usada."""
    meses, conflitos = _por_mes(registros)
    if not meses:
        return Abstencao(MOTIVO_SEM_MESES)
    preco_valor = _numero(preco)
    if preco_valor is None or preco_valor <= 0:
        return Abstencao(MOTIVO_PRECO)
    final = max(meses)
    mes, rendimentos, por_mes = final, [], {}
    for _ in range(MESES):  # `mes` sempre existe: o final, ou o `anterior` com cota
        anterior = _anterior(mes)
        dy = normalizacao.dy_na_fronteira(
            _numero(meses[mes].get("Percentual_Dividend_Yield_Mes")), PROVEDOR
        ).valor
        cota = _numero(meses.get(anterior, {}).get("Valor_Patrimonial_Cotas"))
        if dy is None or cota is None or cota <= 0:
            return Abstencao(MOTIVO_MESES_INCOMPLETOS)
        for usado in (mes, anterior):
            if usado in conflitos:
                return Abstencao(f"{MOTIVO_CONFLITO}: {usado[0]:04d}-{usado[1]:02d}")
        rendimentos.append(dy * cota)
        por_mes[f"{mes[0]:04d}-{mes[1]:02d}"] = dy * cota
        mes = anterior
    rendimento = sum(rendimentos)
    dy_12m = rendimento / preco_valor
    # F2B-54 (BUG-2B-36): entradas finitas podem transbordar no produto, na soma ou na divisão.
    if not all(math.isfinite(v) for v in (*rendimentos, rendimento, dy_12m)):
        return Abstencao(MOTIVO_NAO_FINITO)
    return {
        "dy": dy_12m,
        "rendimento_12m": rendimento,
        "rendimentos": dict(sorted(por_mes.items())),
        "meses": MESES,
        "mes_final": f"{final[0]:04d}-{final[1]:02d}",
        "base": BASE,
        "conversao": normalizacao.proveniencia_dy(PROVEDOR),
    }


# ── guardas da ficha FII 1.2 (F2B-2, F2B-55) ──────────────────────────────────

MOTIVO_IDADE = "Informe mais recente com mais de 3 meses"
MOTIVO_DY_NEGATIVO = "DY mensal negativo declarado no Informe"
MOTIVO_AMORTIZACAO = (
    "amortização na janela: devolução de capital, fluxo não representativo"
)
MOTIVO_AMORTIZACAO_INVALIDA = "amortização inválida no Informe"
MOTIVO_COTAS = "cotas emitidas inválidas: base de cota incompatível"
MOTIVO_SEM_COMPOSICAO = "composição do Informe do mês final indisponível"
MOTIVO_EVENTOS_INDISPONIVEIS = (
    "fonte de eventos de cota indisponível: continuidade não demonstrável"
)
MOTIVO_RENDIMENTO_NAO_POSITIVO = "rendimento anual não positivo"
MOTIVO_DY_NAO_CONFIAVEL = "rendimento não confiável: DY de 12 meses acima de 25%"
DY_MAXIMO = 0.25
IDADE_MAXIMA_MESES = 3


def _entregue(registro: Mapping, dia_as_of: date) -> bool:
    """Data de entrega demonstrada e anterior ao dia do as_of (o dia só vale depois do fim)."""
    try:
        return date.fromisoformat(str(registro.get("Data_Entrega"))[:10]) < dia_as_of
    except ValueError:
        return False


def _rotulo(mes: tuple[int, int]) -> str:
    return f"{mes[0]:04d}-{mes[1]:02d}"


def avaliar(
    registros: Iterable[Mapping],
    composicoes: Iterable[Mapping],
    *,
    b3: object,
    codigo: str,
    isin: str | None,
    preco: object,
    dia_as_of: date,
) -> dict | Abstencao:
    """Rendimento de 12 meses do FII com as guardas da ficha FII 1.2, ou a abstenção.

    Só as linhas do Informe entregues antes do dia do as_of; janela terminada no último mês
    elegível, até 3 meses civis antes do as_of; DY mensal negativo, amortização e cotas
    não positivas abstêm (a fração vale, ficha FII 1.2); só tijolo pela composição do mês final; desdobramento ou grupamento
    da B3 na janela (do primeiro VP ao as_of), ou a B3 sem resposta válida, abstêm. A
    conferência com o rendimento da B3 só gera aviso. Emissões ficam em contexto.
    """
    elegiveis = [r for r in registros if _entregue(r, dia_as_of)]
    meses, conflitos = _por_mes(elegiveis)
    if not meses:
        return Abstencao(MOTIVO_SEM_MESES)
    final = max(meses)
    if (dia_as_of.year * 12 + dia_as_of.month) - (final[0] * 12 + final[1]) > (
        IDADE_MAXIMA_MESES
    ):
        return Abstencao(MOTIVO_IDADE)
    janela = [final]
    while len(janela) < MESES + 1:
        janela.append(_anterior(janela[-1]))
    cotas_por_mes = {}
    for mes in janela:
        linha = meses.get(mes)
        if linha is None:
            return Abstencao(MOTIVO_MESES_INCOMPLETOS)
        if mes in conflitos:
            return Abstencao(f"{MOTIVO_CONFLITO}: {_rotulo(mes)}")
        cotas = _numero(linha.get("Cotas_Emitidas"))
        if cotas is None or cotas <= 0:
            return Abstencao(MOTIVO_COTAS)
        # Ficha FII 1.2: quantidade fracionária vale; só detecta eventos (emissões).
        cotas_por_mes[mes] = int(cotas) if cotas.is_integer() else cotas
        if mes == janela[-1]:
            continue  # o 13º mês só dá o VP
        dy_mes = _numero(linha.get("Percentual_Dividend_Yield_Mes"))
        if dy_mes is not None and dy_mes < 0:
            return Abstencao(MOTIVO_DY_NEGATIVO)
        amortizacao = linha.get("Percentual_Amortizacao_Cotas_Mes")
        if not (
            amortizacao is None
            or (isinstance(amortizacao, float) and math.isnan(amortizacao))
            or (isinstance(amortizacao, str) and not amortizacao.strip())
        ):
            valor = _numero(amortizacao)
            if valor is None or valor < 0:
                return Abstencao(MOTIVO_AMORTIZACAO_INVALIDA)
            if valor > 0:
                return Abstencao(MOTIVO_AMORTIZACAO)
    medida = rendimento_12_meses(
        [r for r in elegiveis if _mes(r) in set(janela)], preco
    )
    if isinstance(medida, Abstencao):
        return medida
    entregues = {(_mes(r), _versao(r)) for r in elegiveis if _mes(r) == final}
    composicao = [c for c in composicoes if (_mes(c), _versao(c)) in entregues]
    if not composicao:
        return Abstencao(MOTIVO_SEM_COMPOSICAO)
    maior = max(map(_versao, composicao))
    da_maior = [c for c in composicao if _versao(c) == maior]
    if len({fii_elegibilidade.posicoes(c) for c in da_maior}) > 1:
        # F2B-57 (BUG-2B-37, reaberto): composições da mesma versão em conflito abstêm.
        return Abstencao(f"{MOTIVO_CONFLITO}: {_rotulo(final)} (composição)")
    tipo = fii_elegibilidade.tipo_pela_composicao(da_maior[0])
    if isinstance(tipo, fii_elegibilidade.Abstencao):
        return Abstencao(tipo.motivo)
    if tipo != "tijolo":
        return Abstencao(f"tipo de FII fora do escopo na 2B: {tipo}")
    if not fii_elegibilidade.resposta_b3_valida(b3, codigo):
        return Abstencao(MOTIVO_EVENTOS_INDISPONIVEIS)
    primeiro = janela[-1]
    evento = fii_elegibilidade.evento_de_cota(
        b3["stockDividends"], date(primeiro[0], primeiro[1], 1), dia_as_of
    )
    if evento is not None:
        return Abstencao(evento)
    if medida["rendimento_12m"] <= 0:
        return Abstencao(MOTIVO_RENDIMENTO_NAO_POSITIVO)
    if medida["dy"] > DY_MAXIMO:
        return Abstencao(MOTIVO_DY_NAO_CONFIAVEL)
    ordem = sorted(cotas_por_mes)
    emissoes = [
        {
            "mes": _rotulo(depois),
            "cotas_antes": cotas_por_mes[antes],
            "cotas_depois": cotas_por_mes[depois],
        }
        for antes, depois in pairwise(ordem)
        if cotas_por_mes[depois] != cotas_por_mes[antes]
    ]
    return {
        **medida,
        "tipo": tipo,
        "emissoes": emissoes,
        "avisos": fii_elegibilidade.conferencia_b3(
            medida["rendimentos"], b3["cashDividends"], isin
        ),
    }


MOTIVO_SEM_INFORME = "insumo ausente: Informe Mensal do FII"
FUSO = ZoneInfo("America/Sao_Paulo")


def entradas(dados: Mapping, instante: datetime) -> dict | Abstencao:
    """`avaliar` sobre o que a cascata gravou (`informe_fii`, `b3_fundo`, preço), no as_of.

    O dia do as_of é o de Brasília; as_of sem fuso abstém.
    """
    if instante.tzinfo is None or instante.utcoffset() is None:
        return Abstencao("as_of exige fuso horário")
    informe = dados.get("informe_fii")
    if not isinstance(informe, Mapping) or "registros" not in informe:
        motivo = informe.get("abstencao") if isinstance(informe, Mapping) else None
        return Abstencao(
            f"{MOTIVO_SEM_INFORME}: {motivo}" if motivo else MOTIVO_SEM_INFORME
        )
    b3 = dados.get("b3_fundo")
    resposta = b3.get("resposta") if isinstance(b3, Mapping) else None
    return avaliar(
        informe.get("registros") or (),
        informe.get("composicoes") or (),
        b3=resposta,
        codigo=str(dados.get("ticker") or "")[:4],
        isin=informe.get("isin"),
        preco=dados.get("preco_atual"),
        dia_as_of=instante.astimezone(FUSO).date(),
    )
