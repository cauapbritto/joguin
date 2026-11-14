"""Progresso salvo no computador: capítulos zerados (o 1 libera o Aryel Corrompido, o 2 o Borba Jr
Corrompido, o 3 o Albeguinio Corrompido e o 4 o Cauanzera Corrompido) e melhores tempos da campanha
inteira.

Fica em %APPDATA%/SoulStrike/progresso.json no Windows (ou ~/.soulstrike no Linux/Mac).
A variável de ambiente SOULSTRIKE_PROGRESS troca o arquivo (usada nos testes).
"""
import copy
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


# a última leitura do arquivo: a Casa pergunta pelo progresso várias vezes por quadro (pet, skins,
# guarda-roupa) e ler o disco toda vez dava engasgo em PC com HD lento ou antivírus olhando o arquivo.
# Vale enquanto o arquivo não muda (mesmo caminho, data e tamanho).
_cache = {"key": None, "data": None}


def load():
    p = path()
    try:
        st = p.stat()
        key = (str(p), st.st_mtime_ns, st.st_size)
    except OSError:
        return {}
    if _cache["key"] != key:
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            data = None
        _cache["key"], _cache["data"] = key, data if isinstance(data, dict) else {}
    # cópia: quem recebe pode mexer à vontade sem estragar a guardada (só save() grava)
    return copy.deepcopy(_cache["data"])


def save(data):
    p = path()
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        tmp = p.with_suffix(".tmp")
        tmp.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
        tmp.replace(p)
        _cache["key"] = None                 # a próxima leitura pega o que acabou de ser gravado
        return True
    except OSError:
        return False


def chapter_cleared(chapter):
    """Capítulo zerado. Quem zerou a campanha antiga (só tinha o capítulo 1) tem "campanha_zerada"."""
    data = load()
    if chapter == 1:
        return bool(data.get("capitulo1_zerado") or data.get("campanha_zerada"))
    return bool(data.get(f"capitulo{chapter}_zerado"))


def campaign_cleared():
    """Capítulo 1 zerado (libera o Aryel Corrompido e o atalho para o capítulo 2)."""
    return chapter_cleared(1)


def record_chapter(chapter):
    """Fim de um capítulo que não é o último (1: o cristal quebrou; 2: o fragmento se partiu;
    3: o caco virou pó).
    Devolve True se o lutador secreto dele foi liberado agora."""
    unlocked_now = not chapter_cleared(chapter)
    data = load()
    for k in range(1, chapter + 1):
        data[f"capitulo{k}_zerado"] = True
    save(data)
    return unlocked_now


def record_chapter1():
    return record_chapter(1)


LAST_CHAPTER = 4
TIMES = "melhor_tempo_4cap"      # a campanha ganhou o capítulo 4: os tempos de 3 capítulos ficam de fora


def best_time(difficulty):
    value = load().get(TIMES, {}).get(difficulty)
    return value if isinstance(value, (int, float)) else None


def record_campaign(seconds, difficulty, players, full=True):
    """Registra a campanha zerada (fim do último capítulo). Devolve (recorde_novo, desbloqueou_agora):
    o desbloqueio é o do Cauanzera Corrompido. O tempo só conta como recorde na campanha inteira
    (``full``); quem começou direto de outro capítulo não entra no recorde."""
    data = load()
    unlocked_now = not data.get(f"capitulo{LAST_CHAPTER}_zerado")
    for k in range(1, LAST_CHAPTER + 1):
        data[f"capitulo{k}_zerado"] = True
    times = data.setdefault(TIMES, {})
    old = times.get(difficulty)
    record = full and (not isinstance(old, (int, float)) or seconds < old)
    if record:
        times[difficulty] = int(seconds)
    data["vezes_zerada"] = int(data.get("vezes_zerada", 0)) + 1
    seals = data.setdefault("selos", {})              # selo de zerado de cada dificuldade
    seals[difficulty] = True
    data["jogadores_ultima"] = players
    save(data)
    return record, unlocked_now


def seals():
    """Dificuldades em que a campanha já foi zerada (os selos do menu)."""
    return {k for k, v in load().get("selos", {}).items() if v}


def rush_seals():
    return {k for k, v in load().get("selos_reuniao", {}).items() if v}


def record_rush(difficulty):
    """Reunião dos Corrompidos vencida nessa dificuldade. Devolve True se o selo é novo."""
    data = load()
    seals_ = data.setdefault("selos_reuniao", {})
    new = not seals_.get(difficulty)
    seals_[difficulty] = True
    save(data)
    return new


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


def uniform_on():
    """UNIFORME ligado nas regras, e só para quem já zerou o capítulo 4."""
    from . import settings
    return bool(settings.get("uniforme")) and chapter_cleared(4)
