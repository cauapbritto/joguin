"""Mansão do Carimbo (capítulo 4 da campanha): os monstros, os efeitos e os perigos das salas.

A lasca do caco foi parar no servidor do CPD e virou a IARA, a inteligência artificial que o
Cauanzera criou para "otimizar" o órgão. Agora todo objeto de repartição ganhou vida. Como no resto
da campanha, todo golpe tem um aviso antes e um jeito claro de escapar:

- Processo Ambulante: anda atrás do herói e, quando cai, se desmonta em dois Apensos (menores).
- Carimbo Indeferidor: o retângulo INDEFERIDO aparece no chão, ele pula e carimba; depois fica
  um tempo com o cabo preso no chão (leva mais dano).
- Impressora Possuída: cospe folhas em leque; depois de 3 rajadas ATOLA O PAPEL (leva mais dano).
- Garrafa Térmica: mantém distância e joga café quente: o círculo marrom avisa onde cai e fica
  uma poça que queima quem pisa.
- Tuiuiú-Drone: voa em roda e dá rasante em linha reta (a linha laranja aparece no chão antes).
- Ponto Eletrônico: o visor pisca e ele marca FALTA num herói: por 5 s esse herói leva mais dano.
- Pop-up da IARA: some e reaparece perto do herói; se terminar de carregar, abre o "ACEITAR
  COOKIES?" em cima dele (tapa a visão). Bater nele enquanto carrega fecha a janela.
- Projetor de Slides: projeta um gráfico de pizza no chão em volta do herói; as fatias que
  piscam queimam (é só ficar numa fatia apagada ou sair do círculo).
- Arquivo de Aço (elite): investe em linha (a linha aparece no chão) e no fim as gavetas abrem:
  fica GAVETAS ABERTAS levando o dobro de dano.

Perigos das salas (entram em hazards.HAZARDS):

- fila (Fila do Atendimento): quando a senha é chamada, as faixas de fila andam e arrastam quem
  estiver em cima na direção da seta (as setas piscam antes; é só sair da faixa).
- pilha (Arquivo Geral): pilhas de processo caem do alto da estante; a sombra no chão avisa.
- calor (Pátio a 47°C): no sol o calor sobe; na sombra dos toldos baixa. Com o termômetro cheio,
  INSOLAÇÃO: fica lento e perde vida até voltar para a sombra.
- energia (Subsolo do CPD): caiu a energia; só se enxerga em volta de cada herói. Três no-breaks
  nas paredes: ATACAR perto liga cada um (a luz volta aos poucos).
- reuniao (Sala de Reunião do Comitê): de tempos em tempos entra PAUTA NOVA e a mesa puxa todo
  mundo para o meio da sala (o aviso aparece antes; dá para andar contra).
"""
import math
import random

import pygame

from . import config, theme
from .data import WeaponStats
from .entities import Entity, Particle, hostile

IARA = (60, 230, 255)
IARA_D = (20, 130, 170)
IARA_L = (200, 250, 255)
MANILA = (222, 196, 132)
INK_RED = (210, 50, 60)
COFFEE = (120, 74, 40)
COFFEE_L = (196, 140, 86)
SUN = (255, 186, 60)
TUIUIU = (255, 140, 60)
FALTA_FRAMES = 5 * config.FPS
FALTA_MULT = 1.3
COOKIE_FRAMES = round(1.6 * config.FPS)


def _w(name, kind, damage, speed=0, cooldown=16, reach=0, style=""):
    return WeaponStats(name, kind, damage, bullet_speed=speed, cooldown=cooldown, reach=reach, style=style)


def creature_stats():
    """As criaturas da mansão (entram em enemies.CREATURES)."""
    from .enemies import EnemyStats
    return {
        "processo": EnemyStats(
            "processo", "Processo Ambulante", 40, 2.4, MANILA, "", "",
            (_w("Grampo de Pasta", "melee", 7, cooldown=40, reach=28),), "processo",
            radius=13, drop_chance=0.10),
        "apenso": EnemyStats(
            "apenso", "Apenso", 14, 3.4, MANILA, "", "",
            (_w("Folhinha", "melee", 4, cooldown=36, reach=22),), "apenso",
            radius=9, drop_chance=0.04),
        "carimbador": EnemyStats(
            "carimbador", "Carimbo Indeferidor", 46, 2.2, INK_RED, "", "",
            (_w("Cabo do Carimbo", "melee", 8, cooldown=44, reach=30),), "carimbador",
            radius=14, drop_chance=0.12),
        "impressora": EnemyStats(
            "impressora", "Impressora Possuída", 48, 2.0, (210, 212, 218), "", "",
            (_w("Folha A4", "ranged", 5, speed=7.5, cooldown=6, style="boleto"),), "impressora",
            radius=15, drop_chance=0.14),
        "garrafa_termica": EnemyStats(
            "garrafa_termica", "Garrafa Térmica", 38, 2.3, COFFEE_L, "", "",
            (_w("Tampinha", "melee", 5, cooldown=40, reach=24),), "garrafa_termica",
            radius=12, drop_chance=0.12),
        "tuiuiu_drone": EnemyStats(
            "tuiuiu_drone", "Tuiuiú-Drone", 30, 3.4, TUIUIU, "", "",
            (_w("Bico", "melee", 6, cooldown=40, reach=26),), "tuiuiu_drone",
            radius=13, drop_chance=0.10),
        "ponto_eletronico": EnemyStats(
            "ponto_eletronico", "Ponto Eletrônico", 44, 2.0, (120, 230, 140), "", "",
            (_w("Choque do Leitor", "melee", 6, cooldown=44, reach=26),), "ponto_eletronico",
            radius=13, drop_chance=0.14),
        "popup_iara": EnemyStats(
            "popup_iara", "Pop-up da IARA", 34, 2.8, IARA, "", "",
            (_w("Clique", "melee", 6, cooldown=36, reach=28),), "popup_iara",
            radius=12, drop_chance=0.12),
        "projetor": EnemyStats(
            "projetor", "Projetor de Slides", 60, 1.6, (230, 230, 210), "", "",
            (_w("Feixe", "melee", 6, cooldown=50, reach=24),), "projetor",
            radius=15, drop_chance=0.16),
        "iara_nucleo": EnemyStats(
            "iara_nucleo", "IARA", 720, 0.0, IARA, "", "",
            (_w("Tentáculo", "melee", 0, cooldown=60, reach=10),), "iara",
            radius=30, elite=True, knock_resist=1.0, drop_chance=0.0),
        "arquivo_aco": EnemyStats(
            "arquivo_aco", "Arquivo de Aço", 250, 2.0, (150, 160, 176), "", "",
            (_w("Gaveta", "melee", 14, cooldown=60, reach=44),), "arquivo_aco",
            radius=20, elite=True, knock_resist=0.85, drop_chance=0.6),
    }


BIG = ("arquivo_aco", "iara_nucleo")
IARA_CABLE_ARMOR = 0.1        # IARA com cabo inteiro: quase nada passa
IARA_EXPOSED = 1.3            # sem os 4 cabos: leva mais dano


# ─────────────────────────────────────────────
#  Efeitos
# ─────────────────────────────────────────────
class CoffeeSplash(Entity):
    """Café da Garrafa Térmica: o círculo marrom pisca no chão e, no fim, o café cai. Quem estava
    em cima se queima, e fica uma poça quente que machuca de pouquinho quem pisa."""

    flat = True
    LIFE = 4 * config.FPS

    def __init__(self, owner, x, y, frames, damage, radius=46):
        super().__init__(x, y)
        self.owner = owner
        self.frames = self.left = max(1, frames)
        self.damage = damage
        self.radius = radius
        self.age = 0

    def _inside(self, f):
        return math.hypot(f.x - self.x, (f.y - self.y) * 2) < self.radius + f.radius * 0.5

    def update(self, match):
        if self.left > 0:
            self.left -= 1
            if self.left == 0:
                for f in match.fighters:
                    if hostile(self.owner, f) and f.alive_in_match and f.lift <= 0 and self._inside(f):
                        f.take_damage(self.damage, self.x, self.y, attacker=self.owner, match=match)
                match.burst(self.x, self.y, COFFEE_L, 14, speed=4)
                match.assets.play("gosma", 0.35)
            return
        self.age += 1
        if self.age >= self.LIFE:
            self.alive = False
            return
        if self.age % 30 == 0:
            for f in match.fighters:
                if hostile(self.owner, f) and f.alive_in_match and f.lift <= 0 and self._inside(f):
                    f.take_damage(max(1, self.damage // 4), self.x, self.y, match=match)
                    f.knock = [0.0, 0.0]
        if self.age % 12 == 0:
            match.particles.append(Particle(self.x + random.uniform(-20, 20), self.y, 0, -0.6,
                                            (236, 226, 214), 22, 3))

    def draw(self, surf, camera):
        r = self.radius
        cx, cy = round(self.x - camera.x), round(self.y - camera.y + 12)
        layer = pygame.Surface((r * 2, r), pygame.SRCALPHA)
        if self.left > 0:
            t = 1 - self.left / self.frames
            on = (self.left // 4) % 2 == 0 or t > 0.7
            pygame.draw.ellipse(layer, (*COFFEE, round(40 + 80 * t)), layer.get_rect())
            pygame.draw.ellipse(layer, (*(COFFEE_L if on else COFFEE), 230), layer.get_rect(), 3)
            surf.blit(layer, (cx - r, cy - r // 2))
            # a gota caindo
            drop = round((1 - t) * 90)
            pygame.draw.circle(surf, COFFEE, (cx, cy - drop - 6), 5)
            return
        fade = min(1.0, (self.LIFE - self.age) / 40)
        pygame.draw.ellipse(layer, (*COFFEE, round(170 * fade)), layer.get_rect())
        pygame.draw.ellipse(layer, (*COFFEE_L, round(200 * fade)), (r // 2, r // 4, r, r // 3))
        surf.blit(layer, (cx - r, cy - r // 2))


class FaltaMark(Entity):
    """FALTA do Ponto Eletrônico: por 5 s o herói marcado leva mais dano (a plaquinha vermelha
    fica em cima dele)."""

    def __init__(self, target, frames=FALTA_FRAMES):
        super().__init__(target.x, target.y)
        self.target = target
        self.left = frames
        target.vulnerability = max(target.vulnerability, FALTA_MULT)

    def update(self, match):
        self.left -= 1
        self.x, self.y = self.target.x, self.target.y
        if self.left <= 0 or not self.target.alive_in_match:
            self.target.vulnerability = 1.0
            self.target.falta = None
            self.alive = False

    def draw(self, surf, camera):
        if (self.left // 8) % 4 == 0 and self.left < 60:
            return
        cx, cy = round(self.x - camera.x), round(self.y - camera.y - 74)
        tag = _label("FALTA", INK_RED)
        box = tag.get_rect(center=(cx, cy)).inflate(10, 4)
        surf.fill((250, 246, 236), box)
        pygame.draw.rect(surf, INK_RED, box, 2)
        surf.blit(tag, tag.get_rect(center=(cx, cy)))


class PieChart(Entity):
    """Gráfico de pizza do Projetor: o círculo dividido em 6 fatias aparece no chão. As fatias
    que vão queimar piscam; no fim queimam quem estiver em cima delas."""

    flat = True
    SLICES = 6
    BURN = 18

    def __init__(self, owner, x, y, frames, damage, radius=150, lit=None):
        super().__init__(x, y)
        self.owner = owner
        self.frames = self.left = max(1, frames)
        self.damage = damage
        self.radius = radius
        self.lit = set(lit) if lit is not None else set(random.sample(range(self.SLICES), 3))
        self.after = self.BURN
        self.offset = random.uniform(0, math.tau)

    def slice_of(self, x, y):
        a = (math.atan2((y - self.y) * 2, x - self.x) - self.offset) % math.tau
        return int(a // (math.tau / self.SLICES))

    def covers(self, f):
        if math.hypot(f.x - self.x, (f.y - self.y) * 2) > self.radius:
            return False
        return self.slice_of(f.x, f.y) in self.lit

    def update(self, match):
        if self.left > 0:
            self.left -= 1
            if self.left == 0:
                for f in match.fighters:
                    if hostile(self.owner, f) and f.alive_in_match and f.lift <= 0 and self.covers(f):
                        f.take_damage(self.damage, self.x, self.y, attacker=self.owner, match=match)
                match.assets.play("laser", 0.3)
            return
        self.after -= 1
        if self.after <= 0:
            self.alive = False

    def draw(self, surf, camera):
        r = self.radius
        cx, cy = self.x - camera.x, self.y - camera.y + 12
        layer = pygame.Surface((r * 2 + 4, r + 4), pygame.SRCALPHA)
        burning = self.left == 0
        t = 1 - self.left / self.frames
        on = burning or (self.left // 4) % 2 == 0 or t > 0.7
        colors = ((255, 120, 80), (255, 200, 70), (110, 200, 255), (160, 230, 120), (230, 130, 230), (250, 250, 250))
        step = math.tau / self.SLICES
        for k in range(self.SLICES):
            a0, a1 = self.offset + k * step, self.offset + (k + 1) * step
            pts = [(r + 2, r // 2 + 2)]
            for j in range(9):
                a = a0 + (a1 - a0) * j / 8
                pts.append((r + 2 + math.cos(a) * r, r // 2 + 2 + math.sin(a) * r / 2))
            if k in self.lit:
                alpha = 200 if burning else round(40 + 90 * t) if on else 30
                color = (255, 250, 230) if burning else colors[k]
            else:
                alpha, color = 26, colors[k]
            pygame.draw.polygon(layer, (*color, alpha), pts)
            pygame.draw.polygon(layer, (40, 40, 50, 120), pts, 1)
        pygame.draw.ellipse(layer, (250, 250, 240, 200), (2, 2, r * 2, r), 2)
        surf.blit(layer, (round(cx - r - 2), round(cy - r // 2 - 2)))


class TentacleBeam(Entity):
    """Tentáculo de cabo da IARA: a linha ciano aparece no chão (aviso) e depois o choque corre
    por ela, machucando quem estiver em cima."""

    flat = True
    BURN = 14
    HALF = 16

    def __init__(self, owner, x, y, dx, dy, length, frames, damage):
        super().__init__(x, y)
        self.owner = owner
        self.dx, self.dy = dx, dy
        self.length = length
        self.frames = self.left = max(1, frames)
        self.damage = damage
        self.burn = self.BURN
        self.hit = set()

    def touches(self, f):
        px, py = f.x - self.x, f.y - self.y
        t = px * self.dx + py * self.dy
        return 0 < t < self.length and abs(px * self.dy - py * self.dx) < self.HALF + f.radius * 0.5

    def update(self, match):
        if self.left > 0:
            self.left -= 1
            if self.left == 0:
                match.assets.play("eletrico", 0.35)
            return
        self.burn -= 1
        for f in match.fighters:
            if f in self.hit or not hostile(self.owner, f) or not f.alive_in_match or f.lift > 0 or not self.touches(f):
                continue
            self.hit.add(f)
            if f.take_damage(self.damage, f.x, f.y, attacker=self.owner, match=match):
                match.burst(f.x, f.y - 10, IARA, 6, speed=3)
        if self.burn <= 0:
            self.alive = False

    def draw(self, surf, camera):
        x0, y0 = self.x - camera.x, self.y - camera.y
        x1, y1 = x0 + self.dx * self.length, y0 + self.dy * self.length
        if self.left > 0:
            t = 1 - self.left / self.frames
            on = (self.left // 4) % 2 == 0 or t > 0.7
            pygame.draw.line(surf, IARA if on else IARA_D, (x0, y0), (x1, y1), 2 + round(4 * t))
            return
        nx, ny = -self.dy, self.dx
        pts = []
        for k in range(13):
            t = k / 12
            wob = math.sin(t * 14 + self.burn) * 6
            pts.append((x0 + (x1 - x0) * t + nx * wob, y0 + (y1 - y0) * t + ny * wob))
        pygame.draw.lines(surf, IARA_D, False, pts, 12)
        pygame.draw.lines(surf, IARA_L, False, pts, 4)


class CookieNotice:
    """A janela do Pop-up da IARA em cima de um herói: "ACEITAR COOKIES?" (tapa a visão por 1,6 s)."""

    def __init__(self, target, frames=COOKIE_FRAMES):
        self.target = target
        self.frames = self.left = frames

    @property
    def alive(self):
        return self.left > 0

    def update(self):
        self.left -= 1

    def draw(self, screen, cam, ui):
        sx, sy = cam.to_screen(self.target.x, self.target.y - 30)
        grow = min(1.0, (self.frames - self.left) / 6)
        fade = min(1.0, self.left / 10)
        w, h = round(320 * grow), round(150 * grow)
        if w < 10:
            return
        box = pygame.Rect(0, 0, w, h)
        box.center = (round(sx), round(sy))
        layer = pygame.Surface((w, h), pygame.SRCALPHA)
        a = round(248 * fade)
        layer.fill((236, 248, 252, a))
        layer.fill((*IARA_D, a), (0, 0, w, 26))
        pygame.draw.rect(layer, (*IARA, a), (0, 0, w, h), 3)
        screen.blit(layer, box.topleft)
        if grow < 1:
            return
        ui.text(screen, "IARA · ASSISTENTE", theme.XS, (236, 250, 255), (box.x + 12, box.y + 13), anchor="midleft")
        ui.text(screen, "X", theme.XS, (236, 250, 255), (box.right - 14, box.y + 13))
        ui.text(screen, "ACEITAR COOKIES?", theme.M, (20, 40, 56), (box.centerx, box.y + 62))
        for k, label in enumerate(("ACEITAR", "ACEITAR TUDO")):
            b = pygame.Rect(0, 0, 130, 28)
            b.center = (box.centerx - 70 + k * 140, box.y + 112)
            screen.fill(IARA if k else (200, 220, 230), b)
            ui.text(screen, label, theme.XS, (12, 30, 44), b.center)


_LABELS = {}


def _label(text, color):
    key = (text, color)
    if key not in _LABELS:
        _LABELS[key] = pygame.font.Font(None, 22).render(text, True, color)
    return _LABELS[key]


# ─────────────────────────────────────────────
#  Cérebros
# ─────────────────────────────────────────────
def brains():
    """Cérebros das criaturas da mansão (entram em enemies.BRAINS)."""
    from . import enemies as en
    from .clinica import Stamp

    class ProcessoAI(en.DiabreteAI):
        """Anda atrás e dá um bote curto. Quando cai, se desmonta em dois Apensos."""

        WINDUP = 20

        def on_death(self, me, match):
            for k in (-1, 1):
                x, y = match.arena.free_spot(me.x + k * 24, me.y + 6, 12)
                e = match.spawn_now("apenso", x, y)
                e.stun(20)
            match.burst(me.x, me.y - 10, MANILA, 16, speed=4)
            match.popup(me.x, me.y - 50, "DESAPENSOU!", MANILA)
            match.assets.play("pagina", 0.4)

    class ApensoAI(en.DiabreteAI):
        """Folhinha solta: rápida e fraca."""

        WINDUP = 14

    class CarimbadorAI(en.EnemyAI):
        """Escolhe onde o herói está, o retângulo INDEFERIDO aparece no chão e ele pula lá para
        carimbar. Depois fica com o cabo preso no chão: CARIMBO PRESO, leva mais dano."""

        reaction = 7
        WINDUP = 44
        STUCK = 60

        def __init__(self, difficulty="normal"):
            super().__init__(difficulty)
            self.cd = random.randint(60, 120)
            self.spot = None
            self.stuck = 0

        def act(self, me, match, target):
            if self.stuck > 0:
                self.stuck -= 1
                me.steer(0, 0)
                if self.stuck == 0:
                    me.vulnerability = 1.0
                return
            if me.windup > 0:
                me.steer(0, 0)
                if me.windup == 1 and self.spot is not None:
                    me.x, me.y = self.spot
                    match.arena.resolve(me)
                    self.stuck = self.STUCK
                    me.vulnerability = 1.5
                    match.popup(me.x, me.y - 50, "CARIMBO PRESO", (240, 220, 200))
                return
            self.cd -= 1
            me.steer(*self.move)
            d = me.distance_to(target)
            if self.cd <= 0 and d < 320 and not match.arena.blocks_segment((me.x, me.y), (target.x, target.y)):
                self.cd = round(random.randint(170, 230) / self.aggression)
                frames = round(self.WINDUP / max(0.8, self.aggression))
                self.spot = match.arena.free_spot(target.x, target.y, me.radius)
                me.face(target)
                me.start_windup(frames, INK_RED)
                match.add_effect(Stamp(me, self.spot[0], self.spot[1], frames, round(14 * me.damage_bonus),
                                       radius=48, word="INDEFERIDO", stun=34))
            elif d < me.weapon.reach + target.radius + 4:
                me.attack(match, target)

    class ImpressoraAI(en.EnemyAI):
        """Fica a meia distância e cospe 3 rajadas de folhas em leque (a luz verde pisca antes).
        Depois ATOLA O PAPEL: fica parada, levando mais dano."""

        reaction = 7
        AIM = 24
        BURSTS = 3
        JAM = 90

        def __init__(self, difficulty="normal"):
            super().__init__(difficulty)
            self.bursts = 0
            self.jam = 0
            self.cd = random.randint(40, 90)

        def decide(self, me, match, target):
            d = me.distance_to(target)
            if match.arena.blocks_segment((me.x, me.y), (target.x, target.y)) or d > 340:
                self.move = self.chase(me, match, target.x, target.y)
            elif d < 180:
                self.move = self.chase(me, match, target.x, target.y, away=True)
            else:
                ax, ay = me.direction_to(target)
                self.move = (-ay * self.strafe * 0.5, ax * self.strafe * 0.5)

        def act(self, me, match, target):
            if self.jam > 0:
                self.jam -= 1
                me.steer(0, 0)
                if self.jam % 10 == 0:
                    match.burst(me.x, me.y - 24, (246, 244, 236), 2, speed=1.5)
                if self.jam == 0:
                    me.vulnerability = 1.0
                return
            if me.windup > 0:
                me.steer(0, 0)
                me.face(target)
                if me.windup == 1:
                    self._fan(me, match, target)
                return
            self.cd -= 1
            me.steer(*self.move)
            if self.cd <= 0 and me.distance_to(target) < 480 and not match.arena.blocks_segment((me.x, me.y), (target.x, target.y)):
                me.start_windup(round(self.AIM / max(0.8, self.aggression)), (140, 240, 150))

        def _fan(self, me, match, target):
            dx, dy = me.direction_to(target)
            w = me.weapon
            for a in (-0.3, -0.1, 0.1, 0.3):
                c, s = math.cos(a), math.sin(a)
                match.spawn_projectile(me, w, (dx * c - dy * s, dx * s + dy * c), round(w.damage * me.damage_bonus))
            match.assets.play("pagina", 0.35)
            self.bursts += 1
            if self.bursts >= self.BURSTS:
                self.bursts = 0
                self.jam = self.JAM
                me.vulnerability = 1.6
                match.popup(me.x, me.y - 50, "ATOLOU PAPEL", (246, 244, 236))
            self.cd = round(34 / self.aggression) if self.bursts else 24

    class GarrafaAI(en.EsqueletoAI):
        """Mantém distância. A tampa abre (aviso marrom) e o café cai onde o herói está: o
        círculo no chão avisa e fica uma poça quente."""

        AIM = 26
        FALL = 40

        def act(self, me, match, target):
            if me.windup > 0:
                me.steer(0, 0)
                me.face(target)
                if me.windup == 1:
                    frames = round(self.FALL / max(0.8, self.aggression))
                    x, y = match.arena.free_spot(target.x + target.vx * 10 if hasattr(target, "vx") else target.x,
                                                 target.y, 10)
                    match.add_effect(CoffeeSplash(me, x, y, frames, round(10 * me.damage_bonus)))
                    me.attack_cd = round(110 / self.aggression)
                    match.assets.play("arremesso", 0.3)
                return
            me.steer(*self.move)
            d = me.distance_to(target)
            if me.attack_cd <= 0 and d < 520 and not match.arena.blocks_segment((me.x, me.y), (target.x, target.y)):
                if random.random() < 0.05 * self.aggression:
                    me.start_windup(round(self.AIM / max(0.8, self.aggression)), COFFEE_L)

    class TuiuiuAI(en.DroneAI):
        """O tuiuiú do Pantanal com hélice: voa em roda e dá rasante (linha laranja no chão)."""

        COLOR = TUIUIU
        SOUND = "drone"
        DIVE = 20
        WINDUP = 28

    class PontoAI(en.EnemyAI):
        """Chega perto, o visor pisca vermelho e ele marca FALTA no herói mais perto (se o herói
        ainda não estiver marcado). Com a falta, o herói leva mais dano por 5 s."""

        reaction = 7
        WINDUP = 40

        def __init__(self, difficulty="normal"):
            super().__init__(difficulty)
            self.cd = random.randint(80, 140)
            self.mark = None

        def act(self, me, match, target):
            if me.windup > 0:
                me.steer(0, 0)
                me.face(target)
                if me.windup == 1 and me.distance_to(target) < 300 and getattr(target, "falta", None) is None:
                    target.falta = FaltaMark(target)
                    match.add_effect(target.falta)
                    match.popup(target.x, target.y - 90, "BATEU FALTA!", INK_RED)
                    match.assets.play("bip", 0.5)
                return
            self.cd -= 1
            me.steer(*self.move)
            d = me.distance_to(target)
            if self.cd <= 0 and d < 260 and getattr(target, "falta", None) is None:
                self.cd = round(random.randint(240, 300) / self.aggression)
                me.start_windup(round(self.WINDUP / max(0.8, self.aggression)), INK_RED)
            elif d < me.weapon.reach + target.radius + 4:
                me.attack(match, target)

    class PopupAI(en.EnemyAI):
        """Some e reaparece perto do herói (o brilho ciano marca o lugar antes). Lá, carrega a
        janela (CARREGANDO...): se terminar, abre o ACEITAR COOKIES? em cima do herói. Bater
        nele enquanto carrega fecha a janela."""

        reaction = 6
        WARN = 30
        LOAD = 70

        def __init__(self, difficulty="normal"):
            super().__init__(difficulty)
            self.jump_cd = random.randint(90, 160)
            self.spot = None
            self.warn = 0
            self.loading = 0
            self.last_hp = None

        def act(self, me, match, target):
            hit = me.hp < (me.max_hp if self.last_hp is None else self.last_hp)
            self.last_hp = me.hp
            if self.warn > 0:
                self.warn -= 1
                me.steer(0, 0)
                if self.warn % 4 == 0:
                    match.burst(self.spot[0], self.spot[1] - 10, IARA, 3, speed=1.5)
                if self.warn == 0:
                    me.x, me.y = self.spot
                    match.arena.resolve(me)
                    me.cloak = 0.0
                    me.face(target)
                    self.loading = round(self.LOAD / max(0.8, self.aggression))
                    me.start_windup(self.loading, IARA)
                    me.phase_label = "CARREGANDO..."
                return
            if self.loading > 0:
                me.steer(0, 0)
                if hit:
                    self.loading = 0
                    me.windup = 0
                    me.phase_label = ""
                    match.popup(me.x, me.y - 50, "JANELA FECHADA!", IARA_L)
                    self.jump_cd = round(160 / self.aggression)
                    return
                self.loading -= 1
                if self.loading == 0:
                    me.phase_label = ""
                    victims = [p for p in match.alive_players if p.distance_to(me) < 500]
                    if victims and hasattr(match, "add_notice"):
                        match.add_notice(CookieNotice(min(victims, key=me.distance_to)))
                        match.assets.play("notificacao", 0.5)
                    self.jump_cd = round(random.randint(200, 260) / self.aggression)
                return
            me.cloak += ((0.5 if me.distance_to(target) > 200 else 0.0) - me.cloak) * 0.1
            self.jump_cd -= 1
            me.steer(*self.move)
            d = me.distance_to(target)
            if self.jump_cd <= 0:
                a = random.uniform(0, math.tau)
                self.spot = match.arena.free_spot(target.x + math.cos(a) * 110, target.y + math.sin(a) * 110, me.radius)
                self.warn = round(self.WARN / max(0.8, self.aggression))
                me.cloak = 0.9
            elif d < me.weapon.reach + target.radius + 4:
                me.attack(match, target)

    class ProjetorAI(en.EnemyAI):
        """Anda devagar, a lente acende e projeta o gráfico de pizza em volta do herói. Metade das
        fatias pisca e depois queima."""

        reaction = 8
        WINDUP = 24
        CAST = 56

        def __init__(self, difficulty="normal"):
            super().__init__(difficulty)
            self.cd = random.randint(70, 130)

        def decide(self, me, match, target):
            d = me.distance_to(target)
            if d > 380 or match.arena.blocks_segment((me.x, me.y), (target.x, target.y)):
                self.move = self.chase(me, match, target.x, target.y)
            elif d < 200:
                self.move = self.chase(me, match, target.x, target.y, away=True)
            else:
                self.move = (0.0, 0.0)

        def act(self, me, match, target):
            if me.windup > 0:
                me.steer(0, 0)
                me.face(target)
                if me.windup == 1:
                    frames = round(self.CAST / max(0.8, self.aggression))
                    match.add_effect(PieChart(me, target.x, target.y, frames, round(12 * me.damage_bonus)))
                    match.assets.play("bip", 0.3)
                return
            self.cd -= 1
            me.steer(*self.move)
            if self.cd <= 0 and me.distance_to(target) < 520:
                self.cd = round(random.randint(200, 260) / self.aggression)
                me.start_windup(self.WINDUP, (255, 250, 220))

    class ArquivoAI(en.ExoAI):
        """Arquivo de Aço (elite): investe em linha (a linha aparece no chão) e no fim as gavetas
        abrem: GAVETAS ABERTAS, leva o dobro de dano."""

        def act(self, me, match, target):
            was = self.charging
            super().act(me, match, target)
            if was and not self.charging:
                me.vulnerability = 2.0
                match.popup(me.x, me.y - 76, "GAVETAS ABERTAS", (230, 236, 244))
                match.assets.play("soco_metal", 0.4)

    class IaraAI(en.EnemyAI):
        """A IARA, flutuando no meio do núcleo. Enquanto um dos 4 cabos estiver inteiro, quase
        nada passa nela. De tempos em tempos estica os tentáculos na direção de cada herói (a linha
        ciano avisa antes) e abre pop-ups pela sala."""

        reaction = 6
        CAST = 50

        def __init__(self, difficulty="normal"):
            super().__init__(difficulty)
            self.cd = 120
            self.cables = []
            self.casts = 0
            self.exposed = False

        def decide(self, me, match, target):
            self.move = (0.0, 0.0)

        def act(self, me, match, target):
            me.steer(0, 0)
            me.face(target)
            if not self.exposed and self.cables and not any(c.alive_in_match for c in self.cables):
                self.exposed = True
                me.vulnerability = IARA_EXPOSED
                match.popup(me.x, me.y - 120, "CABOS CORTADOS: IARA EXPOSTA!", theme.MOSS)
                match.assets.play("vidro", 0.5)
            elif not self.exposed:
                me.vulnerability = IARA_CABLE_ARMOR
                me.phase_label = "CORTEM OS 4 CABOS"
            else:
                me.phase_label = ""
            if match.frame % 6 == 0:
                match.particles.append(Particle(me.x + random.uniform(-30, 30), me.y - random.uniform(10, 70),
                                                0, -0.6, IARA_L, 20, 2))
            if me.windup > 0:
                if me.windup == 1:
                    self._cast(me, match)
                return
            self.cd -= 1
            if self.cd <= 0:
                self.cd = round(random.randint(130, 170) / self.aggression)
                me.start_windup(24, IARA)

        def _cast(self, me, match):
            self.casts += 1
            frames = round(self.CAST / max(0.8, self.aggression))
            dmg = round(14 * me.damage_bonus)
            for p in match.alive_players:
                dx, dy = me.direction_to(p)
                if (dx, dy) == (0.0, 0.0):
                    continue
                for off in ((0.0,) if self.casts % 2 else (-0.35, 0.35)):
                    c, s_ = math.cos(off), math.sin(off)
                    match.add_effect(TentacleBeam(me, me.x, me.y, dx * c - dy * s_, dx * s_ + dy * c, 700, frames, dmg))
            popups = [e for e in match.alive_enemies if getattr(e, "kind", "") == "popup_iara"]
            if self.casts % 2 == 0 and len(popups) < 2:
                match.summon(("popup_iara",), me)
            match.assets.play("bip", 0.4)

    return {"iara_nucleo": IaraAI, "processo": ProcessoAI, "apenso": ApensoAI, "carimbador": CarimbadorAI, "impressora": ImpressoraAI,
            "garrafa_termica": GarrafaAI, "tuiuiu_drone": TuiuiuAI, "ponto_eletronico": PontoAI,
            "popup_iara": PopupAI, "projetor": ProjetorAI, "arquivo_aco": ArquivoAI}


# ─────────────────────────────────────────────
#  Perigos das salas
# ─────────────────────────────────────────────
class QueueLanes:
    """Fila do Atendimento: faixas de fila (as fitas no chão) entre os guichês. Quando a senha é
    chamada, a fila anda: quem estiver numa faixa é arrastado na direção da seta. As setas piscam
    antes; é só sair da faixa."""

    WARN = 60
    MOVE = 100
    CALL = (220, 300)
    PUSH = 2.6
    PATIENCE = 4 * 60            # segredo: parado na fila esse tanto
    LANES = ((180, 300, 1240, 70, (1, 0)), (180, 1060, 1240, 70, (-1, 0)),
             (460, 360, 70, 560, (0, -1)), (1070, 360, 70, 560, (0, 1)))

    def __init__(self, arena, rng=random):
        self.arena = arena
        self.rng = rng
        self.lanes = [(pygame.Rect(*arena.at(x, y), w, h), d) for x, y, w, h, d in self.LANES]
        self.active = []
        self.state = "calm"
        self.timer = 150
        self.ticket = rng.randint(100, 180)
        self.waiting = {}            # segredo: jogador -> (x, y, quadros parado numa faixa)
        self.called = set()

    def update(self, match):
        self._wait_in_line(match)
        self.timer -= 1
        if self.state == "calm" and self.timer <= 0:
            self.state, self.timer = "warn", self.WARN
            self.ticket += 1
            self.active = self.rng.sample(range(len(self.lanes)), 2)
            match.assets.play("senha", 0.4)
        elif self.state == "warn" and self.timer <= 0:
            self.state, self.timer = "move", self.MOVE
        elif self.state == "move":
            for i in self.active:
                rect, (dx, dy) = self.lanes[i]
                for f in match.fighters:
                    if not f.alive_in_match or f.lift > 0 or not rect.collidepoint(f.x, f.y):
                        continue
                    k = self.PUSH * (1 - getattr(f, "knock_resist", 0.0))
                    if k > 0.01:
                        f.x += dx * k
                        f.y += dy * k
                        self.arena.resolve(f)
            if self.timer <= 0:
                self.state, self.timer = "calm", self.rng.randint(*self.CALL)
                self.active = []

    def _wait_in_line(self, match):
        """Segredo: quem fica parado numa faixa da fila, educadamente, é chamado pela senha."""
        from . import segredos
        for p in getattr(match, "players", ()):
            x, y, n = self.waiting.get(p, (None, None, 0))
            here = (round(p.x), round(p.y))
            if p in self.called or not p.alive_in_match or here != (x, y) \
                    or not any(rect.collidepoint(p.x, p.y) for rect, _ in self.lanes):
                self.waiting[p] = (*here, 0)
                continue
            self.waiting[p] = (x, y, n + 1)
            if n + 1 >= self.PATIENCE:
                self.called.add(p)
                text = f"SENHA {self.ticket + 1:03d}... {p.label}?"
                segredos.hint(match, p.x, p.y - config.SPRITE_HEIGHT - 10, text, (255, 236, 120), life=110)
                segredos.find("senha", match, p.x, p.y - config.SPRITE_HEIGHT - 40)

    def draw(self, view, cam, frame):
        for i, (rect, (dx, dy)) in enumerate(self.lanes):
            r = rect.move(-round(cam.x), -round(cam.y))
            on = i in self.active
            # as fitas da fila (os pedestais nas pontas)
            tape = (200, 40, 50) if on and (self.state == "move" or (frame // 6) % 2 == 0) else (70, 70, 120)
            if dx:
                view.fill(tape, (r.x, r.y, r.w, 3))
                view.fill(tape, (r.x, r.bottom - 3, r.w, 3))
                posts = [(x, y) for x in range(r.x, r.right + 1, 124) for y in (r.y, r.bottom)]
            else:
                view.fill(tape, (r.x, r.y, 3, r.h))
                view.fill(tape, (r.right - 3, r.y, 3, r.h))
                posts = [(x, y) for y in range(r.y, r.bottom + 1, 112) for x in (r.x, r.right)]
            for px, py in posts:
                view.fill((60, 60, 70), (px - 3, py - 14, 6, 14))
                view.fill((210, 200, 120), (px - 4, py - 16, 8, 3))
            if not on:
                continue
            # setas no chão indo para onde a fila anda
            shift = (frame * 3) % 60 if self.state == "move" else 0
            n = (r.w if dx else r.h) // 60
            for k in range(n):
                if dx:
                    cx, cy = r.x + (k * 60 + shift * dx) % r.w, r.centery
                else:
                    cx, cy = r.centerx, r.y + (k * 60 + shift * dy) % r.h
                pts = [(cx + dx * 12, cy + dy * 12), (cx - dx * 6 - dy * 10, cy - dy * 6 + dx * 10),
                       (cx - dx * 6 + dy * 10, cy - dy * 6 - dx * 10)]
                pygame.draw.polygon(view, (255, 220, 90), pts)

    def draw_screen(self, screen, ui, frame):
        w = screen.get_width()
        box = pygame.Rect(0, 0, 320, 44)
        box.midtop = (w // 2, 60)
        lit = self.state != "calm" and (frame // 6) % 2 == 0
        pygame.draw.rect(screen, (16, 16, 30), box, border_radius=6)
        pygame.draw.rect(screen, (255, 220, 90) if lit else (90, 90, 140), box, 2, border_radius=6)
        ui.text(screen, f"SENHA {self.ticket:03d} · GUICHÊ {self.ticket % 3 + 1}", theme.S,
                (255, 236, 120) if lit else (180, 190, 230), box.center)
        if self.state == "warn" and (frame // 8) % 2 == 0:
            ui.text(screen, "A FILA VAI ANDAR! SAIAM DAS FAIXAS", theme.XS, (255, 220, 90), (w // 2, 116))


class FallingPiles:
    """Arquivo Geral: pilhas de processo despencam do alto das estantes. A sombra no chão cresce
    (aviso) e, quando a pilha cai, machuca e atordoa quem estiver embaixo. Sobra papel no chão."""

    WARN = 60
    GAP = (70, 110)
    DAMAGE = 12
    RADIUS = 44

    def __init__(self, arena, rng=random):
        self.arena = arena
        self.rng = rng
        self.piles = []                 # [x, y, idade]
        self.rubble = []                # [x, y, vida]
        self.timer = 100

    def update(self, match):
        self.timer -= 1
        if self.timer <= 0:
            self.timer = self.rng.randint(*self.GAP)
            targets = match.alive_players
            for k in range(2 if self.rng.random() < 0.4 else 1):
                if targets and self.rng.random() < 0.6:
                    p = self.rng.choice(targets)
                    x, y = p.x + self.rng.uniform(-50, 50), p.y + self.rng.uniform(-40, 40)
                else:
                    x, y = self.arena.random_free_spot(30)
                self.piles.append([x, y, -k * 18])
        for pile in self.piles:
            pile[2] += 1
            if pile[2] == self.WARN:
                x, y = pile[0], pile[1]
                for f in match.fighters:
                    if f.alive_in_match and f.lift <= 0 and math.hypot(f.x - x, (f.y - y) * 1.6) < self.RADIUS + f.radius * 0.5:
                        if f.take_damage(round(self.DAMAGE * match.enemy_dmg), x, y, match=match):
                            f.stun(24)
                match.burst(x, y - 10, MANILA, 14, speed=4)
                match.dust(x, y + 10, 8)
                match.camera.shake(3)
                match.assets.play("pagina", 0.5)
                self.rubble.append([x, y, 5 * config.FPS])
        self.piles = [p for p in self.piles if p[2] < self.WARN]
        for r in self.rubble:
            r[2] -= 1
        self.rubble = [r for r in self.rubble if r[2] > 0]

    def draw(self, view, cam, frame):
        for x, y, life in self.rubble:
            sx, sy = round(x - cam.x), round(y - cam.y + 10)
            a = min(1.0, life / 40)
            for k in range(5):
                ox, oy = (k * 13) % 34 - 17, (k * 7) % 14 - 7
                c = tuple(round(v * (0.6 + 0.4 * a)) for v in (MANILA if k % 2 else (240, 238, 228)))
                view.fill(c, (sx + ox, sy + oy, 12, 8))
        for x, y, age in self.piles:
            if age < 0:
                continue
            t = age / self.WARN
            sx, sy = round(x - cam.x), round(y - cam.y + 10)
            r = round(self.RADIUS * (0.4 + 0.6 * t))
            layer = pygame.Surface((r * 2, r), pygame.SRCALPHA)
            pygame.draw.ellipse(layer, (20, 14, 10, round(60 + 120 * t)), layer.get_rect())
            if (age // 4) % 2 == 0 or t > 0.7:
                pygame.draw.ellipse(layer, (*INK_RED, 200), layer.get_rect(), 2)
            view.blit(layer, (sx - r, sy - r // 2))
            # a pilha caindo
            drop = round((1 - t) * 220)
            if drop < 200:
                for k in range(4):
                    view.fill((60, 46, 30), (sx - 16, sy - drop - 12 - k * 7, 32, 7))
                    view.fill(MANILA if k % 2 else (240, 238, 228), (sx - 15, sy - drop - 11 - k * 7, 30, 5))

    def draw_screen(self, screen, ui, frame):
        if self.piles and (frame // 10) % 3 == 0:
            ui.text(screen, "PILHAS CAINDO! SAIAM DAS SOMBRAS", theme.XS, MANILA, (screen.get_width() // 2, 96))


class Heat:
    """Pátio a 47°C: cada herói tem um termômetro. No sol ele sobe; na sombra dos toldos baixa
    rápido. Cheio, vem a INSOLAÇÃO: fica lento e perde um pouco de vida até ir para a sombra."""

    RISE = 1 / (14 * config.FPS)     # sol: enche em 14 s
    COOL = 1 / (2.5 * config.FPS)    # sombra: esvazia em 2,5 s
    SHADES = ((560, 600), (1440, 600), (1000, 700), (560, 1000), (1440, 1000), (1000, 200))
    SHADE = (200, 120)

    def __init__(self, arena, rng=random):
        self.arena = arena
        self.heat = {}
        self.shades = []
        for x, y in self.SHADES:
            x, y = arena.free_spot(*arena.at(x, y), 40)
            self.shades.append(pygame.Rect(round(x - self.SHADE[0] / 2), round(y - self.SHADE[1] / 2), *self.SHADE))
        self.match = None

    def in_shade(self, f):
        return any(r.collidepoint(f.x, f.y) for r in self.shades)

    def update(self, match):
        self.match = match
        for p in match.players:
            if not p.alive_in_match:
                self.heat[p] = 0.0
                continue
            h = self.heat.get(p, 0.0)
            h = max(0.0, h - self.COOL) if self.in_shade(p) else min(1.0, h + self.RISE)
            self.heat[p] = h
            if h >= 1.0:
                p.slow(10)
                if match.frame % 40 == 0:
                    p.take_damage(max(1, round(3 * match.enemy_dmg)), p.x, p.y, match=match)
                    p.knock = [0.0, 0.0]
                    match.popup(p.x, p.y - 70, "INSOLAÇÃO!", SUN)
                if match.frame % 8 == 0:
                    match.particles.append(Particle(p.x + random.uniform(-10, 10), p.y - 40, 0, -1.0,
                                                    (255, 230, 160), 18, 2))

    def draw(self, view, cam, frame):
        for r in self.shades:
            rr = r.move(-round(cam.x), -round(cam.y))
            layer = pygame.Surface(rr.size, pygame.SRCALPHA)
            layer.fill((10, 30, 50, 90))
            view.blit(layer, rr)
            # o toldo listrado em cima
            top = pygame.Rect(rr.x + 10, rr.y - 24, rr.w - 20, 22)
            for k in range(0, top.w, 20):
                view.fill((230, 70, 60) if (k // 20) % 2 else (246, 240, 226), (top.x + k, top.y, min(20, top.w - k), top.h))
            view.fill((60, 50, 40), (top.x, top.bottom, top.w, 3))
            view.fill((90, 90, 96), (top.x + 4, top.bottom, 4, rr.h // 2))
            view.fill((90, 90, 96), (top.right - 8, top.bottom, 4, rr.h // 2))

    def draw_screen(self, screen, ui, frame):
        match = self.match
        if match is None:
            return
        cam = match.camera
        for p in match.alive_players:
            h = self.heat.get(p, 0.0)
            if h < 0.05:
                continue
            sx, sy = cam.to_screen(p.x + 26, p.y - 40)
            bar = pygame.Rect(round(sx), round(sy), 8, 40)
            screen.fill((30, 20, 20), bar.inflate(4, 4))
            fill = round(bar.h * h)
            hot = h >= 1.0 and (frame // 6) % 2 == 0
            screen.fill((255, 250, 220) if hot else (255, round(200 - 150 * h), 50), (bar.x, bar.bottom - fill, bar.w, fill))
        if any(self.heat.get(p, 0) > 0.7 for p in match.alive_players) and (frame // 12) % 2 == 0:
            ui.text(screen, "TÁ FERVENDO! FIQUEM NA SOMBRA DOS TOLDOS", theme.XS, SUN, (screen.get_width() // 2, 96))


class NoBreak:
    """No-break do CPD: ATACAR perto liga."""

    RADIUS = 70

    def __init__(self, x, y):
        self.x, self.y = x, y
        self.on = False
        self.flash = 0

    def near(self, f):
        return abs(f.x - self.x) < self.RADIUS and abs(f.y - self.y) < self.RADIUS


class Blackout:
    """Subsolo do CPD: caiu a energia. Escuro, só se enxerga em volta de cada herói. Três
    no-breaks nas paredes: ATACAR perto liga um (fica mais claro); os três ligados, a luz volta."""

    SIGHT = 180
    SPOTS = ((90, 160), (1510, 160), (800, 1110))
    DARK = (6, 10, 18)

    def __init__(self, arena, rng=random):
        self.arena = arena
        self.boxes = [NoBreak(*arena.free_spot(*arena.at(x, y), 24)) for x, y in self.SPOTS]
        self.density = 1.0
        self.match = None
        self._veil = None

    @property
    def off_boxes(self):
        return [b for b in self.boxes if not b.on]

    def interact(self, f, match):
        for b in self.off_boxes:
            if b.near(f):
                b.on = True
                b.flash = 30
                left = len(self.off_boxes)
                text = "A LUZ VOLTOU!" if left == 0 else f"NO-BREAK LIGADO ({3 - left}/3)"
                match.popup(b.x, b.y - 60, text, (140, 255, 170))
                match.burst(b.x, b.y - 20, (140, 255, 170), 14, speed=3)
                match.assets.play("eletrico", 0.5)
                return True
        return False

    def update(self, match):
        self.match = match
        want = len(self.off_boxes) / len(self.boxes)
        self.density += (want - self.density) * 0.03
        for b in self.boxes:
            b.flash = max(0, b.flash - 1)

    def draw(self, view, cam, frame):
        for b in self.boxes:
            sx, sy = round(b.x - cam.x), round(b.y - cam.y)
            body = pygame.Rect(sx - 16, sy - 40, 32, 40)
            view.fill((30, 32, 40), body.inflate(4, 4))
            view.fill((60, 64, 76), body)
            led = (90, 255, 140) if b.on else ((255, 60, 60) if (frame // 15) % 2 else (90, 20, 20))
            view.fill(led, (body.x + 6, body.y + 8, 6, 6))
            view.fill((20, 20, 26), (body.x + 6, body.y + 20, 20, 12))
            if b.on:
                view.fill((90, 255, 140), (body.x + 8, body.y + 22, 16, 8))

    def draw_screen(self, screen, ui, frame):
        match = self.match
        if self.density < 0.03 or match is None:
            return
        w, h = screen.get_size()
        if self._veil is None or self._veil.get_size() != (w, h):
            self._veil = pygame.Surface((w, h), pygame.SRCALPHA)
        veil = self._veil
        top = round(235 * self.density)
        dark = self.DARK if (frame // 40) % 2 else (34, 6, 10)       # a luz de emergência piscando
        veil.fill((*dark, top))
        cam = match.camera
        sight = round(self.SIGHT * cam.zoom) if hasattr(cam, "zoom") else self.SIGHT
        steps = 10
        for k in range(steps + 1):
            t = k / steps
            r = max(10, round(sight + 60 - 120 * t))
            alpha = round(top * (1 - t) ** 1.6)
            for p in match.alive_players:
                sx, sy = cam.to_screen(p.x, p.y - 10)
                pygame.draw.circle(veil, (*dark, alpha), (round(sx), round(sy)), r)
        for rect in getattr(match, "hud_regions", lambda: [])():
            veil.fill((*dark, round(50 * self.density)), rect)
        screen.blit(veil, (0, 0))
        for e in match.alive_enemies:                 # os olhos dos monstros no escuro
            sx, sy = cam.to_screen(e.x, e.y - 22 * getattr(e, "draw_scale", 1))
            screen.fill((255, 60, 60), (round(sx) - 4, round(sy), 2, 2))
            screen.fill((255, 60, 60), (round(sx) + 2, round(sy), 2, 2))
        for b in self.off_boxes:
            sx, sy = cam.to_screen(b.x, b.y - 60)
            if (frame // 10) % 2 == 0:
                ui.text(screen, "NO-BREAK", theme.XS, (255, 90, 90), (round(sx), round(sy)))
        if self.off_boxes and (frame // 30) % 4 == 0:
            ui.text(screen, "LIGUEM OS NO-BREAKS (ATACAR PERTO)", theme.XS, (150, 170, 200), (w // 2, 96))


class Meeting:
    """Sala de Reunião do Comitê: de tempos em tempos entra PAUTA NOVA e a mesa puxa todo mundo
    para o meio da sala (os anéis aparecem antes). Dá para andar contra o puxão."""

    WARN = 70
    PULL = 120
    GAP = (360, 480)
    FORCE = 1.6
    TOPICS = ("PAUTA NOVA: O NOVO PROCESSO DO PROCESSO", "PAUTA NOVA: REUNIÃO PARA MARCAR A REUNIÃO",
              "PAUTA NOVA: OTIMIZAÇÃO COM IA", "PAUTA NOVA: ALINHAMENTO DO ALINHAMENTO")

    def __init__(self, arena, rng=random):
        self.arena = arena
        self.rng = rng
        self.state = "calm"
        self.timer = 240
        self.center = arena.room.center
        self.topic = self.TOPICS[0]

    def update(self, match):
        self.timer -= 1
        if self.state == "calm" and self.timer <= 0:
            self.state, self.timer = "warn", self.WARN
            self.topic = self.rng.choice(self.TOPICS)
            match.assets.play("alarme", 0.3)
        elif self.state == "warn" and self.timer <= 0:
            self.state, self.timer = "pull", self.PULL
        elif self.state == "pull":
            ease = min(1.0, (self.PULL - self.timer) / 20, self.timer / 20)
            cx, cy = self.center
            for f in match.fighters:
                if f.team == 1 or not f.alive_in_match or f.lift > 0:
                    continue
                dx, dy = cx - f.x, cy - f.y
                d = math.hypot(dx, dy)
                if d < 120:
                    continue
                k = self.FORCE * ease
                f.x += dx / d * k
                f.y += dy / d * k
                self.arena.resolve(f)
            if self.timer <= 0:
                self.state, self.timer = "calm", self.rng.randint(*self.GAP)

    def draw(self, view, cam, frame):
        if self.state == "calm":
            return
        cx, cy = round(self.center[0] - cam.x), round(self.center[1] - cam.y)
        for k in range(4):
            phase = ((frame * (3 if self.state == "pull" else 1) + k * 40) % 160) / 160
            r = round(520 * (1 - phase)) if self.state == "pull" else round(160 + 360 * phase)
            if r < 40:
                continue
            layer = pygame.Surface((r * 2, r), pygame.SRCALPHA)
            pygame.draw.ellipse(layer, (*IARA, round(150 * (1 - abs(phase - 0.5) * 2))), layer.get_rect(), 3)
            view.blit(layer, (cx - r, cy - r // 2))

    def draw_screen(self, screen, ui, frame):
        if self.state == "calm":
            return
        if self.state == "pull" or (frame // 8) % 2 == 0:
            ui.text(screen, self.topic, theme.XS, IARA_L, (screen.get_width() // 2, 96))
        if self.state == "warn":
            ui.text(screen, "A MESA VAI PUXAR TODO MUNDO: SEGUREM FIRME", theme.XS, IARA, (screen.get_width() // 2, 116))


HAZARDS = {"fila": QueueLanes, "pilha": FallingPiles, "calor": Heat, "energia": Blackout, "reuniao": Meeting}


# ── recompensa: a IARA mascote ───────────────
MASCOT_LINES = ("PROTOCOLO RECEBIDO!", "AGORA SÓ ASSISTENTE", "CAFÉ PASSADO?", "SEM COOKIES, PROMETO",
                "DESPACHO: DEFERIDO", "47°C LÁ FORA...", "NADA DE OTIMIZAR NINGUÉM")
MASCOT_SCALE = 0.42
MASCOT_TALK = 540            # uma fala a cada 9 s


class IaraMascot:
    """A IARA pequenininha (e do bem) flutuando atrás do P1 nos acampamentos, depois do capítulo 4.
    Só enfeite: não bate, não apanha, não segura passagem."""

    alive = True

    def __init__(self, target, sprites=None):
        self.target = target
        self.x, self.y = target.x - 46, target.y - 40
        self.age = 0
        self.lines = list(MASCOT_LINES)
        random.shuffle(self.lines)
        self.frames = []
        if sprites is not None:
            for i in range(4):
                img = sprites.frame("frente", i)
                size = (max(1, round(img.get_width() * MASCOT_SCALE)), max(1, round(img.get_height() * MASCOT_SCALE)))
                self.frames.append(pygame.transform.smoothscale(img, size))

    def update(self, match):
        self.age += 1
        t = self.target
        side = -1 if t.facing[0] >= 0 else 1                 # fica do lado de trás de quem ela segue
        gx, gy = t.x + side * 46, t.y - 40
        self.x += (gx - self.x) * 0.08
        self.y += (gy - self.y) * 0.08
        if self.age % MASCOT_TALK == 120:
            line = self.lines[(self.age // MASCOT_TALK) % len(self.lines)]
            match.popup(self.x, self.y - 70, line, IARA)
        if self.age % 30 == 0:
            match.particles.append(Particle(self.x + random.uniform(-6, 6), self.y - 10, 0, -0.4, IARA, 18, 2))

    def draw(self, surf, cam):
        pass                                                   # desenhada por cima de todo mundo

    def draw_over(self, surf, cam):
        sx = round(self.x - cam.x)
        sy = round(self.y - cam.y + math.sin(self.age * 0.07) * 5)
        if self.frames:
            img = self.frames[(self.age // 10) % len(self.frames)]
            surf.blit(img, img.get_rect(midbottom=(sx, sy)))
        else:
            pygame.draw.circle(surf, IARA, (sx, sy - 14), 10)
            pygame.draw.circle(surf, (150, 80, 220), (sx, sy - 14), 4)
