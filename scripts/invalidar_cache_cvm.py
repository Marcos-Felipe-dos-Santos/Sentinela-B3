"""Apaga de `fundamentals_cache` os tickers informados (F1-15).

Sem `--aplicar`, só lista o que apagaria.
Uso: python scripts/invalidar_cache_cvm.py [--banco sentinela_v6.db] [--aplicar] TICKER...
"""

from __future__ import annotations

import argparse
import sqlite3
from contextlib import closing


def invalidar(banco: str, tickers: list[str], aplicar: bool) -> list[str]:
    """Devolve os tickers presentes no cache; só os apaga com `aplicar`."""
    if not tickers:
        return []
    with closing(sqlite3.connect(banco)) as conn:
        marcas = ",".join("?" * len(tickers))
        achados = [
            r[0]
            for r in conn.execute(
                f"SELECT ticker FROM fundamentals_cache WHERE ticker IN ({marcas})",
                tickers,
            )
        ]
        if aplicar and achados:
            with conn:
                conn.execute(
                    f"DELETE FROM fundamentals_cache WHERE ticker IN ({marcas})",
                    tickers,
                )
    return achados


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("tickers", nargs="+")
    ap.add_argument("--banco", default="sentinela_v6.db")
    ap.add_argument("--aplicar", action="store_true")
    args = ap.parse_args()
    tickers = [t.upper().strip() for t in args.tickers]
    achados = invalidar(args.banco, tickers, args.aplicar)
    verbo = "apagados" if args.aplicar else "seriam apagados (use --aplicar)"
    print(f"{len(achados)} {verbo}: {', '.join(achados) or '-'}")


if __name__ == "__main__":
    main()
