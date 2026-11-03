"""Texto da Release do GitHub a partir das novidades do jogo (soulstrike/novidades.py).

    python tools/notas_release.py 1.10.0 > notas.md

A tela de ATUALIZAR mostra as 4 primeiras linhas (sem os "- " e pulando as que começam com "#"),
então o texto começa com uma linha por página das novidades e depois traz tudo, página a página.
Sem versão, usa a do __init__.py; aceita "v1.10.0".
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from soulstrike import __version__  # noqa: E402
from soulstrike.novidades import NEWS, pages_of, summary  # noqa: E402


def notes(version):
    version = version.strip().lstrip("vV")
    entry = NEWS.get(version)
    if not entry:
        return f"Soul Strike {version}"
    out = [f"- {line}" for line in summary(entry)]
    for _, title, _, lines in pages_of(version, entry):
        out += ["", f"### {title}"]
        out.extend(f"- {line}" for line in lines)
    return "\n".join(out)


if __name__ == "__main__":
    print(notes(sys.argv[1] if len(sys.argv) > 1 else __version__))
