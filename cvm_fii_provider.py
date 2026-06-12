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
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Optional

import pandas as pd
import requests

logger = logging.getLogger(__name__)

_INF_URL = (
    "https://dados.cvm.gov.br/dados/FII/DOC/INF_MENSAL/DADOS/"
    "inf_mensal_fii_{ano}.zip"
)
_CACHE_TTL_DAYS = 7


def _to_float(value) -> Optional[float]:
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

    def baixar_informe(self, ano: int) -> Path:
        """Baixa o ZIP do informe mensal FII do ano e retorna o Path local (cache 7d)."""
        return self._baixar(
            _INF_URL.format(ano=ano),
            self._cache_path(f"inf_mensal_fii_{ano}.zip"),
        )

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

    # ------------------------------------------------------------------
    # API pública
    # ------------------------------------------------------------------

    def obter_dados_fii(self, cnpj_fundo: str) -> Optional[dict]:
        """Retorna os dados mais recentes do fundo, ou None se não encontrado.

        Campos no retorno:
          cnpj_fundo, dt_referencia, patrimonio_liquido, cotas_emitidas,
          valor_cota (VPA oficial = PL/cotas), dy_mes_decimal,
          vacancia_fisica (sempre None — não disponível no informe mensal).
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

                # Registro mais recente
                if "Data_Referencia" in fundo_df.columns:
                    fundo_df = fundo_df.sort_values("Data_Referencia", ascending=False)
                row = fundo_df.iloc[0]

                pl = _to_float(row.get("Patrimonio_Liquido"))
                cotas = _to_float(row.get("Cotas_Emitidas"))
                vpa = _to_float(row.get("Valor_Patrimonial_Cotas"))
                dy_mes = _to_float(row.get("Percentual_Dividend_Yield_Mes"))

                if pl is None:
                    continue

                result: dict = {
                    "cnpj_fundo":        cnpj,
                    "dt_referencia":     str(row.get("Data_Referencia", "")),
                    "patrimonio_liquido": pl,
                    "cotas_emitidas":    cotas,
                    "valor_cota":        vpa,
                    "dy_mes_decimal":    dy_mes,
                    # Vacância física não disponível no informe mensal CVM.
                    # Quando disponível em fonte futura, preencher aqui.
                    "vacancia_fisica":   None,
                }
                return result

            except Exception as exc:
                logger.warning(
                    "Erro ao obter dados FII cnpj=%s ano=%d: %s", cnpj, ano, exc
                )

        return None
