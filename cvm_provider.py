import io
import logging
import re
import threading
import zipfile
from collections import OrderedDict
from dataclasses import replace
from datetime import date
from pathlib import Path

import pandas as pd

from cvm_download import baixar_arquivo
from sentinela.data import contas_cvm, proveniencia
from sentinela.data.acoes_cvm import (
    MOTIVO_DOCUMENTO_DIFERENTE,
    MOTIVO_SEM_COMPOSICAO,
    Composicao,
    roe_dos_controladores,
)

logger = logging.getLogger(__name__)

_DFP_URL = "https://dados.cvm.gov.br/dados/CIA_ABERTA/DOC/DFP/DADOS/dfp_cia_aberta_{ano}.zip"
_ITR_URL = "https://dados.cvm.gov.br/dados/CIA_ABERTA/DOC/ITR/DADOS/itr_cia_aberta_{ano}.zip"

# Chave semântica → (campo da tabela de contas, demonstrativo). A leitura confere o par
# (código, descrição) pela tabela do F2A-33 (ADR-0003, D20); nunca só o código.
_CONTAS: dict[str, tuple[str, str]] = {
    "ativo_total":        ("ativo_total", "bpa"),
    "ativo_circulante":   ("ativo_circulante", "bpa"),
    "passivo_total":      ("passivo_total", "bpp"),
    "passivo_circulante": ("passivo_circulante", "bpp"),
    "patrimonio_liquido": ("pl_total", "bpp"),
    "receita_liquida":    ("receita_liquida", "dre"),
    "ebit":               ("ebit", "dre"),
    "lucro_liquido":      ("lucro_liquido", "dre"),
}

_OUTPUT_COLS = ["CNPJ_CIA", "DT_REFER", "CD_CONTA", "DS_CONTA", "VL_CONTA"]

# Memoização por processo dos demonstrativos já filtrados (E-16). A chave inclui
# mtime e tamanho do ZIP: download novo invalida a entrada.
_CACHE_MAX_ENTRADAS = 32
_cache_parse: OrderedDict[tuple, pd.DataFrame] = OrderedDict()
_cache_trava = threading.Lock()
_travas_chave: dict[tuple, threading.Lock] = {}

# F2A-3: linhas 3.99 (LPA divulgado, em R$ por ação, sem a escala monetária) e Composição
# do Capital, por arquivo. A chave inclui mtime e tamanho, como a do parse.
_cache_por_acao: dict[tuple, tuple[pd.DataFrame, pd.DataFrame]] = {}
_CACHE_POR_ACAO_MAX = 8
# F2A-32: índice de entregas do ZIP (`<doc>_cia_aberta_<ano>.csv`, com `DT_RECEB`), por arquivo.
_cache_entregas: dict[tuple, list[dict]] = {}
_CACHE_ENTREGAS_MAX = 8
_COLUNAS_COMPOSICAO = {
    "on": "QT_ACAO_ORDIN_CAP_INTEGR",
    "pn": "QT_ACAO_PREF_CAP_INTEGR",
    "tesouraria_on": "QT_ACAO_ORDIN_TESOURO",
    "tesouraria_pn": "QT_ACAO_PREF_TESOURO",
    "tesouraria_total": "QT_ACAO_TOTAL_TESOURO",
}


def _numero(valor) -> float:
    numero = pd.to_numeric(valor, errors="coerce")
    return 0.0 if pd.isna(numero) else float(numero)


def _ler(df: pd.DataFrame, campo: str, modelo: str):
    return contas_cvm.ler_conta(df.to_dict("records"), campo, modelo, contas_cvm.tabela())


def _pares_de_todos_os_modelos(campo: str) -> tuple[contas_cvm.Conta, ...]:
    """Os pares do campo em qualquer modelo, sem repetir, na ordem da tabela.

    O caminho dos controladores do F2A-3 achava a linha pela descrição em qualquer modelo; a
    união preserva isso (o banco sem setor no índice segue achando "aos sócios").
    """
    vistos: dict[tuple[str, str], contas_cvm.Conta] = {}
    for conta in contas_cvm.tabela():
        if conta.campo == campo:
            vistos.setdefault(
                (conta.codigo, conta.descricao), replace(conta, modelo="empresa")
            )
    return tuple(vistos.values())


def _ler_em_qualquer_modelo(df: pd.DataFrame, campo: str):
    return contas_cvm.ler_conta(
        df.to_dict("records"), campo, "empresa", _pares_de_todos_os_modelos(campo)
    )


def lucro_total_da_dre(dre_emp: pd.DataFrame) -> float | None:
    """Lucro consolidado do período pela tabela, em qualquer modelo (insumo da reserva)."""
    leitura = _ler_em_qualquer_modelo(dre_emp, "lucro_liquido")
    return leitura.valor if isinstance(leitura, contas_cvm.Leitura) else None


def lucro_controladores(dre_emp: pd.DataFrame, lucro_total: float | None) -> float | None:
    """Lucro atribuído aos sócios da controladora (3.11.01, 3.09.01 ou 3.13.01), pela tabela.

    Reservas do F2A-3, que o F2A-37 revisa pela D20: sem a linha reconhecida, vale o lucro
    total; com ela zerada e os não controladores zerados ou sem linha reconhecida, também
    (KLBN11 e SBSP3 na DFP 2025). Valor inválido na linha da controladora: `None`.
    """
    leitura = _ler_em_qualquer_modelo(dre_emp, "lucro_controladores")
    if isinstance(leitura, contas_cvm.Abstencao):
        if leitura.motivo == contas_cvm.MOTIVO_VALOR_INVALIDO:
            return None
        return lucro_total
    if leitura.valor == 0 and lucro_total:
        minoritarios = _ler_em_qualquer_modelo(dre_emp, "lucro_nao_controladores")
        if not (isinstance(minoritarios, contas_cvm.Leitura) and minoritarios.valor != 0):
            return lucro_total
    return leitura.valor


def pl_controladores(bpp_emp: pd.DataFrame, modelo: str = "empresa") -> float | None:
    """PL dos controladores: PL total menos não controladores, pela tabela de contas.

    Sem o par do PL no modelo (a 2.03 do banco é "Provisões", F2A-16), devolve `None`: o PL
    certo dos bancos é do F2A-9.
    """
    total = _ler(bpp_emp, "pl_total", modelo)
    if isinstance(total, contas_cvm.Abstencao):
        return None
    minoritarios = _ler(bpp_emp, "pl_nao_controladores", modelo)
    if isinstance(minoritarios, contas_cvm.Leitura):
        return total.valor - minoritarios.valor
    return total.valor


def lpa_divulgado(linhas_399: pd.DataFrame) -> dict | None:
    """LPA básico divulgado no documento, pela espécie da descrição: ON, depois PN.

    O código da conta não define a espécie (a 3.99.01.01 é PN em algumas companhias); sem
    linha por espécie, vale a 3.99.01 e, por fim, a 3.99, se diferentes de zero.
    """
    if linhas_399.empty:
        return None
    basico = linhas_399[linhas_399["CD_CONTA"].str.startswith("3.99.01.")]
    descricao = basico["DS_CONTA"].fillna("").str.strip().str.upper()
    candidatos = [
        ("ON", basico[descricao == "ON"]),
        ("PN", basico[descricao.str.startswith("PN")]),
        ("BASICO", linhas_399[linhas_399["CD_CONTA"] == "3.99.01"]),
        ("BASICO", linhas_399[linhas_399["CD_CONTA"] == "3.99"]),
    ]
    for especie, linhas in candidatos:
        valores = pd.to_numeric(linhas["VL_CONTA"], errors="coerce")
        valores = valores[valores.notna() & (valores != 0)]
        if not valores.empty:
            return {
                "especie": especie,
                "conta": str(linhas.loc[valores.index[0], "CD_CONTA"]),
                "valor": float(valores.iloc[0]),
            }
    return None


def lpa_divulgado_por_especie(linhas_399: pd.DataFrame) -> dict[str, float]:
    """LPA básico divulgado por espécie (ON e PN, pela descrição da linha 3.99.01.xx), sem zeros."""
    if linhas_399.empty:
        return {}
    basico = linhas_399[linhas_399["CD_CONTA"].str.startswith("3.99.01.")]
    descricao = basico["DS_CONTA"].fillna("").str.strip().str.upper()
    valores = pd.to_numeric(basico["VL_CONTA"], errors="coerce")
    resultado: dict[str, float] = {}
    for especie, filtro in (("ON", descricao == "ON"), ("PN", descricao.str.startswith("PN"))):
        achados = valores[filtro & valores.notna() & (valores != 0)]
        if not achados.empty:
            resultado[especie] = float(achados.iloc[0])
    return resultado


def composicao_do_documento(
    cc: pd.DataFrame, cnpj: str | None, dt_refer: str | None, versao: str | None
) -> tuple[Composicao | None, str | None]:
    """Composição do Capital do mesmo documento (CNPJ, `DT_REFER`, `VERSAO`) ou o motivo da falta."""
    if cc.empty or not cnpj:
        return None, MOTIVO_SEM_COMPOSICAO
    da_cia = cc[cc["CNPJ_CIA"] == cnpj]
    if da_cia.empty:
        return None, MOTIVO_SEM_COMPOSICAO
    mesmo = da_cia[
        (da_cia["DT_REFER"].astype(str) == str(dt_refer))
        & (da_cia["VERSAO"].astype(str) == str(versao))
    ]
    if mesmo.empty:
        return None, MOTIVO_DOCUMENTO_DIFERENTE
    linha = mesmo.iloc[0]
    valores = {campo: _numero(linha.get(coluna)) for campo, coluna in _COLUNAS_COMPOSICAO.items()}
    if pd.isna(pd.to_numeric(linha.get("QT_ACAO_TOTAL_TESOURO"), errors="coerce")):
        # Sem o total da tesouraria, vale a soma das espécies.
        valores["tesouraria_total"] = valores["tesouraria_on"] + valores["tesouraria_pn"]
    return (
        Composicao(
            **valores,
            dt_refer=str(linha["DT_REFER"]),
            versao=str(linha["VERSAO"]),
        ),
        None,
    )


class CVMProvider:
    def __init__(self, cache_dir: str = "data/cvm"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Cache de arquivos
    # ------------------------------------------------------------------

    def _cache_path(self, nome: str) -> Path:
        return self.cache_dir / nome

    def baixar_dfp(self, ano: int) -> Path:
        """Baixa o ZIP de DFP do ano e retorna o Path local (com cache 7d), com a proveniência ao lado."""
        caminho = baixar_arquivo(_DFP_URL.format(ano=ano), self._cache_path(f"dfp_{ano}.zip"))
        proveniencia.registrar_sem_falhar(caminho, _DFP_URL.format(ano=ano), "DFP", str(ano))
        return caminho

    def baixar_itr(self, ano: int) -> Path:
        """Baixa o ZIP de ITR do ano e retorna o Path local (com cache 7d), com a proveniência ao lado."""
        caminho = baixar_arquivo(_ITR_URL.format(ano=ano), self._cache_path(f"itr_{ano}.zip"))
        proveniencia.registrar_sem_falhar(caminho, _ITR_URL.format(ano=ano), "ITR", str(ano))
        return caminho

    def _entregas(self, zip_path: Path) -> list[dict]:
        """Linhas do índice de entregas do ZIP (`dfp_cia_aberta_<ano>.csv` ou o do ITR)."""
        stat = Path(zip_path).stat()
        chave = (str(Path(zip_path).resolve()), stat.st_mtime_ns, stat.st_size)
        with _cache_trava:
            if chave in _cache_entregas:
                return _cache_entregas[chave]
        with zipfile.ZipFile(zip_path) as zf:
            nome = next(
                n for n in zf.namelist() if re.fullmatch(r"(dfp|itr)_cia_aberta_\d{4}\.csv", n)
            )
            with zf.open(nome) as f:
                linhas = pd.read_csv(
                    io.TextIOWrapper(f, encoding="latin-1"), sep=";", dtype=str
                ).to_dict("records")
        with _cache_trava:
            _cache_entregas[chave] = linhas
            while len(_cache_entregas) > _CACHE_ENTREGAS_MAX:
                _cache_entregas.pop(next(iter(_cache_entregas)))
        return linhas

    def proveniencia_do_documento(
        self, zip_path: Path, ano: int, cnpj: str | None, dt_refer: str | None, versao: str | None
    ) -> dict | None:
        """Proveniência da DFP usada (F2A-32): período, entrega (`DT_RECEB`), versão, fonte e hash.

        `None` se o arquivo local não existe ou não é legível.
        """
        try:
            arquivo = proveniencia.registrar_arquivo(
                zip_path, _DFP_URL.format(ano=ano), "DFP", str(ano)
            )
        except OSError:
            return None
        try:
            entrega = proveniencia.entrega_no_indice(
                self._entregas(zip_path),
                {"CNPJ_CIA": cnpj, "DT_REFER": dt_refer, "VERSAO": versao},
            )
        except (OSError, StopIteration, ValueError, KeyError, zipfile.BadZipFile):
            entrega = None
        return arquivo.do_documento(
            dt_refer, versao, entrega, proveniencia.MOTIVO_DOCUMENTO_FORA_DO_INDICE
        ).para_dict()

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

    def parsear_demonstrativo(self, zip_path: Path, tipo: str, include_cd_cvm: bool = False, include_versao: bool = False) -> pd.DataFrame:
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
        stat = Path(zip_path).stat()
        chave = (
            str(Path(zip_path).resolve()),
            stat.st_mtime_ns,
            stat.st_size,
            tipo,
            include_cd_cvm,
            include_versao,
        )
        with _cache_trava:
            trava = _travas_chave.setdefault(chave[:1] + chave[3:], threading.Lock())
        with trava:
            with _cache_trava:
                if chave in _cache_parse:
                    _cache_parse.move_to_end(chave)
                    return _cache_parse[chave].copy()
            df = self._parsear_sem_cache(zip_path, tipo, include_cd_cvm, include_versao)
            with _cache_trava:
                _cache_parse[chave] = df
                while len(_cache_parse) > _CACHE_MAX_ENTRADAS:
                    _cache_parse.popitem(last=False)
        return df.copy()

    def _parsear_sem_cache(self, zip_path: Path, tipo: str, include_cd_cvm: bool, include_versao: bool) -> pd.DataFrame:
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
        if include_versao and "VERSAO" in df.columns:
            cols.append("VERSAO")

        return df[cols].reset_index(drop=True)

    def _dados_por_acao(self, zip_path: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
        """(linhas 3.99 da DRE consolidada, sem escala monetária; Composição do Capital).

        Frames vazios se o arquivo não existe ou não tem os CSVs: a CVM se abstém.
        """
        vazio = (pd.DataFrame(), pd.DataFrame())
        try:
            stat = Path(zip_path).stat()
        except OSError:
            return vazio
        chave = (str(Path(zip_path).resolve()), stat.st_mtime_ns, stat.st_size)
        with _cache_trava:
            if chave in _cache_por_acao:
                return _cache_por_acao[chave]
        try:
            dre = self._read_raw(zip_path, "DRE_con")
            cc = self._read_raw(zip_path, "composicao_capital")
            if "ORDEM_EXERC" in dre.columns:
                dre = dre[dre["ORDEM_EXERC"] == "ÚLTIMO"]
            linhas_399 = dre[dre["CD_CONTA"].astype(str).str.startswith("3.99")][
                ["CNPJ_CIA", "DT_REFER", "VERSAO", "CD_CONTA", "DS_CONTA", "VL_CONTA"]
            ].reset_index(drop=True)
        except (OSError, KeyError, ValueError, zipfile.BadZipFile):
            return vazio
        with _cache_trava:
            _cache_por_acao[chave] = (linhas_399, cc)
            while len(_cache_por_acao) > _CACHE_POR_ACAO_MAX:
                _cache_por_acao.pop(next(iter(_cache_por_acao)))
        return linhas_399, cc


    # ------------------------------------------------------------------
    # Cálculo de indicadores históricos
    # ------------------------------------------------------------------

    def calcular_indicadores(self, cd_cvm: int, anos: int = 5, modelo: str = "empresa") -> dict:
        """
        Retorna dict {ano: {indicador: valor}} para os últimos N anos.

        Indicadores: ativo_total, ativo_circulante, passivo_total,
        passivo_circulante, patrimonio_liquido, receita_liquida, ebit,
        lucro_liquido, roe, margem_liquida, divida_pl.

        `modelo` é o modelo de demonstração (`contas_cvm.modelo_do_setor`). Cada conta é lida
        pelo par (código, descrição); sem correspondência, o campo fica `None` e o motivo vai
        para `contas_abstidas`. Os campos genéricos e o PL dos bancos ainda são lidos como os de
        empresa (abstêm-se): a leitura do modelo de banco é do F2A-9. O lucro dos controladores
        procura os pares de todos os modelos, como o F2A-3 fazia pela descrição.
        """
        leitura_generica = "empresa" if modelo == "banco" else modelo
        ano_atual = date.today().year
        resultado: dict[int, dict] = {}

        for delta in range(1, anos + 1):
            ano = ano_atual - delta
            try:
                zip_path = self.baixar_dfp(ano)
                bpa = self.parsear_demonstrativo(zip_path, "BPA_con", include_cd_cvm=True, include_versao=True)
                bpp = self.parsear_demonstrativo(zip_path, "BPP_con", include_cd_cvm=True, include_versao=True)
                dre = self.parsear_demonstrativo(zip_path, "DRE_con", include_cd_cvm=True, include_versao=True)

                def _filtrar(df: pd.DataFrame) -> pd.DataFrame:
                    if "CD_CVM" in df.columns:
                        return df[df["CD_CVM"] == cd_cvm]
                    return df.iloc[0:0]

                bpa_emp = _filtrar(bpa)
                bpp_emp = _filtrar(bpp)
                dre_emp = _filtrar(dre)

                # Descobre a maior VERSAO do DT_REFER mais recente
                metadata: dict = {}
                df_concat = pd.concat([bpa_emp, bpp_emp, dre_emp], ignore_index=True)

                if not df_concat.empty and "DT_REFER" in df_concat.columns:
                    if "VERSAO" in df_concat.columns:
                        # Converte VERSAO para numérico temporariamente para ordenação correta (ex: "10" > "9")
                        df_concat["_VERSAO_NUM"] = pd.to_numeric(df_concat["VERSAO"], errors="coerce").fillna(0)
                        df_concat = df_concat.sort_values(by=["DT_REFER", "_VERSAO_NUM"], ascending=[False, False])
                        df_concat = df_concat.drop(columns=["_VERSAO_NUM"])
                    else:
                        df_concat = df_concat.sort_values(by=["DT_REFER"], ascending=[False])

                    row = df_concat.iloc[0]

                    dt_ref = str(row["DT_REFER"]) if pd.notna(row["DT_REFER"]) else None
                    ver = str(row["VERSAO"]) if "VERSAO" in row and pd.notna(row["VERSAO"]) else None

                    metadata["cvm_dt_refer"] = dt_ref
                    metadata["cvm_versao"] = ver

                    def _filtrar_versao(df: pd.DataFrame) -> pd.DataFrame:
                        if df.empty:
                            return df
                        if dt_ref and "DT_REFER" in df.columns:
                            df = df[df["DT_REFER"].astype(str) == dt_ref]
                        if ver and "VERSAO" in df.columns:
                            df = df[df["VERSAO"].astype(str) == ver]
                        return df

                    bpa_emp = _filtrar_versao(bpa_emp)
                    bpp_emp = _filtrar_versao(bpp_emp)
                    dre_emp = _filtrar_versao(dre_emp)

                demonstrativos = {"bpa": bpa_emp, "bpp": bpp_emp, "dre": dre_emp}
                valores: dict[str, float | None] = {}
                contas_abstidas: dict[str, str] = {}
                for chave, (campo, demonstrativo) in _CONTAS.items():
                    leitura = _ler(demonstrativos[demonstrativo], campo, leitura_generica)
                    if isinstance(leitura, contas_cvm.Leitura):
                        valores[chave] = leitura.valor
                        continue
                    valores[chave] = None
                    if leitura.motivo != contas_cvm.MOTIVO_LINHA_AUSENTE:
                        contas_abstidas[chave] = f"{leitura.motivo} ({leitura.detalhe})"
                ativo_total        = valores["ativo_total"]
                ativo_circulante   = valores["ativo_circulante"]
                passivo_total      = valores["passivo_total"]
                passivo_circulante = valores["passivo_circulante"]
                pl                 = valores["patrimonio_liquido"]
                receita            = valores["receita_liquida"]
                ebit               = valores["ebit"]
                lucro              = valores["lucro_liquido"]

                cnpj = next(
                    (str(df["CNPJ_CIA"].iloc[0]) for df in (dre_emp, bpp_emp, bpa_emp)
                     if not df.empty and "CNPJ_CIA" in df.columns),
                    None,
                )
                lucro_ctrl = lucro_controladores(dre_emp, lucro_total_da_dre(dre_emp))
                pl_ctrl = pl_controladores(bpp_emp, leitura_generica)
                linhas_399, cc = self._dados_por_acao(zip_path)
                if not linhas_399.empty and cnpj:
                    linhas_399 = linhas_399[
                        (linhas_399["CNPJ_CIA"] == cnpj)
                        & (linhas_399["DT_REFER"].astype(str) == str(metadata.get("cvm_dt_refer")))
                        & (linhas_399["VERSAO"].astype(str) == str(metadata.get("cvm_versao")))
                    ]
                else:
                    linhas_399 = pd.DataFrame()
                composicao, motivo_composicao = composicao_do_documento(
                    cc, cnpj, metadata.get("cvm_dt_refer"), metadata.get("cvm_versao")
                )
                roe_ctrl, motivo_roe = roe_dos_controladores(lucro_ctrl, pl_ctrl)

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
                    "cnpj":               cnpj,
                    "lucro_controladores": lucro_ctrl,
                    "pl_controladores":   pl_ctrl,
                    "roe_motivo":         motivo_roe,
                    "lpa_divulgado":      lpa_divulgado(linhas_399),
                    "lpa_divulgado_por_especie": lpa_divulgado_por_especie(linhas_399),
                    "composicao_capital": composicao,
                    "composicao_motivo":  motivo_composicao,
                    "contas_abstidas":    contas_abstidas,
                    "proveniencia":       self.proveniencia_do_documento(
                        zip_path, ano, cnpj,
                        metadata.get("cvm_dt_refer"), metadata.get("cvm_versao"),
                    ),
                }
                ind["roe"] = roe_ctrl

                if pl and pl != 0:
                    if passivo_total is not None:
                        ind["divida_pl"] = (passivo_total - pl) / pl

                if receita and receita != 0 and lucro is not None:
                    ind["margem_liquida"] = lucro / receita

                resultado[ano] = ind

            except Exception as exc:
                logger.warning("Erro ao calcular indicadores cd_cvm=%d ano=%d: %s", cd_cvm, ano, exc)

        return resultado
