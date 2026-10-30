"""Carregamento de recursos: fontes, sons, sprites, texturas e QR codes."""
import io
import json
import re
import unicodedata

import pygame

from . import config, settings
from .data import CHARACTERS, SHADOW_CHARACTERS

DIRECTIONS = ("frente", "costas", "direita", "esquerda")
# folha de sprite (tools/gerar_sprites.py): uma linha por direção, colunas nesta ordem
SHEET_DIRECTIONS = DIRECTIONS
SHEET_POSES = (("andar", 8), ("parado", 2), ("ataque", 3), ("dano", 1), ("esquiva", 1))
# poses do esporte (só os heróis): pular, arremessar, enterrar, dar toco, chutar, carrinho e comemorar.
# Uma pose que a folha não tiver cai no quadro parado (SpriteSet.pose).
SPORT_POSES = (("pulo", 2), ("arremesso", 3), ("enterrada", 3), ("toco", 2), ("chute", 3), ("carrinho", 1),
               ("comemora", 2), ("bate", 4), ("espera", 2), ("mergulho", 2))
SHEET_FACTOR = 2                 # a arte é ampliada 2x sem suavizar
TEAM_KITS = ("azul", "vermelho")  # uniforme do time 0 e do time 1 no futebol (characters/uniformes)
MUSIC_VOLUME = 0.3               # música com o volume das opções no máximo
MAX_SAME_SOUND = 3               # o mesmo efeito tocando junto no máximo (rajadas não viram parede de ruído)
MUSIC_FILES = {"menu": "bgm.ogg", "battle": "battle_bgm.mp3", "camp": "camp_bgm.ogg", "boss": "boss_bgm.ogg", "boss_lag": "boss_lag_bgm.ogg"}


class SpriteSet:
    """Quadros de um personagem nas quatro direções, separados por pose:
    andar, parado, ataque, dano e esquiva (folhas novas) ou só andar (arte antiga)."""

    def __init__(self, frames=None, poses=None, hands=None, glow=()):
        if poses is None:
            poses = {d: {"andar": list(imgs)} for d, imgs in frames.items()}
        self.poses = poses                       # {direção: {pose: [Surface, ...]}}
        self.frames = {d: kinds["andar"] for d, kinds in poses.items()}
        self.hands = hands                       # {direção: {pose: [(dx, dy), ...]}} ou None
        self.glow = tuple(glow)                  # cores dos olhos (acendem na alma corrompida)
        self._flash = {}
        self.cache = {}                          # imagens derivadas prontas (ex.: caído no chão)

    @property
    def walk_len(self):
        return len(self.frames["frente"])

    def frame(self, direction, index):
        """Quadro da caminhada (o índice dá a volta)."""
        frames = self.frames.get(direction) or self.frames["frente"]
        return frames[index % len(frames)]

    def pose(self, direction, kind, index=0):
        if kind == "andar":
            return self.frame(direction, index)
        frames = (self.poses.get(direction) or self.poses["frente"]).get(kind)
        if not frames:
            parado = (self.poses.get(direction) or self.poses["frente"]).get("parado")
            return parado[0] if parado else self.frame(direction, 0)
        return frames[min(index, len(frames) - 1)]

    def hand(self, direction, kind, index):
        """Onde fica a mão que segura a arma, em pixels de tela a partir do meio de baixo
        do sprite (None na arte antiga, que não tem essa informação)."""
        if self.hands is None:
            return None
        spots = self.hands.get(direction, {}).get(kind) or self.hands.get(direction, {}).get("andar")
        if not spots:
            return None
        return spots[index % len(spots)] if kind == "andar" else spots[min(index, len(spots) - 1)]

    def flash(self, direction, index, kind="andar"):
        """Silhueta branca do quadro (usada quando o personagem leva dano)."""
        key = (direction, kind, index)
        if key not in self._flash:
            img = self.pose(direction, kind, index)
            mask = pygame.mask.from_surface(img)
            self._flash[key] = mask.to_surface(setcolor=(255, 255, 255, 255), unsetcolor=(0, 0, 0, 0))
        return self._flash[key]

    @property
    def portrait(self):
        return self.pose("frente", "parado", 0)


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
        self.music_paused = False      # pausa do jogo: música muda

    # ── carga ────────────────────────────────
    def load_steps(self):
        """Carrega tudo aos poucos; cada passo devolve o progresso (0..1)."""
        from .enemies import CREATURES
        steps = [self._load_sounds, self._load_tiles, self._load_weapons]
        steps += [(lambda c=c: self._load_character(c)) for c in CHARACTERS]
        # criaturas da campanha: mesma escala de pixel dos heróis (o diabrete fica menor, o golem maior)
        steps += [(lambda c=c: self._load_character(c, factor=2)) for c in CREATURES.values()]
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

    def shadow_sprites(self, key):
        """Sprites da alma corrompida de um herói (gerados na primeira vez que alguém pede)."""
        name = "sombra:" + key
        if name not in self.sprites:
            from .enemies import SHADOW_TINT, TINTS, tint_sprites
            if key not in self.sprites:                               # borba_exo não é personagem: lê a folha
                self.sprites[key] = load_sheet(key)
            self.sprites[name] = tint_sprites(self.sprites[key], TINTS.get(key, SHADOW_TINT))
        return self.sprites[name]

    def kit_sprites(self, key, team):
        """Sprites do herói com o uniforme do time (futebol). Carregados na primeira vez que
        alguém pede; sem a folha do uniforme (ex.: Aryel Corrompido), ficam os de sempre."""
        name = f"uniforme:{TEAM_KITS[team]}:{key}"
        if name not in self.sprites:
            stats = next((c for c in CHARACTERS if c.key == key), None)
            sheet = None
            if stats is not None and key not in SHADOW_CHARACTERS:
                kit = config.CHAR_DIR / "uniformes" / f"{stats.sprite}_{TEAM_KITS[team]}.png"
                sheet = load_sheet(stats.sprite, image=kit)
            self.sprites[name] = sheet or self.sprites[key]
        return self.sprites[name]

    def exo_sprites(self, fighter):
        """Sprites do Borba Jr de exoesqueleto (com o uniforme do time no futebol). None se não houver."""
        kit = getattr(fighter, "kit", None)
        suffix = f"_{TEAM_KITS[kit]}" if kit is not None else ""
        name = f"exo{suffix}:{fighter.stats.key}"
        if name not in self.sprites:
            base = f"{fighter.stats.sprite}_exo"
            folder = config.CHAR_DIR / "uniformes" if kit is not None else config.CHAR_DIR
            self.sprites[name] = load_sheet(base, image=folder / f"{base}{suffix}.png")
        return self.sprites[name]

    def _load_character(self, stats, factor=None):
        if stats.key in SHADOW_CHARACTERS:
            self.sprites[stats.key] = self.shadow_sprites(stats.sprite)
            return
        sheet = load_sheet(stats.sprite)
        if sheet is not None:
            self.sprites[stats.key] = sheet
            return
        # arte antiga: um PNG por quadro (<nome>[n]<direção>.png)
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
            self.sprites[stats.key] = SpriteSet(_normalize(raw, factor))
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
        if sound and sound.get_num_channels() < MAX_SAME_SOUND:
            sound.set_volume(volume * settings.sfx_volume())
            sound.play()

    def music(self, name):
        if name == self._music or pygame.mixer.get_init() is None:
            return
        path = config.SOUNDS_DIR / MUSIC_FILES[name] if name in MUSIC_FILES else None
        self._music = name
        try:
            if path is None or not path.is_file():
                pygame.mixer.music.fadeout(600)
                return
            pygame.mixer.music.load(str(path))
            self.music_paused = False
            pygame.mixer.music.set_volume(MUSIC_VOLUME * settings.music_volume())
            pygame.mixer.music.play(-1, fade_ms=600)
        except pygame.error:
            pass

    def apply_music_volume(self):
        """Volume da música mudou nas opções: vale já, sem recomeçar a faixa."""
        if pygame.mixer.get_init():
            volume = 0.0 if self.music_paused else MUSIC_VOLUME * settings.music_volume()
            pygame.mixer.music.set_volume(volume)

    def pause_music(self, paused):
        """Pausa: a música fica muda (sem parar a faixa).

        Não usa music.pause()/unpause(): no pygame 2.6 eles seguram o GIL enquanto esperam o
        áudio, e se um efeito terminar no mesmo instante o jogo trava para sempre.
        """
        self.music_paused = paused
        self.apply_music_volume()

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


def load_sheet(name, image=None):
    """Folha de sprite gerada por tools/gerar_sprites.py (<nome>.png + <nome>.json), ou None.
    ``image`` troca só a imagem (o uniforme usa o mesmo .json do personagem)."""
    png, meta = image or config.CHAR_DIR / f"{name}.png", config.CHAR_DIR / f"{name}.json"
    if not (png.is_file() and meta.is_file()):
        return None
    try:
        info = json.loads(meta.read_text(encoding="utf-8"))
        sheet = pygame.image.load(str(png))
    except (OSError, ValueError, pygame.error):
        return None
    if pygame.display.get_surface() is not None:
        sheet = sheet.convert_alpha()
    cw, ch = info["cell"]
    poses = [(kind, n) for kind, n in info["poses"]]
    if sheet.get_width() < cw * sum(n for _, n in poses) or sheet.get_height() < ch * len(SHEET_DIRECTIONS):
        return None
    f = SHEET_FACTOR
    frames, hands = {}, {}
    for row, direction in enumerate(SHEET_DIRECTIONS):
        frames[direction], col = {}, 0
        for kind, n in poses:
            cells = []
            for i in range(n):
                cell = sheet.subsurface((col * cw, row * ch, cw, ch))
                cells.append(pygame.transform.scale(cell, (cw * f, ch * f)))
                col += 1
            frames[direction][kind] = cells
    raw_hands = info.get("hand", {})
    for direction in SHEET_DIRECTIONS:
        source = raw_hands.get("direita" if direction == "esquerda" else direction)
        if not source:
            continue
        mirror = -1 if direction == "esquerda" else 1
        spots = [(mirror * (x - cw / 2) * f, (y - ch) * f) for x, y in source]
        hands[direction], col = {}, 0
        for kind, n in poses:
            hands[direction][kind] = spots[col:col + n]
            col += n
    return SpriteSet(poses=frames, hands=hands or None, glow=[tuple(c) for c in info.get("eyes", ())])


def window_icon(size=32):
    """Ícone da janela/executável: cabeça do Guerreiro sobre fundo escuro."""
    surf = pygame.Surface((size, size), pygame.SRCALPHA)
    pygame.draw.rect(surf, (22, 19, 30), surf.get_rect(), border_radius=size // 6)
    sprites = load_sheet("guerreiro")
    if sprites is None:
        return surf
    img = sprites.portrait
    top = img.get_bounding_rect().y
    cx = img.get_width() // 2
    head = img.subsurface((cx - 16, top, 32, min(32, img.get_height() - top)))
    k = max(1, size // max(head.get_size()))           # ampliação inteira: pixel art sem borrar
    head = pygame.transform.scale(head, (head.get_width() * k, head.get_height() * k))
    surf.blit(head, head.get_rect(center=(size // 2, size // 2 + size // 20)))
    return surf


def _normalize(raw, factor=None):
    """Recorta as margens e coloca todos os quadros na mesma escala, sem distorcer.
    factor: ampliação fixa (criaturas de tamanhos diferentes); sem ele, todos ficam da mesma altura."""
    cropped = {d: [img.subsurface(img.get_bounding_rect()).copy() for img in frames]
               for d, frames in raw.items()}
    tallest = max(img.get_height() for frames in cropped.values() for img in frames)
    if factor is None and tallest > config.SPRITE_HEIGHT:
        # arte desenhada à mão: alguns quadros foram desenhados num tamanho um pouco diferente
        # (o personagem "pulava" ao andar); cada quadro fica da altura do maior daquela direção
        for d, frames in cropped.items():
            top = max(img.get_height() for img in frames)
            cropped[d] = [img if img.get_height() >= top * 0.97 else
                          pygame.transform.smoothscale(img, (round(img.get_width() * top / img.get_height()), top))
                          for img in frames]
    if factor is not None:
        smooth = False
    elif tallest <= config.SPRITE_HEIGHT:
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
