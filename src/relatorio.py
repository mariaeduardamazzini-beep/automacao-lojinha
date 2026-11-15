"""Histórico do que foi cadastrado ou falhou"""

import json
import os
import shutil
from datetime import datetime


def registrar(config, produto, status, detalhe=""):
    path = config.relatorio_json
    try:
        historico = _ler(path)
        historico.append({
            "data_hora": datetime.now().isoformat(timespec="seconds"),
            "status": status,  # CADASTRADO ou FALHOU
            "nome": produto.nome,
            "arquivo": produto.foto.name,
            "categoria": produto.categoria,
            "subcategoria": produto.subcategoria,
            "detalhe": detalhe,
        })
        # grava num arquivo temporário 
        tmp = f"{path}.tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(historico, f, ensure_ascii=False, indent=2)
        os.replace(tmp, path)
    except Exception as e:
        print("-> Não consegui gravar no relatório:", e)


def _ler(path):
    if not path.is_file():
        return []
    try:
        with open(path, encoding="utf-8") as f:
            dados = json.load(f)
        if isinstance(dados, list):
            return dados
    except (json.JSONDecodeError, OSError):
        pass
    copia = f"{path}.corrompido-{datetime.now():%Y%m%d%H%M%S}"
    shutil.copy(path, copia)
    print(f"Relatório ilegível; há uma cópia em {copia}.")
    return []
