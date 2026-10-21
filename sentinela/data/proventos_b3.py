"""Proventos em dinheiro de 12 meses pela relação da B3 (F2B-31; ficha Bazin 1.2, §2 a §4).

Soma de dividendos e JCP brutos por ação da espécie do ticker (ou dos componentes da unit),
com data ex na janela (referência − 12 meses, referência], sobre os registros literais do
serviço `GetListedCashDividends` (leiaute em `sentinela.data.providers.b3_proventos`).

Leiaute e escala, conferidos em 20/10/2026:
- `valueCash` é o valor **bruto** por ação, com vírgula decimal: o JCP da Lojas Renner com
  data com em 2025 soma R$ 0,83829, contra R$ 0,8494 bruto pela DVA de 2025 (834.310 mil ÷
  982.199 mil ações do fim do ano) e R$ 0,7220 se fosse líquido de 15%;
- `typeStock` separa ON, PN, PNA e PNB, mesmo para units (a TAEE11 sai como ON e PN);
- `lastDatePriorEx` é o último dia com direito; a data ex é o pregão seguinte. Com a
  referência num pregão, data ex ≤ referência vale exatamente quando data com < referência,
  e data ex > início vale quando data com ≥ início. Data com na semana anterior ao início é
  decidida pelo calendário de pregões (`pregoes`); sem ele, abstenção;
- `quotedPerShares` diferente de 1 (cotação por lote, nos anos 1990) abstém o evento da
  janela, em vez de supor a conversão.

Abstenções, com o motivo (marcador da 2B, §2.1 e §2.2): relação incompleta (registros lidos
diferentes do total do serviço), relação sem algum provento em dinheiro do complemento do
emissor (a busca pelo nome de pregão não é a do emissor), histórico sem evento anterior à janela (cobertura de 12
meses não demonstrada), preço sem pregão encerrado antes do as_of, campo ausente ou
inválido, provento negativo, natureza diferente de dividendo e JCP na janela, evento em
ações na janela (sem reconciliação nesta versão) e unit sem composição válida.
Duplicatas idênticas contam uma vez.

Função pura: sem rede, sem relógio, sem `config`.
"""

from __future__ import annotations

import math
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

FUSO = ZoneInfo("America/Sao_Paulo")
NATUREZAS = {"DIVIDENDO": "dividendo", "JRS CAP PROPRIO": "jcp"}
# Hipótese declarada: a B3 não fica sete dias seguidos sem pregão; data com até sete dias
# antes do início da janela tem a data ex (pregão seguinte) antes dele, e fica fora.
FOLGA_SEM_PREGAO = timedelta(days=7)
# R$ por evento conferido: o yfinance publica seis casas por evento (TAEE11, 20/10/2026: B3
# R$ 3,0064572, yfinance R$ 3,006456); o mínimo de R$ 0,000001 é o do marcador da 2B, §2.3.
TOLERANCIA_CONFERENCIA = 1e-6
ESPECIE_DO_ISIN = {"ACNOR": "ON", "ACNPR": "PN", "ACNPA": "PNA", "ACNPB": "PNB"}

MOTIVO_SEM_RELACAO = "insumo ausente: relação de proventos da B3"
MOTIVO_INCOMPLETA = (
    "cobertura da relação B3 não demonstrada: registros lidos diferem do total"
)
MOTIVO_HISTORICO = (
    "cobertura de 12 meses não demonstrada: nenhum provento antes da janela"
)
MOTIVO_PRECO = "insumo ausente: data do preço de referência"
MOTIVO_PRECO_NAO_ENCERRADO = "preço sem pregão encerrado antes do as_of"
MOTIVO_AS_OF = "as_of exige fuso horário"
MOTIVO_CALENDARIO = "calendário de pregões necessário para a data ex"
MOTIVO_NEGATIVO = "insumo fora do domínio: provento, negativo"
MOTIVO_LOTE = "insumo fora do domínio: provento cotado por lote"
MOTIVO_NATUREZA = "natureza do provento fora de dividendo e JCP na janela"
MOTIVO_EVENTO_ACOES = "evento em ações na janela sem reconciliação"
MOTIVO_UNIT = "unit sem composição válida"
MOTIVO_DISPONIBILIDADE = (
    "disponibilidade histórica não demonstrada: provento sem data de aprovação"
)
MOTIVO_ESPECIE = "insumo ausente: espécie do ticker"
MOTIVO_ESPECIE_SEM_REGISTRO = "série B3 sem nenhum registro da espécie"
MOTIVO_ESPECIE_ILEGIVEL = "insumo inválido: espécie do provento"
MOTIVO_COLETA = (
    "disponibilidade histórica não demonstrada: relação B3 sem coleta até o as_of"
)
MOTIVO_CRUZAMENTO = (
    "relação B3 pelo nome de pregão sem provento do complemento do emissor"
)
AVISO_SEM_CONFERENCIA = "conferência dos proventos no yfinance indisponível"
# Ficha Bazin 1.2, §3 (decisão do Marcos de 20/10/2026): fora de `riscos`.
AVISO_EXTRAORDINARIA = (
    "proventos de 12 meses podem incluir distribuição extraordinária, "
    "não identificada nesta versão"
)


@dataclass(frozen=True)
class Abstencao:
    motivo: str


@dataclass(frozen=True)
class Evento:
    especie: str
    natureza: str
    valor: float
    data_com: date
    aprovacao: date | None


def _texto(bruto: object) -> str | None:
    if not isinstance(bruto, str) or not bruto.strip():
        return None
    return bruto.strip()


def ler_data(bruto: object) -> date | None:
    texto = _texto(bruto)
    if texto is None:
        return None
    partes = texto.split("/")
    if len(partes) != 3 or not all(parte.isdigit() for parte in partes):
        return None
    dia, mes, ano = (int(parte) for parte in partes)
    try:
        return date(ano, mes, dia)
    except ValueError:
        return None


def _numero(bruto: object, nome: str) -> float | Abstencao:
    """Número finito da B3 (vírgula decimal), com os motivos do marcador, §2.1."""
    texto = _texto(bruto)
    if texto is None:
        return Abstencao(f"insumo ausente: {nome}")
    if "," in texto:
        texto = texto.replace(".", "").replace(",", ".")
    try:
        numero = float(texto)
    except ValueError:
        return Abstencao(f"insumo inválido: {nome}, tipo ou unidade")
    if math.isnan(numero):
        return Abstencao(f"insumo inválido: {nome}, NaN")
    if math.isinf(numero):
        return Abstencao(f"insumo inválido: {nome}, infinito")
    return numero


def inicio_da_janela(referencia: date) -> date:
    """Mesmo dia do ano anterior (29/02 vira 28/02); a janela exclui esse dia."""
    try:
        return referencia.replace(year=referencia.year - 1)
    except ValueError:
        return referencia.replace(year=referencia.year - 1, day=28)


def _na_janela(
    data_com: date, inicio: date, referencia: date, pregoes: frozenset[date] | None
) -> bool | None:
    """Data ex (pregão seguinte à data com) em (inicio, referencia]; `None` sem calendário."""
    if data_com >= referencia:
        return False
    if data_com >= inicio:
        return True
    if data_com <= inicio - FOLGA_SEM_PREGAO:
        return False
    if not pregoes:
        return None
    seguintes = [p for p in pregoes if p > data_com]
    if not seguintes or max(pregoes) < inicio:
        return None
    return min(seguintes) > inicio


def _componentes(
    especie: str | None, eh_unit: bool, acoes_por_unit: object
) -> dict[str, int] | Abstencao:
    if not eh_unit:
        return {especie: 1} if especie else Abstencao(MOTIVO_ESPECIE)
    if not isinstance(acoes_por_unit, Mapping) or not acoes_por_unit:
        return Abstencao(MOTIVO_UNIT)
    componentes: dict[str, int] = {}
    for classe, quantidade in acoes_por_unit.items():
        if (
            not isinstance(quantidade, (int, float))
            or isinstance(quantidade, bool)
            or not math.isfinite(quantidade)
            or quantidade <= 0
            or quantidade % 1
        ):
            return Abstencao(MOTIVO_UNIT)
        rotulo = str(classe).upper()
        componentes[rotulo] = componentes.get(rotulo, 0) + int(quantidade)
    return componentes


def _evento_de_acoes_na_janela(
    eventos_acoes: Iterable[Mapping],
    especies: Iterable[str],
    inicio: date,
    referencia: date,
) -> str | None:
    """Rótulo e data do evento em ações que alcança a janela; sem calendário, conservador."""
    alvo = set(especies)
    for evento in eventos_acoes:
        data_com = ler_data(evento.get("lastDatePrior"))
        isin = str(evento.get("isinCode") or "")
        especie = ESPECIE_DO_ISIN.get(isin[6:11])
        if especie is not None and especie not in alvo:
            continue
        if data_com is None or inicio - FOLGA_SEM_PREGAO < data_com < referencia:
            return f"{evento.get('label')} {evento.get('lastDatePrior')}"
    return None


def _cruzamento(
    registros: list[Mapping], complemento: Iterable[Mapping], referencia: date
) -> str | None:
    """Provento do complemento (ISIN de espécie conhecida) ausente da relação, ou `None`.

    Só os de data com anterior à referência: o anúncio recente, com data ex depois dela,
    pode ainda não estar na relação e não entra na janela. Data com ilegível não é conferida
    como ausente: conta como falta.
    """
    chaves = set()
    for r in registros:
        valor = _numero(r.get("valueCash"), "valor")
        if not isinstance(valor, Abstencao):
            chaves.add(
                (
                    r.get("typeStock"),
                    r.get("corporateAction"),
                    r.get("lastDatePriorEx"),
                    valor,
                )
            )
    for evento in complemento:
        especie = ESPECIE_DO_ISIN.get(str(evento.get("isinCode") or "")[6:11])
        data_com = ler_data(evento.get("lastDatePrior"))
        if especie is None or (data_com is not None and data_com >= referencia):
            continue
        valor = _numero(evento.get("rate"), "valor")
        chave = (especie, evento.get("label"), evento.get("lastDatePrior"))
        if isinstance(valor, Abstencao) or not any(
            (e, n, d) == chave and abs(v - valor) <= 1e-9 for e, n, d, v in chaves
        ):
            return f"{chave[1]} {chave[2]} {especie}"
    return None


def serie_12_meses(
    registros: Iterable[Mapping],
    *,
    total: object,
    referencia: date,
    dia_as_of: date,
    especie: str | None,
    eh_unit: bool = False,
    acoes_por_unit: object = None,
    eventos_acoes: Iterable[Mapping] = (),
    dinheiro_complemento: Iterable[Mapping] = (),
    pregoes: Iterable[date] | None = None,
) -> dict | Abstencao:
    """Proventos brutos de 12 meses por papel (ação ou unit), com os eventos somados."""
    if referencia >= dia_as_of:
        return Abstencao(MOTIVO_PRECO_NAO_ENCERRADO)
    registros = list(registros)
    if not isinstance(total, int) or isinstance(total, bool) or total != len(registros):
        return Abstencao(MOTIVO_INCOMPLETA)
    faltante = _cruzamento(registros, dinheiro_complemento, referencia)
    if faltante is not None:
        return Abstencao(f"{MOTIVO_CRUZAMENTO}: {faltante}")
    componentes = _componentes(especie, eh_unit, acoes_por_unit)
    if isinstance(componentes, Abstencao):
        return componentes
    inicio = inicio_da_janela(referencia)
    calendario = frozenset(pregoes) if pregoes is not None else None
    datas_com: list[date] = []
    eventos: set[Evento] = set()
    for registro in registros:
        data_com = ler_data(registro.get("lastDatePriorEx"))
        if data_com is None:
            return Abstencao("insumo inválido: data com do provento, tipo ou unidade")
        datas_com.append(data_com)
        classe = _texto(registro.get("typeStock"))
        if classe is None:
            # F2B-54 (BUG-2B-34): espécie ilegível não comprova a série, nem com D zero.
            return Abstencao(MOTIVO_ESPECIE_ILEGIVEL)
        if classe not in componentes:
            continue
        dentro = _na_janela(data_com, inicio, referencia, calendario)
        if dentro is None:
            return Abstencao(f"{MOTIVO_CALENDARIO}: data com {data_com.isoformat()}")
        if not dentro:
            continue
        aprovacao = ler_data(registro.get("dateApproval"))
        if aprovacao is None:
            return Abstencao(MOTIVO_DISPONIBILIDADE)
        if aprovacao > dia_as_of:
            continue
        rotulo = _texto(registro.get("corporateAction"))
        natureza = NATUREZAS.get(rotulo or "")
        if natureza is None:
            return Abstencao(f"{MOTIVO_NATUREZA}: {rotulo}")
        lote = _numero(registro.get("quotedPerShares"), "cotação por lote do provento")
        if isinstance(lote, Abstencao):
            return lote
        if lote != 1:
            return Abstencao(MOTIVO_LOTE)
        valor = _numero(registro.get("valueCash"), "valor do provento")
        if isinstance(valor, Abstencao):
            return valor
        if valor < 0:
            return Abstencao(MOTIVO_NEGATIVO)
        eventos.add(Evento(classe, natureza, valor, data_com, aprovacao))
    if not datas_com or min(datas_com) >= inicio:
        return Abstencao(MOTIVO_HISTORICO)
    # F2B-53 (decisões do Marcos de 20/10/2026; ficha Bazin 1.1): toda série, com ou sem
    # provento, exige ao menos um registro da espécie (ou de cada componente da unit) na
    # relação, em qualquer data. Registros UNT são só conferência e não contam.
    especies_na_relacao = {_texto(r.get("typeStock")) for r in registros}
    for classe in componentes:
        if classe not in especies_na_relacao:
            return Abstencao(f"{MOTIVO_ESPECIE_SEM_REGISTRO}: {classe}")
    evento_acoes = _evento_de_acoes_na_janela(
        eventos_acoes, componentes, inicio, referencia
    )
    if evento_acoes is not None:
        return Abstencao(f"{MOTIVO_EVENTO_ACOES}: {evento_acoes}")
    por_componente = {
        classe: sum(e.valor for e in eventos if e.especie == classe)
        for classe in componentes
    }
    total_papel = sum(
        quantidade * por_componente[c] for c, quantidade in componentes.items()
    )
    if not math.isfinite(total_papel):
        return Abstencao("resultado não finito: soma dos proventos")
    return {
        "d_bruto_12m": total_papel,
        "por_componente": por_componente,
        "componentes": componentes,
        "inicio_exclusivo": inicio.isoformat(),
        "referencia": referencia.isoformat(),
        "eventos": [
            {
                "especie": e.especie,
                "natureza": e.natureza,
                "valor": e.valor,
                "data_com": e.data_com.isoformat(),
                "aprovacao": e.aprovacao.isoformat() if e.aprovacao else None,
            }
            for e in sorted(
                eventos, key=lambda e: (e.data_com, e.especie, e.natureza, e.valor)
            )
        ],
    }


def conferencia_yfinance(
    serie: Mapping, dividendos: Mapping[str, object] | None
) -> list[str]:
    """Avisos da conferência no yfinance (mesma janela, data ex dele, valor por papel).

    Só conferência: nunca muda a série da B3 (ficha Bazin, §2). Compara a soma da janela e,
    com ela igual, cada evento (F2B-54, BUG-2B-35): o evento da B3, somado por papel na data
    com, casa com o primeiro dividendo livre do yfinance de data ex até 7 dias depois dela,
    na ordem das datas com; evento sem par ou valores que só se compensam na soma geram
    aviso. `None` (sem a coluna de dividendos) é conferência indisponível; `{}` é o
    yfinance sem pagamento (BUG-2B-38).
    """
    if dividendos is None:
        return [AVISO_SEM_CONFERENCIA]
    inicio = date.fromisoformat(serie["inicio_exclusivo"])
    referencia = date.fromisoformat(serie["referencia"])
    do_yfinance: dict[date, float] = {}
    for dia, valor in dividendos.items():
        try:
            data_ex = date.fromisoformat(str(dia)[:10])
            numero = float(valor)
        except (TypeError, ValueError):
            return [AVISO_SEM_CONFERENCIA]
        if not math.isfinite(numero):
            return [AVISO_SEM_CONFERENCIA]
        if inicio < data_ex <= referencia:
            do_yfinance[data_ex] = do_yfinance.get(data_ex, 0.0) + numero
    soma = sum(do_yfinance.values())
    tolerancia = TOLERANCIA_CONFERENCIA * max(1, len(do_yfinance))
    if abs(soma - serie["d_bruto_12m"]) > tolerancia:
        return [
            (
                "proventos de 12 meses divergem do yfinance na mesma janela: "
                f"B3 R$ {serie['d_bruto_12m']:.6f}, yfinance R$ {soma:.6f}"
            )
        ]
    da_b3: dict[date, float] = {}
    componentes = serie.get("componentes") or {}
    for evento in serie.get("eventos") or ():
        data_com = date.fromisoformat(evento["data_com"])
        da_b3[data_com] = da_b3.get(data_com, 0.0) + evento["valor"] * componentes.get(
            evento["especie"], 1
        )
    divergencias, pares, usados = [], [], set()
    for data_com, valor in sorted(da_b3.items()):
        candidatos = sorted(
            d
            for d in do_yfinance
            if data_com < d <= data_com + FOLGA_SEM_PREGAO and d not in usados
        )
        if not candidatos:
            divergencias.append(
                f"B3 data com {data_com.isoformat()} R$ {valor:.6f} sem par no yfinance"
            )
            continue
        usados.add(candidatos[0])
        pares.append((data_com, valor, do_yfinance[candidatos[0]]))
    divergencias += [
        f"yfinance data ex {d.isoformat()} R$ {v:.6f} sem par na B3"
        for d, v in sorted(do_yfinance.items())
        if d not in usados
    ]
    if not divergencias and sum(abs(b - y) for _, b, y in pares) > tolerancia:
        divergencias = [
            f"data com {d.isoformat()}: B3 R$ {b:.6f}, yfinance R$ {y:.6f}"
            for d, b, y in pares
            if abs(b - y) > TOLERANCIA_CONFERENCIA
        ]
    if divergencias:
        return ["proventos divergem do yfinance por evento: " + "; ".join(divergencias)]
    return []


def entradas(dados: Mapping, instante: datetime) -> dict | Abstencao:
    """DY bruto de 12 meses da B3 sobre o último fechamento antes do as_of, e os avisos.

    O preço é o fechamento do último pregão encerrado antes do dia do as_of (marcador da 2B,
    §2.2), da mesma referência que fecha a janela dos proventos.
    """
    if instante.tzinfo is None or instante.utcoffset() is None:
        return Abstencao(MOTIVO_AS_OF)
    relacao = dados.get("proventos_b3")
    if not isinstance(relacao, Mapping):
        return Abstencao(MOTIVO_SEM_RELACAO)
    if "abstencao" in relacao:
        return Abstencao(str(relacao["abstencao"]))
    # Marcador da 2B, §2: uma coleta posterior não prova disponibilidade anterior.
    try:
        coleta = datetime.fromisoformat(str(relacao.get("coleta")))
    except ValueError:
        return Abstencao(MOTIVO_COLETA)
    if coleta.tzinfo is None or coleta.utcoffset() is None or coleta > instante:
        return Abstencao(MOTIVO_COLETA)
    dia_as_of = instante.astimezone(FUSO).date()
    fechamentos = relacao.get("fechamentos")
    if not isinstance(fechamentos, Mapping) or not fechamentos:
        return Abstencao(MOTIVO_PRECO)
    try:
        por_dia = {date.fromisoformat(str(d)): v for d, v in fechamentos.items()}
    except ValueError:
        return Abstencao(MOTIVO_PRECO)
    encerrados = [d for d in por_dia if d < dia_as_of]
    if not encerrados:
        return Abstencao(MOTIVO_PRECO_NAO_ENCERRADO)
    referencia = max(encerrados)
    preco = por_dia[referencia]
    pregoes = relacao.get("pregoes")
    serie = serie_12_meses(
        relacao.get("registros") or (),
        total=relacao.get("total"),
        referencia=referencia,
        dia_as_of=dia_as_of,
        especie=dados.get("especie"),
        eh_unit=dados.get("classe_ativo") == "UNIT",
        acoes_por_unit=dados.get("acoes_por_unit"),
        eventos_acoes=relacao.get("eventos_acoes") or (),
        dinheiro_complemento=relacao.get("dinheiro_complemento") or (),
        pregoes=None if pregoes is None else [date.fromisoformat(p) for p in pregoes],
    )
    if isinstance(serie, Abstencao):
        return serie
    if (
        not isinstance(preco, (int, float))
        or isinstance(preco, bool)
        or not math.isfinite(preco)
        or preco <= 0
    ):
        return Abstencao("insumo fora do domínio: preço, não positivo")
    # F2B-53 (decisão do Marcos de 20/10/2026; ficha Bazin 1.1, §4, linha "D e DY"): série
    # válida sem provento na janela, com cobertura completa, é DY = 0. Provento negativo já
    # abstém na série.
    return {
        "dy": serie["d_bruto_12m"] / preco,
        "preco_referencia": preco,
        "serie": serie,
        "avisos": conferencia_yfinance(serie, relacao.get("conferencia_yfinance")),
    }
