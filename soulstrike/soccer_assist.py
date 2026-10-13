"""Geometria do futebol: colisão contínua, trajetória da bola e assistências de mira.

Funções puras (sem pygame), fáceis de testar.
"""
import math
from dataclasses import dataclass


@dataclass(frozen=True)
class AssistLevel:
    label: str
    pass_cone: float      # graus: companheiro dentro desse ângulo da direção apontada recebe o passe
    shot_cone: float      # graus: chute que sairia para fora é corrigido para o gol dentro desse ângulo
    trap_pull: float      # força com que a bola que chega perto é puxada para o pé
    trap_range: float     # px além do alcance normal em que o puxão age
    trap_bonus: float     # bola um pouco mais rápida ainda pode ser dominada


ASSIST_LEVELS = {
    "alta": AssistLevel("ALTA", 60, 30, 0.45, 26, 2.0),
    "media": AssistLevel("MÉDIA", 45, 18, 0.25, 18, 1.0),
    "desligada": AssistLevel("DESLIGADA", 0, 0, 0.0, 0, 0.0),
}
ASSIST_ORDER = ("alta", "media", "desligada")


def unit(dx, dy):
    m = math.hypot(dx, dy)
    if m < 1e-9:
        return 0.0, 0.0
    return dx / m, dy / m


def segment_contact(x0, y0, x1, y1, cx, cy, r):
    """Primeiro instante t (0..1) em que um ponto indo de (x0, y0) a (x1, y1) chega
    a menos de r de (cx, cy). None se não chega. 0 se já começou encostado.

    Serve para a bola rápida não atravessar o corpo de um jogador entre dois quadros.
    """
    dx, dy = x1 - x0, y1 - y0
    fx, fy = x0 - cx, y0 - cy
    c = fx * fx + fy * fy - r * r
    if c <= 0:
        return 0.0
    a = dx * dx + dy * dy
    if a < 1e-9:
        return None
    b = 2 * (fx * dx + fy * dy)
    disc = b * b - 4 * a * c
    if disc < 0:
        return None
    t = (-b - math.sqrt(disc)) / (2 * a)
    return t if 0.0 <= t <= 1.0 else None


def closest_approach(bx, by, vx, vy, px, py, horizon):
    """Daqui a quantos quadros (até `horizon`) a bola passa mais perto de (px, py), e a que distância.
    Ignora o atrito: para poucos quadros a diferença é pequena."""
    v2 = vx * vx + vy * vy
    if v2 < 1e-6:
        return 0.0, math.hypot(bx - px, by - py)
    t = -((bx - px) * vx + (by - py) * vy) / v2
    t = max(0.0, min(float(horizon), t))
    return t, math.hypot(bx + vx * t - px, by + vy * t - py)


def blend(a, b, weight):
    """Direção entre a e b: weight=0 → a, weight=1 → b."""
    return unit(a[0] + (b[0] - a[0]) * weight, a[1] + (b[1] - a[1]) * weight)


def angle_between(a, b):
    """Ângulo (graus) entre duas direções unitárias."""
    dot = max(-1.0, min(1.0, a[0] * b[0] + a[1] * b[1]))
    return math.degrees(math.acos(dot))


SHOT_ASSIST_RANGE = 700     # chute de mais longe que isso não é corrigido


def shot_assist(bx, by, direction, goal_x, goal_top, goal_bottom, cone, margin=18):
    """Corrige um chute que sairia para fora para dentro do gol (se o erro for pequeno e o
    chute for de perto). Chute que já vai no gol fica como está."""
    dx, dy = direction
    if cone <= 0 or abs(dx) < 1e-6 or (goal_x - bx) * dx <= 0 or abs(goal_x - bx) > SHOT_ASSIST_RANGE:
        return direction
    t = (goal_x - bx) / dx
    cross = by + dy * t
    lo, hi = goal_top + margin, goal_bottom - margin
    if lo <= cross <= hi:
        return direction
    want = unit(goal_x - bx, min(hi, max(lo, cross)) - by)
    return want if angle_between(direction, want) <= cone else direction


def pick_receiver(px, py, direction, mates, cone):
    """Companheiro que está na direção apontada (o mais alinhado; perto desempata). None se ninguém."""
    best, best_score = None, 1e9
    for m in mates:
        vx, vy = m.x - m.prev_pos[0], m.y - m.prev_pos[1]
        tx, ty = m.x + vx * 12, m.y + vy * 12           # onde ele vai estar
        to = unit(tx - px, ty - py)
        ang = angle_between(direction, to)
        if ang <= cone:
            score = ang + math.hypot(tx - px, ty - py) * 0.02
            if score < best_score:
                best, best_score = m, score
    return best
