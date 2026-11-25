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

Identidade do emissor (F3-P01, decisões 30 e 33 do Marcos, 10/11/2026): `conferir_emissor`
aceita a relação lida pelo nome de pregão só se (a) cada espécie (`typeStock`) dela tem ISIN
da companhia no GetDetail pelo código CVM, (b) cada provento em dinheiro do complemento
aparece nela com a mesma data com e o mesmo valor na precisão da relação (`mesmo_valor`) e
(c) o complemento traz algum provento; qualquer falha devolve o motivo da abstenção.

Função pura: sem rede, sem relógio, sem `config`.
"""

from __future__ import annotations

import math
import re
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from zoneinfo import ZoneInfo

FUSO = ZoneInfo("America/Sao_Paulo")
NATUREZAS = {"DIVIDENDO": "dividendo", "JRS CAP PROPRIO": "jcp"}
# Hipótese declarada: a B3 não fica sete dias seguidos sem pregão; data com até sete dias
# antes do início da janela tem a data ex (pregão seguinte) antes dele, e fica fora.
FOLGA_SEM_PREGAO = timedelta(days=7)
# R$ por evento conferido: o yfinance publica seis casas por evento (TAEE11, 20/10/2026: B3
# R$ 3,0064572, yfinance R$ 3,006456); o mínimo de R$ 0,000001 é o do marcador da 2B, §2.3.
TOLERANCIA_CONFERENCIA = 1e-6
ESPECIE_DO_ISIN = {
    "ACNOR": "ON",
    "ACNPR": "PN",
    "ACNPA": "PNA",
    "ACNPB": "PNB",
    "ACNPC": "PNC",
    "ACNPD": "PND",
    "ACNPE": "PNE",
    "ACNPF": "PNF",
    "ACNPG": "PNG",
    "ACNPH": "PNH",
}
# Decisão 33 (b): o complemento traz 11 casas e a relação, em geral, 4; o valor confere se
# |relação − complemento arredondado a 4 casas| ≤ 0,00005. Empate arredonda para cima.
CASAS_COMPLEMENTO = Decimal("0.0001")
TOLERANCIA_COMPLEMENTO = Decimal("0.00005")

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
MOTIVO_IDENTIDADE = "identidade do emissor não comprovada"
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


def isin_legivel(isin: str) -> bool:
    """Confere a estrutura e o dígito verificador do ISIN (ISO 6166)."""
    if re.fullmatch(r"[A-Z]{2}[A-Z0-9]{9}[0-9]", isin) is None:
        return False
    digitos = "".join(str(int(caractere, 36)) for caractere in isin)
    total = 0
    for posicao, digito in enumerate(reversed(digitos)):
        produto = int(digito) * (1 + posicao % 2)
        total += produto // 10 + produto % 10
    return total % 10 == 0


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


def _decimal(bruto: object) -> Decimal | None:
    """Valor da B3 (vírgula decimal) como `Decimal` finito, ou `None`."""
    texto = _texto(bruto)
    if texto is None or "_" in texto:  # `Decimal` aceitaria "1_000"
        return None
    if "," in texto:
        texto = texto.replace(".", "").replace(",", ".")
    try:
        numero = Decimal(texto)
    except InvalidOperation:
        return None
    return numero if numero.is_finite() else None


def mesmo_valor(relacao: object, complemento: object) -> bool:
    """Decisão 33 (b): valor da relação igual ao do complemento na precisão da relação."""
    r, c = _decimal(relacao), _decimal(complemento)
    if r is None or c is None:
        return False
    arredondado = c.quantize(CASAS_COMPLEMENTO, rounding=ROUND_HALF_UP)
    return abs(r - arredondado) <= TOLERANCIA_COMPLEMENTO


def conferir_emissor(
    registros: Iterable[object],
    complemento: Iterable[object],
    isins: Iterable[str],
    corte: date | None = None,
) -> str | None:
    """Motivo da abstenção se a relação não é comprovadamente do emissor; senão `None`.

    `isins` são os da companhia no GetDetail pelo código CVM (`otherCodes`); `complemento`,
    os proventos em dinheiro do GetListedSupplementCompany do emissor. Leitura literal da
    decisão 33 (b), "todo provento do complemento": sem o corte de espécie e de janela do
    `_cruzamento`. Provento por ISIN da unit (`CDAM`), que a relação por espécie não traz,
    e anúncio que a relação ainda não traz abstêm (DD-06).

    `corte` (decisão 51, BUG-3-61; D na análise, o dia seguinte a T no retorno): o provento
    do complemento anunciado (`approvedOn`) no corte ou depois e ausente da relação não
    decide a identidade numa data anterior ao anúncio; o de aprovação ilegível segue
    comparado. DD-90: ao menos um provento do complemento precisa estar na relação.
    """
    isins = tuple(isins)
    if not isins:
        return f"{MOTIVO_IDENTIDADE}: GetDetail sem ISIN da companhia"
    especies = {ESPECIE_DO_ISIN.get(str(isin)[6:11]) for isin in isins} - {None}
    lidos = []
    for registro in registros:
        if not isinstance(registro, Mapping):
            return f"{MOTIVO_IDENTIDADE}: registro da relação ilegível"
        especie = registro.get("typeStock")
        if especie not in especies:
            return (
                f"{MOTIVO_IDENTIDADE}: espécie {especie} da relação sem ISIN da "
                "companhia no GetDetail"
            )
        lidos.append(
            (ler_data(registro.get("lastDatePriorEx")), registro.get("valueCash"))
        )
    complemento = tuple(complemento)
    if not complemento:
        return f"{MOTIVO_IDENTIDADE}: complemento sem proventos para conferir"
    algum_na_relacao = False
    for evento in complemento:
        if not isinstance(evento, Mapping):
            return f"{MOTIVO_IDENTIDADE}: provento do complemento ilegível"
        data_com = ler_data(evento.get("lastDatePrior"))
        if data_com is None or _decimal(evento.get("rate")) is None:
            return f"{MOTIVO_IDENTIDADE}: provento do complemento ilegível"
        if any(d == data_com and mesmo_valor(v, evento.get("rate")) for d, v in lidos):
            algum_na_relacao = True
            continue
        anuncio = ler_data(evento.get("approvedOn"))
        if corte is not None and anuncio is not None and anuncio >= corte:
            continue
        return (
            f"{MOTIVO_IDENTIDADE}: provento do complemento {evento.get('label')} "
            f"{evento.get('lastDatePrior')} ausente da relação"
        )
    if not algum_na_relacao:
        return f"{MOTIVO_IDENTIDADE}: nenhum provento do complemento na relação"
    return None


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
    dia_as_of: date,
    isins_emissor: Iterable[str],
) -> str | None:
    """Rótulo e data de um evento atribuível e disponível que alcança a janela."""
    alvo = set(especies)
    isins = frozenset(isins_emissor)
    for evento in eventos_acoes:
        aprovacao = ler_data(evento.get("approvedOn"))
        if aprovacao is not None and aprovacao >= dia_as_of:
            continue
        isin = str(evento.get("isinCode") or "")
        # Sem ISIN legível (estrutura e dígito verificador), a identidade do evento não pode
        # ser descartada (BUG-4-12).
        if isins and isin not in isins and isin_legivel(isin):
            continue
        data_com = ler_data(evento.get("lastDatePrior"))
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
                    r.get("valueCash"),
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
            (e, n, d) == chave and mesmo_valor(v, evento.get("rate"))
            for e, n, d, v in chaves
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
    isins_emissor: Iterable[str] = (),
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
    especies_na_relacao: set[str] = set()
    for registro in registros:
        aprovacao = ler_data(registro.get("dateApproval"))
        if aprovacao is not None and aprovacao >= dia_as_of:
            continue
        data_com = ler_data(registro.get("lastDatePriorEx"))
        if data_com is None:
            return Abstencao("insumo inválido: data com do provento, tipo ou unidade")
        datas_com.append(data_com)
        classe = _texto(registro.get("typeStock"))
        if classe is None:
            # F2B-54 (BUG-2B-34): espécie ilegível não comprova a série, nem com D zero.
            return Abstencao(MOTIVO_ESPECIE_ILEGIVEL)
        especies_na_relacao.add(classe)
        if classe not in componentes:
            continue
        dentro = _na_janela(data_com, inicio, referencia, calendario)
        if dentro is None:
            return Abstencao(f"{MOTIVO_CALENDARIO}: data com {data_com.isoformat()}")
        if not dentro:
            continue
        if aprovacao is None:
            return Abstencao(MOTIVO_DISPONIBILIDADE)
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
    for classe in componentes:
        if classe not in especies_na_relacao:
            return Abstencao(f"{MOTIVO_ESPECIE_SEM_REGISTRO}: {classe}")
    evento_acoes = _evento_de_acoes_na_janela(
        eventos_acoes, componentes, inicio, referencia, dia_as_of, isins_emissor
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
    # Marcador da 2B, §2: uma coleta posterior não prova disponibilidade anterior. Decisão 40
    # (F3-8h): só o bloco montado do banco por `b3_proventos.relacao_ate`, que já retirou os
    # registros aprovados em D ou depois, vale pela publicação numa data passada; a coleta
    # continua exigida e datada, sem ser critério. A relação coletada agora pela cascata
    # corrente mantém a guarda de coleta mesmo com a marca (DD-65).
    try:
        coleta = datetime.fromisoformat(str(relacao.get("coleta")))
    except ValueError:
        return Abstencao(MOTIVO_COLETA)
    por_publicacao = (
        dados.get("disponibilidade_por_publicacao") is True
        and relacao.get("aprovacao_antes_de_d") is True
    )
    if (
        coleta.tzinfo is None
        or coleta.utcoffset() is None
        or (coleta > instante and not por_publicacao)
    ):
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
        isins_emissor=relacao.get("isins_emissor") or (),
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


# --- Calendário anual de pregões para a lente de qualidade (F3-P14b) -----------------------
# Contrato: `docs/decisoes/calendario-proventos-3.md`. Pregão = data com negócio no mercado à
# vista do COTAHIST guardado (F3-4a); o ano Y só está coberto pela carga do arquivo anual
# `COTAHIST_A{Y}` gerado em ou depois de 31/12/Y, ou do último pregão de dezembro guardado
# (decisão 44, BUG-3-41), ou, no ano ainda aberto, até a data de geração (inclusive: o arquivo
# gerado em D traz o pregão de D). Carga sem data de geração não
# cobre; o ano vem do nome do arquivo guardado (`cargas_cotahist.arquivo`).

MOTIVO_CALENDARIO_SEM_ANO = "calendário anual B3 sem a carga do COTAHIST anual de {ano}"
MOTIVO_CALENDARIO_GERACAO = (
    "calendário anual B3: COTAHIST anual de {ano} gerado em {geracao}, antes de {fim}"
)
MOTIVO_CALENDARIO_VAZIO = "calendário anual B3 sem pregões no intervalo"
MOTIVO_CALENDARIO_BANCO = "calendário anual B3: banco único indisponível"
MERCADO_A_VISTA = "010"  # o de `b3_cotahist`, sem importar o provedor (rede) aqui


def _ano_do_arquivo(arquivo: object) -> int | None:
    nome = str(arquivo or "").upper()
    if not (nome.startswith("COTAHIST_A") and nome.endswith(".ZIP")):
        return None
    ano = nome[len("COTAHIST_A") : -len(".ZIP")]
    return int(ano) if len(ano) == 4 and ano.isdigit() else None


def _ate_o_ultimo_pregao(necessario: date, pregoes: set[date]) -> date:
    """Decisão 44 (BUG-3-41): no último dia do mês, a cobertura vai até o último pregão do mês.

    O último pregão é o maior guardado no mês até `necessario`, por qualquer carga do COTAHIST
    (31/12 não tem pregão; o arquivo anual sai no último). Fora do fim do mês, ou sem pregão
    guardado no mês, vale o próprio dia.
    """
    if (necessario + timedelta(days=1)).month == necessario.month:
        return necessario
    do_mes = [
        p
        for p in pregoes
        if (p.year, p.month) == (necessario.year, necessario.month) and p <= necessario
    ]
    return max(do_mes, default=necessario)


def calendario_anual(
    pregoes: Iterable[date], cargas: Iterable[Mapping], inicio: date, fim: date
) -> dict | Abstencao:
    """Calendário de `inicio` a `fim` (inclusive) para `calendario_proventos_b3`, ou o motivo.

    `cargas`: as do COTAHIST (`arquivo`, `data_geracao` ISO, `coleta`, `hash_sha256`). Cada ano
    do intervalo precisa de uma carga do arquivo anual cuja geração alcance `fim` naquele ano
    (o ano todo, se gerado em ou depois de 31/12); quando o fim é o último dia de um mês, basta
    a geração no último pregão guardado do mês (decisão 44); vale a carga de geração mais nova, e no empate
    a primeira na ordem recebida. Os pregões são
    os de `pregoes` dentro do intervalo.
    """
    melhores: dict[int, Mapping] = {}
    for carga in cargas:
        ano = _ano_do_arquivo(carga.get("arquivo"))
        geracao = str(carga.get("data_geracao") or "")
        if ano is not None and geracao > str(
            melhores.get(ano, {}).get("data_geracao") or ""
        ):
            melhores[ano] = carga
    usadas = []
    guardados = {p for p in pregoes if inicio <= p <= fim}
    for ano in range(inicio.year, fim.year + 1):
        carga = melhores.get(ano)
        if carga is None:
            return Abstencao(MOTIVO_CALENDARIO_SEM_ANO.format(ano=ano))
        necessario = _ate_o_ultimo_pregao(min(fim, date(ano, 12, 31)), guardados)
        if str(carga["data_geracao"]) < necessario.isoformat():
            return Abstencao(
                MOTIVO_CALENDARIO_GERACAO.format(
                    ano=ano, geracao=carga["data_geracao"], fim=necessario.isoformat()
                )
            )
        usadas.append(carga)
    dentro = sorted(guardados)
    if not dentro:
        return Abstencao(MOTIVO_CALENDARIO_VAZIO)
    return {
        "fonte": "B3, COTAHIST anual: "
        + "; ".join(f"{c['arquivo']} (sha256 {c['hash_sha256']})" for c in usadas),
        "coleta": max(str(c["coleta"]) for c in usadas),
        "inicio": inicio.isoformat(),
        "fim": fim.isoformat(),
        "pregoes": [p.isoformat() for p in dentro],
    }


def calendario_do_banco(conn, inicio: date, fim: date) -> dict | Abstencao:
    """`calendario_anual` com os pregões e as cargas do COTAHIST do banco único."""
    if conn is None:
        return Abstencao(MOTIVO_CALENDARIO_BANCO)
    pregoes = [
        date.fromisoformat(d)
        for (d,) in conn.execute(
            "SELECT DISTINCT data FROM precos WHERE tipo_mercado = ? AND data BETWEEN ? AND ?",
            (MERCADO_A_VISTA, inicio.isoformat(), fim.isoformat()),
        )
    ]
    cargas = [
        {"arquivo": a, "data_geracao": g, "coleta": c, "hash_sha256": h}
        for a, g, c, h in conn.execute(
            "SELECT arquivo, data_geracao, coleta, hash_sha256 FROM cargas_cotahist "
            "ORDER BY arquivo, data_geracao, hash_sha256"
        )
    ]
    return calendario_anual(pregoes, cargas, inicio, fim)
