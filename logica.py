"""Motor lógico do Fuga Lógica.

Aqui ficam os conectivos da Lógica Proposicional e as operações que o jogo
usa para decidir se um sinal abre: avaliar fórmulas, montar tabelas-verdade,
classificar (tautologia, contradição, contingência), comparar equivalências
e verificar a validade de argumentos.

Sintaxe das fórmulas (ASCII, como aparecem nos arquivos JSON):

    ~   negação        (¬)
    &   conjunção      (∧)
    |   disjunção      (∨)
    ->  condicional    (→)
    <-> bicondicional  (↔)

Variáveis são letras maiúsculas isoladas (P, Q, R...). Precedência, da maior
para a menor: ~, &, |, ->, <->. Na dúvida, use parênteses.

Nenhuma fórmula é executada com eval(): o texto é lido por um analisador
próprio, então nada vindo do navegador vira código Python.
"""

from functools import lru_cache
from itertools import product


class ErroDeFormula(ValueError):
    """Fórmula escrita de forma inválida."""


# ---------------------------------------------------------------------------
# Conectivos
# ---------------------------------------------------------------------------

def nao(a):
    return not a


def e(a, b):
    return a and b


def ou(a, b):
    return a or b


def implica(a, b):
    """P -> Q só é falsa quando P é verdadeira e Q é falsa."""
    return (not a) or b


def bicondicional(a, b):
    """P <-> Q é verdadeira quando P e Q têm o mesmo valor."""
    return a == b


# ---------------------------------------------------------------------------
# Leitura da fórmula (analisador descendente recursivo)
#
#   bic  := imp ('<->' imp)*
#   imp  := ou ('->' imp)?          (associa à direita)
#   ou   := e ('|' e)*
#   e    := neg ('&' neg)*
#   neg  := '~' neg | atomo
#   atomo:= VARIAVEL | '(' bic ')'
# ---------------------------------------------------------------------------

def _tokenizar(texto):
    tokens = []
    i = 0
    while i < len(texto):
        c = texto[i]
        if c.isspace():
            i += 1
        elif texto.startswith("<->", i):
            tokens.append("<->")
            i += 3
        elif texto.startswith("->", i):
            tokens.append("->")
            i += 2
        elif c in "~&|()":
            tokens.append(c)
            i += 1
        elif c.isalpha() and c.isupper():
            tokens.append(c)
            i += 1
        else:
            raise ErroDeFormula(f"Símbolo inválido '{c}' na fórmula '{texto}'.")
    return tokens


class _Leitor:
    def __init__(self, tokens, texto):
        self.tokens = tokens
        self.pos = 0
        self.texto = texto

    def _olhar(self):
        return self.tokens[self.pos] if self.pos < len(self.tokens) else None

    def _consumir(self, esperado=None):
        token = self._olhar()
        if token is None or (esperado is not None and token != esperado):
            raise ErroDeFormula(f"Fórmula incompleta ou mal formada: '{self.texto}'.")
        self.pos += 1
        return token

    def ler(self):
        arvore = self._bic()
        if self._olhar() is not None:
            raise ErroDeFormula(f"Sobrou texto na fórmula: '{self.texto}'.")
        return arvore

    def _bic(self):
        esquerda = self._imp()
        while self._olhar() == "<->":
            self._consumir()
            esquerda = ("bic", esquerda, self._imp())
        return esquerda

    def _imp(self):
        esquerda = self._ou()
        if self._olhar() == "->":
            self._consumir()
            return ("imp", esquerda, self._imp())
        return esquerda

    def _ou(self):
        esquerda = self._e()
        while self._olhar() == "|":
            self._consumir()
            esquerda = ("ou", esquerda, self._e())
        return esquerda

    def _e(self):
        esquerda = self._neg()
        while self._olhar() == "&":
            self._consumir()
            esquerda = ("e", esquerda, self._neg())
        return esquerda

    def _neg(self):
        if self._olhar() == "~":
            self._consumir()
            return ("nao", self._neg())
        return self._atomo()

    def _atomo(self):
        token = self._olhar()
        if token == "(":
            self._consumir("(")
            dentro = self._bic()
            self._consumir(")")
            return dentro
        if token is not None and token.isalpha():
            self._consumir()
            return ("var", token)
        raise ErroDeFormula(f"Fórmula incompleta ou mal formada: '{self.texto}'.")


@lru_cache(maxsize=None)
def ler_formula(texto):
    """Transforma o texto em uma árvore (tuplas aninhadas)."""
    return _Leitor(_tokenizar(texto), texto).ler()


# ---------------------------------------------------------------------------
# Avaliação
# ---------------------------------------------------------------------------

def _avaliar(arvore, valores):
    tipo = arvore[0]
    if tipo == "var":
        return valores[arvore[1]]
    if tipo == "nao":
        return nao(_avaliar(arvore[1], valores))
    a = _avaliar(arvore[1], valores)
    b = _avaliar(arvore[2], valores)
    if tipo == "e":
        return e(a, b)
    if tipo == "ou":
        return ou(a, b)
    if tipo == "imp":
        return implica(a, b)
    return bicondicional(a, b)


def avaliar(formula, valores):
    """Valor lógico (True/False) da fórmula para as atribuições dadas."""
    return _avaliar(ler_formula(formula), valores)


def variaveis(*formulas):
    """Variáveis usadas nas fórmulas, em ordem alfabética."""
    nomes = set()
    for formula in formulas:
        nomes.update(c for c in formula if c.isalpha() and c.isupper())
    return sorted(nomes)


def atribuicoes(nomes):
    """Todas as combinações de V/F para as variáveis (2^n linhas)."""
    for combinacao in product([True, False], repeat=len(nomes)):
        yield dict(zip(nomes, combinacao))


def tabela_verdade(formula):
    """Lista de (atribuição, resultado) com todas as linhas da tabela."""
    ler_formula(formula)  # valida a sintaxe antes de gerar as linhas
    return [(linha, avaliar(formula, linha)) for linha in atribuicoes(variaveis(formula))]


# ---------------------------------------------------------------------------
# Classificações e relações entre fórmulas
# ---------------------------------------------------------------------------

def e_tautologia(formula):
    return all(resultado for _, resultado in tabela_verdade(formula))


def e_contradicao(formula):
    return not any(resultado for _, resultado in tabela_verdade(formula))


def classificar(formula):
    if e_tautologia(formula):
        return "tautologia"
    if e_contradicao(formula):
        return "contradicao"
    return "contingencia"


def contraexemplo_equivalencia(f1, f2):
    """Primeira linha em que f1 e f2 têm valores diferentes (ou None)."""
    for linha in atribuicoes(variaveis(f1, f2)):
        if avaliar(f1, linha) != avaliar(f2, linha):
            return linha
    return None


def equivalentes(f1, f2):
    return contraexemplo_equivalencia(f1, f2) is None


def contraexemplo_argumento(premissas, conclusao):
    """Linha em que todas as premissas são V e a conclusão é F (ou None)."""
    for linha in atribuicoes(variaveis(conclusao, *premissas)):
        if all(avaliar(p, linha) for p in premissas) and not avaliar(conclusao, linha):
            return linha
    return None


def argumento_valido(premissas, conclusao):
    """Um argumento é válido quando não existe contraexemplo."""
    return contraexemplo_argumento(premissas, conclusao) is None


def linha_falsa(formula):
    """Primeira linha da tabela-verdade em que a fórmula é falsa (ou None)."""
    for linha, resultado in tabela_verdade(formula):
        if not resultado:
            return linha
    return None


# ---------------------------------------------------------------------------
# Apresentação
# ---------------------------------------------------------------------------

_SIMBOLOS = (("<->", "↔"), ("->", "→"), ("~", "¬"), ("&", "∧"), ("|", "∨"))


def formatar(formula):
    """Converte a sintaxe ASCII nos símbolos usados na tela."""
    for ascii_, simbolo in _SIMBOLOS:
        formula = formula.replace(ascii_, simbolo)
    return formula


def descrever(linha):
    """{'P': True, 'Q': False} -> 'P = V, Q = F'."""
    return ", ".join(f"{nome} = {'V' if valor else 'F'}" for nome, valor in linha.items())
