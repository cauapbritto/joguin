"""Cria um cupom novo para a loja de CACOS sem deixar o código escrito no jogo.

Uso:  python tools/novo_cupom.py CODIGO CACOS [skin]

Mostra a linha para colar em COUPONS (soulstrike/cacos.py): o jogo só guarda a impressão digital
do código, então quem lê o código-fonte vê quanto o cupom dá, mas não qual é a palavra.
O código aceita maiúsculas e minúsculas, acento, espaço e pontuação ("Borba Jr" = "BORBAJR").
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from soulstrike.cacos import fingerprint, normalize  # noqa: E402
from soulstrike.skins import SKINS  # noqa: E402


def main(argv):
    if len(argv) < 2:
        print(__doc__)
        return 1
    code, amount = argv[0], int(argv[1])
    skin = argv[2] if len(argv) > 2 else None
    if skin is not None and skin not in SKINS:
        print(f"skin desconhecida: {skin}. Opções: {', '.join(SKINS)}")
        return 1
    print(f"# {normalize(code)[:2]}... ({amount} cacos{', ' + skin if skin else ''})")
    print(f'    "{fingerprint(code)}": ({amount}, {skin!r}),')
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
