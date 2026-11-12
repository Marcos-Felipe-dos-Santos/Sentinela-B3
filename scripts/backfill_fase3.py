"""Backfill ponto-no-tempo da Fase 3 (F3-7b, DD-54; decisões 7, 10, 38 e 39).

Executa no banco único, sobre o intervalo confirmado na parada 2 (2010 em diante, L1), as
cargas já implementadas: CVM (FCA, DFP, ITR e Informe de FII, F3-3b), COTAHIST anual (F3-4a),
séries da taxa real (F3-1c), CDI e Ibovespa (F3-7a), eventos em ações e proventos em dinheiro
da B3 (F3-4b e F3-7a) e a geração do universo (F3-5). Cada carga já é idempotente pelo hash;
o estado (`estado.json`) guarda as etapas concluídas e a execução seguinte as pula, então uma
execução interrompida retoma de onde parou.

Relatório por etapa (`relatorio.json`): arquivos (nome, bytes e SHA-256), o resumo da carga,
falhas e lacunas, e, no fim, o espaço dos brutos e do banco contra a projeção do L1 (1,26 GB
de brutos, 18 GB com o banco). Acima de 100 GB de brutos a execução para (decisão 39).
Downloads um de cada vez, com pausa entre eles (decisão 38).

Banco real: com dados, só migra com um `backup.json` do `sentinela.data.store.backup` cuja
cópia e restauração conferem e cujas contagens de antes são as de agora (política §3, caso 3).

Uso: `python scripts/backfill_fase3.py --banco sentinela_store.db --backup <backup.json>`.
Brutos em `data/fontes/backfill/` e relatórios em `outputs/backfill/`, fora do git.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
import sys
import time
from collections.abc import Callable
from contextlib import closing
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from cvm_download import baixar_arquivo
from sentinela.data.pit import carga_cvm
from sentinela.data.providers import (
    b3_cotahist,
    b3_indices,
    b3_proventos,
    macro,
)
from sentinela.data.referencia import universo
from sentinela.data.store import migracoes

LIMITE_BRUTOS = 100 * 1024**3
PROJECAO_BRUTOS = 1_263_635_166
PROJECAO_TOTAL = 17_960_314_332
ANO_INICIAL = 2010
CVM = "https://dados.cvm.gov.br/dados"
URLS = {
    "FCA": CVM + "/CIA_ABERTA/DOC/FCA/DADOS/fca_cia_aberta_{ano}.zip",
    "DFP": CVM + "/CIA_ABERTA/DOC/DFP/DADOS/dfp_cia_aberta_{ano}.zip",
    "ITR": CVM + "/CIA_ABERTA/DOC/ITR/DADOS/itr_cia_aberta_{ano}.zip",
    "FII_INFORME": CVM + "/FII/DOC/INF_MENSAL/DADOS/inf_mensal_fii_{ano}.zip",
    "COTAHIST": "https://bvmf.bmfbovespa.com.br/InstDados/SerHist/COTAHIST_A{ano}.ZIP",
}
PRIMEIRO_ANO = {"ITR": 2011, "FII_INFORME": 2016}  # L1 §1


class VolumeExcedido(RuntimeError):
    """Brutos acima de 100 GB: para e pergunta (decisão 39)."""


class ArquivoRecusado(ValueError):
    """Arquivo da CVM lido sem nenhuma linha gravada e com linhas recusadas: a etapa falha e o
    registro do arquivo é desfeito, para a próxima execução carregar de novo (BUG-3-25)."""


@dataclass
class Fontes:
    """O que vem de fora: downloads, provedor macro, serviço da B3 e relógio."""

    baixar: Callable[[str, Path], Path] = baixar_arquivo
    macro: Any = None
    obter_b3: Callable[[str], tuple[Any, dict]] = b3_proventos.obter_json
    agora: Callable[[], datetime] = lambda: datetime.now(UTC)
    pausa: float = 2.0
    dormir: Callable[[float], None] = time.sleep
    baixados: list[str] = field(default_factory=list)

    def arquivo(self, url: str, destino: Path) -> Path:
        if self.baixados:
            self.dormir(self.pausa)
        self.baixados.append(url)
        destino.parent.mkdir(parents=True, exist_ok=True)
        return self.baixar(url, destino)


def _sha256(caminho: Path) -> str:
    h = hashlib.sha256()
    with open(caminho, "rb") as f:
        for bloco in iter(lambda: f.read(1 << 20), b""):
            h.update(bloco)
    return h.hexdigest()


def _contagens(conn) -> dict[str, int]:
    tabelas = [
        n for (n,) in conn.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%'"
        )
    ]  # fmt: skip
    return {
        t: conn.execute(f'SELECT COUNT(*) FROM "{t}"').fetchone()[0]
        for t in sorted(tabelas)
    }


def conferir_backup(banco: Path, backup: Path | None) -> None:
    """Banco com dados só migra com backup verificado e sem mudança desde ele."""
    if not banco.exists():
        return
    with closing(sqlite3.connect(banco)) as conn:
        atuais = _contagens(conn)
    if not any(atuais.values()):
        return
    if backup is None:
        raise RuntimeError(
            f"banco {banco.name} com dados: informe o backup.json verificado"
        )
    registros = json.loads(backup.read_text(encoding="utf-8"))
    copia = next(
        (
            r
            for r in registros
            if Path(str(r.get("origem"))).name == banco.name and "sha256" in r
        ),
        None,
    )
    if copia is None or not (copia.get("iguais") and copia.get("restauracao_iguais")):
        raise RuntimeError(f"backup sem cópia verificada de {banco.name}")
    if copia["contagens_antes"] != atuais:
        raise RuntimeError(f"banco {banco.name} mudou depois do backup: faça outro")


def _datas_mensais(de: int, agora: date) -> list[date]:
    """Último dia de cada mês encerrado, de janeiro de `de` ao mês anterior a `agora`."""
    datas, mes = [], date(de, 1, 1)
    while (mes.year, mes.month) < (agora.year, agora.month):
        seguinte = date(mes.year + (mes.month == 12), mes.month % 12 + 1, 1)
        datas.append(seguinte - timedelta(days=1))
        mes = seguinte
    return datas


@dataclass
class Backfill:
    conn: sqlite3.Connection
    brutos: Path
    saida: Path
    fontes: Fontes
    de: int = ANO_INICIAL
    ate: int | None = None
    estado: dict = field(default_factory=dict)
    relatorio: list[dict] = field(default_factory=list)

    def __post_init__(self):
        self.agora = self.fontes.agora()
        if self.agora.utcoffset() is None:
            raise ValueError("o relógio do backfill exige fuso horário")
        self.ate = self.ate or self.agora.year
        self.saida.mkdir(parents=True, exist_ok=True)
        caminho = self.saida / "estado.json"
        if caminho.exists():
            self.estado = json.loads(caminho.read_text(encoding="utf-8"))

    def _guardar(self) -> None:
        (self.saida / "estado.json").write_text(
            json.dumps(self.estado, ensure_ascii=False, indent=1), encoding="utf-8"
        )
        (self.saida / "relatorio.json").write_text(
            json.dumps(self.relatorio, ensure_ascii=False, indent=1, default=str),
            encoding="utf-8",
        )

    def _volume(self) -> int:
        total = sum(p.stat().st_size for p in self.brutos.rglob("*") if p.is_file())
        if total > LIMITE_BRUTOS:
            raise VolumeExcedido(
                f"brutos com {total} bytes, acima de 100 GB (decisão 39)"
            )
        return total

    def etapa(
        self, chave: str, executar: Callable[[], dict], *, atomica: bool = True
    ) -> None:
        """Executa a etapa uma vez; a falha fica no relatório e a etapa não é marcada.

        Etapa atômica roda num `SAVEPOINT`, e a falha desfaz tudo o que ela gravou. A do macro
        não é (`atomica=False`): `macro.gravar_series` grava cada família na própria transação.
        """
        if self.estado.get(chave) == "ok":
            return
        registro = {"etapa": chave, "inicio": datetime.now(UTC).isoformat()}
        if atomica:
            self.conn.execute("SAVEPOINT etapa")
        try:
            registro |= executar()
        except Exception as erro:  # noqa: BLE001  (a falha de uma etapa vai para o relatório)
            if atomica and self.conn.in_transaction:
                self.conn.execute("ROLLBACK TO etapa")
                self.conn.execute("RELEASE etapa")
            self.conn.rollback()
            registro["falha"] = f"{type(erro).__name__}: {erro}"
        else:
            if atomica:
                self.conn.execute("RELEASE etapa")
            self.conn.commit()
            self.estado[chave] = "ok"
        self.relatorio.append(registro)
        self._guardar()
        self._volume()

    def _zip(self, familia: str, ano: int) -> dict:
        url = URLS[familia].format(ano=ano)
        destino = self.brutos / familia.lower() / url.rsplit("/", 1)[1]
        caminho = self.fontes.arquivo(url, destino)
        info = {
            "arquivo": caminho.name,
            "bytes": caminho.stat().st_size,
            "sha256": _sha256(caminho),
        }
        coleta = self.agora.isoformat()
        if familia == "COTAHIST":
            resumo = b3_cotahist.carregar(self.conn, caminho, fonte=url, coleta=coleta)
        else:
            resumo = carga_cvm.carregar(
                self.conn, caminho, tipo=familia, fonte=url, coleta=coleta
            )
            if (
                not resumo.ja_carregado
                and not any(resumo.inseridas.values())
                and not any(resumo.repetidas.values())
                and resumo.total_recusadas
            ):
                raise ArquivoRecusado(
                    f"{caminho.name}: nenhuma linha gravada, "
                    f"{resumo.total_recusadas} recusadas ({resumo.recusadas[0]['motivo']})"
                )
            resumo = {
                "tipo": resumo.tipo,
                "ja_carregado": resumo.ja_carregado,
                "so_ultima_versao": resumo.so_ultima_versao,
                **resumo.para_dict(),
            }
        return {"arquivos": [info], "resumo": resumo}

    def _proventos(self, cd_cvm: int) -> dict:
        relacao = b3_proventos.coletar(cd_cvm, self.agora, self._obter_pausado)
        return {
            "eventos": b3_proventos.gravar_eventos(self.conn, relacao, cd_cvm),
            "proventos": b3_proventos.gravar_proventos(self.conn, relacao, cd_cvm),
            "identidade": relacao.identidade,
        }

    def _obter_pausado(self, endereco: str):
        if self.fontes.baixados:
            self.fontes.dormir(self.fontes.pausa)
        self.fontes.baixados.append(endereco)
        return self.fontes.obter_b3(endereco)

    def _ibovespa(self, ano: int) -> dict:
        fechamentos, fonte = b3_indices.coletar(ano, self._obter_pausado)
        resumo = b3_indices.gravar_ibovespa(self.conn, fechamentos, fonte, self.agora)
        lacuna = None if fechamentos else "ano sem fechamento do Ibovespa"
        return {"arquivos": [fonte], "resumo": resumo, "lacuna": lacuna}

    def executar(self, companhias: list[int]) -> list[dict]:
        anos = range(self.de, self.ate + 1)
        for familia in ("FCA", "DFP", "ITR", "FII_INFORME", "COTAHIST"):
            for ano in anos:
                if ano >= PRIMEIRO_ANO.get(familia, self.de):
                    self.etapa(
                        f"{familia}:{ano}", lambda f=familia, a=ano: self._zip(f, a)
                    )
        if self.fontes.macro is not None:
            datas = _datas_mensais(self.de, self.agora.date())
            self.etapa(
                "macro",
                lambda: {"resumo": macro.gravar_series(
                    self.conn, self.fontes.macro, coleta=self.agora, datas=datas
                )},
                atomica=False,
            )  # fmt: skip
            self.etapa(
                "cdi",
                lambda: {"resumo": macro.gravar_cdi(
                    self.conn, self.fontes.macro, self.agora.date(), self.agora
                )},
            )  # fmt: skip
        for ano in anos:
            self.etapa(f"IBOV:{ano}", lambda a=ano: self._ibovespa(a))
        for cd_cvm in companhias:
            self.etapa(f"proventos:{cd_cvm}", lambda c=cd_cvm: self._proventos(c))
        self.etapa(
            "universo",
            lambda: {
                "resumo": {
                    "listagens": universo.gerar(self.conn, self.agora.isoformat())
                }
            },
        )
        self.etapa("cobertura_proventos", self._cobertura_proventos)
        self.relatorio.append(self._espaco())
        self._guardar()
        return self.relatorio

    def _cobertura_proventos(self) -> dict:
        """Por ano: companhias do FCA no fim do ano, quantas têm coleta e quantas, identidade (DD-35).

        Conta a coleta mais recente de cada emissor com a identidade conferida (decisão 33). É
        teto do que `proventos_ate` lê: ele também exige a coleta antes do dia de D e a relação
        completa (total declarado igual aos registros).
        """
        com_coleta, com_identidade = set(), set()
        for cd, identidade in self.conn.execute(
            "SELECT cd_cvm, identidade FROM proventos_coletas AS p WHERE coleta = ("
            "SELECT MAX(coleta) FROM proventos_coletas AS q WHERE q.emissor = p.emissor)"
        ):
            com_coleta.add(cd)
            if identidade is None:
                com_identidade.add(cd)
        cd_por_cnpj = {
            cnpj: str(int(cd)) for cnpj, cd in self.conn.execute(
                "SELECT cnpj, cd_cvm FROM fca_entregas WHERE cd_cvm IS NOT NULL"
            )
            if str(cd).strip().isdigit()
        }  # fmt: skip
        por_ano = {}
        for ano in range(self.de, self.ate + 1):
            dia = min(date(ano, 12, 31), self.agora.date())
            cnpjs = {
                c["cnpj"] for c in universo.companhias_em(self.conn, dia)["companhias"]
            }
            cobertas = {c for c in cnpjs if cd_por_cnpj.get(c) in com_coleta}
            conferidas = {c for c in cnpjs if cd_por_cnpj.get(c) in com_identidade}
            por_ano[str(ano)] = {
                "companhias": len(cnpjs),
                "com_proventos": len(cobertas),
                "com_identidade": len(conferidas),
            }
        return {"resumo": por_ano}

    def _espaco(self) -> dict:
        brutos = self._volume()
        caminho = self._caminho_banco()
        banco = sum(
            Path(caminho + sufixo).stat().st_size
            for sufixo in ("", "-wal", "-shm")
            if caminho and Path(caminho + sufixo).is_file()
        )
        return {
            "etapa": "espaco",
            "brutos_bytes": brutos,
            "banco_bytes": banco,
            "projecao_brutos_bytes": PROJECAO_BRUTOS,
            "projecao_total_bytes": PROJECAO_TOTAL,
        }

    def _caminho_banco(self) -> str:
        (_, _, caminho), *_ = self.conn.execute("PRAGMA database_list").fetchall()
        return caminho


def companhias_do_indice(caminho: Path) -> list[int]:
    """Códigos CVM das ações e units do índice atual (a B3 só devolve listadas hoje, L1 §4)."""
    registros = json.loads(caminho.read_text(encoding="utf-8"))["registros"]
    return sorted(
        {
            int(r["cd_cvm"]) for r in registros.values()
            if r.get("classe") in ("STOCK", "UNIT") and r.get("cd_cvm") is not None
        }
    )  # fmt: skip


def main(argv: list[str] | None = None) -> int:
    args = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    args.add_argument("--banco", type=Path, required=True)
    args.add_argument("--backup", type=Path)
    args.add_argument("--brutos", type=Path, default=Path("data/fontes/backfill"))
    args.add_argument("--saida", type=Path, default=Path("outputs/backfill"))
    args.add_argument(
        "--indice", type=Path, default=Path("data/referencia/indice.json")
    )
    args.add_argument("--de", type=int, default=ANO_INICIAL)
    args.add_argument("--ate", type=int)
    args.add_argument("--pausa", type=float, default=2.0)
    a = args.parse_args(argv)
    conferir_backup(a.banco, a.backup)
    fontes = Fontes(macro=macro.MacroProvider(a.brutos / "macro"), pausa=a.pausa)
    with closing(sqlite3.connect(a.banco)) as conn:
        migracoes.aplicar(conn)
        Backfill(conn, a.brutos, a.saida, fontes, a.de, a.ate).executar(
            companhias_do_indice(a.indice)
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
