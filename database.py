import sqlite3
import json
import logging
from datetime import datetime
from contextlib import closing

logger = logging.getLogger("Database")

class DatabaseManager:
    # TODO: Considerar tabela cache_fundamentos para guardar última coleta válida
    # do Fundamentus, com TTL de 24h. Permitiria fallback quando scraper falha.
    # Riscos: dados defasados usados em análise fresca sem aviso ao usuário.
    # Implementar apenas quando houver flag clara de "cache_stale" no resultado.
    # Por ora, salvar_analise() já persiste dados_completos como JSON readonly.
    def __init__(self, db_path="sentinela_v6.db"):
        self.db_path = db_path
        self._init_db()

    def _get_conn(self):
        conn = sqlite3.connect(self.db_path, timeout=30)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with closing(self._get_conn()) as conn:
            with conn:
                conn.execute("""CREATE TABLE IF NOT EXISTS analises (
                    ticker       TEXT PRIMARY KEY,
                    data_analise TEXT,
                    score        INTEGER,
                    recomendacao TEXT,
                    dados_completos TEXT
                )""")
                conn.execute("""CREATE TABLE IF NOT EXISTS carteira_real (
                    ticker      TEXT PRIMARY KEY,
                    quantidade  INTEGER,
                    preco_medio REAL,
                    data_aporte TEXT
                )""")
                # CORRIGIDO: índice idx_data estava ausente desde v10.
                # Sem ele, queries filtradas por data fazem full-scan.
                conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_data
                    ON analises (data_analise)
                """)

    def adicionar_posicao(self, ticker, qtd, preco):
        ticker = ticker.upper().strip()
        with closing(self._get_conn()) as conn:
            with conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT quantidade, preco_medio FROM carteira_real WHERE ticker = ?",
                    (ticker,)
                )
                row = cursor.fetchone()

                if row:
                    qtd_antiga = row['quantidade']
                    pm_antigo  = row['preco_medio']
                    nova_qtd   = qtd_antiga + qtd

                    if nova_qtd > 0:
                        novo_pm = ((qtd_antiga * pm_antigo) + (qtd * preco)) / nova_qtd
                        conn.execute(
                            "UPDATE carteira_real SET quantidade=?, preco_medio=? WHERE ticker=?",
                            (nova_qtd, novo_pm, ticker)
                        )
                    else:
                        conn.execute("DELETE FROM carteira_real WHERE ticker=?", (ticker,))
                else:
                    if qtd > 0:
                        conn.execute(
                            "INSERT INTO carteira_real VALUES (?, ?, ?, ?)",
                            (ticker, qtd, preco, datetime.now().strftime("%Y-%m-%d"))
                        )

    def listar_carteira(self):
        with closing(self._get_conn()) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM carteira_real")
            return [dict(row) for row in cursor.fetchall()]

    def salvar_analise(self, dados):
        ticker = dados.get('ticker')
        if not ticker:
            return
        try:
            with closing(self._get_conn()) as conn:
                with conn:
                    conn.execute(
                        "INSERT OR REPLACE INTO analises VALUES (?, ?, ?, ?, ?)",
                        (
                            ticker,
                            datetime.now().strftime("%Y-%m-%d %H:%M"),
                            int(dados.get('score_final', 0)),
                            dados.get('recomendacao', 'NEUTRO'),
                            json.dumps(dados, default=str),
                        )
                    )
        except Exception as e:
            logger.error(f"Erro ao salvar {ticker}: {e}")

    def buscar_analise(self, ticker):
        with closing(self._get_conn()) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT dados_completos FROM analises WHERE ticker=?",
                (ticker,)
            )
            row = cursor.fetchone()
            if row and row[0]:
                try:
                    return json.loads(row[0])
                except (json.JSONDecodeError, TypeError) as e:
                    logger.error(f"JSON corrompido para {ticker}: {e}")
            return None

    def reset_db(self):
        import os
        base_path, _ = os.path.splitext(self.db_path)
        db_paths = {
            self.db_path,
            f"{self.db_path}-wal",
            f"{self.db_path}-shm",
            f"{base_path}.db-wal",
            f"{base_path}.db-shm",
            f"{base_path}.sqlite-wal",
            f"{base_path}.sqlite-shm",
        }
        removed = False
        for db_path in db_paths:
            if os.path.exists(db_path):
                os.remove(db_path)
                removed = True
        if removed:
            self._init_db()
