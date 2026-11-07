"""Os chefões da campanha: Aryel Corrompido (capítulo 1), Borba Jr Corrompido (capítulo 2) e
Albeguinio Corrompido (capítulo 3, lá embaixo).

Aryel alterna golpes em sequência (chuva de bombas, anel de granadas, martelada com pulo e a
investida sombria) e depois de cada sequência fica CANSADO por um tempo: é a hora de bater.
Com metade da vida chama ajuda (com uma alma corrompida de herói); com 20% fica furioso, mais
rápido e ganha a armadura de sombra, que só quebra quando ele cansa.

Borba Jr segue o mesmo modelo dentro do exoesqueleto: Canhão de Pulso (a linha azul engrossa antes
do tiro), Punho Mecânico em série (o 3º soco abre uma onda de choque) e o salto do exo. No lugar
de CANSADO ele fica SUPERAQUECIDO, soltando vapor; com metade da vida chama drones e um Miliciano
de Exo, e com 20% liga a blindagem total, que só cai quando ele superaquece.
"""
import math
import random

import pygame

from . import theme
from .data import WeaponStats
from .enemies import PATROL_RED, SHADOW_AURA, SHADOW_RIM, AimLine, EnemyAI, EnemyStats, Shockwave
from .entities import Entity, FloatingText, GroundMark, ShadowBomb

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


def spawn_boss(match, x, y, which="aryel"):
    from .fighter import Fighter
    stats, sprite, brain = BOSSES[which]
    f = Fighter(stats, 0, x, y, match.assets.shadow_sprites(sprite), stats.name.upper(), SHADOW_AURA,
                team=1, weapon_index=0, is_cpu=True)
    f.radius = f.base_radius = stats.radius
    f.draw_scale = SCALE
    f.knock_resist = 1.0
    f.unstoppable = True
    f.overlay = "none"           # a vida aparece na barra grande do topo
    f.aura = SHADOW_RIM
    f.ring_color = SHADOW_RIM
    f.kind = "chefe"
    f.phase_label = ""
    return f, brain(match.session.difficulty, len(match.players))


class BossLine(FloatingText):
    """Uma fala do chefe durante a luta: fica parada em cima dele uns 2,5 s (não sobe como o dano)."""

    def __init__(self, boss, text, color):
        super().__init__(boss.x, boss.y - 170, text, color)
        self.boss = boss
        self.life = 150

    def update(self):
        self.x, self.y = self.boss.x, self.boss.y - 170
        self.life -= 1
        return self.life > 0


class BossAI(EnemyAI):
    reaction = 6
    # falas na luta: ao entrar, na primeira vez que cansa e quando a vida está acabando
    LINES = ("VIERAM APOSTAR CONTRA A CASA?", "SÓ... MAIS... UMA RODADA...", "A VOZ PROMETEU GREEN!")
    LINE_COLOR = (214, 170, 255)
    LAST_LINE_AT = 0.15
    PATTERNS = ("rain", "ring", "jump", "dash")
    WINDUPS = {"rain": 44, "ring": 34, "jump": 26, "dash": 40}
    COLORS = {"rain": (200, 120, 255), "ring": (255, 150, 70), "jump": (255, 90, 90), "dash": (150, 60, 230)}
    TIRED_LABEL = "CANSADO! HORA DE ATACAR"
    TIRED_POPUP = "CANSADO"
    ROAR_LABEL = "AS SOMBRAS ESTÃO VINDO"
    ARMOR_LABEL = "ARMADURA DE SOMBRA: ESPERE ELE CANSAR"
    ARMOR_NAME = "ARMADURA DE SOMBRA"
    ARMOR = ARMOR
    LAND_COLOR = (220, 120, 255)
    ENRAGE_POPUP = "FURIOSO!"

    def summon_kinds(self):
        return ("diabrete",) * 3 + ("esqueleto", random.choice(SHADES))

    def _on_half(self, me, match):
        """Metade da vida: chama ajuda."""
        match.summon(self.summon_kinds(), me)

    def _on_enrage(self, me, match):
        """20% da vida (depois do rugido)."""

    def __init__(self, difficulty="normal", players=1):
        super().__init__(difficulty)
        self.players = players
        # Ibrahim e Borba: fica furioso mais cedo (no Borba, com metade da vida: é quase uma fase a mais)
        from .campaign import LEVELS
        self.enrage_at = LEVELS[difficulty].enrage if difficulty in LEVELS else 0.2
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
        self.said = set()

    # ── utilidades ───────────────────────────
    def say(self, me, match, which):
        """Solta a fala ``which`` (0 entrada, 1 cansado, 2 fim) uma vez só na luta."""
        if which in self.said or which >= len(self.LINES) or not hasattr(match, "popups"):
            return
        self.said.add(which)
        match.popups.append(BossLine(me, self.LINES[which], self.LINE_COLOR))

    @property
    def speed(self):
        return (1.35 if self.enraged else 1.0) * self.aggression

    def _wait(self, frames):
        return max(8, round(frames / self.speed))

    def _set(self, me, state, frames):
        self.state = state
        self.timer = frames
        me.vulnerability = 1.6 if state == "tired" else self.ARMOR if self.enraged else 1.0
        me.phase_label = {"tired": self.TIRED_LABEL, "roar": self.ROAR_LABEL}.get(
            state, self.ARMOR_LABEL if self.enraged else "")

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
        self.say(me, match, 0)
        if ratio <= self.LAST_LINE_AT:
            self.say(me, match, 2)
        if not self.summoned and ratio <= 0.5 and self.state not in ("jump", "air"):
            self.summoned = True
            self._roar(me, match)
            self._on_half(me, match)
        elif not self.enraged and ratio <= self.enrage_at and self.state not in ("jump", "air"):
            self.enraged = True
            me.aura = ENRAGED_AURA
            me.speed_mult *= 1.25
            self._roar(me, match)
            match.popup(me.x, me.y - 120, self.ENRAGE_POPUP, ENRAGED_AURA)
            self._on_enrage(me, match)
            match.popup(me.x, me.y - 100, self.ARMOR_NAME, (190, 120, 255))

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
            self.say(me, match, 1)
            if self.timer % 30 == 0:
                match.popup(me.x, me.y - 120, self.TIRED_POPUP, theme.MUTED)
            self._tired_tick(me, match)
            if self.timer <= 0:
                self._set(me, "walk", self._wait(120))
        elif state == "jump":
            me.steer(0, 0)
            me.face(target)
            if self.timer <= 0:
                self._take_off(me, match, target)
        elif state == "air":
            self._fly(me, match)
        elif state == "pause":
            self._walk(me, match, target, shoot=False)
            if self.timer <= 0:
                self._next(me, match)
        else:
            self._pattern(me, match, target, state)

    def _tired_tick(self, me, match):
        pass

    def _pattern(self, me, match, target, state):
        """Os golpes próprios de cada chefão (os outros estados são comuns aos dois)."""
        if state == "rain":
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
        elif state == "dash":
            me.steer(0, 0)
            if self.timer <= 0:
                self._set(me, "dashing", 44)
                self.dash_hit = set()
                match.assets.play("dash", 0.6)
        elif state == "dashing":
            self._dashing(me, match)

    def _next(self, me, match, pause=0):
        if pause:
            self._set(me, "pause", self._wait(pause))
            return
        if not self.combo:
            self._set(me, "tired", round(TIRED / max(0.8, self.aggression)))
            return
        pattern = self.combo.pop(0)
        self.last_pattern = pattern
        windup = self.WINDUPS[pattern]
        me.start_windup(self._wait(windup), self.COLORS[pattern])
        self._set(me, pattern, self._wait(windup))
        self._begin(me, match, pattern, self._wait(windup))

    def _begin(self, me, match, pattern, frames):
        if pattern == "dash":
            self._aim_dash(me, match, frames)

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
            self._basic_attack(me, match, target, d)

    def _basic_attack(self, me, match, target, d):
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
            room = match.arena.room
            if not (room.x + 30 < x < room.right - 30 and room.y + 30 < y < room.bottom - 30):
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
        room = arena.room
        hit_wall = not (room.x + margin < me.x < room.right - margin and room.y + margin < me.y < room.bottom - margin)
        me.x = min(max(me.x, room.x + margin), room.right - margin)
        me.y = min(max(me.y, room.y + margin), room.bottom - margin)
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
                                       color=self.LAND_COLOR))
            me.melee_flash = 12
            match.assets.play("passo_pesado", 0.7)
            self._next(me, match, pause=36)


# ─────────────────────────────────────────────
#  Borba Jr Corrompido (capítulo 2)
# ─────────────────────────────────────────────
PULSE_BLUE = (90, 170, 255)
STEAM = (226, 230, 236)
BORBA_STATS = EnemyStats(
    "borba_corrompido", "Borba Jr Corrompido", 1650, 2.5, SHADOW_AURA,
    "Sobrecarga", "Canhão de pulso gigante.",
    (WeaponStats("Canhão de Pulso", "ranged", 14, bullet_speed=9, cooldown=40, style="pulso", charge=True),
     WeaponStats("Punho Mecânico", "melee", 22, reach=64, cooldown=40)), "borba_exo",
    radius=26, elite=True, armed=True, knock_resist=1.0, drop_chance=0.0)
HEAT_ARMOR = 0.12            # blindagem total (com 20% da vida): quase nada passa, menos superaquecido


class BorbaBossAI(BossAI):
    """Borba Jr Corrompido: Canhão de Pulso, Punho Mecânico em série e o salto do exo."""

    PATTERNS = ("cannon", "punch", "jump")
    WINDUPS = {"cannon": 56, "punch": 18, "jump": 26}
    COLORS = {"cannon": PULSE_BLUE, "punch": (255, 150, 70), "jump": (255, 90, 90)}
    LINES = ("O EXO NÃO ERRA. O EXO NÃO PENSA.", "SUPERAQUECEU... IGUAL FORNO DE PÃO", "A VOZ DISSE QUE ERA PERFEITO...")
    TIRED_LABEL = "SUPERAQUECIDO! HORA DE ATACAR"
    TIRED_POPUP = "SUPERAQUECIDO"
    ROAR_LABEL = "A PATRULHA ESTÁ VINDO"
    ARMOR_LABEL = "BLINDAGEM TOTAL: ESPERE ELE SUPERAQUECER"
    ARMOR_NAME = "BLINDAGEM TOTAL"
    ARMOR = HEAT_ARMOR
    LAND_COLOR = PULSE_BLUE
    PUNCHES = 3
    PUNCH_STEP = 34

    def __init__(self, difficulty="normal", players=1):
        super().__init__(difficulty, players)
        self.aim = (1.0, 0.0)
        self.punches = 0
        self.cannon = WeaponStats("Canhão de Pulso", "ranged", 26, bullet_speed=9, cooldown=40, style="pulso",
                                  charge=True)

    def summon_kinds(self):
        return ("drone",) * 3 + ("miliciano_exo",)

    def _basic_attack(self, me, match, target, d):
        if d < 90:
            me.weapon_index = 1
            me.attack(match, target)
            return
        # tiro de pulso pequeno andando (o grande é o golpe carregado)
        me.attack_cd = 34
        match.spawn_projectile(me, self.cannon, me.direction_to(target), round(12 * me.damage_bonus), power=0.4)

    def _tired_tick(self, me, match):
        if self.timer % 4 == 0:              # vapor saindo do exo
            match.burst(me.x + random.uniform(-26, 26), me.y - 70, STEAM, 2, speed=1.5)
        if self.timer % 40 == 0:
            match.assets.play("vapor", 0.4)

    def _begin(self, me, match, pattern, frames):
        target = match.nearest_player(me)
        if target is None:
            return
        me.face(target)
        if pattern == "cannon":
            # a linha azul aparece já travada: dá tempo de sair de lado
            self.aim = me.direction_to(target) if me.direction_to(target) != (0.0, 0.0) else me.facing
            match.add_effect(AimLine(me.x, me.y, *self.aim, 900, frames, color=PULSE_BLUE, width=2, grow=12))
            match.assets.play("carga", 0.5)
        elif pattern == "punch":
            self.punches = self.PUNCHES

    def _pattern(self, me, match, target, state):
        if state == "cannon":
            me.steer(0, 0)
            if self.timer == 1:
                self._fire(me, match)
            if self.timer <= 0:
                self._next(me, match, pause=40)
        elif state == "punch":
            me.steer(0, 0)
            if self.timer == 1:
                self._punch(me, match, target)
            if self.timer <= 0:
                if self.punches > 0:
                    frames = self._wait(14)
                    me.face(target)
                    me.start_windup(frames, self.COLORS["punch"])
                    self.timer = frames
                else:
                    self._next(me, match, pause=36)

    def _fire(self, me, match):
        """Uma bola grande pela linha (com 20% da vida, três em leque)."""
        dmg = round(self.cannon.damage * me.damage_bonus)
        angles = (-0.22, 0.0, 0.22) if self.enraged else (0.0,)
        dx, dy = self.aim
        for a in angles:
            c, s_ = math.cos(a), math.sin(a)
            match.spawn_projectile(me, self.cannon, (dx * c - dy * s_, dx * s_ + dy * c), dmg, power=2.0)
        me.knock = [-dx * 4, -dy * 4]
        match.camera.shake(6)
        match.assets.play("explosion", 0.5)

    def _punch(self, me, match, target):
        """Um passo para a frente e um soco em arco; o terceiro abre a onda de choque."""
        self.punches -= 1
        dx, dy = me.direction_to(target) if me.distance_to(target) > 1 else me.facing
        me.facing = (dx, dy)
        me.x += dx * self.PUNCH_STEP
        me.y += dy * self.PUNCH_STEP
        match.arena.resolve(me)
        fx, fy = me.x + dx * 56, me.y + dy * 56
        me.melee_flash = 10
        match.assets.play("soco_metal", 0.5)
        if self.punches == 0:
            match.add_effect(Shockwave(me, fx, fy, 130, round(22 * me.damage_bonus), stun=30, color=PULSE_BLUE))
            return
        dmg = round(16 * me.damage_bonus)
        for p in match.alive_players:
            if math.hypot(p.x - fx, p.y - fy) < 58 + p.radius:
                if p.take_damage(dmg, me.x, me.y, attacker=me, match=match):
                    p.knock = [dx * 9, dy * 9]
        match.burst(fx, fy - 20, (255, 200, 120), 8, speed=4)


# ─────────────────────────────────────────────
#  Albeguinio Corrompido (capítulo 3)
# ─────────────────────────────────────────────
CLEPA = (255, 110, 190)
CACO = (170, 90, 230)
PAPER = (240, 238, 230)
STAMP_RED = (220, 60, 70)
ALBEGUINIO_STATS = EnemyStats(
    "albeguinio_corrompido", "Albeguinio Corrompido", 1600, 2.6, SHADOW_AURA,
    "Fechamento do Mês", "Carimbo gigante.",
    (WeaponStats("Boleto", "ranged", 11, bullet_speed=8, cooldown=30, style="boleto"),
     WeaponStats("Carimbo", "melee", 22, reach=60, cooldown=40)), "albeguinio_adm",
    radius=26, elite=True, armed=True, knock_resist=1.0, drop_chance=0.0)
CABLE_SPOTS = ((120, 600), (1480, 600), (800, 1040))
HARMONY_ARMOR = 0.1          # harmonizado (cabos inteiros): quase nada passa


class CableLink(Entity):
    """O cabo roxo que liga a máquina ao chefe enquanto os dois estão de pé (Harmonização)."""

    def __init__(self, cable, boss):
        super().__init__(cable.x, cable.y)
        self.cable, self.boss = cable, boss
        self.age = 0

    def update(self, match):
        self.age += 1
        if not (self.cable.alive_in_match and self.boss.alive_in_match):
            self.alive = False

    def draw(self, surf, camera):
        x0, y0 = self.cable.x - camera.x, self.cable.y - 16 - camera.y
        x1, y1 = self.boss.x - camera.x, self.boss.y - 40 - camera.y
        dx, dy = x1 - x0, y1 - y0
        length = math.hypot(dx, dy) or 1
        nx, ny = -dy / length, dx / length
        points = []
        for k in range(17):
            t = k / 16
            wave = math.sin(t * 9 + self.age * 0.25) * 6 * math.sin(t * math.pi)
            points.append((x0 + dx * t + nx * wave, y0 + dy * t + ny * wave))
        pygame.draw.lines(surf, (60, 20, 90), False, points, 6)
        pygame.draw.lines(surf, CACO, False, points, 3)
        k = (self.age // 2) % 17                      # a energia correndo até ele
        px, py = points[k]
        pygame.draw.circle(surf, (240, 210, 255), (round(px), round(py)), 4)


class AlbeguinioBossAI(BossAI):
    """Albeguinio Corrompido, na Sala do Administrativo: chuva de boletos em leque, o carimbo
    gigante (o retângulo vermelho aparece no chão antes: PAGO ou VENCIDO) e a agenda, que "marca
    horário" e solta argila no chão em volta de todo mundo. Depois de cada sequência faz a PAUSA PRO
    CAFÉ (hora de bater). Com metade da vida liga a HARMONIZAÇÃO: três cabos da máquina saem do chão
    e, enquanto um estiver inteiro, quase nada passa nele. Com 20% vem a RECAÍDA: o celular vibra,
    ele fica mais rápido e a armadura só cai na pausa pro café."""

    PATTERNS = ("boletos", "carimbo", "agenda")
    WINDUPS = {"boletos": 30, "carimbo": 36, "agenda": 44}
    COLORS = {"boletos": PAPER, "carimbo": STAMP_RED, "agenda": CLEPA}
    LINES = ("SENHA 47? PODE ENTRAR... NA FILA.", "PAUSA... SÓ UM CAFEZINHO...", "A META DO MÊS... NÃO BATEU...")
    TIRED_LABEL = "PAUSA PRO CAFÉ! HORA DE ATACAR"
    TIRED_POPUP = "PAUSA PRO CAFÉ"
    ROAR_LABEL = "HARMONIZAÇÃO: CORTEM OS 3 CABOS"
    ARMOR_LABEL = "RECAÍDA: ESPERE A PAUSA PRO CAFÉ"
    ARMOR_NAME = "RECAÍDA"
    ENRAGE_POPUP = "O CELULAR VIBROU..."
    LAND_COLOR = CLEPA

    def __init__(self, difficulty="normal", players=1):
        super().__init__(difficulty, players)
        self.cables = []
        self.harmony = False
        self.boleto = ALBEGUINIO_STATS.weapons[0]

    def summon_kinds(self):
        return ("mascara_argila",) * 2 + ("seringuinha",)

    # ── harmonização ─────────────────────────
    def _on_half(self, me, match):
        self.cables = []
        for x, y in CABLE_SPOTS:
            x, y = match.arena.free_spot(*match.arena.at(x, y), 20)
            cable = match.spawn_now("cabo", x, y)
            self.cables.append(cable)
            match.add_effect(CableLink(cable, me))
        self.harmony = True
        me.vulnerability = HARMONY_ARMOR
        me.aura = CLEPA
        match.popup(me.x, me.y - 140, "HARMONIZAÇÃO", CLEPA)
        match.summon(self.summon_kinds(), me)

    def _on_enrage(self, me, match):
        match.popup(me.x, me.y - 160, "BZZZ BZZZ", (230, 230, 240))
        match.assets.play("notificacao", 0.6)

    def _set(self, me, state, frames):
        super()._set(me, state, frames)
        if self.harmony:
            me.vulnerability = HARMONY_ARMOR
            if state != "roar":
                me.phase_label = self.ROAR_LABEL

    def update(self, me, match):
        if self.harmony and me.alive_in_match and not any(c.alive_in_match for c in self.cables):
            self.harmony = False
            me.aura = ENRAGED_AURA if self.enraged else SHADOW_RIM
            match.popup(me.x, me.y - 140, "HARMONIZAÇÃO DESFEITA!", theme.MOSS)
            match.assets.play("vidro", 0.5)
            self._set(me, self.state, self.timer)
        super().update(me, match)

    # ── golpes ───────────────────────────────
    def _basic_attack(self, me, match, target, d):
        if d < 90:
            me.weapon_index = 1
            me.attack(match, target)
            return
        me.attack_cd = 30
        match.spawn_projectile(me, self.boleto, me.direction_to(target), round(10 * me.damage_bonus))

    def _begin(self, me, match, pattern, frames):
        target = match.nearest_player(me)
        if target is not None:
            me.face(target)
        if pattern == "carimbo":
            # o carimbo cai em cima de cada um (com a Recaída, mais dois pela sala)
            from .clinica import Stamp
            dmg = round(22 * me.damage_bonus)
            spots = [(p.x, p.y) for p in match.alive_players]
            if self.enraged:
                spots += [match.arena.random_free_spot(30) for _ in range(2)]
            for x, y in spots:
                match.add_effect(Stamp(me, x, y, frames + self._wait(26), dmg))

    def _pattern(self, me, match, target, state):
        me.steer(0, 0)
        if state == "boletos":
            me.face(target)
            if self.timer == 1:
                self._boletos(me, match, target, 0.0)
            if self.enraged and self.timer == -12:
                self._boletos(me, match, target, 0.13)
            if self.timer <= (-14 if self.enraged else 0):
                self._next(me, match, pause=36)
        elif state == "carimbo":
            if self.timer <= -26:
                self._next(me, match, pause=30)
        elif state == "agenda":
            if self.timer == 1:
                self._agenda(me, match)
            if self.timer <= 0:
                self._next(me, match, pause=40)

    def _boletos(self, me, match, target, offset):
        """Leque de boletos (5; com a Recaída, 7)."""
        count = 7 if self.enraged else 5
        dx, dy = me.direction_to(target) if me.distance_to(target) > 1 else me.facing
        base = math.atan2(dy, dx) + offset
        dmg = round(12 * me.damage_bonus)
        for k in range(count):
            a = base + (k - (count - 1) / 2) * 0.2
            match.spawn_projectile(me, self.boleto, (math.cos(a), math.sin(a)), dmg)
        match.assets.play("arremesso", 0.5)

    def _agenda(self, me, match):
        """A agenda "marca horário": argila no chão em volta de cada um (deixa lento)."""
        from .clinica import ClayPuddle
        for p in match.alive_players:
            for k in range(3):
                a = k * math.tau / 3 + random.uniform(-0.4, 0.4)
                r = random.uniform(60, 110)
                x, y = match.arena.free_spot(p.x + math.cos(a) * r, p.y + math.sin(a) * r, 10)
                match.add_effect(ClayPuddle(x, y, radius=40))
        if len([e for e in match.alive_enemies if e is not me and getattr(e, "kind", "") != "cabo"]) < 2:
            match.summon(("mascara_argila",), me)
        match.popup(me.x, me.y - 130, "AGENDA CHEIA", CLEPA)
        match.assets.play("gosma", 0.5)


# ─────────────────────────────────────────────
#  Cauanzera Corrompido (capítulo 4)
# ─────────────────────────────────────────────
IARA_C = (60, 230, 255)
IARA_L = (200, 250, 255)
CAUANZERA_STATS = EnemyStats(
    "cauanzera_corrompido", "Cauanzera Corrompido", 1700, 2.7, SHADOW_AURA,
    "Otimização Total", "A IARA no comando.",
    (WeaponStats("Pacote de Dados", "ranged", 11, bullet_speed=8, cooldown=30),
     WeaponStats("Teclado", "melee", 22, reach=60, cooldown=40)), "cauanzera_ti",
    radius=26, elite=True, armed=True, knock_resist=1.0, drop_chance=0.0)
IARA_CABLES = ((325, 380), (1275, 380), (325, 800), (1275, 800))
IARA_SPOT = (800, 520)
TURN_AT = 0.25               # com essa vida, na fusão, os aliados chegam
ALLIES = (("aryel", "ARYEL", "Cauanzera, volta pra gente! Isso aí não é você!"),
          ("borba", "BORBA JR", "Já desliguei uma fábrica inteira. Um servidor é moleza."),
          ("albeguinio", "ALBEGUINIO", "Deixa comigo: vou travar a rede dela. Hoje o wi-fi cai do lado certo!"))
ALLY_GAP = 110               # quadros entre a chegada de um aliado e a do próximo


class AllyCameo(Entity):
    """Um aliado entrando na luta (a virada): corre da beira da sala até perto do chefe, solta a
    fala e o golpe dele. O golpe só atordoa o chefe (quem acaba a luta são os jogadores)."""

    RUN = 50

    def __init__(self, key, name, line, start, spot, boss, order):
        super().__init__(*start)
        self.key, self.name, self.line = key, name, line
        self.start, self.spot = start, spot
        self.boss = boss
        self.order = order
        self.age = 0

    def update(self, match):
        self.age += 1
        t = min(1.0, self.age / self.RUN)
        self.x = self.start[0] + (self.spot[0] - self.start[0]) * t
        self.y = self.start[1] + (self.spot[1] - self.start[1]) * t
        if self.age == self.RUN:
            self._strike(match)
        if self.age > self.RUN + 30 and self.age % 40 == 0:
            match.burst(self.x, self.y - 30, (240, 230, 160), 2, speed=1)

    def _strike(self, match):
        b = self.boss
        match.popup(self.x, self.y - 90, self.name + "!", theme.BRASS)
        match.popup(self.x, self.y - 112, self.line, theme.BONE)
        if self.order == 0:                                 # Aryel: chuva de luz em volta do chefe
            for k in range(10):
                a = k * math.tau / 10
                match.burst(b.x + math.cos(a) * 90, b.y + math.sin(a) * 40, (255, 230, 140), 6, speed=3)
            match.assets.play("ability", 0.6)
        elif self.order == 1:                               # Borba Jr: soco do exo no chão
            match.dust(b.x, b.y + 20, 20)
            match.burst(b.x, b.y, (90, 170, 255), 24, speed=6)
            match.assets.play("soco_metal", 0.7)
        else:                                               # Albeguinio: trava a rede
            for k in range(6):
                match.burst(b.x + random.uniform(-50, 50), b.y - random.uniform(0, 90), IARA_C, 5, speed=4)
            match.assets.play("eletrico", 0.7)
        match.camera.shake(8)
        b.stun_timer = max(b.stun_timer, 240)
        match.popup(b.x, b.y - 150, "ATORDOADO", (240, 230, 160))

    def draw(self, surf, camera):
        sprites = self.match_sprites
        if sprites is None:
            return
        running = self.age < self.RUN
        dx = self.spot[0] - self.start[0]
        dy = self.spot[1] - self.start[1]
        if running:
            direction = ("direita" if dx > 0 else "esquerda") if abs(dx) > abs(dy) else ("frente" if dy > 0 else "costas")
            img = sprites.frame(direction, self.age // 4)
        else:
            img = sprites.pose("costas", "ataque" if self.age < self.RUN + 20 else "parado", min(2, (self.age - self.RUN) // 6))
        pos = (round(self.x - camera.x), round(self.y - camera.y) + 22)
        pygame.draw.ellipse(surf, (0, 0, 0), (pos[0] - 18, pos[1] - 6, 36, 10))
        surf.blit(img, img.get_rect(midbottom=pos))

    match_sprites = None


class PowerPlug(Entity):
    """A tomada do servidor (a lasca está ligada ali). ATACAR perto tira da tomada: é o golpe final."""

    RADIUS = 80

    def __init__(self, x, y, boss):
        super().__init__(x, y)
        self.boss = boss
        self.age = 0
        self.pulled = False

    def near(self, f):
        return math.hypot(f.x - self.x, f.y - self.y) < self.RADIUS

    def update(self, match):
        self.age += 1
        if self.pulled:
            return
        if self.age % 8 == 0:
            match.burst(self.x, self.y - 20, CACO, 2, speed=1.5)

    def draw(self, surf, camera):
        sx, sy = round(self.x - camera.x), round(self.y - camera.y)
        b = self.boss
        # o cabo roxo da tomada até o chefe
        if not self.pulled and b.alive_in_match:
            bx, by = b.x - camera.x, b.y - 30 - camera.y
            pts = []
            for k in range(13):
                t = k / 12
                sag = math.sin(t * math.pi) * 40
                pts.append((sx + (bx - sx) * t, sy - 10 + (by - sy + 10) * t + sag))
            pygame.draw.lines(surf, (40, 16, 60), False, pts, 6)
            pygame.draw.lines(surf, CACO, False, pts, 2)
        plate = pygame.Rect(0, 0, 40, 48)
        plate.midbottom = (sx, sy + 10)
        surf.fill((40, 40, 48), plate.inflate(4, 4))
        surf.fill((236, 236, 228), plate)
        for hx in (-7, 7):
            surf.fill((40, 40, 48), (sx + hx - 2, plate.y + 14, 4, 10))
        surf.fill((40, 40, 48), (sx - 3, plate.y + 30, 6, 6))
        if not self.pulled:
            plug = pygame.Rect(0, 0, 24, 18)
            plug.center = (sx, plate.y + 20)
            surf.fill((30, 20, 40), plug)
            surf.fill(CACO, plug.inflate(-6, -6))
            if (self.age // 10) % 2 == 0:
                pygame.draw.rect(surf, (255, 230, 140), plate.inflate(16, 16), 2)


class _TurnDirector(Entity):
    """Conduz a virada quadro a quadro (o cérebro do chefe para enquanto ele está atordoado)."""

    def __init__(self, brain, boss):
        super().__init__(boss.x, boss.y)
        self.brain, self.boss = brain, boss

    def update(self, match):
        if not self.boss.alive_in_match or (self.brain.plug is not None and self.brain.plug.pulled):
            self.alive = False
            return
        self.brain._turn_tick(self.boss, match)

    def draw(self, surf, camera):
        pass


class CauanzeraBossAI(BossAI):
    """Cauanzera Corrompido, no Núcleo da IARA, em três etapas:

    1. Ele sozinho: leque de pacotes de dados, o carimbo INDEFERIDO em cima de cada um, o pulo e a
       investida. Depois de cada sequência fica REINICIANDO (hora de bater).
    2. Com metade da vida liga o FIREWALL (nada passa nele) e a IARA sai do servidor no meio da
       sala, presa por 4 cabos. Cortem os cabos e derrubem a IARA.
    3. FUSÃO: ele puxa o que sobrou da IARA, fica mais rápido e os tentáculos entram na sequência.
       Com 15% da vida vem a virada: o Aryel, o Borba Jr e o Albeguinio chegam um de cada vez e
       atordoam o chefe. Aí aparece a tomada do servidor: ATACAR perto tira a IARA da tomada."""

    PATTERNS = ("pacotes", "carimbo", "jump", "dash")
    WINDUPS = {"pacotes": 30, "carimbo": 36, "jump": 26, "dash": 40, "tentaculos": 34}
    COLORS = {"pacotes": IARA_C, "carimbo": STAMP_RED, "jump": (255, 90, 90), "dash": (150, 60, 230),
              "tentaculos": IARA_C}
    LINES = ("SEU CHAMADO FOI ABERTO. PRAZO: NUNCA.", "REINICIANDO... NÃO DESLIGUE O PC", "IARA, ME AJUDA... IARA?")
    LINE_COLOR = IARA_C
    TIRED_LABEL = "REINICIANDO! HORA DE ATACAR"
    TIRED_POPUP = "REINICIANDO"
    ROAR_LABEL = "FIREWALL: DERRUBEM A IARA"
    ARMOR_LABEL = "FUSÃO: ESPERE ELE REINICIAR"
    ARMOR_NAME = "FUSÃO COM A IARA"
    ENRAGE_POPUP = "FUSÃO!"
    LAND_COLOR = IARA_C

    def __init__(self, difficulty="normal", players=1):
        super().__init__(difficulty, players)
        self.enrage_at = -1.0                # a fúria aqui é a fusão (vem quando a IARA cai)
        self.stage = 1
        self.iara = None
        self.cables = []
        self.turn = 0                        # quadros desde o começo da virada
        self.allies = []
        self.plug = None
        self.packet = CAUANZERA_STATS.weapons[0]

    def summon_kinds(self):
        return ("processo", "popup_iara")

    # ── etapas ───────────────────────────────
    def _on_half(self, me, match):
        """Etapa 2: FIREWALL nele e a IARA no meio da sala, presa por 4 cabos."""
        self.stage = 2
        x, y = match.arena.free_spot(*match.arena.at(*IARA_SPOT), 34)
        self.iara = match.spawn_now("iara_nucleo", x, y)
        brain = match.controllers.get(self.iara)
        self.cables = []
        for cx, cy in IARA_CABLES:
            cx, cy = match.arena.free_spot(*match.arena.at(cx, cy), 20)
            cable = match.spawn_now("cabo", cx, cy)
            self.cables.append(cable)
            match.add_effect(CableLink(cable, self.iara))
        if brain is not None:
            brain.cables = self.cables
        me.aura = IARA_C
        match.popup(x, y - 150, "IARA", IARA_C)
        match.burst(x, y - 40, IARA_C, 40, speed=6)
        match.assets.play("notificacao", 0.6)

    def _fuse(self, me, match):
        """Etapa 3: a IARA caiu e ele puxa o que sobrou dela."""
        self.stage = 3
        self.enraged = True
        me.aura = IARA_C
        me.speed_mult *= 1.15
        self.PATTERNS = ("pacotes", "carimbo", "jump", "dash", "tentaculos")
        self._roar(me, match)
        me.phase_label = ""
        match.popup(me.x, me.y - 140, self.ENRAGE_POPUP, IARA_C)
        match.popup(me.x, me.y - 118, self.ARMOR_NAME, (190, 240, 255))
        for c in self.cables:
            if c.alive_in_match:
                c.hp = 0

    def _start_turn(self, me, match):
        """A virada: os aliados chegam um de cada vez e atordoam o chefe."""
        self.stage = 4
        self.turn = 0
        self.combo = []
        me.windup = 0
        me.invulnerable_timer = 99999
        me.vulnerability = 0.0
        me.phase_label = "AGUENTEM FIRME: A TURMA CHEGOU!"
        me.lift = 0
        match.burst(me.x, me.y - 30, IARA_C, 24, speed=5)
        me.x, me.y = match.arena.free_spot(*match.arena.at(800, 600), me.radius)     # a lasca puxa ele para o meio do núcleo
        match.burst(me.x, me.y - 30, IARA_C, 24, speed=5)
        match.bullets.clear()
        match.add_effect(_TurnDirector(self, me))      # anda mesmo com o chefe atordoado
        if hasattr(match, "_set_banner"):
            match._set_banner("A TURMA CHEGOU!", "ARYEL, BORBA JR E ALBEGUINIO", theme.BRASS)
        match.assets.play("ability", 0.6)

    def update(self, me, match):
        if not me.alive_in_match:
            me.steer(0, 0)
            return
        if self.stage == 2:
            me.vulnerability = 0.0
            me.hp = max(me.hp, round(me.max_hp * 0.5))
            me.phase_label = self.ROAR_LABEL
            if self.iara is not None and not self.iara.alive_in_match:
                self._fuse(me, match)
        elif self.stage == 3:
            if me.hp <= me.max_hp * TURN_AT:
                me.hp = max(1, round(me.max_hp * TURN_AT))
                self._start_turn(me, match)
        if self.stage == 4:
            me.hp = max(me.hp, 1)
            me.steer(0, 0)
            return
        super().update(me, match)
        if self.stage == 2:                  # FIREWALL: nada passa (o _set da base mexe nisso)
            me.vulnerability = 0.0

    def _turn_tick(self, me, match):
        self.turn += 1
        me.hp = max(me.hp, 1)
        if self.turn == 100 and getattr(match, "banner", None):
            match.banner = None
        me.vulnerability = 0.0
        k = self.turn // ALLY_GAP
        if self.turn % ALLY_GAP == 30 and k < len(ALLIES):
            key, name, line = ALLIES[k]
            room = match.arena.room
            starts = ((room.x + 60, me.y), (me.x, room.y + 1130), (room.x + 1540, me.y))
            spots = ((me.x - 170, me.y), (me.x, me.y + 140), (me.x + 170, me.y))
            start = starts[k]
            spot = match.arena.free_spot(*spots[k], 16)
            ally = AllyCameo(key, name, line, start, spot, me, k)
            ally.match_sprites = match.assets.sprites.get(key)
            self.allies.append(ally)
            match.add_effect(ally)
            match.popup(start[0], start[1] - 80, name, theme.BRASS)
        if self.turn == ALLY_GAP * len(ALLIES) + 40 and self.plug is None:
            x, y = match.arena.free_spot(*match.arena.at(800, 210), 20)
            self.plug = PowerPlug(x, y, me)
            match.add_effect(self.plug)
            me.phase_label = "TIREM A IARA DA TOMADA! (ATACAR PERTO)"
            match.popup(x, y - 80, "TOMADA DO SERVIDOR", (255, 230, 140))
            match.assets.play("select", 0.6)
        if self.plug is not None:
            me.stun_timer = max(me.stun_timer, 30)

    @property
    def turn_text(self):
        return "TIREM A IARA DA TOMADA! (ATACAR PERTO)" if self.plug is not None else ""

    def interact(self, f, match):
        """ATACAR perto da tomada: o golpe final."""
        if self.plug is None or self.plug.pulled or not self.plug.near(f) or f not in match.players:
            return False
        self.plug.pulled = True
        b = self.plug.boss
        b.invulnerable_timer = 0
        b.vulnerability = 1.0
        b.shield = 0
        b.unstoppable = False
        match.popup(self.plug.x, self.plug.y - 80, "TIROU DA TOMADA!", theme.MOSS)
        match.burst(self.plug.x, self.plug.y - 20, CACO, 30, speed=6)
        match.assets.play("vidro", 0.7)
        for e in list(match.alive_enemies):
            if e is not b and hasattr(match, "vanish"):
                match.vanish(e)
                e.hp = 0
        b.take_damage(b.hp + 9999, b.x, b.y, attacker=f, match=match)
        b.hp = 0
        return True

    # ── golpes ───────────────────────────────
    def _next(self, me, match, pause=0):
        # etapa 2: ele gasta a força segurando a IARA (descansa o dobro entre um golpe e outro)
        super()._next(me, match, pause=pause * 2 if self.stage == 2 else pause)

    def _basic_attack(self, me, match, target, d):
        if d < 90:
            me.weapon_index = 1
            me.attack(match, target)
            return
        me.attack_cd = 30
        match.spawn_projectile(me, self.packet, me.direction_to(target), round(10 * me.damage_bonus))

    def _begin(self, me, match, pattern, frames):
        super()._begin(me, match, pattern, frames)
        target = match.nearest_player(me)
        if target is not None:
            me.face(target)
        if pattern == "carimbo":
            from .clinica import Stamp
            dmg = round(20 * me.damage_bonus)
            for p in match.alive_players:
                match.add_effect(Stamp(me, p.x, p.y, frames + self._wait(24), dmg, word="INDEFERIDO"))
        elif pattern == "tentaculos":
            from .mansao import TentacleBeam
            dmg = round(16 * me.damage_bonus)
            for k in range(8):
                a = k * math.tau / 8 + random.uniform(-0.1, 0.1)
                match.add_effect(TentacleBeam(me, me.x, me.y, math.cos(a), math.sin(a), 650,
                                              frames + self._wait(20), dmg))

    def _pattern(self, me, match, target, state):
        if state in ("jump", "dash", "dashing"):
            return super()._pattern(me, match, target, state)
        me.steer(0, 0)
        if state == "pacotes":
            me.face(target)
            if self.timer == 1:
                self._packets(me, match, target, 0.0)
            if self.enraged and self.timer == -12:
                self._packets(me, match, target, 0.12)
            if self.timer <= (-14 if self.enraged else 0):
                self._next(me, match, pause=36)
        elif state == "carimbo":
            if self.timer <= -24:
                self._next(me, match, pause=30)
        elif state == "tentaculos":
            if self.timer <= -24:
                self._next(me, match, pause=36)

    def _packets(self, me, match, target, offset):
        count = 7 if self.enraged else 5
        dx, dy = me.direction_to(target) if me.distance_to(target) > 1 else me.facing
        base = math.atan2(dy, dx) + offset
        dmg = round(12 * me.damage_bonus)
        for k in range(count):
            a = base + (k - (count - 1) / 2) * 0.2
            match.spawn_projectile(me, self.packet, (math.cos(a), math.sin(a)), dmg)
        match.assets.play("plasma", 0.4)


BOSSES = {"aryel": (BOSS_STATS, "aryel", BossAI), "borba": (BORBA_STATS, "borba_exo", BorbaBossAI),
          "albeguinio": (ALBEGUINIO_STATS, "albeguinio_adm", AlbeguinioBossAI),
          "cauanzera": (CAUANZERA_STATS, "cauanzera_ti", CauanzeraBossAI)}


class _P:
    def __init__(self, x, y):
        self.x, self.y = x, y
