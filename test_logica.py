"""Testes do motor lógico.  Rode na pasta do projeto:  python -m unittest discover tests"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import logica as L


class TestConectivos(unittest.TestCase):
    def test_tabelas_dos_conectivos(self):
        for a in (True, False):
            self.assertEqual(L.nao(a), not a)
            for b in (True, False):
                self.assertEqual(L.e(a, b), a and b)
                self.assertEqual(L.ou(a, b), a or b)
                self.assertEqual(L.bicondicional(a, b), a == b)
        # a condicional só é falsa em V -> F
        self.assertFalse(L.implica(True, False))
        self.assertTrue(L.implica(True, True))
        self.assertTrue(L.implica(False, True))
        self.assertTrue(L.implica(False, False))


class TestAvaliacao(unittest.TestCase):
    def test_exemplo_do_documento(self):
        # (P & ~Q) -> R com P = V, Q = F exige R = V
        valores = {"P": True, "Q": False}
        self.assertTrue(L.avaliar("(P & ~Q) -> R", {**valores, "R": True}))
        self.assertFalse(L.avaliar("(P & ~Q) -> R", {**valores, "R": False}))

    def test_precedencia_e_associatividade(self):
        # & vem antes de |
        self.assertTrue(L.avaliar("P | Q & R", {"P": True, "Q": False, "R": False}))
        # -> associa à direita: P -> (Q -> R)
        self.assertEqual(
            L.ler_formula("P -> Q -> R"),
            ("imp", ("var", "P"), ("imp", ("var", "Q"), ("var", "R"))),
        )

    def test_tabela_verdade_tem_2_elevado_a_n_linhas(self):
        self.assertEqual(len(L.tabela_verdade("P & Q")), 4)
        self.assertEqual(len(L.tabela_verdade("(P & Q) -> R")), 8)

    def test_formulas_invalidas(self):
        for texto in ("P &", "(P | Q", "P Q", "P $ Q", "", "->P"):
            with self.assertRaises(L.ErroDeFormula, msg=texto):
                L.ler_formula(texto)

    def test_codigo_python_nao_e_executado(self):
        with self.assertRaises(L.ErroDeFormula):
            L.avaliar("__import__('os')", {})


class TestClassificacao(unittest.TestCase):
    def test_tautologias(self):
        for f in ("P | ~P", "(P & Q) -> P", "(P -> Q) | (Q -> P)", "P -> P"):
            self.assertEqual(L.classificar(f), "tautologia", f)

    def test_contradicoes(self):
        for f in ("P & ~P", "~(P | ~P)", "P <-> ~P"):
            self.assertEqual(L.classificar(f), "contradicao", f)

    def test_contingencias(self):
        for f in ("P & Q", "P -> ~P", "P <-> Q"):
            self.assertEqual(L.classificar(f), "contingencia", f)


class TestEquivalenciasEArgumentos(unittest.TestCase):
    def test_de_morgan(self):
        self.assertTrue(L.equivalentes("~(P & Q)", "~P | ~Q"))
        self.assertTrue(L.equivalentes("~(P | Q)", "~P & ~Q"))
        self.assertFalse(L.equivalentes("~(P & Q)", "~P & ~Q"))

    def test_contrapositiva_e_condicional(self):
        self.assertTrue(L.equivalentes("P -> Q", "~Q -> ~P"))
        self.assertTrue(L.equivalentes("P -> Q", "~P | Q"))
        self.assertFalse(L.equivalentes("P -> Q", "Q -> P"))

    def test_regras_de_inferencia(self):
        self.assertTrue(L.argumento_valido(["P -> Q", "P"], "Q"))          # modus ponens
        self.assertTrue(L.argumento_valido(["P -> Q", "~Q"], "~P"))        # modus tollens
        self.assertTrue(L.argumento_valido(["P -> Q", "Q -> R"], "P -> R"))  # silogismo hipotético
        self.assertTrue(L.argumento_valido(["P | Q", "~P"], "Q"))          # silogismo disjuntivo

    def test_falacias_nao_sao_validas(self):
        self.assertFalse(L.argumento_valido(["P -> Q", "Q"], "P"))   # afirmação do consequente
        self.assertFalse(L.argumento_valido(["P -> Q", "~P"], "~Q"))  # negação do antecedente


class TestApresentacao(unittest.TestCase):
    def test_simbolos(self):
        self.assertEqual(L.formatar("(P & ~Q) <-> R"), "(P ∧ ¬Q) ↔ R")
        self.assertEqual(L.formatar("P -> Q | R"), "P → Q ∨ R")


if __name__ == "__main__":
    unittest.main()
