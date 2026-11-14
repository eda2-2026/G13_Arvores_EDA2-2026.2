"""Árvore AVL (Adelson-Velsky e Landis, 1962).

Invariante: em todo nó, |altura(esq) - altura(dir)| <= 1.
Após inserir ou remover, subimos pelo caminho até a raiz atualizando as
alturas; quando o fator de balanceamento vira +2 ou -2, aplicamos uma das
quatro rotações (LL, RR, LR, RL). Altura máxima ~ 1,44 * log2(n).
"""

from src.arvore_bst import ArvoreBST, No


class NoAVL(No):
    __slots__ = ("altura",)

    def __init__(self, chave, valor):
        super().__init__(chave, valor)
        self.altura = 1


def _alt(no):
    return no.altura if no is not None else 0


def _atualizar(no):
    no.altura = 1 + max(_alt(no.esq), _alt(no.dir))


def fator_balanceamento(no):
    return _alt(no.esq) - _alt(no.dir)


class ArvoreAVL(ArvoreBST):
    nome = "AVL"

    def _novo_no(self, chave, valor):
        return NoAVL(chave, valor)

    def _apos_rotacao(self, desceu, subiu):
        # O nó que desceu fica abaixo do que subiu: atualiza primeiro.
        _atualizar(desceu)
        _atualizar(subiu)

    def _apos_inserir(self, no):
        self._rebalancear(no.pai)

    def _apos_remover(self, inicio):
        self._rebalancear(inicio)

    def _rebalancear(self, no):
        while no is not None:
            _atualizar(no)
            fb = fator_balanceamento(no)
            if fb > 1:
                caso = "LL" if fator_balanceamento(no.esq) >= 0 else "LR"
                self._avisar_desbalanceamento(no, fb, caso)
                if caso == "LR":
                    self._rotacao_esquerda(no.esq)
                no = self._rotacao_direita(no)
            elif fb < -1:
                caso = "RR" if fator_balanceamento(no.dir) <= 0 else "RL"
                self._avisar_desbalanceamento(no, fb, caso)
                if caso == "RL":
                    self._rotacao_direita(no.dir)
                no = self._rotacao_esquerda(no)
            no = no.pai

    def _avisar_desbalanceamento(self, no, fb, caso):
        self._emitir("desbalanceado",
                     f"{self._id(no)} ficou com fator {fb:+d}: caso {caso}",
                     destaque=[self._id(no)], caso=caso)

    def altura(self):
        return _alt(self.raiz)

    def _info_no(self, no):
        return {"altura": no.altura, "fb": fator_balanceamento(no)}
