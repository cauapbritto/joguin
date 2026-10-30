"""Gera os efeitos sonoros novos e as músicas do acampamento e do chefão (síntese, sem samples).

Uso:  python tools/gerar_sons.py

Os efeitos saem em assets/sounds/<nome>.wav (mono, 44100 Hz, 16 bits, como os antigos). As
músicas saem em .ogg (precisa do ffmpeg instalado; sem ele ficam em .wav, bem maiores). Tudo é
determinístico (semente fixa): rodar de novo gera os mesmos arquivos.
"""
import math
import random
import shutil
import struct
import subprocess
import wave
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "assets" / "sounds"
RATE = 44100
TAU = math.tau


# ── ferramentas de síntese ─────────────────────────────────
def silence(seconds):
    return [0.0] * int(seconds * RATE)


def env(n, attack=0.005, decay=None, curve=3.0):
    """Envelope: sobe em `attack` segundos e cai exponencialmente até o fim."""
    a = max(1, int(attack * RATE))
    out = []
    for i in range(n):
        if i < a:
            out.append(i / a)
        else:
            t = (i - a) / max(1, n - a)
            out.append((1 - t) ** curve)
    return out


def tone(freq, seconds, wave_kind="sine", vol=1.0, slide=None, attack=0.005, curve=3.0, vibrato=0.0):
    """Nota com o volume caindo. `slide` = frequência no fim (glissando)."""
    n = int(seconds * RATE)
    e = env(n, attack, curve=curve)
    phase = 0.0
    out = []
    for i in range(n):
        t = i / n
        f = freq + (slide - freq) * t if slide else freq
        if vibrato:
            f *= 1 + vibrato * math.sin(TAU * 6 * i / RATE)
        phase += f / RATE
        p = phase % 1.0
        if wave_kind == "sine":
            s = math.sin(TAU * p)
        elif wave_kind == "square":
            s = 1.0 if p < 0.5 else -1.0
        elif wave_kind == "pulse":
            s = 1.0 if p < 0.25 else -1.0
        elif wave_kind == "triangle":
            s = 4 * abs(p - 0.5) - 1
        else:                                   # saw
            s = 2 * p - 1
        out.append(s * e[i] * vol)
    return out


def noise(seconds, vol=1.0, rng=None, attack=0.002, curve=3.0, lowpass=1.0):
    """Ruído branco filtrado (lowpass 0..1: 1 = sem filtro, perto de 0 = abafado)."""
    rng = rng or random.Random(1)
    n = int(seconds * RATE)
    e = env(n, attack, curve=curve)
    out, last = [], 0.0
    for i in range(n):
        last += (rng.uniform(-1, 1) - last) * lowpass
        out.append(last * e[i] * vol)
    return out


def sweep_noise(seconds, start, end, vol=1.0, rng=None, attack=0.01, curve=2.0):
    """Ruído cujo filtro abre ou fecha (som de "vush" de arremesso e de golpe)."""
    rng = rng or random.Random(2)
    n = int(seconds * RATE)
    e = env(n, attack, curve=curve)
    out, last = [], 0.0
    for i in range(n):
        k = start + (end - start) * i / n
        last += (rng.uniform(-1, 1) - last) * k
        out.append(last * e[i] * vol)
    return out


def mix(*tracks, at=None):
    """Soma as faixas (at = deslocamento de cada uma em segundos)."""
    at = at or [0.0] * len(tracks)
    n = max(int(o * RATE) + len(t) for t, o in zip(tracks, at))
    out = [0.0] * n
    for t, o in zip(tracks, at):
        start = int(o * RATE)
        for i, s in enumerate(t):
            out[start + i] += s
    return out


def normalize(samples, peak=0.85):
    top = max(1e-9, max(abs(s) for s in samples))
    return [s * peak / top for s in samples]


def save_wav(name, samples, peak=0.85):
    samples = normalize(samples, peak)
    path = OUT / f"{name}.wav"
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes(b"".join(struct.pack("<h", int(max(-1, min(1, s)) * 32767)) for s in samples))
    return path


# ── efeitos ────────────────────────────────────────────────
def effects():
    r = random.Random(7)
    sons = {
        # golpe corpo a corpo: vush rápido
        "golpe": sweep_noise(0.14, 0.08, 0.6, rng=r, attack=0.02, curve=2.5),
        # arco e besta: corda vibrando + vush da flecha
        "arco": mix(tone(110, 0.16, "triangle", 0.9, slide=90, curve=4),
                    tone(220, 0.08, "square", 0.25, curve=6),
                    sweep_noise(0.12, 0.3, 0.05, 0.5, rng=r), at=[0, 0, 0.01]),
        # arremessos (lança, shuriken, granada, disquete...): vush curto
        "arremesso": sweep_noise(0.12, 0.05, 0.4, rng=r, attack=0.03, curve=2),
        # pistola e canhão: estouro grave
        "tiro_forte": mix(noise(0.22, 1.0, rng=r, curve=5, lowpass=0.35),
                          tone(90, 0.2, "sine", 0.9, slide=40, curve=4)),
        # magia (orbe, crânio, lanterna, colmeia): brilho subindo
        "magia": mix(tone(520, 0.22, "sine", 0.6, slide=880, attack=0.02, vibrato=0.02),
                     tone(780, 0.22, "triangle", 0.3, slide=1320, attack=0.03), at=[0, 0.02]),
        # gelo (cristal, estalactites, espelho): sininho de cristal
        "gelo": mix(tone(1760, 0.25, "sine", 0.6, curve=5), tone(2637, 0.2, "sine", 0.35, curve=6),
                    tone(3520, 0.12, "sine", 0.2, curve=6), at=[0, 0.015, 0.03]),
        # elétrico (raio, canhão de pulso): zap
        "eletrico": mix(tone(1200, 0.16, "saw", 0.5, slide=200, curve=2),
                        noise(0.16, 0.5, rng=r, curve=3, lowpass=0.9)),
        # fogo (lança-chamas): sopro abafado
        "fogo": noise(0.18, 1.0, rng=r, attack=0.03, curve=1.5, lowpass=0.12),
        # futebol
        "chute": mix(tone(150, 0.12, "sine", 1.0, slide=60, curve=5), noise(0.05, 0.4, rng=r, lowpass=0.3)),
        "apito": mix(tone(2350, 0.45, "sine", 0.7, attack=0.02, curve=0.6, vibrato=0.025),
                     noise(0.45, 0.06, rng=r, attack=0.02, curve=0.6, lowpass=0.8)),
        "torcida": mix(noise(1.4, 1.0, rng=r, attack=0.15, curve=1.6, lowpass=0.08),
                       noise(1.4, 0.4, rng=r, attack=0.25, curve=1.4, lowpass=0.3)),
        # campanha
        "bau": mix(tone(180, 0.12, "square", 0.3, slide=120, curve=4),           # tampa batendo
                   *[tone(f, 0.35, "triangle", 0.45, curve=3) for f in (523, 659, 784, 1047)],
                   at=[0, 0.12, 0.2, 0.28, 0.36]),
        "teletransporte": mix(tone(220, 0.6, "sine", 0.6, slide=1760, attack=0.05, curve=1.5),
                              tone(330, 0.6, "triangle", 0.3, slide=2640, attack=0.08, curve=1.5)),
        "levantar": mix(*[tone(f, 0.18, "square", 0.25, curve=3) for f in (392, 523, 659, 784)],
                        at=[0, 0.07, 0.14, 0.21]),
        "passo_pesado": mix(tone(55, 0.3, "sine", 1.0, slide=30, curve=3), noise(0.18, 0.6, rng=r, lowpass=0.08)),
    }
    for name, samples in sons.items():
        save_wav(name, samples)
        print("som", name)


def basketball_effects():
    """Sons do basquete (semente própria: não muda os outros efeitos)."""
    r = random.Random(11)
    sons = {
        # bola quicando no chão: tum grave e curto
        "quique": mix(tone(120, 0.09, "sine", 1.0, slide=70, curve=5), noise(0.03, 0.3, rng=r, lowpass=0.15)),
        # bola no aro: metal batendo (parciais desafinadas)
        "aro": mix(tone(620, 0.35, "sine", 0.6, curve=4), tone(1490, 0.25, "sine", 0.35, curve=5),
                   tone(2380, 0.15, "sine", 0.2, curve=6), noise(0.02, 0.4, rng=r, lowpass=0.7)),
        # bola na tabela: pancada seca de madeira
        "tabela": mix(tone(240, 0.1, "triangle", 0.8, slide=180, curve=5), noise(0.05, 0.6, rng=r, lowpass=0.4)),
        # bola passando pela rede: chuá
        "rede": sweep_noise(0.3, 0.6, 0.1, rng=r, attack=0.02, curve=1.8),
        # toco: tapa forte na bola
        "toco": mix(noise(0.08, 1.0, rng=r, curve=4, lowpass=0.6), tone(160, 0.12, "sine", 0.8, slide=80, curve=4)),
        # buzina do fim do tempo
        "buzina": mix(tone(233, 0.9, "square", 0.5, attack=0.01, curve=0.3),
                      tone(277, 0.9, "square", 0.35, attack=0.01, curve=0.3)),
    }
    for name, samples in sons.items():
        save_wav(name, samples)
        print("som", name)


def souls_effects():
    """Sons da v1.6: almas, loja e novidades (semente própria: não muda os outros efeitos)."""
    r = random.Random(16)
    sons = {
        # almas entrando na carteira: arpejo de sininho subindo
        "alma": mix(tone(784, 0.18, "sine", 0.6, curve=4), tone(1175, 0.18, "sine", 0.5, curve=4),
                    tone(1568, 0.3, "sine", 0.45, curve=3, vibrato=0.01), at=[0, 0.05, 0.1]),
        # compra: moeda de alma (duas notas brilhantes e um tilintar)
        "compra": mix(tone(988, 0.08, "square", 0.35, curve=5), tone(1319, 0.3, "square", 0.3, curve=4),
                      noise(0.04, 0.2, rng=r, lowpass=0.9), at=[0, 0.07, 0.07]),
        # abrir a banca: madeira e um sino abafado
        "loja": mix(tone(180, 0.1, "triangle", 0.7, slide=140, curve=5), noise(0.05, 0.4, rng=r, lowpass=0.3),
                    tone(660, 0.35, "sine", 0.35, curve=3), at=[0, 0, 0.05]),
        # virar a página das novidades: vush de papel
        "pagina": sweep_noise(0.16, 0.2, 0.7, vol=0.6, rng=r, attack=0.02, curve=2.5),
    }
    for name, samples in sons.items():
        save_wav(name, samples)
        print("som", name)


def lag_effects():
    """Sons da v1.8 (capítulo 2, Lag Lobby): inimigos, perigos, chefão e armas novas (semente própria)."""
    r = random.Random(18)
    sons = {
        # Rifle de Plasma: zuuum agudo e um estalo
        "plasma": mix(tone(1800, 0.22, "saw", 0.4, slide=500, curve=3), tone(900, 0.22, "sine", 0.5, slide=300, curve=3),
                      noise(0.04, 0.4, rng=r, curve=5, lowpass=0.9)),
        # bip curto de máquina (drone de bolso, torreta travando)
        "bip": tone(1760, 0.07, "square", 0.4, curve=2),
        # drone inimigo mergulhando: zumbido que sobe
        "drone": mix(tone(220, 0.5, "saw", 0.4, slide=520, attack=0.02, curve=1.5, vibrato=0.05),
                     sweep_noise(0.5, 0.1, 0.5, 0.3, rng=r, attack=0.02, curve=1.5)),
        # rajada do miliciano: três estalos secos
        "rajada": mix(*[mix(noise(0.05, 1.0, rng=r, curve=6, lowpass=0.8), tone(140, 0.08, "sine", 0.7, slide=70, curve=4))
                        for _ in range(3)], at=[0, 0.07, 0.14]),
        # laser do corredor de servidores: zap grave que vibra
        "laser": mix(tone(110, 0.45, "saw", 0.6, curve=1.5, vibrato=0.08), tone(880, 0.45, "square", 0.2, slide=440, curve=2)),
        # rajada de vento no heliponto
        "vento": sweep_noise(1.3, 0.02, 0.25, 0.9, rng=r, attack=0.4, curve=1.3),
        # vapor do exoesqueleto (preso, superaquecido)
        "vapor": sweep_noise(0.6, 0.9, 0.4, 0.7, rng=r, attack=0.01, curve=1.8),
        # canhão do Borba carregando: tom subindo
        "carga": mix(tone(120, 0.8, "saw", 0.4, slide=900, attack=0.05, curve=0.6),
                     tone(240, 0.8, "sine", 0.4, slide=1800, attack=0.05, curve=0.6)),
        # soco de metal (manopla, soco do Borba)
        "soco_metal": mix(tone(80, 0.25, "sine", 1.0, slide=45, curve=4), tone(620, 0.3, "square", 0.25, slide=580, curve=5),
                          noise(0.06, 0.7, rng=r, curve=5, lowpass=0.6)),
        # empurrão do Escudo de Choque
        "choque": mix(*[noise(0.04, 0.7, rng=r, curve=5, lowpass=1.0) for _ in range(4)],
                      tone(70, 0.3, "square", 0.4, slide=40, curve=3), at=[0, 0.05, 0.1, 0.15, 0]),
        # teclas do Teclado Mecânico: clique-clique-clique
        "teclado": mix(*[mix(noise(0.02, 0.8, rng=r, curve=6, lowpass=0.95), tone(2400 + i * 200, 0.03, "square", 0.25, curve=6))
                         for i in range(5)], at=[i * 0.045 for i in range(5)]),
        # alarme da Lag Lobby
        "alarme": mix(*[tone(880 if i % 2 == 0 else 660, 0.2, "square", 0.3, curve=0.5) for i in range(4)],
                      at=[i * 0.2 for i in range(4)]),
        # comemoração do Borba Jr Corrompido: vapor roxo e um tranco
        "comemora_borba_corrompido": mix(sweep_noise(0.9, 0.9, 0.2, 0.7, rng=r, attack=0.01, curve=1.6),
                                         tone(60, 0.5, "sine", 1.0, slide=35, curve=3),
                                         tone(300, 0.6, "saw", 0.3, slide=900, attack=0.05, curve=1.0), at=[0.1, 0, 0.2]),
    }
    for name, samples in sons.items():
        save_wav(name, samples)
        print("som", name)


def crowd(seconds, base, slide=None, voices=9, vol=1.0, rng=None, attack=0.08, curve=1.5, kind="saw"):
    """Várias vozes desafinadas cantando juntas (o "uuuh", o "ooh" e a vaia da torcida)."""
    rng = rng or random.Random(3)
    tracks = []
    for _ in range(voices):
        f = base * rng.uniform(0.92, 1.08)
        end = slide * rng.uniform(0.92, 1.08) if slide else None
        tracks.append(tone(f, seconds, kind, vol / voices, slide=end, attack=attack, curve=curve,
                           vibrato=rng.uniform(0.01, 0.03)))
    tracks.append(noise(seconds, 0.25 * vol, rng=rng, attack=attack, curve=curve, lowpass=0.12))
    return mix(*tracks)


def sport_effects():
    """Sons da v1.7: enterrada, chute, gol, replay, pênaltis e comemorações (semente própria)."""
    r = random.Random(17)
    sons = {
        # enterrada: tranco do aro, rede chicoteando e um tum grave na câmera lenta
        "cravada": mix(tone(52, 0.6, "sine", 1.0, slide=34, curve=2.5), tone(540, 0.4, "sine", 0.5, curve=4),
                       tone(1310, 0.3, "sine", 0.3, curve=5), sweep_noise(0.25, 0.9, 0.15, 0.7, rng=r, curve=2),
                       at=[0, 0, 0, 0.04]),
        # chute forte: estalo seco
        "chute_forte": mix(noise(0.05, 1.0, rng=r, curve=6, lowpass=0.9), tone(110, 0.16, "sine", 0.9, slide=60, curve=4)),
        # chute com curva: assobio que sobe e desce acompanhando a bola
        "assobio": mix(tone(1400, 0.7, "sine", 0.5, slide=2100, attack=0.05, curve=1.2, vibrato=0.02),
                       sweep_noise(0.7, 0.05, 0.3, 0.25, rng=r, attack=0.05, curve=1.5)),
        # gol: a rede estufando (chuá longo)
        "gol_rede": sweep_noise(0.6, 0.7, 0.05, rng=r, attack=0.01, curve=1.4),
        # replay: o mesmo chuá e a torcida, graves e lentos
        "replay": mix(sweep_noise(1.2, 0.3, 0.02, 0.8, rng=r, attack=0.05, curve=1.2),
                      crowd(1.4, 180, 150, rng=r, attack=0.2, curve=1.2, vol=0.6)),
        # pênalti: a torcida abafando até o silêncio antes da batida
        "torcida_abafa": mix(noise(1.6, 0.9, rng=r, attack=0.02, curve=2.2, lowpass=0.18),
                             crowd(1.6, 260, None, rng=r, attack=0.02, curve=2.5, vol=0.5)),
        # coração batendo na decisiva: tum-tum
        "coracao": mix(tone(58, 0.16, "sine", 1.0, slide=40, curve=4), tone(52, 0.2, "sine", 0.8, slide=38, curve=4),
                       at=[0, 0.22]),
        # vaia da torcida rival
        "vaia": crowd(1.4, 140, 120, voices=12, rng=r, attack=0.15, curve=1.4, kind="square"),
        # "uuuh" na isolada e na trave
        "uuuh": crowd(1.2, 300, 190, rng=r, attack=0.06, curve=1.6),
        # catimba e cartão: "ooh" da torcida
        "ooh": crowd(1.0, 220, 330, rng=r, attack=0.08, curve=1.8),
        # apito longo do juiz
        "apito_longo": mix(tone(2800, 0.9, "square", 0.4, attack=0.01, curve=0.4, vibrato=0.04),
                           noise(0.9, 0.2, rng=r, attack=0.01, curve=0.4, lowpass=0.6)),
    }
    # comemorações: um som por herói
    hero = {
        "trovao": mix(noise(0.9, 1.0, rng=r, curve=2.2, lowpass=0.25), tone(45, 0.9, "sine", 0.9, slide=30, curve=2)),
        "aryel": mix(tone(70, 0.9, "saw", 0.6, slide=160, attack=0.05, curve=0.8),
                     tone(140, 0.9, "square", 0.25, slide=320, attack=0.05, curve=0.8)),
        "borba": mix(sweep_noise(0.9, 0.9, 0.1, 0.9, rng=r, attack=0.01, curve=1.5),
                     tone(90, 0.3, "square", 0.4, slide=60, curve=4)),
        "albeguinio": mix(*[noise(0.03, 0.8, rng=r, curve=6, lowpass=0.8) for _ in range(7)],
                          tone(1320, 0.2, "square", 0.3, curve=3), at=[i * 0.08 for i in range(7)] + [0.6]),
        "aryel_corrompido": mix(*[tone(180 - i * 12, 0.16, "saw", 0.5, slide=140 - i * 12, curve=3) for i in range(5)],
                                at=[i * 0.15 for i in range(5)]),
        "geada": mix(tone(2093, 0.6, "sine", 0.5, curve=3), tone(2637, 0.5, "sine", 0.4, curve=3),
                     tone(3136, 0.4, "sine", 0.3, curve=3), sweep_noise(0.5, 0.9, 0.3, 0.3, rng=r), at=[0, 0.06, 0.12, 0]),
        "faisca": mix(*[tone(1568 + i * 260, 0.12, "triangle", 0.4, curve=4) for i in range(5)],
                      at=[i * 0.06 for i in range(5)]),
        "tita": mix(tone(40, 0.7, "sine", 1.0, slide=28, curve=2), noise(0.5, 0.6, rng=r, curve=2, lowpass=0.05)),
        "tanque": mix(tone(70, 0.15, "sine", 1.0, slide=50, curve=4), tone(70, 0.15, "sine", 1.0, slide=50, curve=4),
                      at=[0, 0.25]),
        "guerreiro": mix(tone(1200, 0.5, "sine", 0.5, curve=3), tone(2900, 0.4, "sine", 0.3, curve=4),
                         noise(0.04, 0.6, rng=r, lowpass=0.9)),
        "pirata": mix(tone(392, 0.2, "square", 0.3, curve=3), tone(523, 0.2, "square", 0.3, curve=3),
                      tone(659, 0.4, "square", 0.3, curve=2), at=[0, 0.15, 0.3]),
        "ninja": sweep_noise(0.5, 0.05, 0.6, 0.8, rng=r, attack=0.01, curve=2),
        "fantasma": tone(330, 0.9, "sine", 0.6, slide=220, attack=0.1, curve=1.5, vibrato=0.06),
        "velocista": sweep_noise(0.4, 0.1, 0.9, 0.8, rng=r, attack=0.01, curve=2),
        "ginga": mix(*[tone(f, 0.12, "square", 0.3, curve=4) for f in (523, 659, 784, 659, 523, 659)],
                     at=[i * 0.12 for i in range(6)]),
        "matador": mix(sweep_noise(0.3, 0.3, 0.05, 0.6, rng=r), crowd(0.8, 220, 160, rng=r, vol=0.5)),
        "cauanzera": sweep_noise(0.4, 0.2, 0.8, 0.7, rng=r, attack=0.02, curve=2),
        "atirador": sweep_noise(0.35, 0.4, 0.05, 0.6, rng=r, attack=0.05, curve=2),
        "paredao": mix(tone(110, 0.2, "sine", 0.8, slide=80, curve=4), noise(0.4, 0.4, rng=r, curve=2, lowpass=0.1)),
    }
    for key, samples in hero.items():
        sons["comemora_" + key] = samples
    for name, samples in sons.items():
        save_wav(name, samples)
        print("som", name)


# ── músicas (chiptune) ─────────────────────────────────────
NOTE = {n: i for i, n in enumerate(["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"])}


def freq(note):
    """'A4' -> 440 Hz."""
    name, octave = note[:-1], int(note[-1])
    return 440.0 * 2 ** ((NOTE[name] - 9) / 12 + (octave - 4))


def render(bpm, bars, chords, melody, bass_kind, lead_kind, drums, lead_vol=0.32, seed=3):
    """Uma faixa em loop: acordes em arpejo, baixo, melodia e bateria de ruído."""
    beat = 60 / bpm
    step = beat / 4                                  # semicolcheia
    total = int(bars * 16 * step * RATE)
    out = [0.0] * total
    rng = random.Random(seed)

    def put(samples, t):
        start = int(t * RATE)
        for i, s in enumerate(samples):
            if start + i < total:
                out[start + i] += s

    for bar in range(bars):
        chord = chords[bar % len(chords)]
        t0 = bar * 16 * step
        # arpejo
        for k in range(16):
            note = chord[k % len(chord)]
            put(tone(freq(note), step * 0.9, "pulse", 0.10, curve=2), t0 + k * step)
        # baixo
        root = chord[0][:-1] + str(int(chord[0][-1]) - 1)
        for k in range(0, 16, 4 if bass_kind == "calmo" else 2):
            put(tone(freq(root), step * (3.5 if bass_kind == "calmo" else 1.8), "triangle", 0.30, curve=1.5),
                t0 + k * step)
        # bateria
        for k, hit in enumerate(drums):
            if hit == "k":
                put(tone(70, 0.15, "sine", 0.45, slide=40, curve=4), t0 + k * step)
            elif hit == "s":
                put(noise(0.12, 0.22, rng=rng, curve=4, lowpass=0.6), t0 + k * step)
            elif hit == "h":
                put(noise(0.03, 0.08, rng=rng, curve=4, lowpass=1.0), t0 + k * step)
    # melodia: (nota ou None, duração em semicolcheias)
    t = 0.0
    while t < bars * 16 * step - 1e-6:
        for note, length in melody:
            if note:
                put(tone(freq(note), length * step * 0.95, lead_kind, lead_vol, attack=0.01, curve=1.2,
                         vibrato=0.004), t)
            t += length * step
    # fim do loop suave (sem estalo na emenda)
    fade = int(0.01 * RATE)
    for i in range(fade):
        out[total - 1 - i] *= i / fade
        out[i] *= i / fade
    return out


def music():
    # acampamento: calmo, em lá menor, 84 bpm
    camp = render(
        84, 16,
        chords=[("A3", "C4", "E4"), ("F3", "A3", "C4"), ("C4", "E4", "G4"), ("G3", "B3", "D4")],
        melody=[("E5", 4), ("D5", 2), ("C5", 2), ("A4", 8), (None, 4), ("C5", 2), ("D5", 2), ("E5", 4), ("G5", 4),
                ("F5", 6), ("E5", 2), ("D5", 4), ("C5", 4), ("B4", 8), (None, 8)],
        bass_kind="calmo", lead_kind="triangle",
        drums=["k", "", "h", "", "", "", "h", "", "s", "", "h", "", "", "", "h", ""], lead_vol=0.28)
    # chefão: tenso, em ré menor, 150 bpm
    boss = render(
        150, 16,
        chords=[("D4", "F4", "A4"), ("D4", "F4", "A4"), ("A#3", "D4", "F4"), ("C4", "E4", "G4"),
                ("D4", "F4", "A4"), ("D4", "F4", "A4"), ("G3", "A#3", "D4"), ("A3", "C#4", "E4")],
        melody=[("D5", 2), ("D5", 2), ("F5", 2), ("D5", 2), ("A5", 4), ("G5", 2), ("F5", 2),
                ("E5", 2), ("F5", 2), ("E5", 2), ("C5", 2), ("D5", 8),
                ("A4", 2), ("D5", 2), ("F5", 2), ("A5", 2), ("A#5", 4), ("A5", 4),
                ("G5", 2), ("F5", 2), ("E5", 2), ("C#5", 2), ("D5", 8)],
        bass_kind="tenso", lead_kind="square",
        drums=["k", "h", "h", "h", "s", "h", "k", "h", "k", "h", "h", "h", "s", "h", "h", "s"], lead_vol=0.22)
    # ganho para ficar no mesmo volume percebido da música de batalha (o limitador segura os picos)
    for name, samples, gain in (("camp_bgm", camp, 6), ("boss_bgm", boss, 9)):
        encode(name, samples, gain)


def encode(name, samples, gain):
    """Salva a música em .ogg (o .wav de trabalho é apagado); sem ffmpeg, fica em .wav."""
    tmp = OUT / f"_{name}.wav"
    save_wav(f"_{name}", samples, peak=0.8)
    if shutil.which("ffmpeg"):
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(tmp),
                        "-af", f"volume={gain}dB,alimiter=limit=0.95", "-c:a", "libvorbis", "-q:a", "4",
                        str(OUT / f"{name}.ogg")], check=True)
        tmp.unlink()
    else:
        tmp.replace(OUT / f"{name}.wav")
        print("ffmpeg não encontrado: música salva em .wav")
    print("música", name)


def lag_music():
    """Chefão da Lag Lobby (Borba Jr Corrompido): mais eletrônico, em mi menor, 160 bpm."""
    boss = render(
        160, 16,
        chords=[("E4", "G4", "B4"), ("E4", "G4", "B4"), ("C4", "E4", "G4"), ("D4", "F#4", "A4"),
                ("E4", "G4", "B4"), ("E4", "G4", "B4"), ("A3", "C4", "E4"), ("B3", "D#4", "F#4")],
        melody=[("E5", 2), ("E5", 2), ("G5", 2), ("E5", 2), ("B5", 2), ("A5", 2), ("G5", 2), ("F#5", 2),
                ("E5", 2), ("F#5", 2), ("G5", 2), ("D5", 2), ("E5", 8),
                ("B4", 2), ("E5", 2), ("G5", 2), ("B5", 2), ("C6", 4), ("B5", 4),
                ("A5", 2), ("G5", 2), ("F#5", 2), ("D#5", 2), ("E5", 8)],
        bass_kind="tenso", lead_kind="saw",
        drums=["k", "h", "k", "h", "s", "h", "k", "h", "k", "h", "k", "h", "s", "h", "s", "s"], lead_vol=0.16, seed=18)
    encode("boss_lag_bgm", boss, 9)


if __name__ == "__main__":
    effects()
    basketball_effects()
    souls_effects()
    sport_effects()
    lag_effects()
    music()
    lag_music()
