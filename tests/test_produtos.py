"""Testes sem navegador: validação do produtos.json e regras de texto."""

import json
import shutil
from pathlib import Path

import config as cfg
from produtos import carregar_lista, mover_para_cadastrados
from textos import escolher_opcao, sem_acento

RAIZ = Path(__file__).resolve().parent.parent


def projeto_de_teste(tmp_path, itens, fotos=(), cadastradas=()):
    """Cria um projeto falso numa pasta temporária (nunca mexe nos seus dados)."""
    (tmp_path / "configs").mkdir()
    shutil.copy(RAIZ / "configs" / "settings.yaml", tmp_path / "configs")
    (tmp_path / "dados" / "fotos" / "cadastrados").mkdir(parents=True)
    (tmp_path / "dados" / "produtos.json").write_text(json.dumps(itens), encoding="utf-8")
    for f in fotos:
        (tmp_path / "dados" / "fotos" / f).write_bytes(b"x")
    for f in cadastradas:
        (tmp_path / "dados" / "fotos" / "cadastrados" / f).write_bytes(b"x")
    return cfg.carregar(tmp_path)


def item(arquivo, nome, categoria="Roupas", sub="Vestidos"):
    return {"arquivo": arquivo, "nome": nome, "categoria": categoria, "subcategoria": sub}


def test_sem_acento():
    assert sem_acento("Calçados!") == "calcados"


def test_escolher_opcao_nao_confunde_blusao_com_blusas():
    assert escolher_opcao(["Blusas", "Blusão", "Blusinhas"], "blusao", aproximado=True) == 1


def test_separa_pendente_ja_cadastrado_e_sem_foto(tmp_path):
    config = projeto_de_teste(
        tmp_path,
        [item("a.jpg", "A"), item("b.jpg", "B"), item("c.jpg", "C")],
        fotos=["a.jpg", "solta.jpg"], cadastradas=["b.jpg"],
    )
    s = carregar_lista(config)
    assert [p.nome for p in s.pendentes] == ["A"]
    assert s.ja_cadastrados == ["B"] and s.sem_foto == ["C"] and s.fora_da_lista == ["solta.jpg"]


def test_categoria_aceita_acento_e_maiuscula_diferentes(tmp_path):
    config = projeto_de_teste(tmp_path, [item("a.jpg", "Carrinho", "outros", "BRINQUEDOS")], fotos=["a.jpg"])
    p = carregar_lista(config).pendentes[0]
    assert (p.categoria, p.subcategoria) == ("Outros", "Brinquedos")


def test_subcategoria_inexistente_vira_aviso(tmp_path):
    config = projeto_de_teste(tmp_path, [item("a.jpg", "X", "Roupas", "Gravata")], fotos=["a.jpg"])
    s = carregar_lista(config)
    assert s.pendentes == [] and "Gravata" in s.avisos[0]


def test_mover_nao_sobrescreve(tmp_path):
    config = projeto_de_teste(tmp_path, [], fotos=["a.jpg"], cadastradas=["a.jpg"])
    destino = mover_para_cadastrados(config.fotos / "a.jpg", config)
    assert destino.name == "a_1.jpg"


def test_exemplo_do_repositorio_e_valido(tmp_path):
    exemplo = json.loads((RAIZ / "dados" / "produtos.example.json").read_text(encoding="utf-8"))
    config = projeto_de_teste(tmp_path, exemplo, fotos=[e["arquivo"] for e in exemplo])
    assert len(carregar_lista(config).pendentes) == len(exemplo)
