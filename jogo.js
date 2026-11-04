/* Interface do Fuga Lógica.
 * O navegador só mostra e envia: quem corrige as respostas, mede o tempo e
 * decide vitória ou derrota é o servidor Python (app.py, jogo.py, logica.py).
 */
(() => {
  'use strict';

  const $ = (seletor) => document.querySelector(seletor);
  const cena = $('#cena');
  const carro = $('#carro');
  const viatura = $('#viatura');
  const semaforo = $('#semaforo');
  const placa = $('#placa');
  const medidor = $('#medidor');
  const enchimento = $('#enchimento');
  const pausa = (ms) => new Promise((resolver) => setTimeout(resolver, ms));

  let meta = 150;
  let sinal = null;          // sinal exibido no momento
  let valores = {};          // interruptores escolhidos (tipo "satisfazer")
  let escolha = null;        // opção marcada (tipo "escolha" e "argumento")
  let enviando = false;
  let sondagem = null;
  let ultimoEstado = null;

  /* ---------- Comunicação com o servidor ---------- */

  async function api(url, corpo) {
    const opcoes = corpo === undefined ? {} : {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(corpo),
    };
    const resposta = await fetch(url, opcoes);
    const dados = await resposta.json().catch(() => ({}));
    if (!resposta.ok) throw new Error(dados.erro || 'Falha na comunicação com o servidor.');
    return dados;
  }

  /* ---------- Cena e medidor ---------- */

  function posicionar(distancia) {
    const largura = cena.clientWidth;
    const larguraViatura = viatura.offsetWidth;
    const carroX = Math.min(largura * 0.58, largura - carro.offsetWidth - 96);
    const escala = (carroX + 30) / meta;
    carro.style.left = carroX + 'px';
    viatura.style.transform =
      `translateX(${carroX - larguraViatura - distancia * escala + 30}px)`;
  }

  function atualizarHud(estado) {
    ultimoEstado = estado;
    meta = estado.meta;
    const distancia = Math.max(0, estado.distancia);
    $('#dist-num').textContent = Math.round(distancia);
    $('#nivel-num').textContent = estado.nivel;
    enchimento.style.width = Math.min(100, (distancia / meta) * 100) + '%';
    medidor.setAttribute('aria-valuenow', String(Math.round(distancia)));
    document.body.classList.toggle('perigo', distancia < 25);
    posicionar(distancia);

    const cronometro = $('#cronometro');
    if (cronometro && sinal) {
      cronometro.querySelector('.segundos').textContent =
        estado.segundos_no_sinal.toFixed(1).replace('.', ',');
      cronometro.querySelector('.bonus').textContent =
        estado.bonus_atual > 0 ? `+${estado.bonus_atual} m` : 'sem bônus';
    }
  }

  async function dirigir() {
    cena.classList.add('andando');
    semaforo.dataset.fase = 'saindo';
    await pausa(1100);
    semaforo.dataset.fase = 'fora';
    semaforo.dataset.luz = 'vermelha';
    void semaforo.offsetWidth;  // aplica o estado "fora" antes de voltar
    semaforo.dataset.fase = 'parado';
  }

  async function parar() {
    await pausa(900);
    cena.classList.remove('andando');
  }

  /* ---------- Montagem do sinal ---------- */

  function criar(tag, classe, texto) {
    const no = document.createElement(tag);
    if (classe) no.className = classe;
    if (texto !== undefined) no.textContent = texto;
    return no;
  }

  function alternarChave(botao, nome) {
    valores[nome] = !valores[nome];
    botao.setAttribute('aria-pressed', String(valores[nome]));
    botao.textContent = valores[nome] ? 'V' : 'F';
  }

  function montarInterruptores(lista) {
    const caixa = criar('div', 'interruptores');
    lista.forEach((v) => {
      const item = criar('div', 'variavel' + (v.livre ? '' : ' fixa'));
      item.appendChild(criar('span', 'nome', v.nome));
      if (v.livre) {
        valores[v.nome] = false;
        const botao = criar('button', 'chave', 'F');
        botao.type = 'button';
        botao.setAttribute('aria-pressed', 'false');
        botao.setAttribute('aria-label', `Interruptor ${v.nome}`);
        botao.addEventListener('click', () => alternarChave(botao, v.nome));
        item.appendChild(botao);
      } else {
        item.appendChild(criar('span', 'valor-fixo', v.valor ? 'V' : 'F'));
        item.appendChild(criar('span', 'dica', 'fixa'));
      }
      caixa.appendChild(item);
    });
    return caixa;
  }

  function montarOpcoes(opcoes, botaoConfirmar) {
    const caixa = criar('div', 'opcoes');
    opcoes.forEach((texto, indice) => {
      const botao = criar('button', 'opcao', texto);
      botao.type = 'button';
      botao.setAttribute('aria-pressed', 'false');
      botao.addEventListener('click', () => {
        escolha = indice;
        caixa.querySelectorAll('.opcao').forEach((b, i) =>
          b.setAttribute('aria-pressed', String(i === indice)));
        botaoConfirmar.disabled = false;
      });
      caixa.appendChild(botao);
    });
    return caixa;
  }

  function mostrarSinal(dados) {
    sinal = dados;
    valores = {};
    escolha = null;
    placa.replaceChildren();

    const topo = criar('div', 'placa-topo');
    topo.appendChild(criar('h2', null, `Sinal fechado · nível ${dados.nivel}`));
    const cronometro = criar('p', 'cronometro');
    cronometro.id = 'cronometro';
    cronometro.innerHTML = 'Tempo <strong class="segundos">0,0</strong> s · bônus agora <strong class="bonus"></strong>';
    topo.appendChild(cronometro);
    placa.appendChild(topo);
    placa.appendChild(criar('p', 'enunciado', dados.enunciado));

    const botao = criar('button', 'botao', 'Confirmar');
    botao.type = 'button';
    botao.id = 'btn-confirmar';

    if (dados.tipo === 'satisfazer') {
      placa.appendChild(criar('div', 'formula', dados.formula));
      placa.appendChild(montarInterruptores(dados.variaveis));
    } else {
      if (dados.referencia) {
        placa.appendChild(criar('p', 'rotulo', 'Proposição de referência'));
        placa.appendChild(criar('div', 'formula pequena', dados.referencia));
      }
      if (dados.premissas) {
        placa.appendChild(criar('p', 'rotulo', 'Premissas'));
        const lista = criar('ol', 'premissas');
        dados.premissas.forEach((p) => lista.appendChild(criar('li', null, p)));
        placa.appendChild(lista);
        placa.appendChild(criar('p', 'rotulo', 'Conclusão'));
      }
      botao.disabled = true;
      placa.appendChild(montarOpcoes(dados.opcoes, botao));
    }

    const acoes = criar('div', 'acoes');
    const retorno = criar('p', 'retorno');
    retorno.id = 'retorno';
    acoes.append(botao, retorno);
    placa.appendChild(acoes);
    botao.addEventListener('click', enviar);

    placa.hidden = false;
    semaforo.dataset.luz = 'vermelha';
  }

  function mostrarRetorno(texto, ok) {
    const retorno = $('#retorno');
    if (!retorno) return;
    retorno.textContent = texto;
    retorno.className = 'retorno ' + (ok ? 'ok' : 'erro');
  }

  /* ---------- Fluxo do jogo ---------- */

  async function carregarSinal() {
    const dados = await api('/api/sinal');
    atualizarHud(dados.estado);
    if (dados.estado.situacao !== 'jogando') return fim(dados.estado);
    mostrarSinal(dados.sinal);
    atualizarHud(dados.estado);
    iniciarSondagem();
  }

  function iniciarSondagem() {
    pararSondagem();
    sondagem = setInterval(async () => {
      if (enviando || !sinal) return;
      try {
        const estado = await api('/api/estado');
        if (enviando || !sinal) return;
        atualizarHud(estado);
        if (estado.situacao !== 'jogando') fim(estado);
      } catch (erro) { /* tenta de novo no próximo ciclo */ }
    }, 250);
  }

  function pararSondagem() {
    if (sondagem) clearInterval(sondagem);
    sondagem = null;
  }

  async function enviar() {
    if (enviando || !sinal) return;
    enviando = true;
    const botao = $('#btn-confirmar');
    botao.disabled = true;
    try {
      const corpo = sinal.tipo === 'satisfazer' ? { valores } : { escolha };
      const resp = await api('/api/responder', corpo);
      atualizarHud(resp.estado);

      if (resp.correto) {
        pararSondagem();
        mostrarRetorno(resp.mensagem, true);
        semaforo.dataset.luz = 'verde';
        sinal = null;
        if (resp.estado.situacao === 'vitoria') {
          await pausa(900);
          return fim(resp.estado);
        }
        await pausa(900);
        placa.hidden = true;
        await dirigir();
        await carregarSinal();
        enviando = false;
        parar();
      } else {
        mostrarRetorno(resp.mensagem, false);
        placa.classList.remove('tremer');
        void placa.offsetWidth;
        placa.classList.add('tremer');
        if (resp.estado.situacao === 'derrota') return fim(resp.estado);
        botao.disabled = sinal.tipo !== 'satisfazer' && escolha === null;
      }
    } catch (erro) {
      mostrarRetorno(erro.message, false);
      botao.disabled = false;
    } finally {
      enviando = false;
    }
  }

  function fim(estado) {
    pararSondagem();
    sinal = null;
    cena.classList.remove('andando');
    const venceu = estado.situacao === 'vitoria';
    $('#fim-titulo').textContent = venceu ? 'Você escapou!' : 'A viatura te alcançou';
    $('#fim-texto').textContent = venceu
      ? `Vantagem final de ${Math.round(estado.distancia)} m. Você abriu ${estado.resolvidos} sinais, com ${estado.erros} erro(s), e chegou ao nível ${estado.nivel}.`
      : `Você abriu ${estado.resolvidos} sinais, com ${estado.erros} erro(s), e chegou ao nível ${estado.nivel}. Tente de novo: o raciocínio rápido abre mais distância.`;
    $('#tela-fim').hidden = false;
    $('#btn-reiniciar').focus();
  }

  async function iniciar() {
    $('#tela-inicio').hidden = true;
    $('#tela-fim').hidden = true;
    placa.hidden = true;
    const estado = await api('/api/novo-jogo', {});
    atualizarHud(estado);
    semaforo.dataset.fase = 'fora';
    semaforo.dataset.luz = 'vermelha';
    void semaforo.offsetWidth;
    cena.classList.add('andando');
    semaforo.dataset.fase = 'parado';
    await carregarSinal();
    await parar();
  }

  $('#btn-comecar').addEventListener('click', iniciar);
  $('#btn-reiniciar').addEventListener('click', iniciar);
  window.addEventListener('resize', () => ultimoEstado && posicionar(ultimoEstado.distancia));
  posicionar(60);
})();
