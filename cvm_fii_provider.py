"""Provider de dados de FIIs a partir do Informe Mensal CVM.

Schema verificado contra inf_mensal_fii_*_2024.csv (CVM, 2024-06):
  complemento : CNPJ_Fundo_Classe, Data_Referencia, Patrimonio_Liquido,
                Cotas_Emitidas, Valor_Patrimonial_Cotas, Percentual_Dividend_Yield_Mes
  geral        : CNPJ_Fundo_Classe, Quantidade_Cotas_Emitidas, Segmento_Atuacao

Observação: vacância física NÃO está disponível no informe mensal.
"""
import json
import logging
import math
import zipfile
from collections import defaultdict
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd

from cvm_download import baixar_arquivo
from sentinela.data import proveniencia, rendimento_fii
from sentinela.data.cache_leitura import ler_csv_zip
from sentinela.data.pit import leitura

logger = logging.getLogger(__name__)

_INF_URL = (
    "https://dados.cvm.gov.br/dados/FII/DOC/INF_MENSAL/DADOS/"
    "inf_mensal_fii_{ano}.zip"
)


MOTIVO_DATA_ILEGIVEL = "Informe Mensal com Data_Referencia ilegível"


def _data_iso(value) -> bool:
    try:
        date.fromisoformat(str(value)[:10])
    except ValueError:
        return False
    return True


def _ler_informe(zip_path: Path, membro: str, *, literal: bool = False) -> pd.DataFrame:
    """Um CSV do Informe, com o CNPJ do fundo em `CNPJ_Fundo_Classe` nos dois leiautes.

    BUG-3-42: os anos de 2016 a 2020 vêm no leiaute anterior à Resolução 175, com a coluna
    `CNPJ_Fundo` (a carga do BUG-3-25 os grava assim, e a remontagem devolve o cabeçalho
    original). Só o nome da coluna muda; o arquivo do leiaute novo sai como está.
    """
    df = ler_csv_zip(zip_path, membro, literal=literal)
    if "CNPJ_Fundo_Classe" not in df.columns and "CNPJ_Fundo" in df.columns:
        return df.rename(columns={"CNPJ_Fundo": "CNPJ_Fundo_Classe"})
    return df


def _to_float(value) -> float | None:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    try:
        return float(str(value).replace(",", "."))
    except (ValueError, TypeError):
        return None


class CVMFIIProvider:
    def __init__(self, cache_dir: str = "data/cvm_fii"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Cache de arquivos
    # ------------------------------------------------------------------

    def _cache_path(self, nome: str) -> Path:
        return self.cache_dir / nome

    def baixar_informe(self, ano: int) -> Path:
        """Baixa o ZIP do informe mensal FII do ano e retorna o Path local (cache 7d).

        Grava a proveniência do arquivo ao lado dele (F2A-32).
        """
        caminho = baixar_arquivo(
            _INF_URL.format(ano=ano),
            self._cache_path(f"inf_mensal_fii_{ano}.zip"),
        )
        proveniencia.registrar_sem_falhar(
            caminho, _INF_URL.format(ano=ano), "Informe Mensal", str(ano)
        )
        return caminho

    # ------------------------------------------------------------------
    # Parse
    # ------------------------------------------------------------------

    def _parsear_complemento(
        self, zip_path: Path, ano: int, *, literal: bool = False
    ) -> pd.DataFrame:
        """Lê inf_mensal_fii_complemento_{ano}.csv do ZIP. Retorna DataFrame.

        `literal=True` (F2B-61, ficha FII 1.3): as células chegam como estão no arquivo, sem os
        `na_values` do pandas; a célula vazia fica `""` e o `NaN` declarado fica `"NaN"`.
        """
        target = f"inf_mensal_fii_complemento_{ano}.csv"
        with zipfile.ZipFile(zip_path) as zf:
            names = zf.namelist()
            csv_name = target if target in names else next(
                (n for n in names if "complemento" in n.lower() and n.endswith(".csv")),
                None,
            )
            if csv_name is None:
                logger.warning("Arquivo complemento não encontrado em %s", zip_path.name)
                return pd.DataFrame()
        return _ler_informe(zip_path, csv_name, literal=literal)

    def _proveniencia(self, zip_path: Path, ano: int, row) -> dict | None:
        """Proveniência do informe usado (F2A-32): mês, versão e `Data_Entrega` do `geral`.

        `None` se o arquivo local não é legível.
        """
        if isinstance(row, pd.Series):
            row = row.to_dict()  # Converte escalares do pandas para os tipos do registro.
        try:
            arquivo = proveniencia.registrar_arquivo(
                zip_path, _INF_URL.format(ano=ano), "Informe Mensal", str(ano)
            )
        except OSError:
            return None
        documento = {
            "CNPJ_Fundo_Classe": row.get("CNPJ_Fundo_Classe"),
            "Data_Referencia": row.get("Data_Referencia"),
            "Versao": row.get("Versao"),
        }
        if row.get("_pit_entrega_selecionada") is True:
            # O recorte já conferiu esta entrega; reler o índice perderia a seleção.
            entrega = row.get("Data_Entrega")
        else:
            try:
                geral = _ler_informe(zip_path, f"inf_mensal_fii_geral_{ano}.csv")
                entrega = proveniencia.entrega_no_indice(
                    geral.to_dict("records"), documento, coluna="Data_Entrega"
                )
            except (OSError, KeyError, ValueError, zipfile.BadZipFile):
                entrega = None
        return arquivo.do_documento(
            documento["Data_Referencia"],
            documento["Versao"],
            entrega,
            proveniencia.MOTIVO_DOCUMENTO_FORA_DO_INDICE,
        ).para_dict()

    # ------------------------------------------------------------------
    # API pública
    # ------------------------------------------------------------------

    def _recorte_informe(
        self, zip_path: Path, cnpj: str, registros: list[dict], dia: date
    ) -> tuple[list[dict], dict[str, str], tuple[str, ...]]:
        """Mesma seleção documental do PIT, também para o arquivo aberto direto."""
        with zipfile.ZipFile(zip_path) as zf:
            controle = (
                json.loads(zf.read("sentinela_informe_pit.json"))
                if "sentinela_informe_pit.json" in zf.namelist() else {}
            )
        modo = controle.get("modo", leitura.ESTRITO)
        if modo not in leitura.MODOS:
            raise ValueError(f"modo desconhecido no Informe: {modo}")
        if controle and controle.get("dia") != dia.isoformat():
            raise ValueError("recorte do Informe pertence a outra data")
        motivos = dict(controle.get("motivos", {}).get(cnpj, {}))
        geral: dict[str, dict[str, set]] = defaultdict(lambda: defaultdict(set))
        tabela = self._tabela(zip_path, "geral", literal=True)
        for r in tabela.to_dict("records"):
            if str(r.get("CNPJ_Fundo_Classe", "")).strip() == cnpj:
                geral[str(r.get("Data_Referencia", ""))][str(r.get("Versao", ""))].add(
                    (r.get("Data_Entrega"), r.get("Codigo_ISIN"))
                )
        usadas: dict[tuple[str, str], tuple] = {}
        for ref, versoes in geral.items():
            if not leitura._mes_encerrado(ref, dia):
                continue
            presentes = {str(r.get("Versao", "")) for r in registros if r.get("Data_Referencia") == ref}
            motivo, escolhidas = leitura._versoes_com_numeros(versoes, presentes, dia, modo)
            if motivo:
                motivos[ref] = motivo
            usadas.update({(ref, v): entrega for v, entrega in escolhidas.items()})
        for r in registros:
            ref, versao = str(r.get("Data_Referencia", "")), str(r.get("Versao", ""))
            if leitura._mes_encerrado(ref, dia) and versao not in geral.get(ref, {}):
                motivos[ref] = leitura.MOTIVO_SEM_GERAL
        selecionados = []
        for r in registros:
            ref, versao = str(r.get("Data_Referencia", "")), str(r.get("Versao", ""))
            if ref in motivos or (ref, versao) not in usadas:
                continue
            entrega, isin = usadas[(ref, versao)]
            linha = {**r, "Data_Entrega": entrega, "Codigo_ISIN": isin,
                     "_pit_entrega_selecionada": True}
            if modo == leitura.EXPLORATORIO:
                # Só o leitor temporal pode declarar esta disponibilidade; a entrega fica literal.
                linha["_pit_exploratorio"] = True
                linha["_pit_dia"] = dia.isoformat()
            selecionados.append(linha)
        _, conflitos = rendimento_fii._por_mes(
            selecionados, colunas=(*rendimento_fii._COLUNAS_DA_CONTA, "Patrimonio_Liquido")
        )
        for ano, mes in conflitos:
            motivos[f"{ano:04d}-{mes:02d}-01"] = rendimento_fii.MOTIVO_CONFLITO
        selecionados = [r for r in selecionados if r["Data_Referencia"] not in motivos]
        return selecionados, motivos, leitura._avisos(modo)

    @staticmethod
    def _bloqueio_informe(
        registros: list[dict], motivos: dict[str, str], meses: int
    ) -> str | None:
        """Bloqueio no documento vigente ou nos 13 meses necessários, nunca recuo."""
        referencias = [str(r.get("Data_Referencia", "")) for r in registros] + list(motivos)
        datas = [date.fromisoformat(r[:10]) for r in referencias if _data_iso(r)]
        if not datas:
            return None
        final = max(datas)
        limite = final.year * 12 + final.month - meses
        for ref, motivo in sorted(motivos.items(), reverse=True):
            if _data_iso(ref):
                mes = date.fromisoformat(ref[:10])
                if mes.year * 12 + mes.month >= limite:
                    return motivo
        return None

    def obter_dados_fii(self, cnpj_fundo: str, *, as_of: datetime | None = None) -> dict | None:
        """Retorna os dados mais recentes do fundo, ou None se não encontrado.

        as_of seleciona meses encerrados e versões entregues antes do dia de São Paulo,
        pela mesma regra documental do leitor PIT. Documento vigente bloqueado abstém,
        sem recuo. Recorte exploratório explicitamente rotulado mantém a entrega original.

        Campos no retorno:
          cnpj_fundo, dt_referencia, patrimonio_liquido, cotas_emitidas,
          valor_cota (VPA oficial = PL/cotas),
          vacancia_fisica (sempre None — não disponível no informe mensal),
          proveniencia (F2A-32).

        Com `Data_Referencia` ilegível numa linha do fundo, devolve
        `{"abstencao": MOTIVO_DATA_ILEGIVEL}` (F2B-2, aceite Gemini HEAD60e61e2).
        """
        cnpj = cnpj_fundo.strip()
        if as_of is not None and as_of.utcoffset() is None:
            raise ValueError("as_of exige fuso horário")
        dia = date.today() if as_of is None else as_of.astimezone(ZoneInfo("America/Sao_Paulo")).date()
        ano_atual = dia.year

        for ano in [ano_atual, ano_atual - 1]:
            try:
                avisos: tuple[str, ...] = ()
                if as_of is not None:
                    lido = self._linhas_do_fundo(cnpj, ano)
                    if lido is None:
                        continue
                    zip_path, linhas, _ = lido
                    if any(not _data_iso(r.get("Data_Referencia")) for r in linhas):
                        return {"abstencao": MOTIVO_DATA_ILEGIVEL}
                    linhas, motivos, avisos = self._recorte_informe(zip_path, cnpj, linhas, dia)
                    motivo = self._bloqueio_informe(linhas, motivos, 0)
                    if motivo:
                        return {"abstencao": motivo, "avisos": list(avisos)}
                    df = pd.DataFrame(linhas)
                else:
                    zip_path = self.baixar_informe(ano)
                    df = self._parsear_complemento(zip_path, ano)
                if df.empty or "CNPJ_Fundo_Classe" not in df.columns:
                    continue

                mask = df["CNPJ_Fundo_Classe"].str.strip() == cnpj
                fundo_df = df[mask]
                if fundo_df.empty:
                    continue

                # F2B-2 (aceite Gemini HEAD60e61e2): data de referência ilegível abstém, com
                # motivo; a ordenação a deixaria escolher a linha errada em silêncio.
                if "Data_Referencia" in fundo_df.columns and not all(
                    _data_iso(v) for v in fundo_df["Data_Referencia"]
                ):
                    return {"abstencao": MOTIVO_DATA_ILEGIVEL}

                # Registro mais recente; na mesma data, a reapresentação (maior `Versao`, F2B-38).
                if "Data_Referencia" in fundo_df.columns:
                    chaves = ["Data_Referencia"]
                    if "Versao" in fundo_df.columns:
                        fundo_df = fundo_df.assign(
                            _versao=pd.to_numeric(fundo_df["Versao"], errors="coerce")
                        )
                        chaves.append("_versao")
                    fundo_df = fundo_df.sort_values(chaves, ascending=False)
                row = fundo_df.iloc[0]

                pl = _to_float(row.get("Patrimonio_Liquido"))
                cotas = _to_float(row.get("Cotas_Emitidas"))
                vpa = _to_float(row.get("Valor_Patrimonial_Cotas"))

                if as_of is not None:
                    for campo, valor in (("Patrimonio_Liquido", pl),
                                         ("Cotas_Emitidas", cotas),
                                         ("Valor_Patrimonial_Cotas", vpa)):
                        if valor is not None and not math.isfinite(valor):
                            return {"abstencao": f"{campo} não finito no Informe vigente",
                                    "avisos": list(avisos)}
                if pl is None:
                    if as_of is not None:
                        return {"abstencao": "Patrimonio_Liquido ausente ou ilegível no Informe vigente",
                                "avisos": list(avisos)}
                    continue
                if as_of is not None and vpa is None:
                    return {"abstencao": "Valor_Patrimonial_Cotas ausente ou ilegível no Informe vigente",
                            "avisos": list(avisos)}

                result: dict = {
                    "cnpj_fundo":        cnpj,
                    "dt_referencia":     str(row.get("Data_Referencia", "")),
                    "patrimonio_liquido": pl,
                    "cotas_emitidas":    cotas,
                    "valor_cota":        vpa,
                    # Vacância física não disponível no informe mensal CVM.
                    # Quando disponível em fonte futura, preencher aqui.
                    "vacancia_fisica":   None,
                    "proveniencia":      self._proveniencia(zip_path, ano, row),
                }
                if avisos:
                    result["avisos"] = list(avisos)
                return result

            except Exception as exc:
                logger.warning(
                    "Erro ao obter dados FII cnpj=%s ano=%d: %s", cnpj, ano, exc
                )

        return None

    def _tabela(
        self, zip_path: Path, parte: str, *, literal: bool = False
    ) -> pd.DataFrame:
        """Um CSV do Informe (`geral`, `ativo_passivo`), em texto; vazio se não existe.

        `literal=True`: sem os `na_values` do pandas, como em `_parsear_complemento`.
        """
        with zipfile.ZipFile(zip_path) as zf:
            nome = next(
                (n for n in zf.namelist() if parte in n.lower() and n.endswith(".csv")),
                None,
            )
            if nome is None:
                return pd.DataFrame()
        return _ler_informe(zip_path, nome, literal=literal)

    def _linhas_do_fundo(
        self, cnpj: str, ano: int
    ) -> tuple[Path, list[dict], list[dict]] | None:
        """Linhas do fundo; `None` se complemento/geral ilegível, composição vazia se falha.

        Cada linha do complemento recebe a `Data_Entrega` e o `Codigo_ISIN` do `geral` da
        mesma referência e versão (F2B-2: corte por entrega da ficha FII 1.1, §3); sem o par
        no `geral`, ficam sem esses campos, e a entrega não está demonstrada.
        """
        try:
            zip_path = self.baixar_informe(ano)
            df = self._parsear_complemento(zip_path, ano, literal=True)
            if df.empty or "CNPJ_Fundo_Classe" not in df.columns:
                return zip_path, [], []
            linhas = df[df["CNPJ_Fundo_Classe"].str.strip() == cnpj].to_dict("records")
            geral = self._tabela(zip_path, "geral", literal=True)
            entregas = {}
            if {"CNPJ_Fundo_Classe", "Data_Referencia", "Versao"} <= set(geral.columns):
                do_fundo = geral[geral["CNPJ_Fundo_Classe"].str.strip() == cnpj]
                for linha in do_fundo.to_dict("records"):
                    entregas[(linha["Data_Referencia"], linha["Versao"])] = {
                        "Data_Entrega": linha.get("Data_Entrega"),
                        "Codigo_ISIN": linha.get("Codigo_ISIN"),
                    }
            for linha in linhas:
                linha.update(
                    entregas.get((linha.get("Data_Referencia"), linha.get("Versao")), {})
                )
            try:
                ativo = self._tabela(zip_path, "ativo_passivo", literal=True)
                composicoes = (
                    ativo[ativo["CNPJ_Fundo_Classe"].str.strip() == cnpj].to_dict("records")
                    if "CNPJ_Fundo_Classe" in ativo.columns
                    else []
                )
            except (OSError, ValueError, KeyError, zipfile.BadZipFile) as exc:
                # A falha da composição não apaga a identidade nem o bloqueio do documento.
                logger.warning("Composição do Informe ilegível cnpj=%s ano=%d: %s", cnpj, ano, exc)
                composicoes = []
        except (OSError, ValueError, KeyError, zipfile.BadZipFile) as exc:
            logger.warning(
                "Erro ao ler rendimentos FII cnpj=%s ano=%d: %s", cnpj, ano, exc
            )
            return None
        return zip_path, linhas, composicoes

    def obter_rendimentos_fii(self, cnpj_fundo: str, *, as_of: datetime | None = None) -> dict:
        """Meses do fundo nos Informes do ano e do anterior, para o rendimento de 12 meses (F2B-28).

        Sem meses do fundo no ano corrente (começo do ano, antes do Informe de janeiro, ou
        Informe do ano ilegível), o último mês é do ano anterior, e a janela precisa da cota
        de dois anos atrás: lê também esse Informe. Devolve todas as linhas do complemento
        (todas as versões; a escolha da maior é da conta, `sentinela.data.rendimento_fii`),
        com a entrega e o ISIN do `geral`, as do `ativo_passivo` (F2B-2), o ISIN da linha
        mais recente e a proveniência dela. Ano que falha fica de fora, com aviso no log; se
        todos os anos lidos falham, a fonte está indisponível e sai `OSError` (F3-P04,
        BUG-3-02), que a cascata registra em `riscos_dados`. Se só parte falha, ou um ano
        necessário vem sem linhas do fundo, `lacunas` diz quais (BUG-3-03), e a cascata
        também as registra; o ano corrente sem linhas ou sem arquivo (em janeiro a CVM ainda
        não o publicou), que só manda ler o de dois anos atrás, não é lacuna.
        Com as_of, o leitor documental seleciona as versões e preserva bloqueios nos 13
        meses necessários; o modo exploratório mantém data original e aviso obrigatório.
        """
        cnpj = cnpj_fundo.strip()
        if as_of is not None and as_of.utcoffset() is None:
            raise ValueError("as_of exige fuso horário")
        dia = date.today() if as_of is None else as_of.astimezone(ZoneInfo("America/Sao_Paulo")).date()
        ano_atual = dia.year
        registros: list[dict] = []
        composicoes: list[dict] = []
        mais_recente = None
        anos = [ano_atual, ano_atual - 1]
        falhas = []
        lacunas = []
        motivos: dict[str, str] = {}
        avisos: set[str] = set()
        modos: set[str] = set()
        for ano in anos:
            lido = self._linhas_do_fundo(cnpj, ano)
            if ano == ano_atual and not (lido and lido[1]):
                anos.append(ano_atual - 2)
            if lido is None:
                falhas.append(ano)
                if ano != ano_atual:  # o do ano corrente pode não ter sido publicado ainda
                    lacunas.append(f"{ano} ilegível ou indisponível")
                continue
            zip_path, linhas, do_ano = lido
            if as_of is not None:
                linhas, bloqueios, rotulos = self._recorte_informe(zip_path, cnpj, linhas, dia)
                por_mes, _ = rendimento_fii._por_mes(linhas)
                chaves = {(r["Data_Referencia"], r["Versao"]) for r in por_mes.values()}
                do_ano = [r for r in do_ano if (r.get("Data_Referencia"), r.get("Versao")) in chaves]
                motivos.update(bloqueios)
                avisos.update(rotulos)
                if linhas or bloqueios:
                    modos.add(leitura.EXPLORATORIO if rotulos else leitura.ESTRITO)
                if ano == ano_atual and not linhas and ano_atual - 2 not in anos:
                    anos.append(ano_atual - 2)
            if not linhas and ano != ano_atual:
                lacunas.append(f"{ano} sem linhas do fundo")
            registros.extend(linhas)
            composicoes.extend(do_ano)
            for linha in linhas:
                # F2B-2: data ilegível ("nan", "2024-13-01") não vira a linha mais recente.
                if not _data_iso(linha.get("Data_Referencia")):
                    continue
                chave = (
                    str(linha.get("Data_Referencia") or ""),
                    _to_float(linha.get("Versao")) or 0.0,
                )
                if mais_recente is None or chave > mais_recente[0]:
                    mais_recente = (chave, zip_path, ano, linha)
        if len(falhas) == len(anos):
            raise OSError(
                "Informe Mensal ilegível ou indisponível em todos os anos lidos: "
                + ", ".join(str(ano) for ano in falhas)
            )
        if len(modos) > 1:
            raise leitura.ModosMisturados("Informes de modos diferentes na mesma janela")
        motivo = self._bloqueio_informe(registros, motivos, 12)
        if motivo:
            return {"abstencao": motivo, "lacunas": [motivo], "avisos": sorted(avisos)}
        proveniencia_recente = (
            self._proveniencia(mais_recente[1], mais_recente[2], mais_recente[3])
            if mais_recente
            else None
        )
        isin = mais_recente[3].get("Codigo_ISIN") if mais_recente else None
        resultado = {
            "registros": registros,
            "composicoes": composicoes,
            "isin": isin if isinstance(isin, str) and isin.strip() else None,
            "proveniencia": proveniencia_recente,
            "lacunas": lacunas,
        }
        if avisos:
            resultado["avisos"] = sorted(avisos)
        return resultado
