"""Progresso salvo no computador: capítulos zerados (o 1 libera o Aryel Corrompido, o 2 o Borba Jr
Corrompido) e melhores tempos da campanha inteira.

Fica em %APPDATA%/SoulStrike/progresso.json no Windows (ou ~/.soulstrike no Linux/Mac).
A variável de ambiente SOULSTRIKE_PROGRESS troca o arquivo (usada nos testes).
"""
import json
import os
from pathlib import Path


def path():
    custom = os.environ.get("SOULSTRIKE_PROGRESS")
    if custom:
        return Path(custom)
    base = os.environ.get("APPDATA")
    folder = Path(base) / "SoulStrike" if base else Path.home() / ".soulstrike"
    return folder / "progresso.json"


def load():
    try:
        data = json.loads(path().read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def save(data):
    p = path()
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        tmp = p.with_suffix(".tmp")
        tmp.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
        tmp.replace(p)
        return True
    except OSError:
        return False


def chapter_cleared(chapter):
    """Capítulo zerado. Quem zerou a campanha antiga (só tinha o capítulo 1) tem "campanha_zerada"."""
    data = load()
    if chapter == 1:
        return bool(data.get("capitulo1_zerado") or data.get("campanha_zerada"))
    return bool(data.get("capitulo2_zerado"))


def campaign_cleared():
    """Capítulo 1 zerado (libera o Aryel Corrompido e o atalho para o capítulo 2)."""
    return chapter_cleared(1)


def record_chapter1():
    """Fim do capítulo 1 (o cristal quebrou). Devolve True se o Aryel Corrompido foi liberado agora."""
    data = load()
    unlocked_now = not (data.get("capitulo1_zerado") or data.get("campanha_zerada"))
    data["capitulo1_zerado"] = True
    save(data)
    return unlocked_now


TIMES = "melhor_tempo_2cap"      # a campanha ganhou o capítulo 2: os tempos antigos (só o 1) ficam de fora


def best_time(difficulty):
    value = load().get(TIMES, {}).get(difficulty)
    return value if isinstance(value, (int, float)) else None


def record_campaign(seconds, difficulty, players, full=True):
    """Registra a campanha zerada (fim do capítulo 2). Devolve (recorde_novo, desbloqueou_agora):
    o desbloqueio é o do Borba Jr Corrompido. O tempo só conta como recorde na campanha inteira
    (``full``); quem começou direto do capítulo 2 não entra no recorde."""
    data = load()
    unlocked_now = not data.get("capitulo2_zerado")
    data["capitulo1_zerado"] = data["capitulo2_zerado"] = True
    times = data.setdefault(TIMES, {})
    old = times.get(difficulty)
    record = full and (not isinstance(old, (int, float)) or seconds < old)
    if record:
        times[difficulty] = int(seconds)
    data["vezes_zerada"] = int(data.get("vezes_zerada", 0)) + 1
    data["jogadores_ultima"] = players
    save(data)
    return record, unlocked_now


# ── campanha salva (no começo de cada fase) ──
def save_campaign(state):
    data = load()
    data["campanha_salva"] = state
    return save(data)


def saved_campaign():
    state = load().get("campanha_salva")
    return state if isinstance(state, dict) else None


def clear_campaign():
    data = load()
    if data.pop("campanha_salva", None) is not None:
        save(data)
