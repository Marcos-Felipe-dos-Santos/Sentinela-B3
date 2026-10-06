import io
import logging
import zipfile
from datetime import date, datetime, timedelta
from pathlib import Path

import pandas as pd
import requests

logger = logging.getLogger(__name__)

_DFP_URL = "https://dados.cvm.gov.br/dados/CIA_ABERTA/DOC/DFP/DADOS/dfp_cia_aberta_{ano}.zip"
_ITR_URL = "https://dados.cvm.gov.br/dados/CIA_ABERTA/DOC/ITR/DADOS/itr_cia_aberta_{ano}.zip"
_CACHE_TTL_DAYS = 7

# Plano de contas CVM → chave semântica
_CONTAS: dict[str, str] = {
    "ativo_total":        "1",
    "ativo_circulante":   "1.01",
    "passivo_total":      "2",
    "passivo_circulante": "2.01",
    "patrimonio_liquido": "2.03",
    "receita_liquida":    "3.01",
    "ebit":               "3.05",
    "lucro_liquido":      "3.11",
}

_OUTPUT_COLS = ["CNPJ_CIA", "DT_REFER", "VERSAO", "CD_CONTA", "DS_CONTA", "VL_CONTA"]


class CVMProvider:
    def __init__(self, cache_dir: str = "data/cvm"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Cache de arquivos
    # ------------------------------------------------------------------

    def _cache_path(self, nome: str) -> Path:
        return self.cache_dir / nome

    def _is_fresh(self, path: Path) -> bool:
        if not path.exists():
            return False
        age = datetime.now() - datetime.fromtimestamp(path.stat().st_mtime)
        return age < timedelta(days=_CACHE_TTL_DAYS)

    def _baixar(self, url: str, dest: Path) -> Path:
        if self._is_fresh(dest):
            logger.debug("Cache válido: %s", dest)
            return dest
        logger.info("Baixando %s → %s", url, dest)
        resp = requests.get(url, timeout=60, stream=True)
        resp.raise_for_status()
        dest.write_bytes(resp.content)
        return dest

    def baixar_dfp(self, ano: int) -> Path:
        """Baixa o ZIP de DFP do ano e retorna o Path local (com cache 7d)."""
        return self._baixar(_DFP_URL.format(ano=ano), self._cache_path(f"dfp_{ano}.zip"))

    def baixar_itr(self, ano: int) -> Path:
        """Baixa o ZIP de ITR do ano e retorna o Path local (com cache 7d)."""
        return self._baixar(_ITR_URL.format(ano=ano), self._cache_path(f"itr_{ano}.zip"))

    # ------------------------------------------------------------------
    # Leitura e parse de CSVs dentro do ZIP
    # ------------------------------------------------------------------

    def _find_csv_name(self, zip_path: Path, tipo: str) -> str:
        with zipfile.ZipFile(zip_path) as zf:
            for name in zf.namelist():
                if tipo in name and name.lower().endswith(".csv"):
                    return name
        raise FileNotFoundError(f"Tipo '{tipo}' não encontrado em {zip_path.name}")

    def _read_raw(self, zip_path: Path, tipo: str) -> pd.DataFrame:
        csv_name = self._find_csv_name(zip_path, tipo)
        with zipfile.ZipFile(zip_path) as zf, zf.open(csv_name) as f:
            return pd.read_csv(
                io.TextIOWrapper(f, encoding="latin-1"),
                sep=";",
                dtype=str,
                low_memory=False,
            )

    def parsear_demonstrativo(self, zip_path: Path, tipo: str, include_cd_cvm: bool = False) -> pd.DataFrame:
        """
        Lê o CSV do tipo dentro do ZIP e retorna DataFrame limpo.
        Por padrão, retorna 5 colunas:
        CNPJ_CIA, DT_REFER, CD_CONTA, DS_CONTA, VL_CONTA.

        Se include_cd_cvm for True, inclui a coluna CD_CVM.

        Aplica a escala monetária (MIL -> BRL) em VL_CONTA.

        Filtros aplicados:
        - ORDEM_EXERC == "ÚLTIMO"  (descarta reapresentações)
        - GRUPO_DFP contém "Consolidado"
        """
        df = self._read_raw(zip_path, tipo)

        if "ORDEM_EXERC" in df.columns:
            df = df[df["ORDEM_EXERC"] == "ÚLTIMO"]
        if "GRUPO_DFP" in df.columns:
            df = df[df["GRUPO_DFP"].str.contains("Consolidado", na=False)]

        df["VL_CONTA"] = pd.to_numeric(df["VL_CONTA"], errors="coerce")

        if "CD_CVM" in df.columns:
            df["CD_CVM"] = pd.to_numeric(df["CD_CVM"], errors="coerce").astype("Int64")

        if "ESCALA_MOEDA" in df.columns:
            mask_mil = df["ESCALA_MOEDA"].str.upper() == "MIL"
            df.loc[mask_mil, "VL_CONTA"] = df.loc[mask_mil, "VL_CONTA"] * 1000

        cols = [c for c in _OUTPUT_COLS if c in df.columns]
        if include_cd_cvm and "CD_CVM" in df.columns:
            cols.append("CD_CVM")

        return df[cols].reset_index(drop=True)


    # ------------------------------------------------------------------
    # Cálculo de indicadores históricos
    # ------------------------------------------------------------------

    def calcular_indicadores(self, cd_cvm: int, anos: int = 5) -> dict:
        """
        Retorna dict {ano: {indicador: valor}} para os últimos N anos.

        Indicadores: ativo_total, ativo_circulante, passivo_total,
        passivo_circulante, patrimonio_liquido, receita_liquida, ebit,
        lucro_liquido, roe, margem_liquida, divida_pl.
        """
        ano_atual = date.today().year
        resultado: dict[int, dict] = {}

        for delta in range(1, anos + 1):
            ano = ano_atual - delta
            try:
                zip_path = self.baixar_dfp(ano)
                bpa = self.parsear_demonstrativo(zip_path, "BPA_con", include_cd_cvm=True)
                bpp = self.parsear_demonstrativo(zip_path, "BPP_con", include_cd_cvm=True)
                dre = self.parsear_demonstrativo(zip_path, "DRE_con", include_cd_cvm=True)

                def _filtrar(df: pd.DataFrame) -> pd.DataFrame:
                    if "CD_CVM" in df.columns:
                        return df[df["CD_CVM"] == cd_cvm]
                    return df.iloc[0:0]

                bpa_emp = _filtrar(bpa)
                bpp_emp = _filtrar(bpp)
                dre_emp = _filtrar(dre)

                metadata: dict = {}

                def _conta(df: pd.DataFrame, codigo: str) -> float | None:
                    rows = df[df["CD_CONTA"] == codigo]
                    if rows.empty:
                        return None

                    if "DT_REFER" in rows.columns and "VERSAO" in rows.columns:
                        rows = rows.sort_values(by=["DT_REFER", "VERSAO"], ascending=[False, False])
                    elif "DT_REFER" in rows.columns:
                        rows = rows.sort_values(by=["DT_REFER"], ascending=[False])

                    # Se já temos metadados, devemos filtrar a conta pela mesma versão. Se não existir, falha.
                    if metadata:
                        dt = metadata.get("cvm_dt_refer")
                        ver = metadata.get("cvm_versao")
                        if dt and "DT_REFER" in rows.columns:
                            rows = rows[rows["DT_REFER"].astype(str) == dt]
                        if ver and "VERSAO" in rows.columns:
                            rows = rows[rows["VERSAO"].astype(str) == ver]

                        if rows.empty:
                            return None

                    row = rows.iloc[0]

                    if not metadata and "DT_REFER" in row and "VERSAO" in row:
                        metadata["cvm_dt_refer"] = str(row["DT_REFER"]) if pd.notna(row["DT_REFER"]) else None
                        metadata["cvm_versao"] = str(row["VERSAO"]) if pd.notna(row["VERSAO"]) else None

                    val = row["VL_CONTA"]
                    return float(val) if pd.notna(val) else None

                ativo_total        = _conta(bpa_emp, _CONTAS["ativo_total"])
                ativo_circulante   = _conta(bpa_emp, _CONTAS["ativo_circulante"])
                passivo_total      = _conta(bpp_emp, _CONTAS["passivo_total"])
                passivo_circulante = _conta(bpp_emp, _CONTAS["passivo_circulante"])
                pl                 = _conta(bpp_emp, _CONTAS["patrimonio_liquido"])
                receita            = _conta(dre_emp, _CONTAS["receita_liquida"])
                ebit               = _conta(dre_emp, _CONTAS["ebit"])
                lucro              = _conta(dre_emp, _CONTAS["lucro_liquido"])

                ind: dict = {
                    "ativo_total":        ativo_total,
                    "ativo_circulante":   ativo_circulante,
                    "passivo_total":      passivo_total,
                    "passivo_circulante": passivo_circulante,
                    "patrimonio_liquido": pl,
                    "receita_liquida":    receita,
                    "ebit":               ebit,
                    "lucro_liquido":      lucro,
                    "roe":                None,
                    "margem_liquida":     None,
                    "divida_pl":          None,
                    "cvm_dt_refer":       metadata.get("cvm_dt_refer"),
                    "cvm_versao":         metadata.get("cvm_versao"),
                }

                if pl and pl != 0:
                    if lucro is not None:
                        ind["roe"] = lucro / pl
                    if passivo_total is not None:
                        ind["divida_pl"] = (passivo_total - pl) / pl

                if receita and receita != 0 and lucro is not None:
                    ind["margem_liquida"] = lucro / receita

                resultado[ano] = ind

            except Exception as exc:
                logger.warning("Erro ao calcular indicadores cd_cvm=%d ano=%d: %s", cd_cvm, ano, exc)

        return resultado
