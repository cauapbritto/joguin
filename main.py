"""Soul Strike — ponto de entrada.

    python main.py             tela cheia
    python main.py --janela    em janela
    python main.py --sem-vsync sem sincronia vertical (se a imagem ficar travando em algum monitor)
"""
import os
import sys

# executável sem console: print() e logs não têm para onde ir
if sys.stdout is None:
    sys.stdout = open(os.devnull, "w")
if sys.stderr is None:
    sys.stderr = open(os.devnull, "w")

from soulstrike.game import Game  # noqa: E402


def main():
    args = sys.argv[1:]
    windowed = any(arg in ("--janela", "--windowed", "-w") for arg in args)
    vsync = "--sem-vsync" not in args
    Game(fullscreen=not windowed, vsync=vsync).run()


if __name__ == "__main__":
    main()
