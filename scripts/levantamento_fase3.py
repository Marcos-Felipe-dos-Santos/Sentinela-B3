"""Levantamento L1 da Fase 3 (F3-L1, pacote §2): disponibilidade ponto-no-tempo das fontes.

Uso, na raiz do repositório: `python scripts/levantamento_fase3.py [--saida data/fontes/l1]`

Só lê fontes públicas oficiais (CVM, B3, Tesouro, IBGE, BCB). Grava, fora do git, o resumo
`levantamento.json` e as amostras baixadas, cada uma com URL, data da consulta e SHA-256.
Uma medida que falha vira `{"falha": motivo}` e não derruba as outras. Não toca no código de
produção nem no banco; a resposta sobre reapresentações sai das próprias amostras da CVM.
"""

from __future__ import annotations

import argparse
import base64
import csv
import hashlib
import io
import json
import re
import shutil
import sys
import time
import zipfile
from collections import Counter, defaultdict
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

import requests

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

ANO_INICIAL = 2010
CVM = "https://dados.cvm.gov.br/dados"
FAMILIAS_CVM = {
    "DFP": f"{CVM}/CIA_ABERTA/DOC/DFP/DADOS/",
    "ITR": f"{CVM}/CIA_ABERTA/DOC/ITR/DADOS/",
    "FCA": f"{CVM}/CIA_ABERTA/DOC/FCA/DADOS/",
    "CAD": f"{CVM}/CIA_ABERTA/CAD/DADOS/",
    "INF_MENSAL_FII": f"{CVM}/FII/DOC/INF_MENSAL/DADOS/",
}
COTAHIST = "https://bvmf.bmfbovespa.com.br/InstDados/SerHist/COTAHIST_A{ano}.ZIP"
TESOURO = (
    "https://www.tesourotransparente.gov.br/ckan/api/3/action/package_show"
    "?id=taxas-dos-titulos-ofertados-pelo-tesouro-direto"
)
SIDRA = "https://apisidra.ibge.gov.br/values/t/1737/n1/all/v/63/p/all?formato=json"
FOCUS = (
    "https://olinda.bcb.gov.br/olinda/servico/Expectativas/versao/v1/odata/"
    "ExpectativasMercadoAnuais?$top={top}&$filter=Indicador%20eq%20'PIB%20Total'"
    "&$orderby=Data%20{ordem}&$format=json&$select=Data,DataReferencia,Mediana"
)
SGS = (
    "https://api.bcb.gov.br/dados/serie/bcdata.sgs.{serie}/dados?formato=json"
    "&dataInicial={inicio}&dataFinal={fim}"
)
IBOV = "https://sistemaswebb3-listados.b3.com.br/indexStatisticsProxy/IndexCall/GetPortfolioDay/{p}"
# Amostra de companhias para proventos e reapresentações (código CVM, ticker de referência).
AMOSTRA_PROVENTOS = {
    "23264": "ABEV3",
    "19348": "ITUB4",
    "20257": "TAEE11",
    "9512": "PETR4",
    "8133": "LREN3",
}
# Companhias com registro cancelado na CVM depois de 2018 (cad_cia_aberta.csv): a B3 ainda
# devolve o cadastro e os proventos de quem saiu da bolsa? (universo PIT com deslistadas)
DESLISTADAS = {
    "23035": "LINX S.A. (cancelada em 2021-08-02)",
    "14761": "CIA HERING (cancelada em 2022-02-23)",
    "8117": "LOJAS HERING SA (cancelada em 2019-05-10)",
    "22551": "SOMOS EDUCAÇÃO S.A. (cancelada em 2019-05-22)",
}
# Companhias com reapresentação conhecida da DFP (ano do exercício reapresentado).
REAPRESENTACOES = {"24180": ("IRB BRASIL RESSEGUROS", 2019)}
TIMEOUT = 60
# Decisão 39: pedidos em série, com pausa entre eles e repetição com espera crescente.
PAUSA = 0.5
TENTATIVAS = 3
CABECALHO = {"User-Agent": "sentinela-b3-levantamento/1.0"}


def _agora() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def _data_br(texto: str) -> date:
    """`dd/mm/aaaa` como data (sem hora nem fuso)."""
    dia, mes, ano = (int(x) for x in texto.split("/"))
    return date(ano, mes, dia)


def _sha(dados: bytes) -> str:
    return hashlib.sha256(dados).hexdigest()


def medir(nome: str, funcao, *args) -> Any:
    try:
        return funcao(*args)
    except Exception as erro:  # noqa: BLE001 - levantamento: toda falha vira registro
        print(f"  [falha] {nome}: {type(erro).__name__}: {erro}", file=sys.stderr)
        return {"falha": f"{type(erro).__name__}: {erro}"}


def _pedir(metodo, url: str, **kwargs) -> requests.Response:
    """Um pedido por vez (decisão 39): pausa antes e até `TENTATIVAS`, com espera crescente.

    Resposta 429 ou 5xx, ou corpo vazio num GET, conta como falha e é repetida.
    """
    resposta = None
    for tentativa in range(1, TENTATIVAS + 1):
        time.sleep(PAUSA)
        try:
            resposta = metodo(url, timeout=TIMEOUT, headers=CABECALHO, **kwargs)
            vazio = metodo is requests.get and not resposta.content
            if resposta.status_code < 500 and resposta.status_code != 429 and not vazio:
                return resposta
        except requests.RequestException:
            if tentativa == TENTATIVAS:
                raise
        time.sleep(2**tentativa)
    return resposta


def baixar(url: str, destino: Path | None = None) -> dict:
    """GET com proveniência; grava em `destino` se pedido."""
    resposta = _pedir(requests.get, url)
    resposta.raise_for_status()
    corpo = resposta.content
    registro = {
        "url": url,
        "consulta": _agora(),
        "bytes": len(corpo),
        "sha256": _sha(corpo),
        "last_modified": resposta.headers.get("Last-Modified"),
    }
    if destino is not None:
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_bytes(corpo)
        registro["arquivo"] = str(destino.relative_to(RAIZ))
    registro["_corpo"] = corpo
    return registro


def cabecalho(url: str) -> dict:
    resposta = _pedir(requests.head, url, allow_redirects=True)
    if resposta.status_code != 200:
        return {"url": url, "status": resposta.status_code}
    return {
        "url": url,
        "status": 200,
        "bytes": int(resposta.headers.get("Content-Length", 0)) or None,
        "last_modified": resposta.headers.get("Last-Modified"),
    }


def _sem_corpo(registro: dict) -> dict:
    return {k: v for k, v in registro.items() if k != "_corpo"}


# --- CVM ---------------------------------------------------------------------------------


def familia_cvm(nome: str, indice: str) -> dict:
    pagina = _pedir(requests.get, indice).text
    arquivos = sorted(set(re.findall(r'href="([^"]+\.(?:zip|csv))"', pagina)))
    por_ano, outros = {}, []
    for arquivo in arquivos:
        ano = re.search(r"_(\d{4})\.zip$", arquivo)
        info = cabecalho(indice + arquivo)
        if ano and int(ano.group(1)) >= ANO_INICIAL:
            por_ano[ano.group(1)] = info
        elif not ano:
            outros.append(info)
    anos_todos = sorted(
        int(a.group(1)) for f in arquivos if (a := re.search(r"_(\d{4})\.zip$", f))
    )
    total = sum(i.get("bytes") or 0 for i in por_ano.values())
    return {
        "indice": indice,
        "consulta": _agora(),
        "primeiro_ano_aberto": anos_todos[0] if anos_todos else None,
        "ultimo_ano": anos_todos[-1] if anos_todos else None,
        "por_ano": por_ano,
        "outros_arquivos": outros,
        "total_bytes_desde_inicio": total,
    }


def _ler_csv_do_zip(conteudo: bytes, sufixo: str) -> tuple[str, list[dict]]:
    with zipfile.ZipFile(io.BytesIO(conteudo)) as z:
        nomes = [n for n in z.namelist() if n.endswith(sufixo)]
        nome = min(nomes, key=len)
        texto = z.read(nome).decode("latin-1")
    return nome, list(csv.DictReader(io.StringIO(texto), delimiter=";"))


def versoes_cvm(familia: str, ano: int, saida: Path) -> dict:
    """Uma companhia e período com mais de uma `VERSAO` no arquivo aberto = guarda versões."""
    url = f"{FAMILIAS_CVM[familia]}{familia.lower()}_cia_aberta_{ano}.zip"
    registro = baixar(url, saida / "cvm" / f"{familia.lower()}_cia_aberta_{ano}.zip")
    corpo = registro.pop("_corpo")
    with zipfile.ZipFile(io.BytesIO(corpo)) as z:
        membros = {n: z.getinfo(n).file_size for n in z.namelist()}
    nome, linhas = _ler_csv_do_zip(corpo, f"_{ano}.csv")
    colunas = list(linhas[0].keys()) if linhas else []
    por_doc = defaultdict(set)
    recebimentos = defaultdict(set)
    for linha in linhas:
        chave = (linha.get("CD_CVM"), linha.get("DT_REFER"))
        por_doc[chave].add(linha.get("VERSAO"))
        recebimentos[chave].add(linha.get("DT_RECEB"))
    multiplas = {k: sorted(v) for k, v in por_doc.items() if len(v) > 1}
    amostras = {}
    for cd_cvm, (empresa, ano_conhecido) in REAPRESENTACOES.items():
        docs = [
            {
                "dt_refer": k[1],
                "versoes": sorted(v),
                "dt_receb": sorted(recebimentos[k]),
            }
            for k, v in por_doc.items()
            if (k[0] or "").lstrip("0") == cd_cvm.lstrip("0")
        ]
        amostras[cd_cvm] = {
            "empresa": empresa,
            "ano_reapresentado": ano_conhecido,
            "documentos": docs,
        }
    return {
        **registro,
        "membros_descompactados_bytes": membros,
        "arquivo_indice": nome,
        "colunas": colunas,
        "documentos": len(por_doc),
        "documentos_com_mais_de_uma_versao": len(multiplas),
        "exemplos_multiplas": dict(
            list({f"{k[0]}|{k[1]}": v for k, v in multiplas.items()}.items())[:5]
        ),
        "versoes_distintas": Counter(
            v for vs in por_doc.values() for v in vs
        ).most_common(6),
        "amostras_reapresentacao": amostras,
        "intervalo_primeira_ultima_entrega_dias": _intervalos(recebimentos),
        "demonstracoes": _versoes_nas_demonstracoes(corpo, ano, multiplas),
    }


def _intervalos(recebimentos: dict) -> dict:
    """Dias entre a primeira e a última `DT_RECEB` dos documentos com mais de uma entrega."""
    dias = sorted(
        (max(datas) - min(datas)).days
        for datas in (
            [date.fromisoformat(d) for d in v if d] for v in recebimentos.values()
        )
        if len(datas) > 1
    )
    if not dias:
        return {"documentos": 0}
    return {
        "documentos": len(dias),
        "mediana": dias[len(dias) // 2],
        "p90": dias[int(0.9 * len(dias))],
        "maximo": dias[-1],
        "acima_de_90": sum(1 for d in dias if d > 90),
        "acima_de_365": sum(1 for d in dias if d > 365),
    }


def _versoes_nas_demonstracoes(corpo: bytes, ano: int, multiplas: dict) -> dict:
    """Por demonstração: documentos com linhas de mais de uma `VERSAO`, e as versões presentes
    nas linhas dos documentos que o índice diz reapresentados."""
    resultado = {}
    with zipfile.ZipFile(io.BytesIO(corpo)) as z:
        for nome in sorted(z.namelist()):
            if nome.endswith(f"_{ano}.csv") and "_con_" in nome:
                texto = z.read(nome).decode("latin-1")
                linhas = csv.DictReader(io.StringIO(texto), delimiter=";")
                por_doc = defaultdict(set)
                for linha in linhas:
                    chave = (
                        (linha.get("CD_CVM") or "").lstrip("0"),
                        linha.get("DT_REFER"),
                    )
                    por_doc[chave].add(linha.get("VERSAO"))
                reapresentados = {
                    (k[0].lstrip("0"), k[1]): v for k, v in multiplas.items()
                }
                presentes = [
                    {
                        "documento": f"{k[0]}|{k[1]}",
                        "versoes_no_indice": v,
                        "versoes_nas_linhas": sorted(por_doc[k]),
                    }
                    for k, v in reapresentados.items()
                    if k in por_doc
                ]
                resultado[nome] = {
                    "documentos": len(por_doc),
                    "com_mais_de_uma_versao_nas_linhas": sum(
                        1 for v in por_doc.values() if len(v) > 1
                    ),
                    "reapresentados_presentes": len(presentes),
                    "reapresentados_so_com_a_ultima_versao": sum(
                        1
                        for d in presentes
                        if d["versoes_nas_linhas"]
                        == [max(d["versoes_no_indice"], key=int)]
                    ),
                    "exemplos": presentes[:3],
                }
    return resultado


# --- B3 ----------------------------------------------------------------------------------


def cotahist(ano_final: int) -> dict:
    por_ano = {
        str(a): cabecalho(COTAHIST.format(ano=a))
        for a in range(ANO_INICIAL, ano_final + 1)
    }
    return {
        "consulta": _agora(),
        "por_ano": por_ano,
        "total_bytes": sum(i.get("bytes") or 0 for i in por_ano.values()),
    }


def _numero_br(texto: str | None) -> float | None:
    if not texto:
        return None
    return float(texto.replace(".", "").replace(",", "."))


def ibovespa(ano_final: int, saida: Path) -> dict:
    """Fechamentos diários do IBOV por ano (tabela dia × mês da B3)."""
    por_ano, ultimos_por_mes = {}, {}
    for ano in range(ANO_INICIAL, ano_final + 1):
        parametro = base64.b64encode(
            json.dumps(
                {"index": "IBOV", "language": "pt-br", "year": str(ano)}
            ).encode()
        ).decode()
        registro = baixar(IBOV.format(p=parametro), saida / "b3" / f"ibov_{ano}.json")
        corpo = json.loads(registro.pop("_corpo"))
        dias = 0
        for linha in corpo.get("results", []):
            for mes in range(1, 13):
                valor = _numero_br(linha.get(f"rateValue{mes}"))
                if valor is not None:
                    dias += 1
                    chave = f"{ano}-{mes:02d}"
                    ultimos_por_mes[chave] = max(
                        ultimos_por_mes.get(chave, 0), int(linha["day"])
                    )
        por_ano[str(ano)] = {**_sem_corpo(registro), "dias_com_fechamento": dias}
    return {"por_ano": por_ano, "ultimo_dia_por_mes": ultimos_por_mes}


def proventos_b3(agora: datetime) -> dict:
    from sentinela.data.providers import b3_proventos

    resultado = {}
    for cd_cvm, ticker in AMOSTRA_PROVENTOS.items():

        def _uma(cd=cd_cvm, tk=ticker):
            relacao = b3_proventos.coletar(cd, agora)
            por_ano = Counter()
            antecedencia = []
            for r in relacao.registros:
                ex = r.get("lastDatePrior") or r.get("lastDatePriorEx")
                aprov = r.get("dateApproval")
                try:
                    d_ex = _data_br(ex)
                    por_ano[d_ex.year] += 1
                    if aprov:
                        d_ap = _data_br(aprov)
                        antecedencia.append((d_ex - d_ap).days)
                except (AttributeError, TypeError, ValueError):
                    por_ano["data_ilegivel"] += 1
            anos = sorted(a for a in por_ano if isinstance(a, int))
            lacunas = (
                [a for a in range(anos[0], anos[-1] + 1) if a not in por_ano]
                if anos
                else []
            )
            return {
                "ticker_referencia": tk,
                "nome_pregao": relacao.nome_pregao,
                "registros": len(relacao.registros),
                "total_declarado": relacao.total,
                "por_ano_data_ex": {
                    str(k): v for k, v in sorted(por_ano.items(), key=str)
                },
                "primeiro_ano": anos[0] if anos else None,
                "anos_sem_registro": lacunas,
                "dias_aprovacao_ate_data_ex": {
                    "min": min(antecedencia) if antecedencia else None,
                    "max": max(antecedencia) if antecedencia else None,
                    "negativos": sum(1 for d in antecedencia if d < 0),
                },
                "identidade": relacao.identidade or "conferida",
                "campos": sorted(relacao.registros[0].keys())
                if relacao.registros
                else [],
                "coleta": relacao.coleta,
            }

        resultado[cd_cvm] = medir(f"proventos {ticker}", _uma)
    return resultado


def proventos_deslistadas(agora: datetime) -> dict:
    from sentinela.data.providers import b3_proventos

    resultado = {}
    for cd_cvm, descricao in DESLISTADAS.items():
        try:
            relacao = b3_proventos.coletar(cd_cvm, agora)
            resultado[cd_cvm] = {
                "companhia": descricao,
                "registros": len(relacao.registros),
                "identidade": relacao.identidade or "conferida",
            }
        except (ValueError, TypeError, requests.RequestException) as erro:
            resultado[cd_cvm] = {
                "companhia": descricao,
                "falha": f"{type(erro).__name__}: {erro}",
            }
    return resultado


# --- macro -------------------------------------------------------------------------------


def tesouro(saida: Path) -> dict:
    pacote = _pedir(requests.get, TESOURO).json()["result"]
    recurso = next(r for r in pacote["resources"] if r["url"].lower().endswith(".csv"))
    registro = baixar(recurso["url"], saida / "tesouro" / "precotaxatesourodireto.csv")
    texto = registro.pop("_corpo").decode("latin-1")
    linhas = list(csv.DictReader(io.StringIO(texto), delimiter=";"))
    por_tipo = defaultdict(list)
    for linha in linhas:
        por_tipo[linha.get("Tipo Titulo")].append(_data_br(linha["Data Base"]))
    return {
        **registro,
        "recurso": recurso.get("name"),
        "linhas": len(linhas),
        "colunas": list(linhas[0].keys()) if linhas else [],
        "por_tipo": {
            tipo: {
                "primeira": min(d).isoformat(),
                "ultima": max(d).isoformat(),
                "linhas": len(d),
            }
            for tipo, d in sorted(por_tipo.items(), key=lambda x: str(x[0]))
        },
    }


def sidra(saida: Path) -> dict:
    registro = baixar(SIDRA, saida / "macro" / "sidra_1737_v63.json")
    dados = json.loads(registro.pop("_corpo"))[1:]
    periodos = sorted(d["D3C"] for d in dados)
    return {
        **registro,
        "observacoes": len(dados),
        "primeiro_periodo": periodos[0],
        "ultimo_periodo": periodos[-1],
    }


def focus(saida: Path) -> dict:
    primeiro = baixar(
        FOCUS.format(top=1, ordem="asc"), saida / "macro" / "focus_pib_primeira.json"
    )
    ultimo = baixar(
        FOCUS.format(top=1, ordem="desc"), saida / "macro" / "focus_pib_ultima.json"
    )
    return {
        "primeira": json.loads(primeiro.pop("_corpo"))["value"],
        "ultima": json.loads(ultimo.pop("_corpo"))["value"],
        "consulta": _agora(),
        "url": FOCUS.format(top=1, ordem="asc"),
        "sha256_primeira": primeiro["sha256"],
        "sha256_ultima": ultimo["sha256"],
    }


def sgs(serie: int, hoje: date, saida: Path) -> dict:
    janelas = [(date(ANO_INICIAL, 1, 1), date(2019, 12, 31)), (date(2020, 1, 1), hoje)]
    observacoes, registros = [], []
    for inicio, fim in janelas:
        registro = baixar(
            SGS.format(
                serie=serie,
                inicio=inicio.strftime("%d/%m/%Y"),
                fim=fim.strftime("%d/%m/%Y"),
            ),
            saida / "macro" / f"sgs_{serie}_{inicio.year}.json",
        )
        observacoes += json.loads(registro.pop("_corpo"))
        registros.append(registro)
    datas = [_data_br(o["data"]) for o in observacoes]
    ultimos = {}
    for d in datas:
        chave = f"{d.year}-{d.month:02d}"
        ultimos[chave] = max(ultimos.get(chave, 0), d.day)
    return {
        "janelas": registros,
        "observacoes": len(datas),
        "primeira": min(datas).isoformat(),
        "ultima": max(datas).isoformat(),
        "ultimo_dia_por_mes": ultimos,
    }


def alinhamento(ibov: dict, cdi: dict) -> dict:
    a, b = ibov.get("ultimo_dia_por_mes", {}), cdi.get("ultimo_dia_por_mes", {})
    meses = sorted(set(a) & set(b))
    divergentes = {m: {"ibov": a[m], "cdi": b[m]} for m in meses if a[m] != b[m]}
    return {
        "meses_comparados": len(meses),
        "ultimo_pregao_igual": len(meses) - len(divergentes),
        "divergentes": divergentes,
        "so_ibov": sorted(set(a) - set(b)),
        "so_cdi": sorted(set(b) - set(a)),
    }


# --- projeção ----------------------------------------------------------------------------


def projecao(resultado: dict, hoje: date) -> dict:
    zip_cvm = sum(
        f.get("total_bytes_desde_inicio", 0)
        for f in resultado.get("cvm", {}).values()
        if isinstance(f, dict)
    )
    cotahist_total = resultado.get("cotahist", {}).get("total_bytes", 0)
    tesouro_bytes = resultado.get("tesouro", {}).get("bytes", 0) or 0
    brutos = zip_cvm + cotahist_total + tesouro_bytes
    # Banco: CSV descompactado das amostras como teto por ano (o banco guarda só as contas usadas).
    descompactado_por_ano = {}
    for chave in ("dfp_amostra", "itr_amostra"):
        amostra = resultado.get("reapresentacoes", {}).get(chave, {})
        if isinstance(amostra, dict) and "membros_descompactados_bytes" in amostra:
            descompactado_por_ano[chave] = sum(
                amostra["membros_descompactados_bytes"].values()
            )
    anos = hoje.year - ANO_INICIAL + 1
    teto_banco = sum(descompactado_por_ano.values()) * anos
    return {
        "brutos_zip_bytes": brutos,
        "brutos_componentes": {
            "cvm_zip": zip_cvm,
            "cotahist_zip": cotahist_total,
            "tesouro_csv": tesouro_bytes,
        },
        "teto_banco_bytes": teto_banco,
        "metodo_banco": "soma dos CSV descompactados de uma DFP e de um ITR × anos desde 2010 (teto; o banco guarda só as contas usadas)",
        "total_projetado_bytes": brutos + teto_banco,
        "limite_brutos_bytes": 100 * 10**9,  # decisão 39 (antes 20 GB)
        "disco_livre_bytes": shutil.disk_usage(RAIZ / "data").free,
        "acima_do_limite": brutos > 100 * 10**9,
        "disco_abaixo_do_dobro": shutil.disk_usage(RAIZ / "data").free
        < 2 * (brutos + teto_banco),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--saida", default="data/fontes/l1")
    args = parser.parse_args(argv)
    saida = (RAIZ / args.saida).resolve()
    saida.mkdir(parents=True, exist_ok=True)
    agora = datetime.now(UTC)
    hoje = agora.date()
    print(f"Levantamento L1 em {saida} ({agora.isoformat(timespec='seconds')})")
    r: dict[str, Any] = {"inicio": agora.isoformat(timespec="seconds")}
    r["cvm"] = {
        nome: medir(nome, familia_cvm, nome, url) for nome, url in FAMILIAS_CVM.items()
    }
    r["reapresentacoes"] = {
        "dfp_amostra": medir("DFP 2019", versoes_cvm, "DFP", 2019, saida),
        "itr_amostra": medir("ITR 2020", versoes_cvm, "ITR", 2020, saida),
    }
    r["cotahist"] = medir("COTAHIST", cotahist, hoje.year)
    r["tesouro"] = medir("Tesouro", tesouro, saida)
    r["sidra_ipca"] = medir("SIDRA", sidra, saida)
    r["focus_pib"] = medir("Focus", focus, saida)
    r["sgs"] = {str(s): medir(f"SGS {s}", sgs, s, hoje, saida) for s in (432, 12)}
    r["ibovespa"] = medir("Ibovespa", ibovespa, hoje.year, saida)
    r["alinhamento_ibov_cdi"] = medir(
        "alinhamento", alinhamento, r["ibovespa"], r["sgs"]["12"]
    )
    r["proventos_b3"] = medir("proventos", proventos_b3, agora)
    r["proventos_deslistadas"] = medir("deslistadas", proventos_deslistadas, agora)
    r["projecao"] = medir("projeção", projecao, r, hoje)
    r["fim"] = _agora()
    destino = saida / "levantamento.json"
    destino.write_text(
        json.dumps(r, ensure_ascii=False, indent=1, default=str), encoding="utf-8"
    )
    p = r["projecao"]
    print(f"Resumo em {destino}")
    if "falha" in p:
        print(f"Projeção indisponível: {p['falha']}")
        return 1
    print(
        f"Brutos: {p['brutos_zip_bytes'] / 1e9:.2f} GB; teto do banco: {p['teto_banco_bytes'] / 1e9:.2f} GB; "
        f"total: {p['total_projetado_bytes'] / 1e9:.2f} GB (limite de brutos: 100 GB, decisão 39)"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
