"""BUG-4-24: a CVM consome o ZIP de outra execução com a coleta adiantada desta.

O F4-C02 (BUG-4-16) marca o download pelo hash dos bytes que a execução gravou e confere esse
hash ao registrar a proveniência. Depois da conferência, porém, o consumidor da CVM reabre o
caminho compartilhado: se outra execução B publicar o mesmo destino nesse intervalo, a leitura
usa os bytes de B com a coleta adiantada de A (bloqueio 2 da segunda rodada da R2 do bloco 0,
`docs/loop/auditorias/bloco0-codex-2.md`; DD-97 contestada). Regra do Marcos de 25/11/2026: a
proveniência adiantada só vale para os bytes efetivamente consumidos.

A roda dentro de `coleta_da_execucao`; B, num contexto vazio. Dois ZIPs válidos com conteúdos
distintos; HTTP simulado.
"""

import builtins
import contextvars
import hashlib
import io
import os
import zipfile
from datetime import UTC, datetime, timedelta

import pytest
import requests

import cvm_download
from cvm_provider import CVMProvider
from sentinela.data import proveniencia
from sentinela.data.providers.ifdata import Capital, IFDataProvider

AS_OF = datetime(2026, 9, 15, 15, 0, tzinfo=UTC)


def _zip(conteudo: str) -> bytes:
    memoria = io.BytesIO()
    with zipfile.ZipFile(memoria, "w") as arquivo:
        arquivo.writestr("dados.csv", conteudo)
    return memoria.getvalue()


class _Resposta:
    def __init__(self, corpo: bytes):
        self.corpo = corpo

    def __enter__(self):
        return self

    def __exit__(self, *erro):
        return False

    def raise_for_status(self):
        return None

    def iter_content(self, chunk_size):
        yield self.corpo


def _b_publica(destino, corpo: bytes, monkeypatch) -> None:
    """Outra execução baixa e publica o mesmo destino (contexto vazio, cache ignorado)."""
    monkeypatch.setattr(requests, "get", lambda *a, **k: _Resposta(corpo))
    monkeypatch.setattr(cvm_download, "is_fresh", lambda caminho: False)
    contextvars.Context().run(
        cvm_download.baixar_arquivo, "https://cvm/teste.zip", destino
    )


def test_bytes_consumidos_depois_da_conferencia_sao_os_da_execucao(
    tmp_path, monkeypatch
):
    destino = tmp_path / "dfp_2026.zip"
    corpo_a, corpo_b = _zip("A" * 32), _zip("B" * 32)
    monkeypatch.setattr(requests, "get", lambda *a, **k: _Resposta(corpo_a))
    with proveniencia.coleta_da_execucao(AS_OF, AS_OF):
        caminho = cvm_download.baixar_arquivo("https://cvm/teste.zip", destino)
        registro = proveniencia.registrar_arquivo(
            caminho, "https://cvm/teste.zip", "DFP", "2026"
        )
        assert isinstance(
            registro, proveniencia.ProvenienciaDaExecucao
        )  # conferência de A

        _b_publica(destino, corpo_b, monkeypatch)
        lidos = caminho.read_bytes()  # o consumidor reabre depois da conferência

    assert hashlib.sha256(lidos).hexdigest() == registro.hash_sha256
    assert lidos == corpo_a


def test_provedor_cvm_le_o_zip_da_execucao_mesmo_com_troca_posterior(
    tmp_path, monkeypatch
):
    provedor = CVMProvider(cache_dir=str(tmp_path / "cvm"))
    corpo_a, corpo_b = _zip("A" * 32), _zip("B" * 32)
    monkeypatch.setattr(requests, "get", lambda *a, **k: _Resposta(corpo_a))
    with proveniencia.coleta_da_execucao(AS_OF, AS_OF):
        caminho = provedor.baixar_dfp(2026)
        registro = proveniencia.ler_registro(caminho)

        _b_publica(provedor._cache_path("dfp_2026.zip"), corpo_b, monkeypatch)
        with zipfile.ZipFile(caminho) as arquivo:
            conteudo = arquivo.read("dados.csv").decode()

    assert conteudo == "A" * 32
    assert registro.hash_sha256 == hashlib.sha256(corpo_a).hexdigest()


def test_sem_troca_a_execucao_continua_com_a_coleta_adiantada(tmp_path, monkeypatch):
    """Controle do F4-A09: sem concorrência, o próprio download vale no as_of."""
    destino = tmp_path / "dfp_2026.zip"
    monkeypatch.setattr(requests, "get", lambda *a, **k: _Resposta(_zip("A")))
    with proveniencia.coleta_da_execucao(AS_OF, AS_OF):
        caminho = cvm_download.baixar_arquivo("https://cvm/teste.zip", destino)
        registro = proveniencia.registrar_arquivo(
            caminho, "https://cvm/teste.zip", "DFP", "2026"
        )

    assert datetime.fromisoformat(registro.data_coleta) == AS_OF


def test_consumido_diferente_do_marcado_nao_e_da_execucao(tmp_path, monkeypatch):
    """IF.data e afins: o hash dos bytes lidos tem de bater com o marcado por esta execução."""
    destino = tmp_path / "relatorio.json"
    with proveniencia.coleta_da_execucao(AS_OF, AS_OF):
        destino.write_bytes(b"[1]")
        proveniencia.marcar_baixado(destino, hashlib.sha256(b"[1]").hexdigest())
        registro = proveniencia.registrar_arquivo(
            destino,
            "https://ifdata/x",
            "IF.data",
            "202606",
            motivo=proveniencia.MOTIVO_SEM_ENTREGA_NA_FONTE,
            consumido=hashlib.sha256(b"[2]").hexdigest(),
        )

    assert type(registro) is proveniencia.Proveniencia


def test_limpeza_preserva_pastas_recentes_e_arquivos(tmp_path, monkeypatch):
    agora = 1_800_000_000
    limite = agora - 24 * 3600
    monkeypatch.setattr(proveniencia.time, "time", lambda: agora)
    raiz = tmp_path / ".execucao"
    antiga = raiz / "antiga"
    no_limite = raiz / "no-limite"
    recente = raiz / "recente"
    for pasta, instante in (
        (antiga, limite - 1),
        (no_limite, limite),
        (recente, limite + 1),
    ):
        pasta.mkdir(parents=True)
        (pasta / "dfp.zip").write_bytes(b"zip")
        os.utime(pasta, (instante, instante))
    arquivo = raiz / "arquivo"
    arquivo.write_bytes(b"arquivo")
    os.utime(arquivo, (limite - 1, limite - 1))

    proveniencia._limpar_copias_antigas(raiz)

    assert not antiga.exists()
    assert (no_limite / "dfp.zip").read_bytes() == b"zip"
    assert (recente / "dfp.zip").read_bytes() == b"zip"
    assert arquivo.read_bytes() == b"arquivo"


def test_fallback_de_copia_substitui_link_sem_sobrescrever_o_original(
    tmp_path, monkeypatch
):
    destino = tmp_path / "dfp.zip"
    anterior = tmp_path / "anterior.tmp"
    novo = tmp_path / "novo.tmp"
    anterior.write_bytes(_zip("A"))
    novo.write_bytes(anterior.read_bytes())

    def sem_hardlink(privado, temporario):
        assert privado == copia_anterior
        assert temporario == novo
        assert not privado.exists()
        raise OSError("hardlinks indisponíveis")

    with proveniencia.coleta_da_execucao(AS_OF, AS_OF):
        proveniencia.marcar_baixado(
            destino, hashlib.sha256(anterior.read_bytes()).hexdigest(), anterior
        )
        copia_anterior = proveniencia.caminho_da_execucao(destino)
        assert copia_anterior.samefile(anterior)
        monkeypatch.setattr(type(destino), "hardlink_to", sem_hardlink)
        resumo = hashlib.sha256(novo.read_bytes()).hexdigest()
        proveniencia.marcar_baixado(destino, resumo, novo)
        copia = proveniencia.caminho_da_execucao(destino)
        assert copia == copia_anterior
        assert copia.read_bytes() == novo.read_bytes()
        with zipfile.ZipFile(anterior) as arquivo:
            assert arquivo.read("dados.csv") == b"A"
        assert not copia.samefile(novo)
        assert isinstance(
            proveniencia.registrar_arquivo(
                copia, "https://cvm/teste.zip", "DFP", "2026"
            ),
            proveniencia.ProvenienciaDaExecucao,
        )


def test_limpeza_prossegue_se_uma_remocao_falhar(tmp_path, monkeypatch):
    agora = 1_800_000_000
    monkeypatch.setattr(proveniencia.time, "time", lambda: agora)
    bloqueada = tmp_path / "bloqueada"
    removivel = tmp_path / "removivel"
    for pasta in (bloqueada, removivel):
        pasta.mkdir()
        os.utime(pasta, (0, 0))

    listar = type(tmp_path).iterdir
    remover = proveniencia.shutil.rmtree

    def listar_em_ordem(pasta):
        if pasta == tmp_path:
            return iter((bloqueada, removivel))
        return listar(pasta)

    def remover_se_permitido(pasta):
        if pasta == bloqueada:
            raise PermissionError(pasta)
        remover(pasta)

    with monkeypatch.context() as patch:
        patch.setattr(type(tmp_path), "iterdir", listar_em_ordem)
        patch.setattr(proveniencia.shutil, "rmtree", remover_se_permitido)
        proveniencia._limpar_copias_antigas(tmp_path)

    assert bloqueada.is_dir()
    assert not removivel.exists()


@pytest.mark.parametrize(
    "cache_fresco", [True, False], ids=["cache-valido", "cache-antigo"]
)
def test_ifdata_nao_adianta_coleta_se_cache_muda_apos_leitura(
    tmp_path, monkeypatch, cache_fresco
):
    provedor = IFDataProvider(str(tmp_path))
    caminho = "Teste(AnoMes=@AnoMes)?@AnoMes=202606"
    destino = provedor._arquivo(caminho)
    bytes_a = b'[{"valor":"A"}]'
    bytes_b = b'[{"valor":"B"}]'
    destino.write_bytes(bytes_b)
    instante_b = AS_OF - timedelta(days=1 if cache_fresco else 8)
    os.utime(destino, (instante_b.timestamp(), instante_b.timestamp()))
    troca = tmp_path / "troca"
    troca.write_bytes(bytes_a)

    def rede_indisponivel(*args, **kwargs):
        raise requests.ConnectionError("sem resposta")

    monkeypatch.setattr(requests, "get", rede_indisponivel)

    def trocar_apos_leitura(ler):
        def ler_e_republicar(arquivo, *args, **kwargs):
            lidos = ler(arquivo, *args, **kwargs)
            if arquivo == destino and troca.exists():
                troca.replace(destino)
            return lidos

        return ler_e_republicar

    for metodo in ("read_bytes", "read_text"):
        monkeypatch.setattr(
            type(destino), metodo, trocar_apos_leitura(getattr(type(destino), metodo))
        )

    def consumir(_cnpj, _referencia, buscar, **kwargs):
        assert buscar(caminho) == [{"valor": "B"}]
        return Capital(None, None, None, None)

    monkeypatch.setattr("sentinela.data.providers.ifdata.ler_capital", consumir)
    with proveniencia.coleta_da_execucao(AS_OF, AS_OF):
        proveniencia.marcar_baixado(destino, hashlib.sha256(bytes_a).hexdigest())
        with pytest.raises(ValueError, match="cache trocado após a leitura"):
            provedor.capital(None, AS_OF.date(), as_of=AS_OF)


def test_segundo_download_na_mesma_execucao_preserva_o_zip_ja_entregue(
    tmp_path, monkeypatch
):
    destino = tmp_path / "dfp_2026.zip"
    corpo_a, corpo_b = _zip("A"), _zip("B")
    respostas = iter((corpo_a, corpo_b))
    monkeypatch.setattr(requests, "get", lambda *a, **k: _Resposta(next(respostas)))
    monkeypatch.setattr(cvm_download, "is_fresh", lambda caminho: False)

    with proveniencia.coleta_da_execucao(AS_OF, AS_OF):
        primeiro = cvm_download.baixar_arquivo("https://cvm/teste.zip", destino)
        registro = proveniencia.registrar_arquivo(
            primeiro, "https://cvm/teste.zip", "DFP", "2026"
        )
        segundo = cvm_download.baixar_arquivo("https://cvm/teste.zip", destino)
        assert segundo.read_bytes() == corpo_b
        assert primeiro.read_bytes() == corpo_a
        assert registro.hash_sha256 == hashlib.sha256(primeiro.read_bytes()).hexdigest()


def test_ifdata_cache_valido_inalterado_vincula_hash_ao_resultado(
    tmp_path, monkeypatch
):
    provedor = IFDataProvider(str(tmp_path))
    caminho = "Teste(AnoMes=@AnoMes)?@AnoMes=202606"
    destino = provedor._arquivo(caminho)
    corpo = b'[{"valor":"A"}]'
    destino.write_bytes(corpo)
    coletado = (AS_OF - timedelta(minutes=1)).timestamp()
    os.utime(destino, (coletado, coletado))

    def consumir(_cnpj, _referencia, buscar, **kwargs):
        assert buscar(caminho) == [{"valor": "A"}]
        return Capital(None, None, None, None)

    monkeypatch.setattr("sentinela.data.providers.ifdata.ler_capital", consumir)
    capital = provedor.capital(None, AS_OF.date(), as_of=AS_OF)

    assert len(capital.proveniencia) == 1
    assert capital.proveniencia[0]["hash_sha256"] == hashlib.sha256(corpo).hexdigest()


def test_registro_le_data_e_hash_da_mesma_versao_do_ifdata(tmp_path, monkeypatch):
    destino = tmp_path / "relatorio.json"
    troca = tmp_path / "troca.json"
    instante_a = AS_OF - timedelta(days=2)
    instante_b = AS_OF - timedelta(days=1)
    for arquivo, corpo, instante in (
        (destino, b"[1]", instante_a),
        (troca, b"[2]", instante_b),
    ):
        arquivo.write_bytes(corpo)
        os.utime(arquivo, (instante.timestamp(), instante.timestamp()))

    def trocar_ao_abrir(abrir):
        def abrir_com_troca(arquivo, modo="r", *args, **kwargs):
            if arquivo == destino and modo == "rb" and troca.exists():
                troca.replace(destino)
            return abrir(arquivo, modo, *args, **kwargs)

        return abrir_com_troca

    monkeypatch.setattr(builtins, "open", trocar_ao_abrir(builtins.open))
    monkeypatch.setattr(io, "open", trocar_ao_abrir(io.open))

    registro = proveniencia.registrar_arquivo(
        destino,
        "https://ifdata/x",
        "IF.data",
        "202606",
        consumido=hashlib.sha256(b"[2]").hexdigest(),
    )

    assert registro.hash_sha256 == hashlib.sha256(b"[2]").hexdigest()
    assert datetime.fromisoformat(registro.data_coleta) == instante_b


def test_publicacao_com_falha_nao_disponibiliza_a_copia_privada(tmp_path, monkeypatch):
    destino = tmp_path / "dfp_2026.zip"
    corpo_a, corpo_b = _zip("A"), _zip("B")
    monkeypatch.setattr(requests, "get", lambda *a, **k: _Resposta(corpo_a))
    substituir = os.replace

    def publicar_b_e_falhar(origem, alvo):
        assert alvo == destino
        destino.write_bytes(corpo_b)
        raise OSError("publicação concorrente")

    with proveniencia.coleta_da_execucao(AS_OF, AS_OF):
        monkeypatch.setattr(cvm_download.os, "replace", publicar_b_e_falhar)
        with pytest.raises(OSError, match="publicação concorrente"):
            cvm_download.baixar_arquivo("https://cvm/teste.zip", destino)
        monkeypatch.setattr(cvm_download.os, "replace", substituir)
        resultado = cvm_download.baixar_arquivo("https://cvm/teste.zip", destino)

    assert resultado == destino
    assert resultado.read_bytes() == corpo_b
