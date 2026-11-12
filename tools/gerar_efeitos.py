"""Refaz os efeitos em camadas (impacto + corpo + cauda) e gera os sons de ambiente.

Uso:  python tools/gerar_efeitos.py        (precisa de numpy; o coro e os sinos usam o fluidsynth do
                                            tools/gerar_trilha.py; depois rode tools/gerar_variacoes.py)

Cada efeito da lista GROUPS ganha camadas por cima do som que já existe:
  - impacto (golpe, soco, chute): um "tum" grave e um estalo curto;
  - tiro: corpo grave curto e um eco;
  - explosão: estrondo grave longo, ronco e destroços caindo;
  - poder (SUPER, carga, alma, barreira): brilho uma oitava acima, eco longo e um coro;
  - baú e menu: sininho com uma nota do tema.
O volume de pico fica igual ao do som antigo. O arquivo camadas.json guarda a impressão digital
de cada som já refeito, então rodar de novo não empilha camada em cima de camada.

Os ambientes (ambiente_<lugar>.ogg) são fundos de 20 s em loop, bem baixinhos: vento no Templo,
grilos e folhas na Floresta, ar-condicionado na Lag Lobby, vapor e bipes na Clínica, relógio e
papel na Mansão e passarinhos no quintal da Casa.
"""
import hashlib
import json
import math
import subprocess
import sys
import tempfile
import wave
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import gerar_trilha as trilha  # noqa: E402

OUT = Path(__file__).resolve().parent.parent / "assets" / "sounds"
MANIFEST = OUT / "camadas.json"
RATE = 44100
rng = np.random.default_rng(5)

GROUPS = {
    "impacto": ("hit", "golpe", "soco_metal", "chute", "chute_forte", "toco", "passo_pesado"),
    "tiro": ("shoot", "shoot2", "plasma", "laser", "rajada", "tiro_forte", "arco", "gelo", "fogo", "eletrico",
             "magia", "barrier"),
    "explosao": ("explosion",),
    "poder": ("ability", "carga", "teletransporte"),
    "brilho": ("bau", "compra", "confirm", "select", "alma"),
}


# ── ferramentas ───────────────────────────────────────────
def read(name):
    with wave.open(str(OUT / f"{name}.wav")) as w:
        x = np.frombuffer(w.readframes(w.getnframes()), dtype="<i2").astype(np.float64) / 32768
        if w.getnchannels() == 2:
            x = x.reshape(-1, 2).mean(axis=1)
        return x


def write(name, x, peak):
    x = np.asarray(x, dtype=np.float64)
    top = float(np.abs(x).max()) or 1.0
    x = peak * np.tanh(x / top * 1.15) / math.tanh(1.15)
    with wave.open(str(OUT / f"{name}.wav"), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes((np.clip(x, -1, 1) * 32767).astype("<i2").tobytes())


def digest(name):
    return hashlib.sha1((OUT / f"{name}.wav").read_bytes()).hexdigest()


def t(seconds):
    return np.arange(int(seconds * RATE)) / RATE


def sweep(f0, f1, seconds, decay):
    tt = t(seconds)
    f = f0 * (f1 / f0) ** (tt / seconds)
    phase = 2 * np.pi * np.cumsum(f) / RATE
    return np.sin(phase) * np.exp(-tt * decay)


def lowpass(x, cutoff):
    """Filtro passa-baixa de um polo (bom para ronco e vento)."""
    a = math.exp(-2 * math.pi * cutoff / RATE)
    y = np.empty_like(x)
    acc = 0.0
    for i, v in enumerate(x):
        acc = (1 - a) * v + a * acc
        y[i] = acc
    return y


def noise(seconds):
    return rng.uniform(-1, 1, int(seconds * RATE))


def reverb(x, seconds, mix):
    """Eco: convolução com um rabo de ruído que cai exponencialmente."""
    ir = noise(seconds) * np.exp(-t(seconds) * (6.0 / seconds))
    ir = lowpass(ir, 5000)
    ir /= np.sqrt((ir ** 2).sum()) or 1.0
    n = len(x) + len(ir)
    size = 1 << (n - 1).bit_length()
    wet = np.fft.irfft(np.fft.rfft(x, size) * np.fft.rfft(ir, size), size)[:n]
    out = np.zeros(n)
    out[:len(x)] += x
    return out + wet * mix


def put(base, layer, at=0.0, gain=1.0):
    start = int(at * RATE)
    end = start + len(layer)
    if end > len(base):
        base = np.concatenate([base, np.zeros(end - len(base))])
    base[start:end] += layer * gain
    return base


def octave_up(x):
    return x[::2].copy()


def instrument(program, notes, seconds, drums=False):
    """Toca notas num instrumento do SoundFont (coro, sinos) e devolve mono."""
    song = trilha.Song("_fx", 120, max(1, math.ceil(seconds / 2)), stinger=True)
    part = song.part("fx", program, vol=110, reverb=80, drums=drums)
    for beat, dur, pitch, vel in notes:
        part.n(beat, dur, pitch, vel)
    sf2 = trilha.soundfont()
    with tempfile.TemporaryDirectory() as tmp:
        mid, wav_path = Path(tmp) / "fx.mid", Path(tmp) / "fx.wav"
        trilha.write_midi(song, 0, mid)
        trilha.render_wav(mid, wav_path, sf2)
        x = trilha.read_wav(wav_path).mean(axis=1)
    x = x[:int(seconds * RATE)]
    fade = min(len(x), int(0.15 * RATE))
    x[-fade:] *= np.linspace(1, 0, fade)
    return x / (np.abs(x).max() or 1.0)


# ── camadas por grupo ─────────────────────────────────────
def impacto(x):
    peak = np.abs(x).max()
    out = put(x.copy(), sweep(110, 45, 0.22, 18), 0.0, peak * 0.7)
    out = put(out, noise(0.012) * np.exp(-t(0.012) * 300), 0.0, peak * 0.5)
    return reverb(out, 0.25, 0.18)


def tiro(x):
    peak = np.abs(x).max()
    out = put(x.copy(), sweep(160, 70, 0.12, 30), 0.0, peak * 0.45)
    return reverb(out, 0.4, 0.22)


def explosao(x):
    peak = np.abs(x).max()
    out = put(x.copy(), sweep(70, 28, 1.2, 3.2), 0.0, peak * 0.9)
    out = put(out, lowpass(noise(1.4), 180) * np.exp(-t(1.4) * 2.6), 0.02, peak * 2.2)
    for _ in range(14):                                  # destroços caindo
        at = rng.uniform(0.25, 1.1)
        click = lowpass(noise(0.03), 2500) * np.exp(-t(0.03) * 120)
        out = put(out, click, at, peak * rng.uniform(0.08, 0.2))
    return reverb(out, 0.9, 0.25)


def poder(x):
    peak = np.abs(x).max()
    out = put(x.copy(), octave_up(x), 0.0, 0.3)
    length = max(0.6, len(x) / RATE)
    choir = instrument(trilha.CHOIR, [(0, length * 2, 62, 90), (0, length * 2, 69, 84), (0, length * 2, 74, 80)],
                       length + 0.3)
    out = put(out, choir, 0.0, peak * 0.35)
    return reverb(out, 1.1, 0.3)


def brilho(x):
    peak = np.abs(x).max()
    glock = instrument(trilha.GLOCK, [(0, 0.5, 86, 100)], 0.6)
    out = put(x.copy(), glock, 0.0, peak * 0.3)
    return reverb(out, 0.5, 0.18)


LAYERS = {"impacto": impacto, "tiro": tiro, "explosao": explosao, "poder": poder, "brilho": brilho}


def effects():
    done = json.loads(MANIFEST.read_text()) if MANIFEST.is_file() else {}
    for group, names in GROUPS.items():
        for name in names:
            if not (OUT / f"{name}.wav").is_file():
                print("sem", name)
                continue
            if done.get(name) == digest(name):
                continue                                  # já refeito: não empilha de novo
            x = read(name)
            write(name, LAYERS[group](x), float(np.abs(x).max()))
            done[name] = digest(name)
            print("camadas em", name)
    MANIFEST.write_text(json.dumps(done, indent=1, sort_keys=True) + "\n")


# ── ambientes ─────────────────────────────────────────────
AMBIENT_SECONDS = 20


def loopable(x):
    """Emenda o fim no começo com meio segundo de cruzamento."""
    fade = int(0.5 * RATE)
    head, tail = x[:fade], x[-fade:]
    ramp = np.linspace(0, 1, fade)
    x = x[:-fade].copy()
    x[:fade] = head * ramp + tail * (1 - ramp)
    return x


def chirp(f0, f1, seconds):
    return sweep(f0, f1, seconds, 6) * np.hanning(int(seconds * RATE))


def ambiente_templo():
    n = AMBIENT_SECONDS
    wind = lowpass(noise(n + 0.5), 400)
    gust = 0.6 + 0.4 * np.sin(2 * np.pi * t(n + 0.5) / 7.0)
    x = wind * gust
    for _ in range(6):                                   # sininhos de gelo
        bell = sweep(2600, 2550, 1.2, 3) * 0.08
        x = put(x, bell, rng.uniform(0, n - 1.5))
    return x


def ambiente_floresta():
    n = AMBIENT_SECONDS
    x = lowpass(noise(n + 0.5), 900) * 0.35
    for k in range(int(n * 3)):                          # grilos
        at = rng.uniform(0, n - 0.2)
        cri = np.sin(2 * np.pi * 4300 * t(0.08)) * np.abs(np.sin(2 * np.pi * 30 * t(0.08))) * 0.06
        x = put(x, cri, at)
    return x


def ambiente_escritorio():
    n = AMBIENT_SECONDS
    hum = np.sin(2 * np.pi * 60 * t(n + 0.5)) * 0.15 + np.sin(2 * np.pi * 120 * t(n + 0.5)) * 0.06
    air = lowpass(noise(n + 0.5), 1500) * 0.4
    x = hum + air
    for _ in range(5):                                   # teclado longe
        at = rng.uniform(0, n - 2)
        for k in range(rng.integers(4, 10)):
            x = put(x, lowpass(noise(0.015), 3000) * np.exp(-t(0.015) * 200) * 0.25, at + k * 0.11)
    return x


def ambiente_clinica():
    n = AMBIENT_SECONDS
    x = lowpass(noise(n + 0.5), 3000) * 0.18
    for at in np.arange(0.3, n - 0.3, 2.0):              # bipe de monitor
        x = put(x, np.sin(2 * np.pi * 1320 * t(0.09)) * np.hanning(int(0.09 * RATE)) * 0.12, at)
    for _ in range(3):                                   # vapor
        at = rng.uniform(0, n - 2.5)
        x = put(x, noise(2.0) * np.hanning(int(2.0 * RATE)) * 0.35, at)
    return x


def ambiente_mansao():
    n = AMBIENT_SECONDS
    x = lowpass(noise(n + 0.5), 250) * 0.4
    for k, at in enumerate(np.arange(0.0, n, 1.0)):      # relógio
        tick = lowpass(noise(0.02), 4000) * np.exp(-t(0.02) * 250) * (0.3 if k % 2 else 0.22)
        x = put(x, tick, at)
    for _ in range(4):                                   # papel
        at = rng.uniform(0, n - 1)
        x = put(x, lowpass(noise(0.5), 6000) * np.hanning(int(0.5 * RATE)) * 0.12, at)
    return x


def ambiente_quintal():
    n = AMBIENT_SECONDS
    x = lowpass(noise(n + 0.5), 700) * 0.25
    for _ in range(12):                                  # passarinhos
        at = rng.uniform(0, n - 1)
        f = rng.uniform(2800, 4200)
        for k in range(rng.integers(2, 5)):
            x = put(x, chirp(f, f * 1.25, 0.09) * 0.12, at + k * 0.13)
    return x


AMBIENTS = (ambiente_templo, ambiente_floresta, ambiente_escritorio, ambiente_clinica, ambiente_mansao,
            ambiente_quintal)


def ambients():
    global rng
    for k, make in enumerate(AMBIENTS):
        rng = np.random.default_rng(100 + k)             # cada ambiente com a sua semente (sai sempre igual)
        x = loopable(make())
        x = x / (np.abs(x).max() or 1.0) * 0.6
        with tempfile.TemporaryDirectory() as tmp:
            wav_path = Path(tmp) / "a.wav"
            with wave.open(str(wav_path), "wb") as w:
                w.setnchannels(1)
                w.setsampwidth(2)
                w.setframerate(RATE)
                w.writeframes((x * 32767).astype("<i2").tobytes())
            subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(wav_path), "-c:a", "libvorbis",
                            "-q:a", "1", "-map_metadata", "-1", "-fflags", "+bitexact", "-flags:a", "+bitexact", str(OUT / f"{make.__name__}.ogg")], check=True)
        print(make.__name__)


if __name__ == "__main__":
    effects()
    ambients()
