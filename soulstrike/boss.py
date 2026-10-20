"""O chefão da campanha: Aryel Corrompido.

Ele alterna golpes em sequência (chuva de bombas, anel de granadas, martelada com pulo e a
investida sombria) e depois de cada sequência fica CANSADO por um tempo: é a hora de bater.
Com metade da vida chama ajuda (com uma alma corrompida de herói); com 20% fica furioso, mais
rápido e ganha a armadura de sombra, que só quebra quando ele cansa.
"""
import math
import random

from . import theme
from .data import WeaponStats
from .enemies import SHADOW_AURA, SHADOW_RIM, EnemyAI, EnemyStats, Shockwave
from .entities import GroundMark, ShadowBomb

BOSS_STATS = EnemyStats(
    "aryel_corrompido", "Aryel Corrompido", 1500, 2.6, SHADOW_AURA,
    "Chuva Sombria", "Faz chover bombas sombrias em volta do alvo.",
    (WeaponStats("Granada", "ranged", 12, bullet_speed=10, cooldown=34),
     WeaponStats("Martelo", "melee", 24, reach=62, cooldown=40)), "aryel",
    radius=26, elite=True, armed=True, knock_resist=1.0, drop_chance=0.0)

SCALE = 1.7
ENRAGED_AURA = (170, 20, 40)
ARMOR = 0.35                 # furioso: a armadura de sombra segura boa parte do dano (menos quando cansa)
TIRED = 77                   # quadros CANSADO (antes 110)
SHADES = ("sombra:velocista", "sombra:ninja", "sombra:tanque")


def spawn_boss(match, x, y):
    from .fighter import Fighter
    f = Fighter(BOSS_STATS, 0, x, y, match.assets.shadow_sprites("aryel"), "ARYEL CORROMPIDO", SHADOW_AURA,
                team=1, weapon_index=0, is_cpu=True)
    f.radius = f.base_radius = BOSS_STATS.radius
    f.draw_scale = SCALE
    f.knock_resist = 1.0
    f.unstoppable = True
    f.overlay = "none"           # a vida aparece na barra grande do topo
    f.aura = SHADOW_RIM
    f.ring_color = SHADOW_RIM
    f.kind = "chefe"
    f.phase_label = ""
    return f, BossAI(match.session.difficulty, len(match.players))


class BossAI(EnemyAI):
    reaction = 6
    PATTERNS = ("rain", "ring", "jump", "dash")

    def __init__(self, difficulty="normal", players=1):
        super().__init__(difficulty)
        self.players = players
        self.state = "walk"
        self.timer = 110
        self.combo = []
        self.summoned = False
        self.enraged = False
        self.jump_from = self.jump_to = (0, 0)
        self.jump_frames = 0
        self.last_pattern = None
        self.dash_dir = (1.0, 0.0)
        self.dash_hit = set()

    # ── utilidades ───────────────────────────
    @property
    def speed(self):
        return (1.35 if self.enraged else 1.0) * self.aggression

    def _wait(self, frames):
        return max(8, round(frames / self.speed))

    def _set(self, me, state, frames):
        self.state = state
        self.timer = frames
        me.vulnerability = 1.6 if state == "tired" else ARMOR if self.enraged else 1.0
        me.phase_label = {"tired": "CANSADO! HORA DE ATACAR", "roar": "AS SOMBRAS ESTÃO VINDO"}.get(
            state, "ARMADURA DE SOMBRA: ESPERE ELE CANSAR" if self.enraged else "")

    def _new_combo(self):
        size = 4 if self.enraged else 3
        options = [p for p in self.PATTERNS if p != self.last_pattern]
        random.shuffle(options)
        combo = options[:size]
        while len(combo) < size:
            combo.append(random.choice(self.PATTERNS))
        return combo

    # ── cérebro ──────────────────────────────
    def update(self, me, match):
        if not me.alive_in_match:
            me.steer(0, 0)
            return
        ratio = me.hp / me.max_hp
        if not self.summoned and ratio <= 0.5 and self.state not in ("jump", "air"):
            self.summoned = True
            self._roar(me, match)
            match.summon(("diabrete",) * 3 + ("esqueleto", random.choice(SHADES)), me)
        elif not self.enraged and ratio <= 0.2 and self.state not in ("jump", "air"):
            self.enraged = True
            me.aura = ENRAGED_AURA
            me.speed_mult *= 1.25
            self._roar(me, match)
            match.popup(me.x, me.y - 120, "FURIOSO!", ENRAGED_AURA)
            match.popup(me.x, me.y - 100, "ARMADURA DE SOMBRA", (190, 120, 255))

        target = match.nearest_player(me)
        self.timer -= 1
        state = self.state
        if target is None:
            me.steer(0, 0)
            return
        if state == "walk":
            self._walk(me, match, target)
            if self.timer <= 0:
                self.combo = self._new_combo()
                self._next(me, match)
        elif state == "roar":
            me.steer(0, 0)
            if self.timer % 10 == 0:
                match.camera.shake(6)
                match.burst(me.x, me.y - 40, me.aura, 8, speed=6)
            if self.timer <= 0:
                me.invulnerable_timer = 0
                self._set(me, "walk", self._wait(80))
        elif state == "tired":
            me.steer(0, 0)
            if self.timer % 30 == 0:
                match.popup(me.x, me.y - 120, "CANSADO", theme.MUTED)
            if self.timer <= 0:
                self._set(me, "walk", self._wait(120))
        elif state == "rain":
            me.steer(0, 0)
            me.face(target)
            if self.timer == 1:
                self._rain(me, match)
            if self.timer <= 0:
                self._next(me, match, pause=50)
        elif state == "ring":
            me.steer(0, 0)
            if self.timer == 1:
                self._ring(me, match, 0.0)
            if self.enraged and self.timer == -14:
                self._ring(me, match, math.pi / 14)
            if self.timer <= (-16 if self.enraged else 0):
                self._next(me, match, pause=40)
        elif state == "jump":
            me.steer(0, 0)
            me.face(target)
            if self.timer <= 0:
                self._take_off(me, match, target)
        elif state == "air":
            self._fly(me, match)
        elif state == "dash":
            me.steer(0, 0)
            if self.timer <= 0:
                self._set(me, "dashing", 44)
                self.dash_hit = set()
                match.assets.play("dash", 0.6)
        elif state == "dashing":
            self._dashing(me, match)
        elif state == "pause":
            self._walk(me, match, target, shoot=False)
            if self.timer <= 0:
                self._next(me, match)

    def _next(self, me, match, pause=0):
        if pause:
            self._set(me, "pause", self._wait(pause))
            return
        if not self.combo:
            self._set(me, "tired", round(TIRED / max(0.8, self.aggression)))
            return
        pattern = self.combo.pop(0)
        self.last_pattern = pattern
        windup = {"rain": 44, "ring": 34, "jump": 26, "dash": 40}[pattern]
        color = {"rain": (200, 120, 255), "ring": (255, 150, 70), "jump": (255, 90, 90),
                 "dash": (150, 60, 230)}[pattern]
        me.start_windup(self._wait(windup), color)
        self._set(me, pattern, self._wait(windup))
        if pattern == "dash":
            self._aim_dash(me, match, self._wait(windup))

    def _roar(self, me, match):
        me.invulnerable_timer = 70
        me.windup = 0
        self.combo = []
        self._set(me, "roar", 70)
        match.assets.play("explosion", 0.6)

    def _walk(self, me, match, target, shoot=True):
        d = me.distance_to(target)
        if d > 260:
            move = self.chase(me, match, target.x, target.y)
        elif d < 150:
            move = self.chase(me, match, target.x, target.y, away=True)
        else:
            ax, ay = me.direction_to(target)
            move = (-ay * self.strafe * 0.8, ax * self.strafe * 0.8)
            if random.random() < 0.01:
                self.strafe = -self.strafe
        me.steer(*move)
        if shoot and me.attack_cd <= 0 and random.random() < 0.06 * self.speed:
            me.weapon_index = 1 if d < 90 else 0
            me.attack(match, target)

    # ── golpes ───────────────────────────────
    def _rain(self, me, match):
        """Bombas caem em cima de cada jogador e em volta deles."""
        dmg = round(18 * me.damage_bonus)
        for p in match.alive_players:
            match.add_effect(ShadowBomb(me, p.x, p.y, delay=self._wait(54), damage=dmg))
            for _ in range(2 if self.enraged else 1):
                a = random.uniform(0, math.tau)
                r = random.uniform(80, 150)
                x, y = match.arena.free_spot(p.x + math.cos(a) * r, p.y + math.sin(a) * r, 10)
                match.add_effect(ShadowBomb(me, x, y, delay=self._wait(72), damage=dmg))
        for _ in range(3):
            x, y = match.arena.random_free_spot(20)
            if me.distance_to(_P(x, y)) < 600:
                match.add_effect(ShadowBomb(me, x, y, delay=self._wait(80), damage=dmg))
        match.assets.play("ability", 0.5)

    def _ring(self, me, match, offset):
        count = 14 if self.enraged else 12
        speed = me.weapons[0].bullet_speed * 0.95
        dmg = round(14 * me.damage_bonus)
        for k in range(count):
            a = offset + k * math.tau / count
            match.spawn_bullet(me, math.cos(a), math.sin(a), speed, dmg, explosive=True)
        match.assets.play("explosion", 0.4)
        match.camera.shake(4)

    DASH_SPEED = 15
    DASH_DAMAGE = 24

    def _aim_dash(self, me, match, frames):
        """Investida sombria: mira no jogador e marca o caminho no chão (dá para sair da frente)."""
        target = match.nearest_player(me)
        if target is None:
            return
        self.dash_dir = me.direction_to(target)
        if self.dash_dir == (0.0, 0.0):
            self.dash_dir = me.facing
        me.face(target)
        dx, dy = self.dash_dir
        for k in range(1, 12):
            x, y = me.x + dx * k * 60, me.y + dy * k * 60
            if not (30 < x < match.arena.width - 30 and 30 < y < match.arena.height - 30):
                break
            match.add_effect(GroundMark(x, y, 44, frames, (150, 60, 230)))

    def _dashing(self, me, match):
        """Atravessa a arena: bate em quem estiver no caminho e larga bombas atrás."""
        dx, dy = self.dash_dir
        me.facing = (dx, dy)
        me.dash_dir = (dx, dy)
        me.vx = me.vy = 0.0
        # sombra: atravessa as paredes (só a borda da arena para a investida)
        arena = match.arena
        me.x += dx * self.DASH_SPEED
        me.y += dy * self.DASH_SPEED
        margin = me.radius + 40
        hit_wall = not (margin < me.x < arena.width - margin and margin < me.y < arena.height - margin)
        me.x = min(max(me.x, margin), arena.width - margin)
        me.y = min(max(me.y, margin), arena.height - margin)
        me.pull_timer = 0
        me.ghost_walk = True
        if self.timer % 5 == 0:
            match.add_effect(ShadowBomb(me, me.x, me.y, delay=self._wait(34), damage=round(16 * me.damage_bonus),
                                        radius=46))
        if self.timer % 2 == 0:
            match.burst(me.x, me.y - 30, (150, 60, 230), 3, speed=2)
        for p in match.alive_players:
            if p not in self.dash_hit and me.distance_to(p) < me.radius + p.radius + 10:
                self.dash_hit.add(p)
                if p.take_damage(round(self.DASH_DAMAGE * me.damage_bonus), me.x, me.y, attacker=me, match=match):
                    p.knock = [dx * 12 - dy * 6, dy * 12 + dx * 6]
        if hit_wall or self.timer <= 0:
            me.ghost_walk = False
            arena.resolve(me)                         # se parou dentro de uma parede, sai dela
            match.camera.shake(7)
            match.assets.play("passo_pesado", 0.6)
            match.dust(me.x, me.y + 30, 12)
            self._next(me, match, pause=30)

    AIR = 46

    def _take_off(self, me, match, target):
        self.jump_from = (me.x, me.y)
        tx, ty = target.x + target.vx * 18, target.y + target.vy * 18
        tx, ty = match.arena.free_spot(tx, ty, me.radius + 2)
        self.jump_to = (tx, ty)
        self.jump_frames = 0
        me.invulnerable_timer = self.AIR + 2
        me.armed = False
        match.add_effect(GroundMark(tx, ty, 140, self.AIR, (255, 90, 90)))
        match.dust(me.x, me.y + 30, 10)
        match.assets.play("dash", 0.5)
        self._set(me, "air", self.AIR)

    def _fly(self, me, match):
        self.jump_frames += 1
        t = self.jump_frames / self.AIR
        (x0, y0), (x1, y1) = self.jump_from, self.jump_to
        me.x = x0 + (x1 - x0) * t
        me.y = y0 + (y1 - y0) * t
        me.lift = math.sin(t * math.pi) * 150
        me.vx = me.vy = 0.0
        me.steer(0, 0)
        if self.jump_frames >= self.AIR:
            me.lift = 0
            me.armed = True
            me.invulnerable_timer = 0
            match.add_effect(Shockwave(me, me.x, me.y, 140, round(26 * me.damage_bonus), stun=36,
                                       color=(220, 120, 255)))
            me.melee_flash = 12
            match.assets.play("passo_pesado", 0.7)
            self._next(me, match, pause=36)


class _P:
    def __init__(self, x, y):
        self.x, self.y = x, y
