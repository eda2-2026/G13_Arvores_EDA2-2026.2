"""Árvore Rubro-Negra (Bayer 1972; Guibas e Sedgewick 1978).

Propriedades:
  1. Todo nó é vermelho ou preto.
  2. A raiz é preta.
  3. Folhas nulas (None) são pretas.
  4. Um nó vermelho não tem filho vermelho.
  5. Todo caminho de um nó até suas folhas nulas tem o mesmo número de
     nós pretos (altura negra).
Consequência: altura <= 2 * log2(n + 1). Faz menos rotações que a AVL
(no máximo 2 por inserção e 3 por remoção), mas a árvore fica um pouco mais alta.

Aqui a chave é o nome normalizado da disciplina, o que permite listar em
ordem alfabética e buscar por prefixo (autocompletar).
"""

from src.arvore_bst import ArvoreBST, No
from src.normaliza import normalizar

VERMELHO = "vermelho"
PRETO = "preto"


class NoRB(No):
    __slots__ = ("cor",)

    def __init__(self, chave, valor):
        super().__init__(chave, valor)
        self.cor = VERMELHO


def _cor(no):
    return no.cor if no is not None else PRETO


def chave_por_nome(disciplina):
    # O código desempata nomes iguais e mantém as chaves únicas.
    return (normalizar(disciplina["nome"]), disciplina["codigo"])


class ArvoreRubroNegra(ArvoreBST):
    nome = "Rubro-Negra"

    def __init__(self, chave=chave_por_nome, ao_passo=None):
        super().__init__(chave=chave, ao_passo=ao_passo)

    def _novo_no(self, chave, valor):
        return NoRB(chave, valor)

    def _pintar(self, no, cor, motivo=""):
        if no is not None and no.cor != cor:
            no.cor = cor
            self.recoloracoes += 1
            self._emitir("recolorir", f"{self._id(no)} fica {cor}" +
                         (f" ({motivo})" if motivo else ""),
                         destaque=[self._id(no)], cor=cor)

    # --------------------------------------------------------------- inserção
    def _apos_inserir(self, z):
        while _cor(z.pai) == VERMELHO:
            pai = z.pai
            avo = pai.pai
            if pai is avo.esq:
                tio = avo.dir
                if _cor(tio) == VERMELHO:
                    # Caso 1: tio vermelho, então recolore e sobe o problema.
                    self._pintar(pai, PRETO, "caso 1: tio vermelho")
                    self._pintar(tio, PRETO, "caso 1: tio vermelho")
                    self._pintar(avo, VERMELHO, "caso 1: tio vermelho")
                    z = avo
                    continue
                if z is pai.dir:
                    # Caso 2: triângulo, que vira linha com uma rotação.
                    z = pai
                    self._rotacao_esquerda(z)
                    pai = z.pai
                # Caso 3: linha, então rotaciona o avô e troca as cores.
                self._pintar(pai, PRETO, "caso 3")
                self._pintar(avo, VERMELHO, "caso 3")
                self._rotacao_direita(avo)
            else:
                tio = avo.esq
                if _cor(tio) == VERMELHO:
                    self._pintar(pai, PRETO, "caso 1: tio vermelho")
                    self._pintar(tio, PRETO, "caso 1: tio vermelho")
                    self._pintar(avo, VERMELHO, "caso 1: tio vermelho")
                    z = avo
                    continue
                if z is pai.esq:
                    z = pai
                    self._rotacao_direita(z)
                    pai = z.pai
                self._pintar(pai, PRETO, "caso 3")
                self._pintar(avo, VERMELHO, "caso 3")
                self._rotacao_esquerda(avo)
        self._pintar(self.raiz, PRETO, "a raiz é sempre preta")

    # ---------------------------------------------------------------- remoção
    def remover(self, chave):
        z = self._achar(chave)
        if z is None:
            return False
        removido = self._id(z)
        cor_retirada = z.cor
        if z.esq is None:
            x, x_pai = z.dir, z.pai
            self._transplantar(z, z.dir)
        elif z.dir is None:
            x, x_pai = z.esq, z.pai
            self._transplantar(z, z.esq)
        else:
            y = self._minimo_no(z.dir)
            cor_retirada = y.cor
            x = y.dir
            if y.pai is z:
                x_pai = y
            else:
                x_pai = y.pai
                self._transplantar(y, y.dir)
                y.dir = z.dir
                y.dir.pai = y
            self._transplantar(z, y)
            y.esq = z.esq
            y.esq.pai = y
            y.cor = z.cor
        self.tamanho -= 1
        self._emitir("remocao", f"{removido} removido")
        if cor_retirada == PRETO:
            self._corrigir_remocao(x, x_pai)
        self._emitir("fim", "Remoção concluída")
        return True

    def _corrigir_remocao(self, x, pai):
        # x carrega um "preto extra" que precisa ser eliminado.
        while x is not self.raiz and _cor(x) == PRETO:
            if x is pai.esq:
                irmao = pai.dir
                if _cor(irmao) == VERMELHO:
                    self._pintar(irmao, PRETO, "irmão vermelho")
                    self._pintar(pai, VERMELHO, "irmão vermelho")
                    self._rotacao_esquerda(pai)
                    irmao = pai.dir
                if _cor(irmao.esq) == PRETO and _cor(irmao.dir) == PRETO:
                    self._pintar(irmao, VERMELHO, "sobrinhos pretos")
                    x, pai = pai, pai.pai
                else:
                    if _cor(irmao.dir) == PRETO:
                        self._pintar(irmao.esq, PRETO, "sobrinho próximo vermelho")
                        self._pintar(irmao, VERMELHO, "sobrinho próximo vermelho")
                        self._rotacao_direita(irmao)
                        irmao = pai.dir
                    self._pintar(irmao, pai.cor, "sobrinho distante vermelho")
                    self._pintar(pai, PRETO, "sobrinho distante vermelho")
                    self._pintar(irmao.dir, PRETO, "sobrinho distante vermelho")
                    self._rotacao_esquerda(pai)
                    x, pai = self.raiz, None
            else:
                irmao = pai.esq
                if _cor(irmao) == VERMELHO:
                    self._pintar(irmao, PRETO, "irmão vermelho")
                    self._pintar(pai, VERMELHO, "irmão vermelho")
                    self._rotacao_direita(pai)
                    irmao = pai.esq
                if _cor(irmao.esq) == PRETO and _cor(irmao.dir) == PRETO:
                    self._pintar(irmao, VERMELHO, "sobrinhos pretos")
                    x, pai = pai, pai.pai
                else:
                    if _cor(irmao.esq) == PRETO:
                        self._pintar(irmao.dir, PRETO, "sobrinho próximo vermelho")
                        self._pintar(irmao, VERMELHO, "sobrinho próximo vermelho")
                        self._rotacao_esquerda(irmao)
                        irmao = pai.esq
                    self._pintar(irmao, pai.cor, "sobrinho distante vermelho")
                    self._pintar(pai, PRETO, "sobrinho distante vermelho")
                    self._pintar(irmao.esq, PRETO, "sobrinho distante vermelho")
                    self._rotacao_direita(pai)
                    x, pai = self.raiz, None
        self._pintar(x, PRETO, "elimina o preto extra")

    # ------------------------------------------------------------------ busca
    def prefixo(self, texto):
        """Disciplinas cujo nome normalizado começa com `texto`."""
        p = normalizar(texto)
        return self.faixa((p, ""), (p + "￿", ""))

    def altura_negra(self):
        h, no = 0, self.raiz
        while no is not None:
            if no.cor == PRETO:
                h += 1
            no = no.esq
        return h

    def _rotulo(self, no):
        return no.valor["nome"]

    def _info_no(self, no):
        return {"cor": no.cor}
