"""Geometria do basquete: trajetória do arremesso, aro, tabela e cesta.

Funções puras (sem pygame), fáceis de testar. A bola de basquete não perde velocidade no ar,
então as contas são exatas: só a gravidade puxa para baixo.
"""
import math

from .soccer_assist import unit


def flight_frames(dist):
    """Quadros no ar de um arremesso de tão longe (mais longe = mais alto e mais demorado)."""
    return round(34 + dist / 16)


def shot_velocity(x, y, z, tx, ty, tz, frames, gravity):
    """Velocidade de saída para a bola ir de (x, y, z) a (tx, ty, tz) em `frames` quadros.

    A conta segue a ordem do jogo: a cada quadro a gravidade sai do vz e depois a bola anda."""
    vx = (tx - x) / frames
    vy = (ty - y) / frames
    # z depois de n quadros = z + n*vz - g*n*(n+1)/2
    vz = (tz - z + gravity * frames * (frames + 1) / 2) / frames
    return vx, vy, vz


def rim_contact(bx, by, bz, hx, hy, hz, rim_r, ball_r):
    """A bola encosta no aro (um anel de raio rim_r na altura hz)? Devolve a normal (nx, ny, nz) e
    quanto ela entrou, ou None. A normal aponta do ponto do aro mais perto para a bola."""
    dx, dy = bx - hx, by - hy
    d = math.hypot(dx, dy)
    if d < 1e-6:
        ux, uy = 1.0, 0.0
    else:
        ux, uy = dx / d, dy / d
    px, py, pz = hx + ux * rim_r, hy + uy * rim_r, hz       # ponto do aro mais perto da bola
    nx, ny, nz = bx - px, by - py, bz - pz
    dist = math.sqrt(nx * nx + ny * ny + nz * nz)
    if dist >= ball_r or dist < 1e-6:
        return None
    return (nx / dist, ny / dist, nz / dist), ball_r - dist


def bounce(v, normal, keep):
    """Rebate a velocidade (vx, vy, vz) numa superfície com essa normal, guardando `keep` da força."""
    vx, vy, vz = v
    nx, ny, nz = normal
    dot = vx * nx + vy * ny + vz * nz
    if dot >= 0:
        return v                            # já está saindo
    return ((vx - 2 * dot * nx) * keep, (vy - 2 * dot * ny) * keep, (vz - 2 * dot * nz) * keep)


def through_hoop(z0, z1, bx, by, hx, hy, hz, rim_r, ball_r):
    """A bola desceu pelo meio do aro neste quadro (de z0 para z1)? Isso é cesta."""
    if not (z0 >= hz > z1):
        return False
    return math.hypot(bx - hx, by - hy) < rim_r - ball_r * 0.25


def board_hit(x0, x1, dy, bz, board_x, side, half, z_range, ball_r):
    """A bola bateu na tabela neste quadro (indo de x0 para x1)? A tabela é um plano em x = board_x,
    voltado para a quadra (side 0: a quadra fica à direita). dy = distância do meio da tabela."""
    lo, hi = z_range
    if not (lo - ball_r < bz < hi + ball_r) or abs(dy) > half + ball_r:
        return False
    face = board_x + ball_r if side == 0 else board_x - ball_r
    if side == 0:
        return x0 >= face > x1
    return x0 <= face < x1


def aim_point(hx, hy, toward_x, toward_y, miss, side_sign):
    """Para onde mirar: o centro do aro (miss=0) ou a borda dele (miss>0), para errar no aro.

    side_sign escolhe o lado da borda (-1 ou 1), na direção de quem arremessa ou para o lado."""
    if miss <= 0:
        return hx, hy
    ux, uy = unit(toward_x - hx, toward_y - hy)
    # borda da frente/de trás (bate e volta) ou de lado (gira no aro)
    px, py = -uy, ux
    ax = ux * 0.6 + px * 0.8 * side_sign
    ay = uy * 0.6 + py * 0.8 * side_sign
    ax, ay = unit(ax, ay)
    return hx + ax * miss, hy + ay * miss


# ── barrinha do arremesso ────────────────────
JUMP_FRAMES = 40                # duração do pulo do arremesso; o topo é na metade
FIRE_HALF = 0.45                # pegando fogo: faixa verde quase inteira


def green_half(dist, three, on_fire=False):
    """Meia largura da faixa verde (a barra vai de 0 a 1 e o centro, 0.5, é o topo do pulo).

    Meia distância: cerca de 60% da barra. De 3: cerca de 15%. Muito longe (do meio da quadra
    para trás) a faixa vai encolhendo até um quarto disso."""
    if on_fire:
        return FIRE_HALF
    half = 0.075 if three else 0.30
    if dist > 700:
        half *= max(0.25, 1 - (dist - 700) / 500)
    return half


def shot_error(timing, half):
    """Quanto a soltada passou da faixa verde (0 = dentro, cesta)."""
    return max(0.0, abs(timing - 0.5) - half)


def miss_distance(err, rim_r):
    """Erro na barrinha vira distância do alvo ao centro do aro: perto da faixa a bola bate no
    aro (e às vezes ainda cai), longe dela a bola passa direto."""
    if err <= 0:
        return 0.0
    return rim_r + 3 + min(26.0, err * 90)


# ── roubo ────────────────────────────────────
def steal_chance(facing, rel_x, rel_y, protecting=False):
    """Chance do roubo de quem está em (rel_x, rel_y) em relação a quem tem a bola.

    Pela frente é difícil, de lado é bom e por trás é quase certo. Contra quem protege a bola
    (de costas para o marcador) quase não pega."""
    if protecting:
        return 0.05
    ux, uy = unit(rel_x, rel_y)
    dot = facing[0] * ux + facing[1] * uy
    if dot > 0.4:
        return 0.25
    if dot < -0.4:
        return 0.7
    return 0.55
