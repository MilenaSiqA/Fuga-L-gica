# Fuga Lógica

Jogo digital de Lógica Matemática. Um carro foge da polícia por uma rodovia cheia de sinais. Cada sinal só abre quando o jogador resolve uma condição de Lógica Proposicional. Quanto mais rápido ele acerta, mais distância abre da viatura. Enquanto o carro está parado, a viatura se aproxima.

- **Lógica e regras:** Python (Flask)
- **Interface:** HTML, CSS e JavaScript no navegador

## Como rodar

Requisitos: Python 3.10 ou superior.

```bash
pip install -r requirements.txt
python app.py
```

Abra **http://localhost:5000** no navegador e clique em *Começar a fuga*.

## Publicar online (Render)

- **Build Command:** `pip install -r requirements.txt`
- **Start Command:** `gunicorn app:app --workers 1 --threads 4`
- **Variável de ambiente:** `SECRET_KEY` com um texto aleatório

Use **1 worker**: as partidas ficam na memória do servidor, e mais de um worker faria o jogo "esquecer" a partida.

## Como jogar

| Tipo de sinal | Níveis | O que o jogador faz |
|---|---|---|
| Interruptores | 1 e 2 | Liga ou desliga as variáveis livres (V/F) até a condição ficar verdadeira. Usa ¬, ∧, ∨, → e ↔. |
| Bifurcação | 3 | Escolhe a rota cuja proposição é tautologia ou contradição. |
| Equivalência | 4 | Escolhe a proposição equivalente à de referência (De Morgan, contrapositiva, condicional). |
| Argumento | 5 | Escolhe a conclusão que torna o argumento válido (modus ponens, modus tollens, silogismos). |

**Regras de distância** (valores em `dados/config.json`):

| Regra | Valor |
|---|---|
| Distância inicial | 60 m |
| Vitória | 150 m ou mais |
| Derrota | 0 m |
| Viatura se aproxima (carro parado) | 1 m por segundo |
| Acerto em até 5 s / 10 s / 20 s | +30 m / +15 m / +5 m |
| Erro | −10 m (o sinal continua fechado) |
| Tempo extra por nível | +3 s nas faixas de bônus |
| Sinais por nível | 2 |

Quando o jogador erra, a tela explica o motivo usando a linha da tabela-verdade que mostra o erro.

## Estrutura

```text
fuga-logica/
  app.py              servidor Flask e rotas da API
  logica.py           motor lógico: conectivos, leitor de fórmulas, tabela-verdade,
                      tautologia, equivalência, validade de argumentos
  jogo.py             regras: distância, tempo, níveis, vitória e derrota
  dados/
    proposicoes.json  sinais de cada nível
    config.json       valores de balanceamento
  templates/index.html
  static/estilo.css, jogo.js, imagens/
  tests/              testes automáticos
```

## Rotas da API

| Rota | O que faz |
|---|---|
| `POST /api/novo-jogo` | Zera a partida |
| `GET /api/sinal` | Entrega o sinal atual e inicia o cronômetro |
| `POST /api/responder` | Corrige a resposta (`{"valores": {...}}` ou `{"escolha": n}`) |
| `GET /api/estado` | Distância, nível e situação (jogando, vitoria, derrota) |

O tempo é medido no Python, entre a entrega do sinal e a resposta. O navegador nunca recebe a resposta certa.

## Como adicionar um sinal

Edite `dados/proposicoes.json`. Sintaxe das fórmulas: `~` (¬), `&` (∧), `|` (∨), `->` (→), `<->` (↔), variáveis em maiúscula (P, Q, R...).

```json
{"id": "2-6", "nivel": 2, "tipo": "satisfazer",
 "enunciado": "Ajuste os interruptores livres para a condição ficar verdadeira.",
 "formula": "(P -> Q) & (Q -> R)", "variaveis": {"P": true, "Q": null, "R": null}}
```

Variável com `null` é livre. Qualquer combinação que torne a fórmula verdadeira abre o sinal.
Depois de editar, rode os testes: eles conferem se todo sinal tem solução e se nenhum é trivial.

## Testes

```bash
python -m unittest discover tests
```

## Ajustes úteis

- **Demonstração com todos os níveis:** aumente `meta_vitoria` (por exemplo, 400) em `dados/config.json` para o jogo durar até o nível 5.
- **Mais difícil ou mais fácil:** mude `aproximacao_m_por_s`, `penalidade_erro` e `bonus_por_tempo`. Não é preciso alterar o código.

## Membros da equipe
 
| Nome Completo | E-mail Institucional |
|---|---|
| Letícia Almeida Abreu de Siqueira  | laas2@cesar.school |
| Letícia Dornas de Araújo  | lda2@cesar.school |
| Maria Júlia Oliveira Dionísio  | mjod@cesar.school |
| Maria Monalysa da Silva  | mms2@cesar.school |
| Manuela Brayner Medeiros de Araújo  | mbma3@cesar.school |
| Milena Siqueira Araújo  | msa4@cesar.school |
| Rafaela Dubeux Godoy  | rdg@cesar.school |
