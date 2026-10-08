import importlib.util
import json
from pathlib import Path

SCRIPT = Path(__file__).parents[1] / "scripts" / "golden_diff.py"


def _carregar():
    spec = importlib.util.spec_from_file_location("golden_diff", SCRIPT)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


def _caso(id_, saida, motor="acoes", **entrada):
    return {"id": id_, "motor": motor, "entrada": entrada, "saida": saida}


def _gravar(caminho, casos):
    caminho.write_text(
        "".join(json.dumps(c, ensure_ascii=False) + "\n" for c in casos),
        encoding="utf-8",
    )
    return str(caminho)


def _rodar(modulo, tmp_path, antigo, novo, *args):
    base = _gravar(tmp_path / "base.jsonl", antigo)
    atual = _gravar(tmp_path / "novo.jsonl", novo)
    return modulo.main(["--base", base, "--novo", atual, *args])


def test_lista_alterados_incluidos_e_removidos(tmp_path, capsys):
    gd = _carregar()
    antigo = [
        _caso("igual", {"v": 1}),
        _caso("muda", {"v": 1}),
        _caso("sai", {"v": 1}),
    ]
    novo = [
        _caso("igual", {"v": 1}),
        _caso("muda", {"v": 2}),
        _caso("entra", {"v": 3}),
    ]
    assert _rodar(gd, tmp_path, antigo, novo) == 0
    linhas = capsys.readouterr().out.splitlines()
    assert "alterados: 1" in linhas
    assert "incluídos: 1" in linhas
    assert "removidos: 1" in linhas
    assert "  acoes/muda" in linhas
    assert "  acoes/entra" in linhas
    assert "  acoes/sai" in linhas
    assert not any("acoes/igual" in linha for linha in linhas)


def test_sem_mudanca_lista_zero_casos(tmp_path, capsys):
    gd = _carregar()
    casos = [_caso("a", {"v": 1}), _caso("b", {"v": 2}, motor="fii")]
    assert _rodar(gd, tmp_path, casos, casos) == 0
    saida = capsys.readouterr().out
    assert "alterados: 0" in saida
    assert "incluídos: 0" in saida
    assert "removidos: 0" in saida


def test_onde_falha_com_caso_fora_do_predicado(tmp_path, capsys):
    gd = _carregar()
    antigo = [_caso("a", {"v": 1}, dy=0.5), _caso("b", {"v": 1}, dy=0.1)]
    novo = [_caso("a", {"v": 2}, dy=0.5), _caso("b", {"v": 2}, dy=0.1)]
    ok = _rodar(gd, tmp_path, antigo, novo, "--onde", "True")
    assert ok == 0
    capsys.readouterr()
    codigo = _rodar(
        gd,
        tmp_path,
        antigo,
        novo,
        "--onde",
        "entrada['dy'] > 0.3 and saida_nova['v'] == saida_antiga['v'] + 1",
    )
    assert codigo == 1
    saida = capsys.readouterr().out
    assert "fora do predicado: 1" in saida
    assert "  acoes/b" in saida.split("fora do predicado")[1]


def test_onde_so_avalia_alterados(tmp_path):
    gd = _carregar()
    antigo = [_caso("a", {"v": 1}), _caso("b", {"v": 1})]
    novo = [_caso("a", {"v": 1}), _caso("b", {"v": 2})]
    assert _rodar(gd, tmp_path, antigo, novo, "--onde", "caso['id'] == 'b'") == 0


def test_par_compara_casos_renomeados(tmp_path, capsys):
    gd = _carregar()
    antigo = [_caso("dy-velho", {"v": 1, "k": "x"}), _caso("outro", {"v": 9})]
    novo = [_caso("dy-novo", {"v": 2, "k": "x"}), _caso("outro", {"v": 9})]
    assert _rodar(gd, tmp_path, antigo, novo, "--par", "velho=novo") == 0
    saida = capsys.readouterr().out
    assert "pares: 1" in saida
    assert "acoes/dy-velho -> acoes/dy-novo" in saida
    assert "v: 1 -> 2" in saida
    assert "k:" not in saida


def test_par_sem_correspondente_fica_como_incluido_e_removido(tmp_path, capsys):
    gd = _carregar()
    antigo = [_caso("dy-velho", {"v": 1})]
    novo = [_caso("outro-novo", {"v": 1})]
    assert _rodar(gd, tmp_path, antigo, novo, "--par", "velho=novo") == 0
    saida = capsys.readouterr().out
    assert "pares: 0" in saida
    assert "incluídos: 1" in saida
    assert "removidos: 1" in saida
