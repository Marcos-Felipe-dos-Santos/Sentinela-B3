"""Provider de dados de FIIs a partir do Informe Mensal CVM.

Schema verificado contra inf_mensal_fii_*_2024.csv (CVM, 2024-06):
  complemento : CNPJ_Fundo_Classe, Data_Referencia, Patrimonio_Liquido,
                Cotas_Emitidas, Valor_Patrimonial_Cotas, Percentual_Dividend_Yield_Mes
  geral        : CNPJ_Fundo_Classe, Quantidade_Cotas_Emitidas, Segmento_Atuacao

Observação: vacância física NÃO está disponível no informe mensal.
"""
import io
import logging
import zipfile
from datetime import date
from pathlib import Path

import pandas as pd

from cvm_download import baixar_arquivo
from sentinela.data import proveniencia

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

    def _parsear_complemento(self, zip_path: Path, ano: int) -> pd.DataFrame:
        """Lê inf_mensal_fii_complemento_{ano}.csv do ZIP. Retorna DataFrame."""
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
            with zf.open(csv_name) as f:
                return pd.read_csv(
                    io.TextIOWrapper(f, encoding="latin-1"),
                    sep=";",
                    dtype=str,
                    low_memory=False,
                )

    def _proveniencia(self, zip_path: Path, ano: int, row) -> dict | None:
        """Proveniência do informe usado (F2A-32): mês, versão e `Data_Entrega` do `geral`.

        `None` se o arquivo local não é legível.
        """
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
        try:
            with zipfile.ZipFile(zip_path) as zf, zf.open(
                f"inf_mensal_fii_geral_{ano}.csv"
            ) as f:
                geral = pd.read_csv(
                    io.TextIOWrapper(f, encoding="latin-1"), sep=";", dtype=str
                )
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

    def obter_dados_fii(self, cnpj_fundo: str) -> dict | None:
        """Retorna os dados mais recentes do fundo, ou None se não encontrado.

        Campos no retorno:
          cnpj_fundo, dt_referencia, patrimonio_liquido, cotas_emitidas,
          valor_cota (VPA oficial = PL/cotas),
          vacancia_fisica (sempre None — não disponível no informe mensal),
          proveniencia (F2A-32).

        Com `Data_Referencia` ilegível numa linha do fundo, devolve
        `{"abstencao": MOTIVO_DATA_ILEGIVEL}` (F2B-2, aceite Gemini HEAD60e61e2).
        """
        cnpj = cnpj_fundo.strip()
        ano_atual = date.today().year

        for ano in [ano_atual, ano_atual - 1]:
            try:
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

                if pl is None:
                    continue

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
                return result

            except Exception as exc:
                logger.warning(
                    "Erro ao obter dados FII cnpj=%s ano=%d: %s", cnpj, ano, exc
                )

        return None

    def _tabela(self, zip_path: Path, parte: str) -> pd.DataFrame:
        """Um CSV do Informe (`geral`, `ativo_passivo`), em texto; vazio se não existe."""
        with zipfile.ZipFile(zip_path) as zf:
            nome = next(
                (n for n in zf.namelist() if parte in n.lower() and n.endswith(".csv")),
                None,
            )
            if nome is None:
                return pd.DataFrame()
            with zf.open(nome) as f:
                return pd.read_csv(
                    io.TextIOWrapper(f, encoding="latin-1"),
                    sep=";",
                    dtype=str,
                    low_memory=False,
                )

    def _linhas_do_fundo(
        self, cnpj: str, ano: int
    ) -> tuple[Path, list[dict], list[dict]] | None:
        """Linhas do fundo no complemento e no `ativo_passivo` do ano; `None` se ilegível.

        Cada linha do complemento recebe a `Data_Entrega` e o `Codigo_ISIN` do `geral` da
        mesma referência e versão (F2B-2: corte por entrega da ficha FII 1.1, §3); sem o par
        no `geral`, ficam sem esses campos, e a entrega não está demonstrada.
        """
        try:
            zip_path = self.baixar_informe(ano)
            df = self._parsear_complemento(zip_path, ano)
            if df.empty or "CNPJ_Fundo_Classe" not in df.columns:
                return zip_path, [], []
            linhas = df[df["CNPJ_Fundo_Classe"].str.strip() == cnpj].to_dict("records")
            geral = self._tabela(zip_path, "geral")
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
            ativo = self._tabela(zip_path, "ativo_passivo")
            composicoes = (
                ativo[ativo["CNPJ_Fundo_Classe"].str.strip() == cnpj].to_dict("records")
                if "CNPJ_Fundo_Classe" in ativo.columns
                else []
            )
        except (OSError, ValueError, KeyError, zipfile.BadZipFile) as exc:
            logger.warning(
                "Erro ao ler rendimentos FII cnpj=%s ano=%d: %s", cnpj, ano, exc
            )
            return None
        return zip_path, linhas, composicoes

    def obter_rendimentos_fii(self, cnpj_fundo: str) -> dict:
        """Meses do fundo nos Informes do ano e do anterior, para o rendimento de 12 meses (F2B-28).

        Sem meses do fundo no ano corrente (começo do ano, antes do Informe de janeiro, ou
        Informe do ano ilegível), o último mês é do ano anterior, e a janela precisa da cota
        de dois anos atrás: lê também esse Informe. Devolve todas as linhas do complemento
        (todas as versões; a escolha da maior é da conta, `sentinela.data.rendimento_fii`),
        com a entrega e o ISIN do `geral`, as do `ativo_passivo` (F2B-2), o ISIN da linha
        mais recente e a proveniência dela. Ano que falha fica de fora, com aviso no log.
        """
        cnpj = cnpj_fundo.strip()
        ano_atual = date.today().year
        registros: list[dict] = []
        composicoes: list[dict] = []
        mais_recente = None
        anos = [ano_atual, ano_atual - 1]
        for ano in anos:
            lido = self._linhas_do_fundo(cnpj, ano)
            if ano == ano_atual and not (lido and lido[1]):
                anos.append(ano_atual - 2)
            if lido is None:
                continue
            zip_path, linhas, do_ano = lido
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
        proveniencia_recente = (
            self._proveniencia(mais_recente[1], mais_recente[2], mais_recente[3])
            if mais_recente
            else None
        )
        isin = mais_recente[3].get("Codigo_ISIN") if mais_recente else None
        return {
            "registros": registros,
            "composicoes": composicoes,
            "isin": isin if isinstance(isin, str) and isin.strip() else None,
            "proveniencia": proveniencia_recente,
        }
