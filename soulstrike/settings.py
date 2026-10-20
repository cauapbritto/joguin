"""Opções do jogador (volume, tela cheia, vsync, tremor, duplo toque), salvas no computador.

Ficam em opcoes.json, na mesma pasta do progresso (veja progress.py). Valor faltando ou
estragado no arquivo volta ao padrão, então um arquivo antigo ou editado à mão não quebra o jogo.
"""
import json

from . import progress

DEFAULTS = {
    "volume_geral": 1.0,
    "volume_musica": 1.0,
    "volume_efeitos": 1.0,
    "tela_cheia": True,
    "vsync": True,
    "tremor": True,         # tremor de tela nos impactos
    "duplo_toque": True,    # duplo toque numa seta = esquiva/corte
}
VOLUME_KEYS = ("volume_geral", "volume_musica", "volume_efeitos")
VOLUME_STEP = 0.1

_values = None


def path():
    return progress.path().parent / "opcoes.json"


def _clean(data):
    values = dict(DEFAULTS)
    if not isinstance(data, dict):
        return values
    for key, default in DEFAULTS.items():
        value = data.get(key)
        if isinstance(default, bool):
            if isinstance(value, bool):
                values[key] = value
        elif isinstance(value, (int, float)) and not isinstance(value, bool):
            values[key] = round(max(0.0, min(1.0, float(value))), 2)
    return values


def load():
    global _values
    try:
        _values = _clean(json.loads(path().read_text(encoding="utf-8")))
    except (OSError, ValueError):
        _values = dict(DEFAULTS)
    return _values


def get(key):
    if _values is None:
        load()
    return _values[key]


def change(key, value):
    if _values is None:
        load()
    _values[key] = _clean({key: value})[key]
    save()
    return _values[key]


def save():
    p = path()
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        tmp = p.with_suffix(".tmp")
        tmp.write_text(json.dumps(_values, ensure_ascii=False, indent=1), encoding="utf-8")
        tmp.replace(p)
        return True
    except OSError:
        return False


def sfx_volume():
    return get("volume_geral") * get("volume_efeitos")


def music_volume():
    return get("volume_geral") * get("volume_musica")
