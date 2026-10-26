"""Gera o pacote .deb do jogo para Linux Mint / Ubuntu / Debian (64 bits).

Uso (num Linux, de preferência na versão mais antiga que vai rodar o jogo):
    pip install -r requirements.txt pyinstaller
    python tools/build_deb.py

Resultado: dist/soulstrike_<versão>_amd64.deb, que não precisa de Python no PC de quem
for jogar. Instala com dois cliques (abre o Instalador de Pacotes) ou com
    sudo apt install ./dist/soulstrike_<versão>_amd64.deb
O jogo vai para /opt/soulstrike, com atalho no menu (Jogos) e o comando `soulstrike`.
"""
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BUILD = ROOT / "build"
sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_exe import make_icon  # noqa: E402

sys.path.insert(0, str(ROOT))
from soulstrike import __version__  # noqa: E402

# A versão do pacote é a do jogo (a mesma que o botão ATUALIZAR compara); numa tag v1.2.3, 1.2.3
VERSION = (os.environ.get("SOULSTRIKE_VERSION") or __version__).lstrip("v")
GLIBC = platform.libc_ver()[1] or "2.31"   # o executável só roda com glibc igual ou mais nova
ARCH = {"x86_64": "amd64", "aarch64": "arm64"}.get(platform.machine(), platform.machine())

DESKTOP = """[Desktop Entry]
Type=Application
Version=1.0
Name=Soul Strike
GenericName=Jogo de luta e aventura
Comment=Campanha cooperativa, duelo de arena e futebol em pixel art, para 1 a 4 jogadores
Exec=soulstrike
Icon=soulstrike
Terminal=false
Categories=Game;ActionGame;
Keywords=jogo;game;pixel;arena;futebol;
StartupWMClass=soulstrike
Actions=Janela;

[Desktop Action Janela]
Name=Jogar em janela
Exec=soulstrike --janela
"""

# Nome da janela igual ao do atalho: o painel agrupa o ícone certo
LAUNCHER = """#!/bin/sh
export SDL_VIDEO_X11_WMCLASS=soulstrike SDL_APP_ID=soulstrike
exec /opt/soulstrike/SoulStrike "$@"
"""

CONTROL = f"""Package: soulstrike
Version: {VERSION}
Section: games
Priority: optional
Architecture: {ARCH}
Maintainer: Soul Strike <soulstrike@users.noreply.github.com>
Depends: libc6 (>= {GLIBC})
Description: Soul Strike - um duelo de heróis em pixel art
 Campanha cooperativa, duelo de arena e futebol para 1 a 4 jogadores,
 no teclado ou com o celular como controle (pela rede Wi-Fi).
"""


def build_binary(extra=()):
    """Pasta build/pyinstaller-dist/SoulStrike com o executável (onedir: abre mais rápido que
    onefile). `extra`: opções a mais do PyInstaller (o tools/build_itch.py usa)."""
    try:
        import PyInstaller.__main__
    except ImportError:
        sys.exit("PyInstaller não encontrado. Instale com:  pip install pyinstaller")
    sep = os.pathsep
    PyInstaller.__main__.run([
        str(ROOT / "main.py"),
        "--name", "SoulStrike",
        "--onedir",
        "--windowed",
        "--noconfirm",
        "--clean",
        "--add-data", f"{ROOT / 'assets'}{sep}assets",
        "--add-data", f"{ROOT / 'web'}{sep}web",
        "--exclude-module", "tkinter",
        "--exclude-module", "pkg_resources",
        "--exclude-module", "setuptools",
        "--distpath", str(BUILD / "pyinstaller-dist"),
        "--workpath", str(BUILD / "pyinstaller"),
        "--specpath", str(BUILD),
        *extra,
    ])
    return BUILD / "pyinstaller-dist" / "SoulStrike"


def write(path, text, mode=0o644):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    path.chmod(mode)


def main():
    if sys.platform != "linux":
        sys.exit("O .deb precisa ser gerado num Linux (no Windows, use tools/build_exe.py).")
    if not shutil.which("dpkg-deb"):
        sys.exit("dpkg-deb não encontrado. Instale com:  sudo apt install dpkg")
    BUILD.mkdir(exist_ok=True)
    app = build_binary()

    pkg = BUILD / "deb"
    shutil.rmtree(pkg, ignore_errors=True)
    shutil.copytree(app, pkg / "opt" / "soulstrike", symlinks=True)
    write(pkg / "usr" / "bin" / "soulstrike", LAUNCHER, 0o755)
    write(pkg / "usr" / "share" / "applications" / "soulstrike.desktop", DESKTOP)
    icon = pkg / "usr" / "share" / "icons" / "hicolor" / "256x256" / "apps" / "soulstrike.png"
    icon.parent.mkdir(parents=True, exist_ok=True)
    make_icon(icon)
    write(pkg / "DEBIAN" / "control", CONTROL)
    for folder in [pkg, *pkg.rglob("*")]:
        if folder.is_dir():
            folder.chmod(0o755)

    out = ROOT / "dist" / f"soulstrike_{VERSION}_{ARCH}.deb"
    out.parent.mkdir(exist_ok=True)
    subprocess.run(["dpkg-deb", "--root-owner-group", "--build", str(pkg), str(out)], check=True)
    print(f"\nPronto: {out}")


if __name__ == "__main__":
    main()
