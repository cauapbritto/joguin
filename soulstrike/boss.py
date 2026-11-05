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
from .entities import Entity, GroundMark, ShadowBomb

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


class BossAI(EnemyAI):
    reaction = 6
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

    # ── utilidades ───────────────────────────
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
            x, y = match.arena.free_spot(x, y, 20)
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


BOSSES = {"aryel": (BOSS_STATS, "aryel", BossAI), "borba": (BORBA_STATS, "borba_exo", BorbaBossAI),
          "albeguinio": (ALBEGUINIO_STATS, "albeguinio_adm", AlbeguinioBossAI)}


class _P:
    def __init__(self, x, y):
        self.x, self.y = x, y
