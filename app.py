"""Servidor do Fuga Lógica.  Rode com:  python app.py"""

import os
import secrets

from flask import Flask, jsonify, render_template, request, session

import jogo

app = Flask(__name__)
# Em produção (Render), defina a variável SECRET_KEY. Localmente, usa uma chave aleatória.
app.secret_key = os.environ.get("SECRET_KEY") or secrets.token_hex(16)

CONFIG = jogo.carregar_config()
BANCO = jogo.carregar_banco()
PARTIDAS = {}  # id da sessão -> Partida (fica na memória do servidor)


def partida_atual():
    pid = session.get("pid")
    if pid not in PARTIDAS:
        pid = secrets.token_hex(8)
        session["pid"] = pid
        PARTIDAS[pid] = jogo.Partida(CONFIG, BANCO)
    return PARTIDAS[pid]


@app.get("/")
def pagina_inicial():
    return render_template("index.html", cfg=CONFIG)


@app.post("/api/novo-jogo")
def novo_jogo():
    pid = session.get("pid") or secrets.token_hex(8)
    session["pid"] = pid
    PARTIDAS[pid] = jogo.Partida(CONFIG, BANCO)
    return jsonify(PARTIDAS[pid].estado())


@app.get("/api/sinal")
def sinal():
    partida = partida_atual()
    dados = partida.proximo_sinal()
    return jsonify({"sinal": dados, "estado": partida.atualizar()})


@app.post("/api/responder")
def responder():
    partida = partida_atual()
    corpo = request.get_json(silent=True) or {}
    try:
        resultado = partida.responder(
            valores=corpo.get("valores"), escolha=corpo.get("escolha")
        )
    except (ValueError, RuntimeError) as erro:
        return jsonify({"erro": str(erro)}), 400
    return jsonify(resultado)


@app.get("/api/estado")
def estado():
    return jsonify(partida_atual().atualizar())


if __name__ == "__main__":
    app.run(debug=True, port=5000)
