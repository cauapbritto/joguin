"""Progresso salvo no computador: campanha zerada (libera o Aryel Corrompido) e melhores tempos.

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


def campaign_cleared():
    return bool(load().get("campanha_zerada"))


def best_time(difficulty):
    value = load().get("melhor_tempo", {}).get(difficulty)
    return value if isinstance(value, (int, float)) else None


def record_campaign(seconds, difficulty, players):
    """Registra uma campanha zerada. Devolve (recorde_novo, desbloqueou_agora)."""
    data = load()
    unlocked_now = not data.get("campanha_zerada")
    data["campanha_zerada"] = True
    times = data.setdefault("melhor_tempo", {})
    old = times.get(difficulty)
    record = not isinstance(old, (int, float)) or seconds < old
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
