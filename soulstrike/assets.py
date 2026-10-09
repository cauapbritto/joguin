"""Carregamento de recursos: fontes, sons, sprites, texturas e QR codes."""
import io
import re
import unicodedata

import pygame

from . import config
from .data import CHARACTERS

DIRECTIONS = ("frente", "costas", "direita", "esquerda")


class SpriteSet:
    """Quadros de animação de um personagem nas quatro direções."""

    def __init__(self, frames):
        self.frames = frames                     # {direção: [Surface, ...]}
        self._flash = {}

    def frame(self, direction, index):
        frames = self.frames.get(direction) or self.frames["frente"]
        return frames[index % len(frames)]

    def flash(self, direction, index):
        """Silhueta branca do quadro (usada quando o personagem leva dano)."""
        key = (direction, index)
        if key not in self._flash:
            img = self.frame(direction, index)
            mask = pygame.mask.from_surface(img)
            self._flash[key] = mask.to_surface(setcolor=(255, 255, 255, 255), unsetcolor=(0, 0, 0, 0))
        return self._flash[key]

    @property
    def portrait(self):
        return self.frames["frente"][0]


class Assets:
    def __init__(self):
        self._fonts = {}
        self._text_cache = {}
        self.sounds = {}
        self.sprites = {}
        self.backgrounds = {}
        self.wall_textures = {}
        self._qr = {}
        self._music = None

    # ── carga ────────────────────────────────
    def load_steps(self):
        """Carrega tudo aos poucos; cada passo devolve o progresso (0..1)."""
        steps = [self._load_sounds, self._load_tiles, self._load_weapons]
        steps += [(lambda c=c: self._load_character(c)) for c in CHARACTERS]
        for i, step in enumerate(steps):
            step()
            yield (i + 1) / len(steps)

    def load(self):
        for _ in self.load_steps():
            pass

    def _load_sounds(self):
        if pygame.mixer.get_init() is None:
            try:
                pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
            except pygame.error:
                return
        for path in config.SOUNDS_DIR.glob("*.wav"):
            try:
                self.sounds[path.stem] = pygame.mixer.Sound(str(path))
            except pygame.error:
                pass

    def _load_character(self, stats):
        pattern = re.compile(rf"^{re.escape(stats.sprite)}(\d*)({'|'.join(DIRECTIONS)})\.png$")
        found = {d: [] for d in DIRECTIONS}
        for path in config.CHAR_DIR.glob(f"{stats.sprite}*.png"):
            m = pattern.match(path.name)
            if not m:
                continue
            try:
                img = pygame.image.load(str(path)).convert_alpha()
            except pygame.error:
                continue
            found[m.group(2)].append((int(m.group(1) or 0), img))
        if all(found.values()):
            raw = {d: [img for _, img in sorted(found[d], key=lambda t: t[0])] for d in DIRECTIONS}
            self.sprites[stats.key] = SpriteSet(_normalize(raw))
        else:
            self.sprites[stats.key] = SpriteSet(_placeholder(stats.color))

    def _load_weapons(self):
        from . import weapon_art
        weapon_art.load()

    def _load_tiles(self):
        if not config.TILES_DIR.is_dir():
            return
        for folder in config.TILES_DIR.iterdir():
            if not folder.is_dir():
                continue
            textures = {}
            for path in folder.glob("*.png"):
                try:
                    if path.stem.startswith("fundo"):
                        self.backgrounds[folder.name] = pygame.image.load(str(path)).convert()
                    else:
                        img = pygame.image.load(str(path)).convert_alpha()
                        textures[img.get_size()] = img
                except pygame.error:
                    pass
            self.wall_textures[folder.name] = textures

    # ── texto ────────────────────────────────
    def font(self, size):
        if size not in self._fonts:
            try:
                self._fonts[size] = pygame.font.Font(str(config.FONT_PATH), size)
                self._pixel_font = True
            except (OSError, pygame.error):
                self._fonts[size] = pygame.font.Font(None, int(size * 1.6))
                self._pixel_font = False
        return self._fonts[size]

    def text(self, text, size, color):
        key = (text, size, tuple(color))
        surf = self._text_cache.get(key)
        if surf is None:
            if len(self._text_cache) > 600:
                self._text_cache.clear()
            surf = self._render(text, size, color)
            self._text_cache[key] = surf
        return surf

    def _render(self, text, size, color):
        """A fonte pixel desenha maiúsculas acentuadas como minúsculas; aqui o acento
        é desenhado à mão sobre a letra maiúscula sem acento."""
        font = self.font(size)
        if not getattr(self, "_pixel_font", False):
            return font.render(text, False, color)
        marks, plain = [], []
        for i, ch in enumerate(text):
            mark = _UPPER_ACCENTS.get(ch)
            if mark:
                plain.append(mark[0])
                marks.append((i, mark[1]))
            else:
                plain.append(ch)
        glyphs = font.render("".join(plain), False, color)
        pad = max(2, size // 4)
        surf = pygame.Surface((glyphs.get_width(), glyphs.get_height() + pad), pygame.SRCALPHA)
        surf.blit(glyphs, (0, pad))
        u = max(1, size // 8)
        for i, mark in marks:
            for ux, uy in _ACCENT_PIXELS[mark]:
                surf.fill(color, (i * size + ux * u, pad + uy * u, u, u))
        return surf

    def text_width(self, text, size):
        return self.font(size).size(text)[0]

    # ── som ──────────────────────────────────
    def play(self, name, volume=0.5):
        sound = self.sounds.get(name)
        if sound:
            sound.set_volume(volume)
            sound.play()

    def music(self, name):
        if name == self._music or pygame.mixer.get_init() is None:
            return
        path = {"menu": config.SOUNDS_DIR / "bgm.wav",
                "battle": config.SOUNDS_DIR / "battle_bgm.mp3"}.get(name)
        self._music = name
        try:
            if path is None or not path.is_file():
                pygame.mixer.music.fadeout(600)
                return
            pygame.mixer.music.load(str(path))
            pygame.mixer.music.set_volume(0.3)
            pygame.mixer.music.play(-1, fade_ms=600)
        except pygame.error:
            pass

    def stop_music(self, fade_ms=1200):
        self._music = None
        if pygame.mixer.get_init():
            pygame.mixer.music.fadeout(fade_ms)

    # ── QR code ──────────────────────────────
    def qr(self, url, module=4, dark=(13, 11, 18), light=(234, 226, 206)):
        key = (url, module)
        if key not in self._qr:
            try:
                import qrcode
            except ImportError:
                self._qr[key] = None
                return None
            qr = qrcode.QRCode(border=2, box_size=1)
            qr.add_data(url)
            qr.make(fit=True)
            matrix = qr.get_matrix()
            n = len(matrix)
            surf = pygame.Surface((n * module, n * module))
            surf.fill(light)
            for y, row in enumerate(matrix):
                for x, on in enumerate(row):
                    if on:
                        surf.fill(dark, (x * module, y * module, module, module))
            self._qr[key] = surf
        return self._qr[key]

    def portrait_pngs(self):
        """PNG do retrato de cada personagem, servido ao celular."""
        result = {}
        for i, stats in enumerate(CHARACTERS):
            buf = io.BytesIO()
            pygame.image.save(self.sprites[stats.key].portrait, buf, "retrato.png")
            result[i] = buf.getvalue()
        return result


_ACCENT_PIXELS = {
    "acute": ((4, -2), (3, -1)),
    "grave": ((2, -2), (3, -1)),
    "circ": ((3, -2), (2, -1), (4, -1)),
    "tilde": ((2, -2), (3, -2), (6, -2), (1, -1), (4, -1), (5, -1)),
}
_MARK_NAMES = {"́": "acute", "̀": "grave", "̂": "circ", "̃": "tilde"}
_UPPER_ACCENTS = {}
for _ch in "ÁÀÂÃÉÊÍÓÔÕÚ":
    _base, _mark = unicodedata.normalize("NFD", _ch)
    _UPPER_ACCENTS[_ch] = (_base, _MARK_NAMES[_mark])


def window_icon(size=32):
    """Ícone da janela/executável: cabeça do Guerreiro sobre fundo escuro."""
    surf = pygame.Surface((size, size), pygame.SRCALPHA)
    pygame.draw.rect(surf, (22, 19, 30), surf.get_rect(), border_radius=size // 6)
    path = config.CHAR_DIR / "guerreirofrente.png"
    try:
        img = pygame.image.load(str(path))
    except (pygame.error, FileNotFoundError):
        return surf
    box = img.get_bounding_rect()
    head = img.subsurface((box.x, box.y, box.w, int(box.h * 0.6)))
    scale = size * 0.86 / max(head.get_size())
    head = pygame.transform.smoothscale(head, (round(head.get_width() * scale), round(head.get_height() * scale)))
    surf.blit(head, head.get_rect(center=(size // 2, size // 2 + size // 20)))
    return surf


def _normalize(raw):
    """Recorta as margens e coloca todos os quadros na mesma escala, sem distorcer."""
    cropped = {d: [img.subsurface(img.get_bounding_rect()).copy() for img in frames]
               for d, frames in raw.items()}
    tallest = max(img.get_height() for frames in cropped.values() for img in frames)
    if tallest <= config.SPRITE_HEIGHT:
        factor = max(1, round(config.SPRITE_HEIGHT / tallest))   # pixel art pequena: escala inteira
        smooth = False
    else:
        factor = config.SPRITE_HEIGHT / tallest
        smooth = True
    out = {}
    for d, frames in cropped.items():
        out[d] = []
        for img in frames:
            size = (max(1, round(img.get_width() * factor)), max(1, round(img.get_height() * factor)))
            scaled = pygame.transform.smoothscale(img, size) if smooth else pygame.transform.scale(img, size)
            out[d].append(scaled)
    return out


def _placeholder(color):
    surf = pygame.Surface((30, 48), pygame.SRCALPHA)
    pygame.draw.ellipse(surf, color, (3, 16, 24, 30))
    pygame.draw.circle(surf, color, (15, 11), 10)
    return {d: [surf] for d in DIRECTIONS}
