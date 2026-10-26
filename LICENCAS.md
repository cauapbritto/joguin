# Soul Strike: créditos e licenças

Desenvolvido por Cauã Pedrozo Brito. Este arquivo vai junto com o jogo (na pasta do
executável) e lista de onde vem cada parte.

## Feito para o jogo

- Código do jogo e da página de controle pelo celular.
- Sprites dos personagens, das criaturas, dos uniformes e das armas, desenhados pelos
  scripts `tools/gerar_sprites.py` e `tools/gerar_armas.py`.
- Quadras de basquete (`assets/tiles/quadra_*`), desenhadas pelo `tools/gerar_quadras.py`.
- Efeitos sonoros novos e as músicas do acampamento e do chefão (`camp_bgm.ogg` e
  `boss_bgm.ogg`), sintetizados pelo `tools/gerar_sons.py`, sem samples.

## De terceiros

| O quê | Arquivo | Autor | Licença |
| --- | --- | --- | --- |
| Fonte Press Start 2P | `assets/font/PressStart2P-Regular.ttf` | CodeMan38 (The Press Start 2P Project Authors) | SIL Open Font License 1.1 (texto em `assets/font/OFL.txt`) |
| Música das partidas | `assets/sounds/battle_bgm.mp3` | MaxKoMusic (maxkomusic.com) | Creative Commons Atribuição-CompartilhaIgual 3.0 (CC BY-SA 3.0): "Music by MaxKoMusic, https://maxkomusic.com/" |

## A confirmar antes de vender

A origem destes arquivos não está registrada no repositório. Antes de publicar numa loja,
confirme que eles foram feitos por você ou que a licença permite usar num jogo publicado
(e, se for cobrar, com uso comercial), e anote aqui o autor e a licença:

- Música do menu: `assets/sounds/bgm.ogg`.
- Efeitos sonoros antigos: `ability`, `barrier`, `cancel`, `click`, `confirm`, `dash`,
  `explosion`, `gameover`, `hit`, `hover`, `select`, `shoot`, `shoot2` e `victory`
  (`assets/sounds/*.wav`).
- Cenários da Arena Clássica e do Coliseu: `assets/tiles/arena_classica/` e `assets/tiles/coliseu/`.

## Bibliotecas que vão dentro do executável

| Biblioteca | Licença |
| --- | --- |
| Python | Python Software Foundation License |
| pygame (e o SDL que vem com ele) | GNU LGPL 2.1 (pygame); zlib (SDL) |
| Flask, Werkzeug, Jinja2, MarkupSafe, itsdangerous, click, blinker | BSD de 3 cláusulas (Pallets) e MIT (blinker) |
| qrcode | BSD |
| Pillow | MIT-CMU (HPND) |
| PyInstaller (o carregador do executável) | GPL 2 com exceção para programas gerados |

O pygame é LGPL: as bibliotecas dele ficam como arquivos separados na pasta do jogo e
podem ser trocadas por outra versão. O código-fonte do pygame está em
https://github.com/pygame/pygame e o do Soul Strike em https://github.com/cauapbritto/joguin.
