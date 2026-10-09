"""O lutador controlado por um jogador ou pela CPU."""
import math

import pygame

from . import config, theme
from .abilities import create_ability
from .entities import Entity
from . import weapon_art

ACCELERATION = 0.3          # quanto da velocidade-alvo é alcançada por quadro
TURN_ACCELERATION = 0.5     # virar para o lado oposto responde mais rápido
FRICTION = 0.24             # frenagem ao soltar o direcional
MOVE_SCALE = 1.15
FEET = 22            # distância do centro de colisão até os pés do sprite


def proximity_damage(dist, base):
    """Tiros disparados de muito perto causam mais dano."""
    if dist <= config.MELEE_BONUS_RANGE:
        t = 1.0 - dist / config.MELEE_BONUS_RANGE
        return min(int(base + (config.MAX_BULLET_DAMAGE - base) * t), config.MAX_BULLET_DAMAGE)
    return base


class Fighter(Entity):
    def __init__(self, stats, slot, x, y, sprites, label, color, team=None, weapon_index=0, is_cpu=False):
        super().__init__(x, y)
        self.radius = config.PLAYER_RADIUS
        self.stats = stats
        self.slot = slot
        self.label = label              # "P1", "CPU"...
        self.color = color              # cor da etiqueta acima da cabeça
        self.ring_color = color         # anel no chão (no futebol, a cor do time)
        self.team = team
        self.is_cpu = is_cpu
        self.sprites = sprites
        self.hp = stats.max_hp
        self.weapon_index = weapon_index
        self.ability = create_ability(stats)

        self.vx = self.vy = 0.0
        self.input = (0.0, 0.0)
        self.facing = (1.0, 0.0) if x < 800 else (-1.0, 0.0)
        self.moving = False

        # tempos (em quadros)
        self.attack_cd = 0
        self.ability_cd = 0
        self.dash_timer = 0
        self.dash_cd = 0
        self.dash_dir = (0.0, 0.0)
        self.charge_timer = 0
        self.charge_dir = (0.0, 0.0)
        self.charge_damage = 0
        self.speed_timer = 0
        self.invulnerable_timer = 0
        self.super_cd = 0
        self.kick_cd = 0
        self.stun_timer = 0
        self.fury_timer = 0
        self.giant_timer = 0
        self.tackle_timer = 0
        self.sprint_timer = 0
        self.power = None               # poder do futebol (definido pela partida)
        self.kicked_dust = False
        self.knock = [0.0, 0.0]
        self.dribbling = False
        self.carrying_close = False
        self.carry_dir = (1.0, 0.0)
        self.kick_charge = 0            # quadros segurando CHUTE
        self.pass_charge = 0            # quadros segurando PASSE
        self.prev_pos = (x, y)
        self.dash_len = config.DASH_FRAMES
        self.armed = True               # no futebol ninguém carrega arma
        self.age = 0

        # efeitos visuais
        self.anim_frame = 0
        self.anim_timer = 0
        self.hit_flash = 0
        self.melee_flash = 0
        self.shoot_flash = 0
        self.teleport_flash = 0
        self.trail = []

        # estatísticas da partida
        self.damage_dealt = 0
        self.hits = 0
        self.goals = 0

    # ── propriedades ─────────────────────────
    @property
    def weapons(self):
        return self.stats.weapons

    @property
    def weapon(self):
        return self.stats.weapons[self.weapon_index]

    @property
    def alive_in_match(self):
        return self.hp > 0

    @property
    def invulnerable(self):
        return self.invulnerable_timer > 0 or self.dash_timer > 0

    @property
    def ability_ready(self):
        return self.ability_cd <= 0

    @property
    def ability_ratio(self):
        return 1 - self.ability_cd / config.ABILITY_COOLDOWN

    @property
    def max_speed(self):
        base = self.stats.speed * MOVE_SCALE
        if self.sprint_timer > 0:
            return base * 1.8
        if self.carrying_close:
            base *= 0.9            # conduzir colado custa um pouco de velocidade
        return base * (2 if self.speed_timer > 0 else 1)

    @property
    def stunned(self):
        return self.stun_timer > 0

    @property
    def damage_mult(self):
        return config.FURY_MULT if self.fury_timer > 0 else 1.0

    def stun(self, frames=config.STUN_FRAMES):
        if self.invulnerable:
            return False
        self.stun_timer = max(self.stun_timer, frames)
        self.charge_timer = 0
        self.kick_charge = self.pass_charge = 0
        return True

    def reset_round(self, x, y, facing):
        """Volta ao estado inicial para um novo round (mantém as estatísticas da partida)."""
        self.x, self.y = x, y
        self.facing = facing
        self.hp = self.stats.max_hp
        self.vx = self.vy = 0.0
        self.input = (0.0, 0.0)
        self.knock = [0.0, 0.0]
        for name in ("attack_cd", "ability_cd", "dash_timer", "dash_cd", "charge_timer", "speed_timer",
                     "invulnerable_timer", "stun_timer", "fury_timer", "hit_flash", "melee_flash",
                     "shoot_flash", "teleport_flash"):
            setattr(self, name, 0)
        self.trail.clear()

    # ── comandos ─────────────────────────────
    def steer(self, dx, dy):
        mag = math.hypot(dx, dy)
        if mag > 1:
            dx, dy = dx / mag, dy / mag
        self.input = (dx, dy)
        if mag > 0.1:
            self.facing = (dx / mag, dy / mag)

    def face(self, target):
        d = self.direction_to(target)
        if d != (0.0, 0.0):
            self.facing = d

    def dash(self, direction=None, frames=config.DASH_FRAMES, cooldown=config.DASH_COOLDOWN):
        if self.dash_cd > 0 or self.charge_timer > 0:
            return False
        dx, dy = direction or self.input
        if not (dx or dy):
            dx, dy = self.facing
        mag = math.hypot(dx, dy) or 1
        self.dash_dir = (dx / mag, dy / mag)
        self.dash_timer = frames
        self.dash_len = frames
        self.dash_cd = cooldown
        self.kicked_dust = True
        return True

    def start_charge(self, direction, damage):
        self.charge_dir = direction
        self.charge_timer = 20
        self.charge_damage = damage
        self.facing = direction

    def switch_weapon(self):
        if len(self.weapons) < 2:
            return False
        self.weapon_index = (self.weapon_index + 1) % len(self.weapons)
        self.attack_cd = max(self.attack_cd, 10)
        return True

    def attack(self, match, target):
        if self.attack_cd > 0 or target is None or self.stunned:
            return False
        self.face(target)
        weapon = self.weapon
        dist = self.distance_to(target)
        if weapon.is_melee:
            self.melee_flash = 12
            self.attack_cd = weapon.cooldown
            match.assets.play("shoot", 0.4)
            self._deflect_bullets(match)
            if dist <= weapon.reach + target.radius:
                target.take_damage(round(weapon.damage * self.damage_mult), self.x, self.y,
                                   attacker=self, match=match)
            return True
        damage = round(proximity_damage(dist, weapon.damage) * self.damage_mult)
        explosive = self.stats.key == "aryel"
        match.spawn_bullet(self, *self.facing, weapon.bullet_speed, damage, explosive=explosive)
        self.attack_cd = weapon.cooldown
        self.shoot_flash = 5
        match.assets.play("shoot" if match.frame % 3 else "shoot2", 0.3)
        return True

    def _deflect_bullets(self, match):
        """O golpe corpo a corpo rebate os tiros que chegam pela frente."""
        reach = self.weapon.reach + 14
        fx, fy = self.facing
        blocked = 0
        for b in match.bullets:
            if b.owner is self or not b.alive:
                continue
            dx, dy = b.x - self.x, b.y - self.y
            dist = math.hypot(dx, dy)
            if dist < reach and (dx * fx + dy * fy) > 0.2 * dist:
                b.alive = False
                b.explosive = False
                blocked += 1
                match.burst(b.x, b.y, (250, 240, 200), 6, speed=3)
        if blocked:
            match.popup(self.x, self.y - 46, "DEFESA", theme.SKY)
            match.assets.play("barrier", 0.35)

    def use_ability(self, match, target):
        if not self.ability_ready or self.stunned:
            return False
        self.ability_cd = config.ABILITY_COOLDOWN
        self.ability.use(self, match, target)
        return True

    def take_damage(self, amount, sx=None, sy=None, attacker=None, match=None):
        if self.invulnerable or self.hp <= 0:
            return False
        dealt = min(amount, self.hp)
        self.hp -= dealt
        self.hit_flash = 6
        if sx is not None:
            dx, dy = self.x - sx, self.y - sy
            mag = math.hypot(dx, dy)
            if mag:
                force = min(11.0, 3 + amount * 0.22)    # golpe forte empurra mais
                self.knock = [dx / mag * force, dy / mag * force]
        if attacker is not None:
            attacker.damage_dealt += dealt
            attacker.hits += 1
        if match is not None:
            match.popup(self.x, self.y - 46, str(amount), theme.BONE if amount < 20 else theme.BRASS)
            match.burst(self.x, self.y - 10, (236, 230, 220), 5, speed=3)
            match.camera.shake(3 if amount < 20 else 6)
            match.hit_pause(min(8, 2 + amount // 6))
            match.assets.play("hit", 0.4)
        return True

    # ── simulação ────────────────────────────
    def _move(self, match, dx, dy):
        """Anda em passos de no máximo 8 px para não atravessar paredes finas em alta velocidade.
        Devolve True se bateu em alguma parede."""
        steps = max(1, math.ceil(max(abs(dx), abs(dy)) / 8))
        hit = False
        for _ in range(steps):
            self.x += dx / steps
            self.y += dy / steps
            if match.arena.resolve(self):
                hit = True
        return hit

    def update(self, match):
        self.age += 1
        for name in ("attack_cd", "ability_cd", "dash_cd", "speed_timer", "invulnerable_timer",
                     "super_cd", "kick_cd", "stun_timer", "fury_timer", "giant_timer", "sprint_timer",
                     "hit_flash", "melee_flash", "shoot_flash", "teleport_flash"):
            value = getattr(self, name)
            if value > 0:
                setattr(self, name, value - 1)
        if self.giant_timer == 0 and self.radius != config.PLAYER_RADIUS:
            self.radius = config.PLAYER_RADIUS
        if self.kicked_dust:
            self.kicked_dust = False
            match.dust(self.x, self.y + FEET, 6)

        if self.hp <= 0:
            self.vx *= 0.85
            self.vy *= 0.85
            self.x += self.vx
            self.y += self.vy
            match.arena.resolve(self)
            return

        moving_fast = False
        if self.dash_timer > 0:
            # arranca forte e desacelera (mesma distância total de antes)
            t = 1 - self.dash_timer / self.dash_len
            self.dash_timer -= 1
            step = self.stats.speed * config.DASH_SPEED_MULT * (1.5 - t)
            self._move(match, self.dash_dir[0] * step, self.dash_dir[1] * step)
            # ao terminar, sai andando na mesma direção em vez de parar seco
            self.vx, self.vy = self.dash_dir[0] * self.max_speed, self.dash_dir[1] * self.max_speed
            moving_fast = True
        elif self.charge_timer > 0:
            self.charge_timer -= 1
            step = self.stats.speed * 4
            if self._move(match, self.charge_dir[0] * step, self.charge_dir[1] * step):
                self.charge_timer = 0
                match.camera.shake(4)
            for other in match.opponents_of(self):
                if other.alive_in_match and self.distance_to(other) < self.radius + other.radius + 6:
                    other.take_damage(self.charge_damage, self.x, self.y, attacker=self, match=match)
                    self.charge_timer = 0
            moving_fast = True
        else:
            ix, iy = (0.0, 0.0) if self.stunned else self.input
            was_fast = math.hypot(self.vx, self.vy) > self.stats.speed * 0.8
            self.moving = abs(ix) > 0.05 or abs(iy) > 0.05
            if self.moving:
                turning = ix * self.vx + iy * self.vy < 0
                k = TURN_ACCELERATION if turning else ACCELERATION
                self.vx += (ix * self.max_speed - self.vx) * k
                self.vy += (iy * self.max_speed - self.vy) * k
                if turning and match.frame % 4 == 0 and math.hypot(self.vx, self.vy) > 1.5:
                    match.dust(self.x, self.y + FEET, 1)
            else:
                self.vx *= 1 - FRICTION
                self.vy *= 1 - FRICTION
                if abs(self.vx) < 0.1:
                    self.vx = 0.0
                if abs(self.vy) < 0.1:
                    self.vy = 0.0
            if was_fast and not self.moving and match.frame % 3 == 0:
                match.dust(self.x, self.y + FEET, 1)       # derrapada
            self._move(match, self.vx + self.knock[0], self.vy + self.knock[1])
            self.knock[0] *= 0.8
            self.knock[1] *= 0.8
            moving_fast = (self.speed_timer > 0 or self.sprint_timer > 0) and self.moving

        # rastro (turbo / esquiva / investida)
        if moving_fast and match.frame % 2 == 0:
            self.trail.append((self.x, self.y, self._direction(), self.anim_frame))
        if len(self.trail) > 4 or (self.trail and not moving_fast and match.frame % 2 == 0):
            self.trail.pop(0)

        # animação de caminhada
        if self.moving or moving_fast:
            self.anim_timer += 1
            speed = math.hypot(self.vx, self.vy)
            if self.anim_timer >= max(4, round(11 - speed * 1.3)):   # passos mais rápidos correndo
                self.anim_timer = 0
                self.anim_frame = (self.anim_frame + 1) % 4
        else:
            self.anim_frame = 0
            self.anim_timer = 0

    # ── desenho ──────────────────────────────
    def _direction(self):
        dx, dy = self.facing
        if abs(dx) >= abs(dy):
            return "direita" if dx > 0 else "esquerda"
        return "costas" if dy < 0 else "frente"

    def draw(self, surf, camera):
        ticks = self.age
        show_weapon = self.armed
        sx, sy = round(self.x - camera.x), round(self.y - camera.y)
        feet = sy + FEET
        direction = self._direction()

        # sombra e anel de identificação
        shadow = pygame.Rect(0, 0, 38 * self.radius // config.PLAYER_RADIUS, 12)
        shadow.center = (sx, feet)
        pygame.draw.ellipse(surf, (10, 8, 14), shadow)
        pygame.draw.ellipse(surf, self.ring_color, shadow.inflate(6, 4), 2)

        if self.hp <= 0:
            self._draw_fallen(surf, sx, feet, direction)
            return

        for i, (tx, ty, tdir, tframe) in enumerate(self.trail):
            ghost = self.sprites.flash(tdir, tframe).copy()
            ghost.fill((*self.stats.color, 255), special_flags=pygame.BLEND_RGBA_MULT)
            ghost.set_alpha(40 + 25 * i)
            surf.blit(ghost, ghost.get_rect(midbottom=(round(tx - camera.x), round(ty - camera.y) + FEET + 2)))

        bob = -1 if self.anim_frame in (1, 3) else 0
        hand = weapon_art.hand_point(sx, sy, direction, bob)
        swinging = self.melee_flash > 0 and self.weapon.is_melee
        swing = 1 - self.melee_flash / 12 if swinging else None
        recoil = 3 if self.shoot_flash > 2 else 0
        if show_weapon and direction == "costas" and not swinging:
            weapon_art.draw_weapon(surf, self.weapon.name, hand, direction, self.facing, recoil=recoil)

        if self.hit_flash > 0 and self.hit_flash % 2 == 0:
            img = self.sprites.flash(direction, self.anim_frame)
        else:
            img = self.sprites.frame(direction, self.anim_frame)
        if self.giant_timer > 0:
            img = pygame.transform.scale(img, (img.get_width() * 3 // 2, img.get_height() * 3 // 2))
        rect = img.get_rect(midbottom=(sx, feet + 2))
        surf.blit(img, rect)

        if self.fury_timer > 0 and (ticks // 3) % 3 == 0:
            glow = self.sprites.flash(direction, self.anim_frame).copy()
            glow.fill((255, 70, 50, 110), special_flags=pygame.BLEND_RGBA_MULT)
            surf.blit(glow, glow.get_rect(midbottom=rect.midbottom))

        if self.stun_timer > 0:
            for k in range(3):
                a = ticks * 0.15 + k * math.tau / 3
                px = sx + math.cos(a) * 14
                py = rect.top - 4 + math.sin(a) * 4
                pygame.draw.rect(surf, (250, 226, 120), (round(px) - 2, round(py) - 2, 4, 4))

        if self.invulnerable_timer > 0 and (ticks // 4) % 2 == 0:
            glow = self.sprites.flash(direction, self.anim_frame).copy()
            glow.fill((255, 210, 90, 120), special_flags=pygame.BLEND_RGBA_MULT)
            surf.blit(glow, rect)

        if show_weapon and (direction != "costas" or swinging):
            tip = weapon_art.draw_weapon(surf, self.weapon.name, hand, direction, self.facing,
                                         swing=swing, recoil=recoil)
            if self.shoot_flash > 0:
                fx, fy = round(tip[0]), round(tip[1])
                r = 1 + self.shoot_flash
                pygame.draw.rect(surf, (255, 236, 170), (fx - r, fy - r, r * 2, r * 2))
                pygame.draw.rect(surf, (255, 255, 255), (fx - r // 2, fy - r // 2, r, r))

        if swinging:
            weapon_art.draw_slash(surf, hand, self.facing, weapon_art.weapon_length(self.weapon.name) + 2,
                                  swing, self.stats.color)

        if self.teleport_flash > 0:
            r = 14 + (20 - self.teleport_flash) * 2
            pygame.draw.circle(surf, self.stats.color, (sx, sy - 14), r, 2)

    def _draw_fallen(self, surf, sx, feet, direction):
        img = self.sprites.frame("direita" if self.facing[0] >= 0 else "esquerda", 0)
        img = pygame.transform.rotate(img, 90 if self.facing[0] >= 0 else -90)
        gray = img.copy()
        gray.fill((150, 140, 150, 255), special_flags=pygame.BLEND_RGBA_MULT)
        surf.blit(gray, gray.get_rect(midbottom=(sx, feet + 4)))

    def draw_overlay(self, surf, camera, ui, show_hp=True):
        """Etiqueta e vida acima da cabeça, desenhadas na tela (fora do zoom)."""
        if self.hp <= 0:
            return
        sx, sy = camera.to_screen(self.x, self.y - 50)
        sx, sy = round(sx), round(sy)
        tag = ui.assets.text(self.label, theme.XS, self.color)
        tr = tag.get_rect(midbottom=(sx, sy - (8 if show_hp else 2)))
        surf.fill(theme.SHADOW, tr.inflate(6, 4))
        surf.blit(tag, tr)
        if show_hp:
            ratio = self.hp / self.stats.max_hp
            color = theme.MOSS if ratio > 0.5 else theme.BRASS if ratio > 0.25 else theme.BLOOD
            ui.bar(surf, (sx - 18, sy - 6, 36, 6), ratio, color)
