"""Fachada usada pelo menu do terminal (main.py) e pelo front-end web.

No navegador, este módulo roda dentro do Pyodide: o JavaScript chama as
funções no fim do arquivo, que recebem e devolvem JSON (texto).
"""

import json
import math
import random

from src.carregaDados import carregar_disciplinas
from src.arvore_bst import ArvoreBST
from src.arvore_avl import ArvoreAVL
from src.arvore_rubro_negra import ArvoreRubroNegra

ORDENS = ("json", "ordenada", "aleatoria")


def _capturar(arvore, acao):
    """Executa `acao` registrando cada passo emitido pela árvore."""
    passos = []
    arvore.ao_passo = passos.append
    try:
        resultado = acao()
    finally:
        arvore.ao_passo = None
    return resultado, passos


def _ordenar(disciplinas, ordem, semente=None):
    lista = list(disciplinas)
    if ordem == "ordenada":
        lista.sort(key=lambda d: d["codigo"])
    elif ordem == "aleatoria":
        random.Random(semente).shuffle(lista)
    elif ordem != "json":
        raise ValueError(f"Ordem inválida: {ordem}")
    return lista


def _limpar_disciplina(dados):
    codigo = str(dados.get("codigo", "")).strip().upper()
    nome = " ".join(str(dados.get("nome", "")).split())
    if not codigo or not nome:
        raise ValueError("Informe código e nome da disciplina.")
    professores = dados.get("professores") or []
    if isinstance(professores, str):
        professores = [p.strip() for p in professores.replace(";", ",").split(",")]
    professores = [p for p in professores if p] or ["A definir"]

    def inteiro(campo, padrao):
        try:
            return int(dados.get(campo) or padrao)
        except (TypeError, ValueError):
            return padrao

    return {
        "codigo": codigo,
        "nome": nome,
        "professores": professores,
        "professor": "; ".join(professores),
        "numero_turmas": inteiro("numero_turmas", 1),
        "carga_horaria": inteiro("carga_horaria", 60),
        "campus": "UnB Gama (FCTE)",
        "ano_periodo_referencia": "2026.2",
        "fonte_disciplina": "inserida_pelo_usuario",
    }


class SistemaArvores:
    def __init__(self, disciplinas=None):
        self.disciplinas = list(disciplinas if disciplinas is not None
                                else carregar_disciplinas())
        self.reconstruir("json")

    # ----------------------------------------------------------- construção
    def reconstruir(self, ordem="json", semente=None):
        """Monta as três árvores inserindo as disciplinas na ordem pedida."""
        self.ordem = ordem
        self.arvores = {"avl": ArvoreAVL(), "rb": ArvoreRubroNegra(), "bst": ArvoreBST()}
        for d in _ordenar(self.disciplinas, ordem, semente):
            for arvore in self.arvores.values():
                arvore.inserir(d)
        return self

    @property
    def avl(self):
        return self.arvores["avl"]

    @property
    def rb(self):
        return self.arvores["rb"]

    @property
    def bst(self):
        return self.arvores["bst"]

    # ---------------------------------------------------------------- busca
    def buscar_codigo(self, codigo, tipo="avl"):
        arvore = self.arvores[tipo]
        codigo = codigo.strip().upper()
        if tipo == "rb":
            # Na RB a chave é o nome: busca o nome pela AVL e depois desce na RB.
            d, _ = self.avl.buscar(codigo)
            if d is None:
                return None, []
            return self.rb.buscar(self.rb.chave_de(d))
        return arvore.buscar(codigo)

    def buscar_prefixo(self, texto):
        return self.rb.prefixo(texto)

    def buscar_faixa(self, inicio, fim):
        inicio, fim = inicio.strip().upper(), fim.strip().upper()
        # `fim` inclusivo para o usuário: tudo que começa com `fim` também entra.
        return self.avl.faixa(inicio, fim + "￿")

    def buscar_professor(self, nome):
        from src.normaliza import normalizar
        palavras = normalizar(nome).split()
        return [d for d in self.avl.em_ordem() if palavras and any(
            all(p in normalizar(prof).split() for p in palavras)
            for prof in d["professores"])]

    # --------------------------------------------------------- modificação
    def inserir(self, dados):
        d = _limpar_disciplina(dados)
        passos = {}
        nova = True
        antiga, _ = self.avl.buscar(d["codigo"])
        if antiga is not None and self.rb.chave_de(antiga) != self.rb.chave_de(d):
            # O nome mudou: a chave da RB mudou, então remove a versão antiga.
            self.rb.remover(self.rb.chave_de(antiga))
        for tipo, arvore in self.arvores.items():
            nova_aqui, passos[tipo] = _capturar(arvore, lambda a=arvore: a.inserir(d))
            nova = nova and nova_aqui
        self.disciplinas = [x for x in self.disciplinas if x["codigo"] != d["codigo"]] + [d]
        return d, nova, passos

    def remover(self, codigo):
        d, _ = self.avl.buscar(codigo.strip().upper())
        if d is None:
            return None, {}
        passos = {}
        for tipo, arvore in self.arvores.items():
            chave = arvore.chave_de(d)
            _, passos[tipo] = _capturar(arvore, lambda a=arvore, c=chave: a.remover(c))
        self.disciplinas = [x for x in self.disciplinas if x["codigo"] != d["codigo"]]
        return d, passos

    # ------------------------------------------------------------ métricas
    def metricas(self):
        n = self.avl.tamanho
        resultado = []
        for tipo, arvore in self.arvores.items():
            info = {
                "tipo": tipo,
                "nome": arvore.nome,
                "nos": arvore.tamanho,
                "altura": arvore.altura(),
                "rotacoes": arvore.rotacoes,
                "recoloracoes": arvore.recoloracoes,
                "comparacoes_media": round(arvore.profundidade_media(), 2),
            }
            if tipo == "rb":
                info["altura_negra"] = arvore.altura_negra()
            resultado.append(info)
        return {
            "ordem": self.ordem,
            "n": n,
            "altura_minima": math.ceil(math.log2(n + 1)) if n else 0,
            "limite_avl": round(1.44 * math.log2(n + 2), 1) if n else 0,
            "limite_rb": round(2 * math.log2(n + 1), 1) if n else 0,
            "arvores": resultado,
        }

    def demonstracao(self, tipo="avl", quantidade=15, ordem="ordenada", semente=None):
        """Constrói do zero uma árvore pequena e devolve todos os passos."""
        classes = {"avl": ArvoreAVL, "rb": ArvoreRubroNegra, "bst": ArvoreBST}
        arvore = classes[tipo]()
        lista = _ordenar(self.disciplinas, ordem, semente)[:max(1, min(quantidade, 40))]
        passos = []
        arvore.ao_passo = passos.append
        for d in lista:
            arvore._emitir("info", f"Inserindo {d['codigo']} — {d['nome']}",
                           destaque=[], com_arvore=False)
            arvore.inserir(d)
        arvore.ao_passo = None
        return passos, arvore


# ----------------------------------------------------------------------------
# Funções chamadas pelo JavaScript (entrada e saída em JSON).
# ----------------------------------------------------------------------------
_sistema = None


def _s():
    global _sistema
    if _sistema is None:
        _sistema = SistemaArvores()
    return _sistema


def _json(obj):
    return json.dumps(obj, ensure_ascii=False)


def estado():
    s = _s()
    return _json({"avl": s.avl.to_dict(), "rb": s.rb.to_dict(), "bst": s.bst.to_dict(),
                  "metricas": s.metricas()})


def disciplina(codigo):
    return _json(_s().avl.buscar(codigo.strip().upper())[0])


def buscar_codigo(codigo, tipo="avl"):
    d, caminho = _s().buscar_codigo(codigo, tipo)
    return _json({"resultado": d, "caminho": caminho})


def buscar_prefixo(texto):
    resultados, visitados = _s().buscar_prefixo(texto)
    return _json({"resultados": resultados, "visitados": visitados})


def buscar_faixa(inicio, fim):
    resultados, visitados = _s().buscar_faixa(inicio, fim)
    return _json({"resultados": resultados, "visitados": visitados})


def buscar_professor(nome):
    return _json({"resultados": _s().buscar_professor(nome)})


def listar(tipo="avl"):
    return _json(_s().arvores[tipo].em_ordem())


def inserir(dados_json):
    try:
        d, nova, passos = _s().inserir(json.loads(dados_json))
    except ValueError as erro:
        return _json({"erro": str(erro)})
    return _json({"disciplina": d, "nova": nova, "passos": passos})


def remover(codigo):
    d, passos = _s().remover(codigo)
    if d is None:
        return _json({"erro": f"Disciplina {codigo} não encontrada."})
    return _json({"disciplina": d, "passos": passos})


def reconstruir(ordem="json"):
    _s().reconstruir(ordem)
    return estado()


def demonstracao(tipo="avl", quantidade=15, ordem="ordenada"):
    passos, _ = _s().demonstracao(tipo, int(quantidade), ordem)
    return _json({"passos": passos})
