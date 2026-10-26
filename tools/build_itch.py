"""Gera a pasta do jogo para enviar ao itch.io (Windows ou Linux, conforme o PC que roda).

Uso:
    pip install -r requirements.txt pyinstaller
    python tools/build_itch.py

Resultado: dist/itch/<windows|linux>/, com o executável (não precisa de Python), as
bibliotecas, o .itch.toml (diz ao app do itch.io o que abrir) e o LICENCAS.md. O
GitHub Actions (.github/workflows/itch.yml) gera as duas e envia com o butler.

ITCH_GAME=usuario/jogo (o endereço usuario.itch.io/jogo) grava a página do itch.io
dentro do jogo: na cópia do itch.io o botão ATUALIZAR abre essa página.
"""
import json
import os
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BUILD = ROOT / "build"
sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_deb import build_binary  # noqa: E402
from build_exe import make_icon  # noqa: E402

CHANNEL = "windows" if sys.platform == "win32" else "linux" if sys.platform == "linux" else None
EXE = "SoulStrike.exe" if sys.platform == "win32" else "SoulStrike"

# O app do itch.io mostra estas opções no botão "Jogar"
ITCH_TOML = """[[actions]]
name = "Jogar"
path = "{exe}"

[[actions]]
name = "Jogar em janela"
path = "{exe}"
args = ["--janela"]
"""


def page_url(game):
    """'usuario/soul-strike' -> 'https://usuario.itch.io/soul-strike' ('' se não for nesse formato)."""
    user, _, slug = (game or "").strip().partition("/")
    return f"https://{user}.itch.io/{slug}" if user and slug and "/" not in slug else ""


def main():
    if CHANNEL is None:
        sys.exit("Gere no Windows ou no Linux (o itch.io recebe uma pasta de cada).")
    BUILD.mkdir(exist_ok=True)
    loja = BUILD / "loja.json"
    loja.write_text(json.dumps({"loja": "itch", "pagina": page_url(os.environ.get("ITCH_GAME"))}),
                    encoding="utf-8")
    icon = BUILD / "icon.png"
    make_icon(icon)
    app = build_binary(["--icon", str(icon), "--add-data", f"{loja}{os.pathsep}."])

    out = ROOT / "dist" / "itch" / CHANNEL
    shutil.rmtree(out, ignore_errors=True)
    shutil.copytree(app, out, symlinks=True)
    (out / ".itch.toml").write_text(ITCH_TOML.format(exe=EXE), encoding="utf-8")
    shutil.copy2(ROOT / "LICENCAS.md", out / "LICENCAS.md")
    print(f"\nPronto: {out} (abra {out / EXE})")


if __name__ == "__main__":
    main()
