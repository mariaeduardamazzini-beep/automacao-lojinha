"""Funções de texto usadas em todo o projeto (comparar nomes sem acento, escolher opções)."""

import difflib
import re
import unicodedata


def sem_acento(texto):
    texto = unicodedata.normalize("NFD", texto or "")
    texto = "".join(c for c in texto if unicodedata.category(c) != "Mn")
    return re.sub(r"[^a-z0-9]", "", texto.lower())


def achar_nome_oficial(lista, valor):
    alvo = sem_acento(valor)
    return next((item for item in lista if sem_acento(item) == alvo), None)


def escolher_opcao(opcoes, alvo, aproximado=False):
    chaves = [sem_acento(o) for o in opcoes]
    for i, c in enumerate(chaves):
        if c and c == alvo:
            return i
    for i, c in enumerate(chaves):
        if c and (c == alvo + "s" or alvo == c + "s"):
            return i
    if aproximado and len(alvo) >= 4:
        for i, c in enumerate(chaves):
            if len(c) >= 4 and (alvo in c or c in alvo):
                return i
        notas = [difflib.SequenceMatcher(None, alvo, c).ratio() for c in chaves]
        if notas and max(notas) >= 0.88:
            return notas.index(max(notas))
    return None
