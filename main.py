"""Soul Strike — ponto de entrada.

    python main.py             tela cheia
    python main.py --janela    em janela
    python main.py --sem-vsync sem sincronia vertical (se a imagem ficar travando em algum monitor)

Sem essas opções, vale o que foi escolhido na tela de Opções do jogo.
"""
import os
import sys

# executável sem console: print() e logs não têm para onde ir
if sys.stdout is None:
    sys.stdout = open(os.devnull, "w")
if sys.stderr is None:
    sys.stderr = open(os.devnull, "w")

from soulstrike import settings  # noqa: E402
from soulstrike.game import Game  # noqa: E402


def display_options(args):
    """(tela cheia, vsync): as opções da linha de comando valem mais que as salvas."""
    windowed = any(arg in ("--janela", "--windowed", "-w") for arg in args)
    fullscreen = settings.get("tela_cheia") and not windowed
    vsync = settings.get("vsync") and "--sem-vsync" not in args
    return fullscreen, vsync


def main():
    fullscreen, vsync = display_options(sys.argv[1:])
    Game(fullscreen=fullscreen, vsync=vsync).run()


if __name__ == "__main__":
    main()
