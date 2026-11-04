"""Regras do Fuga Lógica: distância, tempo, níveis, vitória e derrota.

O tempo é medido aqui, no Python: ele começa quando o sinal é entregue ao
navegador e termina quando a resposta chega. O navegador apenas mostra o
que o servidor decide.
"""

import json
import random
import time
from pathlib import Path

import logica

PASTA_DADOS = Path(__file__).parent / "dados"


def carregar_config():
    with open(PASTA_DADOS / "config.json", encoding="utf-8") as arquivo:
        return json.load(arquivo)


def carregar_banco():
    with open(PASTA_DADOS / "proposicoes.json", encoding="utf-8") as arquivo:
        return json.load(arquivo)["sinais"]


# ---------------------------------------------------------------------------
# Correção dos sinais (usa o motor lógico)
# ---------------------------------------------------------------------------

def _opcao_correta(sinal, texto):
    criterio = sinal.get("criterio")
    if sinal["tipo"] == "argumento":
        return logica.argumento_valido(sinal["premissas"], texto)
    if criterio == "tautologia":
        return logica.e_tautologia(texto)
    if criterio == "contradicao":
        return logica.e_contradicao(texto)
    if criterio == "equivalente":
        return logica.equivalentes(sinal["referencia"], texto)
    raise ValueError(f"Critério desconhecido no sinal {sinal['id']}: {criterio}")


def opcoes_corretas(sinal):
    """Índices das opções corretas de um sinal de escolha ou de argumento."""
    return [i for i, texto in enumerate(sinal["opcoes"]) if _opcao_correta(sinal, texto)]


def solucoes_satisfazer(sinal):
    """Todas as atribuições das variáveis livres que tornam a fórmula verdadeira."""
    fixas = {v: val for v, val in sinal["variaveis"].items() if val is not None}
    livres = [v for v, val in sinal["variaveis"].items() if val is None]
    return [
        linha
        for linha in logica.atribuicoes(livres)
        if logica.avaliar(sinal["formula"], {**fixas, **linha})
    ]


# ---------------------------------------------------------------------------
# Partida
# ---------------------------------------------------------------------------

class Partida:
    def __init__(self, config, banco, relogio=time.monotonic, sorteio=None):
        self.config = config
        self.banco = banco
        self.relogio = relogio
        self.sorteio = sorteio or random.Random()

        self.distancia = float(config["distancia_inicial"])
        self.nivel = 1
        self.resolvidos = 0
        self.erros = 0
        self.situacao = "jogando"  # jogando | vitoria | derrota

        self.sinal = None
        self.ordem = []  # ordem embaralhada das opções mostradas
        self.inicio_sinal = None
        self.ultimo_desconto = None
        self._usados = set()

    # -- tempo -------------------------------------------------------------

    def _descontar_tempo(self, agora):
        """Enquanto o carro está parado, a viatura se aproxima."""
        if self.sinal is None or self.situacao != "jogando":
            return
        decorrido = agora - self.ultimo_desconto
        self.ultimo_desconto = agora
        self.distancia -= decorrido * self.config["aproximacao_m_por_s"]
        if self.distancia <= 0:
            self.distancia = 0
            self.situacao = "derrota"

    def _bonus(self, segundos, nivel):
        extra = self.config["acrescimo_tempo_por_nivel"] * (nivel - 1)
        for faixa in self.config["bonus_por_tempo"]:
            if segundos <= faixa["ate_segundos"] + extra:
                return faixa["metros"]
        return 0

    # -- sinais ------------------------------------------------------------

    def _sortear_sinal(self):
        candidatos = [s for s in self.banco if s["nivel"] == self.nivel]
        novos = [s for s in candidatos if s["id"] not in self._usados]
        if not novos:  # acabaram os sinais do nível: recomeça a fila
            self._usados -= {s["id"] for s in candidatos}
            novos = candidatos
        escolhido = self.sorteio.choice(novos)
        self._usados.add(escolhido["id"])
        return escolhido

    def proximo_sinal(self):
        """Entrega o sinal atual (sorteia um novo se não houver) e inicia o cronômetro."""
        if self.situacao != "jogando":
            return None
        if self.sinal is None:
            self.sinal = self._sortear_sinal()
            self.ordem = list(range(len(self.sinal.get("opcoes", []))))
            self.sorteio.shuffle(self.ordem)
            self.inicio_sinal = self.ultimo_desconto = self.relogio()
        return self._publico()

    def _publico(self):
        """Dados do sinal que o navegador pode ver (nunca a resposta)."""
        s = self.sinal
        dados = {
            "id": s["id"],
            "nivel": s["nivel"],
            "tipo": s["tipo"],
            "enunciado": s["enunciado"],
        }
        if s["tipo"] == "satisfazer":
            dados["formula"] = logica.formatar(s["formula"])
            dados["variaveis"] = [
                {"nome": nome, "valor": valor, "livre": valor is None}
                for nome, valor in s["variaveis"].items()
            ]
        else:
            if "referencia" in s:
                dados["referencia"] = logica.formatar(s["referencia"])
            if "premissas" in s:
                dados["premissas"] = [logica.formatar(p) for p in s["premissas"]]
            dados["opcoes"] = [logica.formatar(s["opcoes"][i]) for i in self.ordem]
        return dados

    # -- estado ------------------------------------------------------------

    def atualizar(self):
        """Aplica o tempo que passou e devolve o estado atual."""
        self._descontar_tempo(self.relogio())
        return self.estado()

    def estado(self):
        segundos = 0.0
        bonus = 0
        if self.sinal is not None and self.situacao == "jogando":
            segundos = self.relogio() - self.inicio_sinal
            bonus = self._bonus(segundos, self.sinal["nivel"])
        return {
            "situacao": self.situacao,
            "distancia": round(self.distancia, 1),
            "meta": self.config["meta_vitoria"],
            "nivel": self.nivel,
            "resolvidos": self.resolvidos,
            "erros": self.erros,
            "segundos_no_sinal": round(segundos, 1),
            "bonus_atual": bonus,
        }

    # -- resposta ----------------------------------------------------------

    def responder(self, valores=None, escolha=None):
        if self.situacao != "jogando" or self.sinal is None:
            raise RuntimeError("Não há sinal aguardando resposta.")

        agora = self.relogio()
        self._descontar_tempo(agora)
        if self.situacao == "derrota":
            return self._resultado(False, "A viatura te alcançou enquanto você pensava.")

        correto, explicacao = self._corrigir(valores, escolha)

        if not correto:
            self.erros += 1
            self.distancia -= self.config["penalidade_erro"]
            if self.distancia <= 0:
                self.distancia = 0
                self.situacao = "derrota"
            return self._resultado(False, explicacao)

        bonus = self._bonus(agora - self.inicio_sinal, self.sinal["nivel"])
        self.distancia += bonus
        self.resolvidos += 1
        self.nivel = min(
            self.config["nivel_maximo"],
            1 + self.resolvidos // self.config["sinais_por_nivel"],
        )
        self.sinal = None
        if self.distancia >= self.config["meta_vitoria"]:
            self.situacao = "vitoria"
        texto = f"Sinal aberto! +{bonus} m" if bonus else "Sinal aberto, mas sem bônus de tempo."
        return self._resultado(True, texto, bonus)

    def _resultado(self, correto, mensagem, bonus=0):
        return {
            "correto": correto,
            "mensagem": mensagem,
            "bonus": bonus,
            "estado": self.estado(),
        }

    def _corrigir(self, valores, escolha):
        s = self.sinal
        if s["tipo"] == "satisfazer":
            return self._corrigir_satisfazer(valores)
        return self._corrigir_escolha(escolha)

    def _corrigir_satisfazer(self, valores):
        s = self.sinal
        valores = valores or {}
        atribuicao = {}
        for nome, fixo in s["variaveis"].items():
            if fixo is not None:
                atribuicao[nome] = fixo
            else:
                if not isinstance(valores.get(nome), bool):
                    raise ValueError(f"Falta o valor da variável {nome}.")
                atribuicao[nome] = valores[nome]
        if logica.avaliar(s["formula"], atribuicao):
            return True, ""
        return False, (
            f"Com {logica.descrever(atribuicao)}, a condição "
            f"{logica.formatar(s['formula'])} fica falsa."
        )

    def _corrigir_escolha(self, escolha):
        s = self.sinal
        if not isinstance(escolha, int) or not 0 <= escolha < len(self.ordem):
            raise ValueError("Escolha uma das opções.")
        texto = s["opcoes"][self.ordem[escolha]]
        if _opcao_correta(s, texto):
            return True, ""
        return False, self._explicar_erro(s, texto)

    @staticmethod
    def _explicar_erro(s, texto):
        mostrada = logica.formatar(texto)
        criterio = s.get("criterio")
        if s["tipo"] == "argumento":
            linha = logica.contraexemplo_argumento(s["premissas"], texto)
            return (
                f"Com {logica.descrever(linha)}, as premissas são verdadeiras "
                f"e {mostrada} é falsa: o argumento não é válido."
            )
        if criterio == "tautologia":
            linha = logica.linha_falsa(texto)
            return f"{mostrada} não é tautologia: com {logica.descrever(linha)} ela é falsa."
        if criterio == "contradicao":
            linha = next(l for l, r in logica.tabela_verdade(texto) if r)
            return f"{mostrada} não é contradição: com {logica.descrever(linha)} ela é verdadeira."
        linha = logica.contraexemplo_equivalencia(s["referencia"], texto)
        return f"{mostrada} não é equivalente: com {logica.descrever(linha)} os valores diferem."
