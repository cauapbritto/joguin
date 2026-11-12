"""Gera as versões dos efeitos que tocam muito (tiro, golpe, chute, passo...).

Uso:  python tools/gerar_variacoes.py    (precisa do ffmpeg)

Para cada som da lista sai <nome>_v2.wav (um pouco mais agudo) e <nome>_v3.wav (um pouco mais
grave). O jogo sorteia entre o original e as versões a cada vez (soulstrike/som.py), e o mesmo
tiro 40 vezes seguidas para de soar idêntico. Rodar de novo gera os mesmos arquivos.
"""
import shutil
import subprocess
import sys
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "assets" / "sounds"
FREQUENT = ("hit", "shoot", "shoot2", "golpe", "chute", "dash", "quique", "passo_pesado", "explosion",
            "soco_metal", "plasma", "rajada", "arco", "gelo", "fogo", "eletrico", "magia", "tabela", "aro")
# (sufixo, quanto muda o tom, quanto muda o volume)
SHIFTS = (("_v2", 1.06, 0.92), ("_v3", 0.94, 1.0))


def main(names=FREQUENT):
    if not shutil.which("ffmpeg"):
        sys.exit("ffmpeg não encontrado")
    for name in names:
        src = OUT / f"{name}.wav"
        if not src.is_file():
            print("sem", name)
            continue
        for suffix, rate, gain in SHIFTS:
            dst = OUT / f"{name}{suffix}.wav"
            subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(src), "-af",
                            f"asetrate={round(44100 * rate)},aresample=44100,volume={gain}",
                            "-ac", "1", "-ar", "44100", "-c:a", "pcm_s16le", "-fflags", "+bitexact",
                            "-flags:a", "+bitexact", "-map_metadata", "-1", str(dst)], check=True)
        print("versões de", name)


if __name__ == "__main__":
    main()
