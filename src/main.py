""" Fluxo: lê o produtos.json -> mostra a situação -> pergunta quantos -> cadastra no site
       -> registra no relatório -> move a foto para dados/fotos/cadastrados.
"""

import getpass
import sys
from datetime import datetime

import config as cfg
import relatorio
from produtos import carregar_lista, mover_para_cadastrados, nomes_repetidos


def mostrar_situacao(s):
    for aviso in s.avisos:
        print("⚠", aviso)
    print("\n=== SITUAÇÃO DA LISTA ===")
    print(f"  Pendentes (serão cadastrados): {len(s.pendentes)}")
    print(f"  Já cadastrados antes: {len(s.ja_cadastrados)}")
    print(f"  Sem foto na pasta: {len(s.sem_foto)}")
    print(f"  Fotos que não estão no produtos.json: {len(s.fora_da_lista)}")
    print("============================")
    for i, p in enumerate(s.pendentes, 1):
        print(f"  {i:>3}. {p.nome}  | {p.categoria} > {p.subcategoria}  <- {p.foto.name}")
    for nome in nomes_repetidos(s.pendentes):
        print(f"⚠ Nome repetido: {nome}")


def perguntar_quantidade(total):
    while True:
        resp = input(f"\nQuantos cadastrar? (1 a {total}, Enter = todos): ").strip()
        if resp == "":
            qtd = total
        elif resp.isdigit() and 1 <= int(resp) <= total:
            qtd = int(resp)
        else:
            print("Número inválido.")
            continue
        confirmado = input(f"Cadastrar {qtd} produto(s)? (s/n): ").strip().lower() in ("s", "sim")
        return qtd if confirmado else 0


def cadastrar_todos(config, produtos):
    from navegador import Navegador  

    email = config.email or input("E-mail da loja: ").strip()
    senha = config.senha or getpass.getpass("Senha da loja: ")
    inicio, sucesso, falhas = datetime.now(), [], []

    with Navegador(config) as nav:
        try:
            nav.login(email, senha)
            nav.ir_para_produtos()
            for i, p in enumerate(produtos, 1):
                print(f"\n========== Produto {i} de {len(produtos)} ==========")
                try:
                    nav.cadastrar(p, ultimo=(i == len(produtos)))
                except Exception as e:
                    print(f"❌ Falhou em '{p.nome}': {e}")
                    nav.salvar_print(p.nome)
                    relatorio.registrar(config, p, "FALHOU", str(e)[:300])
                    falhas.append(p)
                    try:
                        nav.ir_para_produtos()  # recomeça limpo para o próximo
                    except Exception:
                        pass
                    continue
                relatorio.registrar(config, p, "CADASTRADO", "confirmado pelo site")
                mover_para_cadastrados(p.foto, config)
                sucesso.append(p)
        except Exception as e:
            print(f"\n❌ Erro geral: {e}")
            nav.salvar_print("geral")

        conferencia = nav.conferir([p.nome for p in sucesso], inicio) if sucesso else {}
        print("\n========== RESUMO ==========")
        print(f"✅ Cadastrados: {len(sucesso)}")
        for p in sucesso:
            marca = {"ok": "✔ na lista do site", "nao": "⚠ não achei"}
            print(f"   - {p.nome}: {marca.get(conferencia.get(p.nome), 'sem conferência')}")
        print(f"❌ Falharam: {len(falhas)}.  As fotos continuam em dados/fotos")
        for p in falhas:
            print(f"   - {p.nome}")
        input("\nPressione a tecla Enter para fechar o navegador...")


def main():
    config = cfg.carregar()
    config.fotos.mkdir(parents=True, exist_ok=True)
    situacao = carregar_lista(config)
    mostrar_situacao(situacao)

    if "--simular" in sys.argv:
        print("\n(--simular: nada foi enviado ao site)")
        return
    if not situacao.pendentes:
        print("\nNenhum produto para cadastrar.")
        return
    qtd = perguntar_quantidade(len(situacao.pendentes))
    if qtd:
        cadastrar_todos(config, situacao.pendentes[:qtd])


if __name__ == "__main__":
    main()
