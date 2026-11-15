from src.api import SistemaArvores, ORDENS


def imprimir_resultados(resultados):
    if resultados:
        for r in resultados:
            print(f"{r['codigo']} - {r['nome']} ({r['professor']})")
    else:
        print("Nenhuma disciplina encontrada.")


def desenhar(arvore, limite=6):
    """Desenha a árvore deitada (raiz à esquerda) até `limite` níveis."""
    def rotulo(no):
        if hasattr(no, "cor"):
            return f"{no.valor['codigo']} [{'V' if no.cor == 'vermelho' else 'P'}]"
        if hasattr(no, "altura"):
            fb = (no.esq.altura if no.esq else 0) - (no.dir.altura if no.dir else 0)
            return f"{no.valor['codigo']} (fb {fb:+d})"
        return no.valor["codigo"]

    def percorrer(no, prefixo, nivel):
        if no is None or nivel > limite:
            return
        percorrer(no.dir, prefixo + "        ", nivel + 1)
        print(prefixo + "└── " + rotulo(no))
        percorrer(no.esq, prefixo + "        ", nivel + 1)

    percorrer(arvore.raiz, "", 1)


def imprimir_metricas(sistema):
    m = sistema.metricas()
    print(f"\nOrdem de inserção: {m['ordem']} | n = {m['n']} | "
          f"altura mínima possível = {m['altura_minima']}")
    print(f"{'Árvore':<14}{'Altura':>8}{'Rotações':>10}{'Recolor.':>10}{'Comp. média':>13}")
    for a in m["arvores"]:
        print(f"{a['nome']:<14}{a['altura']:>8}{a['rotacoes']:>10}"
              f"{a['recoloracoes']:>10}{a['comparacoes_media']:>13}")
    print()


def main():
    sistema = SistemaArvores()
    print(f"{sistema.avl.tamanho} disciplinas carregadas em AVL, Rubro-Negra e BST.")
    imprimir_metricas(sistema)

    while True:
        print("1 - Buscar por codigo (AVL)")
        print("2 - Buscar por inicio do nome (Rubro-Negra)")
        print("3 - Buscar faixa de codigos (AVL)")
        print("4 - Buscar por professor")
        print("5 - Listar em ordem (percurso em-ordem)")
        print("6 - Inserir disciplina")
        print("7 - Remover disciplina")
        print("8 - Comparar arvores / reconstruir")
        print("9 - Desenhar arvore")
        print("0 - Sair")
        opcao = input("Opcao: ").strip()

        if opcao == "1":
            d, caminho = sistema.buscar_codigo(input("Codigo: "))
            print("Caminho: " + " -> ".join(caminho))
            imprimir_resultados([d] if d else [])
        elif opcao == "2":
            resultados, visitados = sistema.buscar_prefixo(input("Inicio do nome: "))
            print(f"{len(visitados)} nos visitados.")
            imprimir_resultados(resultados)
        elif opcao == "3":
            resultados, visitados = sistema.buscar_faixa(input("De: "), input("Ate: "))
            print(f"{len(visitados)} nos visitados.")
            imprimir_resultados(resultados)
        elif opcao == "4":
            imprimir_resultados(sistema.buscar_professor(input("Professor: ")))
        elif opcao == "5":
            tipo = input("Por codigo (avl) ou por nome (rb)? ").strip().lower() or "avl"
            imprimir_resultados(sistema.arvores.get(tipo, sistema.avl).em_ordem())
        elif opcao == "6":
            dados = {
                "codigo": input("Codigo: "),
                "nome": input("Nome: "),
                "professores": input("Professores (separados por virgula): "),
                "carga_horaria": input("Carga horaria: "),
                "numero_turmas": input("Turmas: "),
            }
            try:
                d, nova, passos = sistema.inserir(dados)
            except ValueError as erro:
                print(erro)
                continue
            for p in passos["avl"]:
                if p["tipo"] in ("desbalanceado", "rotacao"):
                    print("  AVL: " + p["descricao"])
            print(("Inserida: " if nova else "Atualizada: ") + d["codigo"])
        elif opcao == "7":
            d, passos = sistema.remover(input("Codigo: "))
            if d is None:
                print("Disciplina nao encontrada.")
                continue
            for p in passos["avl"]:
                if p["tipo"] in ("desbalanceado", "rotacao"):
                    print("  AVL: " + p["descricao"])
            print("Removida: " + d["codigo"])
        elif opcao == "8":
            ordem = input(f"Ordem de insercao {ORDENS} [enter mantem]: ").strip()
            if ordem in ORDENS:
                sistema.reconstruir(ordem)
            imprimir_metricas(sistema)
        elif opcao == "9":
            tipo = input("Qual arvore (avl, rb, bst)? ").strip().lower() or "avl"
            desenhar(sistema.arvores.get(tipo, sistema.avl))
        elif opcao == "0":
            break
        else:
            print("Opcao invalida.")


if __name__ == "__main__":
    main()
