"""Testes do banco de proposições e das regras do jogo."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import jogo
import logica

CONFIG = jogo.carregar_config()
VEL = CONFIG["aproximacao_m_por_s"]
BANCO = jogo.carregar_banco()


class Relogio:
    """Relógio falso para controlar o tempo nos testes."""

    def __init__(self):
        self.t = 100.0

    def __call__(self):
        return self.t

    def passar(self, segundos):
        self.t += segundos


class TestBancoDeProposicoes(unittest.TestCase):
    def test_todo_nivel_tem_sinais(self):
        for nivel in range(1, CONFIG["nivel_maximo"] + 1):
            self.assertTrue([s for s in BANCO if s["nivel"] == nivel], f"nível {nivel} vazio")

    def test_ids_sao_unicos(self):
        ids = [s["id"] for s in BANCO]
        self.assertEqual(len(ids), len(set(ids)))

    def test_todo_sinal_tem_solucao_e_nao_e_trivial(self):
        for s in BANCO:
            with self.subTest(sinal=s["id"]):
                if s["tipo"] == "satisfazer":
                    logica.ler_formula(s["formula"])
                    solucoes = jogo.solucoes_satisfazer(s)
                    self.assertGreaterEqual(len(solucoes), 1, "sinal impossível")
                    livres = [v for v, val in s["variaveis"].items() if val is None]
                    total = 2 ** len(livres)
                    self.assertLess(len(solucoes), total, "qualquer resposta abre o sinal")
                else:
                    certas = jogo.opcoes_corretas(s)
                    self.assertGreaterEqual(len(certas), 1, "nenhuma opção correta")
                    self.assertLess(len(certas), len(s["opcoes"]), "todas as opções corretas")


def nova_partida(**mudancas):
    config = {**CONFIG, **mudancas}
    relogio = Relogio()
    return jogo.Partida(config, BANCO, relogio=relogio), relogio


def resposta_certa(partida):
    """Descobre a resposta correta do sinal atual (só para testes)."""
    s = partida.sinal
    if s["tipo"] == "satisfazer":
        return {"valores": jogo.solucoes_satisfazer(s)[0]}
    certas = jogo.opcoes_corretas(s)
    texto = s["opcoes"][certas[0]]
    return {"escolha": next(i for i, o in enumerate(partida.ordem) if s["opcoes"][o] == texto)}


def resposta_errada(partida):
    s = partida.sinal
    if s["tipo"] == "satisfazer":
        livres = [v for v, val in s["variaveis"].items() if val is None]
        solucoes = jogo.solucoes_satisfazer(s)
        for linha in logica.atribuicoes(livres):
            if linha not in solucoes:
                return {"valores": linha}
    certas = jogo.opcoes_corretas(s)
    return {"escolha": next(i for i, o in enumerate(partida.ordem) if o not in certas)}


class TestRegras(unittest.TestCase):
    def test_acerto_rapido_da_bonus_e_desconta_o_tempo(self):
        p, relogio = nova_partida()
        p.proximo_sinal()
        relogio.passar(4)  # 4 s parado, bônus +30 m
        r = p.responder(**resposta_certa(p))
        self.assertTrue(r["correto"])
        self.assertEqual(r["bonus"], 30)
        self.assertAlmostEqual(p.distancia, 60 - 4 * VEL + 30)

    def test_acerto_lento_da_bonus_menor(self):
        p, relogio = nova_partida()
        p.proximo_sinal()
        relogio.passar(9)  # 9 s parado, bônus +15 m
        r = p.responder(**resposta_certa(p))
        self.assertEqual(r["bonus"], 15)
        self.assertAlmostEqual(p.distancia, 60 - 9 * VEL + 15)

    def test_erro_custa_penalidade_e_o_sinal_continua_fechado(self):
        p, relogio = nova_partida()
        p.proximo_sinal()
        relogio.passar(2)  # 2 s parado
        r = p.responder(**resposta_errada(p))
        self.assertFalse(r["correto"])
        self.assertTrue(r["mensagem"])
        self.assertAlmostEqual(p.distancia, 60 - 2 * VEL - 10)
        self.assertIsNotNone(p.sinal)
        self.assertEqual(p.erros, 1)

    def test_derrota_quando_a_viatura_alcanca(self):
        p, relogio = nova_partida()
        p.proximo_sinal()
        relogio.passar(60 / VEL + 1)  # a viatura percorre mais de 60 m
        estado = p.atualizar()
        self.assertEqual(estado["situacao"], "derrota")
        self.assertEqual(estado["distancia"], 0)

    def test_derrota_por_erros_seguidos(self):
        p, _ = nova_partida(distancia_inicial=15)
        p.proximo_sinal()
        p.responder(**resposta_errada(p))
        self.assertEqual(p.situacao, "jogando")
        p.responder(**resposta_errada(p))
        self.assertEqual(p.situacao, "derrota")

    def test_vitoria_ao_atingir_a_meta(self):
        p, _ = nova_partida(distancia_inicial=140)
        p.proximo_sinal()
        r = p.responder(**resposta_certa(p))
        self.assertEqual(r["estado"]["situacao"], "vitoria")
        self.assertGreaterEqual(p.distancia, 150)

    def test_nivel_sobe_a_cada_grupo_de_sinais(self):
        p, _ = nova_partida(distancia_inicial=10_000, meta_vitoria=10**9)
        niveis = []
        for _ in range(6):
            p.proximo_sinal()
            niveis.append(p.sinal["nivel"])
            p.responder(**resposta_certa(p))
        self.assertEqual(niveis, [1, 1, 2, 2, 3, 3])

    def test_nivel_nunca_passa_do_maximo(self):
        p, _ = nova_partida(distancia_inicial=10_000, meta_vitoria=10**9)
        for _ in range(14):
            p.proximo_sinal()
            p.responder(**resposta_certa(p))
        self.assertEqual(p.nivel, CONFIG["nivel_maximo"])
        p.proximo_sinal()
        self.assertEqual(p.sinal["nivel"], CONFIG["nivel_maximo"])

    def test_tempo_do_bonus_cresce_com_o_nivel(self):
        p, _ = nova_partida()
        self.assertEqual(p._bonus(6, 1), 15)
        self.assertEqual(p._bonus(6, 2), 30)  # nível 2 ganha 3 s extras

    def test_resposta_invalida_e_rejeitada(self):
        p, _ = nova_partida()
        p.proximo_sinal()
        with self.assertRaises(ValueError):
            p.responder(escolha=99) if p.sinal["tipo"] != "satisfazer" else p.responder(valores={})

    def test_sinal_publico_nao_revela_a_resposta(self):
        p, _ = nova_partida(distancia_inicial=10_000, meta_vitoria=10**9)
        for _ in range(10):
            dados = p.proximo_sinal()
            texto = str(dados)
            for chave in ("criterio", "correta", "solucao", "gabarito"):
                self.assertNotIn(chave, texto)
            p.responder(**resposta_certa(p))

    def test_proximo_sinal_e_idempotente(self):
        p, _ = nova_partida()
        a = p.proximo_sinal()
        b = p.proximo_sinal()
        self.assertEqual(a, b)


if __name__ == "__main__":
    unittest.main()
