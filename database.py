import json
import logging
import sqlite3
from contextlib import closing
from datetime import datetime

from sentinela.data.store import unico
from sentinela.domain.apresentacao import adaptar_leitura

logger = logging.getLogger("Database")

class DatabaseManager:
    # TODO: Considerar tabela cache_fundamentos para guardar última coleta válida
    # do Fundamentus, com TTL de 24h. Permitiria fallback quando scraper falha.
    # Riscos: dados defasados usados em análise fresca sem aviso ao usuário.
    # Implementar apenas quando houver flag clara de "cache_stale" no resultado.
    # Por ora, salvar_analise() já persiste dados_completos como JSON readonly.
    def __init__(self, db_path=None):
        # F3-2c: sem caminho, o banco único (`sentinela.data.store.unico.caminho_padrao`).
        self.db_path = unico.caminho_padrao() if db_path is None else db_path
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
                conn.execute("""CREATE TABLE IF NOT EXISTS fundamentals_cache (
                    ticker        TEXT PRIMARY KEY,
                    dados_json    TEXT NOT NULL,
                    fonte         TEXT,
                    atualizado_em TEXT NOT NULL
                )""")
                # CORRIGIDO: índice idx_data estava ausente desde v10.
                # Sem ele, queries filtradas por data fazem full-scan.
                conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_data
                    ON analises (data_analise)
                """)

    def adicionar_posicao(self, ticker: str, qtd: int, preco: float) -> None:
        """Adiciona ou reduz uma posição da carteira pela regra do custo médio.

        Compra (`qtd` > 0) recalcula o preço médio pela média ponderada; redução parcial
        (`qtd` < 0) mantém o preço médio (F3-P02, BUG-2B-51). Zeragem e redução maior que
        a posição removem a linha, como antes.
        """
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
                        if qtd < 0:
                            novo_pm = pm_antigo
                        else:
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

    def listar_carteira(self) -> list:
        """Retorna todas as posições da carteira como lista de dicts."""
        with closing(self._get_conn()) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM carteira_real")
            return [dict(row) for row in cursor.fetchall()]

    def remover_posicao(self, ticker: str) -> None:
        """Remove completamente uma posição da carteira pelo ticker."""
        ticker = ticker.upper().strip()
        with closing(self._get_conn()) as conn:
            with conn:
                conn.execute(
                    "DELETE FROM carteira_real WHERE ticker = ?",
                    (ticker,)
                )
                logger.info(f"Posição removida: {ticker}")

    def salvar_analise(self, dados: dict) -> None:
        """Persiste ou atualiza a análise de um ticker no banco."""
        ticker = dados.get("ticker")
        if not ticker:
            return
        from sentinela.domain.apresentacao import mesclar_analise

        dados = mesclar_analise({}, dados)
        apresentacao_nova = dados.get("apresentacao_versao") == "1.0"
        try:
            with closing(self._get_conn()) as conn:
                with conn:
                    conn.execute(
                        "INSERT OR REPLACE INTO analises VALUES (?, ?, ?, ?, ?)",
                        (
                            ticker,
                            datetime.now().strftime("%Y-%m-%d %H:%M"),
                            None
                            if apresentacao_nova
                            else int(dados.get("score_final", 0)),
                            None
                            if apresentacao_nova
                            else dados.get("recomendacao", "NEUTRO"),
                            json.dumps(dados, default=str),
                        ),
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
                    return adaptar_leitura(json.loads(row[0]))
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
