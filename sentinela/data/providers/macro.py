"""SIDRA 1737, Focus PIB, séries do SGS e calendários públicos, com cache observado e sem reserva."""

from __future__ import annotations

import calendar
import hashlib
import json
import logging
import math
import re
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from tempfile import NamedTemporaryFile
from zoneinfo import ZoneInfo

import requests

from sentinela.data import macro_por_data
from sentinela.data.taxas import Calendario

IBGE_CALENDARIO = "https://servicodados.ibge.gov.br/api/v3/calendario/9256"
FOCUS = "https://olinda.bcb.gov.br/olinda/servico/Expectativas/versao/v1/odata/ExpectativasMercadoAnuais"
ANBIMA = "https://www.anbima.com.br/feriados/fer_nacionais/{ano}.asp"
SGS = "https://api.bcb.gov.br/dados/serie/bcdata.sgs.{serie}/dados?formato=json"
TTL = 86400
FUSO = ZoneInfo("America/Sao_Paulo")
# Falha da fonte ou do formato vira abstenção com o motivo da exceção; KeyError e TypeError
# são erro do código (F2B-51, BUG-2B-31): vão para o log e têm motivo próprio.
FALHAS_DA_FONTE = (requests.RequestException, OSError, ValueError)
ERROS_DO_CODIGO = (KeyError, TypeError)

logger = logging.getLogger(__name__)


def divulgacao_ibge(texto: str) -> datetime:
    """Instante de divulgação do calendário do IBGE, no horário de Brasília (BUG-2B-32)."""
    return datetime.strptime(texto, "%d/%m/%Y %H:%M:%S").replace(tzinfo=FUSO)


def _falha_da_fonte(erro: Exception) -> dict:
    """Abstenção com a mensagem da falha; sem mensagem, o tipo (o motivo nunca sai vazio)."""
    return {"abstencao": str(erro) or type(erro).__name__}


def _erro_do_codigo(erro: Exception) -> dict:
    logger.error("erro inesperado no provedor macro", exc_info=erro)
    return {"abstencao": f"erro inesperado no provedor macro: {type(erro).__name__}"}


def _local(as_of: datetime) -> date:
    if as_of.tzinfo is None or as_of.utcoffset() is None:
        raise ValueError("as_of exige fuso horário")
    return as_of.astimezone(ZoneInfo("America/Sao_Paulo")).date()


def _numero(valor: object, nome: str) -> float:
    if valor is None or (isinstance(valor, str) and not valor.strip()):
        raise ValueError(f"insumo ausente: {nome}")
    try:
        if isinstance(valor, bool):
            raise TypeError("booleano não representa percentual")
        numero = float(valor)
    except (TypeError, ValueError) as erro:
        raise ValueError(f"insumo inválido: {nome}, tipo ou unidade") from erro
    if math.isnan(numero):
        raise ValueError(f"insumo inválido: {nome}, NaN")
    if math.isinf(numero):
        raise ValueError(f"insumo inválido: {nome}, infinito")
    if numero <= -100:
        raise ValueError(f"insumo fora do domínio: {nome}, exige fator positivo")
    return numero / 100


def ipca_da_janela(
    linhas: list[dict],
    publicacoes: dict[str, date],
    *,
    inicio: date,
    fim: date,
    as_of: datetime,
) -> dict:
    """Produto dos fatores mensais, mesma janela de doze meses da DFP."""
    dia = _local(as_of)
    if (
        inicio.day != 1
        or fim.day != calendar.monthrange(fim.year, fim.month)[1]
        or (fim.year - inicio.year) * 12 + fim.month - inicio.month != 11
    ):
        raise ValueError("janela contábil incompatível: exige 12 meses civis completos")
    valores = {}
    for linha in linhas:
        if linha.get("D1C") != "1" or linha.get("D2C") != "63":
            continue
        mes = linha["D3C"]
        if mes not in publicacoes or publicacoes[mes] >= dia:
            continue
        if linha.get("MN") != "%":
            raise ValueError("unidade do IPCA inválida")
        valor = _numero(linha.get("V"), "IPCA")
        if mes in valores and valores[mes] != valor:
            raise ValueError("IPCA conflitante")
        valores[mes] = valor
    if not valores:
        raise ValueError("IPCA publicado ausente")
    ultimo = max(valores)
    idade = dia.year * 12 + dia.month - (int(ultimo[:4]) * 12 + int(ultimo[4:]))
    if idade < 0 or idade > 2:
        raise ValueError("IPCA com cobertura desatualizada ou futura")
    meses = [
        f"{(inicio.year * 12 + inicio.month - 1 + n) // 12:04}{(inicio.year * 12 + inicio.month - 1 + n) % 12 + 1:02}"
        for n in range(12)
    ]
    if any(mes not in valores for mes in meses):
        raise ValueError("IPCA ausente na janela contábil")
    valor = math.prod(1 + valores[mes] for mes in meses) - 1
    if not math.isfinite(valor) or valor <= -1:
        raise ValueError("resultado não finito ou sem fator positivo")
    return {
        "valor": valor,
        "inicio": inicio.isoformat(),
        "fim": fim.isoformat(),
        "ultimo_mes_publicado": ultimo,
        "publicacao": max(publicacoes[m] for m in meses).isoformat(),
        "variavel": "63",
        "tabela": "1737",
        "unidade": "razão acumulada",
    }


def _encerramentos(exercicios: list[dict]) -> list[date]:
    """Os cinco encerramentos distintos, no fim do mês, em ordem."""
    finais = sorted(date.fromisoformat(e["fim"]) for e in exercicios)
    if len(finais) != 5 or len(set(finais)) != 5:
        raise ValueError("IPCA exige cinco encerramentos distintos")
    if any(d.day != calendar.monthrange(d.year, d.month)[1] for d in finais):
        raise ValueError("IPCA exige encerramento no fim do mês")
    return finais


def _publicacoes_ipca(itens: list[dict]) -> dict[str, date]:
    """Mês de referência (AAAAMM) → dia da divulgação, pelo calendário do IBGE."""
    publicacoes = {}
    for evento in itens:
        if evento.get("produto_id") == 9256:
            mes = f"{int(evento['ano_referencia_inicio']):04}{int(evento['mes_referencia_inicio']):02}"
            publicacoes[mes] = divulgacao_ibge(evento["data_divulgacao"]).date()
    return publicacoes


def indices_ipca(
    linhas: list[dict], publicacoes: dict[str, date], finais: list[date], dia: date
) -> dict[str, float]:
    """Índices relativos nos encerramentos, só com os meses divulgados antes de `dia`."""
    valores = {}
    for linha in linhas:
        if linha.get("D1C") != "1" or linha.get("D2C") != "63":
            continue
        mes = linha["D3C"]
        if mes not in publicacoes or publicacoes[mes] >= dia:
            continue
        if linha.get("MN") != "%":
            raise ValueError("unidade do IPCA inválida")
        valor = _numero(linha.get("V"), "IPCA")
        if mes in valores and valores[mes] != valor:
            raise ValueError("IPCA conflitante")
        valores[mes] = valor
    indices = {}
    acumulado = 1.0
    referencias = {d.strftime("%Y%m") for d in finais}
    primeiro = finais[0].year * 12 + finais[0].month - 1
    ultimo = finais[-1].year * 12 + finais[-1].month - 1
    for numero in range(primeiro, ultimo + 1):
        ano, mes_zero = divmod(numero, 12)
        mes = f"{ano:04}{mes_zero + 1:02}"
        if mes not in valores:
            raise ValueError(f"IPCA ausente ou não publicado na janela: {mes}")
        if numero != primeiro:
            acumulado *= 1 + valores[mes]
        if not math.isfinite(acumulado) or acumulado <= 0:
            raise ValueError("IPCA acumulado sem fator positivo finito")
        if mes in referencias:
            indices[f"{ano:04}-{mes_zero + 1:02}"] = acumulado
    return indices


def pib_focus(
    linhas: list[dict], edicoes: dict[date, datetime], *, as_of: datetime
) -> dict:
    """Base zero, maior horizonte na pesquisa da última edição devida."""
    _local(as_of)
    disponiveis = {d: p for d, p in edicoes.items() if p <= as_of}
    if not disponiveis:
        raise ValueError("edição Focus publicada ausente")
    pesquisa = max(disponiveis, key=disponiveis.get)
    selecionadas = [
        l
        for l in linhas
        if l.get("Indicador") == "PIB Total"
        and type(l.get("baseCalculo")) is int
        and l.get("baseCalculo") == 0
        and l.get("Data") == pesquisa.isoformat()
    ]
    if not selecionadas:
        raise ValueError("edição Focus devida indisponível")
    ano = max(int(l["DataReferencia"]) for l in selecionadas)
    valores = {
        _numero(l.get("Mediana"), "PIB")
        for l in selecionadas
        if int(l["DataReferencia"]) == ano
    }
    if len(valores) != 1:
        raise ValueError("PIB conflitante")
    return {
        "valor": valores.pop(),
        "ano": ano,
        "pesquisa": pesquisa.isoformat(),
        "publicacao": disponiveis[pesquisa].isoformat(),
        "baseCalculo": 0,
        "estatistica": "Mediana",
        "proxima_publicacao": min(
            (p for p in edicoes.values() if p > as_of), default=None
        ),
    }


@dataclass(frozen=True)
class SnapshotMacro:
    conteudo: str
    fonte: str
    coleta: str
    hash_sha256: str
    aviso: str | None = None

    def proveniencia(self) -> dict:
        return {
            "fonte": self.fonte,
            "data_coleta": self.coleta,
            "hash_sha256": self.hash_sha256,
            "aviso": self.aviso,
        }


class MacroProvider:
    def __init__(self, cache_dir: str | Path = "data/macro") -> None:
        self.cache_dir = Path(cache_dir)

    def baixar(self, url: str, instante: datetime) -> SnapshotMacro:
        _local(instante)
        caminho = self.cache_dir / (hashlib.sha256(url.encode()).hexdigest() + ".json")
        anterior = None
        if caminho.exists():
            dados = json.loads(caminho.read_text(encoding="utf-8"))
            anterior = SnapshotMacro(**dados)
            if (
                anterior.fonte != url
                or hashlib.sha256(anterior.conteudo.encode()).hexdigest()
                != anterior.hash_sha256
            ):
                raise ValueError("cache macro sem integridade")
            idade = (instante - datetime.fromisoformat(anterior.coleta)).total_seconds()
            if idade < 0:
                raise ValueError("coleta macro posterior ao as_of")
            if idade < TTL:
                return anterior
        try:
            resposta = requests.get(url, timeout=60)
            resposta.raise_for_status()
        except requests.RequestException:
            if anterior is None:
                raise
            return SnapshotMacro(
                anterior.conteudo,
                url,
                anterior.coleta,
                anterior.hash_sha256,
                "fonte indisponível; cache exige guardas de referência",
            )
        conteudo = resposta.text
        resultado = SnapshotMacro(
            conteudo,
            url,
            instante.astimezone(UTC).isoformat(),
            hashlib.sha256(conteudo.encode()).hexdigest(),
        )
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        with NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=self.cache_dir, delete=False
        ) as arquivo:
            temporario = Path(arquivo.name)
            json.dump(resultado.__dict__, arquivo, ensure_ascii=False)
        try:
            temporario.replace(caminho)
        finally:
            temporario.unlink(missing_ok=True)
        return resultado

    def calendario(self, ano: int, instante: datetime) -> Calendario:
        snapshot = self.baixar(ANBIMA.format(ano=ano), instante)
        datas = re.findall(r">\s*(\d{1,2}/\d{1,2}/\d{2})\s*<", snapshot.conteudo)
        feriados = frozenset(
            datetime.strptime(d + "+0000", "%d/%m/%y%z").date() for d in datas
        )
        if not feriados or any(d.year != ano for d in feriados):
            raise ValueError("calendário ANBIMA inválido ou de outro ano")
        return Calendario(
            date(ano, 1, 1), date(ano, 12, 31), feriados, snapshot.proveniencia()
        )

    def inflacao(
        self,
        inicio: date,
        fim: date,
        instante: datetime,
        coleta: datetime | None = None,
    ) -> dict:
        """IPCA da janela contábil divulgado até `instante`; baixa com `coleta` (F3-1c-a)."""
        dia = _local(instante)
        coleta = instante if coleta is None else coleta
        agenda = self.baixar(IBGE_CALENDARIO, coleta)
        publicacoes = {}
        for evento in json.loads(agenda.conteudo)["items"]:
            if evento.get("produto_id") == 9256:
                mes = f"{int(evento['ano_referencia_inicio']):04}{int(evento['mes_referencia_inicio']):02}"
                publicacoes[mes] = divulgacao_ibge(evento["data_divulgacao"]).date()
        publicados = [mes for mes, entrega in publicacoes.items() if entrega < dia]
        if not publicados:
            raise ValueError("IPCA publicado ausente no calendário")
        ultimo = max(publicados)
        url = f"https://apisidra.ibge.gov.br/values/t/1737/n1/all/v/63/p/{inicio:%Y%m}-{ultimo}?formato=json"
        serie = self.baixar(url, coleta)
        resultado = ipca_da_janela(
            json.loads(serie.conteudo),
            publicacoes,
            inicio=inicio,
            fim=fim,
            as_of=instante,
        )
        return resultado | {
            "proveniencia": serie.proveniencia(),
            "calendario": agenda.proveniencia(),
        }

    def ipca_serie(self, exercicios: list[dict], instante: datetime) -> dict:
        """Índices relativos nos cinco encerramentos, pela variável mensal 63.

        A base arbitrária 1 no primeiro encerramento cancela na razão I_T/I_t.
        Só os meses posteriores a ele entram no produto; cada mês, inclusive o
        primeiro encerramento, exige publicação demonstrada no calendário IBGE.
        A idade do último IPCA corrente não limita esta janela histórica.
        """
        dia = _local(instante)
        finais = _encerramentos(exercicios)
        agenda = self.baixar(IBGE_CALENDARIO, instante)
        publicacoes = _publicacoes_ipca(json.loads(agenda.conteudo)["items"])
        inicio, fim = finais[0], finais[-1]
        url = f"https://apisidra.ibge.gov.br/values/t/1737/n1/all/v/63/p/{inicio:%Y%m}-{fim:%Y%m}?formato=json"
        serie = self.baixar(url, instante)
        indices = indices_ipca(json.loads(serie.conteudo), publicacoes, finais, dia)
        return {
            "fonte": serie.fonte,
            "coleta": serie.coleta,
            "indices": indices,
            "publicacoes": {
                d.strftime("%Y-%m"): publicacoes[d.strftime("%Y%m")].isoformat()
                for d in finais
            },
            "proveniencia": serie.proveniencia(),
            "calendario": agenda.proveniencia(),
            "variavel": "63",
            "tabela": "1737",
        }

    def pib(self, instante: datetime, coleta: datetime | None = None) -> dict:
        """Edição Focus devida até `instante`; baixa com `coleta` (F3-1c-a)."""
        dia = _local(instante)
        coleta = instante if coleta is None else coleta
        agenda = self.baixar(AGENDA_FOCUS.format(ano=dia.year), coleta)
        edicoes = edicoes_focus(agenda.conteudo)
        devidas = [d for d, p in edicoes.items() if p <= instante]
        if not devidas:
            # BUG-3-21: antes do primeiro Focus do ano, a edição devida é a de dezembro, e o
            # calendário informado é o da agenda que a traz.
            agenda = self.baixar(AGENDA_FOCUS.format(ano=dia.year - 1), coleta)
            edicoes = edicoes_focus(agenda.conteudo) | edicoes
        devidas = [d for d, p in edicoes.items() if p <= instante]
        if not devidas:
            raise ValueError("edição Focus devida ausente no calendário")
        pesquisa = max(devidas)
        url = (
            FOCUS
            + f"?$format=json&$filter=Indicador%20eq%20%27PIB%20Total%27%20and%20Data%20eq%20%27{pesquisa}%27"
        )
        serie = self.baixar(url, coleta)
        resultado = pib_focus(
            json.loads(serie.conteudo)["value"], edicoes, as_of=instante
        )
        proxima = resultado["proxima_publicacao"]
        resultado["proxima_publicacao"] = proxima.isoformat() if proxima else None
        return resultado | {
            "proveniencia": serie.proveniencia(),
            "calendario": agenda.proveniencia(),
        }

    def publicacoes_ipca(self, instante: datetime) -> dict:
        """Dia de divulgação de cada mês do IPCA (`AAAAMM` → data), pelo calendário do
        IBGE (decisão 31, F3-1c-a), com a proveniência da agenda; falha vira abstenção."""
        try:
            agenda = self.baixar(IBGE_CALENDARIO, instante)
            publicacoes = {
                f"{int(e['ano_referencia_inicio']):04}{int(e['mes_referencia_inicio']):02}": (
                    divulgacao_ibge(e["data_divulgacao"]).date()
                )
                for e in json.loads(agenda.conteudo)["items"]
                if e.get("produto_id") == 9256
            }
        except FALHAS_DA_FONTE as erro:
            return _falha_da_fonte(erro)
        except ERROS_DO_CODIGO as erro:
            return _erro_do_codigo(erro)
        return {"publicacoes": publicacoes, "proveniencia": agenda.proveniencia()}

    def serie_sgs(self, serie: int, fim: date, instante: datetime) -> dict:
        """Série completa do SGS até `fim` (F3-1b): diárias em janelas de até 10 anos.

        Devolve `observacoes`, `coleta` (data local da coleta mais antiga, limite de
        divulgação do que está na série) e `proveniencia` de cada janela; falha da fonte ou do
        formato vira `{"abstencao": motivo}`.
        """
        base = SGS.format(serie=serie)
        inicio = macro_por_data.INICIO_SERIE.get(serie)
        urls = (
            [
                f"{base}&dataInicial={de:%d/%m/%Y}&dataFinal={ate:%d/%m/%Y}"
                for de, ate in macro_por_data.janelas(inicio, fim)
            ]
            if inicio is not None
            else [base]
        )
        try:
            snapshots = [self.baixar(url, instante) for url in urls]
            observacoes = macro_por_data.juntar(
                macro_por_data.ler_sgs(s.conteudo) for s in snapshots
            )
        except FALHAS_DA_FONTE as erro:
            return _falha_da_fonte(erro)
        except ERROS_DO_CODIGO as erro:
            return _erro_do_codigo(erro)
        if not snapshots:
            return {"abstencao": f"série SGS {serie} sem janela até {fim.isoformat()}"}
        coleta = min(_local(datetime.fromisoformat(s.coleta)) for s in snapshots)
        return {
            "observacoes": observacoes,
            "coleta": coleta,
            "proveniencia": [s.proveniencia() for s in snapshots],
        }

    def registro(
        self,
        instante: datetime,
        janela: tuple[date, date] | None = None,
        coleta: datetime | None = None,
    ) -> dict:
        """Orquestra fontes; dado sem prova não vira constante de contingência.

        Sem a taxa real, `{"abstencao": motivo}`: o da `Abstencao` da cesta ou o da falha da
        fonte; erro do código tem motivo próprio e vai para o log (F2B-51).

        `coleta` (F3-1c-a): instante real dos downloads, posterior ao corte `instante` numa
        data passada (DD-18); o Tesouro passa então pelo leitor histórico (DD-37) e o registro
        leva a coleta e o aviso. Sem `coleta`, o corte é a própria coleta, como na 2B.
        """
        from sentinela.data import taxas
        from sentinela.data.providers.tesouro import (
            AVISO_HISTORICO,
            TesouroProvider,
            ler_historico,
            ler_snapshot,
            selecionar_ofertas,
        )

        historico = coleta is not None and coleta > instante
        coleta = instante if coleta is None else coleta
        try:
            arquivo = TesouroProvider(self.cache_dir / "tesouro").baixar(coleta)
            leitor = ler_historico if historico else ler_snapshot
            cesta = selecionar_ofertas(leitor(arquivo, as_of=instante))
            dia = _local(instante)
            ano_inicial = cesta.data_base.year if cesta.data_base else dia.year
            calendarios = [
                self.calendario(ano, coleta) for ano in range(ano_inicial, dia.year + 1)
            ]
            calendario = Calendario(
                date(ano_inicial, 1, 1),
                date(dia.year, 12, 31),
                frozenset().union(*(c.feriados for c in calendarios)),
                {"anos": [c.proveniencia for c in calendarios]},
            )
            resultado = taxas.calcular(
                cesta,
                as_of=instante,
                calendario=calendario,
                proveniencia=arquivo.proveniencia.para_dict()
                if arquivo.proveniencia
                else {},
            )
            if isinstance(resultado, taxas.Abstencao):
                return {"abstencao": resultado.motivo}
        except FALHAS_DA_FONTE as erro:
            return _falha_da_fonte(erro)
        except ERROS_DO_CODIGO as erro:
            return _erro_do_codigo(erro)
        if historico:
            resultado["coleta"] = coleta.isoformat()
            resultado["avisos"] = [AVISO_HISTORICO]
        if janela is None:
            resultado["inflacao"] = {
                "abstencao": "janela contábil anual não demonstrada"
            }
        else:
            try:
                resultado["inflacao"] = (
                    self.inflacao(*janela, instante, coleta)
                    if historico
                    else self.inflacao(*janela, instante)
                )
            except FALHAS_DA_FONTE as erro:
                resultado["inflacao"] = _falha_da_fonte(erro)
            except ERROS_DO_CODIGO as erro:
                resultado["inflacao"] = _erro_do_codigo(erro)
        try:
            resultado["pib"] = (
                self.pib(instante, coleta) if historico else self.pib(instante)
            )
        except FALHAS_DA_FONTE as erro:
            resultado["pib"] = _falha_da_fonte(erro)
        except ERROS_DO_CODIGO as erro:
            resultado["pib"] = _erro_do_codigo(erro)
        return resultado


# --- Insumos por data no banco único (F3-1c, tabela series_macro) ----------------------

AGENDA_FOCUS = (
    "https://www.bcb.gov.br/api/servico/sitebcb/calendario?inicioAgenda=%27{ano}-01-01%27"
    "&fimAgenda=%27{ano}-12-31%27&lista=Focus"
)
SEM_NTNB_NO_BANCO = "series_macro sem NTN-B até a data"


def edicoes_focus(conteudo: str) -> dict[date, datetime]:
    """Pesquisa (sexta anterior) → instante de publicação, pela agenda do BCB.

    Mesma leitura de `MacroProvider.pib`, para a gravação por data.
    """
    edicoes = {}
    for evento in json.loads(conteudo)["conteudo"]:
        if evento.get("evento") == "Relatório Focus":
            publicacao = datetime.fromisoformat(evento["dataEvento"])
            dia_edicao = publicacao.astimezone(FUSO).date()
            pesquisa = dia_edicao - timedelta(days=(dia_edicao.weekday() - 4) % 7 or 7)
            edicoes[pesquisa] = publicacao
    return edicoes


def _inserir(conn, linhas: list[tuple]) -> int:
    conn.executemany(
        "INSERT INTO series_macro (serie, data, valor, divulgacao, detalhe_json, fonte, "
        "coleta, hash_sha256) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        linhas,
    )
    return len(linhas)


def _detalhe(dados: dict) -> str:
    return json.dumps(dados, ensure_ascii=False, sort_keys=True)


def gravar_series(
    conn,
    provedor: MacroProvider,
    *,
    coleta: datetime,
    datas: list[date],
    janela: tuple[date, date] | None = None,
) -> dict:
    """Grava em `series_macro` os insumos da taxa real das datas pedidas (F3-1c).

    Uma linha por observação, com a linha original da fonte, a fonte, a coleta e o hash do
    conteúdo baixado: NTN-B (as linhas dos títulos da cesta do CSV histórico do Tesouro, uma vez cada; linha diferente do mesmo título e data-base com sufixo na série, BUG-3-19), feriados ANBIMA
    dos anos das datas e do anterior, edições do Focus e a pesquisa devida em cada data, o
    calendário do IBGE e o IPCA da SIDRA na janela, e a Selic (SGS 432). Cada família que
    falha fica no resumo com o motivo; as outras são gravadas.
    """
    from sentinela.data.proveniencia import hash_sha256 as proveniencia_hash
    from sentinela.data.providers import tesouro

    coleta_iso = coleta.astimezone(UTC).isoformat()
    resumo: dict = {}
    anos = sorted({ano for d in datas for ano in (d.year - 1, d.year)})

    def familia(nome, gravar):
        try:
            with conn:
                resumo[nome] = gravar()
        except FALHAS_DA_FONTE as erro:
            resumo[nome] = _falha_da_fonte(erro)
        except ERROS_DO_CODIGO as erro:
            resumo[nome] = _erro_do_codigo(erro)

    def _tesouro():
        arquivo = tesouro.TesouroProvider(provedor.cache_dir / "tesouro").baixar(coleta)
        if arquivo.proveniencia is None:
            raise ValueError("proveniência ausente")
        if proveniencia_hash(arquivo.caminho) != arquivo.proveniencia.hash_sha256:
            raise ValueError("conteúdo diverge da proveniência")
        texto = arquivo.caminho.read_text(encoding="utf-8-sig")
        cabecalho, *corpo = texto.splitlines()
        colunas = cabecalho.split(";")
        linhas = []
        vistas: dict[tuple, list[str]] = {}
        for linha in corpo:
            campos = dict(zip(colunas, linha.split(";"), strict=False))
            if campos.get("Tipo Titulo") not in tesouro._TIPOS:
                continue  # fora da cesta, como em `tesouro.ler_csv` (BUG-3-19)
            dia, mes, ano = campos["Data Base"].split("/")
            par = (
                campos["Tipo Titulo"],
                campos["Data Vencimento"],
                f"{ano}-{mes}-{dia}",
            )
            anteriores = vistas.setdefault(par, [])
            if linha in anteriores:
                continue  # repetida idêntica: uma vez
            anteriores.append(linha)
            # BUG-3-19: linha diferente do mesmo título e data-base fica como o arquivo a traz,
            # com sufixo na série; a leitura pelo banco a vê, e o `ler_csv` marca o conflito
            # da data-base como no caminho histórico, sem abortar a gravação.
            sufixo = f"|{len(anteriores)}" if len(anteriores) > 1 else ""
            linhas.append(
                (
                    f"tesouro|{campos['Tipo Titulo']}|{campos['Data Vencimento']}{sufixo}",
                    f"{ano}-{mes}-{dia}",
                    None,
                    None,
                    _detalhe({"cabecalho": cabecalho, "linha": linha}),
                    tesouro.URL,
                    coleta_iso,
                    arquivo.proveniencia.hash_sha256,
                )
            )
        return _inserir(conn, linhas)

    def _anbima():
        """Ano a ano: um ano sem calendário fica no resumo, os outros são gravados."""
        total = 0
        for ano in anos:
            try:
                calendario = provedor.calendario(ano, coleta)
            except FALHAS_DA_FONTE as erro:
                resumo[f"anbima_{ano}"] = _falha_da_fonte(erro)
                continue
            prov = calendario.proveniencia
            fonte = prov.get("fonte", ANBIMA.format(ano=ano))
            hash_ = prov.get("hash_sha256", "")
            linhas = [
                (
                    "anbima_ano",
                    f"{ano}-01-01",
                    None,
                    None,
                    _detalhe({"proveniencia": prov}),
                    fonte,
                    coleta_iso,
                    hash_,
                )
            ]
            linhas += [
                (
                    "anbima_feriado",
                    f.isoformat(),
                    None,
                    None,
                    _detalhe({"ano": ano}),
                    fonte,
                    coleta_iso,
                    hash_,
                )
                for f in sorted(calendario.feriados)
            ]
            total += _inserir(conn, linhas)
        return total

    def _focus():
        linhas, pesquisas, todas = [], set(), {}
        # BUG-3-21: a agenda do ano anterior também, porque antes do primeiro Focus do ano a
        # edição devida é a de dezembro; cada pesquisa entra uma vez.
        for ano in sorted(
            {a for d in datas for a in (d.year - 1, d.year)}, reverse=True
        ):
            agenda = provedor.baixar(AGENDA_FOCUS.format(ano=ano), coleta)
            novas = {
                p: pub
                for p, pub in edicoes_focus(agenda.conteudo).items()
                if p not in todas
            }
            todas |= novas
            linhas += [
                (
                    "focus_edicao",
                    p.isoformat(),
                    None,
                    publicacao.isoformat(),
                    _detalhe({}),
                    agenda.fonte,
                    coleta_iso,
                    agenda.hash_sha256,
                )
                for p, publicacao in sorted(novas.items())
            ]
        for d in datas:
            # a edição devida no começo e no fim do dia: qualquer instante de D tem a sua
            for limite in (datetime.min.time(), datetime.max.time()):
                corte = datetime.combine(d, limite, FUSO)
                devidas = [p for p, pub in todas.items() if pub <= corte]
                if devidas:
                    pesquisas.add(max(devidas))
        for pesquisa in sorted(pesquisas):
            url = (
                FOCUS
                + f"?$format=json&$filter=Indicador%20eq%20%27PIB%20Total%27%20and%20Data%20eq%20%27{pesquisa}%27"
            )
            serie = provedor.baixar(url, coleta)
            linhas += [
                (
                    f"focus_pib|{i}",
                    pesquisa.isoformat(),
                    linha.get("Mediana"),
                    None,
                    _detalhe(linha),
                    serie.fonte,
                    coleta_iso,
                    serie.hash_sha256,
                )
                for i, linha in enumerate(json.loads(serie.conteudo)["value"])
            ]
        return _inserir(conn, linhas)

    def _ipca():
        agenda = provedor.publicacoes_ipca(coleta)
        if "abstencao" in agenda:
            raise ValueError(agenda["abstencao"])
        prov = agenda["proveniencia"]
        linhas = [
            (
                "ipca_divulgacao",
                f"{mes[:4]}-{mes[4:]}-01",
                None,
                dia.isoformat(),
                _detalhe({}),
                prov["fonte"],
                coleta_iso,
                prov["hash_sha256"],
            )
            for mes, dia in sorted(agenda["publicacoes"].items())
        ]
        publicados = {
            m
            for m, dia in agenda["publicacoes"].items()
            if dia < coleta.astimezone(FUSO).date()
        }
        # BUG-3-20: sem mês publicado, a agenda é gravada assim mesmo; e só meses publicados
        # têm o valor convertido (o SIDRA traz o mês ainda não divulgado com `V = "..."`).
        if janela is not None and publicados:
            url = f"https://apisidra.ibge.gov.br/values/t/1737/n1/all/v/63/p/{janela[0]:%Y%m}-{max(publicados)}?formato=json"
            serie = provedor.baixar(url, coleta)
            linhas += [
                (
                    "ipca_sidra",
                    f"{l['D3C'][:4]}-{l['D3C'][4:]}-01",
                    _numero(l.get("V"), "IPCA"),
                    None,
                    _detalhe(l),
                    serie.fonte,
                    coleta_iso,
                    serie.hash_sha256,
                )
                for l in json.loads(serie.conteudo)
                if l.get("D1C") == "1"
                and l.get("D2C") == "63"
                and str(l.get("D3C")) in publicados
            ]
        return _inserir(conn, linhas)

    def _selic():
        """Cada observação com a fonte e o hash da janela do SGS que a devolveu (BUG-3-18).

        A janela de cada proveniência vem da própria URL (`dataInicial` e `dataFinal`); sem
        elas, a coleta foi a série inteira numa só chamada. Observação fora de toda janela,
        ou em mais de uma, abstém a família: nunca leva a proveniência de outra janela.
        """
        dados = provedor.serie_sgs(macro_por_data.SELIC_META, max(datas), coleta)
        if "abstencao" in dados:
            raise ValueError(dados["abstencao"])
        if not dados["proveniencia"]:
            raise ValueError("Selic sem proveniência da coleta")
        janelas = []
        for prov in dados["proveniencia"]:
            casado = re.search(
                r"[?&]dataInicial=([^&]+)&dataFinal=([^&]+)", prov["fonte"]
            )
            if casado is None:
                if "dataInicial" in prov["fonte"] or "dataFinal" in prov["fonte"]:
                    raise ValueError(f"Selic: janela ilegível na fonte {prov['fonte']}")
                janelas.append((prov, None, None))
            else:
                de, ate = (macro_por_data.data_sgs(t) for t in casado.groups())
                janelas.append((prov, de, ate))
        linhas = []
        for o in dados["observacoes"]:
            donos = [
                prov for prov, de, ate in janelas if de is None or de <= o.data <= ate
            ]
            if len(donos) != 1:
                raise ValueError(
                    f"Selic: observação de {o.data.isoformat()} sem janela única da coleta"
                )
            linhas.append(
                (
                    "sgs_432",
                    o.data.isoformat(),
                    o.valor,
                    None,
                    _detalhe({}),
                    donos[0]["fonte"],
                    coleta_iso,
                    donos[0]["hash_sha256"],
                )
            )
        return _inserir(conn, linhas)

    familia("tesouro", _tesouro)
    familia("anbima", _anbima)
    familia("focus", _focus)
    familia("ipca", _ipca)
    familia("selic", _selic)
    return resumo


def _ultimas(conn, condicao: str, parametros: tuple) -> list[tuple]:
    """Linhas de cada (série, data) na coleta mais recente; `condicao` vem só deste módulo."""
    return conn.execute(
        "SELECT s.serie, s.data, s.valor, s.divulgacao, s.detalhe_json, s.fonte, s.coleta, "
        "s.hash_sha256 FROM series_macro s WHERE " + condicao + " AND s.coleta = ("
        "SELECT MAX(t.coleta) FROM series_macro t WHERE t.serie = s.serie AND t.data = s.data"
        ") ORDER BY s.serie, s.data",
        parametros,
    ).fetchall()


def registro_do_banco(
    conn, instante: datetime, janela: tuple[date, date] | None = None
) -> dict:
    """Registro da taxa real em `instante` só com o que está em `series_macro` (F3-1c).

    Os mesmos cálculos do caminho histórico (F3-1c-a): linhas do Tesouro com data-base
    anterior ao dia, calendário ANBIMA dos anos, edição Focus devida e IPCA divulgado até o
    instante. Sem linha no banco, abstém sem contingência numérica.
    """
    from sentinela.data import taxas
    from sentinela.data.providers.tesouro import (
        AVISO_HISTORICO,
        URL,
        ler_csv,
        selecionar_ofertas,
    )

    dia = _local(instante)
    try:
        # BUG-3-23: cada coleta traz o CSV histórico inteiro; vale a coleta mais recente da
        # família, não a mais recente por série e data (uma linha conflitante de uma coleta
        # antiga, com sufixo na série, não pode sobreviver ao arquivo corrigido).
        tesouro_linhas = _ultimas(
            conn,
            "s.serie LIKE 'tesouro|%' AND s.data < ? AND s.coleta = ("
            "SELECT MAX(t.coleta) FROM series_macro t WHERE t.serie LIKE 'tesouro|%')",
            (dia.isoformat(),),
        )
        if not tesouro_linhas:
            return {"abstencao": SEM_NTNB_NO_BANCO}
        detalhes = [json.loads(linha[4]) for linha in tesouro_linhas]
        texto = (
            "\n".join([detalhes[0]["cabecalho"], *(d["linha"] for d in detalhes)])
            + "\n"
        )
        cesta = selecionar_ofertas(ler_csv(texto, as_of=dia, validar_aplicacao=False))
        ano_inicial = cesta.data_base.year if cesta.data_base else dia.year
        anos = _ultimas(
            conn,
            "s.serie = 'anbima_ano' AND s.data >= ? AND s.data <= ?",
            (f"{ano_inicial}-01-01", f"{dia.year}-01-01"),
        )
        if len(anos) != dia.year - ano_inicial + 1:
            return {"abstencao": "calendário ANBIMA ausente no banco"}
        feriados = _ultimas(
            conn,
            "s.serie = 'anbima_feriado' AND s.data >= ? AND s.data <= ?",
            (f"{ano_inicial}-01-01", f"{dia.year}-12-31"),
        )
        calendario = Calendario(
            date(ano_inicial, 1, 1),
            date(dia.year, 12, 31),
            frozenset(date.fromisoformat(f[1]) for f in feriados),
            {"anos": [json.loads(a[4])["proveniencia"] for a in anos]},
        )
        mais_recente = max(tesouro_linhas, key=lambda linha: linha[6])
        coleta = mais_recente[6]
        resultado = taxas.calcular(
            cesta,
            as_of=instante,
            calendario=calendario,
            proveniencia={
                "fonte": URL,
                "data_coleta": coleta,
                "hash_sha256": mais_recente[7],
                "banco": "series_macro",
            },
        )
        if isinstance(resultado, taxas.Abstencao):
            return {"abstencao": resultado.motivo}
    except FALHAS_DA_FONTE as erro:
        return _falha_da_fonte(erro)
    except ERROS_DO_CODIGO as erro:
        return _erro_do_codigo(erro)
    resultado["coleta"] = coleta
    resultado["avisos"] = [AVISO_HISTORICO]
    resultado["inflacao"] = (
        {"abstencao": "janela contábil anual não demonstrada"}
        if janela is None
        else _inflacao_do_banco(conn, janela, instante)
    )
    resultado["pib"] = _pib_do_banco(conn, instante)
    return resultado


def _proveniencia_das_linhas(linhas: list[tuple]) -> dict:
    """Proveniência no formato do `SnapshotMacro` (BUG-3-20): a da coleta mais recente lida."""
    linha = max(linhas, key=lambda l: l[6])
    return {
        "fonte": linha[5],
        "data_coleta": linha[6],
        "hash_sha256": linha[7],
        "aviso": None,
    }


def _inflacao_do_banco(conn, janela: tuple[date, date], instante: datetime) -> dict:
    try:
        agenda = _ultimas(
            conn, "s.serie = 'ipca_divulgacao' AND s.divulgacao IS NOT NULL", ()
        )
        publicacoes = {
            linha[1][:4] + linha[1][5:7]: date.fromisoformat(linha[3])
            for linha in agenda
        }
        sidra = _ultimas(conn, "s.serie = 'ipca_sidra'", ())
        linhas = [json.loads(linha[4]) for linha in sidra]
        if not publicacoes or not linhas:
            return {"abstencao": "IPCA ausente no banco"}
        resultado = ipca_da_janela(
            linhas, publicacoes, inicio=janela[0], fim=janela[1], as_of=instante
        )
        return resultado | {
            "proveniencia": _proveniencia_das_linhas(sidra),
            "calendario": _proveniencia_das_linhas(agenda),
        }
    except FALHAS_DA_FONTE as erro:
        return _falha_da_fonte(erro)
    except ERROS_DO_CODIGO as erro:
        return _erro_do_codigo(erro)


def ipca_serie_do_banco(conn, exercicios: list[dict], instante: datetime) -> dict:
    """Série do IPCA dos cinco encerramentos só com o que está em `series_macro` (F3-8f).

    A mesma conta de `MacroProvider.ipca_serie` (`indices_ipca`), sobre a agenda do IBGE e os
    meses do SIDRA gravados por `gravar_series`, cada linha da coleta mais recente: só entra o
    mês com data de divulgação guardada e anterior ao dia de `instante` (decisão 31). Sem
    linha no banco, abstém sem contingência numérica. Erro do SQLite sobe para quem chama.
    """
    try:
        dia = _local(instante)
        finais = _encerramentos(exercicios)
        agenda = _ultimas(
            conn, "s.serie = 'ipca_divulgacao' AND s.divulgacao IS NOT NULL", ()
        )
        sidra = _ultimas(
            conn,
            "s.serie = 'ipca_sidra' AND s.data >= ? AND s.data <= ?",
            (f"{finais[0]:%Y-%m}-01", f"{finais[-1]:%Y-%m}-01"),
        )
        if not agenda or not sidra:
            return {"abstencao": "IPCA ausente no banco"}
        publicacoes = {
            linha[1][:4] + linha[1][5:7]: date.fromisoformat(linha[3])
            for linha in agenda
        }
        indices = indices_ipca(
            [json.loads(linha[4]) for linha in sidra], publicacoes, finais, dia
        )
    except FALHAS_DA_FONTE as erro:
        return _falha_da_fonte(erro)
    except ERROS_DO_CODIGO as erro:
        return _erro_do_codigo(erro)
    proveniencia = _proveniencia_das_linhas(sidra)
    return {
        "fonte": proveniencia["fonte"],
        "coleta": proveniencia["data_coleta"],
        "indices": indices,
        "publicacoes": {
            d.strftime("%Y-%m"): publicacoes[d.strftime("%Y%m")].isoformat()
            for d in finais
        },
        "proveniencia": proveniencia,
        "calendario": _proveniencia_das_linhas(agenda),
        "variavel": "63",
        "tabela": "1737",
        "banco": "series_macro",
    }


def _pib_do_banco(conn, instante: datetime) -> dict:
    try:
        dia = _local(instante)
        agenda = [
            linha
            for linha in _ultimas(
                conn,
                "s.serie = 'focus_edicao' AND s.data >= ? AND s.data <= ?",
                # o ano anterior inteiro: a pesquisa da última edição de dezembro pode cair
                # antes do dia 25 (edição de 27/12/2027, pesquisa de 24/12; BUG-3-21)
                (f"{dia.year - 1}-01-01", f"{dia.year}-12-31"),
            )
        ]
        edicoes = {
            date.fromisoformat(linha[1]): datetime.fromisoformat(linha[3])
            for linha in agenda
        }
        devidas = [p for p, pub in edicoes.items() if pub <= instante]
        if not devidas:
            return {"abstencao": "edição Focus devida ausente no banco"}
        serie = _ultimas(
            conn,
            "s.serie LIKE 'focus_pib|%' AND s.data = ?",
            (max(devidas).isoformat(),),
        )
        resultado = pib_focus(
            [json.loads(linha[4]) for linha in serie], edicoes, as_of=instante
        )
    except FALHAS_DA_FONTE as erro:
        return _falha_da_fonte(erro)
    except ERROS_DO_CODIGO as erro:
        return _erro_do_codigo(erro)
    proxima = resultado["proxima_publicacao"]
    resultado["proxima_publicacao"] = proxima.isoformat() if proxima else None
    # BUG-3-20: o mesmo formato do caminho histórico (`MacroProvider.pib`); o calendário é o
    # da agenda que traz a edição devida (BUG-3-21).
    return resultado | {
        "proveniencia": _proveniencia_das_linhas(serie),
        "calendario": _proveniencia_das_linhas(
            [linha for linha in agenda if linha[1] == max(devidas).isoformat()]
        ),
    }


# --- CDI (SGS 12) em `benchmarks` (F3-7a, decisão 7) ------------------------------------------


def _janelas_da_coleta(
    dados: dict, rotulo: str
) -> list[tuple[dict, date | None, date | None]]:
    """Janela de cada proveniência pela própria URL (`dataInicial`, `dataFinal`), BUG-3-18."""
    janelas = []
    for prov in dados["proveniencia"]:
        casado = re.search(r"[?&]dataInicial=([^&]+)&dataFinal=([^&]+)", prov["fonte"])
        if casado is None:
            if "dataInicial" in prov["fonte"] or "dataFinal" in prov["fonte"]:
                raise ValueError(f"{rotulo}: janela ilegível na fonte {prov['fonte']}")
            janelas.append((prov, None, None))
        else:
            de, ate = (macro_por_data.data_sgs(t) for t in casado.groups())
            janelas.append((prov, de, ate))
    return janelas


def gravar_cdi(conn, provedor, fim: date, coleta: datetime) -> dict:
    """Grava a taxa diária do CDI (SGS 12, % ao dia) até `fim` em `benchmarks`.

    Cada observação leva a URL e o hash da janela do SGS que a devolveu (como a Selic,
    BUG-3-18); observação fora de toda janela ou em mais de uma recusa a carga inteira. Já
    gravada pela mesma janela (mesmo hash), conta como repetida. `valor_texto` é o número lido.
    """
    if coleta.utcoffset() is None:
        raise ValueError("coleta exige fuso horário")
    dados = provedor.serie_sgs(macro_por_data.CDI, fim, coleta)
    if "abstencao" in dados:
        raise ValueError(dados["abstencao"])
    if not dados["proveniencia"]:
        raise ValueError("CDI sem proveniência da coleta")
    janelas = _janelas_da_coleta(dados, "CDI")
    linhas = []
    for o in dados["observacoes"]:
        donos = [p for p, de, ate in janelas if de is None or de <= o.data <= ate]
        if len(donos) != 1:
            raise ValueError(
                f"CDI: observação de {o.data.isoformat()} sem janela única da coleta"
            )
        linhas.append(
            (
                "CDI",
                o.data.isoformat(),
                o.valor,
                repr(o.valor),
                donos[0]["fonte"],
                coleta.isoformat(),
                donos[0]["hash_sha256"],
            )
        )
    resumo = {"inseridos": 0, "repetidos": 0}
    conn.execute("SAVEPOINT cdi")
    try:
        for linha in linhas:
            if conn.execute(
                "SELECT 1 FROM benchmarks WHERE serie = ? AND data = ? AND hash_sha256 = ?",
                (linha[0], linha[1], linha[6]),
            ).fetchone():
                resumo["repetidos"] += 1
                continue
            conn.execute(
                "INSERT INTO benchmarks (serie, data, valor, valor_texto, fonte, coleta, "
                "hash_sha256) VALUES (?, ?, ?, ?, ?, ?, ?)",
                linha,
            )
            resumo["inseridos"] += 1
    except BaseException:
        if conn.in_transaction:
            conn.execute("ROLLBACK TO cdi")
            conn.execute("RELEASE cdi")
        raise
    conn.execute("RELEASE cdi")
    return resumo
