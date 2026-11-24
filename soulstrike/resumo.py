"""Resumo da partida para o celular: na tela de resultado, o app mostra os números de quem está
com ele (gols, pontos, dano, abates, almas) e quem foi o DESTAQUE.

O jogo monta o resumo quando a partida acaba (``of_match``, ``of_run`` ou ``of_result``) e publica
no hub (``hub.set_summary``); o /api/status manda só enquanto a tela de resultado está aberta.
O nome de cada um é o apelido do app (hub.nick), ou P1, P2... e CPU.
"""
from . import config, stats
from .net.remote import hub


def _hex(color):
    return "#%02x%02x%02x" % tuple(int(c) for c in color[:3])


def label_of(slot, cpu=False):
    """Como o resumo chama um jogador: o apelido do app, P1... ou CPU."""
    if cpu or not slot:
        return "CPU"
    return hub.nick(slot) or f"P{slot}"


def _num(f, name):
    v = getattr(f, name, 0)
    return v if isinstance(v, int) and not isinstance(v, bool) else 0


def _lines(f, kind, teams):
    """(rótulo, valor) dos números de um jogador nesta modalidade."""
    if kind == "basquete":
        rows = [("PONTOS", _num(f, "points"))]
        rows += [(name, n) for name, n in (("ENTERRADAS", _num(f, "dunks")), ("TOCOS", _num(f, "blocks")),
                                           ("ROUBOS", _num(f, "steals"))) if n]
    elif kind == "futebol":
        rows = [("GOLS", _num(f, "goals"))]
    else:
        rows = [("DANO CAUSADO", _num(f, "damage_dealt")), ("ACERTOS", _num(f, "hits"))]
        if teams:
            rows.append(("ABATES", _num(f, "kills")))
    return [[label, str(value)] for label, value in rows]


def _score(f, kind):
    """Quem foi melhor (o DESTAQUE): pontos e defesa no basquete, gols no futebol, abates e dano no resto."""
    if kind == "basquete":
        return _num(f, "points") + 2 * (_num(f, "blocks") + _num(f, "steals")), _num(f, "dunks")
    if kind == "futebol":
        return _num(f, "goals"), _num(f, "damage_dealt")
    return _num(f, "kills"), _num(f, "damage_dealt")


def _base(result):
    score = getattr(result, "score", None)
    return {"title": result.title, "color": _hex(result.color),
            "score": f"{score[0]} x {score[1]}" if score else None, "mvp": None, "players": {},
            "lines": [[str(a), str(b)] for a, b in getattr(result, "lines", [])][:8], "records": []}


def of_result(result):
    """Só o que a TV mostra (pênaltis, luta): título, placar e as linhas do quadro."""
    return _base(result)


def of_match(match, result, session=None, records=()):
    """Resumo de uma partida de duelo, times, futebol ou basquete que acabou."""
    data = _base(result)
    mode = getattr(session, "mode", "") if session is not None else ""
    kind = stats.category(mode) if mode else "duelos"
    teams = any(getattr(f, "team", None) is not None for f in match.fighters)
    winners = set(map(id, result.winners))
    fighters = [f for f in match.fighters if getattr(f, "stats", None) is not None]
    for f in fighters:
        if f.is_cpu or not f.slot:
            continue
        data["players"][str(f.slot)] = {
            "label": label_of(f.slot), "hero": f.stats.name.upper(),
            "won": (id(f) in winners) if winners else None,
            "lines": _lines(f, kind, teams),
        }
    if fighters:
        best = max(fighters, key=lambda f: (_score(f, kind), id(f) in winners))
        if any(_score(best, kind)):
            data["mvp"] = {"slot": None if best.is_cpu else best.slot, "label": label_of(best.slot, best.is_cpu),
                           "hero": best.stats.name.upper()}
    data["records"] = [stats.RECORD_LABELS[r] for r in records if r in stats.RECORD_LABELS]
    return data


def of_run(run, title, color, won=None):
    """Resumo da campanha (fim de jogo, capítulo concluído, campanha concluída): abates, dano e almas."""
    data = {"title": title, "color": _hex(color), "score": None, "mvp": None, "players": {}, "lines": [],
            "records": []}
    secs = run.frames // config.FPS
    data["lines"] = [["TEMPO", f"{secs // 60}:{secs % 60:02d}"]]
    for s in run.slots:
        data["players"][str(s)] = {
            "label": label_of(s), "hero": "", "won": won,
            "lines": [["ABATES", str(run.kills.get(s, 0))], ["DANO CAUSADO", str(run.damage.get(s, 0))],
                      ["ALMAS NA CARTEIRA", str(run.souls.get(s, 0))]],
        }
    if run.slots:
        best = max(run.slots, key=lambda s: (run.kills.get(s, 0), run.damage.get(s, 0)))
        if run.kills.get(best, 0) or run.damage.get(best, 0):
            data["mvp"] = {"slot": best, "label": label_of(best), "hero": ""}
    return data
