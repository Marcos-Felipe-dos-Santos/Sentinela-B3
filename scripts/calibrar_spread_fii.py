"""Calibração do spread dos FIIs de tijolo sobre a NTN-B (F2B-2; ficha FII 1.1, §6).

Regras do plano final da 2B (`docs/decisoes/plano-final-2b.md`, seção 3), com a observação
de cada mês igual à da lente em produção num as_of no dia seguinte ao último pregão do mês:

- população: todos os FIIs do Informe Mensal ligados a um ticker do mercado à vista pelo
  ISIN do `geral` igual ao do COTAHIST; os sem ligação ficam fora e são contados;
- fundo-mês válido: `rendimento_fii.avaliar` com o as_of do dia seguinte ao último pregão do
  mês (linhas entregues até o pregão, Informe de até 3 meses, guardas da ficha, tijolo pela
  composição do mês final, sem desdobramento ou grupamento oficial da B3 na janela; B3 sem
  resposta válida exclui o fundo-mês), mais a liquidez do F2A-10 (presença ≥ 80% e volume
  mediano ≥ R$ 100 mil nos 63 pregões até o último pregão do mês, por
  `liquidez.metricas`);
- diferença do fundo-mês: DY de 12 meses (rendimento ÷ fechamento bruto do COTAHIST no último
  pregão em que o ticker negociou até o fim do mês) − média da taxa de aplicação da NTN-B
  (cesta da taxa real: NTN-B e NTN-B Principal a partir de 2035, pesos iguais) da última
  data-base até o último pregão;
- spread: `spread_fii.calibrar`, mediana das 60 medianas mensais.

Lê só os arquivos do levantamento do F2B-21 (Informes, COTAHIST anuais e histórico do
Tesouro, com os hashes no registro) e consulta a B3 uma vez por fundo candidato, guardando a
resposta. Grava o resultado em JSON. Uso:

    python scripts/calibrar_spread_fii.py --mes-final 2026-09 --saida outputs/f2b2_spread.json
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import sys
import time
import zipfile
from collections import Counter, defaultdict
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

from sentinela.data import liquidez, rendimento_fii, spread_fii
from sentinela.data.providers import b3_fundos
from sentinela.data.providers.b3_cotahist import Cotacao, parsear_linha
from sentinela.data.providers.tesouro import ler_csv, selecionar_ofertas

CACHE = RAIZ / "outputs" / "levantamento_cache" / "f2b21"
PRESENCA_MIN = 0.80
VOLUME_MIN = 100_000.0
JANELA_LIQUIDEZ = 63
PREGAO = "__PREGAO__"


def _csv(zip_path: Path, parte: str) -> pd.DataFrame:
    with zipfile.ZipFile(zip_path) as z:
        nome = next(n for n in z.namelist() if parte in n)
        with z.open(nome) as f:
            return pd.read_csv(
                io.TextIOWrapper(f, encoding="latin-1"), sep=";", dtype=str
            )


def carregar_informes(anos: range) -> tuple[dict, dict, dict]:
    """Por CNPJ: linhas do complemento (com entrega e ISIN do geral), composições e ISINs."""
    registros: dict[str, list[dict]] = defaultdict(list)
    composicoes: dict[str, list[dict]] = defaultdict(list)
    isins: dict[str, set[str]] = defaultdict(set)
    for ano in anos:
        caminho = CACHE / f"fii_anual_{ano}.resposta"
        comp = _csv(caminho, "complemento").rename(
            columns={"CNPJ_Fundo": "CNPJ_Fundo_Classe"}
        )
        geral = _csv(caminho, "geral").rename(
            columns={"CNPJ_Fundo": "CNPJ_Fundo_Classe"}
        )
        ativo = _csv(caminho, "ativo_passivo").rename(
            columns={"CNPJ_Fundo": "CNPJ_Fundo_Classe"}
        )
        entregas = {
            (r["CNPJ_Fundo_Classe"], r["Data_Referencia"], r["Versao"]): r
            for r in geral[
                [
                    "CNPJ_Fundo_Classe",
                    "Data_Referencia",
                    "Versao",
                    "Data_Entrega",
                    "Codigo_ISIN",
                ]
            ].to_dict("records")
        }
        for linha in comp.to_dict("records"):
            par = entregas.get(
                (linha["CNPJ_Fundo_Classe"], linha["Data_Referencia"], linha["Versao"])
            )
            if par:
                linha["Data_Entrega"] = par["Data_Entrega"]
                linha["Codigo_ISIN"] = par["Codigo_ISIN"]
                if isinstance(par["Codigo_ISIN"], str) and par["Codigo_ISIN"].strip():
                    isins[linha["CNPJ_Fundo_Classe"]].add(par["Codigo_ISIN"].strip())
            registros[linha["CNPJ_Fundo_Classe"]].append(linha)
        for linha in ativo.to_dict("records"):
            composicoes[linha["CNPJ_Fundo_Classe"]].append(linha)
    return registros, composicoes, isins


def carregar_cotahist(anos: range) -> tuple[list[date], dict, dict]:
    """Pregões do mercado à vista, cotações dos FIIs (CODBDI 12) por ticker e ISIN → tickers."""
    pregoes: set[date] = set()
    por_ticker: dict[str, list[Cotacao]] = defaultdict(list)
    tickers_do_isin: dict[str, set[str]] = defaultdict(set)
    for ano in anos:
        with (
            zipfile.ZipFile(CACHE / f"cotahist_anual_{ano}.resposta") as z,
            z.open(z.namelist()[0]) as linhas,
        ):
            for bruta in linhas:
                if bruta[:2] != b"01" or bruta[24:27] != b"010":
                    continue
                pregoes.add(date(int(bruta[2:6]), int(bruta[6:8]), int(bruta[8:10])))
                if bruta[10:12] != b"12":
                    continue
                cotacao = parsear_linha(bruta.decode("latin-1"))
                por_ticker[cotacao.codigo_negociacao].append(cotacao)
                tickers_do_isin[cotacao.isin].add(cotacao.codigo_negociacao)
    return sorted(pregoes), por_ticker, tickers_do_isin


def carregar_tesouro() -> list:
    texto = (CACHE / "tesouro_historico.resposta").read_text(encoding="latin-1")
    return list(ler_csv(texto, as_of=date(2100, 1, 1), validar_aplicacao=False))


def ntnb_ate(titulos: list, dia: date) -> tuple[float | None, str | None]:
    """Média da taxa de aplicação da cesta da última data-base até o dia (inclusive)."""
    cesta = selecionar_ofertas(tuple(t for t in titulos if t.data_base <= dia))
    if cesta.motivo or not cesta.titulos:
        return None, cesta.motivo
    valores = [t.taxa_aplicacao.valor for t in cesta.titulos]
    return sum(valores) / len(valores), cesta.data_base.isoformat()


def resposta_b3(cnpj: str, ticker: str, pasta: Path) -> dict:
    """Resposta da B3 do fundo, do arquivo guardado ou consultada uma vez."""
    pasta.mkdir(parents=True, exist_ok=True)
    arquivo = (
        pasta
        / f"{ticker[:4]}_{cnpj.replace('/', '').replace('.', '').replace('-', '')}.json"
    )
    if arquivo.exists():
        return json.loads(arquivo.read_text())
    try:
        coleta = b3_fundos.coletar(cnpj, ticker, datetime.now(UTC))
    except Exception as erro:  # noqa: BLE001 — falha da fonte vira "indisponível"
        coleta = {"resposta": None, "erro": f"{type(erro).__name__}: {erro}"}
    arquivo.write_text(json.dumps(coleta, ensure_ascii=False))
    time.sleep(0.3)
    return coleta


def liquidez_ate(cotacoes: list[Cotacao], pregoes_janela: list[date], ticker: str):
    marcadores = [
        Cotacao(d, PREGAO, "", "010", "", "", 0.0, 0.0, 0, 0, 1) for d in pregoes_janela
    ]
    fim = pregoes_janela[-1]
    inicio = pregoes_janela[0]
    do_ticker = [c for c in cotacoes if inicio <= c.data <= fim]
    return liquidez.metricas(
        [*marcadores, *do_ticker], ticker, janelas=(JANELA_LIQUIDEZ,)
    )


def main() -> None:
    argumentos = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    argumentos.add_argument("--mes-final", required=True)
    argumentos.add_argument("--saida", type=Path, required=True)
    argumentos.add_argument(
        "--b3", type=Path, default=RAIZ / "outputs" / "f2b2_b3_fundos"
    )
    opcoes = argumentos.parse_args()
    meses = spread_fii.janela(opcoes.mes_final)
    primeiro = date(int(meses[0][:4]), int(meses[0][5:]), 1)
    ultimo_ano = int(opcoes.mes_final[:4])
    registros, composicoes, isins = carregar_informes(
        range(primeiro.year - 2, ultimo_ano + 1)
    )
    pregoes, por_ticker, tickers_do_isin = carregar_cotahist(
        range(primeiro.year - 1, ultimo_ano + 1)
    )
    titulos = carregar_tesouro()

    ligacao, sem_ligacao, ambiguos = {}, [], []
    for cnpj, conjunto in isins.items():
        tickers = set().union(*(tickers_do_isin.get(i, set()) for i in conjunto))
        tickers = {t for t in tickers if t.endswith("11")}
        if len(tickers) == 1:
            ligacao[cnpj] = (tickers.pop(), max(conjunto))
        elif tickers:
            ambiguos.append(cnpj)
        else:
            sem_ligacao.append(cnpj)
    fundos_sem_isin = sorted(set(registros) - set(isins))

    por_mes: dict[str, list[float]] = {}
    exclusoes: dict[str, Counter] = {}
    taxas: dict[str, dict] = {}
    for mes in meses:
        ano, m = int(mes[:4]), int(mes[5:])
        do_mes = [p for p in pregoes if p.year == ano and p.month == m]
        fim = do_mes[-1]
        janela_liq = [p for p in pregoes if p <= fim][-JANELA_LIQUIDEZ:]
        y, base = ntnb_ate(titulos, fim)
        taxas[mes] = {"ultimo_pregao": fim.isoformat(), "ntnb": y, "data_base": base}
        contagem: Counter = Counter()
        diferencas = []
        for cnpj, (ticker, isin) in ligacao.items():
            cotacoes = por_ticker.get(ticker, [])
            negociou = [
                c for c in cotacoes if c.data <= fim and c.data >= janela_liq[0]
            ]
            if not negociou:
                contagem["sem negócio na janela de liquidez"] += 1
                continue
            preco = max(negociou, key=lambda c: c.data).fechamento
            dia = fim + timedelta(days=1)
            avaliado = rendimento_fii.avaliar(
                registros[cnpj],
                composicoes.get(cnpj, []),
                b3={
                    "code": ticker[:4],
                    "fund": "pendente",
                    "cashDividends": [],
                    "stockDividends": [],
                },
                codigo=ticker[:4],
                isin=isin,
                preco=preco,
                dia_as_of=dia,
            )
            if isinstance(avaliado, rendimento_fii.Abstencao):
                contagem[avaliado.motivo.split(":")[0]] += 1
                continue
            medida = liquidez_ate(cotacoes, janela_liq, ticker)
            if isinstance(medida, liquidez.Abstencao):
                contagem["liquidez não medida"] += 1
                continue
            j = medida["janelas"][str(JANELA_LIQUIDEZ)]
            if j["presenca"] < PRESENCA_MIN or j["volume_mediano"] < VOLUME_MIN:
                contagem["liquidez abaixo do mínimo"] += 1
                continue
            coleta = resposta_b3(cnpj, ticker, opcoes.b3)
            avaliado = rendimento_fii.avaliar(
                registros[cnpj],
                composicoes.get(cnpj, []),
                b3=coleta.get("resposta"),
                codigo=ticker[:4],
                isin=isin,
                preco=preco,
                dia_as_of=dia,
            )
            if isinstance(avaliado, rendimento_fii.Abstencao):
                contagem[avaliado.motivo.split(" (")[0].split(":")[0]] += 1
                continue
            if y is None:
                contagem["NTN-B indisponível"] += 1
                continue
            contagem["válido"] += 1
            diferencas.append(avaliado["dy"] - y)
        por_mes[mes] = diferencas
        exclusoes[mes] = contagem
        print(mes, fim, f"y={y}", dict(contagem), flush=True)

    resultado = spread_fii.calibrar(por_mes, opcoes.mes_final)
    saida = {
        "gerado_em": datetime.now(UTC).isoformat(),
        "mes_final": opcoes.mes_final,
        "regras": __doc__,
        "populacao": {
            "fundos_no_informe": len(registros),
            "fundos_sem_isin": len(fundos_sem_isin),
            "fundos_sem_ticker_no_cotahist": len(sem_ligacao),
            "fundos_com_isin_ambiguo": len(ambiguos),
            "fundos_ligados": len(ligacao),
        },
        "taxas": taxas,
        "exclusoes": {m: dict(c) for m, c in exclusoes.items()},
        "diferencas": por_mes,
        "fontes": {
            p.name: hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(CACHE.glob("*.resposta"))
            if p.name.startswith(("fii_anual_", "cotahist_anual_", "tesouro_historico"))
        },
    }
    if isinstance(resultado, spread_fii.Abstencao):
        saida["abstencao"] = resultado.motivo
    else:
        saida["calibracao"] = {
            "spread": resultado.spread,
            "mes_inicial": resultado.mes_inicial,
            "mes_final": resultado.mes_final,
            "fundos_por_mes": resultado.fundos_por_mes,
            "p25": resultado.p25,
            "p75": resultado.p75,
            "medianas": resultado.medianas,
        }
    opcoes.saida.write_text(
        json.dumps(saida, ensure_ascii=False, indent=1, default=str)
    )
    print(
        json.dumps(saida.get("calibracao", saida.get("abstencao")), default=str)[:2000]
    )


if __name__ == "__main__":
    main()
