"""Hub da campanha: a Casa da turma, onde a aventura começa (e onde o CONTINUAR volta).

A casa tem os cantos da turma (Cauanzera, Aryel, Albeguinio e Borba Jr), a vitrine com os heróis
(cada um fala quando alguém chega perto e aperta ATACAR), o livro do Cauanzera com um versículo por vez, as portas
trancadas (abrem conforme a campanha avança) e o quintal com a horta e o City do João, que é a saída
para a aventura: com todos em volta do carro (passagem coletiva, contagem de 2 s), o grupo vai de City
(scenes/viagem.py), o carro quebra no caminho e a fase salva começa na abertura. Ninguém volta para a casa no meio da campanha."""
import math
import random

import pygame

from . import casa_art as art
from . import computador, config, crt, luz_casa, mascotes, progress, skins, theme
from .guarda_roupa import Lockers, WardrobeMenu
from .loja import ShopMenu, ShopStand
from .arena import MAPS_BY_KEY
from .campaign import TILE_PX, CoopMatch, Passage, _spread
from .entities import Entity, Particle, Wall
from .fighter import UNO_HITS
from .lobbies import CASA_SPLIT, CASA_TOP
from .matches import Result
from .net.remote import hub
from .para_onde import ChapterPickMenu

HUB_MAP = "hub_casa"
T = TILE_PX
OY = CASA_TOP * T            # a casa começa abaixo das linhas escuras de cima
QY = CASA_SPLIT              # e o quintal logo abaixo da casa
CITY_AT = (31 * T, QY + 5 * T)  # o City do João no quintal (chão no meio do carro): a saída
GARAGE_DOOR = (39 * T + 50, QY + 5 * T + 44)   # frente da porta da garagem (onde o ATACAR desce)

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
# corrompidos: (chave, capítulo que libera, x, y antigos no canto do amigo). Hoje ficam no salão da garagem.
CORROMPIDOS = (("aryel_corrompido", 1, 44 * T + 20, 6 * T + 30), ("borba_corrompido", 2, 37 * T, 9 * T + 20),
               ("albeguinio_corrompido", 3, 8 * T + 20, 13 * T), ("cauanzera_corrompido", 4, 6 * T, 5 * T + 20))

# portas trancadas: o que abre cada uma
DOORS = (
    ("sotao", "SÓTÃO", "ZERE O CAPÍTULO 1 PARA ABRIR"),
    ("oficina", "OFICINA", "ZERE O CAPÍTULO 2 PARA ABRIR"),
    ("garagem", "GARAGEM", ""),                    # sempre aberta: é onde se escolhe o carro
    ("porao", "PORÃO", "ZERE A CAMPANHA PARA ABRIR"),
)

# garagem: com o que o grupo sai da Casa (chave, nome, capítulo que precisa zerar para liberar)
VEHICLES = (("city", "CITY DO JOÃO", 0), ("uno", "UNO BRANCO", 1), ("moto", "MOTO DO ARYEL", 2))
UNO_STAND = (9 * T + 10, OY + 6 * T)
LOCKERS_AT = (17 * T + 20, QY + 2 * T)  # os 4 armários de vestir as skins (meio da fileira, pé no chão)
SHOP_AT = (12 * T + 30, QY + 3 * T)          # o balcão da loja de CACOS (pé no chão)        # o suporte da armadura de Uno no canto do Cauanzera


def vehicle_ready(key):
    chapter = next(c for k, _, c in VEHICLES if k == key)
    return chapter == 0 or computador.freed() or progress.chapter_cleared(chapter)


FREE_FRAMES = 110          # tela branca do LIBERANDO... antes da casa voltar
GRAU_FRAMES = 100          # moto do Aryel empinada
SPIN_MIN = 0.004           # roleta para quando gira mais devagar que isso
BREAD_FRAMES = 70          # da senha ao pão saindo
USE_REACH = 44             # perto da mesa, da moto, da roleta ou do balcão
TALK_REACH = 86
TALK_FRAMES = 170
BUBBLE_ROOM = 300           # largura de um balão: o vizinho mais perto que isso para de falar
WATERED = 8 * config.FPS          # canteiro regado fica com a florzinha por 8 s
BED_REACH = 46
BOOK_REACH = 70
SCREEN_EVERY = 12                     # quadros entre uma cópia da tela do computador e outra
DOOR_REACH = 96
FLOWER_COLORS = ((240, 110, 150), (250, 200, 80), (170, 120, 240), (250, 250, 250))


def door_open(key):
    """Porta trancada da casa já destravada pelo progresso salvo (ou pelo LIBERAR TUDO)."""
    if computador.freed():
        return True
    if key == "sotao":
        return progress.chapter_cleared(1)
    if key == "oficina":
        return progress.chapter_cleared(2)
    if key == "garagem":
        return True
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
    """Alguém da vitrine (ou o retrato de um amigo) que fala quando um jogador chega perto e aperta
    ATACAR: uma frase por toque, na ordem, e volta ao começo depois da última. Perto, sem falar,
    mostra um balãozinho com "..." para avisar que dá para conversar."""

    def __init__(self, key, x, y, head_y=None):
        self.key = key
        self.x, self.y = x, y
        self.head_y = head_y if head_y is not None else y - config.SPRITE_HEIGHT - 26
        self.lines = FALAS[key]
        self.index = 0
        self.talk = 0
        self.line = None
        self.waiting = False            # alguém perto e livre: mostra o "..."

    def near(self, p):
        return p.alive_in_match and math.hypot(p.x - self.x, p.y - self.y) < TALK_REACH

    def say(self, match):
        """ATACAR perto: a próxima frase (mesmo que a anterior ainda esteja no balão)."""
        self.line = self.lines[self.index % len(self.lines)]
        self.index += 1
        self.talk = TALK_FRAMES
        for o in match.speakers:              # um balão por vez ali perto
            if o is not self and o.talk > 0 and abs(o.x - self.x) < BUBBLE_ROOM \
                    and abs(o.head_y - self.head_y) < 40:
                o.talk = 0
        match.assets.play("click", 0.35)

    def update(self, match):
        if self.talk > 0:
            self.talk -= 1

    def draw(self, screen, cam, ui, assets, frame=0):
        sx, sy = cam.to_screen(self.x, self.head_y)
        if self.talk > 0 and self.line:
            draw_bubble(screen, ui, assets, self.line, round(sx), round(sy))
        elif self.waiting:
            dots = "." * (1 + (frame // 12) % 3)
            draw_bubble(screen, ui, assets, dots.ljust(3), round(sx), round(sy))
            color = theme.BRASS if (frame // 15) % 2 else theme.BONE
            ui.text(screen, "ATACAR: FALAR", theme.XS, color, (round(sx), round(sy) - 40))


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


def _near_rect(f, r, reach=USE_REACH):
    if not f.alive_in_match:
        return False
    dx = max(r.left - f.x, 0, f.x - r.right)
    dy = max(r.top - f.y, 0, f.y - r.bottom)
    return math.hypot(dx, dy) < reach


class Moto(Entity):
    """A moto do Aryel: ATACAR perto dá grau (empina na roda de trás, fumaça e VRUUUM)."""

    def __init__(self, x, y):
        super().__init__(x, y)
        self.still = _bake(art.moto)
        self.body = _bake(art.moto, ground=False)
        self.rect = pygame.Rect(x - 60, y - 14, 120, 22)
        self.grau = 0

    @property
    def sort_y(self):
        return self.y + 2

    @property
    def tilt(self):
        """Ângulo da empinada (graus): sobe rápido, balança lá em cima e desce."""
        if self.grau <= 0:
            return 0.0
        t = GRAU_FRAMES - self.grau
        up = min(1.0, t / 14) * min(1.0, self.grau / 16)
        return up * (24 + 4 * math.sin(t * 0.3))

    def ride(self, match):
        if self.grau > 0:
            return False
        self.grau = GRAU_FRAMES
        match.popup(self.x, self.y - 110, "GRAU!", (240, 150, 60))
        match.popup(self.x + 40, self.y - 84, "VRUUUM", theme.BONE)
        match.assets.play("dash", 0.6)
        return True

    def update(self, match):
        if self.grau <= 0:
            return
        self.grau -= 1
        if self.grau % 3 == 0:                                  # fumaça do escapamento
            match.particles.append(Particle(self.x - 54, self.y - 14, random.uniform(-2.2, -1.0),
                                            random.uniform(-0.8, -0.2), random.choice(((170, 170, 176), (130, 130, 138))),
                                            random.randint(20, 34), random.randint(4, 7)))

    def draw(self, surf, camera):
        angle = self.tilt
        if angle < 0.5:
            b = self.still
            surf.blit(b.image, (round(self.x + b.dx - camera.x), round(self.y + b.dy - camera.y)))
            return
        b = self.body
        shade = pygame.Surface((110, 12), pygame.SRCALPHA)       # sombra fica no chão, curta na frente
        pygame.draw.ellipse(shade, (0, 0, 0, 90), shade.get_rect())
        surf.blit(shade, (round(self.x - 80 - camera.x), round(self.y - 2 - camera.y)))
        img, rect = wheelie(b, self.x - camera.x, self.y - camera.y, angle)
        surf.blit(img, rect)


def wheelie(b, x, y, angle):
    """A moto ``b`` (desenhada com o chão em x, y) empinada ``angle`` graus na roda de trás."""
    img = pygame.transform.rotate(b.image, angle)
    px, py = x - 42, y + 2                                  # pivô: onde a roda de trás toca o chão
    w, h = b.image.get_size()
    cx, cy = x + b.dx + w / 2 - px, y + b.dy + h / 2 - py
    a = math.radians(angle)
    rx, ry = cx * math.cos(a) + cy * math.sin(a), -cx * math.sin(a) + cy * math.cos(a)
    return img, img.get_rect(center=(round(px + rx), round(py + ry)))


class Roulette(Entity):
    """A roleta do Aryel: ATACAR gira; parou, é GREEN ou RED."""

    def __init__(self, x, y):
        super().__init__(x, y)
        self.baked = _bake(art.roulette_table)
        self.rect = pygame.Rect(x - 34, y - 20, 68, 60)
        self.angle = 0.0
        self.speed = 0.0
        self.rest = 0                      # resultado na tela: a próxima girada espera um pouco
        self.last = None

    @property
    def sort_y(self):
        return self.y + 32

    @property
    def spinning(self):
        return self.speed > 0

    @property
    def busy(self):
        return self.spinning or self.rest > 0

    def spin(self, match):
        if self.busy:
            return False
        self.speed = random.uniform(0.42, 0.6)
        match.assets.play("click", 0.4)
        return True

    def result(self):
        """GREEN se a fatia embaixo do ponteiro (em cima) é verde."""
        step = math.tau / 12
        k = int(((-math.pi / 2 - self.angle) % math.tau) // step)
        return "GREEN" if k % 2 == 0 else "RED"

    def update(self, match):
        if self.rest > 0:
            self.rest -= 1
        if not self.spinning:
            return
        self.angle = (self.angle + self.speed) % math.tau
        self.speed *= 0.968
        if self.speed < SPIN_MIN:
            self.speed = 0.0
            self.last = self.result()
            self.rest = 60
            green = self.last == "GREEN"
            match.popup(self.x, self.y - 50, "GREEN!" if green else "RED...", (60, 220, 100) if green else (240, 70, 70))
            match.assets.play("confirm" if green else "cancel", 0.5)
            if green:
                match.burst(self.x, self.y - 10, (90, 240, 120), 18, speed=3)

    def draw(self, surf, camera):
        b = self.baked
        x, y = self.x - camera.x, self.y - camera.y
        surf.blit(b.image, (round(x + b.dx), round(y + b.dy)))
        cx, cy = x, y - 8
        step = math.tau / 12
        for k in range(12):
            a0 = self.angle + k * step
            a1 = a0 + step
            c = (50, 170, 80) if k % 2 == 0 else (200, 50, 50)
            pygame.draw.polygon(surf, c, [(cx, cy), (cx + math.cos(a0) * 22, cy + math.sin(a0) * 10),
                                          (cx + math.cos(a1) * 22, cy + math.sin(a1) * 10)])
        pygame.draw.ellipse(surf, (210, 170, 70), (cx - 23, cy - 11, 46, 22), 2)
        pygame.draw.rect(surf, (240, 240, 240), (cx - 2, cy - 2, 4, 4))
        pygame.draw.polygon(surf, (250, 250, 250), [(cx - 4, cy - 16), (cx + 4, cy - 16), (cx, cy - 9)])
        pygame.draw.polygon(surf, (30, 30, 30), [(cx - 4, cy - 16), (cx + 4, cy - 16), (cx, cy - 9)], 1)


class Bakery:
    """O balcão da padaria do João: ATACAR pega a senha e, pouco depois, sai pão quentinho do forno."""

    def __init__(self, rect, chimney):
        self.rect = rect
        self.chimney = chimney
        self.ticket = 0
        self.wait = 0
        self.rest = 0                               # o pão acabou de sair: o aviso some antes da próxima senha

    @property
    def busy(self):
        return self.wait > 0 or self.rest > 0

    def order(self, match):
        if self.busy:
            return False
        self.ticket = self.ticket % 99 + 1
        self.wait = BREAD_FRAMES
        match.popup(self.rect.centerx, self.rect.y - 90, f"SENHA {self.ticket:03d}", theme.BONE)
        match.assets.play("click", 0.4)
        return True

    def update(self, match):
        if self.rest > 0:
            self.rest -= 1
        if self.wait <= 0:
            return
        self.wait -= 1
        if self.wait == 0:
            self.rest = 60
            match.popup(self.rect.centerx, self.rect.y - 90, "PÃO QUENTINHO SAINDO!", (250, 200, 110))
            match.assets.play("confirm", 0.4)
            x, y = self.chimney
            for _ in range(16):                                 # fumacinha do forno
                match.particles.append(Particle(x + random.uniform(-6, 6), y, random.uniform(-0.3, 0.3),
                                                random.uniform(-1.6, -0.7), (236, 232, 226), random.randint(30, 50),
                                                random.randint(4, 7)))


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


class GarageMenu:
    """A garagem aberta: escolher com o que o grupo sai (City, Uno ou moto), os troféus da campanha e
    os corrompidos liberados. Analógico escolhe, ATACAR troca de carro, ESQUIVA fecha."""

    def __init__(self, match, fighter):
        self.match = match
        self.fighter = fighter
        self.index = next(i for i, v in enumerate(VEHICLES) if v[0] == match.run.vehicle)
        self.age = 0
        self._last = 0

    def handle(self, inp):
        self.age += 1
        if self.age <= 1:
            return True                         # o ATACAR que abriu não escolhe
        if any(inp.pressed(a) for a in ("dodge", "special", "cancel")):
            self.match.assets.play("cancel", 0.3)
            return False
        _, y = inp.axis()
        sy = 1 if y > 0.5 else -1 if y < -0.5 else 0
        if sy and sy != self._last:
            self.index = (self.index + sy) % len(VEHICLES)
            self.match.assets.play("click", 0.25)
        self._last = sy
        if inp.pressed("attack") or inp.pressed("confirm"):
            key = VEHICLES[self.index][0]
            if vehicle_ready(key):
                self.match.choose_vehicle(key)
            else:
                self.match.assets.play("cancel", 0.3)
        return True

    def pick(self, item):
        return False

    def snapshot(self):
        return None

    def draw(self, screen, ui, anchor):
        w, h = 360, 236
        x = max(8, min(config.SCREEN_W - w - 8, round(anchor[0]) - w // 2))
        y = max(56, min(config.SCREEN_H - h - 70, round(anchor[1]) - h - 70))
        rect = pygame.Rect(x, y, w, h)
        pygame.draw.rect(screen, theme.SHADOW, rect.move(3, 3))
        pygame.draw.rect(screen, (34, 32, 40), rect)
        pygame.draw.rect(screen, (120, 116, 130), rect, 2)
        ui.text(screen, "GARAGEM", theme.S, theme.BRASS, (rect.centerx, y + 18))
        ui.text(screen, "COM O QUE A TURMA SAI?", theme.XS, theme.BONE, (rect.centerx, y + 38))
        chosen = self.match.run.vehicle
        for i, (key, name, chapter) in enumerate(VEHICLES):
            row = pygame.Rect(x + 14, y + 52 + i * 26, w - 28, 22)
            ready = vehicle_ready(key)
            if i == self.index:
                pygame.draw.rect(screen, (70, 60, 40), row)
                pygame.draw.rect(screen, theme.BRASS, row, 1)
            color = theme.BONE if ready else (110, 108, 120)
            ui.text(screen, name, theme.XS, color, (row.x + 10, row.centery), anchor="midleft")
            state = ("ESCOLHIDO" if key == chosen else "LIBERADO") if ready else f"ZERE O CAPÍTULO {chapter}"
            ui.text(screen, state, theme.XS, theme.MOSS if key == chosen else color,
                    (row.right - 10, row.centery), anchor="midright")
        # troféus: os selos de cada dificuldade e o melhor tempo
        from .ai import CAMPAIGN_ORDER
        from .scenes.campaign import draw_seal
        ty = y + 146
        ui.text(screen, "TROFÉUS", theme.XS, theme.BRASS, (rect.centerx, ty))
        earned = progress.seals()
        n = len(CAMPAIGN_ORDER)
        for i, key in enumerate(CAMPAIGN_ORDER):
            draw_seal(screen, ui, (rect.centerx - (n - 1) * 30 + i * 60, ty + 30), key, key in earned, size=18)
        best = [t for t in (progress.best_time(k) for k in CAMPAIGN_ORDER) if t is not None]
        freed = sum(1 for _, ch, _, _ in CORROMPIDOS if progress.chapter_cleared(ch))
        info = f"CORROMPIDOS LIBERADOS: {freed}/{len(CORROMPIDOS)}"
        if best:
            m = int(min(best))
            info += f" · MELHOR TEMPO {m // 60}:{m % 60:02d}"
        ui.text(screen, info, theme.XS, (190, 186, 200), (rect.centerx, ty + 62))
        ui.text(screen, "ATACAR: ESCOLHER · ESQUIVA: FECHAR", theme.XS, (130, 126, 140), (rect.centerx, rect.bottom - 10))


# ─────────────────────────────────────────────
#  A partida da casa
# ─────────────────────────────────────────────
class HubMatch(CoopMatch):
    """A Casa da turma. ``story``: começo de campanha (a história da fase passa antes da sala inicial);
    no CONTINUAR vai direto."""

    lobby = True
    music = "camp"

    def __init__(self, game, run, story=True, walk=False, arrive=None):
        self.story = story
        self.walk = walk                                    # PASSEAR NA CASA: o City não sai
        self.going_down = False                             # ATACAR na garagem: o grupo desce
        self._screens = {}                                  # vaga -> versão da tela já mandada ao celular
        cfg = MAPS_BY_KEY[HUB_MAP]
        if arrive == "garagem":                             # voltando da garagem: na porta dela
            starts = [(GARAGE_DOOR[0] - 60 + 40 * i, GARAGE_DOOR[1] + 40) for i in range(len(run.session.slots))]
        else:
            starts = _spread(cfg.markers["S"], len(run.session.slots))
        super().__init__(game, run, cfg.key, starts, (0.0, 1.0))
        art.use(self.assets)
        self.arena.floor = self.arena.floor.copy()          # o chão pintado é compartilhado: os tapetes vão na cópia
        self.speakers = []
        self.beds = []
        self.doors = []                                     # (chave, aberta, ponto, dica)
        self.big_flower = False
        self.computers = []                                 # (tipo, mesa, onde a janela fica presa)
        self.notebook_open = False                          # senha do notebook já digitada nesta visita
        self.freeing = 0                                    # LIBERAR TUDO: quadros da tela branca
        self.reload = False
        self._furnish()
        # a saída é o City do João: o grupo entra no carro (todos em volta dele) e vai de carro
        cx, cy = CITY_AT
        self.exit_rect = pygame.Rect(cx - 86, cy - 58, 172, 60)
        self.door_area = self.exit_rect.inflate(110, 96)
        self.passage = Passage(lambda p: not self.walk and not isinstance(self.menus.get(p), ChapterPickMenu)
                               and self.door_area.collidepoint(p.x, p.y))
        if progress.chapter_cleared(4) and self.players:     # recompensa do capítulo 4: a IARA mascote
            from .mansao import IaraMascot
            self.add_effect(IaraMascot(self.players[0], self.assets.sprites.get("iara_nucleo")))
        # a luz das janelas pela hora do dia, a fumaça do forno e os mascotes (gato, cachorro, papagaio)
        self.add_effect(luz_casa.CasaLight([(13 * T, OY + 4, 120, 52), (32 * T, OY + 4, 120, 52)],
                                           self.bakery.chimney))
        mascotes.furnish(self, T, OY, QY, self._put, art)
        mascotes.join_shop(self)                            # os pets da loja de CACOS

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
        for i, (x, y) in enumerate(((12 * T, OY + 3 * T), (36 * T, OY + 3 * T), (16 * T, OY + 13 * T + 20),
                                    (32 * T, OY + 13 * T + 20))):
            put(art.plant, x, y, art.PLANTS[i], foot=((-10, -10, 20, 14),))
        # a vitrine: cada herói fala quando alguém chega perto
        for key, x, y in VITRINE:
            self._hero(key, x, OY + y)
        # canto do Cauanzera (alto à esquerda): retrato, computador, livro, armadura de Uno e estante
        put(art.frame_portrait, 2 * T, OY + T - 18, "cauanzera", flat=True)
        self.speakers.append(Speaker("cauanzera", 2 * T + 24, OY + 2 * T + 10, head_y=OY + T - 24))
        put(art.pc_desk, 4 * T, OY + 2 * T, foot=((0, 20, 140, 18), (52, 66, 24, 16)))
        self.computers.append(("pc", pygame.Rect(4 * T, OY + 2 * T + 20, 140, 18), (4 * T + 70, OY + 2 * T - 40)))
        self.book = put(art.lectern_book, 2 * T + 10, OY + 5 * T + 20, foot=((-14, 30, 28, 12),))
        self.uno_stand = put(art.uno_stand if self.run.armor else art.uno_armor, *UNO_STAND,
                             foot=((-30, -10, 60, 14),))
        # a armadura de Uno ainda no suporte, e só vale no capítulo 1 (depois é enfeite)
        self.armor_free = not self.run.armor and (self.run.chapter == 1 or self.walk)
        put(art.shelf, 9 * T + 10, OY + T - 20, 70, foot=((0, 50, 70, 20),))
        # canto do Aryel (alto à direita): retrato, pôster, moto, capacetes e a roleta
        put(art.frame_portrait, 44 * T, OY + T - 18, "aryel", flat=True)
        self.speakers.append(Speaker("aryel", 44 * T + 24, OY + 2 * T + 10, head_y=OY + T - 24))
        put(art.poster, 39 * T, OY + T - 14, 60, 34, (24, 84, 48), "GREEN!", (236, 220, 170), flat=True)
        self.moto = Moto(41 * T, OY + 4 * T + 10)
        self.props.append(self.moto)
        self.arena.walls.append(Wall(41 * T - 56, OY + 4 * T, 112, 14, visible=False))
        put(art.helmet_rack, 45 * T + 20, OY + 3 * T + 10, foot=((-14, 62, 28, 12),))
        self.roulette = Roulette(38 * T, OY + 5 * T + 20)
        self.props.append(self.roulette)
        self.arena.walls.append(Wall(38 * T - 30, OY + 5 * T + 44, 60, 16, visible=False))
        # canto do Albeguinio (embaixo à esquerda): retrato no cavalete, arquivo, mesa e o roteador
        put(art.easel_portrait, 3 * T, OY + 10 * T, "albeguinio", foot=((-20, 70, 40, 12),))
        self.speakers.append(Speaker("albeguinio", 3 * T, OY + 12 * T, head_y=OY + 10 * T - 34))
        put(art.file_cabinet, T + 6, OY + 12 * T, foot=((0, 56, 40, 18),))
        put(art.office_desk, 4 * T, OY + 11 * T, foot=((0, 20, 140, 18), (58, 52, 24, 18)))
        self.computers.append(("notebook", pygame.Rect(4 * T, OY + 11 * T + 20, 140, 18), (4 * T + 70, OY + 11 * T - 30)))
        put(art.router, 9 * T, OY + 10 * T + 10)
        # canto do Borba Jr (embaixo à direita): retrato, a padaria do João, o forno e o exo
        put(art.easel_portrait, 46 * T, OY + 8 * T, "borba", foot=((-20, 70, 40, 12),))
        self.speakers.append(Speaker("borba", 46 * T, OY + 10 * T, head_y=OY + 8 * T - 34))
        put(art.bakery, 38 * T, OY + 11 * T, foot=((0, 20, 220, 44),))
        put(art.oven, 43 * T + 30, OY + 10 * T + 20, foot=((0, 38, 80, 32),))
        self.bakery = Bakery(pygame.Rect(38 * T, OY + 11 * T, 220, 64), (43 * T + 70, OY + 10 * T - 12))
        put(art.exo_stand, 35 * T + 30, OY + 13 * T + 10, foot=((-24, -10, 48, 14),))
        # os corrompidos liberados ficam lá embaixo, no salão da garagem (garagem.py)
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
        put(art.scarecrow, T + 30, QY + 3 * T + 10, foot=((-4, -8, 8, 10),))
        put(art.hose, 4 * T + 10, QY + 7 * T + 16)
        self._door("garagem", art.garage_front, 39 * T, QY + 5 * T - 20, w=100, inside=art.inside_garagem)
        self.parked = put(art.city_car, *CITY_AT, foot=((-86, -24, 172, 26),))
        self.parked_moto = None
        self._park(self.run.vehicle)
        self._door("porao", art.cellar_door, 14 * T, QY + 5 * T)
        # a LOJA DE CACOS: o balcão no quintal, entre a horta e o porão
        self.shop = ShopStand(*SHOP_AT)
        self.shop.bake_label(self.game.ui)
        self.props.append(self.shop)
        self.arena.walls.append(self.shop.wall)
        self.lockers = Lockers(*LOCKERS_AT)
        self.lockers.bake_labels(self.game.ui)
        self.props.append(self.lockers)
        self.arena.walls.append(self.lockers.wall)
        for i, key in enumerate(CRAQUES):
            self._hero(key, 34 * T + 20 + i * 80, QY + 2 * T + 20, base="pedra")
        for i, (x, y) in enumerate(((26 * T + 20, QY + T + 10), (33 * T, QY + 7 * T), (45 * T, QY + 2 * T))):
            put(art.plant, x, y, art.PLANTS[(i + 1) % 4], foot=((-10, -10, 20, 14),))

    def _hero(self, key, x, y, base="madeira"):
        self._put(art.mannequin, x, y, key, base=base, foot=((-20, -10, 40, 14),))
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
    def hud_title(self):
        return "PASSEIO" if self.walk else None

    @property
    def objective_text(self):
        if self.walk:
            return "CASA DA TURMA · PAUSE PARA VOLTAR AO MENU"
        return f"CASA DA TURMA · TODOS NO {self.car_name} DO QUINTAL PARA A AVENTURA"

    @property
    def car_name(self):
        return "UNO" if self.run.vehicle == "uno" else "CITY"

    def objective(self):
        if self.walk:
            return None
        return self.exit_rect.centerx, self.exit_rect.y

    def _park(self, key):
        """O carro escolhido na garagem fica estacionado no quintal (a moto encosta do lado do City)."""
        self.parked.baked = _bake(art.uno_car if key == "uno" else art.city_car)
        if key == "moto" and self.parked_moto is None:
            self.parked_moto = Decor(CITY_AT[0] + 150, CITY_AT[1] + 6, _bake(art.moto))
            self.props.append(self.parked_moto)
        elif key != "moto" and self.parked_moto is not None:
            self.props.remove(self.parked_moto)
            self.parked_moto = None

    def choose_vehicle(self, key):
        if self.run.vehicle == key:
            return
        self.run.vehicle = key
        self._park(key)
        name = next(n for k, n, _ in VEHICLES if k == key)
        self.popup(CITY_AT[0], CITY_AT[1] - 90, f"{name} NO QUINTAL", theme.BRASS)
        self.assets.play("confirm", 0.45)

    # ── PARA ONDE? ───────────────────────────
    @property
    def can_pick(self):
        """Escolher o capítulo no carro: só no começo da campanha (não no CONTINUAR nem passeando)."""
        return self.story and not self.walk and not self.run.rush

    def car_near(self, f):
        return self.can_pick and f.alive_in_match and _near_rect(f, self.exit_rect)

    def pick_chapter(self, chapter):
        if self.run.pick_chapter(chapter):
            self.popup(self.exit_rect.centerx, self.exit_rect.y - 90, f"PARA O CAPÍTULO {chapter}!", theme.BRASS)

    def garage_near(self, f):
        if not f.alive_in_match:
            return False
        _, _, (x, y), _ = next(d for d in self.doors if d[0] == "garagem")
        return math.hypot(f.x - x, f.y - y) < DOOR_REACH

    def armor_near(self, f):
        x, y = UNO_STAND
        return self.armor_free and _near_rect(f, pygame.Rect(x - 30, y - 100, 60, 100))

    def wear_armor(self, f):
        self.armor_free = False
        f.uno_hits = UNO_HITS
        self.run.armor[f.slot] = UNO_HITS
        self.uno_stand.baked = _bake(art.uno_stand)
        self.burst(f.x, f.y - 20, (240, 240, 236), 18, speed=3)
        self.popup(f.x, f.y - 60, "ARMADURA DE UNO!", theme.BRASS)
        self.assets.play("confirm", 0.5)

    def speaker_near(self, f):
        """Quem da vitrine ``f`` pode chamar para conversar: o mais perto, e só se não tem outra
        coisa para usar ali (mesa, moto, roleta...), que ganha do ATACAR."""
        if not f.alive_in_match or self._usable_near(f):
            return None
        near = [s for s in self.speakers if s.near(f)]
        return min(near, key=lambda s: math.hypot(f.x - s.x, f.y - s.y)) if near else None

    def _usable_near(self, f):
        return (self.book_near(f) or self.computer_near(f) is not None or self.armor_near(f) or self.garage_near(f)
                or self.shop.near(f) or self.lockers.near(f) is not None
                or any(_near_rect(f, t.rect) for t in (self.moto, self.roulette, self.bakery))
                or any(b.can_water(f) for b in self.beds))

    def computer_near(self, f):
        """A mesa de computador ao alcance de ``f`` que ninguém está usando (ou None)."""
        for kind, rect, anchor in self.computers:
            if _near_rect(f, rect) and not any(getattr(m, "kind", None) == kind for m in self.menus.values()):
                return kind, rect, anchor
        return None

    def free_everything(self, fighter):
        """Chamado pelo computador quando o LIBERAR TUDO termina: tela branca e a casa recarrega."""
        if self.freeing:
            return
        for f in [g for g in self.menus if g is not fighter]:
            del self.menus[f]
        self.freeing = 1
        self.assets.play("confirm", 0.7)

    def redress(self):
        """Depois de vestir/tirar uma skin na loja: todo mundo na casa já aparece com a roupa escolhida."""
        for p in self.players:
            if p.exo_base is not None:
                continue
            if not skins.dress(p, self.assets) and p.skin is not None:
                p.sprites = self.assets.sprites[p.stats.key]
                p.skin = None

    def refresh_pets(self):
        """Depois de trocar de pet no armário."""
        mascotes.refresh_shop(self)

    def book_near(self, f):
        return f.alive_in_match and math.hypot(f.x - self.book.x, f.y - (self.book.y + 40)) < BOOK_REACH

    # ── ciclo ────────────────────────────────
    def phone_shop(self):
        """Além da loja: quem está num computador recebe a cópia da tela no celular (PNG), quando
        ela muda ou a cada SCREEN_EVERY quadros (o cristal do fundo gira)."""
        super().phone_shop()
        for f in self.players:
            if not f.slot:
                continue
            menu = self.menus.get(f)
            if not isinstance(menu, computador.Computer):
                if self._screens.pop(f.slot, None) is not None:
                    hub.set_screen(f.slot, None)
                continue
            if self._screens.get(f.slot) != menu.version or self.frame % SCREEN_EVERY == 0:
                self._screens[f.slot] = menu.version
                hub.set_screen(f.slot, menu.png(self.game.ui))

    def update_stage(self):
        if self.frame == 1:
            if self.walk:
                self._set_banner("CASA DA TURMA", "PASSEIO: ANDEM E MEXAM EM TUDO", theme.BRASS)
            elif self.story:
                self._set_banner("CASA DA TURMA", "A AVENTURA COMEÇA NO QUINTAL", theme.BRASS)
            else:
                self._set_banner("CASA DA TURMA", f"CONTINUANDO DA FASE {self.run.phase_index + 1}", theme.BRASS)
        if self.banner and self.banner[3] > 130:
            self.banner = None
        waiting = {self.speaker_near(p) for p in self.alive_players if p not in self.menus}
        for s in self.speakers:
            s.update(self)
            s.waiting = s in waiting
        self.bakery.update(self)
        self.shop.update(self)
        self.lockers.update(self)
        if self.freeing:
            self.freeing += 1
            if self.freeing >= FREE_FRAMES and not self.finished:
                self.reload = True
                self._finish(won=True)
            return
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
        if self.freeing:
            return True
        if mascotes.interact(self, f):
            return True
        if self.book_near(f):
            self.menus[f] = BookMenu(self, f, next_verse())
            self.assets.play("click", 0.45)
            return True
        if self.armor_near(f):
            self.wear_armor(f)
            return True
        if self.shop.near(f):
            self.menus[f] = ShopMenu(self, f)
            self.assets.play("loja", 0.45)
            return True
        slot = self.lockers.near(f)
        if slot is not None:
            if slot != f.slot:
                self.popup(f.x, f.y - 70, f"ESSE É O ARMÁRIO DO P{slot}", theme.SLOT_COLORS[slot])
                self.assets.play("cancel", 0.3)
                return True
            self.menus[f] = WardrobeMenu(self, f)
            self.assets.play("select", 0.45)
            return True
        if self.car_near(f):
            self.menus[f] = ChapterPickMenu(self, f, self.pick_chapter, self.run.chapter)
            self.assets.play("select", 0.45)
            return True
        if self.garage_near(f):
            self.going_down = True                    # o grupo inteiro desce para a garagem
            self.assets.play("select", 0.45)
            self._finish(won=True)
            return True
        spot = self.computer_near(f)
        if spot is not None:
            kind, _, anchor = spot
            self.menus[f] = computador.make(self, f, kind, anchor)
            self.assets.play("select", 0.45)
            return True
        if _near_rect(f, self.moto.rect) and self.moto.ride(self):
            return True
        if _near_rect(f, self.roulette.rect) and self.roulette.spin(self):
            return True
        if _near_rect(f, self.bakery.rect) and self.bakery.order(self):
            return True
        bed = next((b for b in self.beds if b.can_water(f)), None)
        if bed is not None:
            bed.water(self)
            return True
        speaker = self.speaker_near(f)
        if speaker is not None:
            speaker.say(self)
            return True
        return self.pick_ground(f)

    def _finish(self, won):
        """Saindo da casa: nada passa para a fase (nem o tempo; o relógio da campanha começa na sala inicial)."""
        self.won = won
        self.result = Result("CASA DA TURMA", theme.MOSS, self.players)
        self.finished = True

    def next_scene(self):
        from .scenes.campaign import hub_scene, start_phase
        from .scenes.viagem import CarTripScene
        if self.reload:                          # LIBERAR TUDO: a casa volta com tudo aberto
            return hub_scene(self.game, self.run, story=self.story, walk=self.walk)
        if self.going_down:
            from .scenes.campaign import garage_scene
            from .scenes.garagem import GarageTripScene
            return GarageTripScene(self.game, lambda: garage_scene(self.game, self.run, self.story, walk=self.walk))
        return CarTripScene(self.game, [p.sprites for p in self.players], self.run.chapter,
                            lambda: start_phase(self.game, self.run, story=self.story), vehicle=self.run.vehicle)

    def restart_scene(self):
        from .scenes.campaign import hub_scene
        return hub_scene(self.game, self.run, story=self.story, walk=self.walk)

    # ── desenho ──────────────────────────────
    def draw_screen_layer(self, screen, ui):
        cam = self.camera
        for s in self.speakers:
            s.draw(screen, cam, ui, self.assets, self.frame)
        free = [p for p in self.alive_players if p not in self.menus]
        mascotes.draw_prompts(self, screen, ui, free, self.frame)
        if any(self.book_near(p) for p in free):
            sx, sy = cam.to_screen(self.book.x, self.book.y - 40)
            color = theme.BRASS if (self.frame // 15) % 2 else theme.BONE
            ui.text(screen, "ATACAR: LER O LIVRO", theme.XS, color, (round(sx), round(sy)))
        blink = theme.BRASS if (self.frame // 15) % 2 else theme.BONE
        for kind, rect, _ in self.computers:
            if any(self.computer_near(p) and self.computer_near(p)[0] == kind for p in free):
                sx, sy = cam.to_screen(rect.centerx, rect.y - 70)
                text = "ATACAR: LIGAR O COMPUTADOR" if kind == "pc" else "ATACAR: ABRIR O NOTEBOOK"
                ui.text(screen, text, theme.XS, blink, (round(sx), round(sy)))
        for thing, text, busy in ((self.moto, "ATACAR: DAR GRAU", self.moto.grau > 0),
                                  (self.roulette, "ATACAR: GIRAR A ROLETA", self.roulette.busy),
                                  (self.bakery, "ATACAR: PEGAR A SENHA", self.bakery.busy)):
            if not busy and any(_near_rect(p, thing.rect) for p in free):
                sx, sy = cam.to_screen(thing.rect.centerx, thing.rect.y - (100 if thing is self.bakery else 50))
                ui.text(screen, text, theme.XS, blink, (round(sx), round(sy)))
        if any(self.shop.near(p) for p in free):
            sx, sy = cam.to_screen(self.shop.x, self.shop.y - 160)
            ui.text(screen, "ATACAR: LOJA DE CACOS", theme.XS, blink, (round(sx), round(sy)))
        if any(self.lockers.near(p) is not None for p in free):
            sx, sy = cam.to_screen(self.lockers.x, self.lockers.y - 136)
            ui.text(screen, "ATACAR NO SEU ARMÁRIO: VESTIR SKIN", theme.XS, blink, (round(sx), round(sy)))
        if any(self.armor_near(p) for p in free):
            sx, sy = cam.to_screen(UNO_STAND[0], UNO_STAND[1] - 120)
            ui.text(screen, "ATACAR: VESTIR A ARMADURA", theme.XS, blink, (round(sx), round(sy)))
        if any(self.garage_near(p) for p in free):
            _, _, (gx, gy), _ = next(d for d in self.doors if d[0] == "garagem")
            sx, sy = cam.to_screen(gx, gy - 96)
            ui.text(screen, "ATACAR: DESCER PARA A GARAGEM", theme.XS, blink, (round(sx), round(sy)))
        for b in self.beds:
            if any(b.can_water(p) for p in free) and b.watered <= 0:
                sx, sy = cam.to_screen(b.rect.centerx, b.rect.y - 14)
                color = theme.BRASS if (self.frame // 15) % 2 else theme.BONE
                ui.text(screen, "ATACAR: REGAR", theme.XS, color, (round(sx), round(sy)))
        for key, opened, (x, y), hint in self.doors:
            if opened:
                continue
            if any(math.hypot(p.x - x, p.y - y) < DOOR_REACH for p in free):
                sx, sy = cam.to_screen(x, y + (58 if key == "porao" else 40))  # o porão tem nome pintado embaixo
                ui.text(screen, hint, theme.XS, theme.BONE, (round(sx), round(sy)))
        self.draw_ground(screen, cam, ui)
        self.draw_car_labels(screen, ui, free, blink)
        for f, menu in self.menus.items():
            if isinstance(menu, computador.Computer):
                crt.panel(screen, (menu.kind, f.slot), lambda s, menu=menu: menu.draw(s, ui, cam))
                continue
            at = cam.to_screen(f.x, f.y)
            crt.panel(screen, ("livro", f.slot), lambda s, menu=menu, at=at: menu.draw(s, ui, at))

    def draw_car_labels(self, screen, ui, free, blink):
        """Em cima do carro do quintal: a chamada da saída e o PARA ONDE?."""
        cam = self.camera
        top = self.door_area.y
        sx, sy = cam.to_screen(self.exit_rect.centerx, top)
        if self.walk:
            ui.text(screen, "SÓ PASSEANDO", theme.XS, theme.MUTED, (round(sx), round(sy) - 14))
            return
        ui.text(screen, f"TODOS NO {self.car_name} PARA A AVENTURA", theme.XS, theme.BRASS, (round(sx), round(sy) - 14))
        if self.can_pick:
            near = any(self.car_near(p) for p in free)
            text = "ATACAR: PARA ONDE?" if near else f"RUMO AO CAPÍTULO {self.run.chapter}"
            ui.text(screen, text, theme.XS, blink if near else theme.BONE, (round(sx), round(sy) - 30))
        self.draw_passage(screen, ui, self.passage, self.door_area, (self.exit_rect.centerx, top - 4))

    def draw(self, screen, ui):
        super().draw(screen, ui)
        if self.freeing:
            draw_freeing(screen, ui, self.freeing)

    # ── minimapa ─────────────────────────────
    def minimap_rect(self):
        w, h = self.arena.size
        k = MINI_W / w
        return pygame.Rect(config.SCREEN_W - 12 - MINI_W, MINI_TOP, MINI_W, round((h - OY - 2 * T) * k) + 4)

    def draw_hud(self, screen, ui):
        super().draw_hud(screen, ui)
        draw_minimap(screen, ui, self, self.minimap_rect())

    def hud_regions(self):
        return super().hud_regions() + [self.minimap_rect().inflate(4, 4)]


MINI_W = 200                 # o mapinha da Casa (largura na tela)
MINI_TOP = 44                # embaixo dos CONTINUES, como o da fase
# cantos da casa no mapinha: (nome, coluna, linha, largura, altura) em quadrados, linha 0 = topo da casa
MINI_ZONES = (("CAU", 1, 0, 11, 8), ("ARYEL", 36, 0, 11, 8), ("SALA", 12, 0, 24, 14),
              ("ALBE", 1, 8, 11, 6), ("BORBA", 36, 8, 11, 6))


def draw_minimap(screen, ui, match, rect):
    """O mapinha da Casa: a casa e o quintal, os cantos de cada um, as portas (trancadas em cinza),
    o que dá para usar (ícones pequenos) e um ponto por jogador, na cor dele."""
    w, _ = match.arena.size
    k = (rect.w - 4) / w
    bg = pygame.Surface(rect.size, pygame.SRCALPHA)
    bg.fill((8, 8, 14, 175))
    screen.blit(bg, rect.topleft)
    pygame.draw.rect(screen, (90, 90, 110), rect, 1)

    def at(x, y):
        return round(rect.x + 2 + x * k), round(rect.y + 2 + (y - OY) * k)

    def cells(c, r, cw, ch):
        x, y = at(c * T, OY + r * T)
        return pygame.Rect(x, y, max(1, round(cw * T * k)), max(1, round(ch * T * k)))

    house = cells(0, 0, 48, 15)
    yard = pygame.Rect(house.x, house.bottom, house.w, round(9 * T * k))
    screen.fill((74, 58, 44), house)
    screen.fill((44, 70, 40), yard)
    for name, c, r, cw, ch in MINI_ZONES:
        z = cells(c, r + 1, cw, ch)
        if name != "SALA":
            screen.fill((92, 72, 54), z)
        ui.text(screen, name, theme.XS, (200, 186, 160), (z.centerx, z.centery), shadow=False)
    pygame.draw.rect(screen, (140, 120, 96), house, 1)
    pygame.draw.rect(screen, (90, 130, 80), yard, 1)
    for key, opened, (x, y), _ in match.doors:
        dx, dy = at(x, y)
        color = (230, 190, 90) if opened else (90, 90, 100)
        screen.fill(color, (dx - 3, dy - 2, 6, 4))
    icons = [((80, 160, 240), match.computers[0][1].center), ((240, 240, 240), UNO_STAND),
             ((200, 60, 60), match.roulette.rect.center), ((230, 200, 120), match.bakery.rect.center),
             ((110, 110, 124), match.exit_rect.center)]
    icons += [((90, 200, 90), b.rect.center) for b in match.beds]
    for color, (x, y) in icons:
        pygame.draw.circle(screen, color, at(x, y), 2)
    for p in match.players:
        if not p.alive_in_match:
            continue
        x, y = at(p.x, p.y)
        pygame.draw.circle(screen, (250, 250, 250), (x, y), 5)
        pygame.draw.circle(screen, p.color, (x, y), 4)


def draw_freeing(screen, ui, frame):
    """A tela branca do LIBERAR TUDO: clareia, LIBERANDO... com os pontinhos e a barra enchendo."""
    W, H = config.SCREEN_W, config.SCREEN_H
    k = min(1.0, frame / 24)
    white = pygame.Surface((W, H))
    white.fill((250, 250, 248))
    white.set_alpha(round(255 * k))
    screen.blit(white, (0, 0))
    if k < 0.8:
        return
    dots = "." * (1 + (frame // 10) % 3)
    ui.text(screen, "LIBERANDO" + dots, theme.XL, (40, 40, 52), (W // 2, H // 2 - 20), shadow=False)
    bar = pygame.Rect(0, 0, 320, 10)
    bar.center = (W // 2, H // 2 + 30)
    pygame.draw.rect(screen, (40, 40, 52), bar, 1)
    fill = min(1.0, frame / (FREE_FRAMES - 10))
    screen.fill((84, 162, 222), (bar.x + 2, bar.y + 2, round((bar.w - 4) * fill), bar.h - 4))
    ui.text(screen, "CAPÍTULOS, CORROMPIDOS E PORTAS DA CASA", theme.XS, (90, 90, 100), (W // 2, H // 2 + 56),
            shadow=False)
