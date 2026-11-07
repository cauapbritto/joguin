"""Mapas: definição das arenas, chão pré-renderizado e colisão com paredes."""
import math
import random
from dataclasses import dataclass, field

import pygame

from . import lobbies, scenery
from .entities import Wall, WallStyle, push_circle_out

SOCCER_MAP = "campo_futebol"


class Pitch:
    """Medidas do campo de futebol. Muros, gols, linhas, largada e as zonas do jogo saem daqui."""
    W, H = 2240, 1260                      # 40% maior que o campo antigo (1600 x 900)
    EDGE = 20                              # muro de cima e de baixo; o gol fica atrás da linha
    LINE = 40                              # linha de fundo da esquerda (a da direita: W - LINE)
    GOAL = 160                             # boca do gol
    MID_Y = H / 2
    GOAL_TOP, GOAL_BOTTOM = H // 2 - GOAL // 2, H // 2 + GOAL // 2
    AREA_DEPTH, AREA_HALF = 250, 320       # grande área (fundo e metade da largura)
    SMALL_DEPTH, SMALL_HALF = 100, 150     # pequena área
    SPOT = 190                             # marca do pênalti, a partir da linha de fundo
    CIRCLE = 112                           # círculo central
    STRIPES = 20                           # faixas do gramado

    @classmethod
    def goal_x(cls, team):
        """Onde a bola entra no gol que o time defende (time 0 à esquerda)."""
        return cls.EDGE if team == 0 else cls.W - cls.EDGE

    @classmethod
    def walls(cls):
        W, H, E, L = cls.W, cls.H, cls.EDGE, cls.LINE
        top, bottom = cls.GOAL_TOP, cls.GOAL_BOTTOM
        return [(0, 0, W, E), (0, H - E, W, E),
                (E, E, L - E, top - E), (E, bottom, L - E, H - E - bottom),
                (W - L, E, L - E, top - E), (W - L, bottom, L - E, H - E - bottom)]

    @classmethod
    def spawns(cls):
        """Largada: time 0 à esquerda (vagas 0 e 2), time 1 à direita (1 e 3)."""
        x = round(cls.W * 0.19)
        up, down = round(cls.MID_Y - 130), round(cls.MID_Y + 130)
        return [(x, up), (cls.W - x, up), (x, down), (cls.W - x, down)]


class Court:
    """Medidas da quadra de basquete (as mesmas nas três quadras). A arte de cada uma segue isto."""
    W, H = 2000, 1200
    WALL = 20                              # muro invisível em volta (a bola quica nele)
    LEFT, RIGHT, TOP, BOTTOM = 80, 1920, 80, 1120     # linhas da quadra
    MID_Y = H / 2
    HOOP_IN = 104                          # aro (no chão) a partir da linha de fundo
    RIM_Z = 96                             # altura do aro
    RIM_R = 20                             # raio do aro
    BOARD_IN = 76                          # tabela a partir da linha de fundo
    BOARD_HALF = 60                        # meia largura da tabela
    BOARD_Z = (86, 156)                    # de que altura a que altura vai a tabela
    POLE_IN = -40                          # poste atrás da linha de fundo
    POLE_R = 14
    KEY_DEPTH, KEY_HALF = 380, 160         # garrafão
    THREE_R = 470                          # linha de 3 (a partir do aro)
    CORNER = 70                            # reta do canto: tão longe assim da lateral
    CORNER_LEN = 240                       # e desse tamanho, a partir da linha de fundo
    HOOP_SPRITE = (16, 380)                # canto do sprite da cesta da esquerda

    @classmethod
    def hoop_x(cls, side):
        """Aro da esquerda (0) ou da direita (1)."""
        return cls.LEFT + cls.HOOP_IN if side == 0 else cls.RIGHT - cls.HOOP_IN

    @classmethod
    def board_x(cls, side):
        return cls.LEFT + cls.BOARD_IN if side == 0 else cls.RIGHT - cls.BOARD_IN

    @classmethod
    def pole(cls, side):
        return (cls.LEFT + cls.POLE_IN if side == 0 else cls.RIGHT - cls.POLE_IN), cls.MID_Y

    @classmethod
    def in_key(cls, side, x, y):
        """Dentro do garrafão do aro `side`."""
        inside_x = x <= cls.LEFT + cls.KEY_DEPTH if side == 0 else x >= cls.RIGHT - cls.KEY_DEPTH
        return inside_x and abs(y - cls.MID_Y) <= cls.KEY_HALF

    @classmethod
    def is_three(cls, side, x, y):
        """Arremesso daqui, no aro `side`, vale 3?"""
        if y < cls.TOP + cls.CORNER or y > cls.BOTTOM - cls.CORNER:
            return True                     # canto: fora da reta
        return math.hypot(x - cls.hoop_x(side), y - cls.MID_Y) > cls.THREE_R

    @classmethod
    def bounds(cls):
        W, H, E = cls.W, cls.H, cls.WALL
        rects = [(0, 0, W, E), (0, H - E, W, E), (0, 0, E, H), (W - E, 0, E, H)]
        for side in (0, 1):
            px, py = cls.pole(side)
            r = cls.POLE_R
            rects.append((px - r, py - r, r * 2, r * 2))
        return rects

    @classmethod
    def spawns(cls):
        """Largada: time 0 à esquerda (vagas 0 e 2), time 1 à direita (1 e 3)."""
        up, down = cls.MID_Y - 150, cls.MID_Y + 150
        return [(500, up), (cls.W - 500, up), (500, down), (cls.W - 500, down)]


BASKET_MAPS = ("quadra_ginasio", "quadra_rua", "quadra_soul", "quadra_cuiabrasa")
SOCCER_MAPS = ("campo_futebol", "campo_cuiabrasa")
CUIABRASA_MAPS = {"cuiabrasa_praca", "quadra_cuiabrasa", "campo_cuiabrasa"}   # liberados ao zerar a campanha


@dataclass
class MapConfig:
    key: str
    name: str
    size: tuple
    walls: list                    # (x, y, w, h)
    spawns: list                   # pontos de partida
    floor: tuple = ((18, 16, 30), (22, 20, 35))
    wall_colors: tuple = ((50, 45, 65), (75, 65, 95), (30, 25, 40))
    bounds: list = field(default_factory=list)   # paredes invisíveis (a arte do fundo já mostra o muro)
    battle: bool = True
    theme: str = None              # cenário (chão, paredes, ambiente) de outro mapa; None = o próprio
    void: list = field(default_factory=list)     # áreas fora das salas (masmorra), pintadas de escuro
    markers: dict = field(default_factory=dict)  # acampamento: largada, fogueira, baú, entradas

    @property
    def scenery(self):
        return self.theme or self.key


MAPS = [
    MapConfig(
        "arena_classica", "Arena Clássica", (1600, 1200),
        walls=[(100, 100, 50, 250), (100, 850, 50, 250), (1450, 100, 50, 250), (1450, 850, 50, 250),
               (400, 300, 300, 50), (900, 300, 300, 50), (400, 850, 300, 50), (900, 850, 300, 50),
               (750, 570, 100, 60), (300, 570, 50, 60), (1250, 570, 50, 60)],
        spawns=[(420, 600), (1180, 600), (800, 200), (800, 1000)],
        bounds=[(0, 0, 1600, 24), (0, 1112, 1600, 88), (0, 0, 22, 1200), (1572, 0, 28, 1200)],
    ),
    MapConfig(
        "calabouco", "Calabouço", (1600, 1200),
        walls=[(0, 0, 1600, 30), (0, 0, 30, 1200), (1570, 0, 30, 1200), (0, 1170, 1600, 30),
               (200, 100, 30, 200), (1370, 100, 30, 200), (200, 900, 30, 200), (1370, 900, 30, 200),
               (400, 250, 200, 30), (1000, 250, 200, 30), (400, 920, 200, 30), (1000, 920, 200, 30),
               (700, 400, 200, 30), (700, 770, 200, 30), (600, 500, 30, 200), (970, 500, 30, 200)],
        spawns=[(400, 600), (1200, 600), (800, 150), (800, 1050)],
        floor=((34, 26, 22), (40, 31, 26)), wall_colors=((64, 30, 24), (100, 52, 40), (30, 14, 10)),
    ),
    MapConfig(
        "coliseu", "Coliseu", (1800, 1200),
        walls=[(700, 100, 40, 150), (1060, 100, 40, 150), (700, 950, 40, 150), (1060, 950, 40, 150),
               (400, 500, 40, 200), (1360, 500, 40, 200), (870, 200, 60, 60), (870, 940, 60, 60),
               (300, 200, 150, 30), (1350, 200, 150, 30), (300, 970, 150, 30), (1350, 970, 150, 30)],
        spawns=[(260, 600), (1540, 600), (900, 600), (900, 400)],
        bounds=[(0, 0, 1800, 52), (0, 0, 70, 1200), (1730, 0, 70, 1200), (0, 1140, 1800, 60)],
        wall_colors=((70, 62, 52), (104, 94, 78), (30, 26, 22)),
    ),
    MapConfig(
        "floresta", "Floresta Encantada", (2000, 1400),
        walls=[(0, 0, 2000, 30), (0, 0, 30, 1400), (1970, 0, 30, 1400), (0, 1370, 2000, 30),
               (300, 200, 40, 200), (1660, 200, 40, 200), (300, 1000, 40, 200), (1660, 1000, 40, 200),
               (600, 400, 200, 40), (1200, 400, 200, 40), (600, 960, 200, 40), (1200, 960, 200, 40),
               (900, 650, 200, 100), (400, 680, 60, 40), (1540, 680, 60, 40),
               (750, 620, 30, 160), (1220, 620, 30, 160)],
        spawns=[(520, 700), (1480, 700), (1000, 250), (1000, 1150)],
        floor=((30, 50, 26), (35, 58, 30)), wall_colors=((40, 66, 32), (66, 98, 50), (16, 28, 14)),
    ),
    MapConfig(
        "templo_gelado", "Templo Gelado", (1600, 1200),
        walls=[(0, 0, 1600, 30), (0, 0, 30, 1200), (1570, 0, 30, 1200), (0, 1170, 1600, 30),
               (400, 80, 30, 200), (1170, 80, 30, 200), (400, 920, 30, 200), (1170, 920, 30, 200),
               (200, 350, 150, 30), (1250, 350, 150, 30), (200, 820, 150, 30), (1250, 820, 150, 30),
               (700, 200, 200, 30), (700, 970, 200, 30), (580, 500, 30, 200), (990, 500, 30, 200),
               (750, 560, 100, 80)],
        spawns=[(400, 600), (1200, 600), (800, 360), (800, 840)],
        floor=((38, 48, 60), (46, 57, 70)), wall_colors=((52, 76, 100), (110, 150, 190), (20, 34, 50)),
    ),
    MapConfig(
        SOCCER_MAP, "Estádio", (Pitch.W, Pitch.H),
        walls=Pitch.walls(),
        spawns=Pitch.spawns(),
        floor=((44, 122, 58), (50, 134, 64)), wall_colors=((112, 102, 90), (150, 138, 122), (60, 52, 44)),
        battle=False,
    ),
    # recompensa do capítulo 4: o campo de Cuiabrasa, com a grama torrada pelo sol
    MapConfig(
        "campo_cuiabrasa", "Estádio de Cuiabrasa", (Pitch.W, Pitch.H),
        walls=Pitch.walls(),
        spawns=Pitch.spawns(),
        floor=((150, 140, 62), (162, 150, 70)), wall_colors=((150, 70, 50), (200, 110, 70), (80, 36, 26)),
        battle=False,
    ),
]
# Quadras de basquete: mesmas medidas, só a arte muda (assets/tiles/quadra_*)
MAPS += [
    MapConfig(key, name, (Court.W, Court.H), walls=[], spawns=Court.spawns(), bounds=Court.bounds(),
              floor=floor, battle=False)
    for key, name, floor in (("quadra_ginasio", "Ginásio", ((196, 142, 84), (34, 86, 168))),
                             ("quadra_rua", "Quadra de Rua", ((52, 56, 64), (164, 60, 50))),
                             ("quadra_soul", "Arena Soul Strike", ((30, 24, 44), (74, 32, 118))),
                             ("quadra_cuiabrasa", "Quadra de Cuiabrasa", ((110, 80, 56), (200, 80, 40))))
]
# Variações das arenas (a 2ª masmorra de cada fase da campanha; também valem no duelo)
MAPS += [
    MapConfig(
        "floresta_ruinas", "Ruínas da Floresta", (2000, 1400),
        walls=[(0, 0, 2000, 30), (0, 0, 30, 1400), (1970, 0, 30, 1400), (0, 1370, 2000, 30),
               (800, 520, 140, 40), (1060, 520, 140, 40), (800, 840, 140, 40), (1060, 840, 140, 40),
               (760, 520, 40, 120), (760, 760, 40, 120), (1200, 520, 40, 120), (1200, 760, 40, 120),
               (300, 250, 240, 40), (1460, 250, 240, 40), (300, 1110, 240, 40), (1460, 1110, 240, 40),
               (520, 600, 40, 200), (1440, 600, 40, 200), (980, 150, 40, 180), (980, 1070, 40, 180)],
        spawns=[(300, 700), (1700, 700), (1000, 420), (1000, 990)],
        theme="floresta",
    ),
    MapConfig(
        "calabouco_celas", "Celas do Calabouço", (1600, 1200),
        walls=[(0, 0, 1600, 30), (0, 0, 30, 1200), (1570, 0, 30, 1200), (0, 1170, 1600, 30),
               (300, 30, 30, 220), (600, 30, 30, 220), (970, 30, 30, 220), (1270, 30, 30, 220),
               (300, 950, 30, 220), (600, 950, 30, 220), (970, 950, 30, 220), (1270, 950, 30, 220),
               (500, 480, 60, 60), (1040, 480, 60, 60), (500, 660, 60, 60), (1040, 660, 60, 60),
               (200, 400, 200, 30), (1200, 400, 200, 30), (200, 770, 200, 30), (1200, 770, 200, 30)],
        spawns=[(400, 600), (1200, 600), (800, 180), (800, 1020)],
        theme="calabouco",
    ),
    MapConfig(
        "templo_patio", "Pátio do Templo", (1600, 1200),
        walls=[(0, 0, 1600, 30), (0, 0, 30, 1200), (1570, 0, 30, 1200), (0, 1170, 1600, 30),
               (250, 250, 150, 30), (1200, 250, 150, 30), (250, 920, 150, 30), (1200, 920, 150, 30),
               (560, 380, 30, 160), (1010, 380, 30, 160), (560, 660, 30, 160), (1010, 660, 30, 160),
               (760, 180, 80, 60), (760, 960, 80, 60), (380, 560, 80, 80), (1140, 560, 80, 80)],
        spawns=[(250, 600), (1350, 600), (800, 330), (800, 870)],
        theme="templo_gelado",
    ),
]


# Lag Lobby (capítulo 2 da campanha): só as duas salas sem perigo valem no duelo
MAPS += [
    MapConfig(
        "lag_saguao", "Saguão da Lag Lobby", (1600, 1200),
        walls=[(0, 0, 1600, 30), (0, 0, 30, 1200), (1570, 0, 30, 1200), (0, 1170, 1600, 30),
               (560, 100, 24, 220), (560, 440, 24, 120), (560, 740, 24, 120), (560, 980, 24, 190),
               (880, 500, 240, 40), (880, 540, 40, 120),
               (800, 220, 60, 60), (800, 920, 60, 60), (1250, 250, 60, 60), (1250, 890, 60, 60),
               (1380, 450, 120, 30), (1380, 760, 120, 30)],
        spawns=[(300, 600), (1300, 600), (1000, 360), (1000, 840)],
        theme="lag_escritorio", battle=False,
    ),
    MapConfig(
        "lag_openspace", "Open Space", (2000, 1400),
        walls=[(0, 0, 2000, 30), (0, 0, 30, 1400), (1970, 0, 30, 1400), (0, 1370, 2000, 30)]
              + [r for cx, cy in ((500, 300), (800, 300), (1200, 300), (1500, 300),
                                  (500, 1100), (800, 1100), (1200, 1100), (1500, 1100), (650, 700), (1350, 700))
                 for r in ((cx - 90, cy - 12, 180, 24), (cx - 12, cy + 12, 24, 70))]
              + [(900, 120, 200, 40), (900, 1240, 200, 40)],
        spawns=[(300, 700), (1700, 700), (1000, 450), (1000, 950)],
        theme="lag_escritorio",
    ),
    MapConfig(
        "lag_servidores", "Corredor de Servidores", (2000, 1400),
        walls=[(0, 0, 2000, 30), (0, 0, 30, 1400), (1970, 0, 30, 1400), (0, 1370, 2000, 30)]
              + [r for x in (500, 800, 1100, 1400) for r in ((x, 120, 60, 420), (x, 860, 60, 420))],
        spawns=[(300, 700), (1700, 700), (950, 300), (950, 1100)],
        theme="lag_datacenter", battle=False,
    ),
    MapConfig(
        "lag_laboratorio", "Laboratório do Exo", (1600, 1200),
        walls=[(0, 0, 1600, 30), (0, 0, 30, 1200), (1570, 0, 30, 1200), (0, 1170, 1600, 30),
               (300, 60, 80, 90), (520, 60, 80, 90), (1000, 60, 80, 90), (1220, 60, 80, 90),
               (300, 1050, 80, 90), (520, 1050, 80, 90), (1000, 1050, 80, 90), (1220, 1050, 80, 90),
               (450, 520, 40, 160), (1110, 520, 40, 160), (650, 320, 300, 30), (650, 850, 300, 30)],
        spawns=[(300, 600), (1300, 600), (800, 220), (800, 980)],
        theme="lag_datacenter",
    ),
    MapConfig(
        "lag_heliponto", "Heliponto", (1600, 1200),
        walls=[(0, 0, 1600, 30), (0, 0, 30, 1200), (1570, 0, 30, 1200), (0, 1170, 1600, 30),
               (250, 250, 120, 60), (1230, 250, 120, 60), (250, 880, 120, 60), (1230, 880, 120, 60),
               (560, 180, 60, 120), (980, 180, 60, 120), (560, 880, 60, 120), (980, 880, 60, 120),
               (700, 60, 200, 50)],
        spawns=[(250, 600), (1350, 600), (800, 360), (800, 840)],
        theme="lag_cobertura", battle=False,
    ),
    MapConfig(
        "lag_diretor", "Sala do Diretor", (1600, 1200),
        walls=[(0, 0, 1600, 30), (0, 0, 30, 1200), (1570, 0, 30, 1200), (0, 1170, 1600, 30),
               (680, 120, 240, 50), (200, 200, 40, 300), (1360, 200, 40, 300),
               (200, 850, 180, 40), (1220, 850, 180, 40), (480, 600, 50, 50), (1070, 600, 50, 50)],
        spawns=[(400, 600), (1200, 600), (800, 360), (800, 840)],
        theme="lag_escritorio", battle=False,
    ),
]


# Clínica Clepalovers (capítulo 3): no duelo só as salas sem perigo (consultórios e espelhos)
MAPS += [
    MapConfig(
        "clinica_espera", "Sala de Espera", (1600, 1200),
        walls=[(0, 0, 1600, 30), (0, 0, 30, 1200), (1570, 0, 30, 1200), (0, 1170, 1600, 30),
               (650, 250, 300, 44), (650, 294, 40, 70),                        # balcão da recepção
               (200, 500, 160, 40), (200, 800, 160, 40), (1240, 500, 160, 40), (1240, 800, 160, 40),
               (110, 150, 50, 50), (1440, 150, 50, 50), (110, 1000, 50, 50), (1440, 1000, 50, 50),
               (760, 680, 80, 80)],
        spawns=[(300, 650), (1300, 650), (800, 520), (800, 950)],
        theme="clinica", battle=False,
    ),
    MapConfig(
        "clinica_consultorios", "Corredor dos Consultórios", (2000, 1400),
        walls=[(0, 0, 2000, 30), (0, 0, 30, 1400), (1970, 0, 30, 1400), (0, 1370, 2000, 30),
               (30, 520, 190, 24), (320, 520, 380, 24), (800, 520, 420, 24), (1320, 520, 380, 24),
               (1800, 520, 170, 24),
               (30, 856, 190, 24), (320, 856, 380, 24), (800, 856, 420, 24), (1320, 856, 380, 24),
               (1800, 856, 170, 24),
               (500, 30, 24, 490), (1000, 30, 24, 490), (1500, 30, 24, 490),
               (500, 880, 24, 490), (1000, 880, 24, 490), (1500, 880, 24, 490),
               (240, 200, 120, 50), (740, 200, 120, 50), (1240, 200, 120, 50), (1720, 200, 120, 50),
               (240, 1130, 120, 50), (740, 1130, 120, 50), (1240, 1130, 120, 50), (1720, 1130, 120, 50)],
        spawns=[(300, 700), (1700, 700), (760, 360), (1260, 1040)],
        theme="clinica",
    ),
    MapConfig(
        "clinica_laser", "Sala do Laser", (1600, 1200),
        walls=[(0, 0, 1600, 30), (0, 0, 30, 1200), (1570, 0, 30, 1200), (0, 1170, 1600, 30),
               (380, 280, 60, 60), (1160, 280, 60, 60), (380, 860, 60, 60), (1160, 860, 60, 60),
               (700, 110, 200, 40), (700, 1050, 200, 40), (110, 560, 40, 80), (1450, 560, 40, 80)],
        spawns=[(300, 600), (1300, 600), (800, 360), (800, 840)],
        theme="clinica", battle=False,
    ),
    MapConfig(
        "clinica_spa", "Spa e Sauna", (2000, 1400),
        walls=[(0, 0, 2000, 30), (0, 0, 30, 1400), (1970, 0, 30, 1400), (0, 1370, 2000, 30),
               (480, 280, 170, 120), (1350, 280, 170, 120), (480, 1000, 170, 120), (1350, 1000, 170, 120),
               (860, 580, 280, 40), (860, 780, 280, 40), (860, 620, 40, 160), (1100, 620, 40, 160),
               (900, 170, 200, 30), (900, 1200, 200, 30)],
        spawns=[(300, 700), (1700, 700), (1000, 400), (1000, 1000)],
        theme="clinica_spa", battle=False,
    ),
    MapConfig(
        "clinica_espelhos", "Sala dos Espelhos", (1600, 1200),
        walls=[(0, 0, 1600, 30), (0, 0, 30, 1200), (1570, 0, 30, 1200), (0, 1170, 1600, 30),
               (300, 150, 24, 330), (300, 720, 24, 330), (1276, 150, 24, 330), (1276, 720, 24, 330),
               (520, 330, 260, 24), (820, 330, 260, 24), (520, 846, 260, 24), (820, 846, 260, 24),
               (560, 560, 24, 140), (1016, 560, 24, 140), (700, 600, 200, 24)],
        spawns=[(160, 600), (1440, 600), (800, 200), (800, 1000)],
        theme="clinica_vip",
    ),
    MapConfig(
        "clinica_adm", "Sala do Administrativo", (1600, 1200),
        walls=[(0, 0, 1600, 30), (0, 0, 30, 1200), (1570, 0, 30, 1200), (0, 1170, 1600, 30),
               (660, 120, 280, 54), (200, 200, 40, 300), (1360, 200, 40, 300),
               (200, 850, 140, 40), (1260, 850, 140, 40), (480, 600, 44, 44), (1076, 600, 44, 44)],
        spawns=[(400, 600), (1200, 600), (800, 360), (800, 840)],
        theme="clinica_adm", battle=False,
    ),
]

# Mansão do Carimbo (capítulo 4): Fila, Arquivo, Pátio, CPD, Reunião e o Núcleo da IARA
MAPS += [
    MapConfig(
        "mansao_fila", "Fila do Atendimento", (1600, 1200),
        walls=[(0, 0, 1600, 30), (0, 0, 30, 1200), (1570, 0, 30, 1200), (0, 1170, 1600, 30),
               (220, 130, 340, 44), (630, 130, 340, 44), (1040, 130, 340, 44),     # guichês
               (300, 500, 60, 60), (1240, 500, 60, 60), (300, 850, 60, 60), (1240, 850, 60, 60),
               (110, 680, 40, 200), (1450, 680, 40, 200)],                       # bancos de espera
        spawns=[(200, 600), (1400, 600), (800, 330), (800, 1000)],
        theme="mansao", battle=False,
    ),
    MapConfig(
        "mansao_arquivo", "Arquivo Geral", (2000, 1400),
        walls=[(0, 0, 2000, 30), (0, 0, 30, 1400), (1970, 0, 30, 1400), (0, 1370, 2000, 30)]
              + [(x, y, 500, 40) for y in (300, 560, 820, 1080) for x in (150, 750, 1350)],
        spawns=[(90, 700), (1910, 700), (1000, 170), (1000, 1230)],
        theme="mansao_arquivo", battle=False,
    ),
    MapConfig(
        "mansao_patio", "Pátio a 47°C", (2000, 1400),
        walls=[(0, 0, 2000, 30), (0, 0, 30, 1400), (1970, 0, 30, 1400), (0, 1370, 2000, 30),
               (400, 250, 300, 40), (1300, 250, 300, 40), (400, 1110, 300, 40), (1300, 1110, 300, 40),
               (250, 500, 120, 60), (250, 840, 120, 60), (1630, 500, 120, 60), (1630, 840, 120, 60),
               (700, 450, 60, 120), (1240, 830, 60, 120), (940, 330, 120, 60), (940, 1010, 120, 60)],
        spawns=[(150, 700), (1850, 700), (1000, 180), (1000, 1250)],
        theme="mansao_patio", battle=False,
    ),
    MapConfig(
        "mansao_cpd", "Subsolo do CPD", (1600, 1200),
        walls=[(0, 0, 1600, 30), (0, 0, 30, 1200), (1570, 0, 30, 1200), (0, 1170, 1600, 30),
               (300, 200, 50, 300), (300, 700, 50, 300), (600, 150, 50, 300), (600, 750, 50, 300),
               (950, 150, 50, 300), (950, 750, 50, 300), (1250, 200, 50, 300), (1250, 700, 50, 300)],
        spawns=[(160, 600), (1440, 600), (800, 600), (800, 1080)],
        theme="mansao_cpd", battle=False,
    ),
    MapConfig(
        "mansao_reuniao", "Sala de Reunião do Comitê", (1600, 1200),
        walls=[(0, 0, 1600, 30), (0, 0, 30, 1200), (1570, 0, 30, 1200), (0, 1170, 1600, 30),
               (600, 40, 400, 40),                                              # tela do projetor
               (500, 520, 600, 140),                                            # a mesa do comitê
               (200, 250, 40, 200), (1360, 250, 40, 200), (200, 780, 40, 200), (1360, 780, 40, 200)],
        spawns=[(300, 600), (1300, 600), (800, 360), (800, 860)],
        theme="mansao_reuniao", battle=False,
    ),
    MapConfig(
        "mansao_nucleo", "Núcleo da IARA", (1600, 1200),
        walls=[(0, 0, 1600, 30), (0, 0, 30, 1200), (1570, 0, 30, 1200), (0, 1170, 1600, 30),
               (640, 100, 320, 64),                                             # trono do carimbo
               (300, 300, 50, 50), (1250, 300, 50, 50), (300, 850, 50, 50), (1250, 850, 50, 50)],
        spawns=[(400, 600), (1200, 600), (800, 400), (800, 900)],
        theme="mansao_nucleo", battle=False,
    ),
]


# recompensa do capítulo 4: a praça de Cuiabrasa para o duelo (o pátio da mansão, carros e toldos)
MAPS += [
    MapConfig(
        "cuiabrasa_praca", "Praça de Cuiabrasa", (1600, 1200),
        walls=[(0, 0, 1600, 30), (0, 0, 30, 1200), (1570, 0, 30, 1200), (0, 1170, 1600, 30),
               (300, 220, 120, 60), (1180, 220, 120, 60), (300, 920, 120, 60), (1180, 920, 120, 60),
               (740, 160, 60, 120), (800, 920, 60, 120), (520, 560, 160, 40), (920, 600, 160, 40)],
        spawns=[(200, 600), (1400, 600), (800, 380), (800, 820)],
        theme="mansao_patio",
    ),
]


def battle_maps(cleared=None):
    """Mapas do duelo que dá para escolher (os de Cuiabrasa só depois de zerar a campanha)."""
    if cleared is None:
        from . import progress
        cleared = progress.chapter_cleared(4)
    return [m for m in BATTLE_MAPS if cleared or m.key not in CUIABRASA_MAPS]


def basket_maps(cleared=None):
    if cleared is None:
        from . import progress
        cleared = progress.chapter_cleared(4)
    return tuple(k for k in BASKET_MAPS if cleared or k not in CUIABRASA_MAPS)


def soccer_maps(cleared=None):
    if cleared is None:
        from . import progress
        cleared = progress.chapter_cleared(4)
    return tuple(k for k in SOCCER_MAPS if cleared or k not in CUIABRASA_MAPS)


# Sala de luta do meio de cada fase (a fase é um mapa só: masmorra 1, esta sala e a masmorra final).
# Todas do mesmo tamanho, com a passagem livre no meio da parede da esquerda e no meio da de baixo.
SALA_SIZE = (1200, 880)
_SALA_BORDER = [(0, 0, 1200, 30), (0, 0, 30, 880), (1170, 0, 30, 880), (0, 850, 1200, 30)]
_SALA_SHAPES = (
    [(260, 200, 80, 80), (860, 200, 80, 80), (260, 600, 80, 80), (860, 600, 80, 80), (540, 400, 120, 80)],
    [(200, 170, 300, 30), (700, 170, 300, 30), (200, 680, 300, 30), (700, 680, 300, 30), (585, 330, 30, 220)],
    [(420, 250, 40, 140), (740, 250, 40, 140), (420, 490, 40, 140), (740, 490, 40, 140), (520, 420, 160, 40)],
)
SALAS = (("sala_floresta", "Bosque Fechado", "floresta", 0),
         ("sala_calabouco", "Galeria das Correntes", "calabouco", 1),
         ("sala_templo", "Claustro de Gelo", "templo_gelado", 2),
         ("sala_recepcao", "Sala de Treinamento", "lag_escritorio", 1),
         ("sala_datacenter", "Sala de Cabos", "lag_datacenter", 0),
         ("sala_cobertura", "Terraço", "lag_cobertura", 2),
         ("sala_clinica_recepcao", "Sala de Avaliação", "clinica", 0),
         ("sala_procedimentos", "Sala de Massagem", "clinica_spa", 2),
         ("sala_suite_vip", "Closet VIP", "clinica_vip", 1),
         ("sala_mansao_sede", "Protocolo Geral", "mansao", 2),
         ("sala_mansao_patio", "Estacionamento", "mansao_patio", 0),
         ("sala_mansao_gabinete", "Antessala do Gabinete", "mansao_reuniao", 1))
MAPS += [MapConfig(key, name, SALA_SIZE, walls=_SALA_BORDER + _SALA_SHAPES[shape],
                   spawns=[(160, 440), (1040, 440), (600, 120), (600, 760)], theme=theme, battle=False)
         for key, name, theme, shape in SALAS]


def _casa():
    """Hub da campanha: a Casa da turma com o quintal (lobbies.CASA)."""
    size, walls, void, markers = lobbies.casa_parse()
    return MapConfig("hub_casa", lobbies.CASA[0], size, walls=walls, spawns=markers["S"], battle=False,
                     theme="casa", void=void, markers=markers)


def _garagem():
    """A garagem da Casa, lá embaixo (lobbies.GARAGEM): o hall dos carros e o salão dos corrompidos."""
    size, walls, void, markers = lobbies.parse(lobbies.GARAGEM[1])
    return MapConfig("garagem_casa", lobbies.GARAGEM[0], size, walls=walls, spawns=markers["S"], battle=False,
                     theme="lag_garagem", void=void, markers=markers)


MAPS.append(_casa())
MAPS.append(_garagem())
MAPS_BY_KEY = {m.key: m for m in MAPS}
BATTLE_MAPS = [m for m in MAPS if m.battle]


class Arena:
    def __init__(self, cfg, assets):
        self.cfg = cfg
        self.width, self.height = cfg.size
        style = scenery.wall_style(cfg.scenery) or WallStyle(*cfg.wall_colors)
        textures = assets.wall_textures.get(cfg.key, {})
        self.walls = []
        for x, y, w, h in cfg.walls:
            wall = Wall(x, y, w, h)
            wall.style = style
            wall.image = _fit_texture(textures, w, h)
            self.walls.append(wall)
        for x, y, w, h in cfg.bounds:
            self.walls.append(Wall(x, y, w, h, visible=False))
        for wall in self.walls:
            wall.prepare()          # pronto antes da partida começar (nada de tranco no primeiro quadro)
        self.floor = self._render_floor(assets.backgrounds.get(cfg.key))
        self.ambience = scenery.create_ambience(cfg.scenery, cfg.size, self.walls)
        self.room = pygame.Rect(0, 0, self.width, self.height)

    # ── sala da luta ─────────────────────────
    # Numa arena comum a sala é o mapa inteiro. Na fase em mapa só (mapa_fase.PhaseArena) é a sala
    # de luta onde o grupo está: os perigos, os chefes e os portais dos inimigos ficam dentro dela.
    def at(self, x, y):
        """Ponto (x, y) medido do canto da sala, em coordenadas do mapa."""
        return self.room.x + x, self.room.y + y

    def reset_room(self):
        self.room = pygame.Rect(0, 0, self.width, self.height)

    @property
    def size(self):
        return self.width, self.height

    # ── colisão ──────────────────────────────
    def resolve(self, body):
        """Empurra um corpo circular para fora das paredes e para dentro do mapa."""
        hit = None
        for _ in range(2):
            moved = False
            for wall in self.walls:
                res = push_circle_out(body.x, body.y, body.radius, wall.rect)
                if res:
                    body.x, body.y, nx, ny = res
                    hit = (nx, ny)
                    moved = True
            if not moved:
                break
        r = body.radius
        body.x = min(max(body.x, r), self.width - r)
        body.y = min(max(body.y, r), self.height - r)
        return hit

    def is_free(self, x, y, radius):
        if not (radius <= x <= self.width - radius and radius <= y <= self.height - radius):
            return False
        return not any(w.overlaps_circle(x, y, radius) for w in self.walls)

    def free_spot(self, x, y, radius):
        """Ponto livre mais próximo de (x, y), procurando em espiral."""
        if self.is_free(x, y, radius):
            return x, y
        for dist in range(10, 400, 10):
            for k in range(16):
                a = k * math.pi / 8
                px, py = x + math.cos(a) * dist, y + math.sin(a) * dist
                if self.is_free(px, py, radius):
                    return px, py
        return x, y

    def random_free_spot(self, radius, rng=random):
        """Ponto livre sorteado dentro da sala."""
        r = self.room
        for _ in range(80):
            x = rng.uniform(r.x + 80, r.right - 80)
            y = rng.uniform(r.y + 80, r.bottom - 80)
            if self.is_free(x, y, radius + 6):
                return x, y
        return r.centerx, r.centery

    def blocks_segment(self, a, b):
        return any(w.rect.clipline(a, b) for w in self.walls)

    # ── desenho ──────────────────────────────
    def draw_floor(self, surf, camera, view_size):
        area = pygame.Rect(int(camera.x), int(camera.y), *view_size)
        surf.blit(self.floor, (0, 0), area)

    def draw_walls(self, surf, camera):
        view = pygame.Rect(int(camera.x), int(camera.y), *surf.get_size())
        for wall in self.walls:
            if wall.visible and view.colliderect(wall.area):     # fora da câmera não desenha
                wall.draw(surf, camera)

    def draw_ambience(self, surf, camera, frame, layer):
        self.ambience.draw(surf, camera, frame, layer)

    def thumbnail(self, size):
        """Miniatura do mapa para a tela de seleção."""
        full = self.floor.copy()

        class _Origin:
            x = y = 0
        self.draw_walls(full, _Origin)
        return pygame.transform.smoothscale(full, size)

    def _render_floor(self, background):
        surf = pygame.Surface((self.width, self.height))
        if background is not None:
            surf.blit(pygame.transform.scale(background, (self.width, self.height)), (0, 0))
            return surf
        if self.cfg.key in SOCCER_MAPS:
            _soccer_pitch(surf, self.cfg.floor)
            return surf
        if self.cfg.key in BASKET_MAPS:
            _basket_court(surf, self.cfg.floor)        # sem a arte: só as linhas
            return surf
        painted = scenery.paint_floor(self.cfg.key, (self.width, self.height), self.cfg.theme, self.cfg.void)
        if painted is not None:
            return painted
        rng = random.Random(self.cfg.key)
        a, b = self.cfg.floor
        grout = tuple(max(0, c - 10) for c in a)
        for gx in range(0, self.width, 32):
            for gy in range(0, self.height, 32):
                base = a if ((gx // 32) + (gy // 32)) % 2 else b
                j = rng.randint(-3, 3)
                color = tuple(max(0, min(255, c + j)) for c in base)
                surf.fill(color, (gx, gy, 32, 32))
                surf.fill(grout, (gx, gy, 32, 1))
                surf.fill(grout, (gx, gy, 1, 32))
                if rng.random() < 0.08:
                    surf.fill(grout, (gx + rng.randint(6, 22), gy + rng.randint(6, 22), 3, 2))
        return surf


def _fit_texture(textures, w, h):
    if (w, h) in textures:
        return textures[(w, h)]
    for (tw, th), img in textures.items():
        if tw == w and th > h:                     # mesma largura: junta topo + base
            out = pygame.Surface((w, h), pygame.SRCALPHA)
            top = h // 2
            out.blit(img, (0, 0), (0, 0, w, top))
            out.blit(img, (0, top), (0, th - (h - top), w, h - top))
            return out
        if th == h and tw > w:                     # mesma altura: junta esquerda + direita
            out = pygame.Surface((w, h), pygame.SRCALPHA)
            left = w // 2
            out.blit(img, (0, 0), (0, 0, left, h))
            out.blit(img, (left, 0), (tw - (w - left), 0, w - left, h))
            return out
    return None


def _basket_court(surf, colors):
    C = Court
    floor, paint = colors
    surf.fill(tuple(c * 3 // 4 for c in floor))
    surf.fill(floor, (C.LEFT, C.TOP, C.RIGHT - C.LEFT, C.BOTTOM - C.TOP))
    line = (240, 240, 232)
    cy = round(C.MID_Y)
    pygame.draw.circle(surf, paint, (C.W // 2, cy), 120)
    pygame.draw.circle(surf, line, (C.W // 2, cy), 120, 6)
    pygame.draw.rect(surf, line, (C.LEFT, C.TOP, C.RIGHT - C.LEFT, C.BOTTOM - C.TOP), 6)
    surf.fill(line, (C.W // 2 - 3, C.TOP, 6, C.BOTTOM - C.TOP))
    for side in (0, 1):
        hx = C.hoop_x(side)
        kx = C.LEFT if side == 0 else C.RIGHT - C.KEY_DEPTH
        key = pygame.Rect(kx, cy - C.KEY_HALF, C.KEY_DEPTH, C.KEY_HALF * 2)
        surf.fill(paint, key)
        pygame.draw.rect(surf, line, key, 6)
        reach = math.sqrt(C.THREE_R ** 2 - (C.MID_Y - C.TOP - C.CORNER) ** 2)
        ang = math.atan2(C.MID_Y - C.TOP - C.CORNER, reach)
        arc = pygame.Rect(hx - C.THREE_R, cy - C.THREE_R, C.THREE_R * 2, C.THREE_R * 2)
        a0, a1 = (-ang, ang) if side == 0 else (math.pi - ang, math.pi + ang)
        pygame.draw.arc(surf, line, arc, a0, a1, 6)
        end = hx + reach if side == 0 else hx - reach
        for y in (C.TOP + C.CORNER, C.BOTTOM - C.CORNER):
            x0, x1 = sorted((C.LEFT if side == 0 else C.RIGHT, end))
            surf.fill(line, (x0, y - 3, x1 - x0, 6))


def _soccer_pitch(surf, colors):
    P = Pitch
    w, h = surf.get_size()
    a, b = colors
    stripe = w / P.STRIPES
    for i in range(P.STRIPES):
        x0, x1 = round(i * stripe), round((i + 1) * stripe)
        surf.fill(a if i % 2 else b, (x0, 0, x1 - x0, h))
    line = (226, 232, 214)
    cx, cy = w // 2, h // 2
    left, right = P.LINE, w - P.LINE
    pygame.draw.line(surf, line, (cx, P.EDGE), (cx, h - P.EDGE), 3)
    pygame.draw.circle(surf, line, (cx, cy), P.CIRCLE, 3)
    surf.fill(line, (cx - 4, cy - 4, 8, 8))
    for depth, half in ((P.AREA_DEPTH, P.AREA_HALF), (P.SMALL_DEPTH, P.SMALL_HALF)):
        pygame.draw.rect(surf, line, (left, cy - half, depth, half * 2), 3)
        pygame.draw.rect(surf, line, (right - depth, cy - half, depth, half * 2), 3)
    for sx in (left + P.SPOT, right - P.SPOT):
        surf.fill(line, (sx - 3, cy - 3, 6, 6))
    cr = 40
    top, bottom = P.EDGE, h - P.EDGE
    corners = ((left, top, 1.5 * math.pi, 2 * math.pi), (right, top, math.pi, 1.5 * math.pi),
               (left, bottom, 0, 0.5 * math.pi), (right, bottom, 0.5 * math.pi, math.pi))
    for cx, cy, a0, a1 in corners:
        pygame.draw.arc(surf, line, (cx - cr, cy - cr, cr * 2, cr * 2), a0, a1, 3)
