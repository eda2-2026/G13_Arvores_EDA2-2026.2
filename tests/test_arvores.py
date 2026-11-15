import math
import random
import unittest

from src.carregaDados import carregar_disciplinas
from src.arvore_bst import ArvoreBST
from src.arvore_avl import ArvoreAVL, fator_balanceamento

DISCIPLINAS = carregar_disciplinas()


def verificar_ordem(teste, arvore):
    chaves = [arvore.chave_de(d) for d in arvore.em_ordem()]
    teste.assertEqual(chaves, sorted(chaves))
    teste.assertEqual(len(chaves), arvore.tamanho)


def verificar_pais(teste, no):
    if no is None:
        return
    for filho in (no.esq, no.dir):
        if filho is not None:
            teste.assertIs(filho.pai, no)
            verificar_pais(teste, filho)


class TesteBST(unittest.TestCase):
    def test_entrada_ordenada_degenera(self):
        bst = ArvoreBST()
        for d in sorted(DISCIPLINAS, key=lambda d: d["codigo"]):
            bst.inserir(d)
        self.assertEqual(bst.altura(), len(DISCIPLINAS))
        verificar_ordem(self, bst)


class TesteAVL(unittest.TestCase):
    def verificar_avl(self, avl):
        def checar(no):
            if no is None:
                return 0
            he, hd = checar(no.esq), checar(no.dir)
            self.assertLessEqual(abs(he - hd), 1)
            self.assertEqual(no.altura, 1 + max(he, hd))
            self.assertEqual(fator_balanceamento(no), he - hd)
            return 1 + max(he, hd)

        checar(avl.raiz)
        verificar_ordem(self, avl)
        verificar_pais(self, avl.raiz)
        if avl.tamanho:
            self.assertIsNone(avl.raiz.pai)
            self.assertLessEqual(avl.altura(), 1.45 * math.log2(avl.tamanho + 2))

    def test_insercao_em_varias_ordens(self):
        ordens = [list(DISCIPLINAS), sorted(DISCIPLINAS, key=lambda d: d["codigo"]),
                  sorted(DISCIPLINAS, key=lambda d: d["codigo"], reverse=True)]
        for ordem in ordens:
            avl = ArvoreAVL()
            for d in ordem:
                self.assertTrue(avl.inserir(d))
            self.verificar_avl(avl)

    def test_remocao_e_reinsercao(self):
        rng = random.Random(42)
        avl = ArvoreAVL()
        for d in DISCIPLINAS:
            avl.inserir(d)
        removidas = rng.sample(DISCIPLINAS, len(DISCIPLINAS) // 2)
        for d in removidas:
            self.assertTrue(avl.remover(d["codigo"]))
            self.verificar_avl(avl)
        self.assertFalse(avl.remover("XXX0000"))
        for d in removidas:
            avl.inserir(d)
        self.verificar_avl(avl)
        self.assertEqual(avl.tamanho, len(DISCIPLINAS))

    def test_busca_e_faixa(self):
        avl = ArvoreAVL()
        for d in DISCIPLINAS:
            avl.inserir(d)
        for d in DISCIPLINAS:
            achada, caminho = avl.buscar(d["codigo"])
            self.assertIs(achada, d)
            self.assertLessEqual(len(caminho), avl.altura())
        self.assertIsNone(avl.buscar("ZZZ9999")[0])
        faixa, _ = avl.faixa("FGA0100", "FGA0200")
        esperado = sorted(d["codigo"] for d in DISCIPLINAS
                          if "FGA0100" <= d["codigo"] < "FGA0200")
        self.assertEqual([d["codigo"] for d in faixa], esperado)

    def test_passos_registram_rotacoes(self):
        passos = []
        avl = ArvoreAVL(ao_passo=passos.append)
        for d in sorted(DISCIPLINAS, key=lambda d: d["codigo"])[:3]:
            avl.inserir(d)
        tipos = [p["tipo"] for p in passos]
        self.assertIn("desbalanceado", tipos)
        self.assertIn("rotacao", tipos)
        self.assertEqual(avl.rotacoes, 1)


if __name__ == "__main__":
    unittest.main()


from src.arvore_rubro_negra import ArvoreRubroNegra, VERMELHO, PRETO  # noqa: E402


class TesteRubroNegra(unittest.TestCase):
    def verificar_rb(self, rb):
        self.assertEqual(rb.raiz.cor if rb.raiz else PRETO, PRETO)

        def altura_negra(no):
            if no is None:
                return 1
            if no.cor == VERMELHO:
                for filho in (no.esq, no.dir):
                    self.assertTrue(filho is None or filho.cor == PRETO)
            he, hd = altura_negra(no.esq), altura_negra(no.dir)
            self.assertEqual(he, hd)
            return he + (1 if no.cor == PRETO else 0)

        altura_negra(rb.raiz)
        verificar_ordem(self, rb)
        verificar_pais(self, rb.raiz)
        if rb.tamanho:
            self.assertLessEqual(rb.altura(), 2 * math.log2(rb.tamanho + 1))

    def test_insercao_em_varias_ordens(self):
        for ordem in (list(DISCIPLINAS), sorted(DISCIPLINAS, key=lambda d: d["nome"])):
            rb = ArvoreRubroNegra()
            for d in ordem:
                rb.inserir(d)
            self.verificar_rb(rb)

    def test_remocao_e_reinsercao(self):
        for semente in range(5):
            rng = random.Random(semente)
            rb = ArvoreRubroNegra()
            for d in DISCIPLINAS:
                rb.inserir(d)
            removidas = rng.sample(DISCIPLINAS, len(DISCIPLINAS) * 3 // 4)
            for d in removidas:
                self.assertTrue(rb.remover(rb.chave_de(d)))
                self.verificar_rb(rb)
            for d in removidas:
                rb.inserir(d)
            self.verificar_rb(rb)
            self.assertEqual(rb.tamanho, len(DISCIPLINAS))

    def test_prefixo(self):
        rb = ArvoreRubroNegra()
        for d in DISCIPLINAS:
            rb.inserir(d)
        for termo in ("calc", "Introdução", "e", "zzz"):
            achadas, _ = rb.prefixo(termo)
            from src.normaliza import normalizar
            esperado = sorted((d for d in DISCIPLINAS
                               if normalizar(d["nome"]).startswith(normalizar(termo))),
                              key=lambda d: (normalizar(d["nome"]), d["codigo"]))
            self.assertEqual(achadas, esperado)
