"""Soul Strike — ponto de entrada.

    python main.py             tela cheia
    python main.py --janela    em janela
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
    windowed = any(arg in ("--janela", "--windowed", "-w") for arg in sys.argv[1:])
    Game(fullscreen=not windowed).run()


if __name__ == "__main__":
    main()
