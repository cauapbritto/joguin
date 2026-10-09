"""Gera o executável do jogo para Windows.

Uso:
    pip install pyinstaller
    python tools/build_exe.py

Resultado: dist/SoulStrike.exe (um arquivo só, com sprites, sons e a página do celular dentro).
"""
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BUILD = ROOT / "build"


def make_icon(path):
    """Ícone 256x256: cabeça do Guerreiro sobre fundo escuro."""
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    import pygame

    sys.path.insert(0, str(ROOT))
    from soulstrike.assets import window_icon

    pygame.init()
    pygame.display.set_mode((1, 1))
    pygame.image.save(window_icon(256), str(path))
    pygame.quit()


def main():
    try:
        import PyInstaller.__main__
    except ImportError:
        sys.exit("PyInstaller não encontrado. Instale com:  pip install pyinstaller")
    BUILD.mkdir(exist_ok=True)
    icon = BUILD / "icon.png"
    make_icon(icon)
    sep = os.pathsep
    PyInstaller.__main__.run([
        str(ROOT / "main.py"),
        "--name", "SoulStrike",
        "--onefile",
        "--windowed",
        "--noconfirm",
        "--clean",
        "--icon", str(icon),
        "--add-data", f"{ROOT / 'assets'}{sep}assets",
        "--add-data", f"{ROOT / 'web'}{sep}web",
        "--exclude-module", "tkinter",
        "--exclude-module", "pkg_resources",    # o pygame tenta importar, mas funciona sem
        "--exclude-module", "setuptools",
        "--distpath", str(ROOT / "dist"),
        "--workpath", str(BUILD / "pyinstaller"),
        "--specpath", str(BUILD),
    ])
    print(f"\nPronto: {ROOT / 'dist' / 'SoulStrike.exe'}")


if __name__ == "__main__":
    main()
