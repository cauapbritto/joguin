"""A saída da Casa da turma: o grupo entra no City do João, pega a estrada até o capítulo e o carro
quebra no caminho (daí em diante é a pé).

Uns 7 segundos: o City entra na tela, roda pela estrada enquanto o cenário vai virando o do capítulo
(floresta, Lag Lobby, Clepalovers ou Mansão), começa a falhar, solta fumaça, faz PUFF e para. ESQUIVA,
ESC ou PAUSE pulam a cena."""
import math
import random

import pygame

from .. import casa_art, config, pecas, theme
from ..net.remote import hub
from .base import Scene

DRIVE_IN = 50          # o carro entrando da esquerda
COUGH = 270            # começa a falhar
PUFF = 340             # PUFF: parou
END = 450              # fim da cena
CAR_SCALE = 2

# por capítulo: céu, chão, cor das coisas da beira da estrada e a frase do carro quebrando
CHAPTERS = {
    1: ((70, 110, 150), (52, 84, 46), "pinheiro", "O CITY QUEBROU. DAQUI É A PÉ."),
    2: ((38, 40, 60), (62, 62, 68), "predio", "O CITY QUEBROU NA PORTA DA LAG LOBBY."),
    3: ((150, 170, 200), (200, 196, 190), "clinica", "O CITY QUEBROU. A CLÍNICA É LOGO ALI."),
    4: ((60, 40, 70), (110, 104, 70), "cerca", "O CITY QUEBROU NA FRENTE DA MANSÃO."),
}
SUBURB_SKY, SUBURB_GROUND = (110, 160, 210), (76, 120, 64)


def _mix(a, b, t):
    t = max(0.0, min(1.0, t))
    return tuple(round(x + (y - x) * t) for x, y in zip(a, b))


# vidro de cada carro na imagem de 200 x 80 (antes de ampliar) e onde fica a coluna do meio
GLASS = {"city": ((62, 22, 82, 16), 99), "uno": ((46, 18, 80, 20), 85)}
BREAK_LINE = {"uno": "O UNO PERDEU A PORTA. DAQUI É A PÉ.",
              "moto": "O CITY QUEBROU. A MOTO ESPEROU."}


# carros prontos (assets/pecas, vidro translúcido): meio de cada roda e o pé delas, já ampliados
HD_WHEELS = {"city": ((44, 144), 56, 71), "uno": ((28, 98), 56, 70)}


def _hd_car(vehicle):
    img = pecas.image(f"carro_{vehicle}_vidro")
    if img is None:
        return None
    return pygame.transform.scale(img, (img.get_width() * CAR_SCALE, img.get_height() * CAR_SCALE))


def _glass_rect(car):
    """Onde está o vidro translúcido do carro pronto (é por ali que aparecem as cabeças)."""
    w, h = car.get_size()
    pts = [(x, y) for y in range(0, h, 2) for x in range(0, w, 2) if 0 < car.get_at((x, y)).a < 255]
    if not pts:
        return pygame.Rect(w // 4, h // 6, w // 2, h // 4)
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    return pygame.Rect(min(xs), min(ys), max(xs) - min(xs) + 2, max(ys) - min(ys) + 2)


def _car_image(vehicle="city"):
    hd = _hd_car(vehicle)
    if hd is not None:
        return hd
    surf = pygame.Surface((200, 80), pygame.SRCALPHA)
    (casa_art.uno_car if vehicle == "uno" else casa_art.city_car)(surf, 100, 74)
    return pygame.transform.scale(surf, (200 * CAR_SCALE, 80 * CAR_SCALE))


def _moto_image():
    img = pecas.image("moto")
    if img is not None:
        return pygame.transform.scale(img, (img.get_width() * CAR_SCALE, img.get_height() * CAR_SCALE))
    surf = pygame.Surface((160, 100), pygame.SRCALPHA)
    casa_art.moto(surf, 80, 92)
    return pygame.transform.scale(surf, (160 * CAR_SCALE, 100 * CAR_SCALE))


def _head(sprites, tick):
    """A cabeça do herói para a janela do carro (o terço de cima do quadro de frente)."""
    img = sprites.frame("frente", tick // 10)
    h = max(8, img.get_height() * 2 // 5)
    return img.subsurface((0, 0, img.get_width(), h)).copy()


class CarTripScene(Scene):
    """A cena do City indo para a aventura. ``then`` monta a cena seguinte (a fase)."""

    phase = "story"
    music = None

    def __init__(self, game, sprites, chapter, then, vehicle="city"):
        super().__init__(game)
        self.vehicle = vehicle if vehicle in ("city", "uno", "moto") else "city"
        self.heads = [_head(s, 0) for s in sprites[:4]]
        self.rider = None
        if self.vehicle == "moto" and self.heads:
            self.rider = self.heads.pop(0)            # o P1 vai de moto na frente, empinando
        self.chapter = chapter if chapter in CHAPTERS else 1
        self.then = then
        self.done = False
        self.car_kind = "uno" if self.vehicle == "uno" else "city"
        self.car = _car_image(self.car_kind)
        self.hd = pecas.image(f"carro_{self.car_kind}_vidro") is not None
        self.glass = _glass_rect(self.car) if self.hd else None
        self.seat = (80, 56) if pecas.image("moto") is not None else (132, 104)   # onde senta o P1 na moto
        self.moto = _moto_image() if self.vehicle == "moto" else None
        self.door = None                              # a porta do Uno caindo: [x, y, vy, giro]
        self.smoke = []                       # [x, y, raio, vida]
        self.scroll = 0.0
        rng = random.Random(self.chapter)
        self.roadside = [(rng.randint(0, 1400), rng.randint(0, 2)) for _ in range(14)]
        self.clouds = [(rng.randint(0, 1600), rng.randint(30, 170), rng.randint(3, 6)) for _ in range(8)]
        self.grain = [(rng.randrange(1400), rng.randrange(70)) for _ in range(160)]
        self.suburb = ([pecas.image(f"estrada_casa_{v}") for v in range(4)],
                       [pecas.image(f"estrada_arvore_{v}") for v in range(3)], pecas.image("estrada_poste"))

    def enter(self):
        super().enter()
        hub.set_phase("story", mode="campaign", active=self.active_slots(), banner="A CAMINHO DA AVENTURA")

    # ── tempo ────────────────────────────────
    @property
    def speed(self):
        t = self.ticks
        if t < COUGH:
            return 9.0
        if t < PUFF:
            return 9.0 * (1 - (t - COUGH) / (PUFF - COUGH)) * (0.6 if (t // 6) % 2 else 1.0)
        return 0.0

    @property
    def car_x(self):
        W = config.SCREEN_W
        width = self.car.get_width() + (10 + self.moto.get_width() if self.moto is not None else 0)
        start, mid = -width, W // 2 - width // 2
        if self.ticks < DRIVE_IN:
            k = self.ticks / DRIVE_IN
            return start + (mid - start) * (1 - (1 - k) ** 2)
        return mid

    def _finish(self):
        if not self.done:
            self.done = True
            self.game.change(self.then())

    def handle(self, event):
        if event.type == pygame.KEYDOWN and event.key in (pygame.K_ESCAPE, pygame.K_TAB):
            self._finish()

    def update(self):
        super().update()
        slots = self.active_slots()
        if self.ticks > 15 and any(self.game.inputs[s].pressed(a) for s in slots for a in ("dodge", "pause")):
            self._finish()
            return
        self.scroll += self.speed
        cx = self.car_x
        ground = self.ground_y
        if COUGH <= self.ticks < END and (self.ticks % (3 if self.ticks >= PUFF else 7) == 0):
            # fumaça saindo do capô (frente do carro, à direita)
            self.smoke.append([cx + self.car.get_width() - 40 + random.uniform(-10, 10),
                               ground - 60 * CAR_SCALE // 2 + random.uniform(-6, 6), random.uniform(6, 12), 60])
        if self.ticks == PUFF and self.vehicle == "uno":
            self.door = [cx + 150, ground - 70, -5.0, 0.0]
        if self.door is not None:
            self.door[2] += 0.5
            self.door[1] = min(ground + 30, self.door[1] + self.door[2])
            if self.door[1] >= ground + 30:
                self.door[2] = -self.door[2] * 0.4 if abs(self.door[2]) > 1 else 0
            self.door[3] = min(90.0, self.door[3] + 4)
        if self.ticks == PUFF:
            self.sfx("explosion" if "explosion" in self.assets.sounds else "hit", 0.5)
            for _ in range(18):
                self.smoke.append([cx + self.car.get_width() - 60 + random.uniform(-40, 40),
                                   ground - 50 + random.uniform(-30, 10), random.uniform(10, 22), 80])
        for puff in self.smoke:
            puff[0] -= self.speed * 0.6 + 0.3
            puff[1] -= 0.8
            puff[2] += 0.25
            puff[3] -= 1
        self.smoke = [p for p in self.smoke if p[3] > 0]
        if self.ticks >= END:
            self._finish()

    # ── desenho ──────────────────────────────
    @property
    def ground_y(self):
        return config.SCREEN_H - 150

    @property
    def travel(self):
        """0 = ainda no bairro da casa, 1 = já no cenário do capítulo."""
        return min(1.0, max(0.0, (self.ticks - 40) / 160))

    def draw(self, screen):
        W, H = config.SCREEN_W, config.SCREEN_H
        sky, ground, kind, line = CHAPTERS[self.chapter]
        k = self.travel
        gy = self.ground_y
        top = _mix(SUBURB_SKY, sky, k)
        low = _mix(top, (236, 228, 214) if self.chapter != 2 else (70, 60, 90), 0.55)
        for y in range(0, gy, 6):                          # céu em degradê
            screen.fill(_mix(top, low, y / max(1, gy)), (0, y, W, 6))
        cloud = _mix((248, 250, 252), sky, 0.35 * k)
        for x0, y0, n in self.clouds:                      # nuvens bem devagar
            x = (x0 - self.scroll * 0.08) % 1600 - 200
            for j in range(n):
                pygame.draw.circle(screen, cloud, (round(x + j * 18 - n * 9), y0 + (j % 2) * 6), 14 + (j * 7) % 12)
        # morros lá no fundo, em duas camadas (andam devagar)
        for layer, (col, amp, base, speed) in enumerate((((126, 170, 170), 40, gy - 110, 0.12),
                                                          ((96, 150, 120), 30, gy - 70, 0.25))):
            col = _mix(col, _mix(sky, (20, 20, 30), 0.4 - layer * 0.15), k)
            off = self.scroll * speed
            pts = [(0, H)]
            for x in range(0, W + 20, 20):
                u = x + off
                pts.append((x, base - amp * math.sin(u / 90 + layer * 2) - amp * 0.5 * math.sin(u / 37)))
            pts.append((W, H))
            pygame.draw.polygon(screen, col, pts)
        screen.fill(_mix(SUBURB_GROUND, ground, k), (0, gy - 40, W, H - gy + 40))
        # beira da estrada: casinhas do bairro no começo, depois as coisas do capítulo
        houses, trees, post = self.suburb
        for x0, v in self.roadside:
            x = (x0 - self.scroll * 0.7) % 1400 - 200
            if (x0 * 7) % 100 / 100 < k:
                self._roadside(screen, kind, x, gy - 40, v)
            elif houses[0] is not None:
                img = trees[v % 3] if x0 % 3 == 0 else houses[(x0 + v) % 4]
                screen.blit(img, img.get_rect(midbottom=(round(x) + 45, gy - 34)))
            else:
                self._house(screen, x, gy - 40, v)
        # calçada com meio-fio e postes
        screen.fill(_mix((176, 172, 164), (120, 118, 124), k * 0.5), (0, gy - 8, W, 8))
        for i in range(-1, W // 24 + 2):
            screen.fill((150, 146, 140), (round(i * 24 - (self.scroll % 24)), gy - 8, 1, 8))
        if post is not None:
            for i in range(-1, W // 220 + 2):
                x = i * 220 - (self.scroll % 220) + 60
                screen.blit(post, post.get_rect(midbottom=(round(x), gy - 6)))
        # a estrada, com o asfalto granulado
        screen.fill((58, 58, 64), (0, gy, W, 70))
        screen.fill((44, 44, 50), (0, gy, W, 3))
        for gx, gy2 in self.grain:
            screen.fill((70, 70, 76), (round((gx - self.scroll) % 1400) - 200, gy + gy2, 2, 1))
        screen.fill((30, 30, 34), (0, gy + 70, W, 6))
        for i in range(-1, 12):
            x = i * 100 - self.scroll % 100
            screen.fill((236, 214, 120), (round(x), gy + 33, 50, 4))
        # o carro
        shake = 0
        if COUGH <= self.ticks < PUFF:
            shake = random.choice((-2, -1, 0, 1, 2))
        elif PUFF <= self.ticks < PUFF + 12:
            shake = (PUFF + 12 - self.ticks) // 3 * (1 if self.ticks % 2 else -1)
        if self.hd:                                       # carro pronto: a roda pisa na estrada
            cx, cy = round(self.car_x), gy + 46 - HD_WHEELS[self.car_kind][2] * CAR_SCALE + shake
            shadow = pecas.shadow(self.car.get_width() + 10, 22, 90)
            screen.blit(shadow, (cx - 5, gy + 36))
            self._heads(screen, cx, cy)                   # a turma atrás do vidro translúcido
            screen.blit(self.car, (cx, cy))
        else:
            cx, cy = round(self.car_x), gy + 46 - self.car.get_height() + shake
            screen.blit(self.car, (cx, cy))
            self._heads(screen, cx, cy)
        if self.moto is not None:
            self._moto(screen, cx + self.car.get_width() + 10, gy + 46)
        if self.door is not None:
            door = pygame.Surface((40, 52), pygame.SRCALPHA)
            door.fill((244, 244, 240))
            door.fill((90, 130, 170), (4, 4, 32, 20))
            door.fill((190, 192, 198), (24, 30, 8, 3))
            door = pygame.transform.rotate(door, self.door[3])
            screen.blit(door, door.get_rect(center=(round(self.door[0]), round(self.door[1]))))
        self._wheels(screen, cx, cy)
        for x, y, r, life in self.smoke:
            a = max(0, min(200, life * 4))
            puff = pygame.Surface((round(r * 2), round(r * 2)), pygame.SRCALPHA)
            pygame.draw.circle(puff, (170, 170, 176, a), (round(r), round(r)), round(r))
            screen.blit(puff, (round(x - r), round(y - r)))
        # textos
        if self.ticks < COUGH:
            self.ui.text(screen, "A CAMINHO DA AVENTURA", theme.S, theme.BRASS, (W // 2, 50))
        if PUFF <= self.ticks < PUFF + 50:
            self.ui.text(screen, "PUFF!", theme.XL, theme.BONE, (cx + self.car.get_width() - 60, cy - 30))
        if self.ticks >= PUFF + 20:
            self.ui.text(screen, BREAK_LINE.get(self.vehicle, line), theme.M, theme.BRASS, (W // 2, 70))
        if (self.ticks // 30) % 2:
            self.ui.text(screen, "ESQUIVA: PULAR", theme.XS, theme.LINE, (W - 90, H - 20))

    def _heads(self, screen, cx, cy):
        """Os quatro nas janelas: cada cabeça cortada no vidro, balançando com a estrada."""
        s = CAR_SCALE
        if self.glass is not None:
            glass = self.glass.move(cx, cy)
            bob = (self.ticks // 8) % 2 if self.speed > 0 else 0
            old = screen.get_clip()
            screen.set_clip(glass)
            n = max(1, len(self.heads))
            for i, head in enumerate(self.heads):
                big = pygame.transform.scale(head, (head.get_width() * 3 // 2, head.get_height() * 3 // 2))
                x = glass.x + glass.w * (i + 0.6) / (n + 0.2)
                y = glass.bottom + 6 + (bob if i % 2 else -bob)
                screen.blit(big, big.get_rect(midbottom=(round(x), y)))
            screen.set_clip(old)
            return
        (gx, gy, gw, gh), pillar = GLASS["uno" if self.vehicle == "uno" else "city"]
        glass = pygame.Rect(cx + gx * s, cy + gy * s, gw * s, gh * s)        # as duas janelas juntas
        bob = (self.ticks // 8) % 2 if self.speed > 0 else 0
        old = screen.get_clip()
        screen.set_clip(glass)
        n = max(1, len(self.heads))
        for i, head in enumerate(self.heads):
            x = glass.x + glass.w * (i + 0.5) / n
            y = glass.bottom + 4 + (bob if i % 2 else -bob)
            screen.blit(head, head.get_rect(midbottom=(round(x), y)))
        screen.set_clip(old)
        pillar_color = (244, 244, 240) if self.vehicle == "uno" else (62, 65, 72)
        pygame.draw.rect(screen, pillar_color, (cx + pillar * s, glass.y, 3 * s, glass.h))   # a coluna do meio

    def _moto(self, screen, x, ground):
        """A moto na frente do carro, com o P1 e empinando enquanto o carro anda."""
        wheelie = 0 if self.speed <= 0 else 12 + 6 * math.sin(self.ticks * 0.15)
        bike = self.moto
        if self.rider is not None:                     # o P1 sentado no banco (gira junto quando empina)
            bike = self.moto.copy()
            head = pygame.transform.scale(self.rider, (self.rider.get_width() * 2, self.rider.get_height() * 2))
            bike.blit(head, head.get_rect(midbottom=self.seat))
        img = pygame.transform.rotate(bike, wheelie)
        rect = img.get_rect(midbottom=(x + self.moto.get_width() // 2, ground + 4))
        screen.blit(img, rect)

    def _wheels(self, screen, cx, cy):
        s = CAR_SCALE
        angle = self.scroll / 15
        if self.hd:                                       # os raios girando por cima do aro
            xs, wy, _ = HD_WHEELS[self.car_kind]
            for wx in xs:
                c = (cx + wx * s, cy + wy * s)
                for j in range(2):
                    a = angle + j * math.pi / 2
                    dx, dy = math.cos(a) * 15, math.sin(a) * 15
                    pygame.draw.line(screen, (60, 62, 70), (c[0] - dx, c[1] - dy), (c[0] + dx, c[1] + dy), 3)
                pygame.draw.circle(screen, (120, 124, 134), c, 5)
            return
        for wx in (100 - 52, 100 + 52):
            c = (cx + wx * s, cy + 70 * s)
            for j in range(2):
                a = angle + j * math.pi / 2
                dx, dy = math.cos(a) * 12, math.sin(a) * 12
                pygame.draw.line(screen, (90, 90, 96), (c[0] - dx, c[1] - dy), (c[0] + dx, c[1] + dy), 3)

    @staticmethod
    def _house(screen, x, y, v):
        colors = ((200, 170, 130), (170, 190, 210), (220, 200, 160))
        c = colors[v % 3]
        pygame.draw.rect(screen, c, (round(x), y - 70, 90, 70))
        pygame.draw.polygon(screen, (150, 70, 60), [(x - 8, y - 70), (x + 45, y - 104), (x + 98, y - 70)])
        pygame.draw.rect(screen, (90, 130, 170), (round(x) + 14, y - 54, 20, 18))
        pygame.draw.rect(screen, (110, 80, 60), (round(x) + 56, y - 40, 20, 40))

    @staticmethod
    def _roadside(screen, kind, x, y, v):
        x = round(x)
        if kind == "pinheiro":
            for dx in (0, 46):
                pygame.draw.rect(screen, (80, 56, 40), (x + dx + 16, y - 24, 8, 24))
                pygame.draw.polygon(screen, (34, 80, 44), [(x + dx, y - 20), (x + dx + 20, y - 96), (x + dx + 40, y - 20)])
        elif kind == "predio":
            h = 120 + v * 30
            pygame.draw.rect(screen, (50, 54, 70), (x, y - h, 80, h))
            for wy in range(y - h + 12, y - 10, 22):
                for wx in (x + 10, x + 34, x + 58):
                    on = (wx * 3 + wy) % 5 != 0
                    pygame.draw.rect(screen, (230, 220, 140) if on else (40, 44, 56), (wx, wy, 12, 10))
        elif kind == "clinica":
            pygame.draw.rect(screen, (244, 242, 246), (x, y - 90, 110, 90))
            pygame.draw.rect(screen, (230, 120, 170), (x, y - 96, 110, 10))
            pygame.draw.rect(screen, (230, 120, 170), (x + 46, y - 74, 18, 6))
            pygame.draw.rect(screen, (230, 120, 170), (x + 52, y - 80, 6, 18))
            pygame.draw.rect(screen, (150, 190, 220), (x + 40, y - 40, 30, 40))
        else:                                   # cerca da mansão
            for dx in range(0, 120, 14):
                pygame.draw.rect(screen, (30, 26, 34), (x + dx, y - 60, 5, 60))
                pygame.draw.polygon(screen, (200, 170, 80), [(x + dx - 2, y - 60), (x + dx + 2, y - 68), (x + dx + 7, y - 60)])
            pygame.draw.rect(screen, (30, 26, 34), (x, y - 44, 120, 4))
