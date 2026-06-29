# -*- coding: utf-8 -*-
import os
import pygame
import math
import random
import webbrowser
import qrcode
from io import BytesIO
import remote_input
from web_server import start_server_thread, get_local_ip

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

# --- Futebol ---
TEAM_BLUE_OVERLAY = (40, 80, 255, 90)
TEAM_RED_OVERLAY  = (255, 40, 40, 90)
WIN_SCORE = 3
GOAL_FREEZE = 120
BALL_RADIUS = 12
BALL_FRICTION = 0.985
BALL_MAX_SPEED = 12
KICK_POWER = 10
DRIBBLE_RADIUS = 50
DRIBBLE_SPRING = 0.22
DRIBBLE_TARGET_OFFSET = 3
DRIBBLE_SPEED_LIMIT = 3.0
ZOOM_MIN = 0.55
ZOOM_SMOOTH = 0.04
SUPER_SHOT_COOLDOWN = 1200
SUPER_SHOT_POWER = 16
SUPER_HOMING_FORCE = 0.35
SUPER_HOMING_DURATION = 120
SOCCER_MAP_NAME = "campo_futebol"
GOAL_DETECT_LEFT = 20
GOAL_DETECT_RIGHT = 1580
GOAL_DETECT_TOP = 370
GOAL_DETECT_BOTTOM = 530

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

WARRIOR  = CharacterStats("Guerreiro",  150, 3,  8,  24, BLUE,   "Investida",    "Avança sobre o inimigo causando 35 de dano", "warrior.png", damage=12)
SHOOTER  = CharacterStats("Atirador",    80, 4, 12,  12, CYAN,   "Rajada",      "Dispara 5 balas em leque", "shooter.png", damage=8)
TANK     = CharacterStats("Tanque",     250, 2,  7,  36, GRAY,   "Muralha",     "Cria barreira que bloqueia balas por 4s", "tank.png", damage=15)
NINJA    = CharacterStats("Ninja",      100, 5,  9,  16, TEAL,   "Shuriken",    "Lança 3 shurikens de alto dano", "ninja.png", damage=10)
SPEEDSTER= CharacterStats("Velocista",  100, 3,  9,  18, YELLOW, "Turbo",       "Velocidade 3x por 4s", "speedster.png", damage=9)
BOMBER   = CharacterStats("Aryel",      130, 3,  8,  28, ORANGE, "Explosão",    "Bala que explode ao impacto", "aryel.png", damage=14)
GHOST    = CharacterStats("Fantasma",   110, 4,  9,  20, PURPLE, "Teletransporte","Teleporta para posição aleatória", "ghost.png", damage=11)
TITAN    = CharacterStats("Titã",       200, 2,  7,  32, GOLD,   "Invulnerável","Invulnerável por 5s", "titan.png", damage=13)

CHARACTER_TYPES = [WARRIOR, SHOOTER, TANK, NINJA, SPEEDSTER, BOMBER, GHOST, TITAN]

# ─────────────────────────────────────────────
#  STATS DAS ARMAS
# ─────────────────────────────────────────────
class WeaponStats:
    def __init__(self, name, damage, bullet_speed, shoot_cooldown, weapon_type, melee_range=0):
        self.name = name
        self.damage = damage
        self.bullet_speed = bullet_speed
        self.shoot_cooldown = shoot_cooldown
        self.weapon_type = weapon_type
        self.melee_range = melee_range

WARRIOR_WEAPONS = [
    WeaponStats("Arco",     10, 9,  22, "ranged"),
    WeaponStats("Espada",   22, 0,  0,  "melee", melee_range=70),
]
SHOOTER_WEAPONS = [
    WeaponStats("Rifle",    8,  14, 12, "ranged"),
    WeaponStats("Faca",     16, 0,  0,  "melee", melee_range=50),
]
TANK_WEAPONS = [
    WeaponStats("Lança",    14, 8,  34, "ranged"),
    WeaponStats("Maça",     26, 0,  0,  "melee", melee_range=60),
]
NINJA_WEAPONS = [
    WeaponStats("Shuriken", 9,  11, 16, "ranged"),
    WeaponStats("Katana",   20, 0,  0,  "melee", melee_range=65),
]
SPEEDSTER_WEAPONS = [
    WeaponStats("Estrela",  7,  10, 18, "ranged"),
    WeaponStats("Garras",   14, 0,  0,  "melee", melee_range=45),
]
BOMBER_WEAPONS = [
    WeaponStats("Granada",  12, 7,  28, "ranged"),
    WeaponStats("Martelo",  24, 0,  0,  "melee", melee_range=55),
]
GHOST_WEAPONS = [
    WeaponStats("Orbe",     10, 10, 20, "ranged"),
    WeaponStats("Foice",    20, 0,  0,  "melee", melee_range=60),
]
TITAN_WEAPONS = [
    WeaponStats("Corrente", 12, 8,  32, "ranged"),
    WeaponStats("Espadão",  28, 0,  0,  "melee", melee_range=70),
]

CHARACTER_WEAPONS = {
    "Guerreiro":   WARRIOR_WEAPONS,
    "Atirador":    SHOOTER_WEAPONS,
    "Tanque":      TANK_WEAPONS,
    "Ninja":       NINJA_WEAPONS,
    "Velocista":   SPEEDSTER_WEAPONS,
    "Aryel": BOMBER_WEAPONS,
    "Fantasma":    GHOST_WEAPONS,
    "Titã":        TITAN_WEAPONS,
}

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
    """Gera um frame (120x120) para um personagem. frame=0..3 ciclo de caminhada."""
    surf = pygame.Surface(IMAGE_SIZE, pygame.SRCALPHA)
    w, h = IMAGE_SIZE
    cx, cy = w // 2, h // 2 + 6
    col = stats.color

    # Ciclo de 4 frames: 0=neutro, 1=dir+frente, 2=neutro, 3=esq+frente
    leg_swing_values = [0, 8, 0, -8]
    leg_off = leg_swing_values[frame]
    body_bob = [0, -2, 0, -2][frame]

    cy += body_bob

    # ── Sombra ──
    shadow_scale = 1.0 - body_bob * 0.01
    sw = int(36 * shadow_scale)
    sh = int(8 * shadow_scale)
    pygame.draw.ellipse(surf, (0, 0, 0, 50), (cx - sw // 2, cy + 28, sw, sh))

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

    # ── Braços (balanço oposto às pernas) ──
    arm_len = 16
    arm_w = 4
    shoulder_y = body_t + 4
    arm_swing = -leg_off // 2

    la_x = cx - body_w // 2 - 2 - abs(arm_swing)
    la_y = shoulder_y + arm_len
    _draw_limb(surf, col, cx - body_w // 2, shoulder_y, la_x, la_y, arm_w)

    ra_x = cx + body_w // 2 + 2 + abs(arm_swing)
    ra_y = shoulder_y + arm_len
    _draw_limb(surf, col, cx + body_w // 2, shoulder_y, ra_x, ra_y, arm_w)

    # ── Cabeça ──
    head_r = 11
    head_y = body_t - head_r + 1
    pygame.draw.circle(surf, col, (cx, head_y), head_r)

    eye_y = head_y - 1
    for ex in (-4, 4):
        pygame.draw.circle(surf, WHITE, (cx + ex, eye_y), 3)
        pygame.draw.circle(surf, BLACK, (cx + ex, eye_y), 1.5)
        pygame.draw.circle(surf, WHITE, (cx + ex - 1, eye_y - 1), 1)

    blush = pygame.Surface((6, 3), pygame.SRCALPHA)
    blush.fill((255, 150, 150, 80))
    surf.blit(blush, (cx - 9, head_y + 1))
    surf.blit(blush, (cx + 3, head_y + 1))

    # ── Acessórios únicos por classe ──
    name = stats.name

    if name == "Guerreiro":
        pygame.draw.rect(surf, GRAY, (cx - 10, head_y - head_r - 2, 20, 7), border_radius=3)
        pygame.draw.rect(surf, WHITE, (cx - 8, head_y - head_r + 1, 16, 3))

    elif name == "Atirador":
        pygame.draw.polygon(surf, GRAY, [
            (cx - 12, head_y - head_r + 2),
            (cx + 12, head_y - head_r + 2),
            (cx + 3, head_y - head_r - 14),
            (cx - 3, head_y - head_r - 14),
        ])
        pygame.draw.rect(surf, GRAY, (cx - 4, head_y - head_r - 14, 8, 3))

    elif name == "Tanque":
        pygame.draw.rect(surf, DARK_GRAY, (cx - 9, head_y - head_r - 3, 18, 8), border_radius=4)
        pygame.draw.rect(surf, CYAN, (cx - 6, head_y - 4, 12, 4), border_radius=1)
        big_rect = pygame.Rect(cx - 15, body_t - 2, 30, body_b - body_t + 4)
        pygame.draw.ellipse(surf, col, big_rect)
        pygame.draw.ellipse(surf, WHITE, big_rect, 1)

    elif name == "Ninja":
        pygame.draw.rect(surf, RED, (cx - 13, head_y - 5, 26, 4))
        _draw_limb(surf, RED, cx + 13, head_y - 5, cx + 22, head_y + 3, 2)
        _draw_limb(surf, RED, cx - 13, head_y - 5, cx - 22, head_y + 3, 2)
        pygame.draw.rect(surf, DARK_GRAY, (cx - 8, head_y + 1, 16, 7), border_radius=3)

    elif name == "Velocista":
        cap_phase = [0, 4, 0, -4][frame]
        cap = pygame.Surface((28, head_r * 2), pygame.SRCALPHA)
        pygame.draw.ellipse(cap, (200, 180, 0), (0, 0, 28, head_r * 2))
        surf.blit(cap, (cx - 9 + cap_phase // 2, head_y - head_r - 1))
        pygame.draw.circle(surf, col, (cx, head_y), head_r)
        for ex in (-4, 4):
            pygame.draw.circle(surf, WHITE, (cx + ex, eye_y), 3)
            pygame.draw.circle(surf, BLACK, (cx + ex, eye_y), 2)
        for i in range(3):
            sy = body_t + i * 6 + 2
            _draw_limb(surf, (255, 255, 100), cx - 11, sy, cx - 20 - i * 4, sy, 2)

    elif name == "Aryel":
        pygame.draw.rect(surf, DARK_GRAY, (cx - 13, body_t + 2, 26, 16), border_radius=4)
        pygame.draw.rect(surf, RED, (cx - 9, body_t + 5, 5, 5))
        pygame.draw.rect(surf, RED, (cx + 4, body_t + 5, 5, 5))

    elif name == "Fantasma":
        for i in range(4):
            wy = body_b + i * 7
            wx = 6 * math.sin(i * 0.8 + frame * math.pi / 2)
            alpha = max(30, 150 - i * 30)
            fumaça = pygame.Surface((30, 12), pygame.SRCALPHA)
            pygame.draw.ellipse(fumaça, (*col, alpha), (0, 0, 30, 12))
            surf.blit(fumaça, (int(cx - 15 + wx), int(wy)))
        capa = pygame.Surface((30, 30), pygame.SRCALPHA)
        pygame.draw.ellipse(capa, (*col, 100), (0, 0, 30, 30))
        surf.blit(capa, (cx - 15, body_t - 4))
        pygame.draw.circle(surf, col, (cx, head_y), head_r)
        for ex in (-5, 5):
            pygame.draw.circle(surf, WHITE, (cx + ex, eye_y), 4)
            pygame.draw.circle(surf, CYAN, (cx + ex, eye_y), 2)

    elif name == "Titã":
        big_rect = pygame.Rect(cx - 16, body_t - 4, 32, body_b - body_t + 8)
        pygame.draw.ellipse(surf, col, big_rect)
        pygame.draw.ellipse(surf, WHITE, big_rect, 2)
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
        pygame.draw.line(surf, WHITE, (cx - 10, body_t + 2), (cx + 10, body_t + 2), 2)
        pygame.draw.line(surf, WHITE, (cx - 8, body_t + 8), (cx + 8, body_t + 8), 2)
        pygame.draw.circle(surf, GOLD, (cx - 13, shoulder_y), 6)
        pygame.draw.circle(surf, GOLD, (cx + 13, shoulder_y), 6)

    return surf


ASSET_CHAR_DIR = os.path.join(ASSET_DIR, "characters")

DIR_NAMES = ["frente", "costas", "direita", "esquerda"]

def _char_name_to_file(stats):
    return stats.name.lower().replace("ã", "a").replace("é", "e").replace("ê", "e")

def _load_char_frames(base):
    dirs = {d: [] for d in DIR_NAMES}
    if not os.path.isdir(ASSET_CHAR_DIR):
        return None
    for fname in os.listdir(ASSET_CHAR_DIR):
        if not fname.endswith(".png"):
            continue
        name = fname[:-4]
        for d in DIR_NAMES:
            if name.startswith(base) and name.endswith(d):
                num_str = name[len(base):-len(d)]
                try:
                    num = int(num_str) if num_str else 0
                except ValueError:
                    continue
                path = os.path.join(ASSET_CHAR_DIR, fname)
                try:
                    img = pygame.image.load(path).convert_alpha()
                    dirs[d].append((num, pygame.transform.scale(img, IMAGE_SIZE)))
                except pygame.error:
                    pass
                break
    result = {}
    for d in DIR_NAMES:
        if not dirs[d]:
            return None
        dirs[d].sort(key=lambda x: x[0])
        result[d] = [s for _, s in dirs[d]]
    return result

def load_character_sprites():
    sprites = {}
    for ch in CHARACTER_TYPES:
        base = _char_name_to_file(ch)
        result = _load_char_frames(base)
        if result:
            sprites[ch.image_name] = result
            continue
        frames = [_generate_frame(ch, f) for f in range(4)]
        sprites[ch.image_name] = {
            "frente": [frames[0]],
            "costas": [frames[2]],
            "direita": [frames[1]],
            "esquerda": [frames[3]],
        }
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
        if not (0 < self.x < WORLD_WIDTH and 0 < self.y < WORLD_HEIGHT):
            self.alive = False

    def draw(self, screen):
        sx = int(self.x - camera_x)
        sy = int(self.y - camera_y)
        if sx < -20 or sx > SCREEN_WIDTH + 20 or sy < -20 or sy > SCREEN_HEIGHT + 20:
            return
        if self.explosive:
            pygame.draw.circle(screen, ORANGE, (sx, sy), self.radius + 2)
            pygame.draw.circle(screen, RED,    (sx, sy), self.radius)
        elif self.damage >= MAX_BULLET_DAMAGE * 0.8:
            pygame.draw.circle(screen, YELLOW, (sx, sy), self.radius + 2)
        elif self.damage >= BASE_BULLET_DAMAGE * 1.5:
            pygame.draw.circle(screen, ORANGE, (sx, sy), self.radius + 1)
        else:
            pygame.draw.circle(screen, self.color, (sx, sy), self.radius)

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
        screen.blit(surf, (int(self.x - camera_x) - r, int(self.y - camera_y) - r))

    @property
    def done(self):
        return self.timer <= 0

# ─────────────────────────────────────────────
#  FUTEBOL — BOLA
# ─────────────────────────────────────────────
class Ball:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.vx = 0.0
        self.vy = 0.0
        self.radius = BALL_RADIUS
        self.friction = BALL_FRICTION
        self.homing_timer = 0
        self.homing_target = None
        self.homing_target_player = None
        self.homing_force = 0.0

    def reset(self, x, y):
        self.x = x
        self.y = y
        self.vx = 0.0
        self.vy = 0.0
        self.homing_timer = 0
        self.homing_target = None
        self.homing_target_player = None
        self.homing_force = 0.0

    def update(self):
        self.vx *= self.friction
        self.vy *= self.friction
        if abs(self.vx) < 0.05:
            self.vx = 0.0
        if abs(self.vy) < 0.05:
            self.vy = 0.0
        spd = math.hypot(self.vx, self.vy)
        if spd > BALL_MAX_SPEED:
            self.vx = self.vx / spd * BALL_MAX_SPEED
            self.vy = self.vy / spd * BALL_MAX_SPEED
        if self.homing_timer > 0:
            if self.homing_target_player:
                self.homing_target = (self.homing_target_player.x, self.homing_target_player.y)
            if self.homing_target:
                hdx = self.homing_target[0] - self.x
                hdy = self.homing_target[1] - self.y
                hm = math.hypot(hdx, hdy)
                if hm > 0:
                    self.vx += (hdx / hm) * self.homing_force
                    self.vy += (hdy / hm) * self.homing_force
            self.homing_timer -= 1

        self.x += self.vx
        self.y += self.vy

    def draw(self):
        sx = int(self.x - camera_x)
        sy = int(self.y - camera_y)
        # sombra
        pygame.draw.circle(screen, DARK_GRAY, (sx + 2, sy + 3), self.radius)
        # bola
        pygame.draw.circle(screen, WHITE, (sx, sy), self.radius)
        pygame.draw.circle(screen, BLACK, (sx, sy), self.radius, 2)
        # detalhe
        pygame.draw.line(screen, BLACK, (sx - 4, sy - 4), (sx + 4, sy + 4), 2)
        pygame.draw.line(screen, BLACK, (sx + 4, sy - 4), (sx - 4, sy + 4), 2)

# ─────────────────────────────────────────────
#  FUTEBOL — GOL (DECORATIVO)
# ─────────────────────────────────────────────
class Goal:
    def __init__(self, x, y, w, h, side, color):
        self.rect = pygame.Rect(x, y, w, h)
        self.side = side
        self.color = color

    def draw(self):
        sx = int(self.rect.x - camera_x)
        sy = int(self.rect.y - camera_y)

        # ── Rede (mesh) ──
        net = pygame.Surface((self.rect.w, self.rect.h), pygame.SRCALPHA)
        net.fill((*self.color[:3], 60))
        for i in range(0, self.rect.w, 8):
            pygame.draw.line(net, (*self.color[:3], 100), (i, 0), (i, self.rect.h), 1)
        for i in range(0, self.rect.h, 8):
            pygame.draw.line(net, (*self.color[:3], 100), (0, i), (self.rect.w, i), 1)
        screen.blit(net, (sx, sy))

        # ── Pilares de pedra (laterais) ──
        stone = (110, 100, 90)
        stone_dark = (80, 72, 62)
        stone_light = (140, 128, 115)
        pw = 8
        for px in (sx - pw, sx + self.rect.w):
            # pilar
            p_rect = pygame.Rect(px, sy, pw, self.rect.h)
            pygame.draw.rect(screen, stone, p_rect)
            pygame.draw.rect(screen, stone_dark, p_rect, 1)
            # linhas de argamassa horizontal a cada 16px
            for ly in range(sy + 8, sy + self.rect.h, 16):
                pygame.draw.line(screen, (70, 62, 52), (px + 1, ly), (px + pw - 1, ly), 1)
            # realce de luz no lado externo
            hl = px if px < sx else px + pw - 1
            pygame.draw.line(screen, stone_light, (hl, sy), (hl, sy + self.rect.h - 1), 1)

        # ── Travessão de madeira ──
        bh = 10
        wood = (100, 60, 30)
        wood_dark = (65, 38, 16)
        wood_light = (135, 85, 45)
        bar_rect = pygame.Rect(sx - pw, sy - bh, self.rect.w + pw * 2, bh)
        pygame.draw.rect(screen, wood, bar_rect)
        pygame.draw.rect(screen, wood_dark, bar_rect, 1)
        # grãos de madeira (linhas horizontais curtas)
        for gx in range(sx - pw + 4, sx + self.rect.w + pw, 12):
            gy = sy - bh + 4
            pygame.draw.line(screen, wood_dark, (gx, gy), (gx + 6, gy), 1)
            gy2 = sy - 3
            pygame.draw.line(screen, (120, 75, 40), (gx, gy2), (gx + 6, gy2), 1)

# ── FUNÇÃO DE CHUTE ──
def soccer_kick(player, ball):
    dx = ball.x - player.x
    dy = ball.y - player.y
    dist = math.hypot(dx, dy)
    if dist < player.radius + ball.radius + 15:
        lx, ly = player.last_direction
        if lx == 0 and ly == 0:
            lx, ly = 1, 0
        ball.vx = lx * KICK_POWER
        ball.vy = ly * KICK_POWER
        play_sfx('shoot', vol=0.3)
        return True
    return False

PASS_POWER = 6.0
PASS_HOMING_FORCE = 0.15
PASS_HOMING_DURATION = 45

def soccer_pass(player, ball, teammates, soccer_players=0):
    if not ball:
        return False
    dx = ball.x - player.x
    dy = ball.y - player.y
    dist = math.hypot(dx, dy)
    if dist < player.radius + ball.radius + 15:
        best = None
        best_d = 99999
        for t in teammates:
            if t is None or t is player:
                continue
            td = math.hypot(t.x - player.x, t.y - player.y)
            if td < best_d:
                best_d = td
                best = t
        if best:
            tx = best.x - player.x
            ty = best.y - player.y
            m = math.hypot(tx, ty)
            if m > 0:
                player.last_direction = (tx / m, ty / m)
                ball.vx = player.last_direction[0] * PASS_POWER
                ball.vy = player.last_direction[1] * PASS_POWER
                if soccer_players > 2 and best is not player:
                    ball.homing_timer = PASS_HOMING_DURATION
                    ball.homing_target_player = best
                    ball.homing_target = (best.x, best.y)
                    ball.homing_force = PASS_HOMING_FORCE
                play_sfx('shoot', vol=0.25)
                return True
    return False

# ── COLISÃO JOGADOR-JOGADOR ──
def resolve_player_collision(a, b):
    dx = b.x - a.x
    dy = b.y - a.y
    dist = math.hypot(dx, dy)
    mindist = a.radius + b.radius
    if dist < mindist and dist > 0:
        overlap = (mindist - dist) / 2
        nx = dx / dist
        ny = dy / dist
        a.x -= nx * overlap
        a.y -= ny * overlap
        b.x += nx * overlap
        b.y += ny * overlap

# ── FUTEBOL: DETECÇÃO DE GOL ──
def check_goal(ball):
    if ball.x < GOAL_DETECT_LEFT and GOAL_DETECT_TOP < ball.y < GOAL_DETECT_BOTTOM:
        return 'left'   # Time Azul sofre gol → Time Vermelho marca
    if ball.x > GOAL_DETECT_RIGHT and GOAL_DETECT_TOP < ball.y < GOAL_DETECT_BOTTOM:
        return 'right'  # Time Vermelho sofre gol → Time Azul marca
    return None

# ── FUTEBOL: IA ──
def update_soccer_ai(player, ball, teammates, opponents, walls):
    if not ball:
        return
    # definir alvo
    target_x, target_y = ball.x, ball.y
    dx_gol = player.x - (WORLD_WIDTH - 80 if player.team == 0 else 80)
    dy_gol = player.y - WORLD_HEIGHT // 2
    dist_gol = math.hypot(dx_gol, dy_gol)
    dist_ball = math.hypot(player.x - ball.x, player.y - ball.y)

    # Se meu time tem a bola (alguém do mesmo time está perto)
    team_has_ball = any(
        t is not player and math.hypot(t.x - ball.x, t.y - ball.y) < 40
        for t in teammates
    )
    # time adversário tem a bola
    enemy_has_ball = any(
        o is not player and math.hypot(o.x - ball.x, o.y - ball.y) < 40
        for o in opponents
    )

    if team_has_ball:
        # Avançar em direção ao gol adversário
        gol_x = WORLD_WIDTH - 80 if player.team == 0 else 80
        target_x, target_y = gol_x, WORLD_HEIGHT // 2
        if dist_ball < 30:
            # perto da bola, chutar em direção ao gol
            pass
    elif enemy_has_ball:
        # Defender: ficar entre a bola e o próprio gol
        meu_gol_x = 80 if player.team == 0 else WORLD_WIDTH - 80
        target_x = (ball.x + meu_gol_x) / 2
        target_y = (ball.y + WORLD_HEIGHT // 2) / 2
    else:
        target_x, target_y = ball.x, ball.y

    # mover em direção ao alvo
    dx = target_x - player.x
    dy = target_y - player.y
    dist = math.hypot(dx, dy)
    if dist > 5:
        move_x = dx / dist
        move_y = dy / dist
        player.move(move_x, move_y)

    # chutar se perto da bola e na direção do gol
    if dist_ball < 30:
        gol_x = WORLD_WIDTH - 80 if player.team == 0 else 80
        player.last_direction = (gol_x - player.x, WORLD_HEIGHT // 2 - player.y)
        mag = math.hypot(*player.last_direction)
        if mag > 0:
            player.last_direction = (player.last_direction[0] / mag, player.last_direction[1] / mag)
        soccer_kick(player, ball)

# ─────────────────────────────────────────────
#  JOGADOR
# ─────────────────────────────────────────────
class Player:
    ABILITY_COOLDOWN = 600   # 10 segundos entre usos

    def __init__(self, x, y, controls, char_stats, name="Jogador", weapon=None, team=None):
        self.x               = x
        self.y               = y
        self.radius          = 15
        self.color           = char_stats.color
        self.team            = team
        self.controls        = controls
        self.char_stats      = char_stats
        self.name            = name
        self.hp              = char_stats.max_hp
        self.speed           = char_stats.speed
        self.base_bullet_speed = char_stats.bullet_speed
        if weapon:
            self.weapon         = weapon
            self.damage         = weapon.damage
            self.bullet_speed   = weapon.bullet_speed if weapon.weapon_type == "ranged" else 0
            self.shoot_cooldown = weapon.shoot_cooldown
            self.weapon_name    = weapon.name
        else:
            self.weapon         = None
            self.damage         = char_stats.damage
            self.bullet_speed   = char_stats.bullet_speed
            self.shoot_cooldown = char_stats.shoot_cooldown
            self.weapon_name    = char_stats.name
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

        # Movimento velocity-based
        self.vx                  = 0.0
        self.vy                  = 0.0
        self.acceleration        = 0.18
        self.friction            = 0.12

        # Dash
        self.dash_timer          = 0
        self.dash_cooldown       = 0
        self.dash_dir            = (0, 0)
        self.dash_invulnerable   = False
        self.super_cooldown      = 0

        # Double-tap tracking (para dash)
        self.last_key_time       = {'up': 0, 'down': 0, 'left': 0, 'right': 0}
        self.dash_window         = 300  # ms
        self._dash_held          = {'up': False, 'down': False, 'left': False, 'right': False}

        # Knockback
        self.knockback_vx        = 0.0
        self.knockback_vy        = 0.0

        # Skid / Lean
        self.skid_timer          = 0
        self.lean_angle          = 0.0

        # Animação
        self.moving              = False
        self.anim_frame          = 0
        self.anim_timer          = 0

        # Efeitos visuais
        self.teleport_flash      = 0
        self.shoot_flash         = 0
        self.shoot_flash_pos     = (0, 0)
        self.explosions          = []  # explosões pertencentes a este jogador

        # Cache de rotação (lean)
        self._lean_cache         = {}

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

        if self.dash_timer > 0:
            return

        spd = self.speed * (3 if self.speed_boost else 1)
        target_vx = dx * spd
        target_vy = dy * spd

        if self.moving:
            self.vx += (target_vx - self.vx) * self.acceleration
            self.vy += (target_vy - self.vy) * self.acceleration
        else:
            self.vx *= (1 - self.friction)
            self.vy *= (1 - self.friction)
            if abs(self.vx) < 0.1: self.vx = 0
            if abs(self.vy) < 0.1: self.vy = 0

        self.vx += self.knockback_vx
        self.vy += self.knockback_vy
        self.knockback_vx *= 0.8
        self.knockback_vy *= 0.8

        if not self.moving and (abs(self.vx) > 1.5 or abs(self.vy) > 1.5):
            self.skid_timer = 8

        self.x += self.vx
        self.x = max(self.radius, min(WORLD_WIDTH - self.radius, self.x))
        for wall in walls:
            if wall.collides_with_player(self):
                self.x -= self.vx
                self.vx = 0
                break

        self.y += self.vy
        self.y = max(self.radius, min(WORLD_HEIGHT - self.radius, self.y))
        for wall in walls:
            if wall.collides_with_player(self):
                self.y -= self.vy
                self.vy = 0
                break

    # ── tiro ────────────────────────────────────
    def shoot(self, enemy):
        if self.current_cooldown > 0:
            return

        if self.weapon and self.weapon.weapon_type == "melee":
            self.melee_flash = 10
            self.current_cooldown = self.shoot_cooldown or 16
            play_sfx('shoot', vol=0.5)
            dist = self.distance_to(enemy)
            if dist <= self.weapon.melee_range:
                enemy.take_damage(self.weapon.damage, self.x, self.y)
                play_sfx('hit', vol=0.4)
            return

        dir_x, dir_y = self._normalize(*self.last_direction)
        dist   = self.distance_to(enemy)
        damage = calc_damage(dist, base=self.damage)
        explosive = (self.char_stats == BOMBER)
        bullet = Bullet(self.x, self.y, dir_x, dir_y,
                        self.bullet_speed, self.color, damage, explosive)
        self.bullets.append(bullet)
        self.current_cooldown = self.shoot_cooldown
        self.shoot_flash = 4
        self.shoot_flash_pos = (dir_x, dir_y)
        play_sfx('shoot' if random.random() < 0.7 else 'shoot2', vol=0.3)
        if dist <= MELEE_RANGE:
            self.melee_flash = 8

    # ── poder especial ──────────────────────────
    def use_ability(self, enemy, walls):
        if self.ability_cooldown > 0:
            return
        cs = self.char_stats
        self.ability_cooldown = self.ABILITY_COOLDOWN
        play_sfx('ability', vol=0.4)

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
            dir_x, dir_y = self._normalize(*self.last_direction)
            base_angle = math.atan2(-dir_y, dir_x)
            for i in range(5):
                angle = base_angle + math.radians(30 * (i / 4 - 0.5))
                ddx = math.cos(angle)
                ddy = -math.sin(angle)
                b = Bullet(self.x, self.y, ddx, ddy, self.base_bullet_speed,
                           self.color, self.char_stats.damage)
                self.bullets.append(b)

        elif cs == TANK:
            # Muralha — barreira na direção atual
            dir_x, dir_y = self._normalize(*self.last_direction)
            bx = self.x + dir_x * 40
            by = self.y + dir_y * 40
            self.barrier = Barrier(bx, by, dir_x, dir_y, 4 * FPS)
            play_sfx('barrier', vol=0.4)

        elif cs == NINJA:
            dir_x, dir_y = self._normalize(*self.last_direction)
            base_angle = math.atan2(-dir_y, dir_x)
            for i in range(3):
                angle = base_angle + math.radians(22.5 * (i - 1))
                ddx = math.cos(angle)
                ddy = -math.sin(angle)
                b = Bullet(self.x, self.y, ddx, ddy, self.base_bullet_speed + 2,
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
                b = Bullet(self.x, self.y, dx, dy, self.base_bullet_speed,
                           ORANGE, 25, explosive=True)
                self.bullets.append(b)

        elif cs == GHOST:
            for _ in range(50):
                nx = random.randint(50, WORLD_WIDTH  - 50)
                ny = random.randint(50, WORLD_HEIGHT - 50)
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
        if self.shoot_flash       > 0: self.shoot_flash        -= 1
        if self.skid_timer        > 0: self.skid_timer         -= 1

        # Dash
        if self.dash_timer > 0:
            self.dash_timer -= 1
            self.x += self.dash_dir[0] * self.speed * 5
            self.y += self.dash_dir[1] * self.speed * 5
            self.x = max(self.radius, min(WORLD_WIDTH - self.radius, self.x))
            self.y = max(self.radius, min(WORLD_HEIGHT - self.radius, self.y))
            for wall in walls:
                if wall.collides_with_player(self):
                    self.x -= self.dash_dir[0] * self.speed * 5
                    break
            for wall in walls:
                if wall.collides_with_player(self):
                    self.y -= self.dash_dir[1] * self.speed * 5
                    break
            if self.dash_timer <= 0:
                self.dash_invulnerable = False
        if self.dash_cooldown > 0:
            self.dash_cooldown -= 1

        # Animação de passos (4 frames)
        if self.moving:
            self.anim_timer += 1
            if self.anim_timer >= 6:
                self.anim_timer = 0
                self.anim_frame = (self.anim_frame + 1) % 4
        else:
            if self.anim_frame != 0:
                self.anim_timer += 1
                if self.anim_timer >= 4:
                    self.anim_frame = 0
                    self.anim_timer = 0
            else:
                self.anim_timer = 0

        # Lean visual
        if self.moving or abs(self.vx) > 0.5 or abs(self.vy) > 0.5:
            target_angle = -self.vx * 2
            self.lean_angle += (target_angle - self.lean_angle) * 0.2
        else:
            self.lean_angle *= 0.9
        if abs(self.lean_angle) < 0.5:
            self.lean_angle = 0

        # Efeitos com duração
        if self.ability_active:
            self.ability_timer -= 1
            if self.ability_timer <= 0:
                self.ability_active = False
                self.speed_boost    = False
                self.invulnerable   = False

        if self.charging:
            self.charge_timer -= 1
            spd = self.speed * 4
            self.x += self.charge_dir[0] * spd
            self.y += self.charge_dir[1] * spd
            self.x = max(self.radius, min(WORLD_WIDTH - self.radius, self.x))
            self.y = max(self.radius, min(WORLD_HEIGHT - self.radius, self.y))
            if self.charge_timer <= 0:
                self.charging = False
            # Dano no inimigo se colidir
            if enemy and self.distance_to(enemy) < self.radius + enemy.radius + 5:
                enemy.take_damage(35, self.x, self.y)
                self.charging = False

        # Muralha (Tanque)
        if self.barrier:
            self.barrier.update()
            if self.barrier.done:
                self.barrier = None

        i = 0
        while i < len(self.bullets):
            bullet = self.bullets[i]
            bullet.update()
            out = not bullet.alive
            hit_wall = any(w.collides_with_bullet(bullet) for w in walls)
            hit_barrier = enemy and enemy.barrier and enemy.barrier.collides_with_bullet(bullet)
            if out or hit_wall or hit_barrier:
                if bullet.explosive:
                    self.explosions.append(Explosion(bullet.x, bullet.y, damage=bullet.damage, owner=self))
                self.bullets.pop(i)
            else:
                i += 1

        # Atualizar explosões (iteração reversa)
        i = 0
        while i < len(self.explosions):
            exp = self.explosions[i]
            exp.update()
            if exp.done:
                self.explosions.pop(i)
            else:
                i += 1

    def take_damage(self, amount, source_x=None, source_y=None):
        if self.invulnerable or self.dash_invulnerable:
            return
        self.hp = max(0, self.hp - amount)
        if source_x is not None:
            dx = self.x - source_x
            dy = self.y - source_y
            mag = math.hypot(dx, dy)
            if mag > 0:
                self.knockback_vx = (dx / mag) * 5
                self.knockback_vy = (dy / mag) * 5

    # ── IA ──────────────────────────────────────
    def update_ai(self, enemy, walls, difficulty='medium'):
        if not enemy or enemy.hp <= 0:
            return

        dx = enemy.x - self.x
        dy = enemy.y - self.y
        dist = math.hypot(dx, dy)
        dir_x = dx / dist if dist > 0 else 0
        dir_y = dy / dist if dist > 0 else 1

        # Parâmetros por dificuldade
        diff = DIFFICULTIES.get(difficulty, DIFFICULTIES['medium'])
        reaction = diff['reaction']
        scatter  = diff['scatter']
        shoot_r  = diff['shoot_rate']
        dash_r   = diff['dash_rate']
        ability_r= diff['ability_rate']

        # Atraso de reação — só atualiza a cada N calls
        if not hasattr(self, '_ai_tick'):
            self._ai_tick = 0
        self._ai_tick += 1
        if self._ai_tick < reaction:
            return
        self._ai_tick = 0

        # Adiciona imprecisão à direção
        aim_x = dir_x + random.uniform(-scatter, scatter)
        aim_y = dir_y + random.uniform(-scatter, scatter)
        mag = math.hypot(aim_x, aim_y)
        if mag > 0:
            aim_x /= mag
            aim_y /= mag

        # Troca de strafe periódica
        if not hasattr(self, '_strafe_dir'):
            self._strafe_dir = 1
        if random.random() < 0.005:
            self._strafe_dir = -self._strafe_dir

        preferred_range = diff.get('range', 220)

        # Movimento
        move_x, move_y = 0, 0
        charge = (self.char_stats == WARRIOR and self.ability_cooldown <= 0 and random.random() < 0.1)
        if charge:
            move_x, move_y = aim_x, aim_y
        elif dist > preferred_range + 60:
            move_x, move_y = aim_x, aim_y
        elif dist < preferred_range - 60:
            move_x, move_y = -aim_x, -aim_y
        else:
            move_x = -aim_y * self._strafe_dir
            move_y =  aim_x * self._strafe_dir

        if random.random() < 0.08:
            move_x += random.uniform(-0.3, 0.3)
            move_y += random.uniform(-0.3, 0.3)

        self.move(move_x, move_y)

        # Dash
        if self.dash_cooldown <= 0 and random.random() < dash_r:
            ddir = (-aim_x, -aim_y) if dist < 120 else (aim_x, aim_y)
            self.dash_timer = 12
            self.dash_cooldown = 45
            self.dash_dir = ddir
            self.dash_invulnerable = True
            play_sfx('dash', vol=0.3)

        # Tiro
        if dist < 450 and random.random() < shoot_r:
            self.shoot(enemy)

        # Habilidade
        if self.ability_cooldown <= 0 and random.random() < ability_r:
            self.use_ability(enemy, walls)

    # ── desenho da arma na mão ──────────────────
    def draw_weapon(self, screen, sx, sy, dir_key):
        name = self.weapon_name
        if not name:
            return

        dx, dy = self.last_direction

        # ── Posição da mão pelo frame de animação ──
        if self.moving:
            leg_off = [0, 8, 0, -8][self.anim_frame]
            body_bob = [0, -2, 0, -2][self.anim_frame]
        else:
            leg_off = 0; body_bob = 0
        arm_swing = -leg_off // 2
        hand_x_rel = 13 + abs(arm_swing)
        hand_y_rel = body_bob + 8

        if dir_key == "direita":
            hx, hy = sx + hand_x_rel, sy + hand_y_rel
        elif dir_key == "esquerda":
            hx, hy = sx - hand_x_rel, sy + hand_y_rel
        elif dir_key == "costas":
            hx, hy = sx + hand_x_rel // 3, sy - hand_y_rel + 4
        else:
            hx, hy = sx + hand_x_rel // 3, sy + hand_y_rel + 2

        # ── Comprimento por direção ──
        length = 26 if dir_key in ("frente", "costas") else 32

        if dir_key == "direita":
            wx, wy = hx + length, hy
        elif dir_key == "esquerda":
            wx, wy = hx - length, hy
        elif dir_key == "costas":
            wx, wy = hx, hy - length
        else:
            wx, wy = hx, hy + length

        mx = (hx + wx) // 2
        my = (hy + wy) // 2
        dx_v = wx - hx
        dy_v = wy - hy
        d = max(1, int(math.sqrt(dx_v*dx_v + dy_v*dy_v)))
        px = -dy_v * 5 // d
        py = dx_v * 5 // d

        # ── Desenho de cada arma ──
        if name == "Arco":
            _draw_limb(screen, (160, 120, 70), hx, hy, wx, wy, 3)
            _draw_limb(screen, (200, 180, 120), mx + px, my + py, mx - px, my - py, 2)
            _draw_limb(screen, (180, 160, 140), mx - px*2, my - py*2, mx + px*2, my + py*2, 1)

        elif name == "Rifle":
            _draw_limb(screen, (60, 60, 75), hx, hy, wx, wy, 5)
            _draw_limb(screen, (40, 40, 55), hx, hy, hx + (wx-hx)//3, hy + (wy-hy)//3, 7)
            _draw_limb(screen, (100, 100, 120), wx - (wx-hx)//6, wy - (wy-hy)//6, wx, wy, 3)

        elif name == "Lança":
            _draw_limb(screen, (140, 120, 90), hx, hy, wx, wy, 3)
            _draw_limb(screen, DARK_GRAY, wx - (wx-hx)//8, wy - (wy-hy)//8, wx, wy, 5)
            _draw_limb(screen, GRAY, wx - (wx-hx)//4, wy - (wy-hy)//4, wx - (wx-hx)//8, wy - (wy-hy)//8, 7)

        elif name == "Shuriken":
            _draw_limb(screen, GRAY, hx, hy, wx, wy, 2)
            rot = 0 if dir_key in ("direita", "esquerda") else 45
            for a in range(0, 360, 90):
                rad = math.radians(a + rot)
                ex = mx + int(math.cos(rad) * 9)
                ey = my + int(math.sin(rad) * 9)
                _draw_limb(screen, DARK_GRAY, mx, my, ex, ey, 3)
                _draw_limb(screen, GRAY, mx - (ex-mx)//3, my - (ey-my)//3, ex, ey, 2)
            pygame.draw.circle(screen, RED, (mx, my), 3)

        elif name == "Estrela":
            _draw_limb(screen, GOLD, hx, hy, wx, wy, 2)
            for a in range(0, 360, 45):
                rad = math.radians(a)
                ex = mx + int(math.cos(rad) * 8)
                ey = my + int(math.sin(rad) * 8)
                _draw_limb(screen, YELLOW, mx, my, ex, ey, 2)
            pygame.draw.circle(screen, GOLD, (mx, my), 3)

        elif name == "Granada":
            pygame.draw.circle(screen, DARK_GRAY, (mx-1, my-1), 6)
            pygame.draw.circle(screen, (80, 80, 90), (mx, my), 6)
            fx = mx + (wx-hx)//4; fy = my + (wy-hy)//4
            _draw_limb(screen, GRAY, mx, my, fx, fy, 2)
            _draw_limb(screen, RED, fx, fy, fx + (wx-hx)//6, fy + (wy-hy)//6, 2)
            pygame.draw.circle(screen, ORANGE, (fx + (wx-hx)//6, fy + (wy-hy)//6), 2)
            _draw_limb(screen, RED, mx - px, my - py, mx + px, my + py, 2)

        elif name == "Orbe":
            t = pygame.time.get_ticks() * 0.003
            pulse = 6 + int(2 * math.sin(t))
            pygame.draw.circle(screen, PURPLE, (mx, my), pulse)
            pygame.draw.circle(screen, (200, 100, 255), (mx-1, my-1), pulse-2)
            pygame.draw.circle(screen, WHITE, (mx-2, my-2), 2)
            glow_r = pulse * 2
            glow = pygame.Surface((glow_r*2, glow_r*2), pygame.SRCALPHA)
            pygame.draw.circle(glow, (*PURPLE, 40), (glow_r, glow_r), glow_r)
            screen.blit(glow, (mx - glow_r, my - glow_r))
            for i in range(3):
                a = t + i * 2.094
                ppx = mx + int(math.cos(a) * (pulse + 4))
                ppy = my + int(math.sin(a) * (pulse + 4))
                pygame.draw.circle(screen, (200, 150, 255), (ppx, ppy), 2)

        elif name == "Corrente":
            _draw_limb(screen, GRAY, hx, hy, wx, wy, 3)
            plx, ply = hx, hy
            for i in range(6):
                t = i / 5
                lx = int(hx + (wx-hx) * t + math.sin(t * 8) * 3)
                ly = int(hy + (wy-hy) * t + math.cos(t * 8) * 3)
                pygame.draw.circle(screen, DARK_GRAY, (lx, ly), 2)
                _draw_limb(screen, GRAY, plx, ply, lx, ly, 1)
                plx, ply = lx, ly

        elif name == "Espada":
            _draw_limb(screen, WHITE, hx, hy, wx, wy, 4)
            _draw_limb(screen, GOLD, hx, hy, hx + (wx-hx)//4, hy + (wy-hy)//4, 6)
            _draw_limb(screen, DARK_GRAY, hx, hy, hx - (wx-hx)//8, hy - (wy-hy)//8, 3)
            _draw_limb(screen, GOLD, mx - px, my - py, mx + px, my + py, 3)
            _draw_limb(screen, (200, 200, 255), hx+(wx-hx)//2, hy+(wy-hy)//2, wx-(wx-hx)//4, wy-(wy-hy)//4, 1)

        elif name == "Faca":
            _draw_limb(screen, LIGHT_GRAY, hx, hy, wx, wy, 3)
            _draw_limb(screen, DARK_GRAY, hx, hy, hx + (wx-hx)//4, hy + (wy-hy)//4, 4)
            _draw_limb(screen, GRAY, wx, wy, wx - (wx-hx)//6, wy - (wy-hy)//6, 2)

        elif name == "Maça":
            _draw_limb(screen, (140, 120, 90), hx, hy, wx, wy, 3)
            head_r = 7
            pygame.draw.circle(screen, DARK_GRAY, (mx, my), head_r)
            pygame.draw.circle(screen, GRAY, (mx, my), head_r-1)
            for a in range(0, 360, 60):
                rad = math.radians(a)
                spx = mx + int(math.cos(rad) * head_r)
                spy = my + int(math.sin(rad) * head_r)
                _draw_limb(screen, GRAY, mx + int(math.cos(rad)*(head_r-2)), my + int(math.sin(rad)*(head_r-2)), spx, spy, 2)

        elif name == "Katana":
            _draw_limb(screen, LIGHT_GRAY, hx, hy, wx, wy, 3)
            _draw_limb(screen, DARK_GRAY, hx, hy, hx + (wx-hx)//3, hy + (wy-hy)//3, 5)
            _draw_limb(screen, WHITE, hx + (wx-hx)//3, hy + (wy-hy)//3, wx, wy, 2)
            _draw_limb(screen, GOLD, mx - px*2, my - py*2, mx + px*2, my + py*2, 3)
            pygame.draw.circle(screen, RED, (mx + px//2, my + py//2), 2)

        elif name == "Garras":
            for i in range(3):
                off = (i - 1) * 3
                gx = hx + (wx-hx)//4 + px * (i-1)
                gy = hy + (wy-hy)//4 + py * (i-1)
                _draw_limb(screen, WHITE, gx, gy, wx + px*(i-1), wy + py*(i-1), 2)
                _draw_limb(screen, DARK_GRAY, gx, gy, gx + (wx-gx)//2, gy + (wy-gy)//2, 3)

        elif name == "Martelo":
            _draw_limb(screen, (140, 120, 90), hx, hy, wx, wy, 4)
            hw, hh = 14, 12
            head_rect = pygame.Rect(mx - hw//2, my - hh//2, hw, hh)
            pygame.draw.rect(screen, DARK_GRAY, head_rect, border_radius=2)
            pygame.draw.rect(screen, GRAY, head_rect, 1)
            _draw_limb(screen, GRAY, mx - hw//2 + 2, my, mx + hw//2 - 2, my, 1)

        elif name == "Foice":
            _draw_limb(screen, (140, 120, 90), hx, hy, wx, wy, 3)
            _draw_limb(screen, WHITE, mx - px*2, my - py*2, mx + px, my + py, 4)
            _draw_limb(screen, WHITE, mx + px, my + py, wx, wy, 3)
            _draw_limb(screen, WHITE, mx - px*2, my - py*2, wx, wy, 2)

        elif name == "Espadão":
            _draw_limb(screen, LIGHT_GRAY, hx, hy, wx, wy, 6)
            _draw_limb(screen, GOLD, hx, hy, hx + (wx-hx)//3, hy + (wy-hy)//3, 8)
            _draw_limb(screen, GOLD, mx - px*2, my - py*2, mx + px*2, my + py*2, 4)
            _draw_limb(screen, DARK_GRAY, hx + (wx-hx)//3, hy + (wy-hy)//3, wx - (wx-hx)//6, wy - (wy-hy)//6, 1)

        # ── Flash de tiro ──
        if self.shoot_flash > 0:
            flash_len = 8
            fpx = hx + int(dx_v * 1.2)
            fpy = hy + int(dy_v * 1.2)
            alpha = int(200 * self.shoot_flash / 4)
            flash_surf = pygame.Surface((flash_len*2, flash_len*2), pygame.SRCALPHA)
            pygame.draw.circle(flash_surf, (255, 255, 200, alpha), (flash_len, flash_len), flash_len)
            pygame.draw.circle(flash_surf, (255, 255, 255, alpha+55), (flash_len, flash_len), flash_len//2)
            screen.blit(flash_surf, (fpx - flash_len, fpy - flash_len))

    # ── desenho ─────────────────────────────────
    def draw(self, screen, enemy=None):
        sx = int(self.x - camera_x)
        sy = int(self.y - camera_y)

        if self.teleport_flash > 0:
            r = self.radius + self.teleport_flash * 2
            pygame.draw.circle(screen, PURPLE, (sx, sy), r, 2)

        if self.invulnerable:
            t   = pygame.time.get_ticks()
            glow= self.radius + 6 + int(4 * math.sin(t * 0.01))
            pygame.draw.circle(screen, GOLD, (sx, sy), glow, 3)

        if self.speed_boost:
            t   = pygame.time.get_ticks()
            glow= self.radius + 4 + int(3 * math.sin(t * 0.015))
            pygame.draw.circle(screen, YELLOW, (sx, sy), glow, 2)

        if self.dash_invulnerable:
            t = pygame.time.get_ticks()
            glow = self.radius + 8 + int(5 * math.sin(t * 0.02))
            pygame.draw.circle(screen, CYAN, (sx, sy), glow, 2)

        if self.dash_timer > 0:
            for i in range(3):
                alpha = 80 - i * 25
                tx = int(self.x - camera_x - self.dash_dir[0] * (i + 1) * 8)
                ty = int(self.y - camera_y - self.dash_dir[1] * (i + 1) * 8)
                trail = pygame.Surface((self.radius * 2, self.radius * 2), pygame.SRCALPHA)
                pygame.draw.circle(trail, (*self.color[:3], alpha), (self.radius, self.radius), self.radius)
                screen.blit(trail, (tx - self.radius, ty - self.radius))

        if self.skid_timer > 0:
            for i in range(3):
                ox = random.randint(-4, 4)
                oy = random.randint(2, 6)
                px = int(self.x - camera_x - self.vx * 2 + ox)
                py = int(self.y - camera_y + self.radius + oy)
                clr = (150 + random.randint(0, 60), 150 + random.randint(0, 60), 180 + random.randint(0, 40))
                pygame.draw.circle(screen, clr, (px, py), random.randint(2, 4))

        shadow_offset_x = 3 + int(self.vx * 0.5)
        shadow_offset_y = 3 + int(self.vy * 0.5)
        pygame.draw.circle(screen, DARK_GRAY,
                           (sx + shadow_offset_x, sy + shadow_offset_y), self.radius)

        char_img = character_images.get(self.char_stats.image_name)
        dx, dy = self.last_direction
        if abs(dx) > abs(dy):
            dir_key = "direita" if dx > 0 else "esquerda"
        elif abs(dy) > 0:
            dir_key = "costas" if dy < 0 else "frente"
        else:
            dir_key = "frente"

        # Arma atrás se estiver de costas
        if dir_key == "costas":
            self.draw_weapon(screen, sx, sy, dir_key)

        if char_img:
            frames = char_img.get(dir_key) or char_img.get("frente")
            if frames:
                frame_idx = self.anim_frame % len(frames) if self.moving else 0
                img = frames[frame_idx]
                if abs(self.lean_angle) > 1:
                    key = (dir_key, frame_idx, int(self.lean_angle))
                    if key not in self._lean_cache:
                        self._lean_cache[key] = pygame.transform.rotate(img, self.lean_angle)
                    img = self._lean_cache[key]
                rect = img.get_rect(center=(sx, sy))
                screen.blit(img, rect)
                if soccer_mode and self.team is not None:
                    overlay = pygame.Surface(rect.size, pygame.SRCALPHA)
                    overlay.fill(TEAM_BLUE_OVERLAY if self.team == 0 else TEAM_RED_OVERLAY)
                    screen.blit(overlay, rect)
                if self.melee_flash > 0:
                    flash = pygame.Surface(rect.size, pygame.SRCALPHA)
                    flash.fill((255, 255, 255, 80))
                    screen.blit(flash, rect)
                    if self.weapon and self.weapon.melee_range:
                        alpha = int(self.melee_flash / 10 * 200)
                        angle = math.atan2(self.last_direction[1], self.last_direction[0])
                        arc_radius = self.weapon.melee_range
                        wcol = self.color
                        arc_surf = pygame.Surface((arc_radius * 2, arc_radius * 2), pygame.SRCALPHA)
                        start_a = angle - math.pi / 3
                        end_a   = angle + math.pi / 3
                        points = [(arc_radius, arc_radius)]
                        steps = 12
                        for i in range(steps + 1):
                            a = start_a + (end_a - start_a) * (i / steps)
                            px = arc_radius + math.cos(a) * arc_radius
                            py = arc_radius + math.sin(a) * arc_radius
                            points.append((int(px), int(py)))
                        if len(points) > 2:
                            # White core + weapon color trail
                            pygame.draw.polygon(arc_surf, (*wcol, alpha), points)
                            pygame.draw.polygon(arc_surf, (255, 255, 255, min(255, alpha + 55)), points, 2)
                        screen.blit(arc_surf, (sx - arc_radius, sy - arc_radius))
        else:
            body_color = WHITE if (self.melee_flash > 0 and self.melee_flash % 2 == 0) else self.color
            pygame.draw.circle(screen, body_color, (sx, sy), self.radius)
            if self.melee_flash > 0 and self.weapon and self.weapon.melee_range:
                alpha = int(self.melee_flash / 10 * 200)
                angle = math.atan2(self.last_direction[1], self.last_direction[0])
                arc_radius = self.weapon.melee_range
                wcol = self.color
                arc_surf = pygame.Surface((arc_radius * 2, arc_radius * 2), pygame.SRCALPHA)
                start_a = angle - math.pi / 3
                end_a   = angle + math.pi / 3
                points = [(arc_radius, arc_radius)]
                steps = 12
                for i in range(steps + 1):
                    a = start_a + (end_a - start_a) * (i / steps)
                    px = arc_radius + math.cos(a) * arc_radius
                    py = arc_radius + math.sin(a) * arc_radius
                    points.append((int(px), int(py)))
                if len(points) > 2:
                    pygame.draw.polygon(arc_surf, (*wcol, alpha), points)
                    pygame.draw.polygon(arc_surf, (255, 255, 255, min(255, alpha + 55)), points, 2)
                screen.blit(arc_surf, (sx - arc_radius, sy - arc_radius))

        # Arma na frente (a menos que já tenha sido desenhada atrás)
        if dir_key != "costas":
            self.draw_weapon(screen, sx, sy, dir_key)

        bw   = 40
        bh   = 5
        bx   = sx - bw // 2
        by   = sy - self.radius - 10
        ratio= max(0, self.hp / self.char_stats.max_hp)
        hp_color = GREEN if ratio > 0.5 else (ORANGE if ratio > 0.25 else RED)
        draw_styled_bar(screen, bx, by, bw, bh, ratio, fg_color=hp_color)

        hp_text = f"{self.hp}/{self.char_stats.max_hp}"
        draw_text(screen, hp_text, 14, WHITE, bx + bw // 2, by - 8)

        for exp in self.explosions:
            exp.draw(screen)

# ─────────────────────────────────────────────
#  PAREDE
# ─────────────────────────────────────────────
class Wall:
    def __init__(self, x, y, w, h):
        self.rect = pygame.Rect(x, y, w, h)

    def draw(self, screen):
        if current_map == SOCCER_MAP_NAME:
            self._draw_soccer(screen)
            return

        cfg = MAPS[current_map]
        r = self.rect
        rx = r.x - camera_x
        ry = r.y - camera_y
        if rx + r.w < -10 or rx > SCREEN_WIDTH + 10 or ry + r.h < -10 or ry > SCREEN_HEIGHT + 10:
            return

        tex = self._get_texture()
        if tex:
            screen.blit(tex, (rx, ry))
            return

        shadow = cfg["wall_shadow"]
        fill   = cfg["wall_fill"]
        edge   = cfg["wall_edge"]
        pygame.draw.rect(screen, shadow, (rx - 2, ry - 1, r.w + 4, r.h + 2), border_radius=4)
        pygame.draw.rect(screen, fill, (rx, ry, r.w, r.h), border_radius=3)
        pygame.draw.rect(screen, edge, (rx, ry, r.w, r.h), 2, border_radius=3)
        top_highlight = (edge[0] + 40, edge[1] + 40, edge[2] + 40)
        pygame.draw.line(screen, top_highlight, (rx + 3, ry + 2), (rx + r.w - 3, ry + 2), 1)

    def _draw_soccer(self, screen):
        r = self.rect
        rx = int(r.x - camera_x)
        ry = int(r.y - camera_y)
        if rx + r.w < -10 or rx > SCREEN_WIDTH + 10 or ry + r.h < -10 or ry > SCREEN_HEIGHT + 10:
            return
        # Mureta de pedra medieval
        stone = (120, 108, 95)
        stone_dark = (90, 80, 70)
        stone_light = (150, 138, 125)
        mortar = (75, 65, 55)
        # corpo
        pygame.draw.rect(screen, stone, (rx, ry, r.w, r.h))
        pygame.draw.rect(screen, stone_dark, (rx, ry, r.w, r.h), 2)
        # linhas de argamassa horizontal a cada 18px
        for ly in range(ry + 9, ry + r.h, 18):
            pygame.draw.line(screen, mortar, (rx + 2, ly), (rx + r.w - 2, ly), 1)
        # linhas verticais alternadas para simular tijolos
        row = 0
        for ly in range(ry, ry + r.h, 18):
            offset = 9 if row % 2 else 0
            for lx in range(rx + offset + 8, rx + r.w, 40):
                if lx < rx + r.w - 2:
                    pygame.draw.line(screen, mortar, (lx, ly + 1), (lx, min(ly + 17, ry + r.h - 1)), 1)
            row += 1
        # realce de luz no topo
        pygame.draw.line(screen, stone_light, (rx + 2, ry + 1), (rx + r.w - 2, ry + 1), 1)

    def _get_texture(self):
        key = (current_map, self.rect.w, self.rect.h)
        if key in TILE_CACHE:
            return TILE_CACHE[key]
        tile_dir = os.path.join(TILES_DIR, current_map)
        if not os.path.isdir(tile_dir):
            TILE_CACHE[key] = None
            return None
        for fname in os.listdir(tile_dir):
            if fname.startswith("fundo"):
                continue
            fpath = os.path.join(tile_dir, fname)
            try:
                img = pygame.image.load(fpath).convert_alpha()
                if img.get_width() == self.rect.w and img.get_height() == self.rect.h:
                    TILE_CACHE[key] = img
                    return img
            except pygame.error:
                continue
        TILE_CACHE[key] = None
        return None

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
        screen.blit(surf, (self.rect.x - camera_x, self.rect.y - camera_y))

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
    draw_panel(screen, (SCREEN_WIDTH // 2 - 120, 6, 240, panel_h), fill=(20, 18, 35), bevel=False)
    draw_text(screen, f"{p1.name}",  20, p1.color, SCREEN_WIDTH // 2 - 80, 14)
    draw_text(screen, f"{p2.name}",  20, p2.color, SCREEN_WIDTH // 2 + 80, 14)
    draw_text(screen, f"{int(dist)}px", 16, ORANGE if melee else UI_TEXT_DIM, SCREEN_WIDTH // 2, 35)
    if melee:
        draw_text(screen, "CORPO A CORPO!", 16, UI_GOLD, SCREEN_WIDTH // 2, 52)

    # Painel inferior esquerdo (P1)
    draw_panel(screen, (8, SCREEN_HEIGHT - 62, 220, 54), fill=(20, 18, 35), bevel=True)
    ab_ratio = 1.0 - (p1.ability_cooldown / Player.ABILITY_COOLDOWN) if Player.ABILITY_COOLDOWN else 1.0
    ab_label = f"[F] {p1.char_stats.ability_name}"
    ab_label = ab_label if len(ab_label) <= 12 else ab_label[:11] + "."
    draw_styled_bar(screen, 14, SCREEN_HEIGHT - 50, 90, 8, ab_ratio,
                    fg_color=GREEN if ab_ratio >= 1.0 else CYAN, label=ab_label)
    sc_ratio = 1.0 - (p1.current_cooldown / p1.shoot_cooldown) if p1.shoot_cooldown else 1.0
    sc_color = GREEN if sc_ratio >= 1.0 else ORANGE
    draw_styled_bar(screen, 120, SCREEN_HEIGHT - 50, 50, 8, sc_ratio, fg_color=sc_color, label="TIRO", label_side="bottom")
    if p1.ability_active:
        t_left = p1.ability_timer // FPS + 1
        draw_text(screen, f"ATIVO {t_left}s", 14, UI_GOLD, 100, SCREEN_HEIGHT - 28)
    draw_text(screen, f"[{p1.weapon_name}]", 11, UI_TEXT_DIM, 120, SCREEN_HEIGHT - 12)

    # Painel inferior direito (P2)
    draw_panel(screen, (SCREEN_WIDTH - 228, SCREEN_HEIGHT - 62, 220, 54), fill=(20, 18, 35), bevel=True)
    ab_ratio2 = 1.0 - (p2.ability_cooldown / Player.ABILITY_COOLDOWN) if Player.ABILITY_COOLDOWN else 1.0
    ab_label2 = f"{p2.char_stats.ability_name} [/]"
    ab_label2 = ab_label2 if len(ab_label2) <= 12 else ab_label2[:11] + "."
    draw_styled_bar(screen, SCREEN_WIDTH - 104, SCREEN_HEIGHT - 50, 90, 8, ab_ratio2,
                    fg_color=GREEN if ab_ratio2 >= 1.0 else CYAN, label=ab_label2)
    sc_ratio2 = 1.0 - (p2.current_cooldown / p2.shoot_cooldown) if p2.shoot_cooldown else 1.0
    sc_color2 = GREEN if sc_ratio2 >= 1.0 else ORANGE
    draw_styled_bar(screen, SCREEN_WIDTH - 170, SCREEN_HEIGHT - 50, 50, 8, sc_ratio2, fg_color=sc_color2, label="TIRO", label_side="bottom")
    if p2.ability_active:
        t_left = p2.ability_timer // FPS + 1
        draw_text(screen, f"ATIVO {t_left}s", 14, UI_GOLD, SCREEN_WIDTH - 100, SCREEN_HEIGHT - 28)
    draw_text(screen, f"[{p2.weapon_name}]", 11, UI_TEXT_DIM, SCREEN_WIDTH - 120, SCREEN_HEIGHT - 12)


def draw_soccer_hud(screen):
    draw_panel(screen, (SCREEN_WIDTH // 2 - 130, 8, 260, 40), fill=(20, 18, 35), bevel=False)
    draw_text(screen, f"🔵 AZUL {score_p1}  🆚  {score_p2} VERMELHO 🔴", 18, WHITE, SCREEN_WIDTH // 2, 28)
    # minipainéis nos cantos com nomes dos times
    draw_panel(screen, (8, SCREEN_HEIGHT - 44, 150, 36), fill=TEAM_BLUE_OVERLAY, bevel=True)
    draw_text(screen, "TIME AZUL", 16, WHITE, 83, SCREEN_HEIGHT - 26)
    draw_panel(screen, (SCREEN_WIDTH - 158, SCREEN_HEIGHT - 44, 150, 36), fill=TEAM_RED_OVERLAY, bevel=True)
    draw_text(screen, "TIME VERMELHO", 16, WHITE, SCREEN_WIDTH - 83, SCREEN_HEIGHT - 26)
    # indicador SUPER
    for i, p in enumerate([player1, player2, player3, player4]):
        if p is None: continue
        if p.super_cooldown > 0:
            sec = p.super_cooldown // 60 + 1
            draw_text(screen, f"SUPER {sec}s", 12, (255, 150, 50), 60 + i * 200, SCREEN_HEIGHT - 12)
        else:
            draw_text(screen, "SUPER ✓", 12, (50, 255, 50), 60 + i * 200, SCREEN_HEIGHT - 12)

# ─────────────────────────────────────────────
#  MAPAS (ARENAS)
# ─────────────────────────────────────────────
MAPS = {
    "arena_classica": {
        "name": "Arena Clássica",
        "world_width": 1600, "world_height": 1200,
        "wall_fill": (50, 45, 65),
        "wall_edge": (75, 65, 95),
        "wall_shadow": (30, 25, 40),
        "floor_a": (18, 16, 30),
        "floor_b": (22, 20, 35),
        "walls": lambda: [
            Wall(100, 100, 50, 250),
            Wall(100, 850, 50, 250),
            Wall(1450, 100, 50, 250),
            Wall(1450, 850, 50, 250),
            Wall(400, 300, 300, 50),
            Wall(900, 300, 300, 50),
            Wall(400, 850, 300, 50),
            Wall(900, 850, 300, 50),
            Wall(750, 570, 100, 60),
            Wall(300, 570, 50, 60),
            Wall(1250, 570, 50, 60),
        ]
    },
    "calabouco": {
        "name": "Calabouço",
        "world_width": 1600, "world_height": 1200,
        "wall_fill": (60, 25, 20),
        "wall_edge": (90, 45, 35),
        "wall_shadow": (35, 15, 10),
        "floor_a": (25, 20, 15),
        "floor_b": (30, 25, 20),
        "walls": lambda: [
            Wall(0, 0, 1600, 30),
            Wall(0, 0, 30, 1200),
            Wall(1570, 0, 30, 1200),
            Wall(0, 1170, 1600, 30),
            Wall(200, 100, 30, 200),
            Wall(1370, 100, 30, 200),
            Wall(200, 900, 30, 200),
            Wall(1370, 900, 30, 200),
            Wall(400, 250, 200, 30),
            Wall(1000, 250, 200, 30),
            Wall(400, 920, 200, 30),
            Wall(1000, 920, 200, 30),
            Wall(700, 400, 200, 30),
            Wall(700, 770, 200, 30),
            Wall(600, 500, 30, 200),
            Wall(970, 500, 30, 200),
        ]
    },
    "coliseu": {
        "name": "Coliseu",
        "world_width": 1800, "world_height": 1200,
        "wall_fill": (55, 50, 45),
        "wall_edge": (80, 75, 65),
        "wall_shadow": (30, 28, 25),
        "floor_a": (30, 25, 20),
        "floor_b": (35, 30, 25),
        "walls": lambda: [
            Wall(0, 0, 1800, 30),
            Wall(0, 0, 30, 1200),
            Wall(1770, 0, 30, 1200),
            Wall(0, 1170, 1800, 30),
            Wall(700, 100, 40, 150),
            Wall(1060, 100, 40, 150),
            Wall(700, 950, 40, 150),
            Wall(1060, 950, 40, 150),
            Wall(400, 500, 40, 200),
            Wall(1360, 500, 40, 200),
            Wall(870, 200, 60, 60),
            Wall(870, 940, 60, 60),
            Wall(300, 200, 150, 30),
            Wall(1350, 200, 150, 30),
            Wall(300, 970, 150, 30),
            Wall(1350, 970, 150, 30),
        ]
    },
    "floresta": {
        "name": "Floresta Encantada",
        "world_width": 2000, "world_height": 1400,
        "wall_fill": (30, 55, 25),
        "wall_edge": (50, 80, 40),
        "wall_shadow": (18, 30, 15),
        "floor_a": (25, 45, 20),
        "floor_b": (30, 52, 25),
        "walls": lambda: [
            Wall(0, 0, 2000, 30),
            Wall(0, 0, 30, 1400),
            Wall(1970, 0, 30, 1400),
            Wall(0, 1370, 2000, 30),
            Wall(300, 200, 40, 200),
            Wall(1660, 200, 40, 200),
            Wall(300, 1000, 40, 200),
            Wall(1660, 1000, 40, 200),
            Wall(600, 400, 200, 40),
            Wall(1200, 400, 200, 40),
            Wall(600, 960, 200, 40),
            Wall(1200, 960, 200, 40),
            Wall(900, 650, 200, 100),
            Wall(400, 680, 60, 40),
            Wall(1540, 680, 60, 40),
            Wall(750, 620, 30, 160),
            Wall(1220, 620, 30, 160),
        ]
    },
    "templo_gelado": {
        "name": "Templo Gelado",
        "world_width": 1600, "world_height": 1200,
        "wall_fill": (40, 60, 80),
        "wall_edge": (100, 140, 180),
        "wall_shadow": (20, 35, 50),
        "floor_a": (35, 45, 55),
        "floor_b": (45, 55, 65),
        "walls": lambda: [
            Wall(0, 0, 1600, 30),
            Wall(0, 0, 30, 1200),
            Wall(1570, 0, 30, 1200),
            Wall(0, 1170, 1600, 30),
            Wall(400, 80, 30, 200),
            Wall(1170, 80, 30, 200),
            Wall(400, 920, 30, 200),
            Wall(1170, 920, 30, 200),
            Wall(200, 350, 150, 30),
            Wall(1250, 350, 150, 30),
            Wall(200, 820, 150, 30),
            Wall(1250, 820, 150, 30),
            Wall(700, 200, 200, 30),
            Wall(700, 970, 200, 30),
            Wall(580, 500, 30, 200),
            Wall(990, 500, 30, 200),
            Wall(750, 560, 100, 80),
        ]
    },
    SOCCER_MAP_NAME: {
        "name": "Estádio Soul Strike",
        "world_width": 1600, "world_height": 900,
        "wall_fill": (60, 55, 70),
        "wall_edge": (80, 75, 90),
        "wall_shadow": (35, 30, 45),
        "floor_a": (30, 130, 50),
        "floor_b": (35, 145, 55),
        "walls": lambda: [
            Wall(0, 0, 1600, 20),
            Wall(0, 880, 1600, 20),
            Wall(20, 20, 20, 350),
            Wall(20, 530, 20, 350),
            Wall(1560, 20, 20, 350),
            Wall(1560, 530, 20, 350),
        ]
    },
}

current_map = "arena_classica"

WORLD_WIDTH = SCREEN_WIDTH
WORLD_HEIGHT = SCREEN_HEIGHT
camera_x = 0
camera_y = 0
camera_zoom = 1.0

walls = MAPS[current_map]["walls"]()

TILE_CACHE = {}

def rebuild_map():
    global walls, floor_surface, WORLD_WIDTH, WORLD_HEIGHT, TILE_CACHE
    cfg = MAPS[current_map]
    walls = cfg["walls"]()
    WORLD_WIDTH = cfg.get("world_width", SCREEN_WIDTH)
    WORLD_HEIGHT = cfg.get("world_height", SCREEN_HEIGHT)
    for k in list(TILE_CACHE.keys()):
        if isinstance(k, tuple) and k[0] == current_map:
            del TILE_CACHE[k]

    floor_surface = pygame.Surface((WORLD_WIDTH, WORLD_HEIGHT))
    fundo_img = None
    tile_dir = os.path.join(TILES_DIR, current_map)
    if os.path.isdir(tile_dir):
        for fname in os.listdir(tile_dir):
            if fname.startswith("fundo") and fname.endswith(".png"):
                fpath = os.path.join(tile_dir, fname)
                try:
                    fundo_img = pygame.image.load(fpath).convert()
                    break
                except pygame.error:
                    continue
    if fundo_img:
        fundo_img = pygame.transform.scale(fundo_img, (WORLD_WIDTH, WORLD_HEIGHT))
        floor_surface.blit(fundo_img, (0, 0))
    else:
        for gx in range(0, WORLD_WIDTH, 32):
            for gy in range(0, WORLD_HEIGHT, 32):
                color = cfg["floor_a"] if ((gx // 32) + (gy // 32)) % 2 == 0 else cfg["floor_b"]
                pygame.draw.rect(floor_surface, color, (gx, gy, 32, 32))
                if gx % 64 == 0 and gy % 64 == 0:
                    c = cfg["floor_a"] if color == cfg["floor_b"] else cfg["floor_b"]
                    pygame.draw.rect(floor_surface, c, (gx + 14, gy + 14, 4, 4))

    # ── DESENHO DO CAMPO DE FUTEBOL ──
    if current_map == SOCCER_MAP_NAME:
        lc = (200, 200, 180)
        _draw_rect = lambda r: pygame.draw.rect(floor_surface, lc, r, width=3)
        _draw_circ = lambda c, r: pygame.draw.circle(floor_surface, lc, c, r, width=3)
        _draw_arc  = lambda r, s, e: pygame.draw.arc(floor_surface, lc, r, s, e, width=3)

        # Linha do meio
        pygame.draw.line(floor_surface, lc, (800, 20), (800, 880), 3)

        # Círculo central
        _draw_circ((800, 450), 80)

        # Grande área esquerda
        _draw_rect((20, 200, 200, 500))
        # Pequena área esquerda
        _draw_rect((20, 330, 100, 240))
        # Grande área direita
        _draw_rect((1380, 200, 200, 500))
        # Pequena área direita
        _draw_rect((1480, 330, 100, 240))

        # Escanteios (4 arcos de ¼ de círculo dentro do campo)
        cr = 30
        corners = [
            (20, 20, 0, math.pi/2),            # top-left
            (1580, 20, math.pi/2, math.pi),    # top-right
            (20, 880, 3*math.pi/2, 2*math.pi), # bottom-left
            (1580, 880, math.pi, 3*math.pi/2), # bottom-right
        ]
        for cx, cy, sa, ea in corners:
            _draw_arc(pygame.Rect(cx - cr, cy - cr, cr*2, cr*2), sa, ea)

# ─────────────────────────────────────────────
#  INICIALIZAÇÃO PYGAME
# ─────────────────────────────────────────────
pygame.init()
pygame.display.set_caption("Soul Strike")
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.FULLSCREEN | pygame.SCALED)
clock  = pygame.time.Clock()

for d in (ASSET_DIR, UI_DIR, FONT_DIR, TILES_DIR,
          os.path.join(ASSET_DIR, "characters"),
          os.path.join(ASSET_DIR, "backgrounds"),
          os.path.join(ASSET_DIR, "effects")):
    os.makedirs(d, exist_ok=True)

# ── SOM ──
SOUND_DIR = os.path.join(ASSET_DIR, "sounds")
os.makedirs(SOUND_DIR, exist_ok=True)
sfx = {}
if pygame.mixer.get_init() is None:
    try:
        pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
    except pygame.error:
        pass
if pygame.mixer.get_init():
    for f in os.listdir(SOUND_DIR):
        if f.endswith('.wav'):
            name = os.path.splitext(f)[0]
            try:
                s = pygame.mixer.Sound(os.path.join(SOUND_DIR, f))
                sfx[name] = s
            except pygame.error:
                pass

def play_sfx(name, vol=0.5):
    s = sfx.get(name)
    if s:
        s.set_volume(vol)
        s.play()

# ── BGM ──
bgm_path = os.path.join(SOUND_DIR, "bgm.wav")
battle_bgm_path = os.path.join(SOUND_DIR, "battle_bgm.mp3")

if pygame.mixer.get_init():
    if os.path.isfile(bgm_path):
        try:
            pygame.mixer.music.load(bgm_path)
            pygame.mixer.music.set_volume(0.3)
        except pygame.error:
            pass

def play_menu_bgm():
    if pygame.mixer.get_init() and os.path.isfile(bgm_path):
        try:
            pygame.mixer.music.stop()
            pygame.mixer.music.load(bgm_path)
            pygame.mixer.music.set_volume(0.3)
            pygame.mixer.music.play(-1)
        except pygame.error:
            pass

def play_battle_bgm():
    if pygame.mixer.get_init() and os.path.isfile(battle_bgm_path):
        try:
            pygame.mixer.music.stop()
            pygame.mixer.music.load(battle_bgm_path)
            pygame.mixer.music.set_volume(0.3)
            pygame.mixer.music.play(-1)
        except pygame.error:
            pass

def stop_bgm(fade_ms=1000):
    if pygame.mixer.get_init() and pygame.mixer.music.get_busy():
        pygame.mixer.music.fadeout(fade_ms)

# ── CHÃO PRÉ-RENDERIZADO (usa o mapa atual) ──
rebuild_map()

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
STATE_MAIN_MENU   = 6
STATE_ABOUT       = 7
STATE_CREDITS     = 8
STATE_MODE_SELECT = 9
STATE_QR_CODE    = 10
STATE_DEATH_ANIM = 11

current_state = STATE_LOADING

vs_timer = 0
VS_DURATION = 150  # frames (~2.5s)
DEATH_ANIM_DURATION = 90  # frames (~1.5s)

loading_tips = [
    "Aproxime-se para causar dano extra em combate corpo a corpo!",
    "Cada lutador tem um poder único. Ative com F ou /",
    "Guerreiro causa dano alto de perto, Atirador é devastador à distância.",
    "Tanque é lento mas resistente. Ninja é rápido mas frágil.",
    "Use as paredes da arena para se proteger dos tiros!",
    "A barra de poder mostra quando seu especial está disponível.",
    "Mire com o movimento e atire na direção oposta para surpreender.",
    "Cada classe tem um estilo único — encontre o seu!",
    "5 mapas disponíveis — escolha com [ ] na seleção de personagem!",
    "Nos mapas maiores, a câmera acompanha a batalha automaticamente.",
    "Armas brancas agora têm movimento de ataque mesmo sem acertar.",
    "Habilidades funcionam independente da arma equipada!",
]

character_images = {}
total = len(CHARACTER_TYPES)
start = pygame.time.get_ticks()
for i, ch in enumerate(CHARACTER_TYPES):
    base = _char_name_to_file(ch)
    result = _load_char_frames(base)
    if result:
        character_images[ch.image_name] = result
    else:
        frames = [_generate_frame(ch, f) for f in range(4)]
        character_images[ch.image_name] = {
            "frente": [frames[0]],
            "costas": [frames[2]],
            "direita": [frames[1]],
            "esquerda": [frames[3]],
        }
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

current_state = STATE_MAIN_MENU
play_menu_bgm()

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
p1_weapon_idx = 0
p2_weapon_idx = 0
p1_selected  = False
p2_selected  = False
ai_mode      = False

death_timer = 0
death_particles = []
death_winner_name = ""

# ── Futebol ──
soccer_mode = False
soccer_players = 4
ball = None
goals = []
score_p1 = 0
score_p2 = 0
goal_timer = 0
goal_scorer = ""
goal_team = 0
player3 = None
player4 = None
p3_char_idx = 0
p4_char_idx = 0
p3_selected = False
p4_selected = False
player_chars = [0, 0, 0, 0]


about_scroll = 0
about_lines = [
    (["4 PILARES DA POO NO SOUL STRIKE", ""], UI_GOLD, 28),
    ([], None, 0),
    (["1. ENCAPSULAMENTO", "────────────────────────────────"], ORANGE, 22),
    (["A classe Player encapsula seus dados (hp, x, y, cooldowns)", "e expõe apenas métodos controlados para modificá-los.", "", "Exemplo: take_damage() verifica invulnerabilidade e", "dash_invulnerable antes de alterar o HP. Atributos como", "_dash_held, _lean_cache e _ai_tick são privados por", "convenção (prefixo _), impedindo acesso externo indevido.", "A propriedade @property done em Explosion e Barrier", "permite leitura controlada sem expor o timer interno."], UI_TEXT, 18),
    ([], None, 0),
    (["2. ABSTRAÇÃO", "────────────────────────────────"], ORANGE, 22),
    (["Wall.collides_with_player() esconde a matemática de", "colisão círculo vs retângulo em uma única chamada.", "", "draw_loading() abstrai ~40 linhas de rendering", "(partículas, logo com glow, barra de progresso, dicas)", "em uma chamada com 3 parâmetros.", "", "load_character_sprites() esconde IO de arquivo,", "slicing de spritesheet e fallback procedural.", "", "draw_styled_bar() abstrai o cálculo de proporção,", "cores e bordas de uma barra de progresso."], UI_TEXT, 18),
    ([], None, 0),
    (["3. HERANÇA", "────────────────────────────────"], ORANGE, 22),
    (["Todas as classes do jogo (Player, Bullet, Explosion,", "Wall, Barrier) implementam os mesmos métodos:", "update() e draw() — duck typing em Python.", "", "CharacterStats (namedtuple) serve como estrutura base", "que todos os 8 personagens estendem com valores", "específicos (Guerreiro, Atirador, Tanque, Ninja,", "Speedster, Bomber, Ghost, Titan).", "", "Cada personagem herda a mesma interface de Player", "e especializa o comportamento via use_ability()."], UI_TEXT, 18),
    ([], None, 0),
    (["4. POLIMORFISMO", "────────────────────────────────"], ORANGE, 22),
    (["O método use_ability() tem 8 comportamentos diferentes", "dependendo da classe do personagem:", "", "  Guerreiro → investida (charge em linha reta)", "  Atirador  → rajada (5 balas em leque de 60°)", "  Tanque    → muralha (barreira na direção atual)", "  Ninja     → shuriken (3 projéteis em leque de 45°)", "  Speedster → turbo (3× velocidade por 4s)", "  Bomber    → explosão radial (8 balas explosivas)", "  Ghost     → teletransporte (posição aleatória segura)", "  Titan     → invulnerável (5s sem tomar dano)", "", "O método draw() também é polimórfico: Player desenha", "sprite + vida + efeitos, Bullet desenha projétil,", "Wall desenha parede estilizada com sombra e relevo,", "Explosion desenha explosão em área com fade."], UI_TEXT, 18),
    ([], None, 0),
    (["Pressione ESC ou clique em VOLTAR para retornar"], UI_TEXT_DIM, 16),
]

# Dificuldade da IA
DIFFICULTIES = {
    'easy':   {'reaction': 12, 'scatter': 0.35, 'shoot_rate': 0.015, 'dash_rate': 0.002, 'ability_rate': 0.003, 'range': 260},
    'medium': {'reaction': 6,  'scatter': 0.18, 'shoot_rate': 0.04,  'dash_rate': 0.008, 'ability_rate': 0.015, 'range': 220},
    'hard':   {'reaction': 2,  'scatter': 0.06, 'shoot_rate': 0.07,  'dash_rate': 0.02,  'ability_rate': 0.03,  'range': 200},
}
difficulty = 'medium'

# Botões créditos
CREDIT_BTNS = [
    {'name': 'Cauã Pedrozo Brito', 'github': 'https://github.com/cauapbritto', 'linkedin': 'https://www.linkedin.com/in/cau%C3%A3-pedrozo-brito-8a685b358/'},
    {'name': 'Alber Alberguini Cabral', 'github': 'https://github.com/Alberguini', 'linkedin': 'https://www.linkedin.com/in/alber-alberguini-cabral-939002293/'},
]

# ─────────────────────────────────────────────
#  FUNÇÕES DE ESTADO
# ─────────────────────────────────────────────
def start_game():
    global player1, player2, ai_mode, current_state
    global player3, player4, ball, goals, score_p1, score_p2, goal_timer, goal_scorer
    global soccer_mode, soccer_players
    if soccer_mode:
        remote_chars = remote_input.get_all_player_chars()
        idx1 = remote_chars.get(1, 0)
        idx2 = remote_chars.get(2, 0)
        idx3 = remote_chars.get(3, 0)
        idx4 = remote_chars.get(4, 0)
        ch1 = CHARACTER_TYPES[idx1]
        ch2 = CHARACTER_TYPES[idx2]
        ch3 = CHARACTER_TYPES[idx3]
        ch4 = CHARACTER_TYPES[idx4]
        p1 = Player(300, 350, {}, ch1, name="P1", team=0 if soccer_players > 2 else None)
        p2 = Player(1300, 350, {}, ch2, name="P2", team=1 if soccer_players > 2 else None)
        if soccer_players > 2:
            p3 = Player(300, 550, {}, ch3, name="P3", team=0)
            p4 = Player(1300, 550, {}, ch4, name="P4", team=1)
            player3, player4 = p3, p4
        else:
            player3 = player4 = None
        player1, player2 = p1, p2
        ball = Ball(WORLD_WIDTH // 2, WORLD_HEIGHT // 2)
        goals = [
            Goal(2, 370, 18, 160, 0, TEAM_BLUE_OVERLAY),
            Goal(1580, 370, 18, 160, 1, TEAM_RED_OVERLAY),
        ]
        score_p1 = 0
        score_p2 = 0
        goal_timer = 0
        goal_scorer = ""
    else:
        ch1 = CHARACTER_TYPES[p1_char_idx]
        ch2 = CHARACTER_TYPES[p2_char_idx]
        wp1 = CHARACTER_WEAPONS[ch1.name][p1_weapon_idx]
        wp2 = CHARACTER_WEAPONS[ch2.name][p2_weapon_idx]
        player1 = Player(
            SCREEN_WIDTH // 4, SCREEN_HEIGHT // 2,
            {'up': pygame.K_w, 'down': pygame.K_s, 'left': pygame.K_a,
             'right': pygame.K_d, 'shoot': pygame.K_g, 'ability': pygame.K_f},
            ch1,
            name=p1_name or "Jogador 1",
            weapon=wp1,
        )
        player2 = Player(
            SCREEN_WIDTH * 3 // 4, SCREEN_HEIGHT // 2,
            {'up': pygame.K_UP, 'down': pygame.K_DOWN, 'left': pygame.K_LEFT,
             'right': pygame.K_RIGHT, 'shoot': pygame.K_SEMICOLON, 'ability': pygame.K_SLASH},
            ch2,
            name=p2_name or "Jogador 2",
            weapon=wp2,
        )
        player3 = None
        player4 = None
        ball = None
        goals = []
    global vs_timer, camera_x, camera_y
    if soccer_mode:
        camera_x = 0
        camera_y = 0
    else:
        camera_x = max(0, min(WORLD_WIDTH - SCREEN_WIDTH, (player1.x + player2.x) / 2 - SCREEN_WIDTH / 2))
        camera_y = max(0, min(WORLD_HEIGHT - SCREEN_HEIGHT, (player1.y + player2.y) / 2 - SCREEN_HEIGHT / 2))
    vs_timer = VS_DURATION
    current_state = STATE_VS_SCREEN
    remote_input.release_all()
    remote_input.set_game_state("playing")

def reset_game():
    global player1, player2, winner
    global p1_name, p2_name, active_input
    global p1_char_idx, p2_char_idx, p1_selected, p2_selected, ai_mode
    global about_scroll, current_state, p1_weapon_idx, p2_weapon_idx
    global death_timer, death_particles, death_winner_name
    global soccer_mode, soccer_players, ball, goals, score_p1, score_p2, goal_timer, goal_scorer
    global player3, player4, player_chars
    player1 = player2 = winner = None
    p1_name = p2_name = ""
    active_input = 0
    p1_char_idx = p2_char_idx = 0
    p1_weapon_idx = p2_weapon_idx = 0
    p1_selected = p2_selected = False
    ai_mode = False
    about_scroll = 0
    death_timer = 0
    death_particles = []
    death_winner_name = ""
    soccer_mode = False
    ball = None
    goals = []
    score_p1 = score_p2 = 0
    goal_timer = 0
    goal_scorer = ""
    player3 = player4 = None
    player_chars = [0, 0, 0, 0]
    if current_map == SOCCER_MAP_NAME:
        current_map = "arena_classica"
        rebuild_map()
    current_state = STATE_MAIN_MENU
    remote_input.set_game_state("menu")
    play_menu_bgm()

def _cycle_map(direction):
    global current_map
    keys = list(MAPS.keys())
    idx = keys.index(current_map)
    current_map = keys[(idx + direction) % len(keys)]
    rebuild_map()

# ─────────────────────────────────────────────
#  LOOP PRINCIPAL
# ─────────────────────────────────────────────
start_server_thread()
running = True
while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        # ── MENU PRINCIPAL ────────────────────
        if current_state == STATE_MAIN_MENU:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RETURN or event.key == pygame.K_SPACE:
                    play_sfx('confirm')
                    p1_char_idx = 0
                    p2_char_idx = 0
                    p1_weapon_idx = 0
                    p2_weapon_idx = 0
                    p1_selected = False
                    p2_selected = False
                    current_state = STATE_MODE_SELECT
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mx, my = event.pos
                jogar_rect = pygame.Rect(SCREEN_WIDTH // 2 - 120, 260, 240, 70)
                if jogar_rect.collidepoint(mx, my):
                    play_sfx('confirm')
                    p1_char_idx = 0
                    p2_char_idx = 0
                    p1_weapon_idx = 0
                    p2_weapon_idx = 0
                    p1_selected = False
                    p2_selected = False
                    current_state = STATE_MODE_SELECT
                btn_sobre = pygame.Rect(20, SCREEN_HEIGHT - 60, 40, 40)
                if btn_sobre.collidepoint(mx, my):
                    play_sfx('click')
                    about_scroll = 0
                    if pygame.mixer.get_init():
                        pygame.mixer.music.pause()
                    current_state = STATE_ABOUT
                btn_creditos = pygame.Rect(SCREEN_WIDTH - 60, SCREEN_HEIGHT - 60, 40, 40)
                if btn_creditos.collidepoint(mx, my):
                    play_sfx('click')
                    if pygame.mixer.get_init():
                        pygame.mixer.music.pause()
                    current_state = STATE_CREDITS

        # ── SOBRE ─────────────────────────────
        elif current_state == STATE_ABOUT:
            def _leave_menu():
                play_sfx('click')
                if pygame.mixer.get_init():
                    pygame.mixer.music.unpause()
                return STATE_MAIN_MENU
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    current_state = _leave_menu()
                if event.key == pygame.K_UP:
                    about_scroll = max(0, about_scroll - 20)
                if event.key == pygame.K_DOWN:
                    about_scroll += 20
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mx, my = event.pos
                voltar = pygame.Rect(SCREEN_WIDTH // 2 - 80, SCREEN_HEIGHT - 55, 160, 40)
                if voltar.collidepoint(mx, my):
                    current_state = _leave_menu()
            if event.type == pygame.MOUSEWHEEL:
                about_scroll = max(0, about_scroll - event.y * 30)

        # ── CRÉDITOS ──────────────────────────
        elif current_state == STATE_CREDITS:
            def _leave_credits():
                play_sfx('click')
                if pygame.mixer.get_init():
                    pygame.mixer.music.unpause()
                return STATE_MAIN_MENU
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    current_state = _leave_credits()
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mx, my = event.pos
                voltar = pygame.Rect(SCREEN_WIDTH // 2 - 80, SCREEN_HEIGHT - 55, 160, 40)
                if voltar.collidepoint(mx, my):
                    current_state = _leave_credits()
                for ci, dev in enumerate(CREDIT_BTNS):
                    cy = 110 + ci * 90
                    gh_r = pygame.Rect(SCREEN_WIDTH // 2 - 30, cy + 30, 24, 24)
                    li_r = pygame.Rect(SCREEN_WIDTH // 2 + 8,  cy + 30, 24, 24)
                    if gh_r.collidepoint(mx, my) and dev['github']:
                        webbrowser.open(dev['github'])
                    if li_r.collidepoint(mx, my) and dev['linkedin']:
                        webbrowser.open(dev['linkedin'])

        # ── SELEÇÃO DE MODO ────────────────────
        elif current_state == STATE_MODE_SELECT:
            def _choose_mode(ai):
                play_sfx('confirm')
                global ai_mode, p2_name, p1_selected, p2_selected, current_state, soccer_mode
                soccer_mode = False
                ai_mode = ai
                p2_name = "CPU" if ai else ""
                p2_selected = ai
                p1_selected = False
                if ai:
                    remote_input.release_all()
                    remote_input.set_game_state("char_select")
                    current_state = STATE_CHAR_SELECT
                else:
                    current_state = STATE_QR_CODE
            def _choose_soccer_1v1():
                play_sfx('confirm')
                global soccer_mode, soccer_players, current_state, ai_mode, current_map
                soccer_mode = True
                soccer_players = 2
                current_map = SOCCER_MAP_NAME
                rebuild_map()
                remote_input.release_all()
                remote_input.set_game_state("char_select")
                remote_input.reset_lobby()
                current_state = STATE_QR_CODE
            def _choose_soccer():
                play_sfx('confirm')
                global soccer_mode, soccer_players, current_state, ai_mode, current_map
                soccer_mode = True
                soccer_players = 4
                current_map = SOCCER_MAP_NAME
                rebuild_map()
                remote_input.release_all()
                remote_input.set_game_state("char_select")
                remote_input.reset_lobby()
                current_state = STATE_QR_CODE
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_1 or event.key == pygame.K_LEFT or event.key == pygame.K_RIGHT:
                    _choose_mode(True)
                elif event.key == pygame.K_2:
                    _choose_mode(False)
                elif event.key == pygame.K_3:
                    _choose_soccer()
                elif event.key == pygame.K_4:
                    _choose_soccer_1v1()
                elif event.key == pygame.K_ESCAPE:
                    play_sfx('cancel')
                    current_state = STATE_MAIN_MENU
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mx, my = event.pos
                cw, ch = 240, 200
                gap = 20
                total = cw * 4 + gap * 3
                start_x = SCREEN_WIDTH // 2 - total // 2
                yy = SCREEN_HEIGHT // 2 - ch // 2
                rects = [
                    pygame.Rect(start_x, yy, cw, ch),
                    pygame.Rect(start_x + cw + gap, yy, cw, ch),
                    pygame.Rect(start_x + (cw + gap) * 2, yy, cw, ch),
                    pygame.Rect(start_x + (cw + gap) * 3, yy, cw, ch),
                ]
                if rects[0].collidepoint(mx, my):
                    _choose_mode(True)
                elif rects[1].collidepoint(mx, my):
                    _choose_mode(False)
                elif rects[2].collidepoint(mx, my):
                    _choose_soccer()
                elif rects[3].collidepoint(mx, my):
                    _choose_soccer_1v1()

        # ── QR CODE ────────────────────────────
        elif current_state == STATE_QR_CODE:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RETURN or event.key == pygame.K_SPACE:
                    play_sfx('confirm')
                    remote_input.release_all()
                    remote_input.set_game_state("char_select")
                    if soccer_mode:
                        remote_input.set_game_state("start_game")
                    else:
                        current_state = STATE_CHAR_SELECT
                elif event.key == pygame.K_ESCAPE:
                    play_sfx('cancel')
                    if soccer_mode:
                        soccer_mode = False
                        soccer_players = 4
                    current_state = STATE_MODE_SELECT
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mx, my = event.pos
                cont_rect = pygame.Rect(SCREEN_WIDTH // 2 - 100, SCREEN_HEIGHT - 65, 200, 44)
                if cont_rect.collidepoint(mx, my):
                    play_sfx('confirm')
                    remote_input.release_all()
                    remote_input.set_game_state("char_select")
                    if soccer_mode:
                        remote_input.set_game_state("start_game")
                    else:
                        current_state = STATE_CHAR_SELECT
                if soccer_mode:
                    # Botão INICIAR para futebol
                    iniciar_rect = pygame.Rect(SCREEN_WIDTH // 2 - 100, SCREEN_HEIGHT - 130, 200, 44)
                    if iniciar_rect.collidepoint(mx, my):
                        play_sfx('confirm')
                        remote_input.set_game_state("start_game")

        # ── SELEÇÃO DE PERSONAGEM ──────────────
        elif current_state == STATE_CHAR_SELECT:
            if event.type == pygame.KEYDOWN:
                if not p1_selected:
                    if event.key == pygame.K_a:
                        ch = CHARACTER_TYPES[p1_char_idx]
                        p1_char_idx = (p1_char_idx - 1) % len(CHARACTER_TYPES)
                        p1_weapon_idx = 0
                        play_sfx('select')
                    if event.key == pygame.K_d:
                        ch = CHARACTER_TYPES[p1_char_idx]
                        p1_char_idx = (p1_char_idx + 1) % len(CHARACTER_TYPES)
                        p1_weapon_idx = 0
                        play_sfx('select')
                    if event.key == pygame.K_w:
                        ch = CHARACTER_TYPES[p1_char_idx]
                        weapons = CHARACTER_WEAPONS[ch.name]
                        p1_weapon_idx = (p1_weapon_idx - 1) % len(weapons)
                        play_sfx('select')
                    if event.key == pygame.K_s:
                        ch = CHARACTER_TYPES[p1_char_idx]
                        weapons = CHARACTER_WEAPONS[ch.name]
                        p1_weapon_idx = (p1_weapon_idx + 1) % len(weapons)
                        play_sfx('select')
                    if event.key == pygame.K_g:
                        p1_selected = True
                        play_sfx('confirm')
                if not p2_selected and not ai_mode:
                    if event.key == pygame.K_LEFT:
                        p2_char_idx = (p2_char_idx - 1) % len(CHARACTER_TYPES)
                        p2_weapon_idx = 0
                        play_sfx('select')
                    if event.key == pygame.K_RIGHT:
                        p2_char_idx = (p2_char_idx + 1) % len(CHARACTER_TYPES)
                        p2_weapon_idx = 0
                        play_sfx('select')
                    if event.key == pygame.K_UP:
                        ch2 = CHARACTER_TYPES[p2_char_idx]
                        weapons2 = CHARACTER_WEAPONS[ch2.name]
                        p2_weapon_idx = (p2_weapon_idx - 1) % len(weapons2)
                        play_sfx('select')
                    if event.key == pygame.K_DOWN:
                        ch2 = CHARACTER_TYPES[p2_char_idx]
                        weapons2 = CHARACTER_WEAPONS[ch2.name]
                        p2_weapon_idx = (p2_weapon_idx + 1) % len(weapons2)
                        play_sfx('select')
                    if event.key == pygame.K_m:
                        p2_selected = True
                        play_sfx('confirm')
                if event.key == pygame.K_LEFTBRACKET:
                    _cycle_map(-1)
                    play_sfx('click')
                if event.key == pygame.K_RIGHTBRACKET:
                    _cycle_map(1)
                    play_sfx('click')
                if event.key == pygame.K_ESCAPE:
                    play_sfx('cancel')
                    current_state = STATE_MAIN_MENU
                if p1_selected and (p2_selected or ai_mode):
                    play_sfx('confirm')
                    start_game()
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mx, my = event.pos
                panel_w = 220
                px = SCREEN_WIDTH // 2 - panel_w // 2
                py = SCREEN_HEIGHT - 52
                mlx = px + 8
                mrx = px + panel_w - 38
                myy = py + 5
                map_left_rect  = pygame.Rect(mlx, myy, 30, 30)
                map_right_rect = pygame.Rect(mrx, myy, 30, 30)
                if map_left_rect.collidepoint(mx, my):
                    _cycle_map(-1)
                    play_sfx('click')
                elif map_right_rect.collidepoint(mx, my):
                    _cycle_map(1)
                    play_sfx('click')
                else:
                    card_w, card_h = 280, 340
                    card_y = 85
                    for p_num, (cx, sel, idx, wp_idx) in enumerate([
                        (190, p1_selected, p1_char_idx, p1_weapon_idx),
                        (770, p2_selected if not ai_mode else True, p2_char_idx, p2_weapon_idx),
                    ]):
                        ch = CHARACTER_TYPES[idx]
                        weapons = CHARACTER_WEAPONS[ch.name]
                        card_x = cx - card_w // 2

                        if p_num == 0 and not sel:
                            # Setas personagem
                            left_ch  = pygame.Rect(card_x + 5, card_y + 30, 28, 22)
                            right_ch = pygame.Rect(card_x + card_w - 33, card_y + 30, 28, 22)
                            # Linhas das armas
                            ranged_rect = pygame.Rect(card_x + 10, card_y + 198, card_w - 20, 20)
                            melee_rect  = pygame.Rect(card_x + 10, card_y + 220, card_w - 20, 20)
                            # Card inteiro
                            card_r = pygame.Rect(card_x, card_y, card_w, card_h)

                            if left_ch.collidepoint(mx, my):
                                p1_char_idx = (p1_char_idx - 1) % len(CHARACTER_TYPES)
                                p1_weapon_idx = 0
                                play_sfx('select')
                            elif right_ch.collidepoint(mx, my):
                                p1_char_idx = (p1_char_idx + 1) % len(CHARACTER_TYPES)
                                p1_weapon_idx = 0
                                play_sfx('select')
                            elif ranged_rect.collidepoint(mx, my):
                                p1_weapon_idx = 0
                                play_sfx('select')
                            elif melee_rect.collidepoint(mx, my):
                                p1_weapon_idx = 1 if len(weapons) > 1 else 0
                                play_sfx('select')
                            elif card_r.collidepoint(mx, my):
                                p1_selected = True
                                play_sfx('confirm')

                        if p_num == 1 and not sel and not ai_mode:
                            left_ch  = pygame.Rect(card_x + 5, card_y + 30, 28, 22)
                            right_ch = pygame.Rect(card_x + card_w - 33, card_y + 30, 28, 22)
                            ranged_rect = pygame.Rect(card_x + 10, card_y + 198, card_w - 20, 20)
                            melee_rect  = pygame.Rect(card_x + 10, card_y + 220, card_w - 20, 20)
                            card_r = pygame.Rect(card_x, card_y, card_w, card_h)

                            if left_ch.collidepoint(mx, my):
                                p2_char_idx = (p2_char_idx - 1) % len(CHARACTER_TYPES)
                                p2_weapon_idx = 0
                                play_sfx('select')
                            elif right_ch.collidepoint(mx, my):
                                p2_char_idx = (p2_char_idx + 1) % len(CHARACTER_TYPES)
                                p2_weapon_idx = 0
                                play_sfx('select')
                            elif ranged_rect.collidepoint(mx, my):
                                p2_weapon_idx = 0
                                play_sfx('select')
                            elif melee_rect.collidepoint(mx, my):
                                p2_weapon_idx = 1 if len(weapons) > 1 else 0
                                play_sfx('select')
                            elif card_r.collidepoint(mx, my):
                                p2_selected = True
                                play_sfx('confirm')

        # ── GAME OVER ─────────────────────────
        elif current_state == STATE_GAME_OVER:
            if event.type == pygame.KEYDOWN and event.key == pygame.K_r:
                play_sfx('confirm')
                reset_game()

    # ── Controle remoto na seleção de personagem ──
    if current_state == STATE_CHAR_SELECT:
        r = remote_input.get_state()
        if not p1_selected:
            if r.get("p1_char_left"):
                p1_char_idx = (p1_char_idx - 1) % len(CHARACTER_TYPES)
                p1_weapon_idx = 0
                remote_input.release("p1_char_left")
                play_sfx('select')
            if r.get("p1_char_right"):
                p1_char_idx = (p1_char_idx + 1) % len(CHARACTER_TYPES)
                p1_weapon_idx = 0
                remote_input.release("p1_char_right")
                play_sfx('select')
            if r.get("p1_weapon_toggle"):
                ch = CHARACTER_TYPES[p1_char_idx]
                weapons = CHARACTER_WEAPONS[ch.name]
                p1_weapon_idx = (p1_weapon_idx + 1) % len(weapons)
                remote_input.release("p1_weapon_toggle")
                play_sfx('select')
            if r.get("p1_confirm"):
                p1_selected = True
                remote_input.release("p1_confirm")
                play_sfx('confirm')
        if not p2_selected and not ai_mode:
            if r.get("p2_char_left"):
                p2_char_idx = (p2_char_idx - 1) % len(CHARACTER_TYPES)
                p2_weapon_idx = 0
                remote_input.release("p2_char_left")
                play_sfx('select')
            if r.get("p2_char_right"):
                p2_char_idx = (p2_char_idx + 1) % len(CHARACTER_TYPES)
                p2_weapon_idx = 0
                remote_input.release("p2_char_right")
                play_sfx('select')
            if r.get("p2_weapon_toggle"):
                ch2 = CHARACTER_TYPES[p2_char_idx]
                weapons2 = CHARACTER_WEAPONS[ch2.name]
                p2_weapon_idx = (p2_weapon_idx + 1) % len(weapons2)
                remote_input.release("p2_weapon_toggle")
                play_sfx('select')
            if r.get("p2_confirm"):
                p2_selected = True
                remote_input.release("p2_confirm")
                play_sfx('confirm')
        if p1_selected and (p2_selected or ai_mode):
            play_sfx('confirm')
            start_game()

    # ── VERIFICAR INÍCIO DO FUTEBOL (via remoto) ──
    if current_state == STATE_QR_CODE and soccer_mode:
        if remote_input.get_game_state() == "start_game":
            start_game()

    # ─────────────────────────────────────────
    #  LÓGICA VS SCREEN
    # ─────────────────────────────────────────
    if current_state == STATE_VS_SCREEN:
        vs_timer -= 1
        if vs_timer <= 0:
            current_state = STATE_PLAYING
            play_battle_bgm()

    # ─────────────────────────────────────────
    #  LÓGICA DA ANIMAÇÃO DE MORTE
    # ─────────────────────────────────────────
    if current_state == STATE_DEATH_ANIM:
        death_timer -= 1
        loser = player1 if player1.hp <= 0 else player2
        if death_timer % 2 == 0:
            for _ in range(5):
                angle = random.uniform(0, math.pi * 2)
                speed = random.uniform(2, 7)
                death_particles.append({
                    'x': loser.x + random.uniform(-8, 8),
                    'y': loser.y + random.uniform(-8, 8),
                    'vx': math.cos(angle) * speed,
                    'vy': math.sin(angle) * speed,
                    'life': random.randint(15, 50),
                    'max_life': 50,
                    'color': loser.color,
                    'size': random.randint(2, 6),
                })
        for p in death_particles[:]:
            p['x'] += p['vx']
            p['y'] += p['vy']
            p['vx'] *= 0.96
            p['vy'] *= 0.96
            p['life'] -= 1
            if p['life'] <= 0:
                death_particles.remove(p)
        if death_timer <= 0:
            winner = death_winner_name
            current_state = STATE_GAME_OVER

    # ─────────────────────────────────────────
    #  LÓGICA DO JOGO
    # ─────────────────────────────────────────
    if current_state == STATE_PLAYING:
        keys = pygame.key.get_pressed()
        r = remote_input.get_state()

        if soccer_mode:
            # ── FUTEBOL: INPUT P1-P4 ──
            players_soccer = [player1, player2, player3, player4]
            for i, p in enumerate(players_soccer):
                if p is None:
                    continue
                prefix = f"p{i+1}"
                dx = (1 if r.get(f"{prefix}_right") else 0) - (1 if r.get(f"{prefix}_left") else 0)
                dy = (1 if r.get(f"{prefix}_down") else 0) - (1 if r.get(f"{prefix}_up") else 0)
                if i == 0:
                    dx += keys[pygame.K_d] - keys[pygame.K_a]
                    dy += keys[pygame.K_s] - keys[pygame.K_w]
                elif i == 1:
                    dx += keys[pygame.K_RIGHT] - keys[pygame.K_LEFT]
                    dy += keys[pygame.K_DOWN] - keys[pygame.K_UP]
                if dx != 0 or dy != 0:
                    p.move(dx, dy)
            # P3/P4: CPU se não houver controle remoto
            if player3 and not r.get("p3_up") and not r.get("p3_down") and not r.get("p3_left") and not r.get("p3_right"):
                update_soccer_ai(player3, ball, [player1], [player2, player4], walls)
            if player4 and not r.get("p4_up") and not r.get("p4_down") and not r.get("p4_left") and not r.get("p4_right"):
                update_soccer_ai(player4, ball, [player2], [player1, player3], walls)

            # ── FUTEBOL: CHUTE ──
            for i, p in enumerate(players_soccer):
                if p is None:
                    continue
                prefix = f"p{i+1}"
                wants_kick = r.get(f"{prefix}_attack", False)
                if i == 0 and keys[pygame.K_g]:
                    wants_kick = True
                if i == 1 and keys[pygame.K_SEMICOLON]:
                    wants_kick = True
                if wants_kick:
                    if ball and goal_timer <= 0:
                        # apontar para a bola se não estiver andando
                        if not (r.get(f"{prefix}_up") or r.get(f"{prefix}_down") or r.get(f"{prefix}_left") or r.get(f"{prefix}_right")):
                            bdx = ball.x - p.x
                            bdy = ball.y - p.y
                            bm = math.hypot(bdx, bdy)
                            if bm > 0:
                                p.last_direction = (bdx / bm, bdy / bm)
                        soccer_kick(p, ball)

                # ── FUTEBOL: PASSE ──
                wants_pass = r.get(f"{prefix}_special", False)
                if wants_pass and ball and goal_timer <= 0:
                    teammates = [player1, player3] if p.team == 0 else [player2, player4]
                    soccer_pass(p, ball, teammates, soccer_players)

                # ── FUTEBOL: CORTE (fingir chute / drible lateral) ──
                if r.get(f"{prefix}_corte", False) and p.dash_cooldown <= 0:
                    lx, ly = p.last_direction
                    if lx == 0 and ly == 0:
                        lx, ly = 1, 0
                    # lateral perpendicular
                    cx, cy = -ly, lx
                    p.dash_timer = 6
                    p.dash_cooldown = 30
                    p.dash_dir = (cx, cy)
                    p.dash_invulnerable = True
                    # gruda a bola no pé
                    if ball and goal_timer <= 0:
                        bdist = math.hypot(ball.x - p.x, ball.y - p.y)
                        if bdist < 30:
                            ball.vx += cx * DRIBBLE_SPRING * 4
                            ball.vy += cy * DRIBBLE_SPRING * 4

                # ── FUTEBOL: SUPER CHUTE ──
                if r.get(f"{prefix}_super", False) and p.super_cooldown <= 0 and ball and goal_timer <= 0:
                    bdist = math.hypot(ball.x - p.x, ball.y - p.y)
                    if bdist < p.radius + ball.radius + 20:
                        if p.team == 0:
                            gx, gy = 1580, 450
                        else:
                            gx, gy = 24, 450
                        dx, dy = gx - p.x, gy - p.y
                        m = math.hypot(dx, dy)
                        if m > 0:
                            p.last_direction = (dx / m, dy / m)
                        ball.vx = p.last_direction[0] * SUPER_SHOT_POWER
                        ball.vy = p.last_direction[1] * SUPER_SHOT_POWER
                        ball.homing_timer = SUPER_HOMING_DURATION
                        ball.homing_target = (gx, gy)
                        ball.homing_target_player = None
                        ball.homing_force = SUPER_HOMING_FORCE
                        p.super_cooldown = SUPER_SHOT_COOLDOWN
                        play_sfx('shoot', vol=0.7)

            # ── FUTEBOL: ATUALIZAR DASH ──
            for dp in [player1, player2, player3, player4]:
                if dp is None: continue
                if dp.dash_timer > 0:
                    dp.dash_timer -= 1
                    dp.x += dp.dash_dir[0] * dp.speed * 5
                    dp.y += dp.dash_dir[1] * dp.speed * 5
                    dp.x = max(dp.radius, min(WORLD_WIDTH - dp.radius, dp.x))
                    dp.y = max(dp.radius, min(WORLD_HEIGHT - dp.radius, dp.y))
                    if dp.dash_timer <= 0:
                        dp.dash_invulnerable = False
                if dp.dash_cooldown > 0:
                    dp.dash_cooldown -= 1
                if dp.super_cooldown > 0:
                    dp.super_cooldown -= 1
            # sincronizar cooldowns com o servidor web
            for pi, dp2 in enumerate([player1, player2, player3, player4]):
                if dp2:
                    remote_input.set_super_cooldown(pi + 1, dp2.super_cooldown)

            # ── FUTEBOL: ATUALIZAR BOLA ──
            if ball and goal_timer <= 0:
                ball.update()
                # colisão bola-parede (iterativa, com normal)
                for _ in range(3):
                    any_col = False
                    for wall in walls:
                        cx = max(wall.rect.left, min(ball.x, wall.rect.right))
                        cy = max(wall.rect.top, min(ball.y, wall.rect.bottom))
                        dx = ball.x - cx
                        dy = ball.y - cy
                        d2 = dx*dx + dy*dy
                        # CASO 1: centro dentro da parede
                        if d2 < 0.0001:
                            # empurra pela borda mais próxima
                            to_left   = ball.x + ball.radius - wall.rect.left
                            to_right  = wall.rect.right  - ball.x + ball.radius
                            to_top    = ball.y + ball.radius - wall.rect.top
                            to_bottom = wall.rect.bottom - ball.y + ball.radius
                            min_p = min(to_left, to_right, to_top, to_bottom)
                            if min_p == to_left:
                                ball.x = wall.rect.left - ball.radius
                                if ball.vx < 0: ball.vx = -ball.vx * 0.75
                            elif min_p == to_right:
                                ball.x = wall.rect.right + ball.radius
                                if ball.vx > 0: ball.vx = -ball.vx * 0.75
                            elif min_p == to_top:
                                ball.y = wall.rect.top - ball.radius
                                if ball.vy < 0: ball.vy = -ball.vy * 0.75
                            else:
                                ball.y = wall.rect.bottom + ball.radius
                                if ball.vy > 0: ball.vy = -ball.vy * 0.75
                            any_col = True
                            continue
                        # CASO 2: centro fora, raio tocando
                        dist = math.sqrt(d2)
                        if dist >= ball.radius:
                            continue
                        overlap = ball.radius - dist
                        nx = dx / dist
                        ny = dy / dist
                        ball.x += nx * (overlap + 0.1)
                        ball.y += ny * (overlap + 0.1)
                        dot = ball.vx * nx + ball.vy * ny
                        if dot < 0:
                            ball.vx -= 2 * dot * nx
                            ball.vy -= 2 * dot * ny
                            ball.vx *= 0.75
                            ball.vy *= 0.75
                        any_col = True
                    if not any_col:
                        break
                # colisão bola-jogador
                all_players = [p for p in [player1, player2, player3, player4] if p]
                for idx, p in enumerate(all_players):
                    bdx = ball.x - p.x
                    bdy = ball.y - p.y
                    bdist = math.hypot(bdx, bdy)
                    mindist = ball.radius + p.radius
                    if bdist < mindist and bdist > 0:
                        overlap = mindist - bdist
                        nx = bdx / bdist
                        ny = bdy / bdist
                        ball.x += nx * overlap
                        ball.y += ny * overlap
                        ball.vx += nx * 1.5
                        ball.vy += ny * 1.5
                    # condução (mola)
                    if bdist < DRIBBLE_RADIUS:
                        prefix = f"p{idx+1}"
                        conducao = r.get(f"{prefix}_conducao", False)
                        if conducao:
                            lx, ly = p.last_direction
                            if lx == 0 and ly == 0:
                                tx, ty = p.x, p.y
                            else:
                                tx = p.x + lx * (p.radius + ball.radius + 2)
                                ty = p.y + ly * (p.radius + ball.radius + 2)
                            ball.vx += (tx - ball.x) * DRIBBLE_SPRING * 3
                            ball.vy += (ty - ball.y) * DRIBBLE_SPRING * 3
                            ball.vx *= 0.94
                            ball.vy *= 0.94
                        else:
                            away = (ball.vx * (ball.x - p.x) + ball.vy * (ball.y - p.y)) / bdist
                            if away < 4.0:
                                lx, ly = p.last_direction
                                if lx == 0 and ly == 0:
                                    tx, ty = p.x, p.y
                                else:
                                    tx = p.x + lx * (p.radius + ball.radius + DRIBBLE_TARGET_OFFSET)
                                    ty = p.y + ly * (p.radius + ball.radius + DRIBBLE_TARGET_OFFSET)
                                ball.vx += (tx - ball.x) * DRIBBLE_SPRING
                                ball.vy += (ty - ball.y) * DRIBBLE_SPRING
                # colisão jogador-jogador
                for i in range(len(all_players)):
                    for j in range(i + 1, len(all_players)):
                        resolve_player_collision(all_players[i], all_players[j])
                # anti-travamento: bola presa entre jogadores
                ball_spd = math.hypot(ball.vx, ball.vy)
                if ball_spd < 0.8:
                    close = [p for p in all_players if math.hypot(p.x - ball.x, p.y - ball.y) < ball.radius + p.radius + 5]
                    if len(close) >= 2:
                        cx = sum(p.x for p in close) / len(close)
                        cy = sum(p.y for p in close) / len(close)
                        dx = ball.x - cx
                        dy = ball.y - cy
                        dm = math.hypot(dx, dy)
                        if dm > 0:
                            ball.vx += (dx / dm) * 1.2
                            ball.vy += (dy / dm) * 1.2
                # detecção de gol
                goal_side = check_goal(ball)
                if goal_side == 'right':
                    score_p1 += 1
                    goal_scorer = "TIME AZUL"
                    goal_timer = GOAL_FREEZE
                    play_sfx('victory', vol=0.5)
                elif goal_side == 'left':
                    score_p2 += 1
                    goal_scorer = "TIME VERMELHO"
                    goal_timer = GOAL_FREEZE
                    play_sfx('victory', vol=0.5)
                # bola fora do mundo
                if ball.x < -100 or ball.x > WORLD_WIDTH + 100 or ball.y < -100 or ball.y > WORLD_HEIGHT + 100:
                    ball.reset(WORLD_WIDTH // 2, WORLD_HEIGHT // 2)

            # ── FUTEBOL: GOAL TIMER ──
            if goal_timer > 0:
                goal_timer -= 1
                if goal_timer <= 0:
                    # reposicionar todos
                    ball.reset(WORLD_WIDTH // 2, WORLD_HEIGHT // 2)
                    if player1: player1.x, player1.y = 300, 350
                    if player2: player2.x, player2.y = 1300, 350
                    if player3: player3.x, player3.y = 300, 550
                    if player4: player4.x, player4.y = 1300, 550

            # ── FUTEBOL: FIM DE JOGO ──
            if score_p1 >= WIN_SCORE or score_p2 >= WIN_SCORE:
                death_winner_name = "TIME AZUL" if score_p1 >= WIN_SCORE else "TIME VERMELHO"
                death_timer = DEATH_ANIM_DURATION
                death_particles = []
                current_state = STATE_DEATH_ANIM
                stop_bgm(2000)
                play_sfx('victory', vol=0.5)

        else:
            # ── BATALHA NORMAL ──
            p1_dx = keys[player1.controls['right']] - keys[player1.controls['left']]
            p1_dx += (1 if r.get("p1_right") else 0) - (1 if r.get("p1_left") else 0)
            p1_dy = keys[player1.controls['down']]  - keys[player1.controls['up']]
            p1_dy += (1 if r.get("p1_down") else 0) - (1 if r.get("p1_up") else 0)
            player1.move(p1_dx, p1_dy)

            if ai_mode:
                player2.update_ai(player1, walls, difficulty)
            else:
                p2_dx = keys[player2.controls['right']] - keys[player2.controls['left']]
                p2_dx += (1 if r.get("p2_right") else 0) - (1 if r.get("p2_left") else 0)
                p2_dy = keys[player2.controls['down']]  - keys[player2.controls['up']]
                p2_dy += (1 if r.get("p2_down") else 0) - (1 if r.get("p2_up") else 0)
                player2.move(p2_dx, p2_dy)

        # ── Dash (duplo toque) P1 ──
        for dir_name, key in [('up', pygame.K_w), ('down', pygame.K_s),
                               ('left', pygame.K_a), ('right', pygame.K_d)]:
            held = keys[key]
            if held and not player1._dash_held[dir_name]:
                now = pygame.time.get_ticks()
                last = player1.last_key_time[dir_name]
                if now - last < player1.dash_window and player1.dash_cooldown <= 0:
                    dirmap = {'up': (0, -1), 'down': (0, 1), 'left': (-1, 0), 'right': (1, 0)}
                    player1.dash_timer = 12
                    player1.dash_cooldown = 45
                    player1.dash_dir = dirmap[dir_name]
                    player1.dash_invulnerable = True
                    play_sfx('dash', vol=0.3)
                player1.last_key_time[dir_name] = now
            player1._dash_held[dir_name] = held
        if r.get("p1_up") or r.get("p1_down") or r.get("p1_left") or r.get("p1_right"):
            for dir_name in ['up', 'down', 'left', 'right']:
                held = r.get("p1_" + dir_name, False)
                if held and not player1._dash_held.get('web_' + dir_name):
                    now = pygame.time.get_ticks()
                    last = player1.last_key_time.get('web_' + dir_name, 0)
                    if now - last < player1.dash_window and player1.dash_cooldown <= 0:
                        dirmap = {'up': (0, -1), 'down': (0, 1), 'left': (-1, 0), 'right': (1, 0)}
                        player1.dash_timer = 12
                        player1.dash_cooldown = 45
                        player1.dash_dir = dirmap[dir_name]
                        player1.dash_invulnerable = True
                        play_sfx('dash', vol=0.3)
                    player1.last_key_time['web_' + dir_name] = now
                player1._dash_held['web_' + dir_name] = held

        # ── Dash (duplo toque) P2 ──
        if not ai_mode:
            for dir_name, key in [('up', pygame.K_UP), ('down', pygame.K_DOWN),
                                   ('left', pygame.K_LEFT), ('right', pygame.K_RIGHT)]:
                held = keys[key]
                if held and not player2._dash_held[dir_name]:
                    now = pygame.time.get_ticks()
                    last = player2.last_key_time[dir_name]
                    if now - last < player2.dash_window and player2.dash_cooldown <= 0:
                        dirmap = {'up': (0, -1), 'down': (0, 1), 'left': (-1, 0), 'right': (1, 0)}
                        player2.dash_timer = 12
                        player2.dash_cooldown = 45
                        player2.dash_dir = dirmap[dir_name]
                        player2.dash_invulnerable = True
                        play_sfx('dash', vol=0.3)
                    player2.last_key_time[dir_name] = now
                player2._dash_held[dir_name] = held

        if not ai_mode:
            if r.get("p2_up") or r.get("p2_down") or r.get("p2_left") or r.get("p2_right"):
                for dir_name in ['up', 'down', 'left', 'right']:
                    held = r.get("p2_" + dir_name, False)
                    if held and not player2._dash_held.get('web_' + dir_name):
                        now = pygame.time.get_ticks()
                        last = player2.last_key_time.get('web_' + dir_name, 0)
                        if now - last < player2.dash_window and player2.dash_cooldown <= 0:
                            dirmap = {'up': (0, -1), 'down': (0, 1), 'left': (-1, 0), 'right': (1, 0)}
                            player2.dash_timer = 12
                            player2.dash_cooldown = 45
                            player2.dash_dir = dirmap[dir_name]
                            player2.dash_invulnerable = True
                            play_sfx('dash', vol=0.3)
                        player2.last_key_time['web_' + dir_name] = now
                    player2._dash_held['web_' + dir_name] = held

        # ── Esquiva via web (botão dedicado) P1 ──
        if not soccer_mode:
            dodge_now = r.get("p1_dodge", False)
            if dodge_now and not player1._web_dodge_held and player1.dash_cooldown <= 0:
                dx, dy = player1.last_direction
                if dx == 0 and dy == 0:
                    dy = 1
                player1.dash_timer = 12
                player1.dash_cooldown = 45
                player1.dash_dir = (dx, dy)
                player1.dash_invulnerable = True
                play_sfx('dash', vol=0.3)
            player1._web_dodge_held = dodge_now

        if not ai_mode and not soccer_mode:
            dodge2_now = r.get("p2_dodge", False)
            if not hasattr(player2, '_web_dodge_held'):
                player2._web_dodge_held = False
            if dodge2_now and not player2._web_dodge_held and player2.dash_cooldown <= 0:
                dx, dy = player2.last_direction
                if dx == 0 and dy == 0:
                    dy = 1
                player2.dash_timer = 12
                player2.dash_cooldown = 45
                player2.dash_dir = (dx, dy)
                player2.dash_invulnerable = True
                play_sfx('dash', vol=0.3)
            player2._web_dodge_held = dodge2_now

        if not soccer_mode:
            p1_wants_shoot = keys[player1.controls['shoot']] or r.get("p1_attack")
            if p1_wants_shoot:
                dx = player2.x - player1.x
                dy = player2.y - player1.y
                mag = math.hypot(dx, dy)
                if mag > 0:
                    player1.last_direction = (dx / mag, dy / mag)
                player1.shoot(player2)

            p2_wants_shoot = not ai_mode and (keys[player2.controls['shoot']] or r.get("p2_attack"))
            if p2_wants_shoot:
                dx = player1.x - player2.x
                dy = player1.y - player2.y
                mag = math.hypot(dx, dy)
                if mag > 0:
                    player2.last_direction = (dx / mag, dy / mag)
                player2.shoot(player1)
            player1.update(walls, enemy=player2)
            player2.update(walls, enemy=player1)

            # Colisão bala → jogador (iteração reversa)
            i = 0
            while i < len(player1.bullets):
                bullet = player1.bullets[i]
                if (bullet.x - player2.x)**2 + (bullet.y - player2.y)**2 < (bullet.radius + player2.radius)**2:
                    player2.take_damage(bullet.damage, bullet.x, bullet.y)
                    if bullet.explosive:
                        player1.explosions.append(Explosion(bullet.x, bullet.y, damage=bullet.damage, owner=player1))
                        play_sfx('explosion', vol=0.5)
                    else:
                        play_sfx('hit', vol=0.4)
                    player1.bullets.pop(i)
                else:
                    i += 1

            i = 0
            while i < len(player2.bullets):
                bullet = player2.bullets[i]
                if (bullet.x - player1.x)**2 + (bullet.y - player1.y)**2 < (bullet.radius + player1.radius)**2:
                    player1.take_damage(bullet.damage, bullet.x, bullet.y)
                    if bullet.explosive:
                        player2.explosions.append(Explosion(bullet.x, bullet.y, damage=bullet.damage, owner=player2))
                        play_sfx('explosion', vol=0.5)
                    else:
                        play_sfx('hit', vol=0.4)
                    player2.bullets.pop(i)
                else:
                    i += 1

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
                        target.take_damage(exp.damage, exp.x, exp.y)
                exp.damage_dealt = True

            # Fim de jogo → animação de morte
            if player1.hp <= 0:
                death_winner_name = player2.name
                death_timer = DEATH_ANIM_DURATION
                death_particles = []
                current_state = STATE_DEATH_ANIM
                stop_bgm(2000)
                play_sfx('victory' if (ai_mode and player2.name == "CPU") else 'gameover', vol=0.5)
            elif player2.hp <= 0:
                death_winner_name = player1.name
                death_timer = DEATH_ANIM_DURATION
                death_particles = []
                current_state = STATE_DEATH_ANIM
                stop_bgm(2000)
                play_sfx('victory', vol=0.5)

    # ─────────────────────────────────────────
    #  PODER ESPECIAL (tecla única por frame)
    # ─────────────────────────────────────────
    if current_state == STATE_PLAYING and not soccer_mode:
        keys = pygame.key.get_pressed()
        r = remote_input.get_state()
        if not hasattr(player1, '_f_held'):
            player1._f_held = False
        if not hasattr(player1, '_web_ability_held'):
            player1._web_ability_held = False
        if not hasattr(player1, '_web_dodge_held'):
            player1._web_dodge_held = False
        if not hasattr(player2, '_slash_held'):
            player2._slash_held = False
        if not hasattr(player2, '_web_ability_held'):
            player2._web_ability_held = False
        if not hasattr(player2, '_web_dodge_held'):
            player2._web_dodge_held = False

        f_now = keys[pygame.K_f]
        special_now = r.get("p1_special", False)
        if (f_now and not player1._f_held) or (special_now and not player1._web_ability_held):
            player1.use_ability(player2, walls)
        player1._f_held = f_now
        player1._web_ability_held = special_now

        if not ai_mode:
            slash_now = keys[pygame.K_SLASH]
            special2_now = r.get("p2_special", False)
            if not hasattr(player2, '_web_ability_held'):
                player2._web_ability_held = False
            if (slash_now and not player2._slash_held) or (special2_now and not player2._web_ability_held):
                player2.use_ability(player1, walls)
            player2._slash_held = slash_now
            player2._web_ability_held = special2_now

        # ── Trocar arma ──
        def _switch_weapon(p):
            ws = CHARACTER_WEAPONS[p.char_stats.name]
            if len(ws) < 2:
                return
            for i, w in enumerate(ws):
                if w.name == p.weapon_name:
                    nw = ws[(i + 1) % len(ws)]
                    p.weapon = nw
                    p.damage = nw.damage
                    p.bullet_speed = nw.bullet_speed if nw.weapon_type == "ranged" else 0
                    p.shoot_cooldown = nw.shoot_cooldown
                    p.weapon_name = nw.name
                    play_sfx('click')
                    break

        q_now = keys[pygame.K_q]
        sw_now = r.get("p1_switch_weapon", False)
        if not hasattr(player1, '_q_held'):
            player1._q_held = False
        if not hasattr(player1, '_web_switch_held'):
            player1._web_switch_held = False
        if (q_now and not player1._q_held) or (sw_now and not player1._web_switch_held):
            _switch_weapon(player1)
        player1._q_held = q_now
        player1._web_switch_held = sw_now

        if not ai_mode:
            u_now = keys[pygame.K_u]
            sw2_now = r.get("p2_switch_weapon", False)
            if not hasattr(player2, '_u_held'):
                player2._u_held = False
            if not hasattr(player2, '_web_switch_held2'):
                player2._web_switch_held2 = False
            if (u_now and not player2._u_held) or (sw2_now and not player2._web_switch_held2):
                _switch_weapon(player2)
            player2._u_held = u_now
            player2._web_switch_held2 = sw2_now

    if current_state in (STATE_PLAYING, STATE_DEATH_ANIM):
        all_players = [p for p in [player1, player2, player3, player4] if p]
        if all_players:
            cx = sum(p.x for p in all_players) / len(all_players)
            cy = sum(p.y for p in all_players) / len(all_players)
            target_cx = cx - SCREEN_WIDTH / 2
            target_cy = cy - SCREEN_HEIGHT / 2
            target_cx = max(0, min(WORLD_WIDTH - SCREEN_WIDTH, target_cx))
            target_cy = max(0, min(WORLD_HEIGHT - SCREEN_HEIGHT, target_cy))
            camera_x += (target_cx - camera_x) * 0.08
            camera_y += (target_cy - camera_y) * 0.08
            # zoom dinâmico para futebol
            if soccer_mode:
                min_x = min(p.x for p in all_players)
                max_x = max(p.x for p in all_players)
                min_y = min(p.y for p in all_players)
                max_y = max(p.y for p in all_players)
                spread_w = max_x - min_x + 120
                spread_h = max_y - min_y + 120
                target_zoom = min(1.0, min(SCREEN_WIDTH / spread_w, SCREEN_HEIGHT / spread_h))
                target_zoom = max(ZOOM_MIN, target_zoom)
                camera_zoom += (target_zoom - camera_zoom) * ZOOM_SMOOTH
        else:
            camera_x, camera_y = 0, 0
    elif current_state not in (STATE_GAME_OVER,):
        camera_x, camera_y = 0, 0

    # ── ZOOM: superfície maior ──
    _zoom_surf = None
    if soccer_mode and current_state in (STATE_PLAYING, STATE_DEATH_ANIM) and abs(camera_zoom - 1.0) > 0.01:
        _vw = max(SCREEN_WIDTH, int(SCREEN_WIDTH / camera_zoom))
        _vh = max(SCREEN_HEIGHT, int(SCREEN_HEIGHT / camera_zoom))
        _zoom_surf = pygame.Surface((_vw, _vh))
        _zoom_surf.fill((20, 120, 40))
        _real_screen = screen
        screen = _zoom_surf
        _old_cam_x, _old_cam_y = camera_x, camera_y
        camera_x = max(0, min(WORLD_WIDTH - _vw, camera_x - (_vw - SCREEN_WIDTH) / 2))
        camera_y = max(0, min(WORLD_HEIGHT - _vh, camera_y - (_vh - SCREEN_HEIGHT) / 2))

    # ─────────────────────────────────────────
    #  DESENHO
    # ─────────────────────────────────────────
    screen.blit(floor_surface, (-camera_x, -camera_y))

    # ── MENU PRINCIPAL ─────────────────────────
    if current_state == STATE_MAIN_MENU:
        screen.fill((10, 5, 20))
        t = pygame.time.get_ticks() * 0.001
        for p in particles:
            px = p['x'] + math.sin(t * 2 + p['phase']) * 30
            py = (p['y'] + t * 40) % SCREEN_HEIGHT
            alpha = max(0, min(255, int(80 + 105 * math.sin(t * 3 + p['phase']))))
            clr = (*p['color'][:3], alpha)
            surf = pygame.Surface((p['size'] * 2, p['size'] * 2), pygame.SRCALPHA)
            pygame.draw.circle(surf, clr, (p['size'], p['size']), p['size'])
            screen.blit(surf, (int(px - p['size']), int(py - p['size'])))

        glow = int(15 * math.sin(t * 2))
        for dy in (-1, 0, 1):
            draw_text(screen, "SOUL STRIKE", 66, (*UI_GOLD[:3], 30 + glow),
                      SCREEN_WIDTH // 2, 120 + dy * 3)
        draw_text(screen, "SOUL STRIKE", 66, WHITE, SCREEN_WIDTH // 2, 120)
        draw_text(screen, "Um duelo de heróis!", 22, UI_TEXT_DIM, SCREEN_WIDTH // 2, 165)

        jogar_rect = pygame.Rect(SCREEN_WIDTH // 2 - 120, 260, 240, 70)
        draw_panel(screen, (jogar_rect.x, jogar_rect.y, jogar_rect.w, jogar_rect.h),
                   fill=UI_PANEL, border=UI_GOLD, radius=10)
        draw_text(screen, "JOGAR", 36, WHITE, SCREEN_WIDTH // 2, jogar_rect.centery)

        # Botões inferiores
        mx, my = pygame.mouse.get_pos()
        btn_s = pygame.Rect(20, SCREEN_HEIGHT - 60, 40, 40)
        s_hover = btn_s.collidepoint(mx, my)
        draw_panel(screen, (btn_s.x, btn_s.y, btn_s.w, btn_s.h),
                   fill=UI_PANEL, border=UI_GOLD if s_hover else UI_BORDER, radius=8)
        draw_text(screen, "?", 22, UI_GOLD if s_hover else UI_BORDER_LIT, btn_s.centerx, btn_s.centery)

        btn_c = pygame.Rect(SCREEN_WIDTH - 60, SCREEN_HEIGHT - 60, 40, 40)
        c_hover = btn_c.collidepoint(mx, my)
        star_alpha = int(150 + 105 * math.sin(t * 2))
        star_color = UI_GOLD if c_hover else (*UI_GOLD[:3], star_alpha)
        draw_panel(screen, (btn_c.x, btn_c.y, btn_c.w, btn_c.h),
                   fill=UI_PANEL, border=UI_GOLD if c_hover else UI_BORDER, radius=8)
        draw_text(screen, "✦", 20, star_color, btn_c.centerx, btn_c.centery)

    # ── SOBRE ──────────────────────────────
    elif current_state == STATE_ABOUT:
        screen.fill((10, 5, 20))
        draw_text(screen, "4 PILARES DA POO NO SOUL STRIKE", 24, UI_GOLD, SCREEN_WIDTH // 2, 25)

        clip_rect = pygame.Rect(0, 55, SCREEN_WIDTH, SCREEN_HEIGHT - 105)
        screen.set_clip(clip_rect)
        y = 70 - about_scroll
        for group, color, size in about_lines:
            for line in group:
                if line and y + 20 > 55 and y < SCREEN_HEIGHT - 50:
                    draw_text(screen, line, size, color, SCREEN_WIDTH // 2, y)
                y += 22
        screen.set_clip(None)

        voltar_rect = pygame.Rect(SCREEN_WIDTH // 2 - 80, SCREEN_HEIGHT - 55, 160, 40)
        draw_panel(screen, (voltar_rect.x, voltar_rect.y, voltar_rect.w, voltar_rect.h),
                   fill=UI_PANEL, border=UI_BORDER, radius=8)
        draw_text(screen, "VOLTAR", 20, UI_TEXT, SCREEN_WIDTH // 2, voltar_rect.centery)

    # ── CRÉDITOS ──────────────────────────
    elif current_state == STATE_CREDITS:
        screen.fill((10, 5, 20))
        draw_text(screen, "CRÉDITOS", 28, UI_GOLD, SCREEN_WIDTH // 2, 40)
        mx, my = pygame.mouse.get_pos()
        for ci, dev in enumerate(CREDIT_BTNS):
            cy = 110 + ci * 90
            draw_text(screen, dev['name'], 20, WHITE, SCREEN_WIDTH // 2, cy)
            gh_x, li_x = SCREEN_WIDTH // 2 - 30, SCREEN_WIDTH // 2 + 8
            by = cy + 30
            gh_hover = pygame.Rect(gh_x, by, 24, 24).collidepoint(mx, my)
            li_hover = pygame.Rect(li_x, by, 24, 24).collidepoint(mx, my)
            gh_r2 = 13 if gh_hover else 11
            li_r2 = 13 if li_hover else 11
            gh_c = (80, 80, 80) if dev['github'] else (40, 40, 40)
            li_c = (20, 120, 210) if dev['linkedin'] else (40, 40, 40)
            gh_rect = pygame.Rect(gh_x, by, 24, 24)
            li_rect = pygame.Rect(li_x, by, 24, 24)
            draw_panel(screen, (gh_rect.x, gh_rect.y, gh_rect.w, gh_rect.h),
                       fill=UI_PANEL, border=UI_GOLD if gh_hover and dev['github'] else UI_BORDER, radius=12)
            draw_text(screen, "</>", 10, UI_GOLD if gh_hover and dev['github'] else UI_BORDER_LIT, gh_rect.centerx, gh_rect.centery)
            draw_panel(screen, (li_rect.x, li_rect.y, li_rect.w, li_rect.h),
                       fill=UI_PANEL, border=UI_GOLD if li_hover and dev['linkedin'] else UI_BORDER, radius=12)
            draw_text(screen, "in", 9, UI_GOLD if li_hover and dev['linkedin'] else UI_BORDER_LIT, li_rect.centerx, li_rect.centery)

        voltar_rect = pygame.Rect(SCREEN_WIDTH // 2 - 80, SCREEN_HEIGHT - 55, 160, 40)
        draw_panel(screen, (voltar_rect.x, voltar_rect.y, voltar_rect.w, voltar_rect.h),
                   fill=UI_PANEL, border=UI_BORDER, radius=8)
        draw_text(screen, "VOLTAR", 20, UI_TEXT, SCREEN_WIDTH // 2, voltar_rect.centery)

    # ── SELEÇÃO DE MODO ──────────────────────
    elif current_state == STATE_MODE_SELECT:
        screen.fill((10, 5, 20))
        t = pygame.time.get_ticks() * 0.001
        for p in particles:
            px = p['x'] + math.sin(t * 2 + p['phase']) * 30
            py = (p['y'] + t * 40) % SCREEN_HEIGHT
            alpha = max(0, min(255, int(80 + 105 * math.sin(t * 3 + p['phase']))))
            clr = (*p['color'][:3], alpha)
            surf = pygame.Surface((p['size'] * 2, p['size'] * 2), pygame.SRCALPHA)
            pygame.draw.circle(surf, clr, (p['size'], p['size']), p['size'])
            screen.blit(surf, (int(px - p['size']), int(py - p['size'])))

        draw_text(screen, "SOUL STRIKE", 44, UI_GOLD, SCREEN_WIDTH // 2, 70)
        draw_text(screen, "SELECIONE O MODO DE JOGO", 18, UI_TEXT_DIM, SCREEN_WIDTH // 2, 115)

        cw, ch = 200, 180
        gap = 16
        total_w = cw * 4 + gap * 3
        start_x = SCREEN_WIDTH // 2 - total_w // 2
        yy = SCREEN_HEIGHT // 2 - ch // 2 + 10
        mx, my = pygame.mouse.get_pos()

        for i, (label, sub, icon) in enumerate([
            ("1 JOGADOR", "vs CPU", "⚔"),
            ("2 JOGADORES", "Local", "👥"),
            ("FUTEBOL 2v2", "Times", "⚽"),
            ("FUTEBOL 1v1", "Duelo", "⚽"),
        ]):
            x = start_x + i * (cw + gap)
            hover = pygame.Rect(x, yy, cw, ch).collidepoint(mx, my)
            bcol = UI_GOLD if hover else UI_BORDER
            draw_panel(screen, (x, yy, cw, ch), fill=UI_PANEL, border=bcol, radius=12)
            draw_text(screen, label, 18, UI_TEXT if not hover else UI_GOLD, x + cw // 2, yy + 65)
            draw_text(screen, sub, 14, UI_TEXT_DIM, x + cw // 2, yy + 92)
            draw_text(screen, icon, 32, UI_GOLD, x + cw // 2, yy + 25)

        draw_text(screen, "[1] vs CPU   [2] 2 Jog   [3] Fut 2v2   [4] Fut 1v1   [ESC] Voltar",
                  13, UI_TEXT_DIM, SCREEN_WIDTH // 2, SCREEN_HEIGHT - 30)

    # ── QR CODE (2 JOGADORES / 4 FUTEBOL) ─────
    elif current_state == STATE_QR_CODE:
        screen.fill((10, 5, 20))
        t = pygame.time.get_ticks() * 0.001
        for p in particles:
            px = p['x'] + math.sin(t * 2 + p['phase']) * 30
            py = (p['y'] + t * 40) % SCREEN_HEIGHT
            alpha = max(0, min(255, int(80 + 105 * math.sin(t * 3 + p['phase']))))
            clr = (*p['color'][:3], alpha)
            surf = pygame.Surface((p['size'] * 2, p['size'] * 2), pygame.SRCALPHA)
            pygame.draw.circle(surf, clr, (p['size'], p['size']), p['size'])
            screen.blit(surf, (int(px - p['size']), int(py - p['size'])))

        draw_text(screen, "SOUL STRIKE", 44, UI_GOLD, SCREEN_WIDTH // 2, 50)

        if soccer_mode:
            draw_text(screen, "FUTEBOL 2v2 — CONTROLE REMOTO", 18, UI_TEXT_DIM, SCREEN_WIDTH // 2, 90)
        else:
            draw_text(screen, "CONTROLE REMOTO", 18, UI_TEXT_DIM, SCREEN_WIDTH // 2, 90)

        # Gerar QR codes (uma vez)
        if not hasattr(draw_text, '_qr_p1'):
            ip = get_local_ip()
            port = 5000
            url_p1 = f"http://{ip}:{port}/?player=1"
            url_p2 = f"http://{ip}:{port}/?player=2"
            url_p3 = f"http://{ip}:{port}/?player=3"
            url_p4 = f"http://{ip}:{port}/?player=4"
            qr_p1_img = qrcode.make(url_p1)
            qr_p2_img = qrcode.make(url_p2)
            qr_p3_img = qrcode.make(url_p3)
            qr_p4_img = qrcode.make(url_p4)
            qr_size = 180
            def _qr_to_surf(pil_img):
                mode = pil_img.mode
                size = pil_img.size[0]
                img = pil_img.convert("RGBA")
                raw = img.tobytes()
                surf = pygame.image.frombytes(raw, (size, size), "RGBA")
                return pygame.transform.scale(surf, (qr_size, qr_size))
            draw_text._qr_p1 = _qr_to_surf(qr_p1_img)
            draw_text._qr_p2 = _qr_to_surf(qr_p2_img)
            draw_text._qr_p3 = _qr_to_surf(qr_p3_img)
            draw_text._qr_p4 = _qr_to_surf(qr_p4_img)
            draw_text._url_p1 = url_p1
            draw_text._url_p2 = url_p2
            draw_text._url_p3 = url_p3
            draw_text._url_p4 = url_p4

        qr_size = 180
        panel_w = 260
        panel_h = 320
        gap = 40

        if soccer_mode:
            if soccer_players == 2:
                # 1v1: 2 QR codes lado a lado
                total_w = panel_w * 2 + gap
                start_x = (SCREEN_WIDTH - total_w) // 2
                yy = SCREEN_HEIGHT // 2 - panel_h // 2 + 20
                for i, (qr_surf, label, url, color) in enumerate([
                    (draw_text._qr_p1, "Jogador 1", draw_text._url_p1, BLUE),
                    (draw_text._qr_p2, "Jogador 2", draw_text._url_p2, RED),
                ]):
                    px = start_x + i * (panel_w + gap)
                    draw_panel(screen, (px, yy, panel_w, panel_h), fill=UI_PANEL, border=color, radius=10)
                    draw_text(screen, label, 20, color, px + panel_w // 2, yy + 20)
                    qr_x = px + (panel_w - qr_size) // 2
                    qr_y = yy + 40
                    screen.blit(qr_surf, (qr_x, qr_y))
                    draw_text(screen, url, 10, UI_TEXT_DIM, px + panel_w // 2, qr_y + qr_size + 12, center=True)
            else:
                # 2v2: 4 QR codes em 2x2
                grid_cols = 2
                grid_gap = 20
                total_grid_w = panel_w * grid_cols + grid_gap
                grid_start_x = (SCREEN_WIDTH - total_grid_w) // 2
                grid_start_y = SCREEN_HEIGHT // 2 - panel_h - grid_gap // 2
                qr_data = [
                    (draw_text._qr_p1, "Jogador 1 (Azul)", draw_text._url_p1, BLUE),
                    (draw_text._qr_p2, "Jogador 2 (Vermelho)", draw_text._url_p2, RED),
                    (draw_text._qr_p3, "Jogador 3 (Azul)", draw_text._url_p3, CYAN),
                    (draw_text._qr_p4, "Jogador 4 (Vermelho)", draw_text._url_p4, ORANGE),
                ]
                for idx, (qr_surf, label, url, color) in enumerate(qr_data):
                    col = idx % grid_cols
                    row = idx // grid_cols
                    px = grid_start_x + col * (panel_w + grid_gap)
                    py = grid_start_y + row * (panel_h + grid_gap)
                    draw_panel(screen, (px, py, panel_w, panel_h), fill=UI_PANEL, border=color, radius=10)
                    draw_text(screen, label, 18, color, px + panel_w // 2, py + 12)
                    qr_x = px + (panel_w - qr_size) // 2
                    qr_y = py + 32
                    screen.blit(qr_surf, (qr_x, qr_y))
                    draw_text(screen, url, 9, UI_TEXT_DIM, px + panel_w // 2, qr_y + qr_size + 10, center=True)
        else:
            total_w = panel_w * 2 + gap
            start_x = (SCREEN_WIDTH - total_w) // 2
            yy = SCREEN_HEIGHT // 2 - panel_h // 2 + 20

            for i, (qr_surf, label, url, color) in enumerate([
                (draw_text._qr_p1, "Jogador 1", draw_text._url_p1, BLUE),
                (draw_text._qr_p2, "Jogador 2", draw_text._url_p2, RED),
            ]):
                px = start_x + i * (panel_w + gap)
                draw_panel(screen, (px, yy, panel_w, panel_h), fill=UI_PANEL, border=UI_GOLD, radius=10)
                draw_text(screen, label, 20, color, px + panel_w // 2, yy + 20)
                qr_x = px + (panel_w - qr_size) // 2
                qr_y = yy + 40
                screen.blit(qr_surf, (qr_x, qr_y))
                draw_text(screen, url, 10, UI_TEXT_DIM, px + panel_w // 2, qr_y + qr_size + 12, center=True)

        mx, my = pygame.mouse.get_pos()

        if soccer_mode:
            # Status dos jogadores + botão INICIAR
            claimed = remote_input.get_claimed()
            ready_count = sum(1 for p in claimed if remote_input.is_player_ready(p))
            status_text = f"Jogadores conectados: {len(claimed)}/4  —  Prontos: {ready_count}/{len(claimed) if claimed else 0}"
            draw_text(screen, status_text, 16, UI_GOLD if ready_count == len(claimed) and len(claimed) >= 2 else UI_TEXT,
                      SCREEN_WIDTH // 2, SCREEN_HEIGHT - 175)

            iniciar_rect = pygame.Rect(SCREEN_WIDTH // 2 - 100, SCREEN_HEIGHT - 130, 200, 44)
            i_hover = iniciar_rect.collidepoint(mx, my)
            can_start = len(claimed) >= 2
            draw_panel(screen, (iniciar_rect.x, iniciar_rect.y, iniciar_rect.w, iniciar_rect.h),
                       fill=UI_PANEL, border=GREEN if can_start and i_hover else (UI_GOLD if i_hover else UI_BORDER), radius=8)
            draw_text(screen, "INICIAR PARTIDA", 16, GREEN if can_start else (UI_GOLD if i_hover else UI_TEXT),
                      iniciar_rect.centerx, iniciar_rect.centery)

            draw_text(screen, "Escaneie o QR Code no celular e confirme o personagem",
                      14, UI_TEXT, SCREEN_WIDTH // 2, SCREEN_HEIGHT - 85)
            draw_text(screen, "(certifique-se de estar na mesma rede Wi-Fi)",
                      12, UI_TEXT_DIM, SCREEN_WIDTH // 2, SCREEN_HEIGHT - 65)
            draw_text(screen, "[Enter] Iniciar     [Esc] Voltar",
                      12, UI_TEXT_DIM, SCREEN_WIDTH // 2, SCREEN_HEIGHT - 15)
        else:
            draw_text(screen, "Escaneie o QR Code no celular para controlar o jogador",
                      14, UI_TEXT, SCREEN_WIDTH // 2, SCREEN_HEIGHT - 125)
            draw_text(screen, "(certifique-se de estar na mesma rede Wi-Fi)",
                      12, UI_TEXT_DIM, SCREEN_WIDTH // 2, SCREEN_HEIGHT - 105)

            btn_rect = pygame.Rect(SCREEN_WIDTH // 2 - 100, SCREEN_HEIGHT - 65, 200, 44)
            mx, my = pygame.mouse.get_pos()
            hover = btn_rect.collidepoint(mx, my)
            draw_panel(screen, (btn_rect.x, btn_rect.y, btn_rect.w, btn_rect.h),
                       fill=UI_PANEL, border=UI_GOLD if hover else UI_BORDER, radius=8)
            draw_text(screen, "CONTINUAR", 18, UI_GOLD if hover else UI_TEXT,
                      btn_rect.centerx, btn_rect.centery)
            draw_text(screen, "[Enter] Continuar     [Esc] Voltar",
                      12, UI_TEXT_DIM, SCREEN_WIDTH // 2, SCREEN_HEIGHT - 15)

    # ── SELEÇÃO DE PERSONAGEM ─────────────────
    elif current_state == STATE_CHAR_SELECT:
        draw_text(screen, "SOUL STRIKE", 40, UI_GOLD, SCREEN_WIDTH // 2, 24)
        subtitle = "1 JOGADOR — ESCOLHA SEU LUTADOR" if ai_mode else "2 JOGADORES — ESCOLHAM SEUS LUTADORES"
        draw_text(screen, subtitle, 16, UI_TEXT_DIM, SCREEN_WIDTH // 2, 52)

        mx, my = pygame.mouse.get_pos()
        card_w, card_h = 280, 340

        for i, (px, col, idx, selected, pname, wp_idx) in enumerate([
            (190, BLUE, p1_char_idx, p1_selected, p1_name or "Jogador 1", p1_weapon_idx),
            (770, RED, p2_char_idx,
             p2_selected if not ai_mode else True,
             p2_name or "CPU" if ai_mode else (p2_name or "Jogador 2"),
             p2_weapon_idx if not ai_mode else 0),
        ]):
            ch = CHARACTER_TYPES[idx]
            card_x = px - card_w // 2
            card_y = 85
            weapons = CHARACTER_WEAPONS[ch.name]
            wp = weapons[wp_idx]

            border_col = GREEN if selected else UI_BORDER_LIT
            draw_panel(screen, (card_x, card_y, card_w, card_h), fill=UI_PANEL, border=border_col, radius=10)

            # Nome do jogador
            draw_text(screen, pname.upper(), 14, col, px, card_y + 12)

            # ── Linha do personagem com setas ──
            ch_name_y = card_y + 32
            can_change = i == 0 and not p1_selected or i == 1 and not p2_selected and not ai_mode
            clr_name = UI_GOLD if selected else WHITE
            if can_change:
                draw_text(screen, "◄", 20, UI_GOLD, card_x + 18, ch_name_y)
                draw_text(screen, "►", 20, UI_GOLD, card_x + card_w - 18, ch_name_y)
            draw_text(screen, ch.name, 22, clr_name, px, ch_name_y)

            sp_y = ch_name_y + 28
            char_img = character_images.get(ch.image_name)
            if char_img:
                frames = char_img.get("frente")
                if frames:
                    rect = frames[0].get_rect(center=(px, sp_y + 50))
                    screen.blit(frames[0], rect)

            # ── Armas ──
            arm_y = sp_y + 110
            draw_text(screen, "─── ARMAS ───", 11, UI_BORDER, px, arm_y)

            for wi, wdata in enumerate(weapons):
                wy = arm_y + 16 + wi * 22
                active = (wi == wp_idx)
                bullet = "●" if active else "○"
                clr_wp = UI_GOLD if active else UI_BORDER_LIT
                draw_text(screen, f"{bullet} {wdata.name}", 14, clr_wp, card_x + 18, wy)
                if wdata.weapon_type == "ranged":
                    draw_text(screen, f"dano:{wdata.damage}", 11, UI_TEXT_DIM, card_x + card_w - 45, wy)
                else:
                    draw_text(screen, f"dano:{wdata.damage}", 11, UI_TEXT_DIM, card_x + card_w - 45, wy)

            # ── HP ──
            hp_y = arm_y + 60
            hp_w = card_w - 32
            hp_x = card_x + 16
            ratio = ch.max_hp / 250.0
            draw_styled_bar(screen, hp_x, hp_y, hp_w, 8, ratio, fg_color=RED, label="HP")
            draw_text(screen, f"{ch.max_hp}", 12, RED, px, hp_y + 12)

            # ── Habilidade ──
            ab_y = hp_y + 26
            draw_text(screen, f"⚡ {ch.ability_name}", 12, UI_GOLD, px, ab_y)

            # ── Separador ──
            sep_y = ab_y + 18
            draw_text(screen, "────────────────", 8, UI_BORDER, px, sep_y)

            # ── Status ──
            st_y = sep_y + 16
            if selected:
                draw_text(screen, "CONFIRMADO", 14, GREEN, px, st_y)
            else:
                equip_name = wp.name
                draw_text(screen, f"\u25b6 {equip_name} equipada", 12, UI_BORDER_LIT, px, st_y)

            # ── Controles ──
            ctrl_y = st_y + 16
            if not selected:
                prefix = "[A/D] Pers  [W/S] Arma" if i == 0 else "[←/→] Pers  [↑/↓] Arma"
                draw_text(screen, prefix, 10, UI_TEXT_DIM, px, ctrl_y)
                draw_text(screen, "[G] OK" if i == 0 else "[M] OK", 10, UI_TEXT_DIM, px, ctrl_y + 12)
            elif not (p1_selected and (p2_selected or ai_mode)):
                draw_text(screen, "Aguardando outro jogador...", 10, UI_TEXT_DIM, px, ctrl_y)

        # ── Seletor de mapa ──
        panel_w = 220
        panel_h = 40
        px = SCREEN_WIDTH // 2 - panel_w // 2
        py = SCREEN_HEIGHT - 52
        draw_panel(screen, (px, py, panel_w, panel_h),
                   fill=(18, 16, 30), border=UI_BORDER, radius=6)
        mlx = px + 8
        mrx = px + panel_w - 38
        myy = py + 5
        for side, sx in [("<", mlx), (">", mrx)]:
            b = pygame.Rect(sx, myy, 30, 30)
            bh = b.collidepoint(mx, my)
            draw_panel(screen, (sx, myy, 30, 30),
                       fill=UI_PANEL, border=UI_GOLD if bh else (60, 55, 80), radius=4)
            draw_text(screen, side, 14, UI_GOLD if bh else UI_BORDER_LIT, sx + 15, myy + 8)
        draw_text(screen, f"MAPA: {MAPS[current_map]['name']}", 12, UI_TEXT,
                  SCREEN_WIDTH // 2, py + 12)

        if p1_selected and (p2_selected or ai_mode):
            draw_text(screen, "PREPARANDO BATALHA...", 18, UI_GOLD,
                      SCREEN_WIDTH // 2, SCREEN_HEIGHT - 16)

    # ── TELA VS ──────────────────────────────
    elif current_state == STATE_VS_SCREEN:
        t = vs_timer
        progress = 1.0 - (t / VS_DURATION)

        # Fundo escuro
        screen.fill((10, 5, 20))

        if soccer_mode:
            if not hasattr(draw_text, '_arena_vs'):
                try:
                    arena_path = os.path.join(TILES_DIR, "campo_futebol", "arena completa.png")
                    arena_img = pygame.image.load(arena_path).convert()
                    draw_text._arena_vs = pygame.transform.scale(arena_img, (SCREEN_WIDTH, SCREEN_HEIGHT))
                except Exception:
                    draw_text._arena_vs = None
            if draw_text._arena_vs:
                screen.blit(draw_text._arena_vs, (0, 0))
                overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
                overlay.fill((0, 0, 0, 140))
                screen.blit(overlay, (0, 0))

        # Partículas laterais (chamas)
        for i in range(20):
            px = SCREEN_WIDTH // 2 + int(300 * math.sin(i * 1.7 + t * 0.05))
            py = SCREEN_HEIGHT // 2 + int(100 * math.cos(i * 2.3 + t * 0.03))
            size = 3 + int(4 * math.sin(i + t * 0.1))
            alpha = int(100 + 155 * (0.5 + 0.5 * math.sin(i + t * 0.05)))
            surf = pygame.Surface((size * 2, size * 2), pygame.SRCALPHA)
            pygame.draw.circle(surf, (*ORANGE[:3], alpha), (size, size), size)
            screen.blit(surf, (int(px), int(py)))

        if soccer_mode:
            if soccer_players == 2:
                # 1v1: mostra P1 vs P2 como batalha normal
                for idx, (player, side) in enumerate([(player1, -1), (player2, 1)]):
                    char_img = character_images.get(player.char_stats.image_name)
                    if char_img:
                        frames = char_img.get("frente")
                        if not frames:
                            continue
                        base = frames[0]
                        scale = 2.0 + 0.2 * math.sin(t * 0.05)
                        scaled = pygame.transform.scale(base, (int(120 * scale), int(120 * scale)))
                        px = SCREEN_WIDTH // 2 + side * 200
                        py = SCREEN_HEIGHT // 2 - 20
                        rect = scaled.get_rect(center=(px, py))
                        screen.blit(scaled, rect)
                draw_text(screen, player1.name, 26, player1.color,
                          SCREEN_WIDTH // 4, SCREEN_HEIGHT // 2 + 80)
                draw_text(screen, player2.name, 26, player2.color,
                          SCREEN_WIDTH * 3 // 4, SCREEN_HEIGHT // 2 + 80)
            else:
                # 2v2: mostra 4 jogadores em times
                team_blue = [p for p in [player1, player3] if p]
                team_red  = [p for p in [player2, player4] if p]
                for side, team, color in [(-1, team_blue, TEAM_BLUE_OVERLAY), (1, team_red, TEAM_RED_OVERLAY)]:
                    for ii, p in enumerate(team):
                        char_img = character_images.get(p.char_stats.image_name)
                        if char_img:
                            frames = char_img.get("frente")
                            if not frames:
                                continue
                            base = frames[0]
                            scale = 1.6 + 0.15 * math.sin(t * 0.05)
                            scaled = pygame.transform.scale(base, (int(100 * scale), int(100 * scale)))
                            px = SCREEN_WIDTH // 2 + side * 200
                            py = SCREEN_HEIGHT // 2 - 40 + ii * 70
                            rect = scaled.get_rect(center=(px, py))
                            screen.blit(scaled, rect)
                            draw_text(screen, p.name, 16, UI_TEXT_DIM, px, py + 60)
                draw_text(screen, "TIME AZUL", 28, TEAM_BLUE_OVERLAY[:3], SCREEN_WIDTH // 4, SCREEN_HEIGHT // 2 - 100)
                draw_text(screen, "TIME VERMELHO", 28, TEAM_RED_OVERLAY[:3], SCREEN_WIDTH * 3 // 4, SCREEN_HEIGHT // 2 - 100)
        else:
            for idx, (player, side) in enumerate([(player1, -1), (player2, 1)]):
                char_img = character_images.get(player.char_stats.image_name)
                if char_img:
                    frames = char_img.get("frente")
                    if not frames:
                        continue
                    base = frames[0]
                    scale = 2.0 + 0.2 * math.sin(t * 0.05)
                    scaled = pygame.transform.scale(base, (int(120 * scale), int(120 * scale)))
                    px = SCREEN_WIDTH // 2 + side * 200
                    py = SCREEN_HEIGHT // 2 - 20
                    rect = scaled.get_rect(center=(px, py))
                    screen.blit(scaled, rect)

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

        # FIGHT! / PARTIDA!
        fight_alpha = 0
        if progress > 0.5:
            fight_progress = (progress - 0.5) / 0.3
            fight_alpha = int(255 * min(1, fight_progress * 2) * (1 - max(0, fight_progress - 0.5) * 2))
        if fight_alpha > 0:
            fight_surf = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            font = pygame.font.Font(None, 100)
            label = "PARTIDA!" if soccer_mode else "FIGHT!"
            txt = font.render(label, True, (*YELLOW[:3], fight_alpha))
            tr = txt.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 60))
            fight_surf.blit(txt, tr)
            screen.blit(fight_surf, (0, 0))

    # ── JOGO ──────────────────────────────────
    elif current_state == STATE_PLAYING:
        for wall in walls:
            wall.draw(screen)

        if not soccer_mode:
            if player1.barrier:
                player1.barrier.draw(screen)
            if player2.barrier:
                player2.barrier.draw(screen)

        if soccer_mode:
            # desenhar gols
            for g in goals:
                g.draw()
            # desenhar bola
            if ball:
                ball.draw()

        # desenhar jogadores
        all_draw_players = [p for p in [player1, player2, player3, player4] if p]
        if soccer_mode:
            for p in all_draw_players:
                p.draw(screen)
        else:
            player1.draw(screen, enemy=player2)
            player2.draw(screen, enemy=player1)

        if not soccer_mode:
            for b in player1.bullets + player2.bullets:
                b.draw(screen)

        # ── RESTAURAR ZOOM (antes do HUD) ──
        if _zoom_surf is not None:
            scaled = pygame.transform.scale(screen, (SCREEN_WIDTH, SCREEN_HEIGHT))
            screen = _real_screen
            camera_x, camera_y = _old_cam_x, _old_cam_y
            screen.blit(scaled, (0, 0))
            _zoom_surf = None

        if soccer_mode:
            draw_soccer_hud(screen)
        else:
            draw_hud(screen, player1, player2)

        # overlay de GOL!
        if soccer_mode and goal_timer > 0:
            gol_alpha = min(255, int(255 * (goal_timer / GOAL_FREEZE) * 1.5))
            gol_surf = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            gol_surf.fill((0, 0, 0, gol_alpha // 2))
            screen.blit(gol_surf, (0, 0))
            draw_text(screen, "GOL!", 100, UI_GOLD, SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 40)
            draw_text(screen, goal_scorer, 40, WHITE, SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 40)

    # ── ANIMAÇÃO DE MORTE ──────────────────────
    elif current_state == STATE_DEATH_ANIM:
        for wall in walls:
            wall.draw(screen)

        if not soccer_mode:
            if player1.barrier:
                player1.barrier.draw(screen)
            if player2.barrier:
                player2.barrier.draw(screen)

        progress = 1.0 - (death_timer / DEATH_ANIM_DURATION)

        if soccer_mode:
            all_death_players = [p for p in [player1, player2, player3, player4] if p]
            for p in all_death_players:
                p.draw(screen)
        else:
            for p, is_loser in [(player1, player1.hp <= 0), (player2, player2.hp <= 0)]:
                if is_loser:
                    char_img = character_images.get(p.char_stats.image_name)
                    if char_img:
                        scale = max(0.2, 1.0 - progress * 0.8)
                        frames = char_img.get("frente")
                        if not frames:
                            continue
                        scaled = pygame.transform.scale(frames[0], (int(120 * scale), int(120 * scale)))
                        rect = scaled.get_rect(center=(int(p.x - camera_x), int(p.y - camera_y)))
                        flash_alpha = int(120 + 80 * math.sin(death_timer * 0.4))
                        flash = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
                        flash.fill((*RED[:3], flash_alpha))
                        screen.blit(scaled, rect)
                        screen.blit(flash, rect)
                    else:
                        flash_alpha = int(120 + 80 * math.sin(death_timer * 0.4))
                        scale = max(0.2, 1.0 - progress * 0.8)
                        r = int(p.radius * scale)
                        surf = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
                        pygame.draw.circle(surf, (*RED[:3], flash_alpha), (r, r), r)
                        screen.blit(surf, (int(p.x - camera_x - r), int(p.y - camera_y - r)))
                else:
                    p.draw(screen, enemy=(player2 if p is player1 else player1))

        if not soccer_mode:
            for b in player1.bullets + player2.bullets:
                b.draw(screen)

        for p in death_particles:
            alpha = int(255 * (p['life'] / p['max_life']))
            sz = p['size']
            surf = pygame.Surface((sz * 2, sz * 2), pygame.SRCALPHA)
            pygame.draw.circle(surf, (*p['color'][:3], alpha), (sz, sz), sz)
            screen.blit(surf, (int(p['x'] - camera_x - sz), int(p['y'] - camera_y - sz)))

        # ── RESTAURAR ZOOM (antes do overlay/HUD) ──
        if _zoom_surf is not None:
            scaled = pygame.transform.scale(screen, (SCREEN_WIDTH, SCREEN_HEIGHT))
            screen = _real_screen
            camera_x, camera_y = _old_cam_x, _old_cam_y
            screen.blit(scaled, (0, 0))
            _zoom_surf = None

        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, int(180 * progress)))
        screen.blit(overlay, (0, 0))

        if soccer_mode:
            draw_soccer_hud(screen)
        else:
            draw_hud(screen, player1, player2)

    # ── GAME OVER ─────────────────────────────
    elif current_state == STATE_GAME_OVER:
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        screen.blit(overlay, (0, 0))
        if soccer_mode:
            wcolor = TEAM_BLUE_OVERLAY if "AZUL" in (winner or "") else TEAM_RED_OVERLAY
            draw_panel(screen, (SCREEN_WIDTH // 2 - 220, SCREEN_HEIGHT // 2 - 100, 440, 200),
                       fill=UI_PANEL, border=UI_GOLD, radius=12)
            draw_text(screen, f"{winner} VENCEU!", 44, UI_GOLD, SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 50)
            draw_text(screen, f"🔵 {score_p1}  🆚  {score_p2} 🔴", 36, WHITE, SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 10)
            draw_text(screen, "Pressione R para reiniciar", 20, UI_TEXT_DIM,
                      SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 65)
        else:
            draw_panel(screen, (SCREEN_WIDTH // 2 - 200, SCREEN_HEIGHT // 2 - 90, 400, 180),
                       fill=UI_PANEL, border=UI_GOLD, radius=12)
            draw_text(screen, "FIM DE JOGO!", 52, WHITE, SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 55)
            draw_text(screen, f"{winner} VENCEU!", 44, UI_GOLD, SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 10)
            draw_text(screen, "Pressione R para reiniciar", 20, UI_TEXT_DIM,
                      SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 65)

    pygame.display.flip()
    clock.tick(FPS)

pygame.quit()