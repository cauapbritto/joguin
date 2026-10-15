# Soul Strike

Campanha cooperativa, duelo de arena e futebol em pixel art, para 1 a 4 jogadores.
Dá para jogar no teclado ou usar o celular como controle (pela rede Wi-Fi, sem
instalar nada).

## Como rodar

### Windows, jeito fácil (um clique)

Extraia o zip do projeto e dê dois cliques em **`INSTALAR.bat`**. Ele encontra o
Python 3.10 a 3.13 (ou instala o 3.11 pelo `winget`, se faltar), cria o `.venv`,
instala as bibliotecas (com nova tentativa em redes que interceptam HTTPS) e cria o
atalho **Soul Strike** na Área de Trabalho. Depois é só abrir o atalho (ou o
`SoulStrike.bat`). Pode rodar o instalador de novo quando quiser: o que já existe é
aproveitado. O log fica em `instalar.log`.

Se o Windows mostrar "O Windows protegeu o computador": **Mais informações** →
**Executar assim mesmo**.

### Manual

```
pip install -r requirements.txt
python main.py            # tela cheia
python main.py --janela   # em janela
python main.py --sem-vsync  # sem sincronia vertical (se a imagem engasgar em algum monitor)
```

F11 alterna tela cheia. ESC pausa a partida.

### Executável (Windows)

```
pip install pyinstaller
python tools/build_exe.py
```

Gera `dist/SoulStrike.exe`, um arquivo só que roda em qualquer PC com Windows sem
precisar de Python. Na primeira vez o Windows pode perguntar se libera o acesso à
rede: libere (é o servidor do controle pelo celular).

Se o `pip` reclamar de certificado (rede com proxy), use
`pip install --use-feature=truststore pyinstaller`.

## Modos

- **Campanha** (1 a 4 jogadores, juntos) — Aryel tocou no Cristal das Almas e virou **Aryel
  Corrompido**; quem ele derrota vira sombra. São 3 fases, e cada fase é um caminho de masmorras:
  1. **Acampamento** (no tema da fase, sem batalha): a **fogueira** recupera vida devagar (até
     70%) para quem fica perto. Na parede ficam as **entradas das duas masmorras**: a 1 aberta e a
     2 trancada com grade. Para entrar, o grupo todo vai até a entrada.
  2. **Masmorra 1** (o mapa da fase): ondas de inimigos que saem de portais. Sala limpa, quem caiu
     levanta e aparece uma **porta**: o grupo volta para o acampamento.
  3. **De volta ao acampamento**, a grade da masmorra 2 sobe e, num cantinho escondido, aparece um
     **baú**. Perto dele, ATACAR abre: ele treme, a tampa pula, sobe um feixe de luz e sai **uma
     arma rara para cada jogador** (veja abaixo).
  4. **Masmorra 2** (uma variação do mapa da fase; no Templo é o altar do chefão).
  5. Sala limpa, aparece na tela o botão **TELETRANSPORTE DE FASE**. Cada um confirma (ATACAR no
     teclado, o botão no celular ou clique) e, quando estão todos, o grupo vira luz e vai para a
     próxima fase (antes passa pelas melhorias e pela história).

  As fases: **Floresta Sombria** (Clareira Sombria e Ruínas da Floresta: diabretes, esqueletos
  arqueiros e o Velocista Sombrio), **Calabouço das Almas** (Corredores e Celas das Almas: golem,
  esqueletos e as sombras do Tanque e do Ninja) e **Templo Gelado** (Pátio do Templo e Altar do
  Cristal, com o chefão **Aryel Corrompido**).

  **Armas raras do baú:** viram a 3ª arma do jogador (TROCAR ARMA passa pelas três) e ficam até o
  fim da campanha; o baú da fase seguinte troca por outra. Cada uma tem o seu pente:

  | Arma               | O que faz                                                         |
  |--------------------|-------------------------------------------------------------------|
  | Besta              | Virote pesado e rápido que atravessa dois inimigos.               |
  | Lança-chamas       | Jato de fogo curto que atravessa todo mundo (gasta rápido).       |
  | Bumerangue         | Vai girando e volta para a mão, acertando na ida e na volta.      |
  | Cajado do Raio     | Raio na hora no alvo, que pula para mais dois inimigos perto.     |
  | Canhão de Mão      | Bala de canhão que explode onde bate e dá um coice em quem atira. |

  Inimigos novos: o **diabrete** chega rápido e dá um bote; o **esqueleto arqueiro** para,
  mira (brilha) e atira; o **golem** levanta os punhos e esmaga o chão (saia de perto quando
  ele brilhar). As **almas corrompidas** lutam como os heróis, com a mesma habilidade.
  O chefão alterna **chuva de bombas** (saia dos círculos), **anel de granadas** e **martelada**
  (pula e cai onde o círculo vermelho marca). Depois de cada sequência ele fica **CANSADO** e
  leva mais dano. Com metade da vida chama ajuda; com 20% fica furioso.

  Quem cair pode ser **levantado**: fique perto do companheiro caído até o anel encher. Se todo
  mundo cair, gasta um dos **3 continues** (TENTAR DE NOVO volta para o acampamento da fase).
  No fim de cada fase todos recuperam um pouco da vida
  e cada jogador escolhe **1 de 3 melhorias** (vida, dano, recarga, velocidade, tiros que
  atravessam, esquiva, vampirismo, escudo ou munição), que se acumulam. Mais jogadores, mais inimigos.
  O jogador 1 sempre joga; o 2 entra pelo teclado (tecla `;`) ou celular; o 3 e o 4, pelo celular.
  Escolha a dificuldade na seleção de personagem (TAB). Zerar a campanha libera o **Aryel
  Corrompido** para jogar em todos os modos e guarda o melhor tempo (em
  `%APPDATA%/SoulStrike/progresso.json` no Windows).
- **Duelo contra CPU** — escolha a dificuldade (fácil, normal, difícil) e a arena. Cada arena tem
  o seu clima: a **Floresta** tem cerca viva, trilhas e vaga-lumes; o **Calabouço**, tochas acesas,
  poças e ossos; o **Templo Gelado**, blocos de gelo com pingentes e neve caindo. Cada uma tem
  também uma variação (**Ruínas da Floresta**, **Celas do Calabouço** e **Pátio do Templo**).
- **Duelo local** — dois jogadores no teclado ou no celular.
- **Duelo 2 x 2** — dois times de dois, de 1 a 4 pessoas (quem faltar vira CPU). Não tem fogo
  amigo: tiros, golpes e explosões só pegam no outro time. O round acaba quando o **time inteiro**
  cai, e dá para **levantar o companheiro** uma vez por round (fique perto até o anel encher; ele
  volta com 35% da vida). No fim do tempo vence o time com mais vida somada. Ao atirar, o alvo é o
  adversário para onde você está apontando. No lobby, **TAB** (ou o botão TIMES) troca a divisão:
  `P1+P3 x P2+P4` (os dois do teclado se enfrentam) ou `P1+P2 x P3+P4` (os dois do teclado juntos,
  por exemplo contra a CPU). A divisão vale também para o futebol 2 x 2.
- Duelos em **melhor de 3 rounds** (60 s cada; no fim do tempo vence quem tiver mais vida).
  Itens aparecem na arena: **vida**, **fúria** (+50% de dano por 6 s), **energia**
  (habilidade pronta) e **munição** (pente cheio na hora e mais um pente extra, que aparece em
  dourado). Golpes corpo a corpo rebatem tiros.
- **Munição:** cada arma de tiro tem um pente. Quando acaba (ou depois de um tempo sem atirar
  com o pente pela metade) ela **recarrega sozinha**; dá para trocar para a arma de perto
  enquanto isso. Atirar com bala no pente cancela a recarga. A munição aparece embaixo da vida
  de cada lutador, no HUD e no botão ATACAR do celular. As armas mágicas (Orbe e Cristal) não
  recarregam: a carga volta aos poucos.
- **Futebol 1 x 1 / 2 x 2** — passe, corte, condução, chute e passe pelo alto, cabeçada,
  **correr** (com fôlego), **marcar**, **chutão**, **carrinho de bloqueio** e um **poder
  próprio de cada personagem** no botão SUPER. Primeiro a 3 gols vence. Cada time joga de
  **uniforme**: o time da esquerda de azul e o da direita de vermelho (a roupa do personagem
  muda de cor, o resto continua igual), já na seleção e na tela de VS. O campo é grande
  (2240 x 1260, 40% maior que o primeiro) e a câmera nunca perde a bola: quem fica fora da tela
  aparece como uma setinha na cor do time, na borda.
  No 2 x 2 dá para jogar com 1 a 4 pessoas: quem faltar vira CPU para fechar o time. O jogador 2
  entra apertando `;` no teclado (ou pelo celular) e sai com `/`; o 3 e o 4 entram pelo celular.

## Personagens

| Personagem | Vida | Habilidade (duelo)                                        | Super (futebol)                                  |
|------------|------|-----------------------------------------------------------|--------------------------------------------------|
| Guerreiro  | 150  | Investida: avança e causa 30 de dano                      | Carrinho: desliza, derruba e rouba a bola        |
| Atirador   | 105  | Rajada: 5 balas em leque                                  | Chute certeiro: chute com curva para o gol       |
| Tanque     | 230  | Muralha: barreira que bloqueia tiros por 4 s              | Muralha: barreira na frente do próprio gol       |
| Ninja      | 95   | Shuriken: 3 shurikens de dano alto                        | Sombra: aparece atrás da bola, virado para o gol |
| Velocista  | 115  | Turbo: 2x mais rápido por 4 s                             | Arrancada: corre muito com a bola colada         |
| Aryel      | 130  | Explosão: 8 bombas em volta                               | Bomba: empurra e atordoa quem está perto         |
| Fantasma   | 110  | Teletransporte: some e reaparece                          | Bola fantasma: atravessa os adversários          |
| Titã       | 180  | Invulnerável por 3 s                                      | Gigante: fica enorme e empurra todo mundo        |
| Pirata     | 140  | Gancho: puxa o inimigo para a frente do sabre e o atordoa | Gancho: puxa a bola, até do pé do adversário     |
| Geada      | 100  | Nevasca: onda de gelo, dano em volta e inimigo lento      | Congelar: adversários perto ficam lentos         |
| Aryel Corrompido* | 135 | Chuva Sombria: 5 bombas caem em cima e em volta do inimigo | Bomba sombria: maior, atordoa e deixa lento |

\* Liberado ao zerar a campanha.

### Armas de tiro

Cada arma de tiro tem o seu projétil, com efeito e animação próprios:

| Arma (personagem)    | Pente            | O que tem de especial                                                    |
|----------------------|------------------|--------------------------------------------------------------------------|
| Arco (Guerreiro)     | 6 flechas        | **Segure ATACAR para tensionar** (a corda vai sendo puxada); solte para atirar. Tensa, a flecha brilha, voa mais rápido, causa quase o dobro de dano e atravessa um alvo. Flecha que erra fica fincada na parede. |
| Rifle (Atirador)     | 18 balas         | Tiro rápido com risco de luz; a cápsula pula para o lado.                |
| Lança (Tanque)       | 4 lanças         | Atravessa o primeiro alvo, empurra forte e finca na parede. Sem lanças, a mão fica vazia. |
| Shuriken (Ninja)     | 10               | Gira e **ricocheteia** uma vez na parede.                                |
| Estrela (Velocista)  | 12               | Gira soltando faíscas; acertar dá **embalo** (+25% de velocidade).       |
| Granada (Aryel)      | 5                | Vai **pelo alto, por cima das paredes**, e explode onde cai (o círculo laranja avisa). |
| Orbe (Fantasma)      | 6 (volta sozinha)| **Persegue** o alvo e **atravessa paredes**, mas é lento.                |
| Corrente (Titã)      | 3                | Bola de ferro presa na corrente: vai, **atordoa** quem acertar e volta.  |
| Pistola (Pirata)     | 2                | Dois tiros fortes com nuvem de pólvora e empurrão; recarga lenta.        |
| Cristal (Geada)      | 8 (volta sozinha)| Deixa o alvo **lento** e estilhaça na parede.                            |

## Controles

| Ação                          | Jogador 1 | Jogador 2   |
|-------------------------------|-----------|-------------|
| Mover                         | W A S D   | Setas       |
| Atacar / chutar               | G         | ;           |
| Habilidade / passe            | F         | /           |
| Esquiva (duelo)               | Shift     | .           |
| Trocar arma / super           | Q         | U           |
| Corte / carrinho (futebol)    | Espaço    | .           |
| Correr (futebol)              | Shift     | Shift dir.  |
| Marcar (futebol)              | R         | Enter       |
| Conduzir colado (futebol)     | E         | L           |

Toque duas vezes numa seta para esquivar (dá para desligar na tela de Controles, tecla T).

No futebol:

- Um toque em **chutar** ou **passe** manda a bola rasteira; **segurar e soltar** levanta
  a bola (chute alto ou passe por cima da marcação). Bola na altura da cabeça: chutar vira
  cabeçada.
- **Quanto mais segura, mais longe**: o chute rasteiro atravessa meio campo e o chute alto
  com a carga cheia cai a uns 750 px. O **passe alto** vira **lançamento**: chega no
  companheiro até do outro lado do campo, e quem recebe domina a bola mesmo vindo rápida (se um
  adversário desviar no caminho, já era). Sem companheiro naquela direção, o passe alto vai
  para o espaço, mais longe quanto mais tempo segurou.
- **Passe** vai para o companheiro na direção que você aponta (na frente dele, se estiver
  correndo). Sem apontar, vai para o mais perto. Ninguém para aquele lado: vai para o espaço.
- **Cruzamento** (2 x 2): na ponta, no último terço do campo, com um companheiro entrando
  na área, o passe vira cruzamento. **Passe alto** chega na altura da cabeça, na frente da
  corrida dele; **passe normal** vai rasteiro e forte, para finalizar de primeira. Cabeçada
  na área vai para o gol (com a assistência ligada). Apontar para trás continua sendo recuo.
  A CPU também abre pela ponta, cruza e entra na área.
- **Correr** (segurar): 40% mais rápido, gastando o fôlego (barrinha embaixo do nome). Com a
  bola, ela vai mais solta e é mais fácil de roubar.
- **Marcar** (segurar): vai sozinho até a bola; se o adversário está com ela, fica na frente
  dele, entre ele e o seu gol; perto do seu gol, se posiciona como goleiro. Quem rouba a bola
  continua sendo você (corte ou entrando na frente). No 2 x 2, se o companheiro já está na
  bola, você cobre o espaço atrás.
- No seu campo, **chutar** com a bola solta dá um **chutão** para longe do gol (vale apertar
  um pouco antes de a bola chegar). **Corte** com um chute vindo vira **carrinho de bloqueio**;
  errou o tempo, fica no chão por um instante.
- **Conduzir** colado deixa a bola presa no pé (corre 10% mais devagar).
- **Assistência** (alta, média ou desligada; TAB na escolha de personagens): corrige um pouco
  o chute que sairia para fora, ajuda no passe e puxa para o pé a bola que passa perto.

### Celular

Na tela "Conecte os celulares" aparece um QR code por jogador. Com o celular na
mesma rede do computador, é só escanear. O endereço também aparece no menu
principal (`http://IP-DO-PC:5000/?player=N`). O celular mostra a escolha de
personagem e, durante a partida, um analógico e os botões do modo atual, em arco em volta
do polegar direito: o principal (atacar/chutar) é o grande no canto, e o toque vale para o
botão mais próximo, mesmo um pouco fora dele. Dá para deslizar o dedo de um botão para
outro sem levantar (de MARCAR para CORTE, por exemplo). No futebol, empurrar o analógico
até a borda faz correr, e o anel em volta dele mostra o fôlego; o anel do SUPER mostra a
recarga. O ponto colorido no topo mostra a qualidade da conexão. Se a
rede engasgar, o jogo continua com o último comando; sem notícias do celular por 1 s, o
jogador para por segurança.

## Estrutura

```
main.py                 ponto de entrada
soulstrike/
  game.py               loop principal e troca de telas
  scenes/               telas (menu, seleção, partida, resultado...)
  matches.py            Match, BattleMatch (duelo), TeamBattleMatch (duelo 2 x 2) e SoccerMatch (futebol)
  projectiles.py        um projétil por arma de tiro (flecha, granada, corrente...)
  campaign.py           CampaignRun (a campanha toda), LobbyMatch (acampamento), CampaignMatch
                        (masmorra), as fases e a história
  dungeon.py            entradas com grade, fogueira, baú escondido e a porta de volta
  lobbies.py            os acampamentos desenhados como texto (# parede, . chão, F fogueira...)
  enemies.py            inimigos da campanha e o cérebro de cada um
  boss.py               o chefão Aryel Corrompido
  upgrades.py           melhorias entre as fases
  progress.py           progresso salvo (campanha zerada, melhor tempo)
  fighter.py            o lutador
  abilities.py          uma subclasse de Ability por personagem (duelo)
  soccer_powers.py      uma subclasse de SoccerPower por personagem (futebol)
  entities.py           Entity (base) e projéteis, paredes, barreira
  arena.py              mapas e colisão
  scenery.py            cenário dos mapas (chão, paredes e ambiente: vaga-lumes, tochas, neve)
  ai.py                 CPU do duelo e do futebol
  soccer_assist.py      geometria do futebol e assistências de passe, chute e domínio
  camera.py, hud.py, ui.py, assets.py, theme.py, data.py, config.py
  net/                  servidor Flask e estado compartilhado com o celular
web/                    página do controle no celular
assets/                 sprites, tiles, sons e fonte
tools/gerar_sprites.py  gera os sprites pixel art dos personagens e das criaturas
tools/gerar_armas.py    gera os sprites das armas
tools/build_exe.py      gera dist/SoulStrike.exe
tests/                  testes automáticos
```

## Testes

```
python -m unittest discover tests
```

## Sprites

Todos os personagens e as criaturas da campanha (diabrete, esqueleto e golem) são pixel
art gerada pelo script `tools/gerar_sprites.py`. Cada um vira uma folha
`assets/characters/<nome>.png` com 4 direções e 15 quadros: caminhada (8), parado
respirando (2), ataque (3), dano (1) e esquiva (1). O `<nome>.json` ao lado guarda onde fica
a mão que segura a arma em cada quadro e a cor dos olhos. As almas corrompidas são os
próprios heróis escurecidos pelo jogo, com os olhos (e os óculos do Aryel) acesos. O mesmo
script gera os uniformes do futebol em `assets/characters/uniformes/<nome>_azul.png` e
`<nome>_vermelho.png` (só a roupa troca de cor; o `.json` é o da folha normal). As 20 armas são geradas por
`tools/gerar_armas.py` (saem em `assets/weapons/`, com o ponto da mão em `grips.json`), junto com
os 4 estágios do arco (vazio, flecha encaixada, meio puxado e tenso) e a flecha em voo. As armas
de arremesso (lança, shuriken, estrela, granada, cristal) usam o próprio sprite da arma girando
como projétil. Rode os scripts de novo depois de editá-los.

## Créditos

Desenvolvido por Cauã Pedrozo Brito.

Toda a honra e glória a Jesus.

> "Porque Deus amou o mundo de tal maneira que deu o seu Filho unigênito, para que todo aquele
> que nele crê não pereça, mas tenha a vida eterna." (João 3:16)
