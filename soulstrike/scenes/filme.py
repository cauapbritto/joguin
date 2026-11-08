"""O cinema da campanha: cada página da história vira um plano de filme que passa sozinho.

Um plano tem o cenário de verdade (o mapa da fase, visto por uma câmera que anda devagar), atores
(os sprites entram andando e param na marca), efeitos (luz roxa da voz do cristal, clarão quando
algo quebra, chuva na abertura, tremida) e legenda dentro da faixa preta de baixo, como no cinema.
Não é vídeo: tudo é desenhado na hora com a arte do jogo, então mudar uma fala não refaz nada.

``Film`` só sabe tocar uma história (as páginas de ``campaign.STORY[key]``) numa superfície do
tamanho da tela. Quem usa: ``StoryScene`` (a campanha, em tela cheia) e a sala de cinema
(``scenes/cinema_sala.py``), que joga o mesmo filme no telão."""
import math
import random

import pygame

from .. import config, theme
from ..arena import MAPS_BY_KEY

TITLE = 80            # quadros do cartão de título no começo de cada história
FADE = 18             # quadros do escuro entre um plano e outro
TYPE_SPEED = 1.4      # letras por quadro da legenda
BAR_TOP = 44          # faixa preta de cima (a de baixo cresce com a legenda)
VOICE_TINT = (120, 50, 200)

# ── onde a câmera olha em cada mapa (centro do plano, em pixels do mapa) ──
FOCUS = {"hub_casa": (960, 400)}
QUINTAL = (1180, 820)       # no quintal da Casa, perto do City

# ── planos montados à mão: (história, página) -> ajustes do plano ──
#   cast: atores (chave do sprite; "sombra:x" = alma corrompida; "~x" = começa caído e levanta)
#   fx: chuva, roxo, clarao, tremor, poeira, porta
#   zoom: 1.0 plano geral, 1.4 aproximado, 1.8 close
SHOTS = {
    ("abertura", 0): {"cast": ("cauanzera", "aryel", "borba", "albeguinio"), "zoom": 1.0, "fx": ("poeira",)},
    ("abertura", 1): {"cast": ("aryel",), "zoom": 1.6},
    ("abertura", 2): {"zoom": 1.3, "fx": ("roxo",)},
    ("abertura", 3): {"cast": ("aryel",), "zoom": 1.2, "fx": ("chuva",), "exit": True, "focus": QUINTAL},
    ("abertura", 4): {"cast": ("cauanzera", "borba", "albeguinio"), "zoom": 1.1, "fx": ("poeira",)},
    ("epilogo", 0): {"cast": ("borba",), "zoom": 1.4, "focus": QUINTAL},
    ("prologo", 1): {"zoom": 1.5, "fx": ("roxo",)},
    ("fim_capitulo1", 0): {"zoom": 1.6, "fx": ("clarao", "tremor")},
    ("fim_capitulo1", 1): {"cast": ("~aryel",), "zoom": 1.4},
    ("fim_capitulo1", 3): {"cast": ("miliciano", "miliciano"), "zoom": 1.1, "exit": True},
    ("fim_capitulo2", 0): {"zoom": 1.5, "fx": ("clarao", "tremor")},
    ("fim_capitulo2", 2): {"cast": ("~albeguinio", "~cauanzera"), "zoom": 1.3},
    ("fim_capitulo2", 3): {"cast": ("miliciano",), "zoom": 1.2, "fx": ("radio",)},
    ("fim_capitulo2", 6): {"cast": ("albeguinio",), "zoom": 1.8},
    ("fim_capitulo3", 0): {"zoom": 1.5, "fx": ("clarao", "tremor")},
    ("final", 1): {"zoom": 1.6, "fx": ("clarao", "tremor")},
    ("final", 2): {"zoom": 1.3, "fx": ("roxo",)},
    ("final", 4): {"cast": ("aryel", "borba", "albeguinio"), "zoom": 1.1, "fx": ("porta",)},
    ("final", 6): {"cast": ("miliciano", "miliciano"), "zoom": 1.1, "exit": True},
    ("epilogo", 4): {"cast": ("cauanzera", "aryel", "borba", "albeguinio"), "zoom": 1.0, "fx": ("poeira",)},
}


def page_frames(text):
    """Quanto tempo uma página fica na tela: entra, digita e espera dar tempo de ler."""
    return FADE + math.ceil(len(text) / TYPE_SPEED) + 70 + len(text) * 2


def _furnish_casa(surf, assets):
    """A sala da Casa com os móveis principais (no jogo eles são peças soltas do HubMatch)."""
    from .. import casa_art as art
    from ..campaign import TILE_PX as T
    from ..lobbies import CASA_SPLIT, CASA_TOP
    art.use(assets)
    oy = CASA_TOP * T

    def put(fn, x, y, *args, **kw):
        b = art.bake(fn, *args, **kw)
        surf.blit(b.image, (x + b.dx, y + b.dy))
    art.rug(surf, 17 * T, oy + 5 * T, 14 * T, 6 * T)
    put(art.window_wall, 13 * T, oy + 4)
    put(art.window_wall, 32 * T, oy + 4)
    for k in range(4):
        put(art.chair, 21 * T + 20 + k * 56, oy + 7 * T - 14)
    put(art.table, 21 * T, oy + 7 * T + 10, 6 * T, 60)
    for k in range(4):
        put(art.chair, 21 * T + 20 + k * 56, oy + 9 * T + 4)
    put(art.sofa, 18 * T, oy + 11 * T + 30, 150)
    put(art.sofa, 27 * T, oy + 11 * T + 30, 150, (120, 70, 90))
    for x, y in ((16 * T + 20, oy + 4 * T + 20), (32 * T, oy + 4 * T + 20)):
        put(art.lamp, x, y)
    for x, y in ((12 * T, oy + 3 * T), (36 * T, oy + 3 * T)):
        put(art.plant, x, y)
    put(art.city_car, 31 * T, CASA_SPLIT + 5 * T)


def _ease(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)


class Film:
    """Toca uma história (título + páginas) e avisa quando acabou (``done``)."""

    def __init__(self, game, key):
        from ..campaign import STORY
        self.game, self.key = game, key
        self.heading, self.map_key, self.pages = STORY[key]
        self.page = 0
        self.age = 0                     # quadros desde o começo da página atual
        self.title_left = TITLE
        self.shown = 0.0
        self.done = False
        self.hold_title = False          # a sala de cinema segura o título aceso enquanto a luz apaga
        self.rng = random.Random(key)
        self.drops = [(self.rng.randrange(config.SCREEN_W), self.rng.randrange(config.SCREEN_H),
                       self.rng.uniform(7, 12)) for _ in range(90)]
        self.motes = [(self.rng.random(), self.rng.random(), self.rng.uniform(0.2, 0.6)) for _ in range(40)]

    # ── estado ───────────────────────────────
    @property
    def text(self):
        return self.pages[self.page][2]

    @property
    def shot(self):
        return SHOTS.get((self.key, self.page), {})

    @property
    def length(self):
        return page_frames(self.text)

    def next_page(self):
        if self.page + 1 < len(self.pages):
            self.page += 1
            self.age = 0
            self.shown = 0.0
        else:
            self.done = True

    def skip(self):
        """ATACAR: no título pula o título; com a legenda digitando mostra tudo; senão vai para a próxima."""
        if self.title_left > 0:
            self.title_left = 0
        elif self.shown < len(self.text):
            self.shown = len(self.text)
            self.age = max(self.age, FADE)
        else:
            self.next_page()

    def update(self):
        if self.done:
            return
        if self.title_left > 0:
            self.title_left -= 1
            return
        self.age += 1
        if self.age > FADE // 2:
            self.shown = min(len(self.text), self.shown + TYPE_SPEED)
        if self.age >= self.length:
            self.next_page()

    # ── desenho ──────────────────────────────
    def _map(self):
        """O mapa inteiro em tamanho real (piso + paredes), guardado no jogo para não refazer."""
        cache = self.game.__dict__.setdefault("_film_maps", {})
        if self.map_key not in cache:
            from ..arena import Arena
            arena = Arena(MAPS_BY_KEY[self.map_key], self.game.assets)
            full = arena.floor.copy()

            class _Origin:
                x = y = 0
            arena.draw_walls(full, _Origin)
            if self.map_key == "hub_casa":
                _furnish_casa(full, self.game.assets)
            cache[self.map_key] = full
        return cache[self.map_key]

    def _camera(self, W, H, zoom, t):
        """Retângulo do mapa que aparece: a câmera anda um pouco durante o plano (para um lado ou outro)."""
        full = self._map()
        mw, mh = full.get_size()
        vw, vh = min(mw, round(W / zoom)), min(mh, round(H / zoom))
        fx, fy = self.shot.get("focus") or FOCUS.get(self.map_key, (mw / 2, mh / 2))
        side = 1 if self.page % 2 == 0 else -1
        drift = 70 * (side * (t - 0.5))
        cx = max(vw / 2, min(mw - vw / 2, fx + drift))
        cy = max(vh / 2, min(mh - vh / 2, fy + 20 * (0.5 - t)))
        return pygame.Rect(round(cx - vw / 2), round(cy - vh / 2), vw, vh)

    def draw(self, screen, ui):
        W, H = screen.get_size()
        screen.fill(theme.INK)
        if self.title_left > 0:
            self._draw_title(screen, ui)
            return
        portrait, speaker, text = self.pages[self.page]
        shot = self.shot
        from ..campaign import BROKEN, CRYSTAL, FRAGMENT, VOICE
        objeto = portrait in (CRYSTAL, BROKEN, FRAGMENT, VOICE)
        zoom = shot.get("zoom", 1.25 if speaker else 1.05)
        t = self.age / max(1, self.length)
        zoom *= 1 + 0.06 * _ease(t)                      # aproxima devagar durante o plano
        fx = shot.get("fx", ())
        shake = (0, 0)
        if "tremor" in fx and self.age < 40:
            k = (40 - self.age) // 6
            shake = (self.rng.randint(-k, k), self.rng.randint(-k, k))

        view = self._camera(W, H, zoom, t)
        scene = pygame.transform.scale(self._map().subsurface(view), (W, H))
        screen.blit(scene, shake)
        dim = pygame.Surface((W, H), pygame.SRCALPHA)
        dim.fill((8, 6, 14, 110 if objeto else 70))
        screen.blit(dim, (0, 0))
        if "roxo" in fx or portrait == VOICE:
            self._purple(screen)

        stage_y = H // 2 + 30
        cast = shot.get("cast")
        if objeto:
            self._draw_object(screen, portrait, (W // 2 + shake[0], stage_y - 40 + shake[1]))
        elif cast:
            self._draw_cast(screen, cast, stage_y, zoom, shot.get("exit"))
        else:
            self._draw_cast(screen, (portrait,), stage_y, zoom, False, close=bool(speaker))
        if "chuva" in fx:
            self._rain(screen)
        if "poeira" in fx:
            self._motes(screen)
        if "porta" in fx and self.age < 30:
            glow = pygame.Surface((W, H), pygame.SRCALPHA)
            glow.fill((255, 240, 200, int(160 * (1 - self.age / 30))))
            screen.blit(glow, (0, 0))
        if "clarao" in fx and self.age < 24:
            flash = pygame.Surface((W, H), pygame.SRCALPHA)
            flash.fill((255, 245, 255, int(255 * (1 - self.age / 24))))
            screen.blit(flash, (0, 0))
        self._vignette(screen)
        self._bars_and_subtitle(screen, ui, speaker, text, "radio" in fx, portrait == VOICE)
        if self.age < FADE:                               # entra do escuro
            fade = pygame.Surface((W, H), pygame.SRCALPHA)
            fade.fill((0, 0, 0, int(255 * (1 - self.age / FADE))))
            screen.blit(fade, (0, 0))
        left = self.length - self.age
        if left < 10 and self.page + 1 < len(self.pages):  # e volta para o escuro antes do próximo
            fade = pygame.Surface((W, H), pygame.SRCALPHA)
            fade.fill((0, 0, 0, int(255 * (1 - left / 10))))
            screen.blit(fade, (0, 0))

    def _draw_title(self, screen, ui):
        W, H = screen.get_size()
        k = self.title_left
        alpha = 1.0 if self.hold_title else min(1.0, (TITLE - k) / 16, k / 16)
        color = tuple(round(c * alpha) for c in theme.BRASS)
        size = ui.fit_size(self.heading, W - 120) if hasattr(ui, "fit_size") else theme.L
        ui.text(screen, self.heading, size, color, (W // 2, H // 2 - 10), shadow=False)
        line_w = round((W // 3) * alpha)
        screen.fill(tuple(round(c * alpha) for c in theme.LINE_HI), (W // 2 - line_w // 2, H // 2 + 22, line_w, 2))

    def _draw_object(self, screen, portrait, center):
        from ..campaign import BROKEN, CRYSTAL, FRAGMENT
        from .campaign import draw_crystal, draw_fragment, draw_voice
        ticks = self.game.clock_ticks if hasattr(self.game, "clock_ticks") else self.age
        if portrait == CRYSTAL:
            draw_crystal(screen, center, 110, ticks)
        elif portrait == BROKEN:
            draw_crystal(screen, center, 110, self.age, broken=True)
        elif portrait == FRAGMENT:
            draw_fragment(screen, center, ticks)
        else:
            draw_voice(screen, center, self.age)

    def _sprites(self, key):
        assets = self.game.assets
        if key.startswith("sombra:"):
            return assets.shadow_sprites(key.split(":", 1)[1])
        return assets.sheet_sprites(key)

    def _draw_cast(self, screen, cast, stage_y, zoom, leaving, close=False):
        """Atores lado a lado: entram andando, param na marca e ficam respirando (ou saem, se ``leaving``)."""
        from ..enemies import SHADOW_RIM
        from ..fighter import draw_aura
        W = screen.get_width()
        n = len(cast)
        gap = min(170, (W - 200) // max(1, n))
        walk = 46
        for i, raw in enumerate(cast):
            down = raw.startswith("~")
            key = raw.lstrip("~")
            try:
                sprites = self._sprites(key)
            except (FileNotFoundError, pygame.error, KeyError):
                continue
            mark = W // 2 + round((i - (n - 1) / 2) * gap)
            if close and n == 1:
                mark = W // 2
            start = -60 if i < n / 2 else W + 60
            age = self.age - i * 8
            if down:                                     # caído no chão, levanta no meio do plano
                x = mark
                img = sprites.pose("frente", "parado", 0)
            elif leaving and self.age > self.length * 0.45:
                k = _ease((self.age - self.length * 0.45) / (self.length * 0.35))
                x = round(mark + (W + 120 - mark) * k)
                img = sprites.frame("direita", self.age // 5)
            elif age < walk:
                k = _ease(max(0, age) / walk)
                x = round(start + (mark - start) * k)
                img = sprites.frame("direita" if start < mark else "esquerda", self.age // 5)
            else:
                x = mark
                img = sprites.pose("frente", "parado", (self.age // 36) % 2)
            factor = 5 if close else 4 if zoom >= 1.3 else 3
            if img.get_height() > 50:
                factor = max(2, factor - 1)
            img = pygame.transform.scale(img, (img.get_width() * factor, img.get_height() * factor))
            if down:
                rise = _ease((self.age - self.length * 0.3) / 40)
                img = pygame.transform.rotate(img, 90 * (1 - rise))
            ground = stage_y + 60
            pygame.draw.ellipse(screen, theme.SHADOW, (x - 16 * factor, ground - 8, 32 * factor, 16))
            rect = img.get_rect(midbottom=(x, ground + 4))
            if key.startswith("sombra:"):
                draw_aura(screen, img, rect, SHADOW_RIM, self.age, 3)
            screen.blit(img, rect)

    def _purple(self, screen):
        W, H = screen.get_size()
        pulse = 0.5 + 0.5 * math.sin(self.age * 0.08)
        tint = pygame.Surface((W, H), pygame.SRCALPHA)
        tint.fill((*VOICE_TINT, int(40 + 40 * pulse)))
        screen.blit(tint, (0, 0))

    def _rain(self, screen):
        W, H = screen.get_size()
        for x, y, v in self.drops:
            yy = (y + self.age * v) % (H + 40) - 20
            xx = (x - self.age * v * 0.25) % W
            pygame.draw.line(screen, (150, 170, 210), (xx, yy), (xx - 3, yy + 10), 1)

    def _motes(self, screen):
        W, H = screen.get_size()
        for x, y, v in self.motes:
            xx = (x * W + self.age * v) % W
            yy = (y * H - self.age * v * 0.5) % H
            screen.fill((255, 230, 170), (round(xx), round(yy), 2, 2))

    def _vignette(self, screen):
        W, H = screen.get_size()
        cache = self.game.__dict__.setdefault("_film_vignette", {})
        if (W, H) not in cache:
            v = pygame.Surface((W, H), pygame.SRCALPHA)
            for k in range(14):
                a = 10 + k * 4
                pygame.draw.rect(v, (0, 0, 0, a), (0, 0, W, H), max(1, 40 - k * 3))
            cache[(W, H)] = v
        screen.blit(cache[(W, H)], (0, 0))

    def _bars_and_subtitle(self, screen, ui, speaker, text, radio, voice):
        W, H = screen.get_size()
        lines = ui.wrap(text, theme.S, W - 160)
        bottom = max(84, 26 + (18 if speaker else 0) + len(lines) * 24)
        come = _ease(min(1.0, (self.age + 10) / 20)) if self.page == 0 else 1.0
        top_h, bot_h = round(BAR_TOP * come), round(bottom * come)
        screen.fill((0, 0, 0), (0, 0, W, top_h))
        screen.fill((0, 0, 0), (0, H - bot_h, W, bot_h))
        if top_h >= BAR_TOP:
            ui.text(screen, self.heading, theme.XS, theme.FAINT, (24, BAR_TOP // 2), anchor="midleft")
            ui.text(screen, "ATACAR ADIANTA", theme.XS, theme.FAINT, (W - 24, BAR_TOP // 2), anchor="midright")
        if bot_h < bottom:
            return
        y = H - bottom + 14
        if speaker:
            color = (200, 150, 250) if ("CORROMPIDO" in speaker or "SOMBRIO" in speaker or voice) else theme.BRASS
            ui.text(screen, speaker, theme.XS, color, (W // 2, y + 4))
            y += 18
        from .campaign import VOICE_TEXT
        color = VOICE_TEXT if voice else (190, 210, 190) if radio else theme.BONE
        left = int(self.shown)
        for line in lines:
            part = line[:max(0, left)]
            left -= len(line) + 1
            if part:
                # a linha fica centrada pelo tamanho final (as letras não pulam enquanto aparecem)
                full_w = ui.assets.text_width(line, theme.S)
                ui.text(screen, part, theme.S, color, (W // 2 - full_w // 2, y), anchor="topleft")
            y += 24
