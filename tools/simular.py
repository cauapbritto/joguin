"""Simula partidas CPU x CPU sem janela e mostra quem está forte ou fraco demais.

    python tools/simular.py duelo              # todos contra todos, CPU difícil, 10 rounds por dupla
    python tools/simular.py futebol1 --jogos 60
    python tools/simular.py futebol2 --jogos 40
    python tools/simular.py basquete --jogos 40

A CPU não joga igual a gente: os números apontam onde olhar, não dão o veredito. Serve para
comparar antes e depois de uma mudança de equilíbrio (rode as duas versões com a mesma --semente).
"""
import argparse
import collections
import os
import random
import statistics
import sys
from concurrent.futures import ProcessPoolExecutor

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "tests"))
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

MODES = {"futebol1": "soccer1", "futebol2": "soccer2", "basquete": "basket2"}
MAX_FRAMES = 60 * 60 * 12


def _game():
    from apoio import game          # a mesma janela escondida dos testes
    return game()


def _duel_round(args):
    a, b, difficulty = args
    from soulstrike.matches import BattleMatch
    from soulstrike.session import Session, SlotSetup
    g = _game()
    g.session = Session("cpu", [SlotSetup(1, char=a, cpu=True), SlotSetup(2, char=b, cpu=True)], difficulty=difficulty)
    m = BattleMatch(g, g.session)
    frames = 0
    while m.rounds_played == 0 and frames < 5000:
        m.step()
        m.frame += 1
        frames += 1
    win = [s for s, w in m.wins.items() if w]
    return {"chars": [f.stats.key for f in m.fighters], "winner": win[0].stats.key if win else None,
            "ko": m.loser is not None, "frames": frames}


def _ball_game(args):
    mode, chars, seed = args
    random.seed(seed)
    from soulstrike.basketball import BasketballMatch
    from soulstrike.data import CHARACTERS
    from soulstrike.matches import SoccerMatch
    from soulstrike.session import Session, SlotSetup
    g = _game()
    g.session = Session(mode, [SlotSetup(i + 1, char=c, cpu=True) for i, c in enumerate(chars)])
    m = (BasketballMatch if mode == "basket2" else SoccerMatch)(g, g.session)
    frames = 0
    while not m.finished and frames < MAX_FRAMES:
        m.step()
        m.frame += 1
        frames += 1
    if mode == "basket2":
        made = {f.stats.key: f.points for f in m.fighters}
    else:
        made = {f.stats.key: f.goals for f in m.fighters}
    return {"chars": [CHARACTERS[c].key for c in chars], "score": list(m.score), "frames": frames, "made": made}


def duel(games, difficulty, workers):
    from soulstrike.data import CHARACTERS
    duelists = [i for i, c in enumerate(CHARACTERS) if not c.soccer_only]
    jobs = []
    for i, a in enumerate(duelists):
        for b in duelists[i + 1:]:
            for r in range(games):
                jobs.append((a, b, difficulty) if r % 2 == 0 else (b, a, difficulty))
    with ProcessPoolExecutor(workers) as pool:
        rounds = list(pool.map(_duel_round, jobs, chunksize=8))
    played, won = collections.Counter(), collections.Counter()
    for r in rounds:
        played.update(r["chars"])
        if r["winner"]:
            won[r["winner"]] += 1
    print(f"{len(rounds)} rounds, CPU {difficulty}; round médio de "
          f"{statistics.mean(r['frames'] for r in rounds) / 60:.0f} s, {sum(not r['ko'] for r in rounds)} no tempo")
    for key in sorted(played, key=lambda k: -won[k] / played[k]):
        rate = won[key] / played[key]
        print(f"  {key:18s} {100 * rate:5.1f}%  {'#' * round(rate * 40)}")


def ball(mode, games, seed, workers):
    from soulstrike.data import CHARACTERS, UNLOCKABLES
    pool_chars = [i for i, c in enumerate(CHARACTERS) if c.key not in UNLOCKABLES]
    rng = random.Random(seed)
    n = 2 if mode == "soccer1" else 4
    jobs = [(mode, rng.sample(pool_chars, n), seed + k) for k in range(games)]
    with ProcessPoolExecutor(workers) as pool:
        results = list(pool.map(_ball_game, jobs))
    gaps = [abs(r["score"][0] - r["score"][1]) for r in results]
    print(f"{len(results)} jogos; duração média {statistics.mean(r['frames'] for r in results) / 3600:.2f} min; "
          f"placar médio {statistics.mean(sum(r['score']) for r in results):.1f}; diferença média {statistics.mean(gaps):.1f}")
    if mode == "basket2":
        print(f"  lavadas (15+ pontos): {sum(g >= 15 for g in gaps)}   decididos por 4 ou menos: {sum(g <= 4 for g in gaps)}")
    made = collections.defaultdict(list)
    for r in results:
        for key, value in r["made"].items():
            made[key].append(value)
    unit = "pontos" if mode == "basket2" else "gols"
    print(f"  {unit} por jogo:")
    for key in sorted(made, key=lambda k: -statistics.mean(made[k])):
        print(f"  {key:12s} {statistics.mean(made[key]):6.1f}  (em {len(made[key])} jogos)")


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("modo", choices=("duelo",) + tuple(MODES))
    parser.add_argument("--jogos", type=int, default=None, help="duelo: rounds por dupla (10); bola: partidas (40)")
    parser.add_argument("--dificuldade", default="dificil", choices=("facil", "normal", "dificil"))
    parser.add_argument("--semente", type=int, default=1)
    parser.add_argument("--processos", type=int, default=os.cpu_count() or 2)
    args = parser.parse_args()
    random.seed(args.semente)
    if args.modo == "duelo":
        duel(args.jogos or 10, args.dificuldade, args.processos)
    else:
        ball(MODES[args.modo], args.jogos or 40, args.semente, args.processos)


if __name__ == "__main__":
    main()
