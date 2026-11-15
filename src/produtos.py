"""Lê o dados/produtos.json, valida cada item e procura a foto de cada um."""

import json
import os
import re
import shutil
from dataclasses import dataclass, field
from pathlib import Path

from textos import achar_nome_oficial, sem_acento

CHAVES = ("arquivo", "nome", "categoria", "subcategoria")
EXTENSOES = (".jpg", ".jpeg", ".png", ".webp")


@dataclass
class Produto:
    nome: str
    foto: Path
    categoria: str
    subcategoria: str


@dataclass
class Situacao:
    """Resultado da leitura do produtos.json."""

    pendentes: list = field(default_factory=list)       # Produto com foto em dados/fotos
    ja_cadastrados: list = field(default_factory=list)  # nomes cuja foto já está em cadastrados/
    sem_foto: list = field(default_factory=list)        # nomes sem foto em lugar nenhum
    fora_da_lista: list = field(default_factory=list)   # fotos na pasta que não estão no JSON
    avisos: list = field(default_factory=list)


def carregar_lista(config):
    try:
        with open(config.produtos_json, encoding="utf-8-sig") as f:
            dados = json.load(f)
    except FileNotFoundError:
        raise SystemExit(f"❌ Não achei {config.produtos_json} (veja dados/produtos.example.json)")
    except json.JSONDecodeError as e:
        raise SystemExit(f"❌ produtos.json mal formado (linha {e.lineno}, coluna {e.colno}): {e.msg}")
    if not isinstance(dados, list):
        raise SystemExit("❌ produtos.json precisa ser uma lista: [ {...}, {...} ]")

    situacao = Situacao()
    na_lista = set()
    for i, item in enumerate(dados, 1):
        # 1) formato
        if not isinstance(item, dict):
            situacao.avisos.append(f"item {i}: não é um objeto {{...}} (ignorado)")
            continue
        faltando = [k for k in CHAVES if not str(item.get(k, "")).strip()]
        if faltando:
            situacao.avisos.append(f"item {i}: faltam as chaves {faltando} (ignorado)")
            continue
        arquivo, nome = item["arquivo"].strip(), item["nome"].strip()
        na_lista.add(arquivo)

        # 2) categoria e subcategoria existem no site?
        categoria = achar_nome_oficial(config.categorias, item["categoria"])
        if not categoria:
            situacao.avisos.append(f"'{nome}': categoria '{item['categoria']}' não existe (ignorado)")
            continue
        sub = achar_nome_oficial(config.categorias[categoria], item["subcategoria"])
        if not sub:
            situacao.avisos.append(f"'{nome}': subcategoria '{item['subcategoria']}' não existe em {categoria} (ignorado)")
            continue

        # 3) onde está a foto?
        foto = config.fotos / arquivo
        if foto.is_file():
            situacao.pendentes.append(Produto(nome, foto, categoria, sub))
        elif ja_cadastrada(arquivo, config):
            situacao.ja_cadastrados.append(nome)
        else:
            situacao.sem_foto.append(nome)
            situacao.avisos.append(f"'{nome}': foto '{arquivo}' não está em dados/fotos (ignorado)")

    if config.fotos.is_dir():
        situacao.fora_da_lista = sorted(
            f for f in os.listdir(config.fotos)
            if f.lower().endswith(EXTENSOES) and f not in na_lista
        )
    return situacao


def ja_cadastrada(arquivo, config):
    """True se a foto já foi movida para fotos/cadastrados (aceita também 'nome_1.jpeg')."""
    if not config.cadastrados.is_dir():
        return False
    base, ext = os.path.splitext(arquivo)
    padrao = re.compile(re.escape(base) + r"(_\d+)?" + re.escape(ext), re.IGNORECASE)
    return any(padrao.fullmatch(f) for f in os.listdir(config.cadastrados))


def mover_para_cadastrados(foto, config):
    """Move a foto para fotos/cadastrados sem sobrescrever (usa _1, _2... se precisar)."""
    config.cadastrados.mkdir(parents=True, exist_ok=True)
    destino = config.cadastrados / foto.name
    n = 1
    while destino.exists():
        destino = config.cadastrados / f"{foto.stem}_{n}{foto.suffix}"
        n += 1
    shutil.move(str(foto), str(destino))
    return destino


def nomes_repetidos(produtos):
    vistos, repetidos = set(), set()
    for p in produtos:
        chave = sem_acento(p.nome)
        (repetidos if chave in vistos else vistos).add(chave)
    return sorted({p.nome for p in produtos if sem_acento(p.nome) in repetidos})
