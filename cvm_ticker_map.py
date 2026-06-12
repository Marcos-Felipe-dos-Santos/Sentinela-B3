import io
import logging
import sqlite3
from contextlib import closing
from datetime import datetime, timedelta

import requests

logger = logging.getLogger(__name__)

CVM_CSV_URL = "https://dados.cvm.gov.br/dados/CIA_ABERTA/CAD/DADOS/cad_cia_aberta.csv"
CVM_CSV_TTL_HOURS = 24

# Tabela manual: CD_CVM → ticker B3 (50 empresas mais líquidas do Ibovespa)
_MANUAL_MAP: dict[int, str] = {
    9512:  "PETR4",
    19348: "VALE3",
    1384:  "ITUB4",
    5258:  "BBDC4",
    906:   "ABEV3",
    4170:  "B3SA3",
    14311: "WEGE3",
    21610: "RENT3",
    6050:  "BBAS3",
    18660: "SUZB3",
    14109: "RADL3",
    21490: "LREN3",
    4983:  "BRFS3",
    17566: "RAIL3",
    23264: "HAPV3",
    20036: "GGBR4",
    22470: "JBSS3",
    18112: "EQTL3",
    19313: "VIVT3",
    14664: "TOTS3",
    24295: "MGLU3",
    14010: "CMIG4",
    4308:  "CSNA3",
    18376: "EMBR3",
    15300: "CPLE6",
    18074: "ELET3",
    20885: "CSAN3",
    12130: "HYPE3",
    21202: "KLBN11",
    23892: "ASAI3",
    23337: "SBSP3",
    21067: "TIMS3",
    19712: "ENEV3",
    24104: "NTCO3",
    22187: "LWSA3",
    24414: "RECV3",
    8133:  "USIM5",
    22616: "AZUL4",
    23124: "COGN3",
    14435: "CYRE3",
    11312: "MRVE3",
    7278:  "GOAU4",
    11541: "SLCE3",
    19569: "GOLL4",
    21539: "BRML3",
    23906: "BEEF3",
    24040: "PETZ3",
    22977: "SOMA3",
    23256: "DESK3",
    12300: "QUAL3",
}

_TICKER_TO_CVM: dict[str, int] = {v: k for k, v in _MANUAL_MAP.items()}


def get_cd_cvm(ticker: str) -> int | None:
    """Retorna o CD_CVM da CVM para um ticker B3, ou None se não mapeado."""
    return _TICKER_TO_CVM.get(ticker.upper().strip())


def get_ticker(cd_cvm: int) -> str | None:
    """Retorna o ticker B3 para um CD_CVM da CVM, ou None se não mapeado."""
    return _MANUAL_MAP.get(cd_cvm)


class CVMTickerMap:
    """Mapa CD_CVM ↔ ticker com cache SQLite e atualização via CSV da CVM."""

    def __init__(self, db_path: str = "sentinela_v6.db"):
        self.db_path = db_path
        self._init_table()

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=30)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.row_factory = sqlite3.Row
        return conn

    def _init_table(self) -> None:
        with closing(self._get_conn()) as conn:
            with conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS cvm_tickers (
                        cd_cvm       INTEGER PRIMARY KEY,
                        ticker       TEXT,
                        cnpj         TEXT,
                        denom_social TEXT,
                        sit_reg      TEXT,
                        atualizado_em TEXT NOT NULL
                    )
                """)
                conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_cvm_ticker
                    ON cvm_tickers (ticker)
                """)

    def _cache_is_fresh(self) -> bool:
        with closing(self._get_conn()) as conn:
            row = conn.execute(
                "SELECT atualizado_em FROM cvm_tickers ORDER BY atualizado_em DESC LIMIT 1"
            ).fetchone()
            if not row:
                return False
            try:
                ts = datetime.fromisoformat(row["atualizado_em"])
                return datetime.now() - ts < timedelta(hours=CVM_CSV_TTL_HOURS)
            except ValueError:
                return False

    def _seed_manual_map(self, conn: sqlite3.Connection) -> None:
        now = datetime.now().isoformat()
        for cd_cvm, ticker in _MANUAL_MAP.items():
            conn.execute(
                """
                INSERT OR IGNORE INTO cvm_tickers
                    (cd_cvm, ticker, cnpj, denom_social, sit_reg, atualizado_em)
                VALUES (?, ?, NULL, NULL, NULL, ?)
                """,
                (cd_cvm, ticker, now),
            )

    def refresh(self, force: bool = False) -> bool:
        """Baixa o CSV da CVM e atualiza o cache. Retorna True se houve atualização."""
        if not force and self._cache_is_fresh():
            return False

        try:
            resp = requests.get(CVM_CSV_URL, timeout=30)
            resp.raise_for_status()
            text = resp.content.decode("latin-1")
        except Exception as exc:
            logger.warning("Falha ao baixar CSV da CVM: %s", exc)
            return False

        now = datetime.now().isoformat()
        import csv

        reader = csv.DictReader(io.StringIO(text), delimiter=";")
        rows = [
            (
                int(r["CD_CVM"]),
                r["CNPJ_CIA"].strip(),
                r["DENOM_SOCIAL"].strip(),
                r["SIT_REG"].strip(),
                now,
            )
            for r in reader
            if r.get("CD_CVM", "").strip().isdigit()
        ]

        with closing(self._get_conn()) as conn:
            with conn:
                conn.executemany(
                    """
                    INSERT INTO cvm_tickers (cd_cvm, cnpj, denom_social, sit_reg, atualizado_em)
                    VALUES (?, ?, ?, ?, ?)
                    ON CONFLICT(cd_cvm) DO UPDATE SET
                        cnpj          = excluded.cnpj,
                        denom_social  = excluded.denom_social,
                        sit_reg       = excluded.sit_reg,
                        atualizado_em = excluded.atualizado_em
                    """,
                    rows,
                )
                self._seed_manual_map(conn)

        logger.info("CVM cache atualizado: %d registros", len(rows))
        return True

    def get_cd_cvm(self, ticker: str) -> int | None:
        ticker = ticker.upper().strip()
        # tenta mapa estático primeiro (mais rápido)
        result = _TICKER_TO_CVM.get(ticker)
        if result is not None:
            return result
        with closing(self._get_conn()) as conn:
            row = conn.execute(
                "SELECT cd_cvm FROM cvm_tickers WHERE ticker = ?", (ticker,)
            ).fetchone()
            return int(row["cd_cvm"]) if row else None

    def get_ticker(self, cd_cvm: int) -> str | None:
        result = _MANUAL_MAP.get(cd_cvm)
        if result is not None:
            return result
        with closing(self._get_conn()) as conn:
            row = conn.execute(
                "SELECT ticker FROM cvm_tickers WHERE cd_cvm = ?", (cd_cvm,)
            ).fetchone()
            return row["ticker"] if row and row["ticker"] else None

    def ensure_seeded(self) -> None:
        """Garante que o mapa manual está no banco (sem rede)."""
        with closing(self._get_conn()) as conn:
            with conn:
                self._seed_manual_map(conn)
