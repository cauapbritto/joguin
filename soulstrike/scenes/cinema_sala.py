"""A sala de cinema (extra liberado ao zerar a campanha).

A turma (Cauanzera, Aryel, Borba Jr e Albeguinio) entra pelo corredor e senta nas poltronas, a luz
apaga, o projetor acende e o telão vem chegando até ocupar a tela inteira. Aí a história passa
sozinha (os planos de scenes/filme.py). No FILME COMPLETO, entre um capítulo e outro, a câmera volta
para a plateia reagindo; no fim, os créditos sobem no telão, a luz acende e a turma levanta e aplaude.

ATACAR adianta o plano. Segurar ESC (ou PAUSA) por meio segundo volta para o menu do cinema."""
import math
import random

import pygame

from .. import config, progress, theme
from ..ui import MenuList
from .campaign import CINEMA, CREATOR, TESTERS, TESTERS_NOTE, _pressed, _RunMenuScene, draw_seals

W, H = config.SCREEN_W, config.SCREEN_H
SCREEN = pygame.Rect(120, 26, 720, 330)          # o telão, visto da plateia
TURMA = ("cauanzera", "aryel", "borba", "albeguinio")
SEATS_X = (390, 450, 510, 570)                    # poltronas da turma (fileira do meio)
ROWS = (378, 428, 484)                            # encosto das fileiras (do fundo para a frente)
ROW_TURMA = 1
ENTRADA, APAGA, ABRE, FECHA, PLATEIA, APLAUSO = 190, 50, 50, 40, 150, 170
HOLD_EXIT = 30                                    # quadros segurando ESC para sair
CREDITS_FRAMES = 620
# o que a plateia fala depois de cada capítulo (história que fecha o capítulo -> falas)
REACTIONS = {"fim_capitulo1": ("UAU!", "O CRISTAL!", "EU ERA MAU?", "PIPOCA?"),
             "fim_capitulo2": ("KKKK", "O EXO!", "LARGUEI!", "O CACO..."),
             "fim_capitulo3": ("OI SUMIDO KKK", "GPU DE GRAÇA?", "NEM LEMBRO", "VISUALIZEI"),
             "final": ("LÊ OS TERMOS!", "VIEMOS A PÉ", "O CITY...", "FECHEI O CAIXA")}
FULL = ("FILME COMPLETO", tuple(k for label, keys in CINEMA if "REUNIÃO" not in label
                                for k in keys if k not in ("creditos", "epilogo")) + ("creditos", "epilogo"))


def _ease(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)


def _lerp_rect(a, b, t):
    return pygame.Rect(round(a.x + (b.x - a.x) * t), round(a.y + (b.y - a.y) * t),
                       round(a.w + (b.w - a.w) * t), round(a.h + (b.h - a.h) * t))


class CreditsRoll:
    """Os créditos subindo dentro do telão: quem criou o jogo e quem testou primeiro."""

    def __init__(self, game):
        self.game = game
        self.age = 0
        self.done = False

    def update(self):
        self.age += 1
        if self.age >= CREDITS_FRAMES:
            self.done = True

    def skip(self):
        self.done = True

    def _sprite(self, surf, sprite, **where):
        try:
            img = self.game.assets.sheet_sprites(sprite).pose("frente", "parado", (self.age // 30) % 2)
            img = pygame.transform.scale(img, (img.get_width() * 2, img.get_height() * 2))
            surf.blit(img, img.get_rect(**where))
        except (FileNotFoundError, pygame.error, KeyError):
            pass

    def draw(self, surf, ui):
        surf.fill((0, 0, 0))
        if self.done:
            ui.text(surf, "FIM", theme.XL, theme.BRASS, (W // 2, H // 2))
            return
        y = surf.get_height() + 20 - self.age * 0.9
        ui.logo(surf, (W // 2, round(y)))
        y += 70
        ui.text(surf, "A CAMPANHA", theme.S, theme.MUTED, (W // 2, round(y)))
        y += 70
        ui.text(surf, "CRIADO POR", theme.M, theme.BRASS, (W // 2, round(y)))
        y += 34
        sprite, name, what = CREATOR
        self._sprite(surf, sprite, midtop=(W // 2, round(y)))
        y += 150
        ui.text(surf, name, theme.M, theme.BONE, (W // 2, round(y)))
        ui.text(surf, what, theme.XS, theme.BRASS, (W // 2, round(y) + 30))
        y += 110
        ui.text(surf, "QUEM TESTOU PRIMEIRO", theme.M, theme.BRASS, (W // 2, round(y)))
        for i, line in enumerate(TESTERS_NOTE):
            ui.text(surf, line, theme.XS, theme.MUTED, (W // 2, round(y) + 32 + i * 20))
        y += 130
        for sprite, name, role in TESTERS:
            self._sprite(surf, sprite, midright=(W // 2 - 150, round(y) + 6))
            ui.text(surf, "inspirou o " + role, theme.XS, theme.BRASS, (W // 2 - 120, round(y) - 8), anchor="midleft")
            ui.text(surf, name, theme.S, theme.BONE, (W // 2 - 120, round(y) + 12), anchor="midleft")
            y += 90
        y += 40
        ui.text(surf, "OBRIGADO POR JOGAR", theme.M, theme.BONE, (W // 2, round(y)))


class CinemaScene(_RunMenuScene):
    """O cinema de verdade: sala, turma nas poltronas, telão e o filme passando sozinho."""

    phase = "story"
    music = "menu"

    def __init__(self, game, index=0):
        super().__init__(game)
        self.items = (FULL,) + tuple(CINEMA)
        self.menu = MenuList([(label, str(i)) for i, (label, _) in enumerate(self.items)] + [("VOLTAR", "back")],
                             topleft=(SCREEN.x + 30, SCREEN.y + 48), width=310, row_h=30)
        self.menu.index = min(index, len(self.items))
        self.state, self.timer = "menu", 0
        self.queue = []
        self.film = None
        self.screen_surf = pygame.Surface((W, H))
        self.hold = 0
        self.last_key = None
        self.lines = ()
        self.rng = random.Random(7)
        self.motes = [(self.rng.random(), self.rng.random(), self.rng.uniform(0.3, 0.9)) for _ in range(50)]
        self._room = None

    # ── fluxo ────────────────────────────────
    def _choose(self, choice):
        if self.state != "menu":
            return
        self.sfx("confirm")
        if choice == "back":
            from .menus import ModeScene
            self.game.change(ModeScene(self.game, "campanha"))
            return
        self.queue = list(self.items[int(choice)][1])
        self.state, self.timer = "entrada", 0

    def _next_film(self):
        """Puxa a próxima história da fila (ou os créditos)."""
        key = self.queue.pop(0)
        self.last_key = key
        if key == "creditos":
            self.film = CreditsRoll(self.game)
        else:
            from .filme import Film
            self.film = Film(self.game, key)
            self.film.hold_title = True

    def _set(self, state):
        self.state, self.timer = state, 0

    def update(self):
        if self.state == "menu":
            super().update()
            return
        self.ticks += 1
        self.timer += 1
        slots = self.active_slots()
        held = pygame.key.get_pressed()[pygame.K_ESCAPE] if pygame.display.get_init() else False
        held = held or any(self.game.inputs[s].held("pause") for s in slots)
        self.hold = self.hold + 1 if held else 0
        if self.hold >= HOLD_EXIT:
            self.hold = 0
            self.film, self.queue = None, []
            self._set("menu")
            return
        skip = self.ticks > 10 and _pressed(self.game, slots, "confirm", "attack")
        if self.state == "entrada" and (self.timer >= ENTRADA or skip):
            self._next_film()
            self._set("apaga")
        elif self.state == "apaga" and self.timer >= APAGA:
            self._set("abre")
        elif self.state == "abre" and self.timer >= ABRE:
            self.film.hold_title = False
            self._set("filme")
        elif self.state == "filme":
            if skip:
                self.sfx("click", 0.4)
                self.film.skip()
            self.film.update()
            if self.film.done:
                if not self.queue:
                    self._set("fecha")
                elif self.last_key in REACTIONS:
                    self.lines = REACTIONS[self.last_key]
                    self._set("plateia")
                else:
                    self._next_film()
        elif self.state == "plateia" and (self.timer >= PLATEIA or skip):
            self._next_film()
            self._set("abre")
        elif self.state == "fecha" and self.timer >= FECHA:
            self._set("aplauso")
        elif self.state == "aplauso" and (self.timer >= APLAUSO or skip):
            self.film = None
            self._set("menu")

    def handle(self, event):
        if self.state == "menu":
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                self._choose("back")
                return
            super().handle(event)
        elif event.type == pygame.KEYDOWN and event.key in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_KP_ENTER):
            if self.state == "filme" and self.film is not None:
                self.film.skip()

    # ── quanto o telão ocupa (0 = visto da plateia, 1 = tela cheia) ──
    @property
    def zoom(self):
        s, t = self.state, self.timer
        if s == "abre":
            return _ease(t / ABRE)
        if s == "filme":
            return 1.0
        if s == "fecha":
            return 1 - _ease(t / FECHA)
        if s == "plateia":
            return 1 - _ease(t / 30)
        return 0.0

    @property
    def dark(self):
        """Quanto a sala está apagada (0 acesa, 1 escura)."""
        s, t = self.state, self.timer
        if s in ("menu", "entrada"):
            return 0.0
        if s == "apaga":
            return _ease(t / APAGA)
        if s == "aplauso":
            return 1 - _ease(t / 60)
        return 1.0

    # ── desenho ──────────────────────────────
    def draw(self, screen):
        z = self.zoom
        if z >= 1.0 and self.film is not None:
            self.film.draw(screen, self.ui)
            self._draw_exit_hint(screen)
            return
        self._draw_room(screen)
        rect = _lerp_rect(SCREEN, screen.get_rect(), z)
        if self.film is not None and self.state not in ("menu", "entrada"):
            self.film.draw(self.screen_surf, self.ui)
            screen.blit(pygame.transform.smoothscale(self.screen_surf, rect.size), rect)
        if self.state == "plateia":
            self._draw_reactions(screen)                         # os balões ficam na frente do telão
        if self.state == "aplauso" and self.timer > 20:
            for i in range(len(TURMA)):
                if (self.timer // 12 + i) % 2 == 0:
                    lift = (self.timer % 12) * 2
                    self.ui.text(screen, "CLAP!", theme.XS, theme.BRASS,
                                 (SEATS_X[i] + (12 if i % 2 else -12), ROWS[ROW_TURMA] - 70 - lift))
        if self.state == "menu":
            self._draw_menu(screen)
        self._draw_exit_hint(screen)

    def _room_base(self):
        """Paredes, cortinas e poltronas vazias (desenhado uma vez)."""
        if self._room is not None:
            return self._room
        s = pygame.Surface((W, H))
        for y in range(H):                                        # parede vinho escurecendo para baixo
            k = y / H
            s.fill((round(60 - 30 * k), round(18 - 8 * k), round(26 - 10 * k)), (0, y, W, 1))
        for x in range(0, W, 48):                                 # painéis da parede
            s.fill((70, 24, 34), (x, 0, 2, SCREEN.bottom + 20))
        frame = SCREEN.inflate(16, 16)
        s.fill((20, 14, 18), frame)
        s.fill((150, 110, 50), frame.inflate(-6, -6))
        s.fill((12, 10, 14), SCREEN)
        for side in (-1, 1):                                      # cortinas vermelhas dos dois lados
            x0 = SCREEN.x - 70 if side < 0 else SCREEN.right + 6
            for k in range(8):
                shade = 120 + (k % 2) * 30
                s.fill((shade, 20, 30), (x0 + k * 8, 0, 8, SCREEN.bottom + 30))
            s.fill((90, 12, 22), (x0, SCREEN.bottom + 20, 64, 10))
        s.fill((150, 20, 30), (SCREEN.x - 70, 0, SCREEN.w + 140, 14))      # bambinela de cima
        for x in range(SCREEN.x - 70, SCREEN.right + 70, 16):
            pygame.draw.circle(s, (170, 30, 40), (x + 8, 14), 8)
        s.fill((26, 12, 18), (0, ROWS[0] - 12, W, H))             # chão
        self._room = s
        return s

    def _seat_row(self, screen, y, light):
        for x in range(40, W - 20, 60):
            if 880 <= x <= 920:                                   # corredor
                continue
            back = pygame.Rect(x - 24, y, 48, 34)
            c = (round(150 * light), round(28 * light), round(40 * light))
            pygame.draw.rect(screen, c, back, border_radius=8)
            pygame.draw.rect(screen, (round(90 * light), round(16 * light), round(24 * light)), back, 2, border_radius=8)
            screen.fill((round(110 * light), round(20 * light), round(30 * light)), (x - 28, y + 24, 6, 18))
            screen.fill((round(110 * light), round(20 * light), round(30 * light)), (x + 22, y + 24, 6, 18))

    def _draw_room(self, screen):
        dark = self.dark
        screen.blit(self._room_base(), (0, 0))
        light = 1 - 0.65 * dark
        shade = pygame.Surface((W, H), pygame.SRCALPHA)
        shade.fill((0, 0, 0, round(200 * dark)))
        screen.blit(shade, (0, 0))
        if self.state in ("menu", "entrada"):                    # telão aceso esperando o filme
            glow = pygame.Surface(SCREEN.size)
            glow.fill((26, 22, 34))
            screen.blit(glow, SCREEN)
            if self.state == "entrada":
                self.ui.text(screen, "O FILME JÁ VAI COMEÇAR", theme.S, theme.MUTED, SCREEN.center)
        if dark > 0.05:
            self._beam(screen, dark)
        self._seat_row(screen, ROWS[0], light)
        self._draw_turma(screen, light)
        self._seat_row(screen, ROWS[2], light)

    def _beam(self, screen, dark):
        """O feixe do projetor (vem de trás da plateia até o telão), com poeira flutuando."""
        beam = pygame.Surface((W, H), pygame.SRCALPHA)
        origin = (W // 2, H + 40)
        pygame.draw.polygon(beam, (230, 230, 255, round(26 * dark)),
                            [origin, SCREEN.topleft, SCREEN.topright])
        pygame.draw.polygon(beam, (230, 230, 255, round(18 * dark)),
                            [origin, SCREEN.bottomleft, SCREEN.bottomright])
        screen.blit(beam, (0, 0))
        for x, y, v in self.motes:
            k = (y + self.ticks * v / 300) % 1.0
            px = origin[0] + (SCREEN.x + x * SCREEN.w - origin[0]) * k
            py = origin[1] + (SCREEN.y + 40 - origin[1]) * k
            screen.fill((255, 250, 220), (round(px), round(py), 2, 2))

    def _friend_pose(self, i):
        """Onde está o amigo ``i`` e o que está fazendo: (x, sentado?, andando?, pulo)."""
        seat = SEATS_X[i]
        if self.state == "entrada":
            start = 960 + i * 50                                  # entra pelo corredor da direita
            t = (self.timer - i * 22) / 110
            if t <= 0:
                return None
            x = round(start + (seat - start) * _ease(t))
            return x, t >= 1.1, t < 1, 0
        if self.state == "menu":
            return None
        if self.state == "aplauso":
            hop = abs(math.sin((self.timer + i * 9) * 0.25)) * 10 if self.timer > 20 else 0
            return seat, self.timer < 20, False, hop
        if self.state == "plateia" and 30 < self.timer < PLATEIA - 30:
            hop = abs(math.sin((self.timer + i * 7) * 0.3)) * 6
            return seat, True, False, hop
        return seat, True, False, 0

    def _draw_turma(self, screen, light):
        y_row = ROWS[ROW_TURMA]
        self._seat_row(screen, y_row, light)
        for i, key in enumerate(TURMA):
            pose = self._friend_pose(i)
            if pose is None:
                continue
            x, sitting, walking, hop = pose
            try:
                sprites = self.assets.sheet_sprites(key)
            except (FileNotFoundError, pygame.error, KeyError):
                continue
            img = (sprites.frame("esquerda", self.ticks // 5) if walking
                   else sprites.pose("costas", "parado", 0))
            img = pygame.transform.scale(img, (img.get_width() * 2, img.get_height() * 2))
            if light < 1:
                img = img.copy()
                k = round(255 * max(0.35, light))
                img.fill((k, k, k), special_flags=pygame.BLEND_RGB_MULT)
            foot = y_row + (44 if sitting else 26) - round(hop)
            screen.blit(img, img.get_rect(midbottom=(x, foot)))
        # o encosto da fileira da turma vai por cima (só a cabeça aparece de quem está sentado)
        for i in range(len(TURMA)):
            pose = self._friend_pose(i)
            if pose and pose[1]:
                x = SEATS_X[i]
                back = pygame.Rect(x - 24, y_row + 14, 48, 22)
                pygame.draw.rect(screen, (round(150 * light), round(28 * light), round(40 * light)), back,
                                 border_radius=6)

    def _draw_reactions(self, screen):
        if not (30 < self.timer < PLATEIA - 20):
            return
        from ..casa import draw_bubble
        for i, line in enumerate(self.lines[:len(TURMA)]):
            if self.timer < 30 + i * 18:
                continue
            draw_bubble(screen, self.ui, self.assets, line, SEATS_X[i], ROWS[ROW_TURMA] - (28 if i % 2 else 52))

    def _draw_menu(self, screen):
        self.ui.text(screen, "CINEMA", theme.M, theme.BRASS, (SCREEN.x + 30, SCREEN.y + 24), anchor="midleft")
        self.menu.draw(screen, self.ui, self.ticks)
        box = pygame.Rect(SCREEN.right - 340, SCREEN.y + 100, 316, 170)
        draw_seals(self, screen, box, progress.seals(), "SELOS DE ZERADO")
        self.footer(screen, [("↑↓", "ESCOLHER"), ("ENTER", "ASSISTIR"), ("ESC", "VOLTAR")])

    def _draw_exit_hint(self, screen):
        if self.state == "menu" or not self.hold:
            return
        k = self.hold / HOLD_EXIT
        center = (W - 40, H - 40)
        pygame.draw.circle(screen, theme.LINE, center, 14, 3)
        pygame.draw.arc(screen, theme.BRASS, pygame.Rect(center[0] - 14, center[1] - 14, 28, 28),
                        math.pi / 2, math.pi / 2 + math.tau * k, 3)
        self.ui.text(screen, "SEGURE ESC PARA SAIR", theme.XS, theme.BONE, (W - 64, H - 40), anchor="midright")
