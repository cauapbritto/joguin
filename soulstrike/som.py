"""Motor de som: canais, lado esquerdo/direito, variações, prioridade, música em camadas e vinhetas.

Quem toca som continua chamando assets.play(nome, volume) e assets.music(nome); este módulo
cuida do resto:

- 32 canais. Os 3 primeiros ficam guardados para som importante (gol, vitória, apito, menu),
  que nunca some numa luta de 4; os 3 seguintes tocam as camadas da música.
- `at=` (x no mundo) põe o som do lado da tela onde ele aconteceu, usando o ouvido que a
  partida registra a cada quadro (Mixer.listen).
- Arquivos <nome>_v2.wav, <nome>_v3.wav... são versões do mesmo som: cada vez sai uma.
- Som grande (explosão, gol, vitória) abaixa a música um instante (DUCK).
- Música com camadas (MUSIC_LAYERS): a base e as camadas tocam juntas, em sincronia, e
  set_intensity(n) liga as camadas de cima aos poucos (fase 2 do chefão, vida baixa).
- Vinheta (stinger): trecho curto que toca por cima, com a música abaixada.
"""
import random
import re

import pygame

from . import config, settings

CHANNELS = 32
PRIORITY_CHANNELS = (0, 1, 2)          # guardados para som importante e vinhetas
LAYER_CHANNELS = (3, 4, 5)             # camadas da música (base + até 2 por cima)
RESERVED = 6
MUSIC_VOLUME = 0.3                     # música com o volume das opções no máximo
MAX_SAME_SOUND = 3                     # o mesmo efeito tocando junto no máximo (contando as versões)
PAN_FLOOR = 0.35                       # o lado de longe nunca fica mudo (som no canto ainda se ouve nos dois)
LAYER_FADE = 1 / 90                    # camada liga/desliga em 1,5 s
VARIANT = re.compile(r"^(.+)_v(\d+)$")

# som que passa na frente quando os canais acabam (e toca nos canais guardados)
PRIORITY = {"victory", "gameover", "gol_rede", "apito", "apito_longo", "alarme", "confirm", "cancel", "select",
            "click", "hover", "compra", "bau", "cravada", "buzina", "replay", "notificacao"}
PRIORITY_PREFIX = ("comemora_", "vinheta_")
# quanto a música abaixa (0..1) e por quantos quadros, quando o som toca
DUCK = {"explosion": (0.25, 24), "victory": (0.6, 150), "gameover": (0.6, 150), "gol_rede": (0.45, 90),
        "cravada": (0.4, 60), "ability": (0.2, 30), "carga": (0.2, 40), "alarme": (0.3, 60)}
DUCK_PREFIX = {"comemora_": (0.5, 90)}
DUCK_RELEASE = 1 / 30                  # a música volta em meio segundo depois do tempo do DUCK


def pan(at, ear):
    """Volume (esquerda, direita) para um som no x `at` do mundo, com a tela em `ear` = (x, largura)."""
    if at is None or ear is None:
        return 1.0, 1.0
    left, width = ear
    rel = min(1.0, max(0.0, (at - left) / max(1.0, width)))
    # meio da tela: igual nos dois lados; canto: o lado de longe cai até PAN_FLOOR
    right = min(1.0, PAN_FLOOR + (1 - PAN_FLOOR) * 2 * rel)
    left_v = min(1.0, PAN_FLOOR + (1 - PAN_FLOOR) * 2 * (1 - rel))
    return left_v, right


def is_priority(name):
    return name in PRIORITY or name.startswith(PRIORITY_PREFIX)


def duck_of(name):
    if name in DUCK:
        return DUCK[name]
    for prefix, value in DUCK_PREFIX.items():
        if name.startswith(prefix):
            return value
    return None


class Mixer:
    def __init__(self):
        self.sounds = {}          # nome -> Sound (o original)
        self.variants = {}        # nome -> [Sound, versões...]
        self.ear = None           # (x da tela no mundo, largura vista) da partida atual
        self.rng = random.Random()
        self.music_name = None
        self.paused = False
        self.duck = 0.0           # quanto a música está abaixada agora (0..1)
        self._duck_hold = 0       # quadros até a música começar a voltar
        self._duck_target = 0.0
        self._next_priority = 0
        # música em camadas
        self.layers = []          # [Sound, ...] tocando nos LAYER_CHANNELS
        self.layer_level = []     # volume atual de cada camada (0..1)
        self.intensity = 0        # camadas ligadas acima da base
        self._layer_fade = 0.0    # fade de entrada (0..1) e de saída
        self._layer_out = False

    # ── carga ────────────────────────────────
    @staticmethod
    def init():
        if pygame.mixer.get_init() is None:
            try:
                pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
            except pygame.error:
                return False
        pygame.mixer.set_num_channels(CHANNELS)
        pygame.mixer.set_reserved(RESERVED)
        return True

    def load(self, folder):
        if not self.init():
            return
        for path in sorted(folder.glob("*.wav")) + sorted(folder.glob("vinheta_*.ogg")):
            try:
                sound = pygame.mixer.Sound(str(path))
            except pygame.error:
                continue
            self.sounds[path.stem] = sound
        for name in list(self.sounds):
            m = VARIANT.match(name)
            if m and m.group(1) in self.sounds:
                self.variants.setdefault(m.group(1), [self.sounds[m.group(1)]]).append(self.sounds[name])

    def listen(self, left, width):
        """A partida diz onde está a tela no mundo: o som ganha lado a partir disso."""
        self.ear = (left, width)

    # ── efeitos ──────────────────────────────
    def pick(self, name):
        group = self.variants.get(name)
        if group:
            return self.rng.choice(group)
        return self.sounds.get(name)

    def playing(self, name):
        group = self.variants.get(name)
        if group:
            return sum(s.get_num_channels() for s in group)
        sound = self.sounds.get(name)
        return sound.get_num_channels() if sound else 0

    def play(self, name, volume=0.5, at=None):
        sound = self.pick(name)
        if sound is None or self.playing(name) >= MAX_SAME_SOUND:
            return None
        sound.set_volume(volume * settings.sfx_volume())
        channel = None
        if is_priority(name):
            channel = self._priority_channel()
            if channel is not None:
                channel.play(sound)
        if channel is None:
            channel = sound.play()
        if channel is not None:
            channel.set_volume(*pan(at, self.ear))
        ducking = duck_of(name)
        if ducking:
            self.duck_music(*ducking)
        return channel

    def _priority_channel(self):
        try:
            for i in PRIORITY_CHANNELS:
                ch = pygame.mixer.Channel(i)
                if not ch.get_busy():
                    return ch
            # todos ocupados: usa o mais antigo, em rodízio
            self._next_priority = (self._next_priority + 1) % len(PRIORITY_CHANNELS)
            return pygame.mixer.Channel(PRIORITY_CHANNELS[self._next_priority])
        except pygame.error:
            return None

    def stinger(self, name, volume=0.7):
        """Vinheta: toca por cima e abaixa a música pelo tempo dela."""
        sound = self.sounds.get(name)
        if sound is None:
            return None
        frames = max(30, round(sound.get_length() * config.FPS))
        self.duck_music(0.65, frames)
        sound.set_volume(volume * settings.music_volume())
        channel = self._priority_channel()
        if channel is not None:
            channel.play(sound)
            channel.set_volume(1.0, 1.0)
        return channel

    # ── música ───────────────────────────────
    def duck_music(self, depth, frames):
        if self._duck_hold <= 0:
            self._duck_target = 0.0
        self._duck_target = max(self._duck_target, depth)
        self._duck_hold = max(self._duck_hold, frames)
        self.duck = max(self.duck, self._duck_target)
        self.apply_volume()

    def calm(self):
        """Música de volta ao volume cheio na hora (sem esperar o fim do DUCK)."""
        self.duck = self._duck_target = 0.0
        self._duck_hold = 0
        self.apply_volume()

    def music_volume(self):
        if self.paused:
            return 0.0
        return MUSIC_VOLUME * settings.music_volume() * (1 - self.duck)

    def apply_volume(self):
        if pygame.mixer.get_init() is None:
            return
        volume = self.music_volume()
        pygame.mixer.music.set_volume(volume)
        self._apply_layers(volume)

    def _apply_layers(self, volume):
        fade = self._layer_fade
        for i, sound in enumerate(self.layers):
            try:
                pygame.mixer.Channel(LAYER_CHANNELS[i]).set_volume(volume * fade * self.layer_level[i])
            except (pygame.error, IndexError):
                pass

    def start_layers(self, files):
        """Toca a base e as camadas juntas (no mesmo quadro, para ficarem em sincronia)."""
        self.stop_layers(0)
        sounds = []
        for path in files[:len(LAYER_CHANNELS)]:
            try:
                sounds.append(pygame.mixer.Sound(str(path)))
            except pygame.error:
                return False
        if not sounds:
            return False
        self.layers = sounds
        self.layer_level = [1.0] + [0.0] * (len(sounds) - 1)
        self.intensity = 0
        self._layer_fade = 0.0
        self._layer_out = False
        for i, sound in enumerate(sounds):
            channel = pygame.mixer.Channel(LAYER_CHANNELS[i])
            channel.set_volume(0.0)
            channel.play(sound, loops=-1)
        self._apply_layers(self.music_volume())
        return True

    def stop_layers(self, fade_ms=1200):
        if not self.layers:
            return
        if fade_ms <= 0 or pygame.mixer.get_init() is None:
            for i in range(len(self.layers)):
                try:
                    pygame.mixer.Channel(LAYER_CHANNELS[i]).stop()
                except pygame.error:
                    pass
            self.layers = []
            self.layer_level = []
            self.intensity = 0
            return
        self._layer_out = True
        self._fade_step = 1000 / config.FPS / fade_ms

    def set_intensity(self, level):
        """Quantas camadas acima da base ficam ligadas (0 = só a base)."""
        self.intensity = max(0, min(level, len(self.layers) - 1)) if self.layers else max(0, level)

    def tick(self):
        """Uma vez por quadro: a música volta depois de abaixar e as camadas sobem/descem."""
        changed = False
        if self._duck_hold > 0:
            self._duck_hold -= 1
        elif self.duck > 0:
            self.duck = max(0.0, self.duck - DUCK_RELEASE)
            self._duck_target = 0.0
            changed = True
        if self.layers:
            if self._layer_out:
                self._layer_fade -= getattr(self, "_fade_step", LAYER_FADE)
                if self._layer_fade <= 0:
                    self.stop_layers(0)
                    return
                changed = True
            elif self._layer_fade < 1:
                self._layer_fade = min(1.0, self._layer_fade + LAYER_FADE * 2)
                changed = True
            for i in range(1, len(self.layer_level)):
                target = 1.0 if i <= self.intensity else 0.0
                level = self.layer_level[i]
                if level != target:
                    step = LAYER_FADE if target > level else LAYER_FADE / 2
                    self.layer_level[i] = min(target, level + step) if target > level else max(target, level - step)
                    changed = True
        if changed:
            self.apply_volume()
