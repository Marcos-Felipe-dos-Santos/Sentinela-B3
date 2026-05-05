"""Append-only repository for analysis snapshots."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from contextlib import closing
from datetime import datetime
from typing import Any, Optional

from sentinela.domain.models import AnalysisResult


class AnalysisRepository:
    """Stores analysis runs without replacing previous snapshots."""

    def __init__(self, db_path: str = "sentinela.db") -> None:
        self.db_path = db_path
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=30)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with closing(self._get_conn()) as conn:
            with conn:
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS analysis_runs (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        ticker TEXT NOT NULL,
                        created_at TEXT NOT NULL,
                        asset_type TEXT,
                        recommendation TEXT,
                        fair_value REAL,
                        current_price REAL,
                        upside REAL,
                        confidence REAL,
                        data_quality_score REAL,
                        input_hash TEXT,
                        payload_json TEXT NOT NULL
                    )
                    """
                )
                conn.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_analysis_runs_ticker
                    ON analysis_runs(ticker)
                    """
                )
                conn.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_analysis_runs_created_at
                    ON analysis_runs(created_at)
                    """
                )
                conn.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_analysis_runs_ticker_created_at
                    ON analysis_runs(ticker, created_at)
                    """
                )

    def save_run(self, analysis: dict | AnalysisResult) -> int:
        """Insert one immutable analysis snapshot and return its row id."""
        payload = self._payload_from_analysis(analysis)
        payload_json = self._serialize_payload(payload)
        input_hash = hashlib.sha256(payload_json.encode("utf-8")).hexdigest()

        ticker = self._normalize_ticker(
            self._first_present(
                payload,
                "ticker",
                ("raw", "ticker"),
                ("market", "ticker"),
            )
        )

        with closing(self._get_conn()) as conn:
            with conn:
                cursor = conn.execute(
                    """
                    INSERT INTO analysis_runs (
                        ticker,
                        created_at,
                        asset_type,
                        recommendation,
                        fair_value,
                        current_price,
                        upside,
                        confidence,
                        data_quality_score,
                        input_hash,
                        payload_json
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        ticker,
                        datetime.now().isoformat(timespec="microseconds"),
                        self._asset_type(payload),
                        self._text_or_none(
                            self._first_present(
                                payload,
                                "recomendacao",
                                "recommendation",
                                ("valuation", "recomendacao"),
                                ("valuation", "recommendation"),
                                ("raw", "recomendacao"),
                            )
                        ),
                        self._float_or_none(
                            self._first_present(
                                payload,
                                "fair_value",
                                ("valuation", "fair_value"),
                                ("raw", "fair_value"),
                            )
                        ),
                        self._float_or_none(
                            self._first_present(
                                payload,
                                "preco_atual",
                                "current_price",
                                ("market", "preco_atual"),
                                ("market", "current_price"),
                                ("raw", "preco_atual"),
                            )
                        ),
                        self._float_or_none(
                            self._first_present(
                                payload,
                                "upside",
                                ("valuation", "upside"),
                                ("raw", "upside"),
                            )
                        ),
                        self._float_or_none(
                            self._first_present(
                                payload,
                                "confianca",
                                "confidence",
                                ("valuation", "confianca"),
                                ("valuation", "confidence"),
                                ("data_quality", "confianca"),
                                ("data_quality", "confidence"),
                                ("raw", "confianca"),
                            )
                        ),
                        self._float_or_none(
                            self._first_present(
                                payload,
                                "data_quality_score",
                                ("data_quality", "score"),
                                ("raw", "data_quality_score"),
                            )
                        ),
                        input_hash,
                        payload_json,
                    ),
                )
                return int(cursor.lastrowid)

    def list_runs(self, ticker: str, limit: int = 20) -> list[dict]:
        """Return recent runs for a ticker, newest first."""
        ticker_norm = self._normalize_ticker(ticker)
        safe_limit = max(0, int(limit))
        with closing(self._get_conn()) as conn:
            cursor = conn.execute(
                """
                SELECT *
                FROM analysis_runs
                WHERE ticker = ?
                ORDER BY created_at DESC, id DESC
                LIMIT ?
                """,
                (ticker_norm, safe_limit),
            )
            return [self._row_to_dict(row) for row in cursor.fetchall()]

    def get_latest(self, ticker: str) -> Optional[dict]:
        """Return the most recent run for a ticker, or None."""
        runs = self.list_runs(ticker, limit=1)
        return runs[0] if runs else None

    def count_runs(self, ticker: Optional[str] = None) -> int:
        """Count all runs or only runs for one ticker."""
        with closing(self._get_conn()) as conn:
            if ticker is None:
                cursor = conn.execute("SELECT COUNT(*) FROM analysis_runs")
            else:
                cursor = conn.execute(
                    "SELECT COUNT(*) FROM analysis_runs WHERE ticker = ?",
                    (self._normalize_ticker(ticker),),
                )
            return int(cursor.fetchone()[0])

    @staticmethod
    def _payload_from_analysis(analysis: dict | AnalysisResult) -> dict[str, Any]:
        if isinstance(analysis, AnalysisResult):
            return analysis.to_dict()
        if isinstance(analysis, dict):
            return dict(analysis)
        if hasattr(analysis, "to_dict"):
            payload = analysis.to_dict()
            return dict(payload) if isinstance(payload, dict) else {"value": payload}
        return {"value": analysis}

    @staticmethod
    def _serialize_payload(payload: dict[str, Any]) -> str:
        try:
            return json.dumps(payload, sort_keys=True, default=str, ensure_ascii=False)
        except (TypeError, ValueError):
            return json.dumps(
                {"value": str(payload)},
                sort_keys=True,
                default=str,
                ensure_ascii=False,
            )

    @staticmethod
    def _normalize_ticker(value: Any) -> str:
        return str(value or "").upper().replace(".SA", "").strip()

    @staticmethod
    def _text_or_none(value: Any) -> Optional[str]:
        if value is None:
            return None
        return str(value)

    @staticmethod
    def _float_or_none(value: Any) -> Optional[float]:
        if value is None or value == "":
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    @classmethod
    def _first_present(cls, payload: dict[str, Any], *paths: Any) -> Any:
        for path in paths:
            value = cls._nested_get(payload, path)
            if value is not None:
                return value
        return None

    @staticmethod
    def _nested_get(payload: dict[str, Any], path: Any) -> Any:
        if isinstance(path, str):
            return payload.get(path)

        current: Any = payload
        for key in path:
            if not isinstance(current, dict) or key not in current:
                return None
            current = current[key]
        return current

    def _asset_type(self, payload: dict[str, Any]) -> Optional[str]:
        value = self._first_present(
            payload,
            "tipo_ativo",
            "asset_type",
            ("raw", "tipo_ativo"),
            ("raw", "asset_type"),
        )
        if value is not None:
            return str(value)
        if payload.get("is_fii") is True:
            return "FII"
        if payload.get("is_fii") is False:
            return "ACAO"
        return None

    def _row_to_dict(self, row: sqlite3.Row) -> dict[str, Any]:
        data = dict(row)
        try:
            data["payload"] = json.loads(data.pop("payload_json"))
        except (json.JSONDecodeError, TypeError):
            data["payload"] = {}
        return data

