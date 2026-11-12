"""Gera a trilha do jogo: partitura em código, tocada por instrumentos de verdade.

Uso:  python tools/gerar_trilha.py            (todas as faixas)
      python tools/gerar_trilha.py menu       (só as faixas com esses nomes)

Precisa, só para gerar (o jogo não precisa de nada disso):
  - fluidsynth e um SoundFont General MIDI. No Linux Mint/Ubuntu: sudo apt install fluidsynth
    fluid-soundfont-gm (FluidR3_GM, licença MIT). Outro .sf2: variável SOULSTRIKE_SF2.
  - ffmpeg (para o .ogg) e os pacotes Python mido e numpy (pip install mido numpy).

Cada faixa é um Song: andamento, tom, compassos e partes (instrumento + notas). A faixa pode ter
camadas (layer 0 = base, 1 e 2 = o que a luta liga por cima). Cada camada vira um .ogg do mesmo
tamanho exato, para tocarem juntas em sincronia (soulstrike/som.py). O rabo do eco do fim volta
para o começo, então o loop emenda sem estalo. Vinhetas (stinger=True) não fazem loop.

Todas as faixas usam o TEMA DA ALMA: quatro notas (1, 5, 4, 3 menor) que voltam em cada lugar,
para o jogo soar como uma obra só. Tudo é determinístico (semente fixa).
"""
import os
import random
import shutil
import subprocess
import sys
import tempfile
import wave
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "assets" / "sounds"
RATE = 44100
TPB = 480                                   # ticks por tempo no MIDI
TAIL = 4.0                                  # segundos de eco renderizados depois do fim
STINGER_TAIL = 2.0                          # vinheta: eco curto e acaba
TARGET_RMS = 0.27                           # volume percebido parecido com o das músicas antigas (~-11 dB)
SF2_PLACES = ("/usr/share/sounds/sf2/FluidR3_GM.sf2", "/usr/share/soundfonts/FluidR3_GM.sf2",
              "/usr/share/sounds/sf2/default-GM.sf2")

# instrumentos General MIDI (número do programa)
PIANO, CELESTA, GLOCK, MUSIC_BOX, VIBES, MARIMBA, BELLS = 0, 8, 9, 10, 11, 12, 14
ORGAN, NYLON, STEEL, CLEAN_GTR, OVERDRIVE, DIST_GTR = 19, 24, 25, 27, 29, 30
ACOUSTIC_BASS, FINGER_BASS, SYNTH_BASS, SYNTH_BASS2 = 32, 33, 38, 39
STRINGS, SLOW_STRINGS, TREMOLO, PIZZICATO, HARP, TIMPANI = 48, 49, 44, 45, 46, 47
CHOIR, VOICE_OOH, SYNTH_VOICE, ORCH_HIT = 52, 53, 54, 55
TRUMPET, TROMBONE, TUBA, HORN, BRASS, SYNTH_BRASS = 56, 57, 58, 60, 61, 62
FLUTE, PAN_FLUTE, OBOE, CLARINET, BASSOON = 73, 75, 68, 71, 70
SAW_LEAD, SQUARE_LEAD, PAD_WARM, PAD_POLY, PAD_HALO, PAD_SWEEP, PAD_NEW_AGE = 81, 80, 89, 90, 94, 95, 88
FX_ATMOS, TAIKO, MELODIC_TOM, SYNTH_DRUM, REVERSE_CYMBAL = 99, 116, 117, 118, 119
# bateria (canal 10)
KICK, SNARE, CLAP, HAT, HAT_OPEN, CRASH, RIDE, TOM_LOW, TOM_MID, TOM_HIGH, TAMB, SHAKER = \
    36, 38, 39, 42, 46, 49, 51, 41, 45, 48, 54, 70

NOTE = {"C": 0, "C#": 1, "Db": 1, "D": 2, "D#": 3, "Eb": 3, "E": 4, "F": 5, "F#": 6, "Gb": 6, "G": 7,
        "G#": 8, "Ab": 8, "A": 9, "A#": 10, "Bb": 10, "B": 11}
SCALES = {"minor": (0, 2, 3, 5, 7, 8, 10), "major": (0, 2, 4, 5, 7, 9, 11),
          "harmonic": (0, 2, 3, 5, 7, 8, 11), "phrygian": (0, 1, 3, 5, 7, 8, 10), "dorian": (0, 2, 3, 5, 7, 9, 10)}
NUMERALS = {"i": 0, "ii": 1, "iii": 2, "iv": 3, "v": 4, "vi": 5, "vii": 6}
THEME = ((0, 2), (4, 1), (3, 1), (2, 4))     # tema da alma: (grau da escala, tempos)


# ── partitura ──────────────────────────────────────────────
class Part:
    def __init__(self, song, name, layer, program, vol, pan, reverb, chorus, drums):
        self.song, self.name, self.layer = song, name, layer
        self.program, self.vol, self.pan, self.reverb, self.chorus = program, vol, pan, reverb, chorus
        self.drums = drums
        self.notes = []                     # (início em tempos, duração em tempos, nota MIDI, força)

    def n(self, beat, dur, pitch, vel=90):
        if pitch is None:
            return
        jitter = self.song.rng.randint(-5, 5)
        self.notes.append((beat, dur, int(pitch), max(1, min(127, int(vel + jitter)))))


class Song:
    def __init__(self, name, bpm, bars, key="A", mode="minor", beats=4, stinger=False, layers=1, seed=7):
        self.name, self.bpm, self.bars, self.beats = name, bpm, bars, beats
        self.tonic = 48 + NOTE[key]          # tônica na oitava 3 (C3 = 48)
        self.mode, self.stinger, self.layers = mode, stinger, layers
        self.rng = random.Random(seed)
        self.parts = []

    def part(self, name, program, layer=0, vol=100, pan=64, reverb=70, chorus=20, drums=False):
        p = Part(self, name, layer, program, vol, pan, reverb, chorus, drums)
        self.parts.append(p)
        return p

    @property
    def length(self):
        return self.bars * self.beats      # em tempos

    # alturas
    def deg(self, d, octave=0, mode=None):
        """Grau da escala (0 = tônica; passa de 6 sobe oitava; negativo desce) em nota MIDI."""
        scale = SCALES[mode or self.mode]
        o, i = divmod(d, 7)
        return self.tonic + 12 * (o + octave) + scale[i]

    def chord(self, numeral, octave=0, size=3):
        """Acorde por algarismo romano (i, VI, iv, V...). V maiúsculo em tom menor = dominante maior."""
        key = numeral.lower().rstrip("o+7")
        root = NUMERALS[key]
        mode = "harmonic" if numeral.startswith("V") and not numeral.startswith("VI") and self.mode == "minor" else None
        notes = [self.deg(root + 2 * k, octave, mode) for k in range(size)]
        if numeral.endswith("7"):
            notes.append(self.deg(root + 6, octave, mode))
        return notes


def bars_of(song, bars):
    return range(song.bars) if bars is None else bars


def chord_at(prog, bar, per=1):
    return prog[(bar // per) % len(prog)]


# ── padrões ───────────────────────────────────────────────
def pad(part, prog, octave=0, vel=70, bars=None, per=1, size=3, spread=False):
    """Acordes segurados (cordas, coro, órgão, pad)."""
    s = part.song
    for bar in bars_of(s, bars):
        if bar % per:
            continue
        notes = s.chord(chord_at(prog, bar, per), octave, size)
        if spread:
            notes = [notes[0] - 12] + notes
        length = min(per, s.bars - bar) * s.beats
        for k in notes:
            part.n(bar * s.beats, length - 0.05, k, vel)


def steps(part, prog, rhythm, tones=(0,), octave=0, vel=90, accent=12, bars=None, per=1, step=0.25, gate=0.9):
    """Ostinato: `rhythm` em semicolcheias ('x' toca, 'X' com acento, '.' pausa); `tones` são as
    notas do acorde, em ciclo (0, 1, 2 = tônica, terça, quinta; +3 = oitava acima)."""
    s = part.song
    k = 0
    for bar in bars_of(s, bars):
        notes = s.chord(chord_at(prog, bar, per), octave, 3)
        notes = notes + [n + 12 for n in notes]
        for i, ch in enumerate(rhythm):
            if ch in "xX":
                pitch = notes[tones[k % len(tones)] % len(notes)]
                part.n(bar * s.beats + i * step, step * gate, pitch, vel + (accent if ch == "X" else 0))
                k += 1


def drums(part, pattern, bars=None, vel=95, step=0.25):
    """Bateria: {nota: 'x...X...'} com uma letra por semicolcheia."""
    s = part.song
    for bar in bars_of(s, bars):
        for pitch, line in pattern.items():
            for i, ch in enumerate(line):
                if ch in "xXo":
                    v = vel + 18 if ch == "X" else vel - 30 if ch == "o" else vel
                    part.n(bar * s.beats + i * step, step, pitch, v)


def melody(part, notes, octave=1, start=0, vel=96, repeat_until=None, mode=None, legato=0.95):
    """Melodia por grau: [(grau ou None, tempos), ...]. `repeat_until` repete até esse tempo."""
    s = part.song
    t = start
    end = repeat_until if repeat_until is not None else start + sum(d for _, d in notes)
    while t < end - 1e-6:
        for d, dur in notes:
            if t >= end - 1e-6:
                break
            if d is not None:
                part.n(t, dur * legato, s.deg(d, octave, mode), vel)
            t += dur


def hits(part, prog, beats=(0,), octave=-1, vel=100, bars=None, per=1, dur=1.0, tone=0):
    """Batidas na nota do acorde (tímpano, taiko, metais curtos)."""
    s = part.song
    for bar in bars_of(s, bars):
        pitch = s.chord(chord_at(prog, bar, per), octave)[tone]
        for b in beats:
            part.n(bar * s.beats + b, dur, pitch, vel)


def roll(part, pitch, start, beats, vel_from=40, vel_to=115, rate=8):
    """Rufo crescendo (tímpano, caixa)."""
    count = int(beats * rate)
    for i in range(count):
        part.n(start + i / rate, 1 / rate, pitch, vel_from + (vel_to - vel_from) * i / max(1, count - 1))


def arp(part, prog, octave=1, step=0.25, order=(0, 1, 2, 3, 2, 1), vel=70, bars=None, per=1, gate=0.8):
    steps(part, prog, "x" * int(part.song.beats / step), tones=order, octave=octave, vel=vel, accent=0,
          bars=bars, per=per, step=step, gate=gate)


def theme(part, start, octave=1, vel=100, answer=None, scale=1.0, mode=None):
    """Toca o tema da alma (e uma resposta opcional depois)."""
    notes = [(d, b * scale) for d, b in THEME] + [(d, b * scale) for d, b in (answer or ())]
    melody(part, notes, octave, start, vel, mode=mode)


# ── render ────────────────────────────────────────────────
def soundfont():
    env = os.environ.get("SOULSTRIKE_SF2")
    for path in ((env,) if env else ()) + SF2_PLACES:
        if path and Path(path).is_file():
            return path
    sys.exit("SoundFont não encontrado: instale fluid-soundfont-gm ou defina SOULSTRIKE_SF2")


def write_midi(song, layer, path):
    import mido
    mid = mido.MidiFile(type=1, ticks_per_beat=TPB)
    meta = mido.MidiTrack()
    meta.append(mido.MetaMessage("set_tempo", tempo=mido.bpm2tempo(song.bpm), time=0))
    mid.tracks.append(meta)
    free = [c for c in range(16) if c != 9]
    for part in [p for p in song.parts if p.layer == layer]:
        ch = 9 if part.drums else free.pop(0)
        events = []
        for beat, dur, pitch, vel in part.notes:
            on, off = round(beat * TPB), round((beat + dur) * TPB)
            events.append((on, 1, mido.Message("note_on", channel=ch, note=pitch, velocity=vel)))
            events.append((max(on + 1, off), 0, mido.Message("note_off", channel=ch, note=pitch, velocity=0)))
        events.sort(key=lambda e: (e[0], e[1]))
        track = mido.MidiTrack()
        head = [mido.Message("control_change", channel=ch, control=7, value=part.vol),
                mido.Message("control_change", channel=ch, control=10, value=part.pan),
                mido.Message("control_change", channel=ch, control=91, value=part.reverb),
                mido.Message("control_change", channel=ch, control=93, value=part.chorus)]
        if not part.drums:
            head.insert(0, mido.Message("program_change", channel=ch, program=part.program))
        for msg in head:
            track.append(msg.copy(time=0))
        now = 0
        for tick, _, msg in events:
            track.append(msg.copy(time=tick - now))
            now = tick
        end = round((song.length + TAIL * song.bpm / 60) * TPB)
        track.append(mido.MetaMessage("end_of_track", time=max(0, end - now)))
        mid.tracks.append(track)
    mid.save(str(path))


def render_wav(mid_path, wav_path, sf2):
    subprocess.run(["fluidsynth", "-ni", "-q", "-r", str(RATE), "-g", "0.5", "-o", "synth.reverb.active=1",
                    "-o", "synth.chorus.active=1", "-F", str(wav_path), sf2, str(mid_path)],
                   check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def read_wav(path):
    import numpy as np
    with wave.open(str(path)) as w:
        data = np.frombuffer(w.readframes(w.getnframes()), dtype="<i2").astype(np.float64) / 32768
        return data.reshape(-1, w.getnchannels())


def render(song, only_layers=None):
    """Devolve uma lista de arrays (amostras x 2), uma por camada, todas do mesmo tamanho."""
    import numpy as np
    sf2 = soundfont()
    loop = round(song.length * 60 / song.bpm * RATE)
    tail = round((STINGER_TAIL if song.stinger else TAIL) * RATE)
    out = []
    with tempfile.TemporaryDirectory() as tmp:
        for layer in range(song.layers):
            mid, wav_path = Path(tmp) / f"{layer}.mid", Path(tmp) / f"{layer}.wav"
            write_midi(song, layer, mid)
            render_wav(mid, wav_path, sf2)
            x = read_wav(wav_path)
            x = np.vstack([x, np.zeros((max(0, loop + tail - len(x)), 2))])[:loop + tail]
            if song.stinger:
                fade = round(0.4 * RATE)
                x[-fade:] *= np.linspace(1, 0, fade)[:, None]
            else:
                base, rest = x[:loop].copy(), x[loop:]
                base[:len(rest)] += rest[:loop]                 # eco do fim emenda no começo
                x = base
            out.append(x)
    # com camadas, a base sozinha já tem o volume certo (as de cima somam por cima, como reforço)
    ref = out[0] if len(out) > 1 else sum(out)
    rms = float(np.sqrt(np.mean(ref ** 2))) or 1.0
    gain = TARGET_RMS / rms * (0.75 if song.stinger else 1.0)
    # camadas de cima um pouco mais baixas: somam reforço sem dar um pulo de volume
    return [0.98 * np.tanh(x * gain * (1.0 if i == 0 else 0.75) / 0.98) for i, x in enumerate(out)]


def save(song, layers):
    """Camadas em .ogg: <nome>.ogg (uma camada) ou <nome>_1.ogg, _2.ogg... (com camadas)."""
    import numpy as np
    names = [song.name] if len(layers) == 1 else [f"{song.name}_{i + 1}" for i in range(len(layers))]
    for name, x in zip(names, layers):
        with tempfile.TemporaryDirectory() as tmp:
            wav_path = Path(tmp) / "x.wav"
            with wave.open(str(wav_path), "wb") as w:
                w.setnchannels(2)
                w.setsampwidth(2)
                w.setframerate(RATE)
                w.writeframes((np.clip(x, -1, 1) * 32767).astype("<i2").tobytes())
            subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(wav_path), "-c:a", "libvorbis",
                            "-q:a", "1.5" if not song.stinger else "3", "-map_metadata", "-1",
                            str(OUT / f"{name}.ogg")], check=True)
        print(f"{name}.ogg  {len(x) / RATE:.1f} s")


# ── as faixas ─────────────────────────────────────────────
def menu():
    """Menu e tela de título: hino épico, lento e grande (ré menor, 72 bpm)."""
    s = Song("trilha_menu", 72, 40, key="D")
    intro, main, calm, top = range(0, 8), range(8, 24), range(24, 32), range(32, 40)
    prog = ["i", "VI", "III", "VII"]
    peak = ["i", "VI", "iv", "V"]
    strings = s.part("cordas", STRINGS, vol=100, reverb=90)
    pad(strings, prog, -1, 62, bars=intro, spread=True)
    pad(strings, prog, 0, 78, bars=main, spread=True)
    pad(strings, peak, 0, 90, bars=top, spread=True)
    low = s.part("cordas graves", SLOW_STRINGS, vol=95, reverb=80)
    steps(low, prog, "X.x.x.x.X.x.x.x.", tones=(0, 0, 2, 0), octave=-2, vel=70, bars=main)
    steps(low, peak, "X.x.x.x.X.x.x.x.", tones=(0, 0, 2, 0), octave=-2, vel=82, bars=top)
    choir = s.part("coro", CHOIR, vol=96, reverb=110)
    pad(choir, prog, 0, 55, bars=range(4, 8))
    pad(choir, prog, 0, 75, bars=calm)
    pad(choir, peak, 1, 85, bars=top)
    horn = s.part("trompa", HORN, vol=105, reverb=90, pan=54)
    theme(horn, 0, octave=1, vel=72, answer=((0, 2), (4, 1), (5, 1), (4, 4)))
    brass = s.part("metais", BRASS, vol=108, reverb=85, pan=74)
    for b in (8, 16):
        theme(brass, b * 4, octave=1, vel=96, answer=((0, 2), (4, 1), (5, 1), (6, 2), (4, 2)))
        melody(brass, [(2, 2), (3, 2), (4, 4), (5, 2), (4, 2), (3, 2), (2, 2)], 1, b * 4 + 16, 92)
    for b in (32, 36):
        theme(brass, b * 4, octave=1, vel=110, answer=((7, 2), (6, 1), (5, 1), (4, 4)))
    piano = s.part("piano", PIANO, vol=90, reverb=95)
    arp(piano, prog, 1, step=0.5, order=(0, 1, 2, 4, 2, 1, 0, 2), vel=58, bars=calm)
    theme(piano, 0, octave=2, vel=50, scale=1.0)
    timp = s.part("tímpano", TIMPANI, vol=110, reverb=80)
    hits(timp, prog, (0, 2), -1, 100, bars=main)
    hits(timp, peak, (0, 1.5, 2, 3), -1, 108, bars=top)
    roll(timp, s.deg(0, -1), 30 * 4, 8, 30, 118)
    taiko = s.part("taiko", TAIKO, vol=105, reverb=70)
    hits(taiko, prog, (0, 2.5), -1, 100, bars=range(16, 24))
    hits(taiko, peak, (0, 0.75, 2, 2.5, 3.5), -1, 110, bars=top)
    synth = s.part("pad sintetizado", PAD_WARM, vol=80, reverb=100)
    pad(synth, prog, 0, 60, bars=range(0, 32))
    pad(synth, peak, 0, 70, bars=top)
    bass = s.part("baixo sintetizado", SYNTH_BASS, vol=80, reverb=30)
    steps(bass, prog, "x.x.x.x.x.x.x.x.", octave=-2, vel=78, accent=0, bars=range(16, 24), step=0.25)
    steps(bass, peak, "x.x.x.x.x.x.x.x.", octave=-2, vel=86, accent=0, bars=top, step=0.25)
    kit = s.part("bateria", 0, drums=True, vol=95, reverb=60)
    drums(kit, {KICK: "X.......x.......", CLAP: "........X......."}, bars=range(16, 24), vel=88)
    drums(kit, {KICK: "X.....x.X.......", SNARE: "........X.......", HAT: "x.x.x.x.x.x.x.x.",
                CRASH: "X..............."}, bars=range(32, 33), vel=96)
    drums(kit, {KICK: "X.....x.X.......", SNARE: "........X.......", HAT: "x.x.x.x.x.x.x.x."},
          bars=range(33, 40), vel=92)
    return s


def chefe_final():
    """Chefão final, Cauanzera e IARA: 3 camadas, uma por etapa da luta (dó menor, 150 bpm)."""
    s = Song("trilha_chefe_final", 150, 48, key="C", layers=3, seed=11)
    a = ["i", "i", "VI", "VI", "iv", "iv", "V", "V"]
    b = ["VI", "VII", "i", "i", "iv", "V", "i", "V"]
    A1, B1, A2, B2 = range(0, 16), range(16, 24), range(24, 40), range(40, 48)

    def both(fn, *args, **kw):
        for prog, bars in ((a, A1), (b, B1), (a, A2), (b, B2)):
            fn(*args[:1], prog, *args[1:], bars=bars, **kw)

    # camada 1 (base): cordas em ostinato, baixo sintetizado, bateria, tímpano e metais graves
    st = s.part("cordas ostinato", STRINGS, 0, vol=100, reverb=60)
    both(steps, st, "XxxxXxxxXxxxXxxx", tones=(0, 0, 3, 0, 2, 0, 3, 0), octave=0, vel=78, accent=14)
    bass = s.part("baixo sintetizado", SYNTH_BASS2, 0, vol=95, reverb=20)
    both(steps, bass, "X.xxX.x.X.xxX.xx", tones=(0,), octave=-2, vel=92, accent=10)
    kit = s.part("bateria", 0, 0, drums=True, vol=100, reverb=40)
    groove = {KICK: "X.....x.X.x.....", SNARE: "....X.......X...", HAT: "x.x.x.x.x.x.x.x."}
    drums(kit, groove, bars=range(0, 48), vel=96)
    drums(kit, {CRASH: "X..............."}, bars=range(0, 48, 8), vel=100)
    timp = s.part("tímpano", TIMPANI, 0, vol=112, reverb=70)
    both(hits, timp, (0, 1.5, 3), -1, 104)
    low = s.part("trombones", TROMBONE, 0, vol=104, reverb=70)
    both(hits, low, (0,), -1, 98, dur=1.5)
    synth = s.part("pad", PAD_SWEEP, 0, vol=70, reverb=90)
    both(pad, synth, 0, 64)
    # camada 2 (etapa 2): coro, taikos e o tema nos metais
    choir = s.part("coro", CHOIR, 1, vol=104, reverb=100)
    both(pad, choir, 0, 88, size=3)
    taiko = s.part("taiko", TAIKO, 1, vol=110, reverb=60)
    both(hits, taiko, (0, 0.75, 1.5, 2, 3, 3.5), -1, 108)
    brass = s.part("metais", BRASS, 1, vol=112, reverb=80)
    for bar in (0, 8, 24, 32):
        theme(brass, bar * 4, octave=1, vel=108, answer=((0, 2), (4, 1), (5, 1), (4, 4)), scale=1.0)
        melody(brass, [(5, 3), (4, 1), (3, 2), (2, 2), (1, 4), (4, 4)], 1, bar * 4 + 16, 104)
    for bar in (16, 40):
        melody(brass, [(5, 4), (6, 4), (7, 6), (6, 2), (5, 4), (4, 4), (3, 4), (4, 4)], 1, bar * 4, 110)
    # camada 3 (etapa 3 em diante): órgão, cordas agudas, arpejo de sintetizador e mais bateria
    organ = s.part("órgão", ORGAN, 2, vol=92, reverb=110)
    both(pad, organ, 0, 80, size=3, spread=True)
    hi = s.part("cordas agudas", STRINGS, 2, vol=98, reverb=80, pan=80)
    for bar in range(0, 48, 4):
        melody(hi, [(7, 1), (9, 1), (8, 1), (7, 1), (6, 2), (4, 2), (5, 1), (6, 1), (7, 2), (4, 4),
                    (None, 4)], 1, bar * 4, 84)
    lead = s.part("arpejo sintetizado", SAW_LEAD, 2, vol=70, reverb=60, pan=44)
    both(arp, lead, 1, step=0.25, order=(0, 1, 2, 3, 2, 1, 0, 1), vel=64)
    kit2 = s.part("bateria extra", 0, 2, drums=True, vol=96, reverb=40)
    drums(kit2, {HAT: "xxxxxxxxxxxxxxxx", TOM_LOW: "..............xx", KICK: "..x.......x....."},
          bars=range(0, 48), vel=72)
    return s


def vinheta_vitoria():
    s = Song("vinheta_vitoria", 120, 3, key="D", mode="major", stinger=True)
    brass = s.part("metais", BRASS, vol=115, reverb=90)
    melody(brass, [(0, 0.5), (4, 0.5), (3, 0.5), (4, 0.5), (7, 3)], 1, 0, 112)
    tr = s.part("trompete", TRUMPET, vol=105, reverb=90)
    melody(tr, [(None, 2), (9, 0.5), (8, 0.5), (9, 3)], 1, 0, 104)
    strings = s.part("cordas", STRINGS, vol=105, reverb=100)
    pad(strings, ["I"], 0, 96, bars=range(1, 3), per=2, spread=True)
    choir = s.part("coro", CHOIR, vol=96, reverb=110)
    pad(choir, ["I"], 1, 90, bars=range(1, 3), per=2)
    timp = s.part("tímpano", TIMPANI, vol=115, reverb=80)
    roll(timp, s.deg(0, -1), 0, 2, 50, 118)
    timp.n(4, 2, s.deg(0, -1), 124)
    kit = s.part("pratos", 0, drums=True, vol=100, reverb=90)
    kit.n(4, 2, CRASH, 118)
    return s


def vinheta_derrota():
    s = Song("vinheta_derrota", 66, 2, key="D", stinger=True)
    strings = s.part("cordas", SLOW_STRINGS, vol=105, reverb=110)
    melody(strings, [(4, 1), (3, 1), (2, 1), (1, 1), (0, 4)], 1, 0, 86)
    low = s.part("cordas graves", STRINGS, vol=98, reverb=110)
    pad(low, ["iv", "i"], -1, 76, bars=range(0, 2), spread=True)
    choir = s.part("coro", VOICE_OOH, vol=96, reverb=120)
    pad(choir, ["iv", "i"], 0, 70, bars=range(0, 2))
    piano = s.part("piano", PIANO, vol=90, reverb=110)
    piano.n(4, 4, s.deg(0, -2), 90)
    piano.n(4, 4, s.deg(0, -1), 80)
    return s


def vinheta_chefe():
    s = Song("vinheta_chefe", 100, 2, key="C", stinger=True)
    hit = s.part("golpe de orquestra", ORCH_HIT, vol=120, reverb=100)
    hit.n(0, 1, s.deg(0, 0), 124)
    hit.n(4, 1, s.deg(0, 0), 124)
    choir = s.part("coro", CHOIR, vol=110, reverb=120)
    for k, d in enumerate((0, 2, 4, 6)):
        choir.n(k * 0.5, 4 - k * 0.5, s.deg(d, 1), 70 + k * 12)
    taiko = s.part("taiko", TAIKO, vol=118, reverb=80)
    for b, v in ((0, 120), (1.5, 100), (2, 110), (3, 118), (3.5, 122), (4, 127)):
        taiko.n(b, 1, s.deg(0, -1), v)
    timp = s.part("tímpano", TIMPANI, vol=115, reverb=80)
    roll(timp, s.deg(0, -1), 1, 3, 40, 122)
    timp.n(4, 2, s.deg(0, -1), 127)
    brass = s.part("metais", TROMBONE, vol=112, reverb=90)
    brass.n(4, 3, s.deg(0, -1), 118)
    brass.n(4, 3, s.deg(4, -1), 112)
    return s


def vinheta_fase():
    """Troca de fase do chefão: metais crescendo e um golpe."""
    s = Song("vinheta_fase", 120, 2, key="C", stinger=True)
    brass = s.part("metais", BRASS, vol=115, reverb=90)
    for k in s.chord("V", 0) + [s.deg(4, 1)]:
        brass.n(0, 3.5, k, 70)
    for i in range(14):
        brass.n(i * 0.25, 0.25, s.deg(4, 0), 60 + i * 4)
    hit = s.part("golpe", ORCH_HIT, vol=120, reverb=100)
    hit.n(4, 1, s.deg(0, 0), 126)
    taiko = s.part("taiko", TAIKO, vol=118, reverb=80)
    for b in (3, 3.5, 3.75, 4):
        taiko.n(b, 1, s.deg(0, -1), 118)
    kit = s.part("pratos", 0, drums=True, vol=100, reverb=90)
    kit.n(4, 2, CRASH, 120)
    return s


# ── capítulos e chefões (etapa 3) ─────────────────────────
HARPSICHORD, WOOD_HI, WOOD_LO, COWBELL, RIM = 6, 76, 77, 56, 37


def over(sections, fn, part, *args, **kw):
    """Aplica um padrão em várias seções: [(progressão, compassos), ...]."""
    for prog, bars in sections:
        fn(part, prog, *args, bars=bars, **kw)


def waltz(part, prog, octave=0, vel=80, bars=None, accent=14):
    """Valsa (3 por compasso): baixo no 1, acorde no 2 e no 3."""
    s = part.song
    for bar in bars_of(s, bars):
        notes = s.chord(chord_at(prog, bar), octave)
        part.n(bar * s.beats, 0.9, notes[0] - 12, vel + accent)
        for b in (1, 2):
            for k in notes[1:]:
                part.n(bar * s.beats + b, 0.6, k, vel - 8)


def cap1():
    """Capítulo 1, Floresta e Calabouço: aventura sombria (mi menor, 100 bpm). Base = explorar, camada 2 = luta."""
    s = Song("trilha_cap1", 100, 32, key="E", layers=2, seed=21)
    a, b = ["i", "VI", "VII", "i"], ["iv", "VI", "III", "V"]
    sec = [(a, range(0, 16)), (b, range(16, 24)), (a, range(24, 32))]
    low = s.part("cordas graves", SLOW_STRINGS, vol=92, reverb=90)
    over(sec, pad, low, -1, 62, spread=True)
    harp = s.part("harpa", HARP, vol=88, reverb=90, pan=44)
    over(sec, arp, harp, 1, step=0.5, order=(0, 1, 2, 3, 4, 3, 2, 1), vel=60)
    flute = s.part("flauta", FLUTE, vol=96, reverb=100, pan=80)
    for bar in (0, 8, 24):
        theme(flute, bar * 4, octave=2, vel=78, answer=((0, 2), (4, 1), (5, 1), (4, 4)))
        melody(flute, [(2, 2), (1, 2), (0, 4), (None, 8)], 2, bar * 4 + 16, 74)
    melody(flute, [(3, 4), (4, 2), (5, 2), (4, 4), (2, 4), (3, 4), (4, 2), (6, 2), (4, 8)], 2, 16 * 4, 76)
    choir = s.part("coro baixo", VOICE_OOH, vol=86, reverb=110)
    over(sec, pad, choir, 0, 48)
    atmos = s.part("pad", PAD_HALO, vol=72, reverb=110)
    over(sec, pad, atmos, 0, 50)
    # luta
    st = s.part("cordas ostinato", STRINGS, 1, vol=100, reverb=70)
    over(sec, steps, st, "X.xxX.xxX.xxX.x.", tones=(0, 0, 2, 0), octave=0, vel=78)
    timp = s.part("tímpano", TIMPANI, 1, vol=110, reverb=80)
    over(sec, hits, timp, (0, 2, 2.5), -1, 100)
    taiko = s.part("taiko", TAIKO, 1, vol=104, reverb=70)
    over(sec, hits, taiko, (0, 1.5, 3), -1, 96)
    horn = s.part("trompas", HORN, 1, vol=106, reverb=90)
    for bar in (0, 8, 16, 24):
        theme(horn, bar * 4, octave=1, vel=100, answer=((0, 2), (4, 1), (5, 1), (6, 2), (4, 2)))
    kit = s.part("tambores", 0, 1, drums=True, vol=96, reverb=60)
    drums(kit, {KICK: "X.......X.x.....", TOM_LOW: "....x.......x..x", TAMB: "..x...x...x...x."}, vel=88)
    return s


def cap1_templo():
    """Templo Gelado: místico e frio (fá sustenido menor, 90 bpm), sinos de gelo."""
    s = Song("trilha_templo", 90, 32, key="F#", layers=2, seed=22)
    a, b = ["i", "iv", "VI", "V"], ["VI", "VII", "i", "i"]
    sec = [(a, range(0, 16)), (b, range(16, 24)), (a, range(24, 32))]
    cel = s.part("celesta", CELESTA, vol=92, reverb=115, pan=50)
    over(sec, arp, cel, 2, step=0.5, order=(0, 2, 1, 3, 2, 4, 3, 1), vel=62)
    choir = s.part("coro feminino", VOICE_OOH, vol=94, reverb=120)
    over(sec, pad, choir, 1, 60)
    strings = s.part("cordas", SLOW_STRINGS, vol=90, reverb=110)
    over(sec, pad, strings, -1, 58, spread=True)
    bells = s.part("sinos", BELLS, vol=84, reverb=120, pan=80)
    over(sec, hits, bells, (0,), 1, 70, dur=3)
    glock = s.part("glockenspiel", GLOCK, vol=86, reverb=115)
    for bar in (0, 16, 24):
        theme(glock, bar * 4, octave=2, vel=70, answer=((0, 4), (None, 4)))
    # luta
    trem = s.part("cordas tremolo", TREMOLO, 1, vol=100, reverb=90)
    over(sec, pad, trem, 0, 82, spread=True)
    timp = s.part("tímpano", TIMPANI, 1, vol=110, reverb=90)
    over(sec, hits, timp, (0, 1.5, 2, 3), -1, 98)
    brass = s.part("metais", BRASS, 1, vol=106, reverb=95)
    for bar in (0, 8, 16, 24):
        theme(brass, bar * 4, octave=1, vel=100, answer=((5, 2), (4, 2), (3, 2), (2, 2)))
    taiko = s.part("taiko", TAIKO, 1, vol=100, reverb=80)
    over(sec, hits, taiko, (0, 2.5, 3.5), -1, 96)
    return s


def cap2():
    """Capítulo 2, Lag Lobby: corporativo e tenso (si menor, 124 bpm), sintetizador e cordas."""
    s = Song("trilha_cap2", 124, 40, key="B", layers=2, seed=23)
    a, b = ["i", "i", "VI", "VII"], ["iv", "iv", "VI", "V"]
    sec = [(a, range(0, 16)), (b, range(16, 24)), (a, range(24, 40))]
    pad_ = s.part("pad", PAD_POLY, vol=80, reverb=90)
    over(sec, pad, pad_, 0, 60)
    bass = s.part("baixo pulsando", SYNTH_BASS, vol=90, reverb=20)
    over(sec, steps, bass, "x.x.x.x.x.x.x.x.", tones=(0,), octave=-2, vel=76, accent=0)
    seq = s.part("sequência", SQUARE_LEAD, vol=60, reverb=60, pan=40)
    over(sec, arp, seq, 1, step=0.25, order=(0, 2, 1, 3, 0, 2, 4, 2), vel=50)
    strings = s.part("cordas", STRINGS, vol=86, reverb=80)
    over(sec, pad, strings, 0, 56)
    kit = s.part("ritmo", 0, drums=True, vol=86, reverb=40)
    drums(kit, {HAT: "..x...x...x...x.", RIM: "....x.......x..."}, vel=70)
    # luta
    kit2 = s.part("bateria", 0, 1, drums=True, vol=100, reverb=40)
    drums(kit2, {KICK: "X...X...X...X...", SNARE: "....X.......X...", HAT: "xxxxxxxxxxxxxxxx"}, vel=94)
    drums(kit2, {CRASH: "X..............."}, bars=range(0, 40, 8), vel=96)
    lead = s.part("tema no sintetizador", SAW_LEAD, 1, vol=82, reverb=70, pan=80)
    for bar in (0, 8, 24, 32):
        theme(lead, bar * 4, octave=1, vel=92, answer=((0, 2), (4, 1), (5, 1), (4, 4)))
    st = s.part("cordas ostinato", STRINGS, 1, vol=96, reverb=60)
    over(sec, steps, st, "XxxxXxxxXxxxXxxx", tones=(0, 2, 3, 2), octave=0, vel=72)
    stab = s.part("metais curtos", SYNTH_BRASS, 1, vol=96, reverb=60)
    over(sec, hits, stab, (0, 0.75, 2.5), 0, 96, dur=0.4)
    return s


def cap3():
    """Capítulo 3, Clínica Clepalovers: estranho e limpo demais (sol menor, valsa a 108 bpm)."""
    s = Song("trilha_cap3", 108, 40, key="G", beats=3, layers=2, seed=24)
    a, b = ["i", "iv", "V", "i"], ["VI", "III", "iv", "V"]
    sec = [(a, range(0, 16)), (b, range(16, 24)), (a, range(24, 40))]
    box = s.part("caixinha de música", MUSIC_BOX, vol=96, reverb=110, pan=50)
    for bar in (0, 8, 24, 32):
        melody(box, [(0, 1), (4, 1), (3, 1), (2, 3), (4, 1), (5, 1), (4, 1), (7, 3), (6, 1), (5, 1), (4, 1),
                     (2, 3), (3, 2), (1, 1), (0, 3)], 2, bar * 3, 78)
    melody(box, [(5, 3), (4, 3), (2, 3), (4, 3), (3, 3), (2, 3), (1, 3), (4, 3)], 2, 16 * 3, 72)
    pizz = s.part("pizzicato", PIZZICATO, vol=92, reverb=80)
    over(sec, waltz, pizz, 0, 70)
    vib = s.part("vibrafone", VIBES, vol=80, reverb=110, pan=80)
    over(sec, pad, vib, 1, 46)
    cl = s.part("clarinete", CLARINET, vol=86, reverb=100)
    melody(cl, [(None, 6), (2, 3), (1, 3), (0, 6), (None, 6)] * 2, 1, 16 * 3, 66)
    kit = s.part("tique-taque", 0, drums=True, vol=80, reverb=70)
    drums(kit, {WOOD_HI: "x...x...x...", WOOD_LO: "x..........."}, vel=60)
    # luta
    st = s.part("cordas em valsa", STRINGS, 1, vol=100, reverb=80)
    over(sec, waltz, st, 0, 86)
    organ = s.part("órgão", ORGAN, 1, vol=86, reverb=110)
    over(sec, pad, organ, 0, 66)
    timp = s.part("tímpano", TIMPANI, 1, vol=108, reverb=80)
    over(sec, hits, timp, (0,), -1, 104)
    brass = s.part("metais", BRASS, 1, vol=104, reverb=90)
    for bar in (0, 16, 24):
        melody(brass, [(0, 2), (None, 1), (4, 1), (3, 1), (2, 1), (2, 3), (None, 3)], 1, bar * 3, 98)
    return s


def cap4():
    """Capítulo 4, Mansão do Carimbo: gótico e burocrático (lá menor, 112 bpm), órgão e cravo."""
    s = Song("trilha_cap4", 112, 32, key="A", layers=2, seed=25)
    a, b = ["i", "VII", "VI", "V"], ["iv", "i", "VI", "V"]
    sec = [(a, range(0, 16)), (b, range(16, 24)), (a, range(24, 32))]
    organ = s.part("órgão", ORGAN, vol=88, reverb=115)
    over(sec, pad, organ, 0, 64, spread=True)
    harpsi = s.part("cravo", HARPSICHORD, vol=90, reverb=80, pan=46)
    over(sec, arp, harpsi, 1, step=0.25, order=(0, 1, 2, 1, 3, 2, 1, 2), vel=62)
    choir = s.part("coro", CHOIR, vol=88, reverb=120)
    over(sec, pad, choir, 1, 52)
    clock = s.part("relógio", 0, drums=True, vol=84, reverb=70)
    drums(clock, {WOOD_HI: "x...x...x...x...", WOOD_LO: "..x.......x....."}, vel=58)
    bassoon = s.part("fagote", BASSOON, vol=90, reverb=90)
    for bar in (0, 8, 24):
        theme(bassoon, bar * 4, octave=0, vel=80, answer=((0, 2), (-1, 1), (-2, 1), (-3, 4)))
    # luta
    st = s.part("cordas ostinato", STRINGS, 1, vol=100, reverb=70)
    over(sec, steps, st, "XxxxXxxxXxxxXxxx", tones=(0, 2, 0, 3), octave=0, vel=76)
    taiko = s.part("taiko", TAIKO, 1, vol=106, reverb=70)
    over(sec, hits, taiko, (0, 0.75, 2, 3.5), -1, 100)
    brass = s.part("metais", BRASS, 1, vol=106, reverb=90)
    for bar in (0, 8, 16, 24):
        theme(brass, bar * 4, octave=1, vel=104, answer=((5, 2), (4, 1), (3, 1), (4, 4)))
    kit = s.part("bateria", 0, 1, drums=True, vol=94, reverb=50)
    drums(kit, {KICK: "X.....x.X.......", SNARE: "....X.......X...", COWBELL: "............x..."}, vel=88)
    bass = s.part("baixo", SYNTH_BASS2, 1, vol=88, reverb=20)
    over(sec, steps, bass, "X.x.X.x.X.x.X.xx", tones=(0,), octave=-2, vel=82, accent=8)
    return s


def chefe_templo():
    """Chefão do Templo (o cristal): épico clássico (mi menor, 140 bpm), 2 camadas."""
    s = Song("trilha_chefe_templo", 140, 32, key="E", layers=2, seed=31)
    a, b = ["i", "i", "VI", "VI", "iv", "iv", "V", "V"], ["VI", "VII", "i", "V"]
    sec = [(a, range(0, 16)), (b, range(16, 24)), (a, range(24, 32))]
    st = s.part("cordas ostinato", STRINGS, vol=100, reverb=70)
    over(sec, steps, st, "XxxxXxxxXxxxXxxx", tones=(0, 0, 3, 0, 2, 0, 3, 2), octave=0, vel=80)
    low = s.part("cordas graves", STRINGS, vol=96, reverb=70)
    over(sec, steps, low, "X.x.X.x.X.x.X.x.", tones=(0,), octave=-2, vel=84)
    timp = s.part("tímpano", TIMPANI, vol=112, reverb=80)
    over(sec, hits, timp, (0, 1.5, 3), -1, 104)
    tbn = s.part("trombones", TROMBONE, vol=104, reverb=80)
    over(sec, hits, tbn, (0,), -1, 98, dur=1.5)
    choir = s.part("coro", CHOIR, vol=96, reverb=110)
    over(sec, pad, choir, 0, 70)
    kit = s.part("bateria", 0, drums=True, vol=94, reverb=50)
    drums(kit, {KICK: "X.....x.X.......", SNARE: "....X.......X...", HAT: "x.x.x.x.x.x.x.x."}, vel=90)
    # fúria
    horn = s.part("trompas", HORN, 1, vol=110, reverb=90)
    for bar in (0, 8, 24):
        theme(horn, bar * 4, octave=1, vel=108, answer=((0, 2), (4, 1), (5, 1), (4, 4)))
        melody(horn, [(5, 3), (4, 1), (3, 2), (2, 2), (1, 4), (4, 4)], 1, bar * 4 + 16, 104)
    melody(horn, [(5, 4), (6, 4), (7, 6), (6, 2), (5, 4), (4, 4), (3, 4), (4, 4)], 1, 16 * 4, 108)
    hi = s.part("coro agudo", CHOIR, 1, vol=100, reverb=110)
    over(sec, pad, hi, 1, 84)
    taiko = s.part("taiko", TAIKO, 1, vol=110, reverb=70)
    over(sec, hits, taiko, (0, 0.75, 1.5, 2, 3, 3.5), -1, 106)
    glock = s.part("sinos", GLOCK, 1, vol=86, reverb=110)
    over(sec, arp, glock, 2, step=0.5, order=(0, 2, 4, 2), vel=70)
    return s


def chefe_lag():
    """Borba Jr Corrompido: eletrônico pesado com orquestra (si menor, 160 bpm), 2 camadas."""
    s = Song("trilha_chefe_lag", 160, 32, key="B", layers=2, seed=32)
    a, b = ["i", "i", "VI", "VII"], ["iv", "V", "i", "V"]
    sec = [(a, range(0, 16)), (b, range(16, 24)), (a, range(24, 32))]
    bass = s.part("baixo sintetizado", SYNTH_BASS2, vol=96, reverb=20)
    over(sec, steps, bass, "XxxxXxxxXxxxXxxx", tones=(0, 0, 3, 0), octave=-2, vel=90)
    kit = s.part("bateria", 0, drums=True, vol=100, reverb=30)
    drums(kit, {KICK: "X...X...X...X...", CLAP: "....X.......X...", HAT: "x.xxx.xxx.xxx.xx"}, vel=96)
    drums(kit, {CRASH: "X..............."}, bars=range(0, 32, 8), vel=100)
    gtr = s.part("guitarra distorcida", DIST_GTR, vol=86, reverb=40)
    over(sec, steps, gtr, "X..x..x.X..x.x..", tones=(0,), octave=-1, vel=92)
    over(sec, steps, gtr, "X..x..x.X..x.x..", tones=(2,), octave=-1, vel=86)
    lead = s.part("arpejo", SAW_LEAD, vol=70, reverb=50, pan=40)
    over(sec, arp, lead, 1, step=0.25, order=(0, 1, 2, 3, 2, 1, 0, 2), vel=60)
    st = s.part("cordas", STRINGS, vol=90, reverb=70)
    over(sec, pad, st, 0, 70)
    # fúria
    brass = s.part("metais", BRASS, 1, vol=112, reverb=80)
    for bar in (0, 8, 16, 24):
        theme(brass, bar * 4, octave=1, vel=110, answer=((0, 2), (4, 1), (5, 1), (6, 2), (4, 2)))
    choir = s.part("coro", CHOIR, 1, vol=100, reverb=100)
    over(sec, pad, choir, 1, 84)
    taiko = s.part("taiko", TAIKO, 1, vol=110, reverb=60)
    over(sec, hits, taiko, (0, 0.5, 1.5, 2, 3, 3.5), -1, 106)
    stab = s.part("metais sintetizados", SYNTH_BRASS, 1, vol=96, reverb=50)
    over(sec, hits, stab, (0, 1.5, 3), 0, 100, dur=0.3)
    return s


def chefe_clinica():
    """Albeguinio Corrompido: valsa macabra (ré menor, 168 bpm em 3), 2 camadas."""
    s = Song("trilha_chefe_clinica", 168, 48, key="D", beats=3, layers=2, seed=33)
    a, b = ["i", "i", "iv", "iv", "V", "V", "i", "i"], ["VI", "VI", "III", "III", "iv", "iv", "V", "V"]
    sec = [(a, range(0, 16)), (b, range(16, 32)), (a, range(32, 48))]
    st = s.part("cordas em valsa", STRINGS, vol=100, reverb=80)
    over(sec, waltz, st, 0, 88)
    organ = s.part("órgão", ORGAN, vol=88, reverb=110)
    over(sec, pad, organ, 0, 70, spread=True)
    timp = s.part("tímpano", TIMPANI, vol=110, reverb=80)
    over(sec, hits, timp, (0,), -1, 106)
    pizz = s.part("pizzicato", PIZZICATO, vol=90, reverb=70)
    over(sec, arp, pizz, 1, step=1, order=(0, 2, 1), vel=74)
    kit = s.part("bateria", 0, drums=True, vol=90, reverb=50)
    drums(kit, {KICK: "X...........", SNARE: "....x...x..."}, vel=86)
    # fúria
    choir = s.part("coro", CHOIR, 1, vol=104, reverb=110)
    over(sec, pad, choir, 1, 86)
    brass = s.part("metais", BRASS, 1, vol=110, reverb=90)
    for bar in (0, 8, 32, 40):
        melody(brass, [(0, 3), (4, 2), (3, 1), (2, 6), (4, 3), (5, 2), (4, 1), (7, 6)], 1, bar * 3, 106)
    box = s.part("caixinha", MUSIC_BOX, 1, vol=96, reverb=110)
    over(sec, arp, box, 2, step=0.5, order=(0, 2, 4, 2, 1, 3), vel=76)
    taiko = s.part("taiko", TAIKO, 1, vol=108, reverb=70)
    over(sec, hits, taiko, (0, 2), -1, 102)
    return s


SONGS = [menu, chefe_final, cap1, cap1_templo, cap2, cap3, cap4, chefe_templo, chefe_lag, chefe_clinica, vinheta_vitoria, vinheta_derrota, vinheta_chefe, vinheta_fase]


def main(names=()):
    for tool in ("fluidsynth", "ffmpeg"):
        if not shutil.which(tool):
            sys.exit(f"{tool} não encontrado")
    for make in SONGS:
        song = make()
        if names and song.name not in names and make.__name__ not in names:
            continue
        save(song, render(song))


if __name__ == "__main__":
    main(sys.argv[1:])
