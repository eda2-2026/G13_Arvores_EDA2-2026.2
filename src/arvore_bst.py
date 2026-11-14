"""Árvore Binária de Busca (BST) simples, sem balanceamento.

Serve de base para a AVL e a Rubro-Negra: as duas reaproveitam a busca,
a inserção "descendo pela árvore", as rotações e a serialização daqui,
e acrescentam apenas as suas regras de balanceamento.
"""


class No:
    __slots__ = ("chave", "valor", "esq", "dir", "pai")

    def __init__(self, chave, valor):
        self.chave = chave
        self.valor = valor
        self.esq = None
        self.dir = None
        self.pai = None


class ArvoreBST:
    nome = "BST simples"

    def __init__(self, chave=lambda d: d["codigo"], ao_passo=None):
        self.raiz = None
        self.tamanho = 0
        self._chave = chave
        # Callback opcional que recebe cada passo (mesmo padrão do quick_sort).
        self.ao_passo = ao_passo
        self.rotacoes = 0
        self.recoloracoes = 0
        self.comparacoes = 0

    # ------------------------------------------------------------ utilidades
    def chave_de(self, disciplina):
        return self._chave(disciplina)

    def _novo_no(self, chave, valor):
        return No(chave, valor)

    @staticmethod
    def _id(no):
        return no.valor["codigo"]

    def _emitir(self, tipo, descricao="", destaque=(), com_arvore=True, **extra):
        if self.ao_passo is None:
            return
        passo = {"tipo": tipo, "descricao": descricao, "destaque": list(destaque)}
        passo.update(extra)
        if com_arvore:
            passo["arvore"] = self.to_dict()
        self.ao_passo(passo)

    def _transplantar(self, u, v):
        """Coloca a subárvore v no lugar de u (ligação com o pai de u)."""
        if u.pai is None:
            self.raiz = v
        elif u is u.pai.esq:
            u.pai.esq = v
        else:
            u.pai.dir = v
        if v is not None:
            v.pai = u.pai

    @staticmethod
    def _minimo_no(no):
        while no.esq is not None:
            no = no.esq
        return no

    # --------------------------------------------------------------- rotações
    def _rotacao_esquerda(self, x):
        y = x.dir
        x.dir = y.esq
        if y.esq is not None:
            y.esq.pai = x
        self._transplantar(x, y)
        y.esq = x
        x.pai = y
        self.rotacoes += 1
        self._apos_rotacao(x, y)
        self._emitir("rotacao", f"Rotação à esquerda em {self._id(x)}: "
                     f"{self._id(y)} sobe", destaque=[self._id(x), self._id(y)],
                     direcao="esquerda")
        return y

    def _rotacao_direita(self, x):
        y = x.esq
        x.esq = y.dir
        if y.dir is not None:
            y.dir.pai = x
        self._transplantar(x, y)
        y.dir = x
        x.pai = y
        self.rotacoes += 1
        self._apos_rotacao(x, y)
        self._emitir("rotacao", f"Rotação à direita em {self._id(x)}: "
                     f"{self._id(y)} sobe", destaque=[self._id(x), self._id(y)],
                     direcao="direita")
        return y

    def _apos_rotacao(self, desceu, subiu):
        pass

    # --------------------------------------------------------------- inserção
    def inserir(self, disciplina):
        """Insere (ou atualiza) a disciplina. Retorna True se for nova."""
        chave = self.chave_de(disciplina)
        pai, atual = None, self.raiz
        while atual is not None:
            self._emitir("visita", f"Comparando com {self._id(atual)}",
                         destaque=[self._id(atual)], com_arvore=False)
            if chave == atual.chave:
                atual.valor = disciplina
                self._emitir("atualizacao", f"{self._id(atual)} já existia: dados atualizados",
                             destaque=[self._id(atual)])
                return False
            pai = atual
            atual = atual.esq if chave < atual.chave else atual.dir

        no = self._novo_no(chave, disciplina)
        no.pai = pai
        if pai is None:
            self.raiz = no
        elif chave < pai.chave:
            pai.esq = no
        else:
            pai.dir = no
        self.tamanho += 1
        self._emitir("insercao", f"{self._id(no)} inserido como folha",
                     destaque=[self._id(no)])
        self._apos_inserir(no)
        self._emitir("fim", "Inserção concluída", destaque=[self._id(no)])
        return True

    def _apos_inserir(self, no):
        pass

    # ---------------------------------------------------------------- remoção
    def remover(self, chave):
        z = self._achar(chave)
        if z is None:
            return False
        removido = self._id(z)
        if z.esq is None:
            inicio = z.pai
            self._transplantar(z, z.dir)
        elif z.dir is None:
            inicio = z.pai
            self._transplantar(z, z.esq)
        else:
            # Dois filhos: o sucessor (menor da subárvore direita) ocupa o lugar.
            y = self._minimo_no(z.dir)
            if y.pai is not z:
                inicio = y.pai
                self._transplantar(y, y.dir)
                y.dir = z.dir
                y.dir.pai = y
            else:
                inicio = y
            self._transplantar(z, y)
            y.esq = z.esq
            y.esq.pai = y
        self.tamanho -= 1
        self._emitir("remocao", f"{removido} removido", destaque=[])
        self._apos_remover(inicio)
        self._emitir("fim", "Remoção concluída")
        return True

    def _apos_remover(self, inicio):
        pass

    # ------------------------------------------------------------------ busca
    def _achar(self, chave):
        atual = self.raiz
        while atual is not None and atual.chave != chave:
            atual = atual.esq if chave < atual.chave else atual.dir
        return atual

    def buscar(self, chave):
        """Retorna (disciplina ou None, caminho de ids visitados)."""
        caminho = []
        atual = self.raiz
        while atual is not None:
            caminho.append(self._id(atual))
            self.comparacoes += 1
            if chave == atual.chave:
                return atual.valor, caminho
            atual = atual.esq if chave < atual.chave else atual.dir
        return None, caminho

    def faixa(self, inicio, fim):
        """Disciplinas com inicio <= chave < fim, em ordem, e os nós visitados.

        Subárvores inteiras fora do intervalo são podadas: O(log n + k).
        """
        resultado, visitados = [], []

        def percorrer(no):
            if no is None:
                return
            visitados.append(self._id(no))
            if inicio < no.chave:
                percorrer(no.esq)
            if inicio <= no.chave < fim:
                resultado.append(no.valor)
            if no.chave < fim:
                percorrer(no.dir)

        percorrer(self.raiz)
        return resultado, visitados

    def em_ordem(self):
        resultado = []

        def percorrer(no):
            if no is not None:
                percorrer(no.esq)
                resultado.append(no.valor)
                percorrer(no.dir)

        percorrer(self.raiz)
        return resultado

    def altura(self):
        def h(no):
            return 0 if no is None else 1 + max(h(no.esq), h(no.dir))
        return h(self.raiz)

    def profundidade_media(self):
        """Número médio de comparações para encontrar cada chave."""
        total = 0

        def somar(no, nivel):
            nonlocal total
            if no is not None:
                total += nivel
                somar(no.esq, nivel + 1)
                somar(no.dir, nivel + 1)

        somar(self.raiz, 1)
        return total / self.tamanho if self.tamanho else 0

    # ---------------------------------------------------------- serialização
    def _info_no(self, no):
        return {}

    def to_dict(self):
        def converter(no):
            if no is None:
                return None
            d = {
                "id": self._id(no),
                "rotulo": self._rotulo(no),
                "esq": converter(no.esq),
                "dir": converter(no.dir),
            }
            d.update(self._info_no(no))
            return d
        return converter(self.raiz)

    def _rotulo(self, no):
        return no.valor["codigo"]
