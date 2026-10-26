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

### Linux Mint (e Ubuntu/Debian), jeito fácil

Extraia o zip do projeto, dê dois cliques em **`INSTALAR.sh`** e escolha
**Executar no terminal** (ou rode `bash INSTALAR.sh` no terminal da pasta). Ele usa o
Python que já vem no Mint (3.10 a 3.13), instala o `python3-venv` pelo `apt` se faltar
(pede a sua senha), cria o `.venv`, instala as bibliotecas e cria o atalho
**Soul Strike** no menu (seção Jogos) e na Área de Trabalho. Também dá para abrir pelo
`SoulStrike.sh`. Pode rodar o instalador de novo quando quiser; o log fica em
`instalar.log`. Para tirar os atalhos: `bash INSTALAR.sh --remover`.

Se o firewall estiver ligado (`sudo ufw status`), libere o controle pelo celular com
`sudo ufw allow 5000/tcp`.

### Manual

```
pip install -r requirements.txt
python main.py            # tela cheia
python main.py --janela   # em janela
python main.py --sem-vsync  # sem sincronia vertical (se a imagem engasgar em algum monitor)
```

F11 alterna tela cheia. ESC pausa a partida. Na tela **Opções** do menu dá para mudar o volume
(geral, música e efeitos), tela cheia, sincronia vertical, tremor de tela e o duplo toque; tudo fica
salvo em `opcoes.json`, na mesma pasta do progresso. `--janela` e `--sem-vsync` valem mais que as opções salvas.

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

### Pacote .deb (Linux Mint / Ubuntu / Debian)

```
pip install -r requirements.txt pyinstaller
python tools/build_deb.py
```

Gera `dist/soulstrike_1.0.0_amd64.deb`, que não precisa de Python no PC de quem for
jogar: dois cliques abrem o Instalador de Pacotes (ou `sudo apt install ./dist/soulstrike_*.deb`).
O jogo vai para `/opt/soulstrike`, com atalho no menu e o comando `soulstrike`; remove
com `sudo apt remove soulstrike`. O executável só roda em sistemas com glibc igual ou
mais nova que a do PC que gerou o pacote, então gere no Linux mais antigo que for usar.

Sem um Linux à mão: na aba **Actions** do GitHub, rode **Pacote Linux (.deb)**. Ele
gera o pacote no Ubuntu 22.04 (serve para o Linux Mint 21 e mais novos) e deixa o
`.deb` nos artefatos da execução; ao criar uma tag `v1.2.3`, anexa o `.deb` à release.
Esse mesmo workflow roda em todo PR: testa o `INSTALAR.sh` e o `.deb` no Linux Mint 21 e
22 (instala, abre o jogo pelo atalho numa tela virtual e remove).

## Atualizar o jogo

No menu principal, **ATUALIZAR** procura no GitHub se saiu versão nova (é a única função
do jogo que usa a internet; sem conexão ela só avisa e nada muda).

- **Instalado pelo INSTALAR.bat / INSTALAR.sh** (ou zip extraído): o jogo baixa a versão
  nova, troca os próprios arquivos e reabre sozinho. Não precisa apagar pasta nenhuma: o
  `.venv` fica, as bibliotecas só são reinstaladas se o `requirements.txt` mudou, e o
  progresso salvo (`%APPDATA%/SoulStrike` ou `~/.soulstrike`) nem é tocado. Se algo der
  errado no meio, os arquivos antigos voltam.
- **Executável (.exe ou .deb em /opt):** o jogo avisa que tem versão nova e abre a página
  para baixar (no Linux, é só abrir o .deb novo por cima do antigo).
- **Clone do git:** use `git pull`.

### Publicar uma versão nova

1. Suba o número em `soulstrike/__init__.py` (`__version__ = "1.1.0"`).
2. No GitHub, em *Releases → Draft a new release*, crie a tag `v1.1.0` (mesmo número) e
   publique. O texto da Release aparece na tela de atualização.

O botão compara a tag da última Release com o `__version__` de quem está jogando.

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

  **Armas que caem dos inimigos:** de vez em quando um inimigo (quase sempre os elites) deixa cair a
  arma de outro herói, uma que ninguém do grupo está usando. Perto dela, ATACAR pega: ela entra no
  lugar da arma do herói do mesmo tipo (de tiro ou de perto) e a antiga fica no chão. A troca vale
  até o fim da campanha e fica salva. A cor do nome mostra a raridade: **comum branca**, **rara
  azul** e **roubada dourada** (no chão e no HUD).
  **Armas raras do baú:** viram a 3ª arma do jogador (TROCAR ARMA passa pelas três) e ficam até o
  fim da campanha. Só dá para ter uma: quando o baú da fase seguinte dá outra, a antiga **fica
  no chão** (com o nome embaixo) e, perto dela, ATACAR **pega de volta** — trocando, e a outra
  fica no lugar. Qualquer jogador pode pegar a arma do chão. Cada uma tem o seu pente, e
  **o baú de cada fase tem as suas armas**, e as do Templo Gelado, a última fase, são roubadas:

  | Fase              | Arma                   | O que faz                                                     |
  |-------------------|------------------------|---------------------------------------------------------------|
  | Floresta Sombria  | Colmeia                | Estoura num enxame de abelhas que persegue o inimigo por 3 s.  |
  |                   | Arco de Espinhos       | 3 espinhos em leque; quem leva fica enraizado 1 s.             |
  |                   | Machado do Lenhador    | De perto: golpe em giro que acerta todo mundo em volta.        |
  |                   | Bumerangue             | Vai girando e volta para a mão, acertando na ida e na volta.   |
  |                   | Besta                  | Virote pesado e rápido que atravessa dois inimigos.            |
  | Calabouço         | Lanterna das Almas     | Feixe verde que suga a vida de quem está na frente.            |
  |                   | Crânio Uivante         | Caveira que persegue o alvo; quem leva foge com medo.          |
  |                   | Foice Espectral        | Atravessa paredes, vai e volta para a mão.                     |
  |                   | Lança-chamas           | Jato de fogo curto que atravessa todo mundo (gasta rápido).    |
  |                   | Canhão de Mão          | Bala de canhão que explode e dá um coice em quem atira.        |
  | Templo Gelado     | Estalactites           | 6 estalactites caem em linha e congelam quem pegam.            |
  | (roubadas)        | Espelho de Cristal     | Raio que reflete até 3 vezes nas paredes e atravessa todos.    |
  |                   | Bola de Neve           | Rola crescendo, arrasta os inimigos e explode no fim.          |
  |                   | Cajado do Raio Supremo | Raio que pula em até 5 inimigos, sem enfraquecer, e atordoa.   |

  Inimigos novos: o **diabrete** chega rápido e dá um bote; o **esqueleto arqueiro** para,
  mira (brilha) e atira; o **golem** levanta os punhos e esmaga o chão (saia de perto quando
  ele brilhar). As **almas corrompidas** lutam como os heróis, com a mesma habilidade.
  O chefão (bem mais forte que antes) alterna **chuva de bombas** (saia dos círculos), **anel de
  granadas**, **martelada** (pula e cai onde o círculo vermelho marca) e a **investida sombria**
  (atravessa a arena, e até as paredes, pelo caminho roxo marcado no chão, largando bombas). Depois
  de cada sequência ele fica **CANSADO** por pouco tempo e leva mais dano. Com metade da vida chama
  ajuda, com uma alma corrompida de herói; com 20% fica furioso e ganha a **armadura de sombra**:
  fora do CANSADO quase não sente os golpes. As armas roubadas do Templo fazem muita diferença.

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
- **Escolha de armas no duelo** (contra CPU, local e 2 x 2): antes de cada round, cada jogador monta o
  par de armas, uma de tiro e uma de perto. Ele vê a que já tem (MANTER) e mais 3 sorteadas de cada
  tipo; quem perdeu o round anterior vê 4. Setas escolhem, ATACAR confirma e ESQUIVA volta. A
  habilidade continua a do herói. Na escolha de personagem, **V** alterna entre armas a cada round e
  armas fixas (fica salvo).
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
  próprio de cada personagem** no botão SUPER. Primeiro a 3 gols vence; na escolha de personagem,
  **T** troca para 5 ou 7 gols, ou para **3 minutos** (o relógio para com a bola parada e, se
  terminar empatado, vale o **gol de ouro**). Com CPU em campo, **1 2 3** escolhem a dificuldade
  dela (velocidade, mira, vontade de roubar a bola e de usar o SUPER). Cada time joga de
  **uniforme**: o time da esquerda de azul e o da direita de vermelho (a roupa do personagem
  muda de cor, o resto continua igual), já na seleção e na tela de VS. O campo é grande
  (2240 x 1260, 40% maior que o primeiro) e a câmera nunca perde a bola: quem fica fora da tela
  aparece como uma setinha na cor do time, na borda.
  No futebol e no basquete a velocidade de todo mundo fica mais perto da média (o Tanque e o Titã
  não ficam para trás, e o Velocista continua o mais rápido).
  No 2 x 2 dá para jogar com 1 a 4 pessoas: quem faltar vira CPU para fechar o time. O jogador 2
  entra apertando `;` no teclado (ou pelo celular) e sai com `/`; o 3 e o 4 entram pelo celular.
- **Basquete 2 x 2** — a CPU também tem dificuldade (1 2 3), que muda o acerto da barrinha do
  arremesso, os tocos e os roubos. Time perdendo por 10 ou mais entra em **REAÇÃO!**: a faixa verde
  do arremesso fica um pouco maior e o SUPER volta 50% mais rápido, até encostar no placar.
  **Empurrão:** CORTE sem a bola em quem está pulando para arremessar deixa a faixa verde dele pela
  metade. Quem está protegendo a bola (MARCAR) segura, e quem empurra à toa (ou empurra de novo o
  mesmo arremesso) fica parado um instante.

## Personagens

| Personagem | Vida | Habilidade (duelo)                                        | Super (futebol)                                  |
|------------|------|-----------------------------------------------------------|--------------------------------------------------|
| Guerreiro  | 150  | Investida: avança, causa 30 de dano e deixa tonto 0,5 s  | Zagueirão: 5 s no seu campo sem cair, roubando só de encostar (veja abaixo) |
| Atirador   | 105  | Rajada: 5 balas em leque                                  | Chute certeiro: chute com curva para o gol       |
| Tanque     | 230  | Muralha: barreira de 4 s que segura os tiros e os devolve | Muralha: barreira na frente do próprio gol por 6 s (segura até a enterrada) |
| Ninja      | 95   | Shuriken: leque fechado de 3 shurikens de dano alto      | Sombra: aparece atrás da bola, virado para o gol |
| Velocista  | 115  | Turbo: 2x mais rápido por 4 s                             | Arrancada: corre muito com a bola colada         |
| Aryel      | 120  | Aposta: roleta de GREEN, meio green ou RED (veja abaixo)  | Grau de moto: 3 s de moto, bola colada, e quem ele atropela cai |
| Fantasma   | 110  | Teletransporte: some e reaparece                          | Bola fantasma: atravessa os adversários          |
| Titã       | 180  | Invulnerável por 3 s                                      | Gigante: fica enorme e empurra todo mundo        |
| Pirata     | 140  | Gancho: puxa o inimigo para a frente do sabre e o atordoa | Gancho: puxa a bola, até do pé do adversário (e do drible mágico) |
| Geada      | 100  | Nevasca: onda de gelo, dano em volta e inimigo lento      | Congelar: adversários perto ficam lentos         |
| Cauanzera  | 100  | Multiesportista: basquete, vôlei e 100 metros, nessa ordem (veja abaixo) | Enterrada: perto da área, pula todo mundo e crava a bola no gol |
| Albeguinio | 140  | Hacker: digita 1 s no notebook e trava todos os adversários por 5 s (3 s no duelo 1 x 1) | Hack: digita e trava os adversários por 2,5 s (recarga de 26 s) |
| Borba Jr   | 125  | Exoesqueleto: 4,5 s de armadura (veja abaixo)             | Exoesqueleto: 4 s em que ninguém toma a bola dele |
| Aryel Corrompido* | 135 | Chuva Sombria: 5 bombas caem em cima e em volta do inimigo | Bomba sombria: maior, atordoa e deixa lento |

\* Liberado ao zerar a campanha.

### Aryel

- **Aposta.** Um bilhete com três símbolos (bola, moeda e trevo) gira em cima da cabeça dele e para
  um por um. **Três iguais é GREEN:** moedas de ouro caem explodindo em cima dos inimigos.
  **Dois iguais é meio green:** solta as 8 bombas em volta. **Nenhum igual é RED:** uma bombinha
  estoura nele mesmo. Como nem sempre dá certo, recarrega mais rápido que as outras.
- **Baixinho:** o corpo é menor, então é mais difícil de acertar, mas ele tem um pouco menos de vida.
- **Grau de moto:** a esquiva vira uma empinada de moto, mais longa, soltando fumaça.
- **Capacete de moto** é a arma de perto (a Granada continua).
- **Futebol, Grau de moto:** sobe na moto por 3 s: anda bem mais rápido, a bola vai colada no pé e
  quem ele atropela cai (e perde a bola, se estava com ela). Serve para puxar o contra-ataque e para
  chegar no atacante.

O Aryel Corrompido continua como era (tamanho normal, Martelo e Chuva Sombria).

### Guerreiro no futebol: Zagueirão

O Guerreiro é o zagueiro do jogo. **Sempre (pegada firme):** rouba a bola na metade do tempo e
MARCAR não fica mais lento. **Super (5 s, só no seu campo; passou do meio, acaba):** não cai, não
trava e não fica lento (bomba, hack, caneta, chute trovão e trombada do exoesqueleto não pegam);
rouba a bola só de encostar, até do drible mágico e do exoesqueleto; a bola que bate nele morre no
pé e perde o efeito (curva, fantasma ou trovão); dá toco na enterrada; e o corte dele vira carrinho,
que derruba quem está com a bola. Recarga de 14 s.

### Cauanzera, Albeguinio e Borba Jr

- **Cauanzera — Multiesportista.** Cada vez que usa, é um esporte, sempre na ordem; o próximo aparece
  no HUD. **Basquete:** arremesso alto que passa por cima das paredes e cai em cima do inimigo (não
  erra, mesmo que ele corra). **Vôlei:** saque rápido que quica de um adversário para o outro; no 1 x 1
  sai dele, bate na parede e volta nele. **100 metros:** corre muito por 2 s e atropela quem estiver
  no caminho. Passiva de **alto**: o golpe corpo a corpo alcança mais longe e, no futebol, cabeceia
  bolas mais altas. No futebol, a **Enterrada** (com a bola, perto da área adversária) pula por cima
  de todo mundo — ninguém toca nele no ar — e crava a bola no gol, a até 450 px da linha do gol.
  Só para em quem estiver no ponto onde ele cai de Zagueirão ou de exoesqueleto, ou na Muralha
  erguida (**toco**). Recarga de 25 s.
- **Albeguinio — Hacker.** Abre o notebook e digita por 1 s, parado. Se apanhar enquanto digita, o
  hack falha. Terminando, o sinal de Wi-Fi sai dele e **todos** os adversários em jogo ficam
  HACKEADOS por 5 s (3 s no duelo 1 x 1): não andam, não atiram e não usam nada (pega até o exoesqueleto; o chefão da
  campanha fica menos tempo). Recarga de 20 s.
- **Borba Jr — Exoesqueleto.** As placas de metal se montam nele (faíscas e vapor) e por 4,5 s ele fica
  um pouco maior, leva metade do dano, não é empurrado nem fica tonto, e o golpe corpo a corpo
  arremessa longe — quem bate na parede fica tonto. Velocidade normal. No futebol (4 s): ninguém
  toma a bola dele, quem tromba nele cai e o corpo blindado segura qualquer chute.

### Craques do futebol

Cinco personagens que só aparecem na escolha do futebol (quadradinho com fundo de gramado).
Além do SUPER, cada um tem uma habilidade que vale o jogo todo:

| Craque  | Sempre                                                   | Super                                                                 |
|---------|----------------------------------------------------------|-----------------------------------------------------------------------|
| Faísca  | Bola protegida: tomar a bola dele demora bem mais         | Drible mágico: por 3 s ninguém toma a bola e ele atravessa os marcadores |
| Trovão  | Cabeça de aço: cabeceia bola mais alta e com mais força   | Chute trovão: bomba reta que derruba quem entra na frente e segue      |
| Ginga   | Condução veloz: bola colada no pé até correndo, sem frear (como na arrancada do Velocista) | Caneta: a bola passa entre as pernas do marcador, que fica tonto, e ele sai com ela |
| Matador | Faro na área: dentro da área o chute vai no gol e sai mais forte | Faro de gol: por 5 s corre mais e a bola solta perto dele vem para o pé |
| Paredão | Corpo fechado: bloqueia a bola de mais longe e a bola fantasma não passa por ele | Antecipação: teleporta até a bola, no próprio campo, e sai com ela (tira até do drible mágico; do exoesqueleto, não) |

Eles jogam de uniforme como todo mundo (número nas costas) e a CPU também usa os poderes.

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
| Disquete (Cauanzera) | 6               | Gira e quica uma vez na parede.                                          |
| Pendrive (Albeguinio) | 4              | Gira no ar e passa um **vírus**: o alvo pisca verde e perde vida aos poucos por 2 s. |
| Canhão de Pulso (Borba Jr) | 3         | Bola de energia azul. **Segure ATACAR para carregar**: sai maior, mais forte e empurra muito. |

Armas de perto da turma: **Cabo de Rede** (Cauanzera, chicote com o maior alcance do jogo),
**Notebook** (Albeguinio, fechado, bate com a tampa) e **Punho Mecânico** (Borba Jr; de
exoesqueleto, arremessa o inimigo).

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

**Esquiva perfeita** (duelo e campanha): esquivar bem na hora de um tiro ou golpe de verdade faz a
esquiva voltar na hora e carrega 20% da habilidade (o lutador brilha e aparece ESQUIVA PERFEITA!).
Esquivar à toa custa caro: a recarga da esquiva é de 1 s (a moto do Aryel, que vai mais longe, 1,3 s).

As teclas do jogador 1 e do jogador 2 podem ser trocadas em **Controles → K (Trocar teclas)**. Trocar
ATACAR troca também o confirmar dos menus; se a tecla já era de outra ação do mesmo jogador, as duas
trocam de lugar. Fica salvo junto das opções.

### Controle USB ou Bluetooth

Controles de Xbox, PlayStation e genéricos funcionam sem configurar nada: o primeiro controle é o
jogador 1, o segundo o jogador 2 e assim por diante (nas **Opções** dá para o primeiro controle ser o
P2, deixando o P1 no teclado). Nos menus o direcional navega, A confirma e B volta.

| Botão (Xbox / PlayStation) | Ação                                   |
|----------------------------|----------------------------------------|
| Analógico ou direcional    | Mover                                  |
| A / X                      | Atacar / chutar / confirmar            |
| X / quadrado               | Habilidade / passe                     |
| B / bola                   | Esquiva / corte                        |
| Y / triângulo              | Trocar arma / super                    |
| LB / L1                    | Marcar (futebol)                       |
| RB / R1                    | Conduzir colado (futebol)              |
| RT / R2                    | Correr (futebol)                       |
| LT / L2                    | Esquiva                                |
| START / OPTIONS            | Pausa                                  |

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
- **Corte** sem a bola é uma arrancada curta para onde você aponta (sem apontar, na direção da
  bola, se ela estiver perto). Encostou em quem está com a bola durante a arrancada, cutuca a bola
  para a frente e quase sempre fica com ela. Com a bola, o corte é um drible para o lado mais
  livre, e a bola vai junto.
- **De goleiro** (segurando MARCAR perto do seu gol), a bola fantasma para em você, o chute trovão
  te derruba mas perde metade da força e o hack trava você bem menos tempo.
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
  dungeon.py            entradas com grade, fogueira, baú escondido, arma no chão e a porta de volta
  lobbies.py            os acampamentos desenhados como texto (# parede, . chão, F fogueira...)
  enemies.py            inimigos da campanha e o cérebro de cada um
  boss.py               o chefão Aryel Corrompido
  upgrades.py           melhorias entre as fases
  progress.py           progresso salvo (campanha zerada, melhor tempo)
  updater.py            botão ATUALIZAR: versão nova no GitHub (única parte que usa a internet)
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
tools/gerar_sons.py     gera os efeitos novos (armas, futebol, campanha) e as músicas do acampamento e do chefão
tools/build_exe.py      gera dist/SoulStrike.exe
tools/build_deb.py      gera o pacote .deb para Linux
tools/simular.py        partidas CPU x CPU sem janela: taxa de vitória no duelo, gols e pontos por personagem
linux/instalar.sh       instalador do Linux (chamado pelo INSTALAR.sh)
linux/teste_instalador.sh, linux/ver_janela.sh
                        testes do instalador no Linux Mint (GitHub Actions)
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
`<nome>_vermelho.png` (só a roupa troca de cor; o `.json` é o da folha normal). As armas são geradas por
`tools/gerar_armas.py` (saem em `assets/weapons/`, com o ponto da mão em `grips.json`), junto com
os 4 estágios do arco (vazio, flecha encaixada, meio puxado e tenso) e a flecha em voo. As armas
de arremesso (lança, shuriken, estrela, granada, cristal) usam o próprio sprite da arma girando
como projétil. Rode os scripts de novo depois de editá-los.

## Créditos

Desenvolvido por Cauã Pedrozo Brito.

Toda a honra e glória a Jesus.

> "Porque Deus amou o mundo de tal maneira que deu o seu Filho unigênito, para que todo aquele
> que nele crê não pereça, mas tenha a vida eterna." (João 3:16)
