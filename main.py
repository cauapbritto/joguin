# -*- coding: utf-8 -*-
import os
import pygame
import math
import random

# --- Configurações Globais ---
SCREEN_WIDTH = 960
SCREEN_HEIGHT = 540
FPS = 60

# --- Cores ---
BLACK      = (0,   0,   0)
WHITE      = (255, 255, 255)
RED        = (255, 0,   0)
BLUE       = (0,   0,   255)
GREEN      = (0,   255, 0)
YELLOW     = (255, 215, 0)
ORANGE     = (255, 140, 0)
PURPLE     = (180, 0,   255)
CYAN       = (0,   230, 230)
PINK       = (255, 80,  180)
GOLD       = (255, 200, 0)
DARK_GRAY  = (50,  50,  50)
GRAY       = (100, 100, 100)
LIGHT_GRAY = (180, 180, 180)
TEAL       = (0,   200, 150)

# --- Cores da UI (tema escuro fantasia) ---
UI_BG        = (15,  12,  25)
UI_PANEL     = (22,  20,  35)
UI_PANEL_LIT = (35,  30,  50)
UI_BORDER    = (60,  55,  80)
UI_BORDER_LIT= (90,  80,  120)
UI_ACCENT    = (255, 200, 50)
UI_TEXT      = (220, 220, 230)
UI_TEXT_DIM  = (140, 135, 160)
UI_GOLD      = (255, 180, 30)
FLOOR_A      = (18,  16,  30)
FLOOR_B      = (22,  20,  35)
WALL_FILL    = (50,  45,  65)
WALL_EDGE    = (75,  65,  95)
WALL_SHADOW  = (30,  25,  40)

# --- Dano ---
BASE_BULLET_DAMAGE = 10
MAX_BULLET_DAMAGE  = 30
MELEE_RANGE        = 80

# ─────────────────────────────────────────────
#  STATS DOS PERSONAGENS
# ─────────────────────────────────────────────
class CharacterStats:
    def __init__(self, name, max_hp, speed, bullet_speed, shoot_cooldown,
                 color, ability_name, ability_desc, image_name, damage=10):
        self.name          = name
        self.max_hp        = max_hp
        self.speed         = speed
        self.bullet_speed  = bullet_speed
        self.shoot_cooldown= shoot_cooldown
        self.color         = color
        self.ability_name  = ability_name
        self.ability_desc  = ability_desc
        self.image_name    = image_name
        self.damage        = damage

WARRIOR  = CharacterStats("Guerreiro",  150, 3,  8,  30, BLUE,   "Investida",    "Avança sobre o inimigo causando 35 de dano", "warrior.png", damage=12)
SHOOTER  = CharacterStats("Atirador",    80, 4, 12,  15, CYAN,   "Rajada",      "Dispara 5 balas em leque", "shooter.png", damage=8)
TANK     = CharacterStats("Tanque",     250, 2,  7,  45, GRAY,   "Muralha",     "Cria barreira que bloqueia balas por 4s", "tank.png", damage=15)
NINJA    = CharacterStats("Ninja",      100, 5,  9,  20, TEAL,   "Shuriken",    "Lança 3 shurikens de alto dano", "ninja.png", damage=10)
SPEEDSTER= CharacterStats("Velocista",  100, 3,  9,  22, YELLOW, "Turbo",       "Velocidade 3x por 4s", "speedster.png", damage=9)
BOMBER   = CharacterStats("Bombardeiro",130, 3,  8,  35, ORANGE, "Explosão",    "Bala que explode ao impacto", "bomber.png", damage=14)
GHOST    = CharacterStats("Fantasma",   110, 4,  9,  25, PURPLE, "Teletransporte","Teleporta para posição aleatória", "ghost.png", damage=11)
TITAN    = CharacterStats("Titã",       200, 2,  7,  40, GOLD,   "Invulnerável","Invulnerável por 5s", "titan.png", damage=13)

CHARACTER_TYPES = [WARRIOR, SHOOTER, TANK, NINJA, SPEEDSTER, BOMBER, GHOST, TITAN]

ASSET_DIR   = "assets"
UI_DIR      = os.path.join(ASSET_DIR, "ui")
FONT_DIR    = os.path.join(ASSET_DIR, "font")
TILES_DIR   = os.path.join(ASSET_DIR, "tiles")
IMAGE_SIZE  = (120, 120)

# ─────────────────────────────────────────────
#  SPRITES PROCEDURAIS ANIMADOS
# ─────────────────────────────────────────────
def _draw_limb(surf, color, x1, y1, x2, y2, width):
    dx = x2 - x1
    dy = y2 - y1
    length = max(1, int(math.sqrt(dx*dx + dy*dy)))
    angle = math.degrees(math.atan2(-dy, dx))
    limb = pygame.Surface((length, width), pygame.SRCALPHA)
    limb.fill(color)
    rotated = pygame.transform.rotate(limb, angle)
    surf.blit(rotated, (x1 - rotated.get_width() // 2, y1 - rotated.get_height() // 2))


def _generate_frame(stats, frame):
    """Gera um frame (120x120) para um personagem. frame=0/1 alterna pernas."""
    surf = pygame.Surface(IMAGE_SIZE, pygame.SRCALPHA)
    w, h = IMAGE_SIZE
    cx, cy = w // 2, h // 2 + 6
    col = stats.color

    leg_swing = 7
    leg_off = leg_swing if frame == 0 else -leg_swing

    # ── Sombra ──
    pygame.draw.ellipse(surf, (0, 0, 0, 50), (cx - 18, cy + 28, 36, 8))

    # ── Perna esquerda ──
    ll_x = cx - 7 + leg_off
    _draw_limb(surf, col, cx - 7, cy + 6, ll_x, cy + 30, 6)
    pygame.draw.ellipse(surf, DARK_GRAY, (ll_x - 4, cy + 28, 8, 5))

    # ── Perna direita ──
    rl_x = cx + 7 - leg_off
    _draw_limb(surf, col, cx + 7, cy + 6, rl_x, cy + 30, 6)
    pygame.draw.ellipse(surf, DARK_GRAY, (rl_x - 4, cy + 28, 8, 5))

    # ── Corpo ──
    body_t = cy - 12
    body_b = cy + 8
    body_w = 22
    body_rect = pygame.Rect(cx - body_w // 2, body_t, body_w, body_b - body_t)
    pygame.draw.ellipse(surf, col, body_rect)
    pygame.draw.ellipse(surf, WHITE, body_rect, 1)

    # ── Braços ──
    arm_len = 16
    arm_w = 4
    shoulder_y = body_t + 4
    arm_off = -leg_off // 2

    la_x = cx - body_w // 2 - 2 - abs(arm_off)
    la_y = shoulder_y + arm_len
    _draw_limb(surf, col, cx - body_w // 2, shoulder_y, la_x, la_y, arm_w)

    ra_x = cx + body_w // 2 + 2 + abs(arm_off)
    ra_y = shoulder_y + arm_len
    _draw_limb(surf, col, cx + body_w // 2, shoulder_y, ra_x, ra_y, arm_w)

    # ── Cabeça ──
    head_r = 11
    head_y = body_t - head_r + 1
    pygame.draw.circle(surf, col, (cx, head_y), head_r)

    # Olhos
    eye_y = head_y - 1
    for ex in (-4, 4):
        pygame.draw.circle(surf, WHITE, (cx + ex, eye_y), 3)
        pygame.draw.circle(surf, BLACK, (cx + ex, eye_y), 1.5)
        pygame.draw.circle(surf, WHITE, (cx + ex - 1, eye_y - 1), 1)

    # Blush
    blush = pygame.Surface((6, 3), pygame.SRCALPHA)
    blush.fill((255, 150, 150, 80))
    surf.blit(blush, (cx - 9, head_y + 1))
    surf.blit(blush, (cx + 3, head_y + 1))

    # ── Acessórios únicos por classe ──
    name = stats.name

    if name == "Guerreiro":
        # Elmo
        pygame.draw.rect(surf, GRAY, (cx - 10, head_y - head_r - 2, 20, 7), border_radius=3)
        pygame.draw.rect(surf, WHITE, (cx - 8, head_y - head_r + 1, 16, 3))
        # Espada
        sword_x = ra_x + 2
        _draw_limb(surf, WHITE, sword_x, ra_y - 4, sword_x + 4, ra_y - 26, 3)
        _draw_limb(surf, GOLD, sword_x - 2, ra_y - 12, sword_x + 6, ra_y - 12, 3)
        # Escudo
        _draw_limb(surf, GRAY, la_x, la_y - 6, la_x, la_y - 22, 10)

    elif name == "Atirador":
        # Chapéu
        pygame.draw.polygon(surf, GRAY, [
            (cx - 12, head_y - head_r + 2),
            (cx + 12, head_y - head_r + 2),
            (cx + 3, head_y - head_r - 14),
            (cx - 3, head_y - head_r - 14),
        ])
        pygame.draw.rect(surf, GRAY, (cx - 4, head_y - head_r - 14, 8, 3))
        # Rifle
        _draw_limb(surf, DARK_GRAY, ra_x + 2, ra_y - 8, ra_x + 18, ra_y - 12, 4)

    elif name == "Tanque":
        # Capacete
        pygame.draw.rect(surf, DARK_GRAY, (cx - 9, head_y - head_r - 3, 18, 8), border_radius=4)
        pygame.draw.rect(surf, CYAN, (cx - 6, head_y - 4, 12, 4), border_radius=1)
        # Corpo largo
        big_rect = pygame.Rect(cx - 15, body_t - 2, 30, body_b - body_t + 4)
        pygame.draw.ellipse(surf, col, big_rect)
        pygame.draw.ellipse(surf, WHITE, big_rect, 1)
        # Escudo grande
        _draw_limb(surf, GRAY, la_x - 2, la_y - 4, la_x - 2, la_y - 26, 14)
        pygame.draw.rect(surf, WHITE, (la_x - 9, la_y - 26, 14, 22), 1)

    elif name == "Ninja":
        # Faixa na cabeça
        pygame.draw.rect(surf, RED, (cx - 13, head_y - 5, 26, 4))
        _draw_limb(surf, RED, cx + 13, head_y - 5, cx + 22, head_y + 3, 2)
        _draw_limb(surf, RED, cx - 13, head_y - 5, cx - 22, head_y + 3, 2)
        # Máscara
        pygame.draw.rect(surf, DARK_GRAY, (cx - 8, head_y + 1, 16, 7), border_radius=3)
        # Kunai
        _draw_limb(surf, GRAY, ra_x + 1, ra_y - 6, ra_x + 10, ra_y - 20, 2)
        pygame.draw.circle(surf, GRAY, (ra_x + 10, ra_y - 20), 3)

    elif name == "Velocista":
        # Capacete aerodinâmico
        dx = 4 if frame == 0 else -4
        cap = pygame.Surface((28, head_r * 2), pygame.SRCALPHA)
        pygame.draw.ellipse(cap, (200, 180, 0), (0, 0, 28, head_r * 2))
        surf.blit(cap, (cx - 9 + dx // 2, head_y - head_r - 1))
        # Redesenha cabeça por cima
        pygame.draw.circle(surf, col, (cx, head_y), head_r)
        # Olhos (com detalhe de velocidade)
        for ex in (-4, 4):
            pygame.draw.circle(surf, WHITE, (cx + ex, eye_y), 3)
            pygame.draw.circle(surf, BLACK, (cx + ex, eye_y), 2)
        # Linhas de velocidade
        for i in range(3):
            sy = body_t + i * 6 + 2
            _draw_limb(surf, (255, 255, 100), cx - 11, sy, cx - 20 - i * 4, sy, 2)

    elif name == "Bombardeiro":
        # Mochila
        pygame.draw.rect(surf, DARK_GRAY, (cx - 13, body_t + 2, 26, 16), border_radius=4)
        pygame.draw.rect(surf, RED, (cx - 9, body_t + 5, 5, 5))
        pygame.draw.rect(surf, RED, (cx + 4, body_t + 5, 5, 5))
        # Bomba na mão
        bomb_x = ra_x + 4
        pygame.draw.circle(surf, DARK_GRAY, (bomb_x, ra_y - 6), 7)
        _draw_limb(surf, RED, bomb_x, ra_y - 13, bomb_x, ra_y - 20, 2)
        pygame.draw.circle(surf, ORANGE, (bomb_x, ra_y - 20), 2)

    elif name == "Fantasma":
        # Corpo esfumaçado (sem pernas, ondulado)
        for i in range(4):
            wy = body_b + i * 7
            wx = 6 * math.sin(i * 0.8 + frame * math.pi)
            alpha = max(30, 150 - i * 30)
            fumaça = pygame.Surface((30, 12), pygame.SRCALPHA)
            pygame.draw.ellipse(fumaça, (*col, alpha), (0, 0, 30, 12))
            surf.blit(fumaça, (int(cx - 15 + wx), int(wy)))
        # Capa
        capa = pygame.Surface((30, 30), pygame.SRCALPHA)
        pygame.draw.ellipse(capa, (*col, 100), (0, 0, 30, 30))
        surf.blit(capa, (cx - 15, body_t - 4))
        # Redesenha cabeça
        pygame.draw.circle(surf, col, (cx, head_y), head_r)
        # Olhos brilhantes
        for ex in (-5, 5):
            pygame.draw.circle(surf, WHITE, (cx + ex, eye_y), 4)
            pygame.draw.circle(surf, CYAN, (cx + ex, eye_y), 2)

    elif name == "Titã":
        # Corpo maior
        big_rect = pygame.Rect(cx - 16, body_t - 4, 32, body_b - body_t + 8)
        pygame.draw.ellipse(surf, col, big_rect)
        pygame.draw.ellipse(surf, WHITE, big_rect, 2)
        # Coroa
        crown_pts = [
            (cx - 11, head_y - head_r + 1),
            (cx - 9, head_y - head_r - 8),
            (cx - 4, head_y - head_r - 3),
            (cx, head_y - head_r - 10),
            (cx + 4, head_y - head_r - 3),
            (cx + 9, head_y - head_r - 8),
            (cx + 11, head_y - head_r + 1),
        ]
        pygame.draw.polygon(surf, GOLD, crown_pts)
        # Armadura
        pygame.draw.line(surf, WHITE, (cx - 10, body_t + 2), (cx + 10, body_t + 2), 2)
        pygame.draw.line(surf, WHITE, (cx - 8, body_t + 8), (cx + 8, body_t + 8), 2)
        # Ombreiras
        pygame.draw.circle(surf, GOLD, (cx - 13, shoulder_y), 6)
        pygame.draw.circle(surf, GOLD, (cx + 13, shoulder_y), 6)

    return surf


def generate_character_sprites():
    sprites = {}
    for ch in CHARACTER_TYPES:
        frames = [_generate_frame(ch, f) for f in range(2)]
        sprites[ch.image_name] = frames
    return sprites

# ─────────────────────────────────────────────
#  DANO POR PROXIMIDADE
# ─────────────────────────────────────────────
def calc_damage(dist, base=BASE_BULLET_DAMAGE):
    if dist <= MELEE_RANGE:
        t = 1.0 - (dist / MELEE_RANGE)
        return min(int(base + (MAX_BULLET_DAMAGE - base) * t), MAX_BULLET_DAMAGE)
    return base

# ─────────────────────────────────────────────
#  BALA
# ─────────────────────────────────────────────
class Bullet:
    def __init__(self, x, y, dir_x, dir_y, speed, color, damage, explosive=False):
        self.x         = x
        self.y         = y
        self.dir_x     = dir_x
        self.dir_y     = dir_y
        self.speed     = speed
        self.radius    = 5 if explosive else 4
        self.color     = color
        self.damage    = damage
        self.explosive = explosive
        self.alive     = True

    def update(self):
        self.x += self.dir_x * self.speed
        self.y += self.dir_y * self.speed

    def draw(self, screen):
        if self.explosive:
            pygame.draw.circle(screen, ORANGE, (int(self.x), int(self.y)), self.radius + 2)
            pygame.draw.circle(screen, RED,    (int(self.x), int(self.y)), self.radius)
        elif self.damage >= MAX_BULLET_DAMAGE * 0.8:
            pygame.draw.circle(screen, YELLOW, (int(self.x), int(self.y)), self.radius + 2)
        elif self.damage >= BASE_BULLET_DAMAGE * 1.5:
            pygame.draw.circle(screen, ORANGE, (int(self.x), int(self.y)), self.radius + 1)
        else:
            pygame.draw.circle(screen, self.color, (int(self.x), int(self.y)), self.radius)

# ─────────────────────────────────────────────
#  EXPLOSÃO (efeito visual + dano em área)
# ─────────────────────────────────────────────
class Explosion:
    def __init__(self, x, y, radius=60, damage=0, owner=None):
        self.x       = x
        self.y       = y
        self.radius  = radius
        self.damage  = damage
        self.owner   = owner
        self.timer   = 20  # frames
        self.max_t   = 20
        self.damage_dealt = False

    def update(self):
        self.timer -= 1

    def draw(self, screen):
        if self.timer <= 0:
            return
        alpha = int(255 * (self.timer / self.max_t))
        r     = int(self.radius * (1 - self.timer / self.max_t) + 10)
        surf  = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
        pygame.draw.circle(surf, (*ORANGE, alpha), (r, r), r)
        pygame.draw.circle(surf, (*YELLOW, alpha // 2), (r, r), r // 2)
        screen.blit(surf, (int(self.x) - r, int(self.y) - r))

    @property
    def done(self):
        return self.timer <= 0

# ─────────────────────────────────────────────
#  JOGADOR
# ─────────────────────────────────────────────
class Player:
    ABILITY_COOLDOWN = 600   # 10 segundos entre usos

    def __init__(self, x, y, controls, char_stats, name="Jogador"):
        self.x               = x
        self.y               = y
        self.radius          = 15
        self.color           = char_stats.color
        self.controls        = controls
        self.char_stats      = char_stats
        self.name            = name
        self.hp              = char_stats.max_hp
        self.speed           = char_stats.speed
        self.bullet_speed    = char_stats.bullet_speed
        self.shoot_cooldown  = char_stats.shoot_cooldown
        self.current_cooldown= 0
        self.bullets         = []
        self.last_direction  = (0, 1)
        self.melee_flash     = 0

        # Poder especial
        self.ability_cooldown    = 0   # frames restantes para poder estar disponível
        self.ability_active      = False
        self.ability_timer       = 0   # duração restante do efeito ativo

        # Velocista
        self.speed_boost         = False

        # Titã
        self.invulnerable        = False

        # Guerreiro (Investida)
        self.charging            = False
        self.charge_timer        = 0
        self.charge_dir          = (0, 0)

        # Tanque (Muralha)
        self.barrier             = None

        # Animação
        self.moving              = False
        self.anim_frame          = 0
        self.anim_timer          = 0

        # Efeitos visuais
        self.teleport_flash      = 0
        self.explosions          = []  # explosões pertencentes a este jogador

    # ── utilidades ──────────────────────────────
    def distance_to(self, other):
        return math.sqrt((self.x - other.x)**2 + (self.y - other.y)**2)

    def _normalize(self, dx, dy):
        mag = math.sqrt(dx**2 + dy**2)
        return (dx / mag, dy / mag) if mag else (0, 1)

    # ── movimento ───────────────────────────────
    def move(self, dx, dy):
        self.moving = (dx != 0 or dy != 0)
        if self.moving:
            self.last_direction = (dx, dy)
        spd = self.speed * (3 if self.speed_boost else 1)
        # Move no eixo X e resolve colisão
        self.x = max(self.radius, min(SCREEN_WIDTH - self.radius, self.x + dx * spd))
        for wall in walls:
            if wall.collides_with_player(self):
                self.x -= dx * spd
                break
        # Move no eixo Y e resolve colisão
        self.y = max(self.radius, min(SCREEN_HEIGHT - self.radius, self.y + dy * spd))
        for wall in walls:
            if wall.collides_with_player(self):
                self.y -= dy * spd
                break

    # ── tiro ────────────────────────────────────
    def shoot(self, enemy):
        if self.current_cooldown > 0:
            return
        dir_x, dir_y = self._normalize(*self.last_direction)
        dist   = self.distance_to(enemy)
        damage = calc_damage(dist, base=self.char_stats.damage)
        explosive = (self.char_stats == BOMBER)
        bullet = Bullet(self.x, self.y, dir_x, dir_y,
                        self.bullet_speed, self.color, damage, explosive)
        self.bullets.append(bullet)
        self.current_cooldown = self.shoot_cooldown
        if dist <= MELEE_RANGE:
            self.melee_flash = 8

    # ── poder especial ──────────────────────────
    def use_ability(self, enemy, walls):
        if self.ability_cooldown > 0:
            return
        cs = self.char_stats
        self.ability_cooldown = self.ABILITY_COOLDOWN

        if cs == WARRIOR:
            # Investida — avança em direção ao inimigo
            dx = enemy.x - self.x
            dy = enemy.y - self.y
            mag = math.sqrt(dx*dx + dy*dy)
            if mag > 0:
                self.charge_dir = (dx / mag, dy / mag)
            self.charging = True
            self.charge_timer = 20

        elif cs == SHOOTER:
            # Rajada — 5 balas em leque de 60°
            dir_x, dir_y = self._normalize(*self.last_direction)
            base_angle = math.atan2(-dir_y, dir_x)
            for i in range(5):
                angle = base_angle + math.radians(30 * (i / 4 - 0.5))
                ddx = math.cos(angle)
                ddy = -math.sin(angle)
                b = Bullet(self.x, self.y, ddx, ddy, self.bullet_speed,
                           self.color, self.char_stats.damage)
                self.bullets.append(b)

        elif cs == TANK:
            # Muralha — barreira na direção atual
            dir_x, dir_y = self._normalize(*self.last_direction)
            bx = self.x + dir_x * 40
            by = self.y + dir_y * 40
            self.barrier = Barrier(bx, by, dir_x, dir_y, 4 * FPS)

        elif cs == NINJA:
            # Shuriken — 3 shurikens em leque de 45°
            dir_x, dir_y = self._normalize(*self.last_direction)
            base_angle = math.atan2(-dir_y, dir_x)
            for i in range(3):
                angle = base_angle + math.radians(22.5 * (i - 1))
                ddx = math.cos(angle)
                ddy = -math.sin(angle)
                b = Bullet(self.x, self.y, ddx, ddy, self.bullet_speed + 2,
                           self.color, 15)
                self.bullets.append(b)

        elif cs == SPEEDSTER:
            self.speed_boost   = True
            self.ability_active= True
            self.ability_timer = 4 * FPS

        elif cs == BOMBER:
            for angle in range(0, 360, 45):
                rad   = math.radians(angle)
                dx, dy= math.cos(rad), math.sin(rad)
                b = Bullet(self.x, self.y, dx, dy, self.bullet_speed,
                           ORANGE, 25, explosive=True)
                self.bullets.append(b)

        elif cs == GHOST:
            for _ in range(50):
                nx = random.randint(50, SCREEN_WIDTH  - 50)
                ny = random.randint(50, SCREEN_HEIGHT - 50)
                ok = all(
                    not w.collides_with_point(nx, ny, self.radius + 5)
                    for w in walls
                )
                if ok:
                    self.x, self.y = nx, ny
                    break
            self.teleport_flash = 20

        elif cs == TITAN:
            self.invulnerable    = True
            self.ability_active  = True
            self.ability_timer   = 5 * FPS

    # ── update ──────────────────────────────────
    def update(self, walls, enemy=None):
        if self.current_cooldown > 0: self.current_cooldown -= 1
        if self.ability_cooldown  > 0: self.ability_cooldown  -= 1
        if self.melee_flash       > 0: self.melee_flash        -= 1
        if self.teleport_flash    > 0: self.teleport_flash     -= 1

        # Animação de passos
        if self.moving:
            self.anim_timer += 1
            if self.anim_timer >= 8:
                self.anim_timer = 0
                self.anim_frame = 1 - self.anim_frame
        else:
            self.anim_frame = 0
            self.anim_timer = 0

        # Efeitos com duração
        if self.ability_active:
            self.ability_timer -= 1
            if self.ability_timer <= 0:
                self.ability_active = False
                self.speed_boost    = False
                self.invulnerable   = False

        # Investida (Guerreiro)
        if self.charging:
            self.charge_timer -= 1
            spd = self.speed * 4
            self.x += self.charge_dir[0] * spd
            self.y += self.charge_dir[1] * spd
            self.x = max(self.radius, min(SCREEN_WIDTH - self.radius, self.x))
            self.y = max(self.radius, min(SCREEN_HEIGHT - self.radius, self.y))
            if self.charge_timer <= 0:
                self.charging = False
            # Dano no inimigo se colidir
            if enemy and self.distance_to(enemy) < self.radius + enemy.radius + 5:
                enemy.take_damage(35)
                self.charging = False

        # Muralha (Tanque)
        if self.barrier:
            self.barrier.update()
            if self.barrier.done:
                self.barrier = None

        # Atualizar balas (com verificação de barreiras)
        for bullet in list(self.bullets):
            bullet.update()
            out = not (0 < bullet.x < SCREEN_WIDTH and 0 < bullet.y < SCREEN_HEIGHT)
            hit_wall = any(w.collides_with_bullet(bullet) for w in walls)
            hit_barrier = False
            if enemy and enemy.barrier and enemy.barrier.collides_with_bullet(bullet):
                hit_barrier = True
            if out or hit_wall or hit_barrier:
                if bullet.explosive:
                    self.explosions.append(Explosion(bullet.x, bullet.y, damage=bullet.damage, owner=self))
                self.bullets.remove(bullet)

        # Atualizar explosões
        for exp in list(self.explosions):
            exp.update()
            if exp.done:
                self.explosions.remove(exp)

    def take_damage(self, amount):
        if not self.invulnerable:
            self.hp = max(0, self.hp - amount)

    # ── desenho ─────────────────────────────────
    def draw(self, screen, enemy=None):
        # Anel de melee range
        if enemy and self.distance_to(enemy) <= MELEE_RANGE:
            pygame.draw.circle(screen, ORANGE,
                               (int(self.x), int(self.y)), MELEE_RANGE, 1)

        # Flash de teleporte
        if self.teleport_flash > 0:
            r = self.radius + self.teleport_flash * 2
            pygame.draw.circle(screen, PURPLE, (int(self.x), int(self.y)), r, 2)

        # Aura de invulnerabilidade
        if self.invulnerable:
            t   = pygame.time.get_ticks()
            glow= self.radius + 6 + int(4 * math.sin(t * 0.01))
            pygame.draw.circle(screen, GOLD, (int(self.x), int(self.y)), glow, 3)

        # Aura de velocidade
        if self.speed_boost:
            t   = pygame.time.get_ticks()
            glow= self.radius + 4 + int(3 * math.sin(t * 0.015))
            pygame.draw.circle(screen, YELLOW, (int(self.x), int(self.y)), glow, 2)

        # Sombra
        pygame.draw.circle(screen, DARK_GRAY, (int(self.x + 3), int(self.y + 3)), self.radius)

        # Corpo / sprite do personagem
        frames = character_images.get(self.char_stats.image_name)
        if frames:
            img = frames[self.anim_frame]
            rect = img.get_rect(center=(int(self.x), int(self.y)))
            screen.blit(img, rect)
            if self.melee_flash > 0:
                overlay = pygame.Surface(rect.size, pygame.SRCALPHA)
                overlay.fill((255, 255, 255, 80))
                screen.blit(overlay, rect)
            pygame.draw.ellipse(screen, WHITE, rect.inflate(4, 4), 2)
        else:
            body_color = WHITE if (self.melee_flash > 0 and self.melee_flash % 2 == 0) else self.color
            pygame.draw.circle(screen, body_color, (int(self.x), int(self.y)), self.radius)
            pygame.draw.circle(screen, WHITE,      (int(self.x), int(self.y)), self.radius, 2)

        # Barra de vida
        bw   = 40
        bh   = 5
        bx   = int(self.x - bw / 2)
        by   = int(self.y - self.radius - 10)
        ratio= max(0, self.hp / self.char_stats.max_hp)
        hp_color = GREEN if ratio > 0.5 else (ORANGE if ratio > 0.25 else RED)
        draw_styled_bar(screen, bx, by, bw, bh, ratio, fg_color=hp_color)

        hp_text = f"{self.hp}/{self.char_stats.max_hp}"
        draw_text(screen, hp_text, 14, WHITE, bx + bw // 2, by - 8)

        # Explosões visuais
        for exp in self.explosions:
            exp.draw(screen)

# ─────────────────────────────────────────────
#  PAREDE
# ─────────────────────────────────────────────
class Wall:
    def __init__(self, x, y, w, h):
        self.rect = pygame.Rect(x, y, w, h)

    def draw(self, screen):
        r = self.rect
        pygame.draw.rect(screen, WALL_SHADOW, (r.x - 2, r.y - 1, r.w + 4, r.h + 2), border_radius=4)
        pygame.draw.rect(screen, WALL_FILL, r, border_radius=3)
        pygame.draw.rect(screen, WALL_EDGE, r, 2, border_radius=3)
        top_highlight = (WALL_EDGE[0] + 40, WALL_EDGE[1] + 40, WALL_EDGE[2] + 40)
        pygame.draw.line(screen, top_highlight, (r.x + 3, r.y + 2), (r.right - 3, r.y + 2), 1)

    def collides_with_player(self, player):
        cx, cy = player.x, player.y
        rx = max(self.rect.left, min(cx, self.rect.right))
        ry = max(self.rect.top,  min(cy, self.rect.bottom))
        return (cx - rx)**2 + (cy - ry)**2 < player.radius**2

    def collides_with_point(self, px, py, radius):
        rx = max(self.rect.left, min(px, self.rect.right))
        ry = max(self.rect.top,  min(py, self.rect.bottom))
        return (px - rx)**2 + (py - ry)**2 < radius**2

    def collides_with_bullet(self, bullet):
        return self.rect.colliderect(
            pygame.Rect(bullet.x - bullet.radius, bullet.y - bullet.radius,
                        bullet.radius * 2, bullet.radius * 2)
        )

# ─────────────────────────────────────────────
#  BARREIRA (MURALHA DO TANQUE)
# ─────────────────────────────────────────────
class Barrier:
    def __init__(self, x, y, dir_x, dir_y, duration):
        w, h = 60, 20
        self.rect = pygame.Rect(x - w // 2, y - h // 2, w, h)
        self.timer = duration
        self.max_t = duration
        self.dir_x = dir_x
        self.dir_y = dir_y

    def update(self):
        self.timer -= 1

    def draw(self, screen):
        if self.timer <= 0:
            return
        alpha = int(200 * (self.timer / self.max_t))
        surf = pygame.Surface((self.rect.w, self.rect.h), pygame.SRCALPHA)
        surf.fill((100, 100, 200, alpha))
        pygame.draw.rect(surf, CYAN, surf.get_rect(), 2)
        screen.blit(surf, self.rect)

    def collides_with_bullet(self, bullet):
        return self.rect.colliderect(
            pygame.Rect(bullet.x - bullet.radius, bullet.y - bullet.radius,
                        bullet.radius * 2, bullet.radius * 2)
        )

    @property
    def done(self):
        return self.timer <= 0

# ─────────────────────────────────────────────
#  HELPERS
# ─────────────────────────────────────────────
def load_image(path, fallback=None, scale=None, colorkey=None):
    try:
        img = pygame.image.load(path).convert_alpha()
        if scale:
            img = pygame.transform.scale(img, scale)
        if colorkey:
            img.set_colorkey(colorkey)
        return img
    except (FileNotFoundError, pygame.error):
        return fallback


def draw_nine_slice(screen, img, rect, slice_size=4):
    img_w = img.get_width()
    img_h = img.get_height()
    x, y, w, h = rect

    if w < slice_size * 2 or h < slice_size * 2:
        screen.blit(pygame.transform.scale(img, (w, h)), (x, y))
        return

    tl = img.subsurface(0, 0, slice_size, slice_size)
    tc = img.subsurface(slice_size, 0, img_w - 2 * slice_size, slice_size)
    tr = img.subsurface(img_w - slice_size, 0, slice_size, slice_size)

    ml = img.subsurface(0, slice_size, slice_size, img_h - 2 * slice_size)
    mr = img.subsurface(img_w - slice_size, slice_size, slice_size, img_h - 2 * slice_size)

    bl = img.subsurface(0, img_h - slice_size, slice_size, slice_size)
    bc = img.subsurface(slice_size, img_h - slice_size, img_w - 2 * slice_size, slice_size)
    br = img.subsurface(img_w - slice_size, img_h - slice_size, slice_size, slice_size)

    cx = w - 2 * slice_size
    cy = h - 2 * slice_size

    screen.blit(tl, (x, y))
    screen.blit(tr, (x + w - slice_size, y))
    screen.blit(bl, (x, y + h - slice_size))
    screen.blit(br, (x + w - slice_size, y + h - slice_size))

    screen.blit(pygame.transform.scale(tc, (cx, slice_size)), (x + slice_size, y))
    screen.blit(pygame.transform.scale(bc, (cx, slice_size)), (x + slice_size, y + h - slice_size))
    screen.blit(pygame.transform.scale(ml, (slice_size, cy)), (x, y + slice_size))
    screen.blit(pygame.transform.scale(mr, (slice_size, cy)), (x + w - slice_size, y + slice_size))

    if cx > 0 and cy > 0:
        center = img.subsurface(slice_size, slice_size, img_w - 2 * slice_size, img_h - 2 * slice_size)
        screen.blit(pygame.transform.scale(center, (cx, cy)), (x + slice_size, y + slice_size))


def draw_panel(screen, rect, fill=UI_PANEL, border=UI_BORDER, radius=6, bevel=True):
    x, y, w, h = rect
    if bevel:
        pygame.draw.rect(screen, UI_BORDER_LIT, (x - 1, y - 1, w + 2, h + 2), border_radius=radius + 1)
        pygame.draw.rect(screen, UI_BORDER, (x, y, w, h), border_radius=radius)
        shadow = (fill[0] // 2, fill[1] // 2, fill[2] // 2)
        inner = (x + 2, y + 2, w - 4, h - 4)
        pygame.draw.rect(screen, shadow, inner, border_radius=max(1, radius - 2))
        pygame.draw.rect(screen, fill, (x + 1, y + 1, w - 2, h - 2), border_radius=max(1, radius - 1))
    else:
        pygame.draw.rect(screen, border, (x, y, w, h), border_radius=radius)
        pygame.draw.rect(screen, fill, (x + 1, y + 1, w - 2, h - 2), border_radius=max(1, radius - 1))


def draw_styled_bar(screen, x, y, w, h, ratio, fg_color=GREEN, bg_color=DARK_GRAY, label="", label_side="top"):
    pygame.draw.rect(screen, bg_color, (x, y, w, h), border_radius=3)
    if ratio > 0:
        fw = max(2, int(w * ratio))
        pygame.draw.rect(screen, fg_color, (x + 1, y + 1, fw - 2, h - 2), border_radius=2)
    pygame.draw.rect(screen, UI_BORDER, (x, y, w, h), 1, border_radius=3)
    if label:
        ly = y - 9 if label_side == "top" else y + h + 4
        draw_text(screen, label, 16, UI_TEXT, x + w // 2, ly)


FONT_CACHE = {}
PIXEL_FONT_PATH = os.path.join(FONT_DIR, "PressStart2P-Regular.ttf")
PIXEL_FONT_OK = os.path.isfile(PIXEL_FONT_PATH)

def _get_font(size):
    key = ("pixel" if PIXEL_FONT_OK else "default", size)
    if key not in FONT_CACHE:
        try:
            if PIXEL_FONT_OK:
                FONT_CACHE[key] = pygame.font.Font(PIXEL_FONT_PATH, size)
            else:
                FONT_CACHE[key] = pygame.font.Font(None, size)
        except pygame.error:
            FONT_CACHE[key] = pygame.font.Font(None, size)
    return FONT_CACHE[key]

def draw_text(screen, text, size, color, x, y, center=True):
    font = _get_font(size)
    surf = font.render(text, True, color)
    rect = surf.get_rect()
    if center: rect.center   = (x, y)
    else:      rect.topleft  = (x, y)
    screen.blit(surf, rect)

def draw_hud(screen, p1, p2):
    dist  = p1.distance_to(p2)
    melee = dist <= MELEE_RANGE

    # Painel superior com nomes e distância
    panel_h = 48 + (18 if melee else 0)
    draw_panel(screen, (SCREEN_WIDTH // 2 - 120, 6, 240, panel_h), fill=(20, 18, 35, 180), bevel=False)
    draw_text(screen, f"{p1.name}",  20, p1.color, SCREEN_WIDTH // 2 - 80, 14)
    draw_text(screen, f"{p2.name}",  20, p2.color, SCREEN_WIDTH // 2 + 80, 14)
    draw_text(screen, f"{int(dist)}px", 16, ORANGE if melee else UI_TEXT_DIM, SCREEN_WIDTH // 2, 35)
    if melee:
        draw_text(screen, "CORPO A CORPO!", 16, UI_GOLD, SCREEN_WIDTH // 2, 52)

    # Painel inferior esquerdo (P1)
    draw_panel(screen, (8, SCREEN_HEIGHT - 62, 220, 54), fill=(20, 18, 35, 200), bevel=True)
    ab_ratio = 1.0 - (p1.ability_cooldown / Player.ABILITY_COOLDOWN) if Player.ABILITY_COOLDOWN else 1.0
    ab_label = f"[Q] {p1.char_stats.ability_name}"
    ab_label = ab_label if len(ab_label) <= 12 else ab_label[:11] + "."
    draw_styled_bar(screen, 14, SCREEN_HEIGHT - 50, 90, 8, ab_ratio,
                    fg_color=GREEN if ab_ratio >= 1.0 else CYAN, label=ab_label)
    sc_ratio = 1.0 - (p1.current_cooldown / p1.shoot_cooldown) if p1.shoot_cooldown else 1.0
    sc_color = GREEN if sc_ratio >= 1.0 else ORANGE
    draw_styled_bar(screen, 120, SCREEN_HEIGHT - 50, 50, 8, sc_ratio, fg_color=sc_color, label="TIRO", label_side="bottom")
    if p1.ability_active:
        t_left = p1.ability_timer // FPS + 1
        draw_text(screen, f"ATIVO {t_left}s", 14, UI_GOLD, 100, SCREEN_HEIGHT - 28)

    # Painel inferior direito (P2)
    draw_panel(screen, (SCREEN_WIDTH - 228, SCREEN_HEIGHT - 62, 220, 54), fill=(20, 18, 35, 200), bevel=True)
    ab_ratio2 = 1.0 - (p2.ability_cooldown / Player.ABILITY_COOLDOWN) if Player.ABILITY_COOLDOWN else 1.0
    ab_label2 = f"{p2.char_stats.ability_name} [.]"
    ab_label2 = ab_label2 if len(ab_label2) <= 12 else ab_label2[:11] + "."
    draw_styled_bar(screen, SCREEN_WIDTH - 104, SCREEN_HEIGHT - 50, 90, 8, ab_ratio2,
                    fg_color=GREEN if ab_ratio2 >= 1.0 else CYAN, label=ab_label2)
    sc_ratio2 = 1.0 - (p2.current_cooldown / p2.shoot_cooldown) if p2.shoot_cooldown else 1.0
    sc_color2 = GREEN if sc_ratio2 >= 1.0 else ORANGE
    draw_styled_bar(screen, SCREEN_WIDTH - 170, SCREEN_HEIGHT - 50, 50, 8, sc_ratio2, fg_color=sc_color2, label="TIRO", label_side="bottom")
    if p2.ability_active:
        t_left = p2.ability_timer // FPS + 1
        draw_text(screen, f"ATIVO {t_left}s", 14, UI_GOLD, SCREEN_WIDTH - 100, SCREEN_HEIGHT - 28)

# ─────────────────────────────────────────────
#  PAREDES DA ARENA
# ─────────────────────────────────────────────
walls = [
    Wall(100, 100, 50, 200),
    Wall(SCREEN_WIDTH - 150, 100, 50, 200),
    Wall(300, 200, 300, 50),
    Wall(300, SCREEN_HEIGHT - 250, 300, 50),
    Wall(50,  SCREEN_HEIGHT // 2 - 25, 50, 50),
    Wall(SCREEN_WIDTH - 100, SCREEN_HEIGHT // 2 - 25, 50, 50),
]

# ─────────────────────────────────────────────
#  INICIALIZAÇÃO PYGAME
# ─────────────────────────────────────────────
pygame.init()
pygame.display.set_caption("Soul Strike")
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.FULLSCREEN | pygame.SCALED)
clock  = pygame.time.Clock()

for d in (ASSET_DIR, UI_DIR, FONT_DIR, TILES_DIR):
    os.makedirs(d, exist_ok=True)

# ── TELA DE CARREGAMENTO ──
particles = []
for _ in range(50):
    particles.append({
        'x': random.randint(0, SCREEN_WIDTH),
        'y': random.randint(0, SCREEN_HEIGHT),
        'vx': random.uniform(-0.8, 0.8),
        'vy': random.uniform(-0.8, -0.2),
        'size': random.randint(2, 6),
        'phase': random.uniform(0, math.pi * 2),
        'color': random.choice([GOLD, YELLOW, WHITE, ORANGE]),
    })

def draw_loading(progress, tip, ticks):
    screen.fill(BLACK)
    t = ticks * 0.001
    # Partículas douradas
    for p in particles:
        px = p['x'] + math.sin(t * 2 + p['phase']) * 30
        py = (p['y'] + t * 40) % SCREEN_HEIGHT
        alpha = int(150 + 105 * math.sin(t * 3 + p['phase']))
        clr = (*p['color'][:3], alpha)
        surf = pygame.Surface((p['size'] * 2, p['size'] * 2), pygame.SRCALPHA)
        pygame.draw.circle(surf, clr, (p['size'], p['size']), p['size'])
        screen.blit(surf, (int(px - p['size']), int(py - p['size'])))

    # Logo com glow pulsante
    glow = int(15 * math.sin(t * 2))
    for dy in (-1, 0, 1):
        draw_text(screen, "SOUL STRIKE", 66, (*UI_GOLD[:3], 30 + glow),
                  SCREEN_WIDTH // 2, SCREEN_HEIGHT // 3 - 30 + dy * 3,)
    draw_text(screen, "SOUL STRIKE", 66, WHITE,
              SCREEN_WIDTH // 2, SCREEN_HEIGHT // 3 - 30)

    # Subtítulo
    draw_text(screen, "Um duelo de heróis!", 22, UI_TEXT_DIM,
              SCREEN_WIDTH // 2, SCREEN_HEIGHT // 3 + 25)

    # Barra de progresso
    bw, bh = 420, 20
    bx = SCREEN_WIDTH // 2 - bw // 2
    by = SCREEN_HEIGHT // 2 + 35
    draw_styled_bar(screen, bx, by, bw, bh, progress, fg_color=UI_GOLD, label="")

    dots = '.' * (int(t * 3) % 4)
    draw_text(screen, f"Carregando{dots}", 24, UI_TEXT_DIM,
              SCREEN_WIDTH // 2, by + bh + 26)
    draw_text(screen, f"{int(progress * 100)}%", 18, UI_GOLD,
              SCREEN_WIDTH // 2, by + bh + 50)

    # Dica
    draw_text(screen, f"Dica: {tip}", 16, UI_TEXT_DIM,
              SCREEN_WIDTH // 2, SCREEN_HEIGHT - 30)

    pygame.display.flip()
    clock.tick(FPS)


# ─────────────────────────────────────────────
#  ESTADOS DO JOGO
# ─────────────────────────────────────────────
STATE_LOADING     = 0
STATE_NAME_INPUT  = 1
STATE_CHAR_SELECT = 2
STATE_VS_SCREEN   = 3
STATE_PLAYING     = 4
STATE_GAME_OVER   = 5

current_state = STATE_LOADING

vs_timer = 0
VS_DURATION = 150  # frames (~2.5s)

loading_tips = [
    "Aproxime-se para causar dano extra em combate corpo a corpo!",
    "Cada lutador tem um poder único. Ative com Q ou .",
    "Guerreiro causa dano alto de perto, Atirador é devastador à distância.",
    "Tanque é lento mas resistente. Ninja é rápido mas frágil.",
    "Use as paredes da arena para se proteger dos tiros!",
    "A barra de poder mostra quando seu especial está disponível.",
    "Mire com o movimento e atire na direção oposta para surpreender.",
    "Cada classe tem um estilo único — encontre o seu!",
]

# Gera sprites com progresso visual
character_images = {}
total = len(CHARACTER_TYPES)
start = pygame.time.get_ticks()
for i, ch in enumerate(CHARACTER_TYPES):
    frames = [_generate_frame(ch, f) for f in range(2)]
    character_images[ch.image_name] = frames
    prog = (i + 1) / total
    now = pygame.time.get_ticks()
    draw_loading(prog, loading_tips[i % len(loading_tips)], now - start)
    for ev in pygame.event.get():
        if ev.type == pygame.QUIT:
            pygame.quit()
            exit()

# Pós-carga (mostra 100% por meio segundo)
for _ in range(30):
    now = pygame.time.get_ticks()
    draw_loading(1.0, "Pronto! Pressione Enter para começar.", now - start)
    for ev in pygame.event.get():
        if ev.type == pygame.QUIT:
            pygame.quit()
            exit()
        if ev.type == pygame.KEYDOWN and ev.key == pygame.K_RETURN:
            break
    else:
        continue
    break

current_state = STATE_NAME_INPUT

# ─────────────────────────────────────────────
#  VARIÁVEIS GLOBAIS
# ─────────────────────────────────────────────
player1 = None
player2 = None
winner  = None

p1_name = ""
p2_name = ""
active_input = 0   # 0 = campo P1, 1 = campo P2

p1_char_idx  = 0
p2_char_idx  = 0
p1_selected  = False
p2_selected  = False

# ─────────────────────────────────────────────
#  FUNÇÕES DE ESTADO
# ─────────────────────────────────────────────
def start_game():
    global player1, player2, current_state
    player1 = Player(
        SCREEN_WIDTH // 4, SCREEN_HEIGHT // 2,
        {'up': pygame.K_w, 'down': pygame.K_s, 'left': pygame.K_a,
         'right': pygame.K_d, 'shoot': pygame.K_g, 'ability': pygame.K_q},
        CHARACTER_TYPES[p1_char_idx],
        name=p1_name or "Jogador 1"
    )
    player2 = Player(
        SCREEN_WIDTH * 3 // 4, SCREEN_HEIGHT // 2,
        {'up': pygame.K_UP, 'down': pygame.K_DOWN, 'left': pygame.K_LEFT,
         'right': pygame.K_RIGHT, 'shoot': pygame.K_SLASH, 'ability': pygame.K_PERIOD},
        CHARACTER_TYPES[p2_char_idx],
        name=p2_name or "Jogador 2"
    )
    global vs_timer
    vs_timer = VS_DURATION
    current_state = STATE_VS_SCREEN

def reset_game():
    global player1, player2, winner
    global p1_name, p2_name, active_input
    global p1_char_idx, p2_char_idx, p1_selected, p2_selected
    global current_state
    player1 = player2 = winner = None
    p1_name = p2_name = ""
    active_input = 0
    p1_char_idx = p2_char_idx = 0
    p1_selected = p2_selected = False
    current_state = STATE_NAME_INPUT

# ─────────────────────────────────────────────
#  LOOP PRINCIPAL
# ─────────────────────────────────────────────
running = True
while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        # ── INSERÇÃO DE NOMES ──────────────────
        if current_state == STATE_NAME_INPUT:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_TAB:
                    active_input = 1 - active_input   # alterna entre campos
                elif event.key == pygame.K_RETURN:
                    if active_input == 0 and p1_name.strip():
                        active_input = 1
                    elif active_input == 1 and p2_name.strip():
                        current_state = STATE_CHAR_SELECT
                elif event.key == pygame.K_BACKSPACE:
                    if active_input == 0:
                        p1_name = p1_name[:-1]
                    else:
                        p2_name = p2_name[:-1]
                else:
                    ch = event.unicode
                    if ch.isprintable():
                        if active_input == 0 and len(p1_name) < 16:
                            p1_name += ch
                        elif active_input == 1 and len(p2_name) < 16:
                            p2_name += ch

        # ── SELEÇÃO DE PERSONAGEM ──────────────
        elif current_state == STATE_CHAR_SELECT:
            if event.type == pygame.KEYDOWN:
                if not p1_selected:
                    if event.key == pygame.K_a:
                        p1_char_idx = (p1_char_idx - 1) % len(CHARACTER_TYPES)
                    if event.key == pygame.K_d:
                        p1_char_idx = (p1_char_idx + 1) % len(CHARACTER_TYPES)
                    if event.key == pygame.K_g:
                        p1_selected = True
                if not p2_selected:
                    if event.key == pygame.K_LEFT:
                        p2_char_idx = (p2_char_idx - 1) % len(CHARACTER_TYPES)
                    if event.key == pygame.K_RIGHT:
                        p2_char_idx = (p2_char_idx + 1) % len(CHARACTER_TYPES)
                    if event.key == pygame.K_m:
                        p2_selected = True
                if p1_selected and p2_selected:
                    start_game()

        # ── GAME OVER ─────────────────────────
        elif current_state == STATE_GAME_OVER:
            if event.type == pygame.KEYDOWN and event.key == pygame.K_r:
                reset_game()

    # ─────────────────────────────────────────
    #  LÓGICA VS SCREEN
    # ─────────────────────────────────────────
    if current_state == STATE_VS_SCREEN:
        vs_timer -= 1
        if vs_timer <= 0:
            current_state = STATE_PLAYING

    # ─────────────────────────────────────────
    #  LÓGICA DO JOGO
    # ─────────────────────────────────────────
    if current_state == STATE_PLAYING:
        keys = pygame.key.get_pressed()

        p1_dx = keys[player1.controls['right']] - keys[player1.controls['left']]
        p1_dy = keys[player1.controls['down']]  - keys[player1.controls['up']]
        p2_dx = keys[player2.controls['right']] - keys[player2.controls['left']]
        p2_dy = keys[player2.controls['down']]  - keys[player2.controls['up']]

        player1.move(p1_dx, p1_dy)
        player2.move(p2_dx, p2_dy)

        if keys[player1.controls['shoot']]:  player1.shoot(player2)
        if keys[player2.controls['shoot']]:  player2.shoot(player1)

        # Poderes especiais (detectados por evento para não repetir)
        # (tratados via pygame.KEYDOWN no loop de eventos acima)
        # Para não duplicar o loop, detectamos via get_pressed com flag
        # usamos variável de estado por frame
        player1.update(walls, enemy=player2)
        player2.update(walls, enemy=player1)

        # Colisão bala → jogador
        for bullet in list(player1.bullets):
            dist = math.sqrt((bullet.x - player2.x)**2 + (bullet.y - player2.y)**2)
            if dist < bullet.radius + player2.radius:
                if bullet.explosive:
                    player2.take_damage(bullet.damage)
                    player1.explosions.append(Explosion(bullet.x, bullet.y, damage=bullet.damage, owner=player1))
                else:
                    player2.take_damage(bullet.damage)
                player1.bullets.remove(bullet)

        for bullet in list(player2.bullets):
            dist = math.sqrt((bullet.x - player1.x)**2 + (bullet.y - player1.y)**2)
            if dist < bullet.radius + player1.radius:
                if bullet.explosive:
                    player1.take_damage(bullet.damage)
                    player2.explosions.append(Explosion(bullet.x, bullet.y, damage=bullet.damage, owner=player2))
                else:
                    player1.take_damage(bullet.damage)
                player2.bullets.remove(bullet)

        # Dano de explosão em área (para explosões de parede/gerais)
        for exp in list(player1.explosions + player2.explosions):
            if exp.damage_dealt or exp.damage <= 0:
                continue
            targets = []
            if exp.owner != player1:
                targets.append(player1)
            if exp.owner != player2:
                targets.append(player2)
            for target in targets:
                edist = math.sqrt((exp.x - target.x)**2 + (exp.y - target.y)**2)
                if edist < exp.radius:
                    target.take_damage(exp.damage)
            exp.damage_dealt = True

        # Fim de jogo
        if player1.hp <= 0:
            winner = player2.name
            current_state = STATE_GAME_OVER
        elif player2.hp <= 0:
            winner = player1.name
            current_state = STATE_GAME_OVER

    # ─────────────────────────────────────────
    #  PODER ESPECIAL (tecla única por frame)
    # ─────────────────────────────────────────
    if current_state == STATE_PLAYING:
        keys = pygame.key.get_pressed()
        # Detectar borda de subida com timers simples
        if not hasattr(player1, '_q_held'):
            player1._q_held = False
        if not hasattr(player2, '_period_held'):
            player2._period_held = False

        q_now = keys[pygame.K_q]
        if q_now and not player1._q_held:
            player1.use_ability(player2, walls)
        player1._q_held = q_now

        period_now = keys[pygame.K_PERIOD] or keys[pygame.K_KP_PERIOD] or keys[pygame.K_0] or keys[pygame.K_KP0]
        if period_now and not player2._period_held:
            player2.use_ability(player1, walls)
        player2._period_held = period_now

    # ─────────────────────────────────────────
    #  DESENHO
    # ─────────────────────────────────────────
    screen.fill(UI_BG)

    # Fundo da arena (chão texturizado com ladrilhos)
    for gx in range(0, SCREEN_WIDTH, 32):
        for gy in range(0, SCREEN_HEIGHT, 32):
            color = FLOOR_A if ((gx // 32) + (gy // 32)) % 2 == 0 else FLOOR_B
            pygame.draw.rect(screen, color, (gx, gy, 32, 32))
            if gx % 64 == 0 and gy % 64 == 0:
                c = FLOOR_A if color == FLOOR_B else FLOOR_B
                pygame.draw.rect(screen, c, (gx + 14, gy + 14, 4, 4))

    # ── TELA DE NOME ──────────────────────────
    if current_state == STATE_NAME_INPUT:
        draw_text(screen, "SOUL STRIKE", 58, UI_GOLD, SCREEN_WIDTH // 2, 70)
        draw_text(screen, "Digite o nome dos jogadores", 22, UI_TEXT_DIM, SCREEN_WIDTH // 2, 115)

        for i, (label, name, cx, col) in enumerate([
            ("JOGADOR 1", p1_name, SCREEN_WIDTH // 4, BLUE),
            ("JOGADOR 2", p2_name, SCREEN_WIDTH * 3 // 4, RED),
        ]):
            draw_text(screen, label, 28, col, cx, 210)
            box_x = cx - 150
            box_y = 240
            box_w, box_h = 300, 48
            border_col = UI_BORDER_LIT if active_input == i else UI_BORDER
            draw_panel(screen, (box_x, box_y, box_w, box_h), fill=UI_PANEL, border=border_col, radius=8)
            cursor = "|" if active_input == i and (pygame.time.get_ticks() // 500) % 2 == 0 else ""
            display_name = name + cursor
            draw_text(screen, display_name or "...", 32, WHITE, cx, box_y + box_h // 2)

        draw_text(screen, "TAB = alternar   |   ENTER = confirmar", 18, UI_TEXT_DIM,
                  SCREEN_WIDTH // 2, 335)

        draw_panel(screen, (SCREEN_WIDTH // 2 - 200, 370, 400, 90), fill=UI_PANEL, border=UI_BORDER, radius=8)
        hints = [
            ("P1: WASD mover | G atirar | Q poder", BLUE),
            ("P2: Setas mover | / atirar | . poder", RED),
        ]
        for i, (hint, col) in enumerate(hints):
            draw_text(screen, hint, 16, col, SCREEN_WIDTH // 2, 395 + i * 25)

    # ── SELEÇÃO DE PERSONAGEM ─────────────────
    elif current_state == STATE_CHAR_SELECT:
        draw_text(screen, "SOUL STRIKE", 50, UI_GOLD, SCREEN_WIDTH // 2, 30)
        draw_text(screen, "SELECIONE SEU LUTADOR", 20, UI_TEXT_DIM, SCREEN_WIDTH // 2, 60)

        for i, (px, col, idx, selected, hint, pname) in enumerate([
            (SCREEN_WIDTH // 4,     BLUE, p1_char_idx, p1_selected,
             "[A/D] trocar   [G] OK", p1_name or "Jogador 1"),
            (SCREEN_WIDTH * 3 // 4, RED,  p2_char_idx, p2_selected,
             "[←/→] trocar   [M] OK", p2_name or "Jogador 2"),
        ]):
            ch = CHARACTER_TYPES[idx]
            card_w, card_h = 290, 420
            card_x = px - card_w // 2
            card_y = 70

            border_col = GREEN if selected else UI_BORDER_LIT
            draw_panel(screen, (card_x, card_y, card_w, card_h), fill=UI_PANEL, border=border_col, radius=10)

            # Nome do jogador
            draw_text(screen, pname.upper(), 18, col, px, card_y + 18)

            # Sprite animado
            frames = character_images.get(ch.image_name)
            if frames:
                img = frames[(pygame.time.get_ticks() // 400) % 2]
                rect = img.get_rect(center=(px, card_y + 80))
                screen.blit(img, rect)
                pygame.draw.ellipse(screen, UI_BORDER_LIT, rect.inflate(6, 6), 1)

            # Nome do personagem
            draw_text(screen, ch.name, 26, WHITE, px, card_y + 140)

            # Stats card
            stat_y = card_y + 155
            stats_w = card_w - 24
            stats_x = card_x + 12
            draw_panel(screen, (stats_x, stat_y, stats_w, 115), fill=(18, 16, 30), border=UI_BORDER, radius=5)

            stats = [
                (f"HP: {ch.max_hp}", RED),
                (f"Vel: {ch.speed}", CYAN),
                (f"Dano: {ch.damage}", ORANGE),
                (f"Cad.: {ch.shoot_cooldown}ms", UI_TEXT_DIM),
                (f"Bala: {ch.bullet_speed}", GOLD),
            ]
            for j, (text, c) in enumerate(stats):
                draw_text(screen, text, 16, c, px, stat_y + 12 + j * 20)

            # Poder card
            pow_y = stat_y + 125
            draw_panel(screen, (stats_x, pow_y, stats_w, 50), fill=(25, 20, 15), border=UI_GOLD, radius=5)
            draw_text(screen, f"{ch.ability_name}", 18, UI_GOLD, px, pow_y + 14)
            draw_text(screen, ch.ability_desc, 13, UI_TEXT_DIM, px, pow_y + 34)

            # Hint / Confirmado
            hint_y = pow_y + 60
            if not selected:
                draw_text(screen, hint, 15, UI_TEXT_DIM, px, hint_y)
            else:
                draw_text(screen, "CONFIRMADO", 18, GREEN, px, hint_y)

        # Navegação visual (nas laterais do card, ao lado do sprite)
        if not p1_selected:
            draw_text(screen, "<", 26, UI_BORDER_LIT, card_x + 10, card_y + 115)
            draw_text(screen, ">", 26, UI_BORDER_LIT, card_x + card_w - 10, card_y + 115)
        if not p2_selected:
            draw_text(screen, "<", 26, UI_BORDER_LIT, card_x + 10, card_y + 115)
            draw_text(screen, ">", 26, UI_BORDER_LIT, card_x + card_w - 10, card_y + 115)

        if p1_selected and p2_selected:
            draw_text(screen, "PREPARANDO BATALHA...", 22, UI_GOLD,
                      SCREEN_WIDTH // 2, SCREEN_HEIGHT - 28)

    # ── TELA VS ──────────────────────────────
    elif current_state == STATE_VS_SCREEN:
        t = vs_timer
        progress = 1.0 - (t / VS_DURATION)

        # Fundo escuro
        screen.fill((10, 5, 20))

        # Partículas laterais (chamas)
        for i in range(20):
            px = SCREEN_WIDTH // 2 + int(300 * math.sin(i * 1.7 + t * 0.05))
            py = SCREEN_HEIGHT // 2 + int(100 * math.cos(i * 2.3 + t * 0.03))
            size = 3 + int(4 * math.sin(i + t * 0.1))
            alpha = int(100 + 155 * (0.5 + 0.5 * math.sin(i + t * 0.05)))
            surf = pygame.Surface((size * 2, size * 2), pygame.SRCALPHA)
            pygame.draw.circle(surf, (*ORANGE[:3], alpha), (size, size), size)
            screen.blit(surf, (int(px), int(py)))

        # Sprites dos jogadores
        for idx, (player, side) in enumerate([(player1, -1), (player2, 1)]):
            frames = character_images.get(player.char_stats.image_name)
            if frames:
                base = frames[0]
                scale = 2.0 + 0.2 * math.sin(t * 0.05)
                scaled = pygame.transform.scale(base, (int(120 * scale), int(120 * scale)))
                px = SCREEN_WIDTH // 2 + side * 200
                py = SCREEN_HEIGHT // 2 - 20
                rect = scaled.get_rect(center=(px, py))
                screen.blit(scaled, rect)

        # VS
        vs_scale = 1.0 + 0.3 * math.sin(t * 0.08)
        font = pygame.font.Font(None, int(80 * vs_scale))
        vs_surf = font.render("VS", True, GOLD)
        vs_rect = vs_surf.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 20))
        # Glow
        for r in range(8, 0, -1):
            glow_surf = font.render("VS", True, (*GOLD[:3], 30 // r))
            gr = glow_surf.get_rect(center=vs_rect.center)
            screen.blit(glow_surf, gr)
        screen.blit(vs_surf, vs_rect)

        # Nomes dos personagens
        draw_text(screen, player1.char_stats.name, 26, player1.color,
                  SCREEN_WIDTH // 4, SCREEN_HEIGHT // 2 + 80)
        draw_text(screen, player2.char_stats.name, 26, player2.color,
                  SCREEN_WIDTH * 3 // 4, SCREEN_HEIGHT // 2 + 80)

        # Nomes dos jogadores
        draw_text(screen, player1.name, 20, UI_TEXT_DIM,
                  SCREEN_WIDTH // 4, SCREEN_HEIGHT // 2 + 110)
        draw_text(screen, player2.name, 20, UI_TEXT_DIM,
                  SCREEN_WIDTH * 3 // 4, SCREEN_HEIGHT // 2 + 110)

        # FIGHT!
        fight_alpha = 0
        if progress > 0.5:
            fight_progress = (progress - 0.5) / 0.3
            fight_alpha = int(255 * min(1, fight_progress * 2) * (1 - max(0, fight_progress - 0.5) * 2))
        if fight_alpha > 0:
            fight_surf = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            font = pygame.font.Font(None, 100)
            txt = font.render("FIGHT!", True, (*YELLOW[:3], fight_alpha))
            tr = txt.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 50))
            fight_surf.blit(txt, tr)
            screen.blit(fight_surf, (0, 0))

    # ── JOGO ──────────────────────────────────
    elif current_state == STATE_PLAYING:
        for wall in walls:
            wall.draw(screen)

        if player1.barrier:
            player1.barrier.draw(screen)
        if player2.barrier:
            player2.barrier.draw(screen)

        player1.draw(screen, enemy=player2)
        player2.draw(screen, enemy=player1)

        for b in player1.bullets + player2.bullets:
            b.draw(screen)

        draw_hud(screen, player1, player2)

    # ── GAME OVER ─────────────────────────────
    elif current_state == STATE_GAME_OVER:
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        screen.blit(overlay, (0, 0))
        draw_panel(screen, (SCREEN_WIDTH // 2 - 200, SCREEN_HEIGHT // 2 - 90, 400, 180),
                   fill=UI_PANEL, border=UI_GOLD, radius=12)
        draw_text(screen, "FIM DE JOGO!", 52, WHITE, SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 55)
        draw_text(screen, f"{winner} VENCEU!", 44, UI_GOLD, SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 10)
        draw_text(screen, "Pressione R para reiniciar", 20, UI_TEXT_DIM,
                  SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 65)

    pygame.display.flip()
    clock.tick(FPS)

pygame.quit()