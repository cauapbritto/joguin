"""A saída da Casa da turma: o grupo entra no City do João, pega a estrada até o capítulo e o carro
quebra no caminho (daí em diante é a pé).

Uns 7 segundos: o City entra na tela, roda pela estrada enquanto o cenário vai virando o do capítulo
(floresta, Lag Lobby, Clepalovers ou Mansão), começa a falhar, solta fumaça, faz PUFF e para. ESQUIVA,
ESC ou PAUSE pulam a cena."""
import math
import random

import pygame

from .. import casa_art, config, theme
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


def _car_image():
    surf = pygame.Surface((200, 80), pygame.SRCALPHA)
    casa_art.city_car(surf, 100, 74)
    return pygame.transform.scale(surf, (200 * CAR_SCALE, 80 * CAR_SCALE))


def _head(sprites, tick):
    """A cabeça do herói para a janela do carro (o terço de cima do quadro de frente)."""
    img = sprites.frame("frente", tick // 10)
    h = max(8, img.get_height() * 2 // 5)
    return img.subsurface((0, 0, img.get_width(), h)).copy()


class CarTripScene(Scene):
    """A cena do City indo para a aventura. ``then`` monta a cena seguinte (a fase)."""

    phase = "story"
    music = None

    def __init__(self, game, sprites, chapter, then):
        super().__init__(game)
        self.heads = [_head(s, 0) for s in sprites[:4]]
        self.chapter = chapter if chapter in CHAPTERS else 1
        self.then = then
        self.done = False
        self.car = _car_image()
        self.smoke = []                       # [x, y, raio, vida]
        self.scroll = 0.0
        rng = random.Random(self.chapter)
        self.roadside = [(rng.randint(0, 1400), rng.randint(0, 2)) for _ in range(14)]

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
        start, mid = -self.car.get_width(), W // 2 - self.car.get_width() // 2
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
        screen.fill(_mix(SUBURB_SKY, sky, k))
        gy = self.ground_y
        # morros lá no fundo (andam devagar)
        far = _mix((90, 130, 100), _mix(sky, (20, 20, 30), 0.4), k)
        for i in range(-1, 7):
            x = i * 220 - (self.scroll * 0.2) % 220
            pygame.draw.circle(screen, far, (round(x), gy - 20), 140)
        screen.fill(_mix(SUBURB_GROUND, ground, k), (0, gy - 40, W, H - gy + 40))
        # beira da estrada: casinhas do bairro no começo, depois as coisas do capítulo
        for x0, v in self.roadside:
            x = (x0 - self.scroll * 0.7) % 1400 - 200
            if (x0 * 7) % 100 / 100 < k:
                self._roadside(screen, kind, x, gy - 40, v)
            else:
                self._house(screen, x, gy - 40, v)
        # a estrada
        screen.fill((48, 48, 54), (0, gy, W, 70))
        screen.fill((30, 30, 34), (0, gy + 70, W, 6))
        for i in range(-1, 12):
            x = i * 100 - self.scroll % 100
            screen.fill((230, 210, 120), (round(x), gy + 33, 50, 4))
        # o carro
        shake = 0
        if COUGH <= self.ticks < PUFF:
            shake = random.choice((-2, -1, 0, 1, 2))
        elif PUFF <= self.ticks < PUFF + 12:
            shake = (PUFF + 12 - self.ticks) // 3 * (1 if self.ticks % 2 else -1)
        cx, cy = round(self.car_x), gy + 46 - self.car.get_height() + shake
        screen.blit(self.car, (cx, cy))
        self._heads(screen, cx, cy)
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
            self.ui.text(screen, line, theme.M, theme.BRASS, (W // 2, 70))
        if (self.ticks // 30) % 2:
            self.ui.text(screen, "ESQUIVA: PULAR", theme.XS, theme.LINE, (W - 90, H - 20))

    def _heads(self, screen, cx, cy):
        """Os quatro nas janelas: cada cabeça cortada no vidro, balançando com a estrada."""
        s = CAR_SCALE
        glass = pygame.Rect(cx + 62 * s, cy + 22 * s, 82 * s, 16 * s)       # as duas janelas juntas
        bob = (self.ticks // 8) % 2 if self.speed > 0 else 0
        old = screen.get_clip()
        screen.set_clip(glass)
        n = max(1, len(self.heads))
        for i, head in enumerate(self.heads):
            x = glass.x + glass.w * (i + 0.5) / n
            y = glass.bottom + 4 + (bob if i % 2 else -bob)
            screen.blit(head, head.get_rect(midbottom=(round(x), y)))
        screen.set_clip(old)
        pygame.draw.rect(screen, (62, 65, 72), (cx + 99 * s, glass.y, 3 * s, glass.h))   # a coluna do meio

    def _wheels(self, screen, cx, cy):
        s = CAR_SCALE
        angle = self.scroll / 15
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
