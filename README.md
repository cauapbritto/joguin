# Soul Strike

Duelo de arena e futebol em pixel art, para 1 a 4 jogadores. Dá para jogar no
teclado ou usar o celular como controle (pela rede Wi-Fi, sem instalar nada).

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

- **Duelo contra CPU** — escolha a dificuldade (fácil, normal, difícil) e a arena.
- **Duelo local** — dois jogadores no teclado ou no celular.
- Duelos em **melhor de 3 rounds** (60 s cada; no fim do tempo vence quem tiver mais vida).
  Itens aparecem na arena: **vida**, **fúria** (+50% de dano por 6 s) e **energia**
  (habilidade pronta). Golpes corpo a corpo rebatem tiros.
- **Futebol 1 x 1 / 2 x 2** — passe, corte, condução, chute e passe pelo alto, cabeçada e
  um **poder próprio de cada personagem** no botão SUPER. Primeiro a 3 gols vence.
  No 2 x 2, quem não conectar o celular vira CPU.

## Controles

| Ação                  | Jogador 1 | Jogador 2   |
|-----------------------|-----------|-------------|
| Mover                 | W A S D   | Setas       |
| Atacar / chutar       | G         | ;           |
| Habilidade / passe    | F         | /           |
| Esquiva / corte       | Shift     | .           |
| Trocar arma / super   | Q         | U           |
| Conduzir a bola       | E         | Shift dir.  |

Toque duas vezes numa direção para esquivar.

No futebol, um toque em **chutar** ou **passe** manda a bola rasteira; **segurar e
soltar** levanta a bola (chute alto ou passe por cima da marcação — a barrinha
embaixo do jogador mostra a força). Bola alta na altura da cabeça: chutar vira
cabeçada. Segurar **conduzir** deixa a bola colada no pé (corre 10% mais devagar).

### Celular

Na tela "Conecte os celulares" aparece um QR code por jogador. Com o celular na
mesma rede do computador, é só escanear. O endereço também aparece no menu
principal (`http://IP-DO-PC:5000/?player=N`). O celular mostra a escolha de
personagem e, durante a partida, um analógico e os botões do modo atual.

## Estrutura

```
main.py                 ponto de entrada
soulstrike/
  game.py               loop principal e troca de telas
  scenes/               telas (menu, seleção, partida, resultado...)
  matches.py            Match, BattleMatch (duelo) e SoccerMatch (futebol)
  fighter.py            o lutador
  abilities.py          uma subclasse de Ability por personagem (duelo)
  soccer_powers.py      uma subclasse de SoccerPower por personagem (futebol)
  entities.py           Entity (base) e projéteis, paredes, barreira
  arena.py              mapas e colisão
  ai.py                 CPU do duelo e do futebol
  camera.py, hud.py, ui.py, assets.py, theme.py, data.py, config.py
  net/                  servidor Flask e estado compartilhado com o celular
web/                    página do controle no celular
assets/                 sprites, tiles, sons e fonte
tools/gerar_sprites.py  gera os sprites pixel art dos personagens
tools/gerar_armas.py    gera os sprites das armas
tools/build_exe.py      gera dist/SoulStrike.exe
tests/                  testes automáticos
```

## Testes

```
python -m unittest discover tests
```

## Sprites

Guerreiro e Aryel têm arte desenhada à mão. Os demais personagens são gerados
pelo script `tools/gerar_sprites.py` (4 direções × 4 quadros de caminhada) e as
16 armas por `tools/gerar_armas.py` (saem em `assets/weapons/`, com o ponto da
mão em `grips.json`). Rode os scripts de novo depois de editá-los.

## Créditos

Cauã Pedrozo Brito e Alber Alberguini Cabral.
