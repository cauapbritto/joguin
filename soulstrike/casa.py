"""Hub da campanha: a Casa da turma, onde a aventura começa (e onde o CONTINUAR volta).

A casa tem os cantos da turma (Cauanzera, Aryel, Albeguinio e Borba Jr), a vitrine com os heróis
(cada um fala quando alguém chega perto), o livro do Cauanzera com um versículo por vez, as portas
trancadas (abrem conforme a campanha avança) e o quintal com a horta, o City do João e a saída para
a aventura. A saída só leva o grupo com a passagem coletiva (todos dentro, contagem de 2 s) e vai
para a sala inicial da fase salva. Ninguém volta para a casa no meio da campanha."""
import math
import random

import pygame

from . import casa_art as art
from . import config, crt, progress, theme
from .arena import MAPS_BY_KEY
from .campaign import TILE_PX, CoopMatch, Passage, _spread
from .entities import Entity, Particle, Wall
from .lobbies import CASA_SPLIT, CASA_TOP, cells_rect
from .matches import Result

HUB_MAP = "hub_casa"
T = TILE_PX
OY = CASA_TOP * T            # a casa começa abaixo das linhas escuras de cima
QY = CASA_SPLIT              # e o quintal logo abaixo da casa

# ── livro do Cauanzera (Almeida Revista e Corrigida) ──
VERSES = (
    ("JOÃO 3:16", "Porque Deus amou o mundo de tal maneira que deu o seu Filho unigênito, para que todo "
                  "aquele que nele crê não pereça, mas tenha a vida eterna."),
    ("ROMANOS 12:2", "E não sede conformados com este mundo, mas sede transformados pela renovação do vosso "
                     "entendimento, para que experimenteis qual seja a boa, agradável e perfeita vontade de Deus."),
    ("MARCOS 11:23", "Porque em verdade vos digo que qualquer que disser a este monte: Ergue-te e lança-te no "
                     "mar, e não duvidar em seu coração, mas crer que se fará aquilo que diz, tudo o que disser "
                     "lhe será feito."),
    ("JOÃO 10:10", "O ladrão não vem senão a roubar, a matar e a destruir; eu vim para que tenham vida e a "
                   "tenham com abundância."),
    ("JOÃO 1:14", "E o Verbo se fez carne e habitou entre nós, e vimos a sua glória, como a glória do "
                  "unigênito do Pai, cheio de graça e de verdade."),
)
VERSE_KEY = "livro_versiculo"

# ── falas da vitrine (no máximo 40 letras cada) ──
FALAS = {
    "guerreiro": ("ESCUDO NA FRENTE, PLANO NENHUM.", "SEGURA QUE A FLECHA TENSA ATRAVESSA.",
                  "INVESTIDA PRIMEIRO, PERGUNTA DEPOIS.", "ESPADA AFIADA, CABEÇA NEM TANTO.",
                  "QUEM FICA TONTO SOU EU? NUNCA."),
    "atirador": ("CINCO BALAS, CINCO AMIGOS.", "DEZOITO NO PENTE. CONTA AÍ.", "RECARREGANDO... FINGE QUE NÃO VIU.",
                 "MIRA É TUDO. A FACA É PLANO B.", "LEQUE ABERTO, PROBLEMA FECHADO."),
    "tanque": ("PODE ATIRAR. EU DEVOLVO.", "MURALHA LIGADA. RELAXA.", "CORRER? EU ANDO COM ESTILO.",
               "230 DE VIDA E ZERO PRESSA.", "A MAÇA RESOLVE. SEMPRE RESOLVE."),
    "ninja": ("VOCÊ NÃO ME VIU AQUI.", "A SHURIKEN VOLTA. EU NÃO.", "SILÊNCIO É MEU NOME DO MEIO.",
              "QUICA NA PAREDE, CAI NO ALVO.", "KATANA LIMPA, CONSCIÊNCIA TAMBÉM."),
    "velocista": ("JÁ VOLTEI. NEM FUI AINDA.", "TURBO LIGADO, FREIO DESLIGADO.", "ACERTOU? GANHOU EMBALO!",
                  "ESPERAR É PARA QUEM É LENTO.", "CHEGUEI PRIMEIRO, COMO SEMPRE."),
    "fantasma": ("TÔ AQUI. ALI. AQUI DE NOVO.", "PAREDE PARA MIM É SUGESTÃO.", "O ORBE TE ACHA. ELE SEMPRE ACHA.",
                 "NÃO ASSOMBRO. SÓ VISITO.", "A FOICE É DE ENFEITE. MENTIRA."),
    "tita": ("DANO? NÃO CONHEÇO.", "TRÊS SEGUNDOS DE INVENCÍVEL.", "A CORRENTE PUXA, O ESPADÃO FECHA.",
             "DEVAGAR E SEMPRE. MAIS DEVAGAR.", "ME EMPURRA. VAI. TENTA."),
    "pirata": ("VEM CÁ, QUE O GANCHO TE TRAZ.", "DOIS TIROS. NÃO PRECISO DE TRÊS.", "RECARGA LENTA, MIRA CERTA.",
               "ESSA CASA TEM TESOURO? TEM BAÚ?", "SABRE NA MÃO, MAR NO CORAÇÃO."),
    "geada": ("CALMA. ESFRIA A CABEÇA.", "NEVASCA CHEGANDO, SEGURA O CASACO.", "DEVAGARZINHO, IGUAL TODO MUNDO.",
              "ESSE CALOR DE CUIABRASA, VIU?", "O CRISTAL VOLTA SOZINHO. EU ESPERO."),
    "aryel": ("GREEN OU RED? SÓ GIRANDO.", "BAIXINHO, MAS DE MOTO.", "SE FALA.",
              "A GRANADA PASSA POR CIMA DO MURO.", "O CAPACETE É ARMA E É SEGURANÇA."),
    "cauanzera": ("BASQUETE, VÔLEI E 100 METROS.", "JÁ ABRIU O CHAMADO?", "JESUS TE AMA, RAPAZ.",
                  "CABO DE REDE: ALCANCE E SINAL.", "ESSA ARMADURA É DE UNO BRANCO."),
    "albeguinio": ("JÁ REINICIOU O WI-FI?", "OI SUMIDO.", "DIGITANDO... PRONTO, TRAVOU.",
                   "ESSE PENDRIVE TEM VÍRUS. DE PROPÓSITO.", "NÃO CONFIE NO SEU MELHOR AMIGO."),
    "borba": ("O EXO FUI EU QUE INVENTEI.", "PÃO QUENTINHO SAINDO AGORA!", "SEGURA QUE O CANHÃO CARREGA.",
              "METADE DO DANO, O DOBRO DO ESTILO.", "VAMOS DE CITY OU DE UNO?"),
    "faisca": ("QUER A BOLA? VAI TER QUE SUAR.", "A BOLA É MINHA, OBRIGADO.", "DRIBLE NÃO SE ENSINA.",
               "TOMAR DE MIM DEMORA, VIU?", "ONDE TEM GRAMA, TEM FAÍSCA."),
    "trovao": ("CABEÇA DE AÇO, CORAÇÃO MOLE.", "CRUZA QUE EU SUBO.", "NINGUÉM PULA MAIS ALTO.",
               "TROVÃO AVISA ANTES. EU NÃO.", "BOLA ALTA? É MINHA."),
    "ginga": ("BOLA COLADA NO PÉ.", "CORRENDO E SEM FREAR.", "GINGADO NÃO TEM MANUAL.",
              "OLHA O CHAPÉU, OLHA O CHAPÉU!", "QUEM PARA SOU EU, QUANDO EU QUISER."),
    "matador": ("NA ÁREA EU NÃO PERDOO.", "CHUTOU, É GOL.", "GOLEIRO, PODE IR SENTANDO.",
                "FARO NÃO SE COMPRA.", "PASSA A BOLA, PASSA A BOLA!"),
    "paredao": ("AQUI NÃO PASSA.", "A BOLA FANTASMA? PASSA NÃO.", "BLOQUEIO DE LONGE, CARA FECHADA.",
                "CORPO FECHADO, GOL FECHADO.", "ATACANTE BOM É ATACANTE PARADO."),
    "aryel_corrompido": ("O RED VEIO. E FICOU.", "CHOVE BOMBA, NÃO MOEDA.", "A SOMBRA TAMBÉM ANDA DE MOTO.",
                         "APOSTEI TUDO NO CRISTAL.", "ESSE MARTELO NÃO É DE OBRA."),
    "borba_corrompido": ("SOBRECARGA EM 3, 2, 1...", "O EXO AGORA PENSA SOZINHO.", "LAG LOBBY FECHOU. EU NÃO.",
                         "PULSO GIGANTE, EM LINHA RETA.", "A PADARIA FICOU SEM DONO."),
    "albeguinio_corrompido": ("FECHAMENTO DO MÊS!", "FALTOU O CARIMBO. CARIMBO!", "BOLETO VENCE HOJE. E AMANHÃ.",
                              "ASSINA AQUI, AQUI E AQUI.", "PROTOCOLO? NA OUTRA SALA."),
    "cauanzera_corrompido": ("OTIMIZAÇÃO TOTAL.", "A IARA SABE O QUE É MELHOR.", "PACOTE ENVIADO. SEM CONFIRMAÇÃO.",
                             "OITO CABOS, NENHUMA PACIÊNCIA.", "TENTOU DESLIGAR DA TOMADA?"),
}

# vitrine: os heróis na sala (esquerda e direita do tapete) e os craques no quintal
VITRINE = (("guerreiro", 12 * T + 20, 7 * T + 10), ("atirador", 13 * T + 30, 7 * T + 10),
           ("tanque", 14 * T + 40, 7 * T + 10), ("ninja", 12 * T + 45, 10 * T + 20),
           ("velocista", 14 * T + 15, 10 * T + 20),
           ("fantasma", 33 * T + 20, 7 * T + 10), ("tita", 34 * T + 30, 7 * T + 10),
           ("pirata", 35 * T + 40, 7 * T + 10), ("geada", 34 * T + 30, 10 * T + 20))
CRAQUES = ("faisca", "trovao", "ginga", "matador", "paredao")
# corrompido liberado: fica no canto do amigo (capítulo que libera, posição na casa)
CORROMPIDOS = (("aryel_corrompido", 1, 44 * T + 20, 6 * T + 30), ("borba_corrompido", 2, 37 * T, 9 * T + 20),
               ("albeguinio_corrompido", 3, 8 * T + 20, 13 * T), ("cauanzera_corrompido", 4, 6 * T, 5 * T + 20))

# portas trancadas: o que abre cada uma
DOORS = (
    ("sotao", "SÓTÃO", "ZERE O CAPÍTULO 1 PARA ABRIR"),
    ("oficina", "OFICINA", "ZERE O CAPÍTULO 2 PARA ABRIR"),
    ("garagem", "GARAGEM", "ZERE O CAPÍTULO 4 PARA ABRIR"),
    ("porao", "PORÃO", "ZERE A CAMPANHA PARA ABRIR"),
)

TALK_REACH = 86
TALK_FRAMES = 170
TALK_GAP = 70
BUBBLE_ROOM = 300           # largura de um balão: vizinhos mais perto que isso esperam a vez
WATERED = 8 * config.FPS          # canteiro regado fica com a florzinha por 8 s
BED_REACH = 46
BOOK_REACH = 70
DOOR_REACH = 96
FLOWER_COLORS = ((240, 110, 150), (250, 200, 80), (170, 120, 240), (250, 250, 250))


def door_open(key):
    """Porta trancada da casa já destravada pelo progresso salvo."""
    if key == "sotao":
        return progress.chapter_cleared(1)
    if key == "oficina":
        return progress.chapter_cleared(2)
    if key == "garagem":
        return progress.chapter_cleared(progress.LAST_CHAPTER)
    if key == "porao":
        return int(progress.load().get("vezes_zerada", 0) or 0) > 0
    return False


def next_verse():
    """O versículo desta vez: cada abertura do livro mostra o próximo (a ordem fica salva)."""
    data = progress.load()
    try:
        index = int(data.get(VERSE_KEY, 0)) % len(VERSES)
    except (TypeError, ValueError):
        index = 0
    data[VERSE_KEY] = (index + 1) % len(VERSES)
    progress.save(data)
    return VERSES[index]


# ─────────────────────────────────────────────
#  Peças da casa
# ─────────────────────────────────────────────
_BAKED = {}


def _bake(fn, *args, **kw):
    key = (fn.__name__, args, tuple(sorted(kw.items())))
    if key not in _BAKED:
        _BAKED[key] = art.bake(fn, *args, **kw)
    return _BAKED[key]


class Decor(Entity):
    """Móvel ou enfeite já desenhado. ``flat``: preso na parede ou no chão (fica por baixo de todo
    mundo); senão entra na ordem de profundidade pelo pé."""

    def __init__(self, x, y, baked, flat=False, foot_y=None):
        super().__init__(x, y)
        self.baked = baked
        self.flat = flat
        self.foot_y = y + baked.bottom - 8 if foot_y is None else foot_y

    @property
    def sort_y(self):
        return self.foot_y

    def update(self, match):
        pass

    def draw(self, surf, camera):
        b = self.baked
        surf.blit(b.image, (round(self.x + b.dx - camera.x), round(self.y + b.dy - camera.y)))


class Speaker:
    """Alguém da vitrine (ou o retrato de um amigo) que fala quando um jogador chega perto, uma
    frase por vez, na ordem, e volta ao começo depois da última."""

    def __init__(self, key, x, y, head_y=None):
        self.key = key
        self.x, self.y = x, y
        self.head_y = head_y if head_y is not None else y - config.SPRITE_HEIGHT - 26
        self.lines = FALAS[key]
        self.index = 0
        self.talk = 0
        self.gap = 0
        self.line = None

    def near(self, p):
        return p.alive_in_match and math.hypot(p.x - self.x, p.y - self.y) < TALK_REACH

    def update(self, match):
        if self.talk > 0:
            self.talk -= 1
            if self.talk == 0:
                self.gap = TALK_GAP
            return
        if self.gap > 0:
            self.gap -= 1
            return
        if any(self.near(p) for p in match.alive_players) and not match.crowded(self):
            self.line = self.lines[self.index % len(self.lines)]
            self.index += 1
            self.talk = TALK_FRAMES

    def draw(self, screen, cam, ui, assets):
        if self.talk <= 0 or not self.line:
            return
        sx, sy = cam.to_screen(self.x, self.head_y)
        draw_bubble(screen, ui, assets, self.line, round(sx), round(sy))


def draw_bubble(screen, ui, assets, text, x, y):
    """Balão de fala branco com a pontinha para baixo (x, y = a ponta)."""
    w = assets.text_width(text, theme.XS) + 14
    rect = pygame.Rect(0, 0, w, 20)
    rect.midbottom = (x, y - 6)
    rect.x = max(4, min(config.SCREEN_W - w - 4, rect.x))
    pygame.draw.rect(screen, theme.SHADOW, rect.move(2, 2))
    pygame.draw.rect(screen, (244, 238, 222), rect)
    pygame.draw.rect(screen, (40, 32, 40), rect, 1)
    pygame.draw.polygon(screen, (244, 238, 222), [(x - 5, rect.bottom - 1), (x + 5, rect.bottom - 1), (x, y)])
    ui.text(screen, text, theme.XS, (40, 32, 40), rect.center, shadow=False)


class Bed(Entity):
    """Canteiro da horta: ATACAR perto rega, e uma florzinha nasce por um tempo. Só enfeite."""

    def __init__(self, x, y, crops, color):
        super().__init__(x, y)
        self.rect = pygame.Rect(x - 4, y - 4, 108, 32)
        self.baked = _bake(art.bed, 100, 3, crops)
        self.color = color
        self.watered = 0
        self.wall = Wall(self.rect.x, self.rect.y, self.rect.w, self.rect.h, visible=False)

    @property
    def sort_y(self):
        return self.rect.bottom - 4

    def can_water(self, f):
        if not f.alive_in_match:
            return False
        r = self.rect
        dx = max(r.left - f.x, 0, f.x - r.right)
        dy = max(r.top - f.y, 0, f.y - r.bottom)
        return math.hypot(dx, dy) < BED_REACH

    def water(self, match):
        fresh = self.watered < WATERED - 60
        self.watered = WATERED
        for _ in range(14):                                     # gotinhas do regador
            match.particles.append(Particle(self.rect.centerx + random.uniform(-44, 44), self.rect.y - 20,
                                            random.uniform(-0.4, 0.4), random.uniform(0.6, 1.6), (120, 190, 250),
                                            random.randint(14, 24), 3, gravity=0.08))
        if fresh:
            match.popup(self.rect.centerx, self.rect.y - 30, "AS PLANTAS AGRADECEM", theme.MOSS)
            match.assets.play("select", 0.4)

    def update(self, match):
        if self.watered > 0:
            self.watered -= 1

    def draw(self, surf, camera):
        b = self.baked
        x, y = self.x - camera.x, self.y - camera.y
        surf.blit(b.image, (round(x + b.dx), round(y + b.dy)))
        if self.watered > 0:
            grow = min(1.0, (WATERED - self.watered) / 20)
            shrink = min(1.0, self.watered / 30)
            k = grow * shrink
            if k > 0.2:
                for i, fx in enumerate((24, 50, 76)):
                    fl = _bake(art.flower, self.color)
                    surf.blit(fl.image, (round(x + fx + fl.dx), round(y + 22 + fl.dy * k)))


class BookMenu:
    """O livro do Cauanzera aberto: o versículo da vez. Fecha com ATACAR ou ESQUIVA."""

    def __init__(self, match, fighter, verse):
        self.match = match
        self.fighter = fighter
        self.ref, self.text = verse
        self.age = 0

    def handle(self, inp):
        self.age += 1
        if self.age <= 1:
            return True                         # o ATACAR que abriu não fecha
        for action in ("attack", "confirm", "dodge", "special", "cancel"):
            if inp.pressed(action):
                self.match.assets.play("click", 0.3)
                return False
        return True

    def pick(self, item):
        return False

    def snapshot(self):
        return None                             # nada na loja do celular

    def draw(self, screen, ui, anchor):
        w = 340
        lines = ui.wrap(self.text, theme.XS, w - 40)
        h = 66 + len(lines) * 14 + 26
        x = max(8, min(config.SCREEN_W - w - 8, round(anchor[0]) - w // 2))
        y = max(60, min(config.SCREEN_H - h - 70, round(anchor[1]) - h - 70))
        rect = pygame.Rect(x, y, w, h)
        pygame.draw.rect(screen, theme.SHADOW, rect.move(3, 3))
        pygame.draw.rect(screen, (90, 30, 36), rect)                         # capa
        page = rect.inflate(-12, -12)
        pygame.draw.rect(screen, (246, 238, 214), page)
        ui.text(screen, "PALAVRA DO DIA", theme.XS, (150, 40, 50), (rect.centerx, page.y + 14), shadow=False)
        ty = page.y + 34
        for line in lines:
            ui.text(screen, line, theme.XS, (50, 36, 30), (rect.centerx, ty), shadow=False)
            ty += 14
        ui.text(screen, self.ref, theme.XS, (120, 90, 60), (rect.centerx, ty + 8), shadow=False)
        ui.text(screen, "ATACAR OU ESQUIVA: FECHAR", theme.XS, (150, 136, 110), (rect.centerx, page.bottom - 10),
                shadow=False)


# ─────────────────────────────────────────────
#  A partida da casa
# ─────────────────────────────────────────────
class HubMatch(CoopMatch):
    """A Casa da turma. ``story``: começo de campanha (a história da fase passa antes da sala inicial);
    no CONTINUAR vai direto."""

    lobby = True
    music = "camp"

    def __init__(self, game, run, story=True):
        self.story = story
        cfg = MAPS_BY_KEY[HUB_MAP]
        starts = _spread(cfg.markers["S"], len(run.session.slots))
        super().__init__(game, run, cfg.key, starts, (0.0, 1.0))
        art.use(self.assets)
        self.arena.floor = self.arena.floor.copy()          # o chão pintado é compartilhado: os tapetes vão na cópia
        self.speakers = []
        self.beds = []
        self.doors = []                                     # (chave, aberta, ponto, dica)
        self.big_flower = False
        self._furnish()
        r = pygame.Rect(cells_rect(cfg.markers["D"]))
        self.exit_rect = r
        self.arena.walls.append(Wall(r.x - 8, r.y + 24, r.w + 16, T, visible=False))
        self.door_area = pygame.Rect(r.x, r.y - 104, r.w, r.h + 104 - 16)
        self.passage = Passage(lambda p: self.door_area.collidepoint(p.x, p.y))
        if progress.chapter_cleared(4) and self.players:     # recompensa do capítulo 4: a IARA mascote
            from .mansao import IaraMascot
            self.add_effect(IaraMascot(self.players[0], self.assets.sprites.get("iara_nucleo")))

    # ── montagem ─────────────────────────────
    def _floor(self, fn, x, y, *args, **kw):
        fn(self.arena.floor, x, y, *args, **kw)        # pintado direto na cópia do chão (tapete é grande)

    def _put(self, fn, x, y, *args, foot=(), flat=False, foot_y=None, **kw):
        """Põe a peça ``fn`` em (x, y). ``foot``: retângulos (dx, dy, w, h) onde ninguém passa."""
        d = Decor(x, y, _bake(fn, *args, **kw), flat=flat, foot_y=foot_y)
        self.props.append(d)
        for fx, fy, fw, fh in foot:
            self.arena.walls.append(Wall(x + fx, y + fy, fw, fh, visible=False))
        return d

    def _furnish(self):
        put = self._put
        # parede de cima: janelas e as portas do sótão e da oficina
        put(art.window_wall, 13 * T, OY + 4, flat=True)
        put(art.window_wall, 32 * T, OY + 4, flat=True)
        self._door("sotao", art.locked_door, 21 * T, OY + 10, inside=art.inside_sotao)
        self._door("oficina", art.locked_door, 26 * T, OY + 10, inside=art.inside_oficina)
        # sala: tapete, mesa com cadeiras, sofás, luminárias e plantas
        self._floor(art.rug, 17 * T, OY + 5 * T, 14 * T, 6 * T)
        put(art.table, 21 * T, OY + 7 * T + 10, 6 * T, 60, foot=((0, 10, 6 * T, 60),))
        for k in range(4):
            put(art.chair, 21 * T + 20 + k * 56, OY + 7 * T - 14, foot=((2, 10, 16, 14),))
            put(art.chair, 21 * T + 20 + k * 56, OY + 9 * T + 4, foot=((2, 10, 16, 14),))
        put(art.sofa, 18 * T, OY + 11 * T + 30, 150, foot=((0, 6, 150, 38),))
        put(art.sofa, 27 * T, OY + 11 * T + 30, 150, (120, 70, 90), foot=((0, 6, 150, 38),))
        for x, y in ((16 * T + 20, OY + 4 * T + 20), (32 * T, OY + 4 * T + 20)):
            put(art.lamp, x, y, foot=((-8, 22, 16, 10),), foot_y=y + 30)
        for x, y in ((12 * T, OY + 3 * T), (36 * T, OY + 3 * T), (16 * T, OY + 13 * T + 20), (32 * T, OY + 13 * T + 20)):
            put(art.plant, x, y, foot=((-10, -10, 20, 14),))
        # a vitrine: cada herói fala quando alguém chega perto
        for key, x, y in VITRINE:
            self._hero(key, x, OY + y)
        # canto do Cauanzera (alto à esquerda): retrato, computador, livro, armadura de Uno e estante
        put(art.frame_portrait, 2 * T, OY + T - 18, "cauanzera", flat=True)
        self.speakers.append(Speaker("cauanzera", 2 * T + 24, OY + 2 * T + 10, head_y=OY + T - 24))
        put(art.pc_desk, 4 * T, OY + 2 * T, foot=((0, 20, 140, 18), (52, 66, 24, 16)))
        self.book = put(art.lectern_book, 2 * T + 10, OY + 5 * T + 20, foot=((-14, 30, 28, 12),))
        put(art.uno_armor, 9 * T + 10, OY + 6 * T, foot=((-30, -10, 60, 14),))
        put(art.shelf, 9 * T + 10, OY + T - 20, 70, foot=((0, 50, 70, 20),))
        # canto do Aryel (alto à direita): retrato, pôster, moto, capacetes e a roleta
        put(art.frame_portrait, 44 * T, OY + T - 18, "aryel", flat=True)
        self.speakers.append(Speaker("aryel", 44 * T + 24, OY + 2 * T + 10, head_y=OY + T - 24))
        put(art.poster, 39 * T, OY + T - 14, 60, 34, (40, 150, 70), "GREEN!", flat=True)
        put(art.moto, 41 * T, OY + 4 * T + 10, foot=((-56, -10, 112, 14),))
        put(art.helmet_rack, 45 * T + 20, OY + 3 * T + 10, foot=((-14, 62, 28, 12),))
        put(art.roulette_table, 38 * T, OY + 5 * T + 20, foot=((-30, 24, 60, 16),))
        # canto do Albeguinio (embaixo à esquerda): retrato no cavalete, arquivo, mesa e o roteador
        put(art.easel_portrait, 3 * T, OY + 10 * T, "albeguinio", foot=((-20, 70, 40, 12),))
        self.speakers.append(Speaker("albeguinio", 3 * T, OY + 12 * T, head_y=OY + 10 * T - 34))
        put(art.file_cabinet, T + 6, OY + 12 * T, foot=((0, 56, 40, 18),))
        put(art.office_desk, 4 * T, OY + 11 * T, foot=((0, 20, 140, 18), (58, 52, 24, 18)))
        put(art.router, 9 * T, OY + 10 * T + 10)
        # canto do Borba Jr (embaixo à direita): retrato, a padaria do João, o forno e o exo
        put(art.easel_portrait, 46 * T, OY + 8 * T, "borba", foot=((-20, 70, 40, 12),))
        self.speakers.append(Speaker("borba", 46 * T, OY + 10 * T, head_y=OY + 8 * T - 34))
        put(art.bakery, 38 * T, OY + 11 * T, foot=((0, 20, 220, 44),))
        put(art.oven, 43 * T + 30, OY + 10 * T + 20, foot=((0, 38, 80, 32),))
        put(art.exo_stand, 35 * T + 30, OY + 13 * T + 10, foot=((-24, -10, 48, 14),))
        # corrompidos liberados: cada um no canto do amigo
        for key, chapter, x, y in CORROMPIDOS:
            if progress.chapter_cleared(chapter):
                self._hero(key, x, OY + y)
        # quintal: a horta, a garagem, o City do João, o porão, os craques e a saída
        for i, (x, y, crops) in enumerate(((3 * T, QY + T, "sprout"), (8 * T + 20, QY + T, "tomate"),
                                           (3 * T, QY + 4 * T + 20, "tomate"), (8 * T + 20, QY + 4 * T + 20, "sprout"))):
            bed = Bed(x, y, crops, FLOWER_COLORS[i])
            self.beds.append(bed)
            self.props.append(bed)
            self.arena.walls.append(bed.wall)
        self.flower_at = (6 * T + 24, QY + 3 * T + 40)
        put(art.sign, 7 * T + 20, QY + 7 * T, "HORTA", foot=((-4, 12, 8, 10),))
        put(art.watering_can, 11 * T, QY + 7 * T)
        self._door("garagem", art.locked_door, 39 * T, QY + 5 * T - 20, w=100, inside=art.inside_garagem)
        put(art.city_car, 31 * T, QY + 5 * T, foot=((-86, -24, 172, 26),))
        self._door("porao", art.cellar_door, 14 * T, QY + 5 * T)
        for i, key in enumerate(CRAQUES):
            self._hero(key, 34 * T + 20 + i * 80, QY + 2 * T + 20)
        for x, y in ((17 * T, QY + 2 * T), (33 * T, QY + 7 * T), (45 * T, QY + 2 * T)):
            put(art.plant, x, y, foot=((-10, -10, 20, 14),))
        put(art.adventure_arch, 21 * T, QY + 8 * T, 6 * T, flat=True)

    def _hero(self, key, x, y):
        self._put(art.mannequin, x, y, key, foot=((-20, -10, 40, 14),))
        self.speakers.append(Speaker(key, x, y))

    def _door(self, key, fn, x, y, w=None, inside=None):
        name, hint = next((n, h) for k, n, h in DOORS if k == key)
        opened = door_open(key)
        if fn is art.cellar_door:
            label = name if opened else f"{name} · TRANCADO"
            self._floor(fn, x, y, label, opened=opened)
            spot = (x + 42, y + 28)
        else:
            closed = "TRANCADA" if key in ("oficina", "garagem") else "TRANCADO"
            label = name if opened else f"{name} · {closed}"
            kw = {"opened": opened}
            if opened and inside is not None:
                kw["inside"] = inside
            if w is not None:
                kw["w"] = w
            self._put(fn, x, y, label, flat=True, **kw)
            spot = (x + (w or 80) // 2, y + 64)
        self.doors.append((key, opened, spot, hint))

    # ── consultas ────────────────────────────
    @property
    def objective_text(self):
        return "CASA DA TURMA · TODOS NA SAÍDA DO QUINTAL PARA A AVENTURA"

    def objective(self):
        return self.exit_rect.centerx, self.exit_rect.y

    def crowded(self, speaker):
        """Outro da vitrine ali do lado já está falando (um balão por vez, senão um cobre o outro)."""
        return any(o is not speaker and o.talk > 0 and abs(o.x - speaker.x) < BUBBLE_ROOM
                   and abs(o.head_y - speaker.head_y) < 40 for o in self.speakers)

    def book_near(self, f):
        return f.alive_in_match and math.hypot(f.x - self.book.x, f.y - (self.book.y + 40)) < BOOK_REACH

    # ── ciclo ────────────────────────────────
    def update_stage(self):
        if self.frame == 1:
            if self.story:
                self._set_banner("CASA DA TURMA", "A AVENTURA COMEÇA NO QUINTAL", theme.BRASS)
            else:
                self._set_banner("CASA DA TURMA", f"CONTINUANDO DA FASE {self.run.phase_index + 1}", theme.BRASS)
        if self.banner and self.banner[3] > 130:
            self.banner = None
        players = self.alive_players
        if players:                         # quem está mais perto de alguém fala primeiro
            self.speakers.sort(key=lambda s: min(math.hypot(p.x - s.x, p.y - s.y) for p in players))
        for s in self.speakers:
            s.update(self)
        if not self.big_flower and self.beds and all(b.watered > 0 for b in self.beds):
            self.big_flower = True                    # os quatro canteiros regados juntos: a flor grande
            x, y = self.flower_at
            self.props.append(Decor(x, y, _bake(art.flower, (250, 120, 170), big=True)))
            self.burst(x, y - 30, (250, 160, 200), 26, speed=3)
            self.popup(x, y - 80, "A HORTA FLORESCEU!", theme.MOSS)
            self.assets.play("confirm", 0.5)
        if self.leaving:
            return
        if self.passage.update(self):
            self.leave()

    def interact(self, f):
        if self.passage.try_force(self, f):
            return True
        if self.book_near(f):
            self.menus[f] = BookMenu(self, f, next_verse())
            self.assets.play("click", 0.45)
            return True
        bed = next((b for b in self.beds if b.can_water(f)), None)
        if bed is not None:
            bed.water(self)
            return True
        return self.pick_ground(f)

    def _finish(self, won):
        """Saindo da casa: nada passa para a fase (nem o tempo; o relógio da campanha começa na sala inicial)."""
        self.won = won
        self.result = Result("CASA DA TURMA", theme.MOSS, self.players)
        self.finished = True

    def next_scene(self):
        from .scenes.campaign import start_phase
        return start_phase(self.game, self.run, story=self.story)

    def restart_scene(self):
        from .scenes.campaign import hub_scene
        return hub_scene(self.game, self.run, story=self.story)

    # ── desenho ──────────────────────────────
    def draw_screen_layer(self, screen, ui):
        cam = self.camera
        for s in self.speakers:
            s.draw(screen, cam, ui, self.assets)
        free = [p for p in self.alive_players if p not in self.menus]
        if any(self.book_near(p) for p in free):
            sx, sy = cam.to_screen(self.book.x, self.book.y - 40)
            color = theme.BRASS if (self.frame // 15) % 2 else theme.BONE
            ui.text(screen, "ATACAR: LER O LIVRO", theme.XS, color, (round(sx), round(sy)))
        for b in self.beds:
            if any(b.can_water(p) for p in free) and b.watered <= 0:
                sx, sy = cam.to_screen(b.rect.centerx, b.rect.y - 14)
                color = theme.BRASS if (self.frame // 15) % 2 else theme.BONE
                ui.text(screen, "ATACAR: REGAR", theme.XS, color, (round(sx), round(sy)))
        for key, opened, (x, y), hint in self.doors:
            if opened:
                continue
            if any(math.hypot(p.x - x, p.y - y) < DOOR_REACH for p in free):
                sx, sy = cam.to_screen(x, y + 40)
                ui.text(screen, hint, theme.XS, theme.BONE, (round(sx), round(sy)))
        self.draw_ground(screen, cam, ui)
        for f, menu in self.menus.items():
            at = cam.to_screen(f.x, f.y)
            crt.panel(screen, ("livro", f.slot), lambda s, menu=menu, at=at: menu.draw(s, ui, at))
        top = self.door_area.y
        sx, sy = cam.to_screen(self.exit_rect.centerx, top)
        ui.text(screen, "SAÍDA PARA A AVENTURA", theme.XS, theme.BRASS, (round(sx), round(sy) - 64))
        self.draw_passage(screen, ui, self.passage, self.door_area, (self.exit_rect.centerx, top - 4))
