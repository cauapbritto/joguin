"""Simula masmorras da campanha com robôs no lugar dos jogadores, em cada dificuldade.

    python tools/simular_campanha.py                       # 4 jogadores, todas as dificuldades
    python tools/simular_campanha.py --jogadores 2 --vezes 4
    python tools/simular_campanha.py --dificuldades borba --fases 2 8

Cada robô anda até o inimigo mais perto (sem colar), segura ATACAR com a arma rara da fase,
usa a habilidade, esquiva de vez em quando e levanta quem caiu. Robô não joga igual gente: os
números servem para comparar uma dificuldade com a outra e o antes e depois de uma mudança.
"""
import argparse
import math
import os
import random
import statistics
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "tests"))
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

MAX_FRAMES = 60 * 60 * 6                 # 6 minutos por masmorra
CHARS = ("guerreiro", "atirador", "ninja", "tanque")


class Robo:
    def __init__(self, fake):
        self.fake = fake
        self.side = random.choice((-1, 1))
        self.t = random.randrange(60)

    def think(self, me, match):
        f = self.fake
        f.end_frame()
        f.release("attack", "special", "dodge")
        self.t += 1
        if not me.alive_in_match:
            f.stick = (0.0, 0.0)
            return
        spot = self._chore(me, match)        # capítulo 4: tomada do chefe e no-breaks do CPD
        if spot is not None:
            dx, dy = spot[0] - me.x, spot[1] - me.y
            n = math.hypot(dx, dy) or 1
            f.stick = (dx / n, dy / n) if n > 40 else (0.0, 0.0)
            if n <= 60 and self.t % 2 == 0:
                f.tap("attack")
            return
        down = [p for p in match.players if not p.alive_in_match]
        enemies = match.fighting_enemies() if hasattr(match, "fighting_enemies") else match.alive_enemies
        target = min(enemies, key=me.distance_to) if enemies else None
        if down and (target is None or target.distance_to(down[0]) > 160):
            d = down[0]
            dx, dy = d.x - me.x, d.y - me.y
            n = math.hypot(dx, dy) or 1
            f.stick = (dx / n, dy / n) if n > 30 else (0.0, 0.0)
            return
        if target is None:
            f.stick = (0.0, 0.0)
            return
        dx, dy = target.x - me.x, target.y - me.y
        n = math.hypot(dx, dy) or 1
        want = 70 if me.weapon.is_melee or getattr(me, "bash_timer", 0) > 0 else 230
        if self.t % 180 == 0:
            self.side = -self.side
        go = 1 if n > want + 40 else -1 if n < want - 40 else 0
        sx, sy = dx / n * go - dy / n * 0.6 * self.side, dy / n * go + dx / n * 0.6 * self.side
        m = math.hypot(sx, sy) or 1
        f.stick = (sx / m, sy / m)
        f.hold("attack")
        # como gente: sem energia para a rara, troca para a arma do herói; com a barra boa, volta
        energy = getattr(me, "energy", None)
        if energy is not None and me.relic is not None:
            from soulstrike.energia import cost
            price = cost(me, me.relic)
            on_relic = me.weapon is me.relic
            if (on_relic and energy < price) or (not on_relic and energy >= max(60, price * 4)):
                if self.t % 20 == 0:
                    f.tap("switch")
        if self.t % 240 == 0:
            f.hold("special")
        if random.random() < 0.01:
            f.hold("dodge")


    def _chore(self, me, match):
        boss = getattr(match, "boss", None)
        brain = match.controllers.get(boss) if boss is not None else None
        plug = getattr(brain, "plug", None)
        if plug is not None and not plug.pulled:
            return plug.x, plug.y
        hazard = getattr(match, "hazard", None)
        boxes = getattr(hazard, "off_boxes", None) or []
        if boxes:
            enemies = match.alive_enemies
            if not enemies or min(me.distance_to(e) for e in enemies) > 260:
                b = min(boxes, key=lambda b: math.hypot(b.x - me.x, b.y - me.y))
                return b.x, b.y
        return None


def masmorra(difficulty, players, phase, stage, seed):
    from apoio import FakeInput, game
    from soulstrike.campaign import DUNGEON_1, DUNGEON_2, PHASES, CampaignMatch, CampaignRun
    from soulstrike.data import PHASE_RELICS
    from soulstrike.data import CHARACTERS
    from soulstrike.session import Session, SlotSetup
    random.seed(seed)
    keys = [c.key for c in CHARACTERS]
    g = game()
    g.session = Session("campaign", [SlotSetup(i + 1, char=keys.index(CHARS[i])) for i in range(players)],
                        difficulty=difficulty)
    run = CampaignRun(g.session)
    run.phase_index = phase
    run.begin_phase()
    run.stage = DUNGEON_2 if stage == 2 else DUNGEON_1
    relics = list(PHASE_RELICS[PHASES[phase].key])
    for k, s in enumerate(run.slots):
        run.relics[s] = relics[k % len(relics)]
        run.held[s] = 2
        run.upgrades[s] = random.sample(["vida", "dano", "recarga", "velocidade", "escudo"], min(3, phase))
    m = CampaignMatch(g, run)
    robos = {}
    for p in m.players:
        fake = FakeInput()
        m.controllers[p] = fake
        robos[p] = Robo(fake)
    downs = empty = 0
    was = set()
    start_cont = run.continues
    for frame in range(MAX_FRAMES):
        for p, r in robos.items():
            r.think(p, m)
            if p.alive_in_match and getattr(p, "energy", None) is not None and p.energy < 4:
                empty += 1
            if not p.alive_in_match and p not in was:
                downs += 1
            (was.add if not p.alive_in_match else was.discard)(p)
        m.update()
        if m.state in ("exit", "vote", "clear"):
            return "venceu", frame, downs, start_cont - run.continues, empty / max(1, frame * players)
        if m.state == "gameover":
            return "perdeu", frame, downs, start_cont - run.continues, empty / max(1, frame * players)
    return "tempo", MAX_FRAMES, downs, start_cont - run.continues, empty / max(1, MAX_FRAMES * players)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--jogadores", type=int, default=4)
    ap.add_argument("--vezes", type=int, default=2)
    ap.add_argument("--dificuldades", nargs="*", default=["facil", "normal", "dificil", "ibrahim", "borba"])
    ap.add_argument("--fases", nargs="*", type=int, default=[0, 5, 8])
    ap.add_argument("--masmorra", type=int, default=2)
    a = ap.parse_args()
    print(f"{a.jogadores} jogadores · fases {a.fases} · masmorra {a.masmorra} · {a.vezes}x cada", flush=True)
    print(f"{'dificuldade':12} {'vitórias':>9} {'tempo médio':>12} {'quedas':>7} {'continues':>10} {'sem energia':>12}")
    for diff in a.dificuldades:
        rows = [masmorra(diff, a.jogadores, ph, a.masmorra, 100 * ph + k)
                for ph in a.fases for k in range(a.vezes)]
        wins = sum(r[0] == "venceu" for r in rows)
        secs = statistics.mean(r[1] for r in rows) / 60
        print(f"{diff:12} {wins:>4}/{len(rows):<4} {secs:>10.0f} s {statistics.mean(r[2] for r in rows):>7.1f}"
              f" {statistics.mean(r[3] for r in rows):>10.1f} {100 * statistics.mean(r[4] for r in rows):>10.0f} %",
              flush=True)


if __name__ == "__main__":
    main()
