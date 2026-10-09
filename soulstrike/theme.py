"""Paleta da interface. Tons tirados da arte das arenas (pedra roxa, tochas)."""

INK = (13, 11, 18)          # fundo
INK_2 = (22, 19, 30)        # painel
INK_3 = (33, 28, 44)        # painel em destaque
LINE = (56, 49, 72)         # bordas
LINE_HI = (96, 86, 118)
BONE = (234, 226, 206)      # texto principal
MUTED = (146, 138, 158)     # texto secundário
FAINT = (92, 86, 106)
BRASS = (228, 170, 76)      # destaque (cor das tochas)
EMBER = (222, 104, 56)
BLOOD = (200, 66, 60)
MOSS = (118, 186, 96)
SKY = (98, 150, 226)
SHADOW = (0, 0, 0)

# Cores por posição de jogador
SLOT_COLORS = {
    1: (92, 146, 236),
    2: (228, 86, 74),
    3: (96, 200, 172),
    4: (238, 176, 72),
}
SLOT_COLORS_DARK = {
    1: (34, 56, 102),
    2: (96, 34, 32),
    3: (30, 84, 72),
    4: (104, 72, 26),
}
CPU_COLOR = (170, 160, 180)

TEAM_COLORS = {0: (86, 136, 232), 1: (226, 80, 70)}
TEAM_NAMES = {0: "AZUL", 1: "VERMELHO"}

# Tamanhos de fonte (múltiplos de 8 deixam a fonte pixel nítida)
XS, S, M, L, XL = 8, 16, 24, 32, 48
