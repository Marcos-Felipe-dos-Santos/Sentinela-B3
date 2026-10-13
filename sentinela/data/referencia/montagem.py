"""Montagem do índice ticker → registro a partir dos arquivos oficiais (F2A-1).

Funções puras sobre DataFrames e cotações já lidos: sem rede, sem banco, sem relógio.
Fontes: FCA (CVM), cadastro de companhias abertas (CVM), Informe Mensal de FII (CVM) e
COTAHIST (B3). A classe nunca vem do sufixo do ticker.
"""

from __future__ import annotations

import logging
import re
from collections.abc import Iterable

import pandas as pd

from sentinela.data.providers.b3_cotahist import Cotacao
from sentinela.data.referencia.correcoes import Correcao, validar_correcoes
from sentinela.data.referencia.registro import Excecao, Indice, Registro
from sentinela.domain.enums import AssetType

logger = logging.getLogger(__name__)
FORMATO_TICKER = re.compile(r"^[A-Z][A-Z0-9]{3}\d{1,2}$")
_ESPECIE_DO_VALOR = {"Ações Ordinárias": "ON", "Ações Preferenciais": "PN"}
_VALOR_UNIT = "Units"
_MERCADOS_FCA = ("Bolsa", "Balcão Organizado")
_CODBDI_BDR = ("34", "35", "36")
_ESPECIE_NO_TEXTO = (
    (re.compile(r"^(ON|ORDIN[ÁA]RIAS?|A[ÇC][ÃA]O ORDIN[ÁA]RIA|A[ÇC][ÕO]ES ORDIN[ÁA]RIAS)$"), "ON"),
    (re.compile(r"^(PN[A-Z]?S?|PREFERENCIAIS?|A[ÇC][ÃA]O PREFERENCIAL|A[ÇC][ÕO]ES PREFERENCIAIS)$"), "PN"),
)  # fmt: skip
_PARTES_UNIT = re.compile(r"\s*(?:\+|/|;|,|\be\b)\s*", re.IGNORECASE)
_QTD_ESPECIE = re.compile(r"^(\d+)\s*(.+)$")
_CODIGO_ESPECIE = re.compile(r"^[A-Z0-9]{4}([3-8])$")


def normalizar_codigo(valor) -> str:
    if valor is None or (not isinstance(valor, str) and pd.isna(valor)):
        return ""
    return str(valor).strip().upper()


def _especie_do_texto(texto: str) -> str | None:
    limpo = texto.strip().upper()
    for padrao, especie in _ESPECIE_NO_TEXTO:
        if padrao.match(limpo):
            return especie
    codigo = _CODIGO_ESPECIE.match(limpo)
    if codigo:
        return "ON" if codigo.group(1) == "3" else "PN"
    return None


def parsear_acoes_por_unit(texto) -> dict | None:
    """Texto livre do FCA ("1 ON / 2 PN") → {"ON": 1, "PN": 2}; `None` se não reconhece tudo."""
    bruto = normalizar_codigo(texto)
    if not bruto:
        return None
    composicao: dict[str, int] = {}
    for parte in _PARTES_UNIT.split(bruto):
        achado = _QTD_ESPECIE.match(parte.strip())
        if not achado:
            return None
        especie = _especie_do_texto(achado.group(2))
        if especie is None:
            return None
        composicao[especie] = composicao.get(especie, 0) + int(achado.group(1))
    return composicao


def fca_mais_recente(fcas: Iterable[tuple[int, pd.DataFrame]]) -> pd.DataFrame:
    """Para cada CNPJ, as linhas do FCA mais recente entregue (ano, referência, versão)."""
    partes = [df.assign(_ano=ano) for ano, df in fcas if len(df)]
    if not partes:
        return pd.DataFrame()
    todas = pd.concat(partes, ignore_index=True)
    todas["_referencia"] = todas["Data_Referencia"].fillna("")
    todas["_versao"] = pd.to_numeric(todas["Versao"], errors="coerce").fillna(0)
    chave = ["_ano", "_referencia", "_versao"]
    melhor = todas.sort_values(chave).groupby("CNPJ_Companhia")[chave].last()
    juntas = todas.merge(
        melhor, left_on="CNPJ_Companhia", right_index=True, suffixes=("", "_max")
    )
    iguais = (juntas[chave].values == juntas[[c + "_max" for c in chave]].values).all(
        axis=1
    )
    return (
        juntas[iguais][todas.columns].drop(columns="_referencia").reset_index(drop=True)
    )


def _texto(valor) -> str | None:
    """Texto sem espaços nas pontas; vazio ou ausente (NaN do CSV) vira `None`."""
    if not isinstance(valor, str):
        return None
    return valor.strip() or None


def _linhas_oficiais(cadastro: pd.DataFrame) -> dict[str, pd.Series]:
    """CNPJ → linha do cadastro com CD_CVM; registro ativo primeiro (regra `cd_oficial` do dossiê)."""
    ativo = cadastro["SIT"].fillna("").str.upper().str.strip().eq("ATIVO").astype(int)
    ordenado = cadastro.assign(_ativo=ativo).sort_values(
        "_ativo", ascending=False, kind="stable"
    )
    resultado: dict[str, pd.Series] = {}
    for _, linha in ordenado.iterrows():
        cnpj = linha["CNPJ_CIA"]
        if cnpj not in resultado and pd.notna(linha["CD_CVM"]):
            resultado[cnpj] = linha
    return resultado


def cd_cvm_por_cnpj(cadastro: pd.DataFrame) -> dict[str, tuple[int, str | None]]:
    """CNPJ → (CD_CVM, nome); registro ativo primeiro (regra `cd_oficial` do dossiê)."""
    return {
        cnpj: (
            int(linha["CD_CVM"]),
            linha["DENOM_SOCIAL"] if pd.notna(linha["DENOM_SOCIAL"]) else None,
        )
        for cnpj, linha in _linhas_oficiais(cadastro).items()
    }


def atributos_por_cnpj(
    cadastro: pd.DataFrame,
) -> dict[str, tuple[str | None, str | None]]:
    """CNPJ → (setor, espécie de controle acionário), da mesma linha que dá o CD_CVM.

    Colunas `SETOR_ATIV` e `CONTROLE_ACIONARIO` do cadastro de companhias abertas (F2A-2).
    """
    return {
        cnpj: (_texto(linha.get("SETOR_ATIV")), _texto(linha.get("CONTROLE_ACIONARIO")))
        for cnpj, linha in _linhas_oficiais(cadastro).items()
    }


def linhas_ativas_do_fca(fca: pd.DataFrame) -> pd.DataFrame:
    """Ações e units em mercado organizado, sem data de fim de negociação."""
    if fca.empty:
        return fca
    limpo = fca.assign(
        Valor_Mobiliario=fca["Valor_Mobiliario"].str.strip(),
        Mercado=fca["Mercado"].str.strip(),
    )
    return limpo[
        limpo["Valor_Mobiliario"].isin([*_ESPECIE_DO_VALOR, _VALOR_UNIT])
        & limpo["Data_Fim_Negociacao"].isna()
        & limpo["Mercado"].isin(_MERCADOS_FCA)
    ]


def classes_preferenciais_por_cnpj(ativas: pd.DataFrame) -> dict[str, list[str]]:
    """CNPJ → siglas das classes do FCA (`Sigla_Classe_Acao_Preferencial`), em ordem alfabética.

    Fonte das classes preferenciais (PNA, PNB…) da D19, regra 3 (F2A-36).
    """
    if "Sigla_Classe_Acao_Preferencial" not in ativas.columns:
        return {}
    resultado: dict[str, list[str]] = {}
    for cnpj, sigla in zip(
        ativas["CNPJ_Companhia"], ativas["Sigla_Classe_Acao_Preferencial"]
    ):
        texto = _texto(sigla)
        if texto and texto.upper() not in resultado.setdefault(cnpj, []):
            resultado[cnpj].append(texto.upper())
    return {cnpj: sorted(siglas) for cnpj, siglas in resultado.items() if siglas}


def montar_companhias(
    fca: pd.DataFrame,
    cadastro: pd.DataFrame,
    fonte_por_ano: dict,
    correcoes: dict[tuple[str, str], Correcao] | None = None,
) -> tuple[list[Registro], list[Excecao]]:
    correcoes = correcoes or {}
    cadastro_por_cnpj = cd_cvm_por_cnpj(cadastro)
    atributos = atributos_por_cnpj(cadastro)
    registros: list[Registro] = []
    excecoes: list[Excecao] = []
    ativas = linhas_ativas_do_fca(fca)
    classes = classes_preferenciais_por_cnpj(ativas)
    for _, linha in ativas.iterrows():
        codigo = normalizar_codigo(linha["Codigo_Negociacao"])
        cnpj = linha["CNPJ_Companhia"]
        nome = (
            linha["Nome_Empresarial"] if pd.notna(linha["Nome_Empresarial"]) else None
        )
        correcao = correcoes.get((cnpj, codigo))
        if correcao is not None:
            codigo = correcao.ticker
        if not codigo:
            excecoes.append(Excecao(codigo, "sem código de negociação", cnpj, nome))
            continue
        if not FORMATO_TICKER.match(codigo):
            excecoes.append(
                Excecao(codigo, "código fora do formato de ticker", cnpj, nome)
            )
            continue
        cd_cvm, nome_cadastro = cadastro_por_cnpj.get(cnpj, (None, None))
        setor, controle = atributos.get(cnpj, (None, None))
        eh_unit = linha["Valor_Mobiliario"] == _VALOR_UNIT
        registros.append(
            Registro(
                ticker=codigo,
                classe=(AssetType.UNIT if eh_unit else AssetType.STOCK).value,
                regra=REGRA_CORRECAO if correcao else "fca:codigo_ativo",
                fonte=fonte_por_ano[str(linha["_ano"])],
                especie=None
                if eh_unit
                else _ESPECIE_DO_VALOR[linha["Valor_Mobiliario"]],
                cnpj=cnpj,
                cd_cvm=cd_cvm,
                nome=nome_cadastro or nome,
                acoes_por_unit=parsear_acoes_por_unit(linha["Composicao_BDR_Unit"])
                if eh_unit
                else None,
                setor=setor,
                controle_acionario=controle,
                correcao=correcao.para_dict() if correcao else None,
                classe_preferencial=None
                if eh_unit
                else _texto(linha.get("Sigla_Classe_Acao_Preferencial")),
                classes_preferenciais=classes.get(cnpj),
            )
        )
    return registros, excecoes


def _isin_para_ticker(cotacoes: Iterable[Cotacao]) -> dict[str, str]:
    """ISIN → ticker: vale o código de fundo imobiliário (`CODBDI` 12) e, entre iguais, o mais recente."""
    melhor: dict[str, tuple[bool, object]] = {}
    mapa: dict[str, str] = {}
    for c in cotacoes:
        if not c.isin:
            continue
        chave = (c.codbdi == "12", c.data)
        if c.isin not in melhor or chave > melhor[c.isin]:
            melhor[c.isin] = chave
            mapa[c.isin] = c.codigo_negociacao
    return mapa


MESES_DE_TOLERANCIA_DO_INFORME = 6


def informe_mais_recente(informe: pd.DataFrame) -> pd.DataFrame:
    """Último informe de cada fundo; some quem não informa há mais de 6 meses (fundo extinto).

    O prazo é medido contra o informe mais novo do próprio arquivo, sem ler relógio.
    """
    if informe.empty:
        return informe
    versao = pd.to_numeric(informe["Versao"], errors="coerce").fillna(0)
    ordenado = informe.assign(_versao=versao).sort_values(
        ["Data_Referencia", "_versao"]
    )
    recentes = ordenado.drop_duplicates("CNPJ_Fundo_Classe", keep="last").drop(
        columns="_versao"
    )
    datas = pd.to_datetime(recentes["Data_Referencia"], errors="coerce")
    if datas.isna().all():
        logger.warning(
            "Informe Mensal sem nenhuma data de referência válida; nenhum FII entra"
        )
        return recentes.iloc[0:0]
    corte = datas.max() - pd.DateOffset(months=MESES_DE_TOLERANCIA_DO_INFORME)
    return recentes[datas >= corte]


def fiis_em_bolsa(informe: pd.DataFrame) -> pd.DataFrame:
    recente = informe_mais_recente(informe)
    if recente.empty:
        return recente
    return recente[recente["Mercado_Negociacao_Bolsa"].fillna("").str.strip() == "S"]


def montar_fiis(
    informe: pd.DataFrame,
    cotacoes: Iterable[Cotacao],
    fonte: dict,
    correcoes: dict[tuple[str, str], Correcao] | None = None,
) -> tuple[list[Registro], list[Excecao]]:
    """Junção do Informe Mensal com o COTAHIST pelo ISIN; reserva: letras 3 a 6 do ISIN + "11".

    A tabela de correções, chaveada por (CNPJ, ISIN), vale antes das duas.
    """
    correcoes = correcoes or {}
    por_isin = _isin_para_ticker(cotacoes)
    registros: list[Registro] = []
    excecoes: list[Excecao] = []
    for _, linha in fiis_em_bolsa(informe).iterrows():
        isin = normalizar_codigo(linha["Codigo_ISIN"])
        cnpj = linha["CNPJ_Fundo_Classe"]
        nome = (
            linha["Nome_Fundo_Classe"] if pd.notna(linha["Nome_Fundo_Classe"]) else None
        )
        if len(isin) != 12:
            excecoes.append(Excecao(isin, "FII em bolsa sem ISIN válido", cnpj, nome))
            continue
        correcao = correcoes.get((cnpj, isin))
        if correcao is not None:
            ticker, regra = correcao.ticker, REGRA_CORRECAO
        elif isin in por_isin:
            ticker, regra = por_isin[isin], "fii:informe+cotahist_isin"
        else:
            ticker, regra = isin[2:6] + "11", "fii:reserva_isin"
        registros.append(
            Registro(
                ticker=ticker,
                classe=AssetType.FII.value,
                regra=regra,
                fonte=fonte,
                cnpj=cnpj,
                nome=nome,
                segmento=_texto(linha.get("Segmento_Atuacao")),
                correcao=correcao.para_dict() if correcao else None,
            )
        )
    return registros, excecoes


def montar_outros(
    cotacoes: Iterable[Cotacao],
    conhecidos: set[str],
    fonte: dict,
    isins_de_fii: frozenset[str] = frozenset(),
) -> list[Registro]:
    """BDR pelo `CODBDI` e `ESPECI` do COTAHIST; cota de fundo fora do Informe vira UNKNOWN.

    Um código antigo de FII do Informe (mesmo ISIN, outro ticker) não vira `UNKNOWN`.
    """
    registros: dict[str, Registro] = {}
    for c in cotacoes:
        codigo = c.codigo_negociacao
        if codigo in conhecidos or codigo in registros or c.isin in isins_de_fii:
            continue
        if c.codbdi in _CODBDI_BDR and c.especificacao.startswith("DR"):
            registros[codigo] = Registro(
                ticker=codigo,
                classe=AssetType.BDR.value,
                regra="cotahist:bdr",
                fonte=fonte,
            )
        elif c.especificacao.startswith("CI"):
            registros[codigo] = Registro(
                ticker=codigo,
                classe=AssetType.UNKNOWN.value,
                regra="cotahist:cota_de_fundo",
                fonte=fonte,
                motivo="cota de fundo listada que não é FII do Informe Mensal nem ETF identificado",
            )
    return list(registros.values())


REGRA_CORRECAO = "correcao"
_PRECEDENCIA = {
    REGRA_CORRECAO: -1,
    "fca:codigo_ativo": 0,
    "fii:informe+cotahist_isin": 1,
    "fii:reserva_isin": 2,
}
MOTIVO_REPETIDO = "ticker repetido em CNPJs distintos"
MOTIVO_RESERVA = "reserva do ISIN colide com ticker de fonte mais forte"
MOTIVO_COMPANHIA = "ticker de FII colide com ticker de companhia do FCA"
MOTIVO_CORRECAO = "ticker ligado a outro CNPJ pela tabela de correções"


def _motivo_do_perdedor(registro: Registro, vencedor: Registro) -> str:
    if vencedor.regra == REGRA_CORRECAO:
        return MOTIVO_CORRECAO
    return MOTIVO_RESERVA if registro.regra == "fii:reserva_isin" else MOTIVO_COMPANHIA


def _resolver_repetidos(
    registros: list[Registro],
) -> tuple[dict[str, Registro], list[Excecao]]:
    """Mesmo ticker em CNPJs distintos: vale a fonte de maior precedência, se só uma tiver o menor posto."""
    por_ticker: dict[str, list[Registro]] = {}
    for registro in registros:
        por_ticker.setdefault(registro.ticker, []).append(registro)
    mantidos: dict[str, Registro] = {}
    excecoes: list[Excecao] = []
    for ticker, grupo in por_ticker.items():
        if len({r.cnpj for r in grupo}) == 1:
            mantidos[ticker] = grupo[0]
            continue
        melhor = min(_PRECEDENCIA[r.regra] for r in grupo)
        vencedores = [r for r in grupo if _PRECEDENCIA[r.regra] == melhor]
        if len({r.cnpj for r in vencedores}) == 1:
            mantidos[ticker] = vencedores[0]
            perdedores = [r for r in grupo if r.cnpj != vencedores[0].cnpj]
            excecoes += [
                Excecao(ticker, _motivo_do_perdedor(r, vencedores[0]), r.cnpj, r.nome)
                for r in perdedores
            ]
        else:
            excecoes += [
                Excecao(ticker, MOTIVO_REPETIDO, r.cnpj, r.nome) for r in grupo
            ]
    return mantidos, excecoes


def montar_indice(
    fcas: Iterable[tuple[int, pd.DataFrame]],
    cadastro: pd.DataFrame,
    informe: pd.DataFrame,
    cotacoes: Iterable[Cotacao],
    fontes: dict,
    gerado_em: str,
    correcoes: Iterable[Correcao] = (),
) -> Indice:
    """Junta companhias, FIIs e outros; em ticker repetido entre CNPJs, vale a fonte mais forte.

    A tabela de correções é validada aqui: linha sem evidência levanta `CorrecaoInvalida`.
    """
    por_chave = validar_correcoes(correcoes)
    cotacoes = list(cotacoes)
    fca = fca_mais_recente(fcas)
    companhias, exc_companhias = montar_companhias(
        fca, cadastro, fontes["fca"], por_chave
    )
    fiis, exc_fiis = montar_fiis(informe, cotacoes, fontes["informe_fii"], por_chave)
    mantidos, exc_repetidos = _resolver_repetidos([*companhias, *fiis])
    indice = Indice(
        gerado_em=gerado_em,
        fontes=fontes,
        registros=mantidos,
        excecoes=[*exc_companhias, *exc_fiis, *exc_repetidos],
    )
    conhecidos = set(mantidos) | {e.codigo for e in exc_repetidos}
    isins_de_fii = frozenset(
        normalizar_codigo(i) for i in fiis_em_bolsa(informe)["Codigo_ISIN"]
    )
    for registro in montar_outros(
        cotacoes, conhecidos, fontes["cotahist"], isins_de_fii
    ):
        indice.registros[registro.ticker] = registro
    return indice
