"""Levantamento F2B-21: fontes públicas, sem config, carteira, banco ou credenciais.

Uso: python scripts/levantamento_fase2b.py [--secao N ...] [--atualizar]
(sem --secao, roda as oito; a 3 lê os resultados da 1 e da 2, e a 5 lê os retratos da 3).
Cada seção grava JSON próprio em outputs/levantamento_cache/f2b21/.
Respostas HTTP, inclusive falhas, preservam URL, status, coleta e SHA-256.
--atualizar repete consultas; sem ele, a execução usa as respostas arquivadas.
"""

from __future__ import annotations

import argparse
import ast
import base64
import hashlib
import json
import math
import re
import sys
import tempfile
import threading
import zipfile
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch
from xml.etree import ElementTree

import pandas as pd
import requests

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))
CACHE = RAIZ / "outputs" / "levantamento_cache" / "f2b21"
TD_API = (
    "https://www.tesourodireto.com.br/json/br/com/b3/tesourodireto/"
    "service/api/treasureList.json"
)
TD_CSV = (
    "https://www.tesourotransparente.gov.br/ckan/dataset/"
    "df56aa42-484a-4a59-8184-7676580c81e3/resource/"
    "796d2059-14e9-44e3-80c9-2d9e30b405c1/download/precotaxatesourodireto.csv"
)
OLINDA = "https://olinda.bcb.gov.br/olinda/servico"
CVM = "https://dados.cvm.gov.br/dados"


def salvar(caminho: Path, dados: Any) -> None:
    """Grava evidência legível, sem números JSON não finitos."""
    caminho.parent.mkdir(parents=True, exist_ok=True)
    caminho.write_text(
        json.dumps(dados, ensure_ascii=False, indent=2, default=str, allow_nan=False)
        + "\n",
        encoding="utf-8",
    )


def consultar(nome: str, url: str, atualizar: bool = False) -> dict[str, Any]:
    """Consulta GET com cache de resposta e metadados; erro não vira dado."""
    meta = CACHE / f"{nome}.meta.json"
    corpo = CACHE / f"{nome}.resposta"
    if meta.exists() and corpo.exists() and not atualizar:
        return json.loads(meta.read_text(encoding="utf-8"))
    registro: dict[str, Any] = {
        "url": url,
        "coleta_utc": datetime.now(UTC).isoformat(),
        "arquivo": str(corpo.relative_to(RAIZ)),
    }
    try:
        resposta = requests.get(
            url,
            timeout=(10, 45),
            headers={"User-Agent": "Mozilla/5.0 (Sentinela F2B-21; leitura)"},
        )
        conteudo = resposta.content
        registro.update(
            status=resposta.status_code,
            url_final=resposta.url,
            content_type=resposta.headers.get("Content-Type"),
            bytes=len(conteudo),
            sha256=hashlib.sha256(conteudo).hexdigest(),
        )
    except requests.RequestException as exc:
        conteudo = b""
        registro.update(status=None, erro=f"{type(exc).__name__}: {exc}")
    corpo.parent.mkdir(parents=True, exist_ok=True)
    corpo.write_bytes(conteudo)
    salvar(meta, registro)
    return registro


def corpo_json(registro: dict[str, Any]) -> Any:
    """Só aceita JSON bem formado em resposta HTTP de sucesso."""
    if registro.get("status") != 200:
        return None
    try:
        return json.loads((RAIZ / registro["arquivo"]).read_bytes())
    except (ValueError, UnicodeError):
        return None


def csv_zip(caminho: Path, trecho: str) -> pd.DataFrame:
    """Lê tabela oficial por nome de arquivo, mantendo os campos como texto."""
    with zipfile.ZipFile(caminho) as arquivo:
        nome = next(n for n in arquivo.namelist() if trecho in n)
        return pd.read_csv(arquivo.open(nome), sep=";", encoding="latin-1", dtype=str)


def fonte_dfp(ano: int, preferir_dados: bool = False) -> Path:
    """Reusa arquivo público local ou coleta CVM no cache do levantamento."""
    candidatos = [RAIZ / f"outputs/levantamento_cache/dfp_{ano}.zip"]
    if preferir_dados:
        candidatos.insert(0, RAIZ / f"data/cvm/dfp_{ano}.zip")
    for caminho in candidatos:
        if caminho.exists():
            return caminho
    meta = consultar(
        f"dfp_{ano}", f"{CVM}/CIA_ABERTA/DOC/DFP/DADOS/dfp_cia_aberta_{ano}.zip"
    )
    if meta.get("status") != 200:
        raise FileNotFoundError(f"DFP {ano}: HTTP {meta.get('status')}")
    return RAIZ / meta["arquivo"]


def mercado_publico(ticker: str) -> tuple[Path, dict[str, Any]]:
    """Somente mercado público do ticker do universo; nunca abre o banco do projeto."""
    legado = RAIZ / f"outputs/dossie_cache/yf_{ticker}.json"
    atual = CACHE / f"yf_{ticker}.json"
    for caminho in (atual, legado):
        if caminho.exists():
            return caminho, json.loads(caminho.read_text())
    import yfinance as yf

    yf.set_tz_cache_location(str(CACHE / "yfinance"))
    try:
        ativo = yf.Ticker(f"{ticker}.SA")
        info = ativo.info or {}
        historico = ativo.history(
            start="2025-10-01", end="2026-10-01", auto_adjust=False
        )
        registro = {
            "preco": numero(historico["Close"].iloc[-1]) if len(historico) else None,
            "shares": numero(info.get("sharesOutstanding")),
            "divs": {
                str(d.date()): numero(v)
                for d, v in historico.get("Dividends", pd.Series(dtype=float)).items()
            },
            "fonte": f"yfinance {ticker}.SA, info e history 2025-10-01..2026-10-01",
            "coleta_utc": datetime.now(UTC).isoformat(),
        }
    except Exception as exc:
        # Bibliotecas de mercado têm classes próprias de erro HTTP e de limite de uso.
        registro = {"estado": "não determinado", "erro_tipo": type(exc).__name__}
    salvar(atual, registro)
    return atual, registro


def numero(valor: Any) -> float | None:
    """Converte número da fonte sem inferir unidade ou preencher ausência."""
    try:
        resultado = float(str(valor).replace(",", "."))
    except (TypeError, ValueError):
        return None
    return resultado if math.isfinite(resultado) else None


def inflacoes_disponiveis(dados: dict[str, Any]) -> list[float]:
    """Cenários de inflação com unidade declarada; não escolhe a inflação do método."""
    valores = {
        r["Mediana"] / 100
        for nome in ("focus_12", "focus_anual")
        for r in (dados.get(nome) or {}).get("value", [])
        if r.get("Mediana") is not None
        and r["Data"] == (dados.get(nome) or {}).get("value", [{}])[0].get("Data")
    }
    for linha in dados.get("ibge_ipca_12m") or []:
        if linha.get("MN") == "%" and "12 meses" in linha.get("D2N", ""):
            valor = numero(linha.get("V"))
            if valor is not None:
                valores.add(valor / 100)
    return sorted(valores)


def universo() -> list[dict[str, str]]:
    """Amostra pública aprovada, exclusivamente do documento de universo inicial."""
    linhas = (RAIZ / "docs/decisoes/universo-inicial.md").read_text().splitlines()
    resultado = []
    for linha in linhas:
        colunas = [c.strip() for c in linha.strip("|").split("|")]
        if len(colunas) >= 5 and re.fullmatch(r"[A-Z]{4}\d{1,2}", colunas[0]):
            resultado.append(
                {
                    "ticker": colunas[0],
                    "cnpj": colunas[1],
                    "classe": colunas[2],
                    "situacao": colunas[-1],
                    "tipo_fii_no_universo": colunas[3].split(" (")[0]
                    if colunas[2] == "FII"
                    else None,
                }
            )
    return resultado


def indice() -> list[dict[str, Any]]:
    """Lê somente o índice oficial local; não usa posições ou banco."""
    return list(
        json.loads((RAIZ / "data/referencia/indice.json").read_text())[
            "registros"
        ].values()
    )


def evidencia_codigo(arquivo: str, nome: str) -> dict[str, Any]:
    """Registra função e linhas do checkout, sem importar módulos que leem config."""
    texto = (RAIZ / arquivo).read_text(encoding="utf-8")
    arvore = ast.parse(texto)
    funcao = next(
        n
        for n in ast.walk(arvore)
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name == nome
    )
    return {
        "arquivo": arquivo,
        "linha": funcao.lineno,
        "fim": funcao.end_lineno,
        "sha256": hashlib.sha256(texto.encode()).hexdigest(),
    }


def secao1(atualizar: bool) -> dict[str, Any]:
    """Tesouro: disponibilidade e vértices candidatos, sem escolher um deles."""
    api = consultar("tesouro_api", TD_API, atualizar)
    historico = consultar("tesouro_historico", TD_CSV, atualizar)
    resultado: dict[str, Any] = {"api": api, "historico": historico}
    if historico.get("status") != 200:
        return {**resultado, "estado": "não determinado", "motivo": "CSV indisponível"}
    tabela = pd.read_csv(RAIZ / historico["arquivo"], sep=";", decimal=",")
    resultado["colunas"] = list(tabela.columns)
    tabela["data"] = pd.to_datetime(tabela["Data Base"], dayfirst=True, errors="coerce")
    tabela["vencimento"] = pd.to_datetime(
        tabela["Data Vencimento"], dayfirst=True, errors="coerce"
    )
    atual = tabela[tabela["data"] == tabela["data"].max()]
    ipca = atual[atual["Tipo Titulo"].str.contains("IPCA", case=False, na=False)]
    resultado.update(
        primeira_data=str(tabela["data"].min().date()),
        ultima_data=str(tabela["data"].max().date()),
        linhas=len(tabela),
        titulos_ipca=ipca.drop(columns=["data", "vencimento"]).to_dict("records"),
    )
    if ipca.empty:
        return {
            **resultado,
            "estado": "não determinado",
            "motivo": "sem IPCA na última data",
        }
    compra, venda = "Taxa Compra Manha", "Taxa Venda Manha"
    resumo = []
    alvo = tabela["data"].max() + pd.DateOffset(years=10)
    for nome, grupo in ipca.groupby("Tipo Titulo"):
        candidatos = {
            "mais_perto_10_anos": grupo.loc[
                [(grupo["vencimento"] - alvo).abs().idxmin()]
            ],
            "2035": grupo[grupo["vencimento"].dt.year == 2035],
            "2045": grupo[grupo["vencimento"].dt.year == 2045],
            "mais_longo": grupo[grupo["vencimento"] == grupo["vencimento"].max()],
            "media_2035_em_diante": grupo[grupo["vencimento"].dt.year >= 2035],
        }
        for vertice, linhas in candidatos.items():
            resumo.append(
                {
                    "tipo": nome,
                    "vertice": vertice,
                    "n": len(linhas),
                    "taxa_compra_percentual": numero(linhas[compra].mean()),
                    "taxa_venda_percentual": numero(linhas[venda].mean()),
                }
            )
    longos = ipca[ipca["vencimento"].dt.year >= 2035]
    resumo.append(
        {
            "tipo": "IPCA+ com e sem cupons",
            "vertice": "media_2035_em_diante",
            "n": len(longos),
            "taxa_compra_percentual": numero(longos[compra].mean()),
            "taxa_venda_percentual": numero(longos[venda].mean()),
        }
    )
    resultado.update(
        estado="medido",
        candidatos=resumo,
        media_csv_compra_2035=numero(longos[compra].mean()),
        media_csv_venda_2035=numero(longos[venda].mean()),
        macro_api="não determinado"
        if corpo_json(api) is None
        else "resposta JSON disponível",
        contingencia_v1=0.07,
        aviso="Médias do CSV não substituem silenciosamente a API da V1; campos e datas diferem.",
    )
    return resultado


def secao2(atualizar: bool) -> dict[str, Any]:
    """IPCA e Focus, preservando ausência de resposta válida e datas de cada série."""
    raiz = f"{OLINDA}/Expectativas/versao/v1/odata/"
    urls = {
        "ipca_12": "https://api.bcb.gov.br/dados/serie/bcdata.sgs.433/dados/ultimos/12?formato=json",
        "focus_12": raiz
        + "ExpectativasMercadoInflacao12Meses?$format=json&$filter=Indicador%20eq%20'IPCA'&$orderby=Data%20desc&$top=10",
        "focus_anual": raiz
        + "ExpectativasMercadoAnuais?$format=json&$filter=Indicador%20eq%20'IPCA'&$orderby=Data%20desc&$top=100",
    }
    urls["ipca_intervalo"] = (
        "https://api.bcb.gov.br/dados/serie/bcdata.sgs.433/dados?formato=json&dataInicial=01/09/2025&dataFinal=30/09/2026"
    )
    urls["selic_historica"] = (
        "https://api.bcb.gov.br/dados/serie/bcdata.sgs.432/dados?formato=json&dataInicial=01/01/2016&dataFinal=18/10/2026"
    )
    urls["ibge_ipca_controle"] = (
        "https://apisidra.ibge.gov.br/values/t/1737/n1/all/v/2266/p/last"
    )
    urls["ibge_metadados"] = (
        "https://servicodados.ibge.gov.br/api/v3/agregados/1737/metadados"
    )
    urls["selic_2016_2020"] = (
        "https://api.bcb.gov.br/dados/serie/bcdata.sgs.432/dados?formato=json&dataInicial=01/01/2016&dataFinal=31/12/2020"
    )
    urls["selic_2021_2026"] = (
        "https://api.bcb.gov.br/dados/serie/bcdata.sgs.432/dados?formato=json&dataInicial=01/01/2021&dataFinal=18/10/2026"
    )
    for nome in ("focus_12", "focus_anual"):
        urls[nome + "_inicio"] = (
            urls[nome]
            .replace("Data%20desc", "Data%20asc")
            .replace("$top=10", "$top=1")
            .replace("$top=100", "$top=1")
        )
    fontes = {nome: consultar(nome, url, atualizar) for nome, url in urls.items()}
    dados = {nome: corpo_json(meta) for nome, meta in fontes.items()}
    metadados_ibge = dados.get("ibge_metadados") or {}
    candidatas = [
        v
        for v in metadados_ibge.get("variaveis", [])
        if "12" in v.get("nome", "") and "acumulad" in v.get("nome", "").lower()
    ]
    if len(candidatas) == 1 and str(candidatas[0].get("id")).isdigit():
        fonte = consultar(
            "ibge_ipca_12m",
            f"https://apisidra.ibge.gov.br/values/t/1737/n1/all/v/{candidatas[0]['id']}/p/last",
            atualizar,
        )
        fontes["ibge_ipca_12m"] = fonte
        dados["ibge_ipca_12m"] = corpo_json(fonte)
    resultado: dict[str, Any] = {"fontes": fontes, "dados": dados}
    ipca = dados["ipca_12"]
    if isinstance(ipca, list) and len(ipca) == 12:
        valores = [numero(r.get("valor")) for r in ipca]
        if all(v is not None for v in valores):
            resultado["ipca_12m"] = math.prod(1 + v / 100 for v in valores) - 1
    resultado["inflacao_implicita"] = {
        "estado": "não determinado",
        "motivo": "Exige casamento de prazo e tipo de fluxo nominal/real; não subtrair taxas de títulos distintos.",
    }
    resultado["inicio_series"] = {
        nome: ((dados.get(nome + "_inicio") or {}).get("value") or [{}])[0].get("Data")
        for nome in ("focus_12", "focus_anual")
    }
    resultado["inicio_series"]["sgs_433"] = (
        "não determinado: consultas não devolveram JSON válido"
    )
    # O que veio no lugar do JSON (página de erro com status 200, recusa por janela…).
    resultado["corpos_sem_json"] = {
        nome: (RAIZ / meta["arquivo"]).read_bytes()[:400].decode("utf-8", "replace")
        for nome, meta in fontes.items()
        if dados.get(nome) is None and meta.get("arquivo")
    }
    return resultado


def secao3(atualizar: bool) -> dict[str, Any]:
    """Matriz diagnóstica com amostra pública e parâmetros explícitos, sem config."""
    del atualizar
    from cvm_provider import CVMProvider
    from sentinela.data import acoes_cvm, contas_cvm
    from sentinela.domain.enums import Perfil
    from sentinela.domain.units import BRL, RateNominal, Ratio
    from sentinela.methods.base import MethodInputs, MethodResult
    from sentinela.methods.bazin import Bazin, BazinParams
    from sentinela.methods.gordon import Gordon, GordonParams
    from sentinela.methods.graham import Graham, GrahamParams
    from sentinela.methods.lynch import Lynch, LynchParams

    class ProvedorLocal(CVMProvider):
        def baixar_dfp(self, ano: int) -> Path:
            return fonte_dfp(ano)

    referencia = date(2026, 9, 30)
    provedor = ProvedorLocal(str(CACHE / "cvm"))
    registros = {r["ticker"]: r for r in indice()}
    retratos = []
    for ativo in universo():
        if ativo["situacao"] != "atual":
            continue
        ticker = ativo["ticker"]
        caminho, mercado = mercado_publico(ticker)
        preco = numero(mercado.get("preco"))
        rendimentos = [
            numero(v)
            for d, v in (mercado.get("divs") or {}).items()
            if date(2025, 10, 1) <= date.fromisoformat(d) <= referencia
        ]
        dividendo = sum(v for v in rendimentos if v is not None)
        dy = dividendo / preco if preco and preco > 0 else None
        registro = registros.get(ticker, {})
        retrato: dict[str, Any] = {
            "ticker": ticker,
            "classe": ativo["classe"],
            "preco": preco,
            "dy": dy,
            "dividendo_ex_12m": dividendo,
            "mercado_arquivo": str(caminho.relative_to(RAIZ)),
            "mercado_sha256": hashlib.sha256(caminho.read_bytes()).hexdigest(),
            "mercado_mtime_utc": datetime.fromtimestamp(
                caminho.stat().st_mtime, UTC
            ).isoformat(),
            "referencia_dividendos": str(referencia),
        }
        if registro.get("cd_cvm") is not None and ativo["classe"] != "FII":
            modelo = contas_cvm.modelo_do_setor(registro.get("setor"))
            indicadores = provedor.calcular_indicadores(
                int(registro["cd_cvm"]), anos=1, modelo=modelo, ano_final=2025
            ).get(2025, {})
            composicao = indicadores.get("composicao_capital")
            especies = sorted(
                {
                    r.get("especie")
                    for r in registros.values()
                    if r.get("cnpj") == registro.get("cnpj") and r.get("especie")
                }
            )
            linhas, _ = acoes_cvm.linhas_da_especie_unica(
                indicadores.get("lpa_basico_por_classe") or {},
                indicadores.get("lpa_basico_agregado"),
                especies,
                lucro_controladores=indicadores.get("lucro_controladores"),
                acoes=composicao.total if composicao else 0,
            )
            divulgados = acoes_cvm.divulgados_coerentes(
                linhas,
                indicadores.get("lucro_controladores"),
                indicadores.get("lucro_liquido"),
            )
            unit = ativo["classe"] == "UNIT"
            componentes = registro.get("acoes_por_unit")
            por_acao = acoes_cvm.derivar_por_acao(
                lucro_controladores=indicadores.get("lucro_controladores"),
                pl_controladores=indicadores.get("pl_controladores"),
                composicao=composicao,
                motivo_composicao=indicadores.get("composicao_motivo"),
                lpa_divulgado=acoes_cvm.divulgado_da_escala(divulgados),
                preco=preco,
                eh_unit=unit,
                acoes_por_unit=componentes,
                lucro_consolidado=indicadores.get("lucro_liquido"),
                shares_outstanding=numero(mercado.get("shares")),
            )
            fator = sum(componentes.values()) if unit and componentes else 1
            recalculado = (
                por_acao.lpa / fator
                if isinstance(por_acao, acoes_cvm.PorAcao) and por_acao.lpa is not None
                else None
            )
            lpa = acoes_cvm.lpa_dos_metodos(
                especie=registro.get("especie"),
                classe=registro.get("classe_preferencial") or registro.get("especie"),
                classes_preferenciais=registro.get("classes_preferenciais"),
                eh_unit=unit,
                acoes_por_unit=componentes,
                divulgados=divulgados,
                recalculado=recalculado,
            )
            retrato.update(
                lpa=lpa[0] if isinstance(lpa, tuple) else None,
                roe=indicadores.get("roe"),
                vpa=por_acao.vpa if isinstance(por_acao, acoes_cvm.PorAcao) else None,
                modelo=modelo,
                cvm_documento=indicadores.get("proveniencia"),
                motivos_por_acao=repr(lpa)
                if isinstance(lpa, acoes_cvm.Abstencao)
                else None,
            )
            proventos = provedor.proventos_do_documento(
                fonte_dfp(2025),
                int(registro["cd_cvm"]),
                indicadores.get("cvm_dt_refer"),
                indicadores.get("cvm_versao"),
                modelo,
            )
            lucro = indicadores.get("lucro_controladores")
            if (
                lucro
                and lucro > 0
                and proventos.get("dividendos") is not None
                and proventos.get("jcp") is not None
            ):
                retrato["payout_dva"] = (
                    proventos["dividendos"] + proventos["jcp"]
                ) / lucro
        retratos.append(retrato)
    salvar(CACHE / "retratos_publicos.json", retratos)

    # Constantes numéricas são lidas pela AST; não há execução nem import de config.
    arvore = ast.parse((RAIZ / "config.py").read_text())
    macro = next(
        n
        for n in arvore.body
        if isinstance(n, ast.ClassDef) and n.name == "MacroContext"
    )
    constantes = {
        n.targets[0].id: n.value.value
        for n in macro.body
        if isinstance(n, ast.Assign)
        and isinstance(n.targets[0], ast.Name)
        and isinstance(n.value, ast.Constant)
        and isinstance(n.value.value, (int, float))
    }
    params_bazin = BazinParams(
        constantes["BAZIN_DY_MIN"],
        constantes["BAZIN_DY_ARMADILHA"],
        constantes["BAZIN_TAXA_MIN"],
    )
    params_gordon = GordonParams(
        constantes["GORDON_DY_MIN"],
        constantes["GORDON_ROE_MIN"],
        constantes["GORDON_G_MAX"],
        constantes["GORDON_PREMIO_RISCO"],
        constantes["GORDON_PAYOUT_MAX"],
    )
    params_graham = GrahamParams(
        constantes["GRAHAM_PL_LIMITE"],
        constantes["GRAHAM_PL_FLOOR"],
        constantes["GRAHAM_PVP_LIMITE_RENDA"],
        constantes["GRAHAM_PVP_LIMITE_CRESCIMENTO"],
    )
    params_lynch = LynchParams(
        constantes["LYNCH_PAYOUT_MAX"],
        constantes["LYNCH_G_MAX"],
        constantes["LYNCH_PL_MULTIPLICADOR"],
        constantes["LYNCH_PL_MAX"],
    )
    v1 = []
    for selic in [0.10 + 0.005 * i for i in range(11)]:
        for retrato in retratos:
            p, dy, roe, lpa = (retrato.get(k) for k in ("preco", "dy", "roe", "lpa"))
            if not p or p <= 0 or dy is None:
                continue
            if retrato.get("classe") == "FII":
                v1.append(
                    {
                        "ticker": retrato["ticker"],
                        "metodo": "rendimento FII V1",
                        "selic": selic,
                        "upside": (
                            dy if 0 <= dy <= constantes["DY_SANIDADE_MAX"] else 0
                        )
                        / (selic * constantes["FII_FATOR_IR"])
                        - 1,
                    }
                )
                continue
            perfil = (
                Perfil.CRESCIMENTO
                if roe is not None
                and roe > constantes["ROE_CRESCIMENTO_MIN"]
                and dy < constantes["DY_CRESCIMENTO_MAX"]
                else Perfil.RENDA
            )
            inputs = MethodInputs(
                as_of=referencia,
                preco=BRL(p),
                lpa=BRL(lpa) if lpa is not None else None,
                roe=Ratio(roe) if roe is not None else None,
                dy=Ratio(dy),
                selic=RateNominal(selic),
                perfil=perfil,
                dy_confiavel=0 <= dy <= constantes["DY_SANIDADE_MAX"],
                pl=Ratio(p / lpa) if lpa else None,
                vpa=BRL(retrato["vpa"]) if retrato.get("vpa") is not None else None,
                pvp=Ratio(p / retrato["vpa"]) if retrato.get("vpa") else None,
            )
            for metodo, params in (
                (Bazin(), params_bazin),
                (Gordon(), params_gordon),
                (Graham(), params_graham),
                (Lynch(), params_lynch),
            ):
                resultado = metodo.calcular(inputs, params)
                v1.append(
                    {
                        "ticker": retrato["ticker"],
                        "metodo": metodo.nome,
                        "selic": selic,
                        "upside": resultado.valor.valor / p - 1
                        if isinstance(resultado, MethodResult)
                        else None,
                        "abstencao": None
                        if isinstance(resultado, MethodResult)
                        else resultado.motivo,
                    }
                )
    pd.DataFrame(v1).to_csv(CACHE / "matriz_v1.csv", index=False)
    tabela_v1 = pd.DataFrame(v1)
    resumo_v1 = (
        tabela_v1.groupby(["metodo", "selic"])["upside"]
        .agg(["count", "median"])
        .reset_index()
        .astype(object)
        .where(lambda d: d.notna(), None)
        .to_dict("records")
    )

    fontes_taxas = json.loads((CACHE / "secao-1.json").read_text())
    taxas = sorted(
        {
            c["taxa_venda_percentual"] / 100
            for c in fontes_taxas.get("candidatos", [])
            if c.get("taxa_venda_percentual") is not None
        }
    )
    focus = json.loads((CACHE / "secao-2.json").read_text())["dados"]
    inflacoes = inflacoes_disponiveis(focus)
    cenarios = []
    for retrato in retratos:
        p, dy, roe, lpa = (retrato.get(k) for k in ("preco", "dy", "roe", "lpa"))
        if not p or p <= 0 or dy is None:
            continue
        for ntnb in taxas:
            for premio in (0.04, 0.05, 0.07):
                k = ntnb + premio
                linha = {"ticker": retrato["ticker"], "ntnb": ntnb, "premio": premio}
                if retrato.get("classe") == "FII":
                    for spread in (0.01, 0.02, 0.03):
                        cenarios.append(
                            {
                                **linha,
                                "modelo": "FII NTN-B + spread",
                                "spread": spread,
                                "upside": (
                                    dy
                                    if 0 <= dy <= constantes["DY_SANIDADE_MAX"]
                                    else 0
                                )
                                / (ntnb + spread)
                                - 1,
                            }
                        )
                    continue
                perfil_crescimento = (
                    roe is not None
                    and roe > constantes["ROE_CRESCIMENTO_MIN"]
                    and dy < constantes["DY_CRESCIMENTO_MAX"]
                )
                if (
                    not perfil_crescimento
                    and constantes["BAZIN_DY_MIN"]
                    <= dy
                    <= constantes["DY_SANIDADE_MAX"]
                ):
                    cenarios.append(
                        {
                            **linha,
                            "modelo": "Bazin taxa fixa 6%",
                            "upside": dy / 0.06 - 1,
                        }
                    )
                    cenarios.append(
                        {
                            **linha,
                            "modelo": "Bazin k real sem crescimento",
                            "upside": dy / k - 1,
                        }
                    )
                if (
                    roe is None
                    or lpa is None
                    or lpa <= 0
                    or not (
                        constantes["GORDON_DY_MIN"]
                        < dy
                        <= constantes["DY_SANIDADE_MAX"]
                    )
                    or not roe > constantes["GORDON_ROE_MIN"]
                ):
                    continue
                retencao = 1 - min(dy * p / lpa, constantes["GORDON_PAYOUT_MAX"])
                g_nominal_v1 = roe * retencao
                for inflacao in inflacoes:
                    for definicao, g_real in (
                        ("i", (1 + g_nominal_v1) / (1 + inflacao) - 1),
                        ("ii", ((1 + roe) / (1 + inflacao) - 1) * retencao),
                        (
                            "iii_teto_candidato_2%",
                            min((1 + g_nominal_v1) / (1 + inflacao) - 1, 0.02),
                        ),
                    ):
                        k_nominal = (1 + k) * (1 + inflacao) - 1
                        g_nominal = (1 + g_real) * (1 + inflacao) - 1
                        if k <= g_real:
                            continue
                        valor_real = dy * p * (1 + g_real) / (k - g_real)
                        valor_nominal = (
                            dy * p * (1 + g_nominal) / (k_nominal - g_nominal)
                        )
                        misto = (
                            dy * p * (1 + g_nominal) / (k - g_nominal)
                            if k > g_nominal
                            else None
                        )
                        cenarios.append(
                            {
                                **linha,
                                "modelo": "Gordon",
                                "definicao": definicao,
                                "inflacao": inflacao,
                                "g_real": g_real,
                                "upside": valor_real / p - 1,
                                "valor_real": valor_real,
                                "valor_nominal": valor_nominal,
                                "erro_fisher": abs(valor_nominal - valor_real),
                                "misto_div_nominal": misto / valor_nominal
                                if misto is not None and valor_nominal
                                else None,
                            }
                        )
    pd.DataFrame(cenarios).to_csv(CACHE / "matriz_sensibilidade.csv", index=False)
    tabela_cenarios = pd.DataFrame(cenarios)
    resumo_cenarios = (
        tabela_cenarios.groupby(
            ["modelo", "premio", "ntnb", "inflacao", "definicao", "spread"],
            dropna=False,
        )["upside"]
        .agg(["count", "median"])
        .reset_index()
        .astype(object)
        .where(lambda d: d.notna(), None)
        .to_dict("records")
    )
    return {
        "estado": "diagnóstico parcial, classificações agregadas não determinadas",
        "amostra_publica": [r for r in universo() if r["situacao"] == "atual"],
        "resumo_v1": resumo_v1,
        "resumo_cenarios": resumo_cenarios,
        "retratos": "outputs/levantamento_cache/f2b21/retratos_publicos.json",
        "limites": "Preços do retrato público yfinance arquivado; proventos ex-data até 30/09/2026; fundamentos DFP2025 recalculados no checkout. Não reproduz a cascata inteira nem o score agregado. O teto real de 2% é apenas um cenário numérico, sem escolha metodológica. Os regimes de Gordon são comparados sobre a mesma série de fluxos.",
        "consequencia": "Usar como sensibilidade diagnóstica, sem aprovar taxa, teto ou spread. Contagens de classificações da V1, IPCA SGS e séries de mercado atualizadas continuam não determinadas.",
        "grades_exigidas": {
            "selic": [0.10, 0.11, 0.12, 0.13, 0.14, 0.15],
            "premio": [0.04, 0.05, 0.07],
            "spread_fii": [0.01, 0.02, 0.03],
            "g_real": [
                "Fisher do ROE vezes retenção nominal",
                "ROE real vezes retenção",
                "teto real a decidir",
            ],
        },
    }


def secao4(atualizar: bool) -> dict[str, Any]:
    """Schema real do Informe e valores de amostra; unidade não inferida por magnitude."""
    meta = consultar("fii_meta_indice", f"{CVM}/FII/DOC/INF_MENSAL/META/", atualizar)
    portal = consultar(
        "fii_dados_indice", f"{CVM}/FII/DOC/INF_MENSAL/DADOS/", atualizar
    )
    consultar(
        "fii_meta_zip",
        f"{CVM}/FII/DOC/INF_MENSAL/META/meta_inf_mensal_fii.zip",
        atualizar,
    )
    consultar(
        "fii_norma",
        "https://conteudo.cvm.gov.br/legislacao/resolucoes/anexos/100/resol175consolid.pdf",
        atualizar,
    )
    consultar(
        "fii_norma_docx",
        "https://conteudo.cvm.gov.br/legislacao/resolucoes/anexos/100/resol184.docx",
        atualizar,
    )
    norma_meta = json.loads((CACHE / "fii_norma_docx.meta.json").read_text())
    with zipfile.ZipFile(RAIZ / norma_meta["arquivo"]) as documento:
        texto_norma = " ".join(
            ElementTree.fromstring(documento.read("word/document.xml")).itertext()
        )
    texto_norma = re.sub(r"\s+", " ", texto_norma)
    norma_confere = bool(
        re.search(
            r"Dividend Yield do Mês de Referência.*Rendimentos declarados por cota.*mês anterior ao de referência",
            texto_norma,
        )
    )

    def anual(ano: int) -> dict[str, Any]:
        return consultar(
            f"fii_anual_{ano}",
            f"{CVM}/FII/DOC/INF_MENSAL/DADOS/inf_mensal_fii_{ano}.zip",
            atualizar,
        )

    with ThreadPoolExecutor(max_workers=4) as executor:
        anuais = list(executor.map(anual, range(2016, 2027)))
    partes = []
    periodos_anuais = []
    cnpjs_amostra = {
        r["cnpj"]
        for r in universo()
        if r["classe"] == "FII" and r["situacao"] == "atual"
    }
    for registro in anuais:
        if registro.get("status") != 200:
            continue
        tabela = csv_zip(RAIZ / registro["arquivo"], "complemento")
        tabela = tabela.rename(columns={"CNPJ_Fundo": "CNPJ_Fundo_Classe"})
        periodos_anuais.append(
            {
                "arquivo": registro["arquivo"],
                "primeira_referencia": str(tabela["Data_Referencia"].min()),
                "ultima_referencia": str(tabela["Data_Referencia"].max()),
                "linhas": len(tabela),
            }
        )
        partes.append(tabela[tabela["CNPJ_Fundo_Classe"].isin(cnpjs_amostra)])
    serie = pd.concat(partes, ignore_index=True) if partes else pd.DataFrame()
    if not serie.empty:
        serie["_versao"] = pd.to_numeric(serie["Versao"], errors="coerce")
        serie = serie.sort_values(
            ["CNPJ_Fundo_Classe", "Data_Referencia", "_versao"], na_position="first"
        ).drop_duplicates(["CNPJ_Fundo_Classe", "Data_Referencia"], keep="last")
        for campo in ("Valor_Patrimonial_Cotas", "Percentual_Dividend_Yield_Mes"):
            serie[campo] = pd.to_numeric(serie[campo], errors="coerce")
        grupo = serie.groupby("CNPJ_Fundo_Classe")
        serie["vp_anterior"] = grupo["Valor_Patrimonial_Cotas"].shift(1)
        serie["mes"] = (
            pd.to_datetime(serie["Data_Referencia"]).dt.to_period("M").astype(int)
        )
        consecutivo = grupo["mes"].diff() == 1
        serie["rendimento_reconstruido"] = (
            serie["Percentual_Dividend_Yield_Mes"] * serie["vp_anterior"]
        ).where(consecutivo)
        serie["rendimento_12m"] = serie.groupby("CNPJ_Fundo_Classe")[
            "rendimento_reconstruido"
        ].transform(lambda x: x.rolling(12, min_periods=12).sum())
        serie.to_csv(CACHE / "fii_rendimentos_candidatos.csv", index=False)
    fontes_precos = []
    precos = []
    tickers = {
        r["ticker"]
        for r in universo()
        if r["classe"] == "FII" and r["situacao"] == "atual"
    }
    tickers_bytes = {t.encode("ascii") for t in tickers}
    for ano in range(2016, 2027):
        registro = consultar(
            f"cotahist_anual_{ano}",
            f"https://bvmf.bmfbovespa.com.br/InstDados/SerHist/COTAHIST_A{ano}.ZIP",
            atualizar,
        )
        fontes_precos.append(registro)
        if registro.get("status") != 200:
            continue
        destino_precos = CACHE / f"cotahist_fii_mensal_{ano}.csv"
        if destino_precos.exists() and not atualizar:
            precos += pd.read_csv(destino_precos).to_dict("records")
            continue
        ultimos: dict[tuple[str, str], dict[str, Any]] = {}
        from sentinela.data.providers.b3_cotahist import parsear_linha

        with (
            zipfile.ZipFile(RAIZ / registro["arquivo"]) as z,
            z.open(z.namelist()[0]) as linhas,
        ):
            for linha in linhas:
                if (
                    linha[:2] != b"01"
                    or linha[24:27] != b"010"
                    or linha[12:24].strip() not in tickers_bytes
                ):
                    continue
                cotacao = parsear_linha(linha.decode("latin-1"))
                chave = (cotacao.codigo_negociacao, cotacao.data.strftime("%Y-%m"))
                if chave not in ultimos or str(cotacao.data) > ultimos[chave]["data"]:
                    ultimos[chave] = {
                        "ticker": chave[0],
                        "mes_texto": chave[1],
                        "data": str(cotacao.data),
                        "preco": cotacao.fechamento,
                    }
        tabela_precos = pd.DataFrame(
            list(ultimos.values()), columns=["ticker", "mes_texto", "data", "preco"]
        )
        tabela_precos.to_csv(destino_precos, index=False)
        precos += tabela_precos.to_dict("records")
    estatisticas_spread = []
    estatisticas_janelas = []
    medianas_mensais = []
    agregados_spread: dict[str, Any] = {}
    upsides_com_medianas: list[dict[str, Any]] = []
    tesouro_meta = consultar("tesouro_historico", TD_CSV, atualizar)
    spread_estado = (
        "medido"
        if precos and not serie.empty and tesouro_meta.get("status") == 200
        else "não determinado: sem preços, sem Informe ou sem o histórico do Tesouro"
    )
    if spread_estado == "medido":
        mapa = {
            r["cnpj"]: r["ticker"]
            for r in universo()
            if r["classe"] == "FII" and r["situacao"] == "atual"
        }
        serie["ticker"] = serie["CNPJ_Fundo_Classe"].map(mapa)
        serie["mes_texto"] = pd.to_datetime(serie["Data_Referencia"]).dt.strftime(
            "%Y-%m"
        )
        serie = serie.merge(
            pd.DataFrame(precos), on=["ticker", "mes_texto"], how="left"
        )
        serie["dy_12m_candidato"] = serie["rendimento_12m"] / serie["preco"]
        tesouro = pd.read_csv(RAIZ / tesouro_meta["arquivo"], sep=";", decimal=",")
        tesouro["data"] = pd.to_datetime(tesouro["Data Base"], dayfirst=True)
        tesouro["vencimento"] = pd.to_datetime(
            tesouro["Data Vencimento"], dayfirst=True
        )
        tesouro = tesouro[
            tesouro["Tipo Titulo"].str.contains("IPCA")
            & (tesouro["vencimento"].dt.year >= 2035)
        ]
        diaria = tesouro.groupby("data")["Taxa Venda Manha"].mean().sort_index()
        mensal = diaria.resample("ME").last()
        taxas = {k.strftime("%Y-%m"): v / 100 for k, v in mensal.items()}
        serie["ntnb_media_2035_candidata"] = serie["mes_texto"].map(taxas)
        serie["spread_candidato"] = (
            serie["dy_12m_candidato"] - serie["ntnb_media_2035_candidata"]
        )
        tipos = {r["ticker"]: r.get("tipo_fii_no_universo") for r in universo()}
        serie["tipo_atual_universo"] = serie["ticker"].map(tipos)
        medianas = (
            serie.groupby(["mes_texto", "tipo_atual_universo"])["spread_candidato"]
            .agg(["count", "median"])
            .reset_index()
        )
        medianas_mensais = (
            medianas.astype(object).where(medianas.notna(), None).to_dict("records")
        )
        serie.to_csv(CACHE / "fii_spreads_candidatos.csv", index=False)
        # Mediana mensal entre os fundos, por grupo, na série toda e nos últimos 5 anos.
        com_spread = serie.dropna(subset=["spread_candidato"])
        fim_serie = pd.to_datetime(com_spread["Data_Referencia"]).max()
        for grupo_nome, sub in (
            ("todos", com_spread),
            ("tijolo", com_spread[com_spread["tipo_atual_universo"] == "tijolo"]),
            ("papel", com_spread[com_spread["tipo_atual_universo"] == "papel"]),
        ):
            mensal_grupo = sub.groupby("mes_texto")["spread_candidato"].median()
            janelas_grupo = {}
            for rotulo, inicio in (
                ("serie_toda", None),
                ("ultimos_5_anos", fim_serie - pd.DateOffset(years=5)),
            ):
                valores = mensal_grupo
                if inicio is not None:
                    valores = mensal_grupo[pd.to_datetime(mensal_grupo.index) > inicio]
                janelas_grupo[rotulo] = {
                    "meses": len(valores),
                    "mediana": numero(valores.median()),
                    "p25": numero(valores.quantile(0.25)),
                    "p75": numero(valores.quantile(0.75)),
                }
            agregados_spread[grupo_nome] = {
                "fundos": int(sub["ticker"].nunique()),
                "primeiro_mes": mensal_grupo.index.min(),
                "ultimo_mes": mensal_grupo.index.max(),
                "atual": numero(mensal_grupo.iloc[-1]),
                **janelas_grupo,
            }
        # Pergunta 3: os FIIs da matriz com NTN-B + as medianas acima (DY do retrato público).
        retratos_fii = CACHE / "retratos_publicos.json"
        candidatos_tesouro = json.loads((CACHE / "secao-1.json").read_text()).get(
            "candidatos", []
        )
        ntnb_media = next(
            (
                c["taxa_venda_percentual"] / 100
                for c in candidatos_tesouro
                if c["tipo"] == "IPCA+ com e sem cupons"
            ),
            None,
        )
        if retratos_fii.exists() and ntnb_media is not None:
            fiis = [
                r
                for r in json.loads(retratos_fii.read_text())
                if r.get("classe") == "FII"
                and r.get("preco")
                and r.get("dy") is not None
            ]
            todos = agregados_spread["todos"]
            for rotulo, spread in (
                ("p25_serie_toda", todos["serie_toda"]["p25"]),
                ("mediana_serie_toda", todos["serie_toda"]["mediana"]),
                ("mediana_ultimos_5_anos", todos["ultimos_5_anos"]["mediana"]),
                ("p75_serie_toda", todos["serie_toda"]["p75"]),
            ):
                ups = [
                    (r["dy"] if 0 <= r["dy"] <= 0.25 else 0) / (ntnb_media + spread) - 1
                    for r in fiis
                ]
                upsides_com_medianas.append(
                    {
                        "spread": rotulo,
                        "valor_spread": spread,
                        "ntnb": ntnb_media,
                        "fiis": len(ups),
                        "mediana_upside": numero(pd.Series(ups).median()),
                    }
                )
        for ticker, grupo_fundo in serie.groupby("ticker"):
            valores = grupo_fundo["spread_candidato"].dropna()
            estatisticas_spread.append(
                {
                    "ticker": ticker,
                    "meses_com_spread": len(valores),
                    "mediana": numero(valores.median()),
                    "p25": numero(valores.quantile(0.25)),
                    "p75": numero(valores.quantile(0.75)),
                    "ultimo": numero(valores.iloc[-1]) if len(valores) else None,
                }
            )
            fim = pd.to_datetime(grupo_fundo["Data_Referencia"]).max()
            for anos in (5, 10):
                janela = grupo_fundo[
                    pd.to_datetime(grupo_fundo["Data_Referencia"])
                    > fim - pd.DateOffset(years=anos)
                ]
                valores_janela = janela["spread_candidato"].dropna()
                estatisticas_janelas.append(
                    {
                        "ticker": ticker,
                        "anos_solicitados": anos,
                        "meses_com_spread": len(valores_janela),
                        "mediana": numero(valores_janela.median()),
                        "p25": numero(valores_janela.quantile(0.25)),
                        "p75": numero(valores_janela.quantile(0.75)),
                        "fim": str(fim.date()),
                    }
                )
    # O ano corrente do Informe, coletado acima (antes vinha de um cache da 2A).
    arquivo = RAIZ / anual(2026)["arquivo"]
    complemento = csv_zip(arquivo, "complemento")
    geral = csv_zip(arquivo, "geral")
    complemento["_versao"] = pd.to_numeric(complemento["Versao"], errors="coerce")
    complemento = complemento.sort_values(
        ["Data_Referencia", "_versao"], ascending=False
    ).drop_duplicates(["CNPJ_Fundo_Classe", "Data_Referencia"])
    campos = [
        "CNPJ_Fundo_Classe",
        "Data_Referencia",
        "Versao",
        "Valor_Patrimonial_Cotas",
        "Percentual_Dividend_Yield_Mes",
    ]
    amostras = []
    for fundo in universo():
        if fundo["classe"] != "FII" or fundo["situacao"] != "atual":
            continue
        linhas = complemento[complemento["CNPJ_Fundo_Classe"] == fundo["cnpj"]]
        cronologico = linhas.sort_values("Data_Referencia").copy()
        for campo in (
            "Valor_Patrimonial_Cotas",
            "Percentual_Rentabilidade_Patrimonial_Mes",
            "Percentual_Dividend_Yield_Mes",
            "Percentual_Amortizacao_Cotas_Mes",
        ):
            cronologico[campo] = pd.to_numeric(cronologico[campo], errors="coerce")
        vp = cronologico["Valor_Patrimonial_Cotas"]
        anterior = vp.shift(1)
        patrimonial = cronologico["Percentual_Rentabilidade_Patrimonial_Mes"]
        consecutivo = (
            pd.to_datetime(cronologico["Data_Referencia"])
            .dt.to_period("M")
            .astype(int)
            .diff()
            == 1
        )
        sem_amortizacao = cronologico["Percentual_Amortizacao_Cotas_Mes"] == 0
        mediveis = consecutivo & sem_amortizacao & (anterior > 0)
        retorno_vp = vp / anterior - 1
        erro_razao = (patrimonial - retorno_vp).abs()[mediveis]
        erro_percentual = (patrimonial / 100 - retorno_vp).abs()[mediveis]
        amostras.append(
            {
                "ticker": fundo["ticker"],
                "meses": len(linhas),
                "ultimos": linhas[campos].head(2).to_dict("records"),
                "identidade_patrimonial": {
                    "meses_sem_amortizacao": int(mediveis.sum()),
                    "erro_mediano_se_razao": numero(erro_razao.median()),
                    "erro_mediano_se_percentual": numero(erro_percentual.median()),
                },
                "rendimento_reconstruido_ultimo": numero(
                    (cronologico["Percentual_Dividend_Yield_Mes"] * anterior).iloc[-1]
                ),
            }
        )
    return {
        "fontes": [meta, portal],
        "anos_no_portal": sorted(
            {
                int(a)
                for a in re.findall(
                    r"inf_mensal_fii_(\d{4})\.zip",
                    (RAIZ / portal["arquivo"]).read_text(),
                )
            }
        ),
        "arquivo_local": str(arquivo.relative_to(RAIZ)),
        "sha256": hashlib.sha256(arquivo.read_bytes()).hexdigest(),
        "colunas_complemento": [
            c for c in complemento.columns if not c.startswith("_")
        ],
        "colunas_geral": list(geral.columns),
        "amostras": amostras,
        "identidade_patrimonial_entre_fundos": {
            "fundos": sum(
                a["identidade_patrimonial"]["erro_mediano_se_razao"] is not None
                for a in amostras
            ),
            "erro_mediano_se_razao": numero(
                pd.Series(
                    [
                        a["identidade_patrimonial"]["erro_mediano_se_razao"]
                        for a in amostras
                    ],
                    dtype=float,
                ).median()
            ),
            "erro_mediano_se_percentual": numero(
                pd.Series(
                    [
                        a["identidade_patrimonial"]["erro_mediano_se_percentual"]
                        for a in amostras
                    ],
                    dtype=float,
                ).median()
            ),
        },
        "norma": norma_meta,
        "fontes_anuais": anuais,
        "periodos_anuais": periodos_anuais,
        "serie_candidata": "outputs/levantamento_cache/f2b21/fii_rendimentos_candidatos.csv",
        "fontes_precos_anuais": fontes_precos,
        "spreads_candidatos_por_fundo": estatisticas_spread,
        "spreads_candidatos_janelas": estatisticas_janelas,
        "medianas_mensais_amostra_tipo_atual": medianas_mensais,
        "spread_estado": spread_estado,
        "spreads_agregados": agregados_spread,
        "fii_upside_ntnb_mais_medianas_de_spread": upsides_com_medianas,
        "limite_spreads": "Diagnóstico da amostra atual com sobrevivência, sem ajuste de eventos de cotas e com um vértice candidato do Tesouro; não é mediana de todos os FIIs historicamente listados nem parâmetro aprovado.",
        "norma_fii_define_base_patrimonial_anterior": norma_confere,
        "unidade_e_base": "Norma FII: rendimento declarado por cota dividido pelo VP da cota do fim do mês anterior. O CSV deve ser confrontado com a identidade patrimonial; nome Percentual sozinho não determina escala.",
        "distribuicao_direta": "não há campo explícito de valor distribuído por cota no complemento; Rendimentos_Distribuir no ativo/passivo é saldo de obrigação, não fluxo pago",
        "spread_5_10_anos": "não determinado sem base/unidade e série de distribuição/ajustes por cota confirmadas; não anualizar o último mês",
        "selic_liquida_mensal": "não determinado sem hipótese de tributação aprovada e série histórica correspondente",
        "consequencia": "F2B-28 deve parar se a base não for determinada; F2B-25 não pode inventar mediana histórica de spread.",
    }


def secao5(atualizar: bool) -> dict[str, Any]:
    """Controle público do IF.data e universo financeiro do índice oficial."""
    raiz = f"{OLINDA}/IFDATA/versao/v1/odata/"
    consultas = {}
    for relatorio in ("1", "16"):
        url = (
            raiz
            + f"IfDataValores(AnoMes=202606,TipoInstituicao=1,Relatorio='{relatorio}')?$format=json&$filter=CodInst%20eq%20'C0080329'"
        )
        meta = consultar(f"ifdata_bb_{relatorio}", url, atualizar)
        consultas[relatorio] = {"fonte": meta, "dados": corpo_json(meta)}
    financeiros = []
    bpp = csv_zip(fonte_dfp(2025, preferir_dados=True), "BPP_con")
    bpp = bpp[bpp["ORDEM_EXERC"] == "ÚLTIMO"]
    for registro in indice():
        setor = str(registro.get("setor") or "")
        if any(
            p in setor.lower()
            for p in ("banc", "financeir", "segur", "corret", "crédito", "credito")
        ):
            financeiro = {
                k: registro.get(k)
                for k in (
                    "ticker",
                    "nome",
                    "cnpj",
                    "cd_cvm",
                    "setor",
                    "segmento",
                    "classe",
                )
            }
            linhas = bpp[
                (bpp["CNPJ_CIA"] == registro.get("cnpj"))
                & bpp["CD_CONTA"].isin(["2.03", "2.07", "2.08"])
            ]
            financeiro["contas_raizes_bpp_2025"] = (
                linhas[["DT_REFER", "VERSAO", "CD_CONTA", "DS_CONTA"]]
                .drop_duplicates()
                .to_dict("records")
            )
            financeiros.append(financeiro)
    dados16 = (consultas["16"]["dados"] or {}).get("value", [])
    saldos = {r["NomeColuna"]: r["Saldo"] for r in dados16}
    inadimplencia = {
        "estado": "fonte encontrada",
        "linhas": [
            {k: r.get(k) for k in ("NomeColuna", "DescricaoColuna", "Conta", "Saldo")}
            for r in dados16
            if r["NomeColuna"]
            in ("Inadimplência", "Ativos problemáticos", "Total Geral")
        ],
        "razao_candidata_mesmo_relatorio": saldos.get("Inadimplência", 0)
        / saldos["Total Geral"]
        if saldos.get("Total Geral")
        else None,
        "limite": "A fonte diz carteira ativa inadimplida arrastada; não afirmar equivalência a atraso de 90 dias ou adotar denominador sem conferir o conceito.",
    }
    bancos = []
    caminho_retratos = CACHE / "retratos_publicos.json"
    if caminho_retratos.exists():
        retratos = json.loads(caminho_retratos.read_text())
        taxas = json.loads((CACHE / "secao-1.json").read_text()).get("candidatos", [])
        inflacoes = json.loads((CACHE / "secao-2.json").read_text())["dados"]
        ipcas = inflacoes_disponiveis(inflacoes)
        for retrato in retratos:
            if retrato.get("modelo") != "banco":
                continue
            roe, vpa, payout, p = (
                retrato.get(k) for k in ("roe", "vpa", "payout_dva", "preco")
            )
            if roe is None or not vpa or vpa <= 0 or payout is None:
                bancos.append(
                    {
                        "ticker": retrato["ticker"],
                        "estado": "não determinado",
                        "motivo": "ROE, VPA positivo ou payout ausente",
                    }
                )
                continue
            for taxa in taxas:
                if taxa.get("taxa_venda_percentual") is None:
                    continue
                for premio in (0.04, 0.05, 0.07):
                    k_real = taxa["taxa_venda_percentual"] / 100 + premio
                    for inflacao in ipcas:
                        roe_real = (1 + roe) / (1 + inflacao) - 1
                        gs = {
                            "ROE_nominal_x_retencao": (1 + roe * (1 - payout))
                            / (1 + inflacao)
                            - 1,
                            "ROE_real_x_retencao": roe_real * (1 - payout),
                            **{
                                f"inflacao_mais_{pontos}pp": (
                                    1 + inflacao + pontos / 100
                                )
                                / (1 + inflacao)
                                - 1
                                for pontos in (0, 1, 2)
                            },
                        }
                        for definicao, g_real in gs.items():
                            if k_real <= g_real:
                                continue
                            g_nominal = (1 + g_real) * (1 + inflacao) - 1
                            k_nominal = (1 + k_real) * (1 + inflacao) - 1
                            real = (roe_real - g_real) / (k_real - g_real)
                            nominal = (roe - g_nominal) / (k_nominal - g_nominal)
                            bancos.append(
                                {
                                    "ticker": retrato["ticker"],
                                    "vertice": taxa["vertice"],
                                    "tipo_titulo": taxa["tipo"],
                                    "premio": premio,
                                    "inflacao": inflacao,
                                    "g": definicao,
                                    "payout_dva": payout,
                                    "roe": roe,
                                    "vpa": vpa,
                                    "pvp_mercado": p / vpa if p else None,
                                    "pvp_real": real,
                                    "pvp_nominal": nominal,
                                    "erro_fisher": abs(real - nominal),
                                }
                            )
    pd.DataFrame(bancos).to_csv(CACHE / "bancos_pvp_candidatos.csv", index=False)
    return {
        "controle_bb": consultas,
        "financeiros_indice": financeiros,
        "inadimplencia": inadimplencia,
        "pvp_justificado": {
            "estado": "medido"
            if caminho_retratos.exists()
            else "não determinado: rode a seção 3 antes (retratos_publicos.json)",
            "arquivo": "outputs/levantamento_cache/f2b21/bancos_pvp_candidatos.csv",
            "cenarios": len(bancos),
            "erro_maximo_fisher": max(
                (r["erro_fisher"] for r in bancos if "erro_fisher" in r), default=None
            ),
        },
        "consequencia": "F2B-3 tem uma fonte candidata de inadimplência, cujo conceito ainda precisa ser validado; modelos e tipos de negócio alimentam FINANCEIRAS sem decidir escopo.",
    }


def secao6(atualizar: bool) -> dict[str, Any]:
    """B3: procura evidência conjunta de ISIN e CNPJ, sem aceitar apenas o ticker."""
    parametros = {"codeCVM": "22616", "language": "pt-br"}
    codificado = base64.b64encode(json.dumps(parametros).encode()).decode()
    urls = {
        "b3_btg_detalhe": "https://sistemaswebb3-listados.b3.com.br/listedCompaniesProxy/CompanyCall/GetDetail/"
        + codificado,
        "b3_instrumentos": "https://arquivos.b3.com.br/apinegocios/tickercsv/2026-10-16",
    }
    fontes = {}
    for nome, url in urls.items():
        meta = consultar(nome, url, atualizar)
        texto = (RAIZ / meta["arquivo"]).read_text(errors="replace")
        fontes[nome] = {
            "fonte": meta,
            "json": corpo_json(meta),
            "tem_isin": "BRBPACUNT006" in texto,
            "tem_cnpj": bool(re.search(r"30\D*306\D*294\D*0*001\D*45", texto)),
        }
    detalhe = fontes["b3_btg_detalhe"]["json"] or {}
    registro_btg = {
        "cnpj": detalhe.get("cnpj"),
        "codeCVM": detalhe.get("codeCVM"),
        "companyName": detalhe.get("companyName"),
        "otherCodes": detalhe.get("otherCodes"),
        "mesmo_registro_cnpj_e_isin": detalhe.get("cnpj") == "30306294000145"
        and any(
            c.get("isin") == "BRBPACUNT006" for c in detalhe.get("otherCodes") or []
        ),
    }
    return {
        "registro_btg": registro_btg,
        "fontes": fontes,
        "estado": "conferir os dois identificadores no mesmo registro",
        "consequencia": "F2A-39 depende da aceitação do Marcos na BTG; nenhuma correção aplicada aqui.",
    }


def secao7(atualizar: bool) -> dict[str, Any]:
    """Coleta evidência de código dos cinco pontos pendentes, sem corrigi-los."""
    del atualizar
    import cvm_provider
    from sentinela.data.providers import b3_cotahist

    tabela = csv_zip(fonte_dfp(2025, preferir_dados=True), "DRE_con")
    basicas = tabela[tabela["CD_CONTA"].str.startswith("3.99.01.")]
    descricoes = sorted(basicas["DS_CONTA"].dropna().str.strip().unique().tolist())
    provedor = cvm_provider.CVMProvider(str(CACHE / "cvm"))
    arquivo = fonte_dfp(2025, preferir_dados=True)
    anual = provedor.parsear_demonstrativo(
        arquivo, "DRE_con", include_cd_cvm=True, include_versao=True
    )
    ttm = provedor.parsear_demonstrativo(
        arquivo,
        "DRE_con",
        include_cd_cvm=True,
        include_versao=True,
        include_periodo=True,
    )
    with tempfile.TemporaryDirectory(dir=CACHE) as pasta:
        resposta = MagicMock()
        resposta.__enter__.return_value = resposta
        resposta.raise_for_status.side_effect = requests.HTTPError("HTTP 404 sintético")
        with (
            patch("cvm_download.requests.get", return_value=resposta) as get,
            patch("cvm_download.time.sleep") as sleep,
        ):
            try:
                b3_cotahist.baixar_arquivo(
                    "https://bvmf.bmfbovespa.com.br/InstDados/SerHist/COTAHIST_A2099.ZIP",
                    Path(pasta) / "ausente.zip",
                )
            except requests.HTTPError:
                pass
            repeticoes = {
                "chamadas_get": get.call_count,
                "backoff_segundos": [c.args[0] for c in sleep.call_args_list],
            }
    return {
        "regex_lpa": {
            "regex": cvm_provider._CLASSE_NA_DESCRICAO.pattern,
            "descricoes_reais": descricoes,
        },
        "moeda": {
            "valores_dfp_2025": tabela["MOEDA"].value_counts().to_dict(),
            "filtro": "parsear_demonstrativo converte escala, mas não valida MOEDA",
        },
        "dva_ttm": {
            "estado": "confirmado",
            "evidencia": "cvm_provider.CVMProvider._acumulados_do_arquivo: DVA_con no laço sem tratamento de arquivo ausente",
        },
        "cache_serie_ttm": {
            "estado": "confirmadas duas projeções distintas em cache",
            "evidencia": "parsear_demonstrativo compartilha _cache_parse; chaves diferem com include_periodo; medir bytes duplicados separadamente",
            "linhas_anual": len(anual),
            "linhas_ttm": len(ttm),
            "bytes_anual": int(anual.memory_usage(deep=True).sum()),
            "bytes_ttm": int(ttm.memory_usage(deep=True).sum()),
        },
        "cotahist_404": {
            "funcao": b3_cotahist.baixar_arquivo.__module__,
            "reproducao_sem_rede": repeticoes,
            "consequencia": "três tentativas também para 404; nenhuma mudança de política neste levantamento",
        },
    }


def secao8(atualizar: bool) -> dict[str, Any]:
    """Medições locais reproduzíveis dos pontos da ficha e da auditoria."""
    del atualizar
    from cvm_provider import composicao_do_documento, lpa_basico_por_classe
    from data_quality import DataQualityReport
    from sentinela.data import acoes_cvm, contas_cvm, proveniencia, series_cvm
    from sentinela.data.referencia.correcoes import Correcao, validar_correcoes

    arquivo = fonte_dfp(2025, preferir_dados=True)
    capital = csv_zip(arquivo, "composicao_capital")
    dre = csv_zip(arquivo, "DRE_con")
    tes = [c for c in capital if "TESOURO" in c]
    zero_com_especies = pd.DataFrame()
    if len(tes) >= 3:
        total = pd.to_numeric(capital["QT_ACAO_TOTAL_TESOURO"], errors="coerce")
        on = pd.to_numeric(capital["QT_ACAO_ORDIN_TESOURO"], errors="coerce")
        pn = pd.to_numeric(capital["QT_ACAO_PREF_TESOURO"], errors="coerce")
        zero_com_especies = capital[(total == 0) & ((on != 0) | (pn != 0))]
    ultimas = dre[dre["ORDEM_EXERC"] == "ÚLTIMO"]
    lpa = ultimas[ultimas["CD_CONTA"].str.startswith("3.99")]
    versoes = lpa.groupby(["CD_CVM", "DT_REFER"])["VERSAO"].nunique()
    resultados = {
        "tesouraria": {
            "colunas": tes,
            "linhas_total_zero_especies_nao_zero": len(zero_com_especies),
            "companhias": zero_com_especies.get(
                "CNPJ_CIA", pd.Series(dtype=str)
            ).nunique(),
            "amostra": zero_com_especies.head(10).to_dict("records"),
        },
        "versoes_399": {
            "companhias_multiversao": len({i[0] for i in versoes[versoes > 1].index}),
            "documentos_multiversao": int((versoes > 1).sum()),
            "grupos": lpa["GRUPO_DFP"].value_counts().to_dict(),
        },
        "divulgados_nan_zero": {
            "nan_com_prejuizo": repr(
                acoes_cvm.divulgados_coerentes({"ON": [float("nan")]}, -10.0, -10.0)
            ),
            "zero_com_prejuizo": repr(
                acoes_cvm.divulgados_coerentes({"ON": [0.0]}, -10.0, -10.0)
            ),
        },
        "meses_ignora_dia": {
            "resultado": series_cvm._meses(date(2026, 1, 31), date(2026, 3, 1)),
            "intervalo": "2026-01-31..2026-03-01",
        },
        "proventos_ausentes": {
            "so_dividendos": series_cvm.proventos(10.0, None),
            "so_jcp": series_cvm.proventos(None, 10.0),
        },
        "cnpj_espacos": proveniencia.entrega_no_indice(
            [{"CNPJ_CIA": " 11.111.111/0001-11 ", "DT_RECEB": "2026-03-01"}],
            {"CNPJ_CIA": "11.111.111/0001-11"},
        ),
        "classe_preferencial_minuscula": acoes_cvm.especie_da_classe("pna"),
    }
    correcao = Correcao(
        "INVALIDO",
        "11.111.111/0001-11",
        "X",
        "sintético",
        "oficial.csv",
        "codigo",
        "2026-10-18",
    )
    resultados["ticker_invalido_aceito"] = bool(validar_correcoes([correcao]))
    registros = [r for r in indice() if r.get("ticker") in ("BTCI11", "TRPL11")]
    resultados["btci_trpl"] = registros
    isins = {"BTCI11": "BRBTCICTF005", "TRPL11": "BRTRPLCTF015"}
    geral_fii = csv_zip(
        RAIZ
        / consultar(
            "fii_anual_2026",
            f"{CVM}/FII/DOC/INF_MENSAL/DADOS/inf_mensal_fii_2026.zip",
        )["arquivo"],
        "geral",
    )
    arvore_config = ast.parse((RAIZ / "config.py").read_text())
    listas = {}
    for no in ast.walk(arvore_config):
        if (
            isinstance(no, ast.Assign)
            and isinstance(no.targets[0], ast.Name)
            and no.targets[0].id in ("FIIS_CONHECIDOS", "UNITS_CONHECIDAS")
        ):
            listas[no.targets[0].id] = {
                e.value for e in ast.walk(no.value) if isinstance(e, ast.Constant)
            }
    resultados["btci_trpl_isin_no_informe_2026"] = {
        t: {
            "isin": i,
            "linhas_no_informe": int((geral_fii["Codigo_ISIN"] == i).sum()),
            "listas_conhecidas": sorted(n for n, v in listas.items() if t in v),
        }
        for t, i in isins.items()
    }
    obrigatorias = [
        "QT_ACAO_ORDIN_CAP_INTEGR",
        "QT_ACAO_PREF_CAP_INTEGR",
        "QT_ACAO_ORDIN_TESOURO",
        "QT_ACAO_PREF_TESOURO",
    ]
    quantidades = capital[obrigatorias].apply(pd.to_numeric, errors="coerce")
    invalidas = (
        quantidades.isna().any(axis=1)
        | (quantidades < 0).any(axis=1)
        | (quantidades % 1 != 0).any(axis=1)
    )
    invalidas |= quantidades[obrigatorias[2]] > quantidades[obrigatorias[0]]
    invalidas |= quantidades[obrigatorias[3]] > quantidades[obrigatorias[1]]
    resultados["composicoes_invalidas_reais"] = {
        "linhas": int(invalidas.sum()),
        "companhias": int(capital.loc[invalidas, "CNPJ_CIA"].nunique()),
    }
    linha_capital = {
        "CNPJ_CIA": "11.111.111/0001-11",
        "DT_REFER": "2025-12-31",
        "VERSAO": "1",
        "QT_ACAO_ORDIN_CAP_INTEGR": "1000",
        "QT_ACAO_PREF_CAP_INTEGR": "0",
        "QT_ACAO_ORDIN_TESOURO": "0",
        "QT_ACAO_PREF_TESOURO": "0",
        "QT_ACAO_TOTAL_TESOURO": "0",
    }
    sem_on = {k: v for k, v in linha_capital.items() if k != "QT_ACAO_ORDIN_CAP_INTEGR"}
    resultados["composicao_sem_coluna_on"] = repr(
        composicao_do_documento(
            pd.DataFrame([sem_on]), "11.111.111/0001-11", "2025-12-31", "1"
        )
    )
    linhas_lpa = pd.DataFrame(
        [
            {"CD_CONTA": "3.99.01.01", "DS_CONTA": "ON", "VL_CONTA": float("nan")},
            {"CD_CONTA": "3.99.01.01", "DS_CONTA": "ON", "VL_CONTA": 1.0},
        ]
    )
    resultados["lpa_invalido_com_linha_valida"] = repr(
        acoes_cvm.divulgados_coerentes(
            lpa_basico_por_classe(linhas_lpa), 1000.0, 1000.0
        )
    )
    cc = acoes_cvm.Composicao(1000, 0, 0, 0, 0, "2025-12-31", "1")
    parametros = {
        "lucro_controladores": 1000.0,
        "pl_controladores": 10000.0,
        "composicao": cc,
        "motivo_composicao": None,
        "lpa_divulgado": 1.0,
        "preco": 10.0,
        "eh_unit": False,
        "acoes_por_unit": None,
    }
    resultados["preco_infinito_por_acao"] = repr(
        acoes_cvm.derivar_por_acao(**{**parametros, "preco": float("inf")})
    )
    resultados["unit_quantidade_fracionaria"] = repr(
        acoes_cvm.derivar_por_acao(
            **{**parametros, "eh_unit": True, "acoes_por_unit": {"ON": 0.5, "PN": 1}}
        )
    )
    resultados["roe_insumos_invalidos"] = {
        "lucro_nan": repr(acoes_cvm.roe_dos_controladores(float("nan"), 10.0)),
        "pl_infinito": repr(acoes_cvm.roe_dos_controladores(10.0, float("inf"))),
    }
    resultados["dominio_perdas"] = {
        "escala_prejuizo": repr(acoes_cvm.inferir_escala(-1000, 1000, -1)),
        "roe_pl_negativo": repr(acoes_cvm.roe_dos_controladores(-100, -1000)),
    }
    resultados["completude_banco_fii"] = {
        "campos_esperados": list(DataQualityReport({}).completude()["campos"]),
        "roe_infinito": DataQualityReport({"roe": float("inf")}).completude()["campos"][
            "roe"
        ],
    }
    campos_qualidade = resultados["completude_banco_fii"]["campos_esperados"]
    resultados["completude_banco_fii"]["banco_sem_tres_campos_inaplicaveis"] = (
        DataQualityReport(
            {
                c: 1
                for c in campos_qualidade
                if c not in ("divida_liq_ebitda", "margem_liquida", "receita_liquida")
            }
        ).completude()["completude_pct"]
    )
    resultados["completude_banco_fii"]["fii_so_preco_dy_pvp"] = DataQualityReport(
        {"preco_atual": 10, "dy": 0.1, "pvp": 1}
    ).completude()["completude_pct"]
    preferenciais = []
    for ticker in ("USIM5", "BRSR5", "BRSR6"):
        registro = next((r for r in indice() if r["ticker"] == ticker), {})
        linhas = capital[capital["CNPJ_CIA"] == registro.get("cnpj")]
        ultimo = linhas.sort_values(["DT_REFER", "VERSAO"]).tail(1)
        publico = RAIZ / f"outputs/dossie_cache/yf_{ticker}.json"
        mercado = json.loads(publico.read_text()) if publico.exists() else {}
        preferenciais.append(
            {
                "ticker": ticker,
                "classe_preferencial": registro.get("classe_preferencial"),
                "classes_preferenciais": registro.get("classes_preferenciais"),
                "capital_documento": ultimo[
                    [
                        "DT_REFER",
                        "VERSAO",
                        "QT_ACAO_PREF_CAP_INTEGR",
                        "QT_ACAO_PREF_TESOURO",
                    ]
                ].to_dict("records"),
                "shares_yfinance": mercado.get("shares"),
                "estado": "quantidades de PN agregadas não identificam PNA/PNB individualmente",
            }
        )
    resultados["preferenciais_yfinance"] = preferenciais
    bpp = csv_zip(arquivo, "BPP_con")
    resultados["submodelos_reais"] = {
        "codigos_pl": bpp[bpp["CD_CONTA"].isin(["2.03", "2.07", "2.08"])]
        .groupby(["CD_CONTA", "DS_CONTA"])["CNPJ_CIA"]
        .nunique()
        .reset_index()
        .to_dict("records"),
        "pares_309_ja_na_tabela_empresa": [
            c.codigo
            for c in contas_cvm.tabela()
            if c.modelo == "empresa" and c.campo == "lucro_controladores"
        ],
        "preposicoes": sorted(
            {
                str(d)
                for d in dre.loc[
                    dre["CD_CONTA"].isin(["3.09.01", "3.11.01", "3.13.01"]), "DS_CONTA"
                ].dropna()
            }
        ),
    }
    # Submodelos: as três leituras dos não controladores e dos controladores, por companhia.
    leituras = []
    registros_indice = indice()
    for modelo in ("banco", "seguradora"):
        cnpjs = {
            r["cnpj"]
            for r in registros_indice
            if r.get("cnpj") and contas_cvm.modelo_do_setor(r.get("setor")) == modelo
        }
        for cnpj in sorted(cnpjs):
            for campo, tabela_campo in (
                ("pl_nao_controladores", bpp),
                ("lucro_nao_controladores", dre),
                ("lucro_controladores", dre),
            ):
                ultimas_linhas = tabela_campo[
                    (tabela_campo["CNPJ_CIA"] == cnpj)
                    & (tabela_campo["ORDEM_EXERC"] == "ÚLTIMO")
                ]
                if ultimas_linhas.empty:
                    continue
                leitura = contas_cvm.ler_conta(
                    ultimas_linhas[["CD_CONTA", "DS_CONTA", "VL_CONTA"]].to_dict(
                        "records"
                    ),
                    campo,
                    modelo,
                    contas_cvm.tabela(),
                )
                leituras.append(
                    {
                        "modelo": modelo,
                        "cnpj": cnpj,
                        "campo": campo,
                        "resultado": "leitura"
                        if isinstance(leitura, contas_cvm.Leitura)
                        else leitura.motivo,
                    }
                )
    resultados["submodelos_leituras"] = (
        pd.DataFrame(leituras)
        .groupby(["modelo", "campo", "resultado"])["cnpj"]
        .nunique()
        .reset_index()
        .to_dict("records")
        if leituras
        else []
    )
    # Dívida líquida: as quatro contas nas companhias com PL consolidado (modelo empresa).
    bpa = csv_zip(arquivo, "BPA_con")
    bpa, bpp_ultimo = (t[t["ORDEM_EXERC"] == "ÚLTIMO"] for t in (bpa, bpp))
    com_pl = set(
        bpp_ultimo[
            (bpp_ultimo["CD_CONTA"] == "2.03")
            & bpp_ultimo["DS_CONTA"].str.contains("Patrim", na=False)
        ]["CNPJ_CIA"]
    )
    resultados["divida_liquida_contas"] = {
        "companhias_com_pl_consolidado": len(com_pl),
        "ausentes_por_conta": {
            codigo: len(com_pl - set(t[t["CD_CONTA"] == codigo]["CNPJ_CIA"]))
            for codigo, t in (
                ("1.01.01", bpa),
                ("1.01.02", bpa),
                ("2.01.04", bpp_ultimo),
                ("2.02.01", bpp_ultimo),
            )
        },
    }
    resultados["arquivo_proveniencia_temporario"] = evidencia_codigo(
        "sentinela/data/proveniencia.py", "registrar_arquivo"
    )
    resultados["evidencias_codigo"] = [
        evidencia_codigo("cvm_provider.py", "composicao_do_documento"),
        evidencia_codigo("cvm_provider.py", "_dados_por_acao"),
        evidencia_codigo("market_engine.py", "_por_acao_cvm"),
        evidencia_codigo("sentinela/data/acoes_cvm.py", "divulgados_coerentes"),
        evidencia_codigo("sentinela/data/series_cvm.py", "proventos"),
        evidencia_codigo("sentinela/data/divida_liquida.py", "medir"),
        evidencia_codigo("sentinela/data/proveniencia.py", "registrar_arquivo"),
    ]
    # Duas gravações chegam à troca de nome depois de escrever no mesmo .tmp.
    # A barreira torna a corrida observável, sem rede ou arquivos de produção.
    with tempfile.TemporaryDirectory(dir=CACHE) as pasta:
        origem = Path(pasta) / "arquivo.zip"
        origem.write_bytes(b"evidencia sintetica")
        barreira = threading.Barrier(2)
        replace_original = Path.replace

        def trocar(caminho: Path, destino: Path) -> Path:
            barreira.wait(timeout=10)
            return replace_original(caminho, destino)

        def gravar() -> str:
            try:
                proveniencia.registrar_arquivo(
                    origem, "fonte pública sintética", "DFP", "2025"
                )
            except (OSError, threading.BrokenBarrierError) as exc:
                return type(exc).__name__
            return "gravado"

        with (
            patch.object(Path, "replace", trocar),
            ThreadPoolExecutor(max_workers=2) as executor,
        ):
            resultados["corrida_temporario"] = list(
                executor.map(lambda _: gravar(), range(2))
            )
    return resultados


SECOES = {
    1: secao1,
    2: secao2,
    3: secao3,
    4: secao4,
    5: secao5,
    6: secao6,
    7: secao7,
    8: secao8,
}


def main() -> None:
    """Executa seções independentes e preserva erros explícitos por seção."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--secao", nargs="+", type=int, choices=SECOES, default=list(SECOES)
    )
    parser.add_argument("--atualizar", action="store_true")
    args = parser.parse_args()
    for secao in args.secao:
        try:
            resultado = SECOES[secao](args.atualizar)
        except (
            OSError,
            ValueError,
            KeyError,
            StopIteration,
            zipfile.BadZipFile,
        ) as exc:
            resultado = {
                "estado": "não determinado",
                "erro": f"{type(exc).__name__}: {exc}",
            }
        salvar(CACHE / f"secao-{secao}.json", resultado)
        print(f"Seção {secao}: {CACHE / f'secao-{secao}.json'}", flush=True)


if __name__ == "__main__":
    main()
