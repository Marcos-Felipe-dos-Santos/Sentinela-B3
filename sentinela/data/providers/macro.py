"""SIDRA 1737, Focus PIB e calendários públicos, com cache observado e sem reserva."""

from __future__ import annotations

import calendar
import hashlib
import json
import math
import re
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from tempfile import NamedTemporaryFile
from zoneinfo import ZoneInfo

import requests

from sentinela.data.taxas import Calendario

IBGE_CALENDARIO = "https://servicodados.ibge.gov.br/api/v3/calendario/9256"
FOCUS = "https://olinda.bcb.gov.br/olinda/servico/Expectativas/versao/v1/odata/ExpectativasMercadoAnuais"
ANBIMA = "https://www.anbima.com.br/feriados/fer_nacionais/{ano}.asp"
TTL = 86400


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

    def inflacao(self, inicio: date, fim: date, instante: datetime) -> dict:
        dia = _local(instante)
        agenda = self.baixar(IBGE_CALENDARIO, instante)
        publicacoes = {}
        for evento in json.loads(agenda.conteudo)["items"]:
            if evento.get("produto_id") == 9256:
                mes = f"{int(evento['ano_referencia_inicio']):04}{int(evento['mes_referencia_inicio']):02}"
                publicacoes[mes] = datetime.strptime(
                    evento["data_divulgacao"] + "+0000", "%d/%m/%Y %H:%M:%S%z"
                ).date()
        publicados = [mes for mes, entrega in publicacoes.items() if entrega < dia]
        if not publicados:
            raise ValueError("IPCA publicado ausente no calendário")
        ultimo = max(publicados)
        url = f"https://apisidra.ibge.gov.br/values/t/1737/n1/all/v/63/p/{inicio:%Y%m}-{ultimo}?formato=json"
        serie = self.baixar(url, instante)
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

    def pib(self, instante: datetime) -> dict:
        dia = _local(instante)
        url_agenda = f"https://www.bcb.gov.br/api/servico/sitebcb/calendario?inicioAgenda=%27{dia.year}-01-01%27&fimAgenda=%27{dia.year}-12-31%27&lista=Focus"
        agenda = self.baixar(url_agenda, instante)
        edicoes = {}
        for evento in json.loads(agenda.conteudo)["conteudo"]:
            if evento.get("evento") == "Relatório Focus":
                publicacao = datetime.fromisoformat(evento["dataEvento"])
                dia_edicao = publicacao.astimezone(ZoneInfo("America/Sao_Paulo")).date()
                # BCB: estatísticas até a sexta anterior. O instante de divulgação
                # vem da agenda, inclusive edições deslocadas por feriado.
                pesquisa = dia_edicao - timedelta(
                    days=(dia_edicao.weekday() - 4) % 7 or 7
                )
                edicoes[pesquisa] = publicacao
        devidas = [d for d, p in edicoes.items() if p <= instante]
        if not devidas:
            raise ValueError("edição Focus devida ausente no calendário")
        pesquisa = max(devidas)
        url = (
            FOCUS
            + f"?$format=json&$filter=Indicador%20eq%20%27PIB%20Total%27%20and%20Data%20eq%20%27{pesquisa}%27"
        )
        serie = self.baixar(url, instante)
        resultado = pib_focus(
            json.loads(serie.conteudo)["value"], edicoes, as_of=instante
        )
        proxima = resultado["proxima_publicacao"]
        resultado["proxima_publicacao"] = proxima.isoformat() if proxima else None
        return resultado | {
            "proveniencia": serie.proveniencia(),
            "calendario": agenda.proveniencia(),
        }

    def registro(
        self, instante: datetime, janela: tuple[date, date] | None = None
    ) -> dict | None:
        """Orquestra fontes; dado sem prova não vira constante de contingência."""
        from sentinela.data import taxas
        from sentinela.data.providers.tesouro import (
            TesouroProvider,
            ler_snapshot,
            selecionar_ofertas,
        )

        try:
            arquivo = TesouroProvider(self.cache_dir / "tesouro").baixar(instante)
            cesta = selecionar_ofertas(ler_snapshot(arquivo, as_of=instante))
            dia = _local(instante)
            ano_inicial = cesta.data_base.year if cesta.data_base else dia.year
            calendarios = [
                self.calendario(ano, instante)
                for ano in range(ano_inicial, dia.year + 1)
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
                return None
        except (requests.RequestException, OSError, ValueError, KeyError, TypeError):
            return None
        if janela is None:
            resultado["inflacao"] = {
                "abstencao": "janela contábil anual não demonstrada"
            }
        else:
            try:
                resultado["inflacao"] = self.inflacao(*janela, instante)
            except (
                requests.RequestException,
                OSError,
                ValueError,
                KeyError,
                TypeError,
            ) as erro:
                resultado["inflacao"] = {"abstencao": str(erro)}
        try:
            resultado["pib"] = self.pib(instante)
        except (
            requests.RequestException,
            OSError,
            ValueError,
            KeyError,
            TypeError,
        ) as erro:
            resultado["pib"] = {"abstencao": str(erro)}
        return resultado
