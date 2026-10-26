"""Comportamento da CPU no duelo e no futebol."""
import math
import random

from . import config
from .entities import hostile

DIFFICULTIES = {
    "facil": {"label": "FÁCIL", "reaction": 14, "scatter": 0.35, "fire": 0.35,
              "dash": 0.01, "ability": 0.05, "dodge": 0.0, "range": 260},
    "normal": {"label": "NORMAL", "reaction": 7, "scatter": 0.18, "fire": 0.6,
               "dash": 0.03, "ability": 0.12, "dodge": 0.25, "range": 220},
    "dificil": {"label": "DIFÍCIL", "reaction": 3, "scatter": 0.06, "fire": 0.85,
                "dash": 0.05, "ability": 0.2, "dodge": 0.6, "range": 200},
}
DIFFICULTY_ORDER = ("facil", "normal", "dificil")

# CPU do futebol e do basquete: speed = velocidade, press = vontade de roubar/dar toco,
# power = vontade de usar o SUPER, aim = erro da mira no gol (px), shoot = de onde chuta,
# hit = acerto da barrinha do arremesso (meia distância, de 3)
BALL_DIFFICULTIES = {
    "facil": {"speed": 0.9, "press": 0.5, "power": 0.5, "aim": 80, "shoot": 460, "hit": (0.6, 0.35)},
    "normal": {"speed": 1.0, "press": 1.0, "power": 1.0, "aim": 50, "shoot": 540, "hit": (0.8, 0.55)},
    "dificil": {"speed": 1.05, "press": 1.6, "power": 1.5, "aim": 30, "shoot": 600, "hit": (0.92, 0.75)},
}


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
        self.preferred = None         # arma escolhida na seleção (volta para ela depois de recarregar)

    def update(self, me, target, match):
        if self.preferred is None:
            self.preferred = me.weapon_index
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

        self._manage_weapon(me, match, dist)
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
        mate = self._downed_mate(me, match)
        reviving = mate is not None and (dist > 170 or blocked)
        if reviving:
            # 2 x 2: vai levantar o companheiro caído (e continua atirando de lá)
            mx, my = mate.x - me.x, mate.y - me.y
            d = math.hypot(mx, my) or 1
            self.move = (mx / d, my / d) if d > 22 else (0.0, 0.0)
        elif item is not None:
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
        elif random.random() < cfg["dash"] and not reviving:
            if me.dash((ax, ay) if dist > 200 else (-ax, -ay)):
                match.assets.play("dash", 0.3)

    def _manage_weapon(self, me, match, dist):
        """Sem munição e com o inimigo colado: troca para a arma de perto enquanto recarrega;
        pente cheio de novo: volta para a arma de tiro (a não ser que ainda esteja colado)."""
        if not me.mag or len(me.weapons) < 2:
            return
        ranged_out = me.reloading or me.ammo <= 0
        if not me.weapon.is_melee and ranged_out and dist < 130:
            if me.switch_weapon():
                match.assets.play("click", 0.3)
        elif (me.weapon.is_melee and not me.weapons[self.preferred].is_melee and not ranged_out
              and dist > 110):
            if me.switch_weapon():
                match.assets.play("click", 0.3)

    @staticmethod
    def _downed_mate(me, match):
        can_revive = getattr(match, "can_revive", None)
        if can_revive is None or me.team is None:
            return None
        mates = [f for f in match.fighters if f is not me and f.team == me.team and can_revive(f)]
        return min(mates, key=me.distance_to) if mates else None

    @staticmethod
    def _wanted_pickup(me, target, match):
        best, best_d = None, 360
        for item in getattr(match, "pickups", ()):
            if item.kind == "vida" and me.hp > me.max_hp * 0.75:
                continue
            if item.kind == "energia" and me.ability_ready:
                continue
            if item.kind == "municao" and (not me.mag or me.ammo >= me.mag // 2 and not me.reloading):
                continue
            d = math.hypot(item.x - me.x, item.y - me.y)
            rival = math.hypot(item.x - target.x, item.y - target.y)
            if d < best_d and d < rival + 80:
                best, best_d = item, d
        return best

    @staticmethod
    def _incoming(me, match):
        for b in match.bullets:
            if not hostile(b.owner, me):
                continue
            rx, ry = me.x - b.x, me.y - b.y
            dist = math.hypot(rx, ry)
            speed = math.hypot(b.vx, b.vy) or 1
            if dist < 140 and (rx * b.vx + ry * b.vy) / (dist * speed + 1e-6) > 0.9:
                return b.vx / speed, b.vy / speed
        return None




class SoccerAI:
    """Jogador de futebol controlado pela CPU."""

    def __init__(self, difficulty="normal"):
        self.cfg = BALL_DIFFICULTIES.get(difficulty, BALL_DIFFICULTIES["normal"])
        self.aim_y = None
        self.swerve = random.choice((-1, 1))
        self.wing = None          # no 2x2, às vezes abre pela ponta para cruzar (lado: -1 ou 1)
        self.had_ball = False
        self.wing_wait = 0

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
            aim = self.cfg["aim"]
            self.aim_y = mid_y + random.choice((-aim, 0, aim))
        mates = [f for f in match.fighters if f.team == me.team and f is not me]
        foes = [f for f in match.fighters if f.team != me.team]
        near = lambda f: math.hypot(f.x - ball.x, f.y - ball.y) < 40
        dist_ball = math.hypot(me.x - ball.x, me.y - ball.y)
        # corre quando vale a pena e tem fôlego: bola solta longe ou adversário perto do meu gol
        owner = match.possessor
        loose_far = owner is None and dist_ball > 220 and me.stamina > 0.4
        danger = (owner is not None and owner.team != me.team and abs(ball.x - home_x) < 650
                  and dist_ball > 120 and me.stamina > 0.3)
        me.sprint_held = loose_far or danger

        if match.possessor is me:
            if not self.had_ball:
                # pegou a bola agora: decide se vai abrir pela ponta
                self.had_ball = True
                self.wing_wait = 0
                self.wing = None
                if mates and random.random() < 0.3:
                    self.wing = 1 if me.y > mid_y else -1
            self._carry(me, match, attack_x, mid_y, mates, foes)
            return
        self.had_ball = False
        if self._defend(me, match, home_x, mid_y):
            return
        if ball.airborne and match.possessor is None:
            # bola no ar: corre para onde ela vai estar na altura da cabeça (ou cair)
            apex = ball.z + max(0.0, ball.vz) ** 2 / (2 * config.GRAVITY)
            if apex >= config.CROSS_HEIGHT:
                lx, ly, _ = ball.descending_point(config.CROSS_HEIGHT)
            else:
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
        going_wide = (owner is not None and owner.team == me.team
                      and abs(attack_x - owner.x) < match.arena.width * 0.5
                      and abs(owner.y - mid_y) >= 170)
        if going_wide:
            # companheiro na ponta: entra na área para receber o cruzamento (no segundo pau)
            fwd = 1 if attack_x > me.x else -1
            side = 1 if owner.y < mid_y else -1
            tx, ty = attack_x - fwd * 180, mid_y + side * 50
            me.sprint_held = me.stamina > 0.2
        elif owner is not None and owner.team == me.team:
            # companheiro com a bola: abre espaço à frente dele
            tx, ty = (owner.x + attack_x) / 2, mid_y + (me.slot % 2 * 2 - 1) * 190
        elif owner is not None and mates and min(mates, key=lambda m: m.distance_to(ball)).distance_to(ball) < dist_ball:
            # o companheiro pressiona; eu fecho o caminho do gol
            tx, ty = (ball.x + home_x) / 2, (ball.y + mid_y) / 2
        elif owner is not None:
            # pressiona por dentro, entre a bola e o meu gol
            gx, gy = home_x - ball.x, mid_y - ball.y
            g = math.hypot(gx, gy) or 1
            tx, ty = ball.x + gx / g * 14, ball.y + gy / g * 14
            if dist_ball < 40 and me.dash_cd <= 0 and random.random() < 0.04 * self.cfg["press"]:
                match.cut(me, ((ball.x - me.x) / (dist_ball or 1), (ball.y - me.y) / (dist_ball or 1)))
        elif any(near(f) for f in mates):
            tx, ty = attack_x, mid_y + (me.slot % 2 * 2 - 1) * 170
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
        chance = (0.35 if me.power.needs_ball and match.touching(me, 20) else 0.06) * self.cfg["power"]
        if me.super_cd <= 0 and random.random() < chance and me.power.worth_using(me, match):
            match.use_power(me)

    def _defend(self, me, match, home_x, mid_y):
        """Bola solta vindo para o meu gol: chutão ou carrinho de bloqueio."""
        ball = match.ball
        if not match.can_clear(me):
            return False
        speed = math.hypot(ball.vx, ball.vy)
        toward_goal = ball.vx * (home_x - ball.x) > 0 and speed > 3
        pressed = abs(ball.x - home_x) < 420 and any(
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
        if self.wing is not None:
            fwd = 1 if attack_x > me.x else -1
            if match.in_cross_position(me):
                # na ponta: cruza quando o companheiro entra na área; se demorar, corta para dentro
                self.wing_wait += 1
                if match.cross_receiver(me, mates) is not None and random.random() < 0.2:
                    if match.pass_ball(me, high=random.random() < 0.65):
                        self.wing = None
                        return
                if self.wing_wait > 110:
                    self.wing = None                     # ninguém chegou: volta ao jogo normal
                else:
                    aim = (fwd * 0.4, -self.wing * 0.3)  # segura na ponta, sem fugir do campo
                    m = math.hypot(*aim)
                    aim = (aim[0] / m, aim[1] / m)
            else:
                wx, wy = attack_x - fwd * 340 - me.x, mid_y + self.wing * 340 - me.y
                w = math.hypot(wx, wy) or 1
                aim = (wx / w, wy / w)
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
        me.sprint_held = blocker is None and me.stamina > 0.5 and abs(attack_x - me.x) > 380
        me.steer(*move)
        if me.super_cd <= 0 and random.random() < 0.08 * self.cfg["power"] and me.power.worth_using(me, match):
            if match.use_power(me):
                return
        if self.wing is not None:
            return                                   # indo para a ponta: ainda não chuta
        near_goal = abs(attack_x - me.x)
        # na ponta, com companheiro entrando na área: cruza
        if near_goal < 600 and match.in_cross_position(me) and random.random() < 0.12:
            if match.cross_receiver(me, mates) is not None and match.pass_ball(me, high=random.random() < 0.65):
                return
        if near_goal < self.cfg["shoot"]:
            me.facing = aim
            # marcador colado na frente: tenta encobrir
            loft = 0.25 if blocker is not None and me.distance_to(blocker) < 80 and near_goal > 280 else 0.0
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


class BasketballAI:
    """Jogador de basquete controlado pela CPU: leva a bola para a cesta, arremessa quando está
    livre ou perto, passa quando é apertado e, sem a bola, marca ou se desmarca."""

    def __init__(self, difficulty="normal"):
        self.cfg = BALL_DIFFICULTIES.get(difficulty, BALL_DIFFICULTIES["normal"])
        self.wait = random.randint(10, 30)      # quadros com a bola antes de pensar em arremessar
        self.had_ball = False
        self.lane = random.choice((-1, 1))      # para que lado abre quando o companheiro tem a bola
        self.release_at = 20

    def _release_frame(self, me, three, jump_frames):
        """Quando soltar a barrinha: a CPU acerta o tempo na maioria das vezes, menos no de 3."""
        half = me.shot_half
        if random.random() < self.cfg["hit"][1 if three else 0]:
            t = 0.5 + random.uniform(-0.8, 0.8) * half
        else:
            t = 0.5 + random.choice((-1, 1)) * (half + random.uniform(0.03, 0.2))
        return max(2, min(jump_frames, round(t * jump_frames)))

    def update(self, me, match):
        from .arena import Court
        from .basket_assist import JUMP_FRAMES
        from .basketball import DUNK_RANGE
        if match.freeze or match.ending:
            me.steer(0, 0)
            return
        ball = match.ball
        owner = match.holder
        if me.jump_shot and owner is me:
            if me.jump >= self.release_at:
                match.release_shot(me)
            return
        power = me.power
        if (power is not None and me.super_cd <= 0 and not me.dunking and random.random() < 0.05 * self.cfg["power"]
                and power.worth_using(me, match) and match.use_power(me)):
            return
        side = match.hoop_of(me.team)
        hx, hy = match.hoop_pos(side)
        home_x, _ = match.hoop_pos(1 - side)
        dist_ball = math.hypot(ball.x - me.x, ball.y - me.y)
        me.sprint_held = dist_ball > 260 and me.stamina > 0.35

        if owner is me:
            if not self.had_ball:
                self.had_ball = True
                self.wait = random.randint(10, 30)
            self.wait -= 1
            dist = math.hypot(hx - me.x, hy - me.y)
            foes = match.foes_of(me)
            pressure = min((math.hypot(f.x - me.x, f.y - me.y) for f in foes), default=999)
            close = Court.in_key(side, me.x, me.y) and dist < DUNK_RANGE
            three = Court.is_three(side, me.x, me.y)
            open_shot = (pressure > 110 and dist < 620) or (pressure > 75 and not three and dist < 420)
            mates = match.mates_of(me)
            blocked = any(_off_lane(f, me, _Spot(hx, hy)) < 50 and f.distance_to(_Spot(hx, hy)) < dist
                          for f in foes)
            if close and blocked and mates and random.random() < 0.05:
                mate = mates[0]
                if all(_off_lane(f, me, mate) > 50 for f in foes):      # garrafão fechado: toca
                    match.pass_ball(me, (mate.x - me.x, mate.y - me.y))
                    return
            late = match.shot_clock > 7 * config.FPS
            if self.wait <= 0 and (close or open_shot or late):
                if match.start_shot(me) and me.jump_shot:
                    self.release_at = self._release_frame(me, Court.is_three(side, me.x, me.y), JUMP_FRAMES)
                return
            if pressure < 45 and random.random() < 0.025:
                match.feint(me)
                return
            if mates and pressure < 50 and random.random() < 0.04:
                mate = mates[0]
                if all(_off_lane(f, me, mate) > 50 for f in foes):      # só passa com a linha livre
                    match.pass_ball(me, (mate.x - me.x, mate.y - me.y))
                    return
            # leva a bola para o garrafão, desviando um pouco de quem marca
            tx, ty = hx + (90 if side == 0 else -90), hy + self.lane * 30
            dx, dy = tx - me.x, ty - me.y
            d = math.hypot(dx, dy) or 1
            mx, my = dx / d, dy / d
            if pressure < 70:
                mx, my = mx - my * 0.5 * self.lane, my + mx * 0.5 * self.lane
            me.steer(mx, my)
            me.sprint_held = me.stamina > 0.3 and dist > 300
            return
        self.had_ball = False
        if not me.jump and not me.dunking:
            if owner is not None and owner.team != me.team:
                d = me.distance_to(owner)
                if owner.jump_shot and not owner.pushed and d < 120 and random.random() < 0.04 * self.cfg["press"]:
                    match.steal(me, (owner.x - me.x, owner.y - me.y))   # empurrão no arremesso
                    return
                if (owner.jump_shot or owner.dunking) and d < 80 and random.random() < 0.12 * self.cfg["press"]:
                    match.jump(me)              # toco
                    return
                if d < 60 and not owner.jump and random.random() < 0.006 * self.cfg["press"]:
                    match.steal(me)
            elif (owner is None and match.shot is not None and match.shot.get("touched")
                  and dist_ball < 40 and 40 < ball.z < 110 and random.random() < 0.2):
                match.jump(me)                  # rebote no alto

        if owner is None:
            # bola solta: vai até onde ela vai cair
            tx, ty = ball.x + ball.vx * 10, ball.y + ball.vy * 10
            mates = match.mates_of(me)
            closer = [m for m in mates if math.hypot(ball.x - m.x, ball.y - m.y) < dist_ball - 40]
            if closer and match.shot is not None and match.shot["team"] != me.team:
                tx, ty = (ball.x + home_x) / 2, (ball.y + hy) / 2      # o companheiro pega: eu volto
        elif owner.team == me.team:
            # companheiro com a bola: abre na ala, perto da linha de 3
            fwd = 1 if side == 1 else -1
            tx, ty = hx - fwd * 380, hy + self.lane * 260
        else:
            # defesa: marca quem tem a bola ou o outro atacante, entre ele e a minha cesta
            mates = match.mates_of(me)
            mine = owner
            if mates and math.hypot(owner.x - mates[0].x, owner.y - mates[0].y) < math.hypot(owner.x - me.x, owner.y - me.y):
                others = [f for f in match.foes_of(me) if f is not owner]
                if others:
                    mine = others[0]
            ux, uy = home_x - mine.x, hy - mine.y
            u = math.hypot(ux, uy) or 1
            tx, ty = mine.x + ux / u * 46, mine.y + uy / u * 46
            me.sprint_held = me.sprint_held or (math.hypot(tx - me.x, ty - me.y) > 160 and me.stamina > 0.3)
        dx, dy = tx - me.x, ty - me.y
        d = math.hypot(dx, dy)
        if d > 10:
            me.steer(dx / d, dy / d)
        else:
            me.steer(0, 0)
            me.face(ball)


def _off_lane(p, a, b):
    """Distância de p até o segmento de a até b (quem está no caminho do passe)."""
    dx, dy = b.x - a.x, b.y - a.y
    L = dx * dx + dy * dy or 1
    t = max(0.0, min(1.0, ((p.x - a.x) * dx + (p.y - a.y) * dy) / L))
    return math.hypot(a.x + dx * t - p.x, a.y + dy * t - p.y)


class _Spot:
    """Um ponto com x e y, para as contas de distância (o aro, por exemplo)."""

    def __init__(self, x, y):
        self.x, self.y = x, y
