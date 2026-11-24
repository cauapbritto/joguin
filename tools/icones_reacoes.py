"""Ícones das reações rápidas do app (GG, KKKK, VEM!, palmas): os mesmos desenhos 12x12 do balão da TV
(soulstrike/reacoes.py), num quadro 16x16 como os outros ícones do app.

Uso: python3 tools/icones_reacoes.py [pasta]   (padrão: android/app/src/main/res/drawable-nodpi)
"""
import sys
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from soulstrike.reacoes import ICONS, PALETTE  # noqa: E402

SIZE = 16


def icon(rows):
    img = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    ox = (SIZE - len(rows[0])) // 2
    oy = (SIZE - len(rows)) // 2
    for y, line in enumerate(rows):
        for x, ch in enumerate(line):
            color = PALETTE.get(ch)
            if color is not None:
                img.putpixel((ox + x, oy + y), tuple(color) + (255,))
    return img


def main():
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "android" / "app" / "src" / "main" / "res" / "drawable-nodpi"
    out.mkdir(parents=True, exist_ok=True)
    for key, rows in ICONS.items():
        path = out / f"r_{key}.png"
        icon(rows).save(path, optimize=True)
        print(path)


if __name__ == "__main__":
    main()
