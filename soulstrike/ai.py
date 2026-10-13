"""Comportamento da CPU no duelo e no futebol."""
import math
import random

from . import config

DIFFICULTIES = {
    "facil": {"label": "FÁCIL", "reaction": 14, "scatter": 0.35, "fire": 0.35,
              "dash": 0.01, "ability": 0.05, "dodge": 0.0, "range": 260},
    "normal": {"label": "NORMAL", "reaction": 7, "scatter": 0.18, "fire": 0.6,
               "dash": 0.03, "ability": 0.12, "dodge": 0.25, "range": 220},
    "dificil": {"label": "DIFÍCIL", "reaction": 3, "scatter": 0.06, "fire": 0.85,
                "dash": 0.05, "ability": 0.2, "dodge": 0.6, "range": 200},
}
DIFFICULTY_ORDER = ("facil", "normal", "dificil")


class FighterAI:
    """Decide a cada poucos quadros (tempo de reação) e aplica a decisão em todos os quadros."""

    def __init__(self, difficulty="normal"):
        self.cfg = DIFFICULTIES[difficulty]
        self.tick = 0
        self.move = (0.0, 0.0)
        self.firing = False
        self.strafe = random.choice((-1, 1))
        self.last_pos = None
        self.detour = 0

    def update(self, me, target, match):
        if target is None or not target.alive_in_match:
            me.steer(0, 0)
            return
        self.tick += 1
        if self.tick >= self.cfg["reaction"]:
            self.tick = 0
            self._decide(me, target, match)
        me.steer(*self.move)
        if self.firing:
            me.attack(match, target)

    def _decide(self, me, target, match):
        cfg = self.cfg
        dx, dy = target.x - me.x, target.y - me.y
        dist = math.hypot(dx, dy) or 1
        ax = dx / dist + random.uniform(-cfg["scatter"], cfg["scatter"])
        ay = dy / dist + random.uniform(-cfg["scatter"], cfg["scatter"])
        mag = math.hypot(ax, ay) or 1
        ax, ay = ax / mag, ay / mag

        weapon = me.weapon
        ideal = weapon.reach * 0.7 if weapon.is_melee else cfg["range"]
        blocked = match.arena.blocks_segment((me.x, me.y), (target.x, target.y))

        # tentou andar e não saiu do lugar: contorna pelo outro lado
        if self.last_pos and any(self.move):
            if abs(me.x - self.last_pos[0]) + abs(me.y - self.last_pos[1]) < 1.5:
                self.strafe = -self.strafe
                self.detour = 40
        self.last_pos = (me.x, me.y)
        if random.random() < 0.04:
            self.strafe = -self.strafe

        side = (-ay * self.strafe, ax * self.strafe)
        item = self._wanted_pickup(me, target, match)
        if item is not None:
            # vai buscar o item (vida quando está machucado, fúria/energia quando está perto)
            ix, iy = item.x - me.x, item.y - me.y
            d = math.hypot(ix, iy) or 1
            self.move = (ix / d, iy / d)
        elif blocked or self.detour > 0:
            # sem visão do alvo: anda de lado para contornar a parede
            self.detour = max(0, self.detour - cfg["reaction"])
            mx, my = side[0] + ax * 0.35, side[1] + ay * 0.35
            m = math.hypot(mx, my) or 1
            self.move = (mx / m, my / m)
        elif dist > ideal + 50:
            self.move = (ax, ay)
        elif dist < ideal - 50 and not weapon.is_melee:
            self.move = (-ax, -ay)
        else:
            self.move = side

        reach = weapon.reach + 20 if weapon.is_melee else 460
        self.firing = dist < reach and not blocked and random.random() < cfg["fire"]

        if me.ability_ready and random.random() < cfg["ability"] and me.ability.worth_using(me, target, dist):
            me.use_ability(match, target)

        threat = self._incoming(me, match)
        if threat and random.random() < cfg["dodge"]:
            bx, by = threat
            if me.dash((-by, bx) if random.random() < 0.5 else (by, -bx)):
                match.assets.play("dash", 0.3)
        elif random.random() < cfg["dash"]:
            if me.dash((ax, ay) if dist > 200 else (-ax, -ay)):
                match.assets.play("dash", 0.3)

    @staticmethod
    def _wanted_pickup(me, target, match):
        best, best_d = None, 360
        for item in getattr(match, "pickups", ()):
            if item.kind == "vida" and me.hp > me.stats.max_hp * 0.75:
                continue
            if item.kind == "energia" and me.ability_ready:
                continue
            d = math.hypot(item.x - me.x, item.y - me.y)
            rival = math.hypot(item.x - target.x, item.y - target.y)
            if d < best_d and d < rival + 80:
                best, best_d = item, d
        return best

    @staticmethod
    def _incoming(me, match):
        for b in match.bullets:
            if b.owner is me:
                continue
            rx, ry = me.x - b.x, me.y - b.y
            dist = math.hypot(rx, ry)
            speed = math.hypot(b.vx, b.vy) or 1
            if dist < 140 and (rx * b.vx + ry * b.vy) / (dist * speed + 1e-6) > 0.9:
                return b.vx / speed, b.vy / speed
        return None


class SoccerAI:
    """Jogador de futebol controlado pela CPU."""

    def __init__(self):
        self.aim_y = None
        self.swerve = random.choice((-1, 1))

    def update(self, me, match):
        ball = match.ball
        if match.freeze > 0 or match.ending:
            me.steer(0, 0)
            self.aim_y = None
            return
        attack_x = match.goal_x(1 - me.team)    # gol adversário
        home_x = match.goal_x(me.team)
        mid_y = match.arena.height / 2
        if self.aim_y is None or random.random() < 0.01:
            self.aim_y = mid_y + random.choice((-50, 0, 50))
        mates = [f for f in match.fighters if f.team == me.team and f is not me]
        foes = [f for f in match.fighters if f.team != me.team]
        near = lambda f: math.hypot(f.x - ball.x, f.y - ball.y) < 40
        dist_ball = math.hypot(me.x - ball.x, me.y - ball.y)
        # corre quando vale a pena e tem fôlego: bola solta longe ou adversário perto do meu gol
        owner = match.possessor
        loose_far = owner is None and dist_ball > 180 and me.stamina > 0.4
        danger = (owner is not None and owner.team != me.team and abs(ball.x - home_x) < 500
                  and dist_ball > 120 and me.stamina > 0.3)
        me.sprint_held = loose_far or danger

        if match.possessor is me:
            self._carry(me, match, attack_x, mid_y, mates, foes)
            return
        if self._defend(me, match, home_x, mid_y):
            return
        if ball.airborne and match.possessor is None:
            # bola no ar: corre para onde ela vai cair (ou cabeceia)
            lx, ly, _ = ball.landing()
            dx, dy = lx - me.x, ly - me.y
            d = math.hypot(dx, dy)
            if d > 8:
                me.steer(dx / d, dy / d)
            else:
                me.steer(0, 0)
            if match.can_head(me):
                gx, gy = attack_x - me.x, self.aim_y - me.y
                g = math.hypot(gx, gy) or 1
                match.header(me, (gx / g, gy / g))
            return
        owner = match.possessor
        if owner is not None and owner.team == me.team:
            # companheiro com a bola: abre espaço à frente dele
            tx, ty = (owner.x + attack_x) / 2, mid_y + (me.slot % 2 * 2 - 1) * 140
        elif owner is not None and mates and min(mates, key=lambda m: m.distance_to(ball)).distance_to(ball) < dist_ball:
            # o companheiro pressiona; eu fecho o caminho do gol
            tx, ty = (ball.x + home_x) / 2, (ball.y + mid_y) / 2
        elif owner is not None:
            # pressiona por dentro, entre a bola e o meu gol
            gx, gy = home_x - ball.x, mid_y - ball.y
            g = math.hypot(gx, gy) or 1
            tx, ty = ball.x + gx / g * 14, ball.y + gy / g * 14
            if dist_ball < 40 and me.dash_cd <= 0 and random.random() < 0.04:
                match.cut(me, ((ball.x - me.x) / (dist_ball or 1), (ball.y - me.y) / (dist_ball or 1)))
        elif any(near(f) for f in mates):
            tx, ty = attack_x, mid_y + (me.slot % 2 * 2 - 1) * 120
        elif any(near(f) for f in foes) and dist_ball > 60:
            tx, ty = (ball.x + home_x) / 2, (ball.y + mid_y) / 2
        else:
            # chega por trás da bola, de frente para o gol adversário
            gx, gy = attack_x - ball.x, self.aim_y - ball.y
            g = math.hypot(gx, gy) or 1
            tx, ty = ball.x - gx / g * 22, ball.y - gy / g * 22
        dx, dy = tx - me.x, ty - me.y
        d = math.hypot(dx, dy)
        if d > 6:
            me.steer(dx / d, dy / d)
        else:
            me.steer(0, 0)
        me.dribbling = me.sprint_timer > 0
        chance = 0.35 if me.power.needs_ball and match.touching(me, 20) else 0.06
        if me.super_cd <= 0 and random.random() < chance and me.power.worth_using(me, match):
            match.use_power(me)

    def _defend(self, me, match, home_x, mid_y):
        """Bola solta vindo para o meu gol: chutão ou carrinho de bloqueio."""
        ball = match.ball
        if not match.can_clear(me):
            return False
        speed = math.hypot(ball.vx, ball.vy)
        toward_goal = ball.vx * (home_x - ball.x) > 0 and speed > 3
        pressed = abs(ball.x - home_x) < 320 and any(
            f.distance_to(ball) < 120 for f in match.foes_of(me))
        if (toward_goal or pressed) and match.touching(me, config.CLEAR_REACH, max_z=config.HEAD_RANGE[1]):
            if random.random() < 0.6 and match.clear_ball(me):
                return True
        if toward_goal and speed > 6 and me.dash_cd <= 0 and random.random() < 0.05:
            # entre a bola e o gol? então vale o carrinho
            if (me.x - ball.x) * (home_x - me.x) > 0 and match.incoming(me, reach=60):
                match.cut(me)
                return True
        return False

    def _carry(self, me, match, attack_x, mid_y, mates, foes):
        """Com a bola: conduz rumo ao gol, desvia de quem marca, passa ou chuta."""
        gx, gy = attack_x - me.x, self.aim_y - me.y
        g = math.hypot(gx, gy) or 1
        aim = (gx / g, gy / g)
        blocker = None
        for f in foes:
            d = me.distance_to(f)
            if d < 110 and ((f.x - me.x) * aim[0] + (f.y - me.y) * aim[1]) > 0.5 * d:
                blocker = f
        move = aim
        if blocker is not None:
            a = math.atan2(aim[1], aim[0]) + self.swerve * math.radians(60)
            move = (math.cos(a), math.sin(a))
            if random.random() < 0.03:
                self.swerve = -self.swerve
        me.dribbling = me.sprint_timer > 0 or blocker is not None
        # campo aberto: arranca com a bola
        me.sprint_held = blocker is None and me.stamina > 0.5 and abs(attack_x - me.x) > 300
        me.steer(*move)
        if me.super_cd <= 0 and random.random() < 0.08 and me.power.worth_using(me, match):
            if match.use_power(me):
                return
        near_goal = abs(attack_x - me.x)
        if near_goal < 420:
            me.facing = aim
            # marcador colado na frente: tenta encobrir
            loft = 0.25 if blocker is not None and me.distance_to(blocker) < 80 and near_goal > 220 else 0.0
            match.kick(me, aim, loft=loft)
        elif blocker is not None and me.distance_to(blocker) < 45:
            open_mates = [m for m in mates if abs(attack_x - m.x) < abs(attack_x - me.x) + 80]
            if open_mates and random.random() < 0.5:
                # marcador entre mim e o companheiro → passe por cima
                mate = min(open_mates, key=me.distance_to)
                over = _between(blocker, me, mate)
                match.pass_ball(me, high=over)
            elif random.random() < 0.15:
                me.facing = move
                match.kick(me, move, loft=0.4 if random.random() < 0.5 else 0.0)


def _between(blocker, a, b):
    """O marcador está no caminho entre a e b?"""
    abx, aby = b.x - a.x, b.y - a.y
    length2 = abx * abx + aby * aby or 1
    t = ((blocker.x - a.x) * abx + (blocker.y - a.y) * aby) / length2
    if not 0 < t < 1:
        return False
    px, py = a.x + abx * t, a.y + aby * t
    return math.hypot(blocker.x - px, blocker.y - py) < 40
