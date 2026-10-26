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
    "controle_comeca_no_p2": False,     # 1º controle USB é o P2 (o P1 fica no teclado)
    "teclas": {},           # teclas trocadas: {"1": {"attack": código}, ...} (controls.py)
    "armas_por_round": True,    # duelo: escolher as armas antes de cada round (V na escolha de personagem)
    "futebol_partida": "3",     # futebol: 3, 5 ou 7 gols, ou "tempo" (T na escolha de personagem)
    "versao_vista": "",     # última versão cujas novidades o jogador já viu (novidades.py)
}
VOLUME_KEYS = ("volume_geral", "volume_musica", "volume_efeitos")
VOLUME_STEP = 0.1

_values = None


def path():
    return progress.path().parent / "opcoes.json"


def _clean(data):
    values = {k: (dict(v) if isinstance(v, dict) else v) for k, v in DEFAULTS.items()}
    if not isinstance(data, dict):
        return values
    for key, default in DEFAULTS.items():
        value = data.get(key)
        if isinstance(default, str):
            if isinstance(value, str):
                values[key] = value[:20]
        elif isinstance(default, bool):
            if isinstance(value, bool):
                values[key] = value
        elif isinstance(default, dict):
            if isinstance(value, dict):
                values[key] = {str(k): dict(v) for k, v in value.items() if isinstance(v, dict)}
        elif isinstance(value, (int, float)) and not isinstance(value, bool):
            values[key] = round(max(0.0, min(1.0, float(value))), 2)
    return values


def load():
    global _values
    try:
        _values = _clean(json.loads(path().read_text(encoding="utf-8")))
    except (OSError, ValueError):
        _values = _clean({})
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
