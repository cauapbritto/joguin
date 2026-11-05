"""Estatísticas e recordes deste computador (tela ESTATÍSTICAS do título).

Cada partida de duelo, futebol ou basquete que termina conta: partidas por modalidade, campanha de
vitórias contra a CPU, heróis mais usados (e quantas vezes ganharam) e os recordes de uma partida.
Fica junto do progresso (progress.py), na chave "estatisticas". Treino e campanha não contam.
"""
from . import progress

KEY = "estatisticas"
CATEGORIES = ("duelos", "futebol", "basquete")


def category(mode):
    if mode.startswith("basket"):
        return "basquete"
    if mode.startswith("soccer") or mode in ("penaltis", "penaltis1", "desafio_goleiro"):
        return "futebol"
    return "duelos"


def counts(session):
    return session is not None and not session.campaign and not session.mode.startswith("treino")


def load():
    data = progress.load().get(KEY)
    return data if isinstance(data, dict) else {}


def _num(d, key):
    v = d.get(key, 0)
    return v if isinstance(v, int) and not isinstance(v, bool) else 0


def _record(stats, key, value, who):
    old = stats.get(key)
    if value > 0 and (not isinstance(old, dict) or value > _num(old, "valor")):
        stats[key] = {"valor": value, "quem": who}
        return True
    return False


def record(session, match):
    """Conta uma partida que acabou. Devolve os recordes batidos agora (para a tela de resultado)."""
    result = getattr(match, "result", None)
    if not counts(session) or result is None:
        return []
    data = progress.load()
    stats = data.get(KEY) if isinstance(data.get(KEY), dict) else {}
    cat = category(session.mode)
    partidas = stats.setdefault("partidas", {})
    partidas[cat] = _num(partidas, cat) + 1
    humans = [f for f in match.fighters if not f.is_cpu and f.slot]
    winners = set(map(id, result.winners))
    heroes = stats.setdefault("herois", {})
    for f in humans:
        h = heroes.setdefault(f.stats.key, {})
        h["jogos"] = _num(h, "jogos") + 1
        if id(f) in winners:
            h["vitorias"] = _num(h, "vitorias") + 1
    beaten = []
    if humans and any(f.is_cpu for f in match.fighters):
        cpu = stats.setdefault("contra_cpu", {})
        if any(id(f) in winners for f in humans):
            cpu["vitorias"] = _num(cpu, "vitorias") + 1
            cpu["seguidas"] = _num(cpu, "seguidas") + 1
            if _record(stats, "maior_sequencia", cpu["seguidas"], ""):
                beaten.append("maior_sequencia")
        elif result.winners:
            cpu["derrotas"] = _num(cpu, "derrotas") + 1
            cpu["seguidas"] = 0
        else:
            cpu["empates"] = _num(cpu, "empates") + 1
    for f in humans:
        name = f.stats.name.upper()
        if cat == "futebol" and _record(stats, "mais_gols", getattr(f, "goals", 0), name):
            beaten.append("mais_gols")
        if cat == "basquete" and _record(stats, "mais_pontos", getattr(f, "points", 0), name):
            beaten.append("mais_pontos")
    if cat == "futebol" and result.score:
        a, b = result.score
        if _record(stats, "maior_goleada", abs(a - b), f"{max(a, b)} x {min(a, b)}"):
            beaten.append("maior_goleada")
    data[KEY] = stats
    progress.save(data)
    return beaten


RECORD_LABELS = {
    "mais_gols": "MAIS GOLS NUMA PARTIDA",
    "mais_pontos": "MAIS PONTOS NUM JOGO DE BASQUETE",
    "maior_goleada": "MAIOR GOLEADA",
    "maior_sequencia": "MAIS VITÓRIAS SEGUIDAS CONTRA A CPU",
}


def top_heroes(stats, n=5):
    heroes = stats.get("herois", {})
    rows = [(k, _num(v, "jogos"), _num(v, "vitorias")) for k, v in heroes.items() if isinstance(v, dict)]
    rows.sort(key=lambda r: (-r[1], -r[2], r[0]))
    return rows[:n]
