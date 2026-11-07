"""Clínica Clepalovers (capítulo 3 da campanha): os monstros, a Daiwone e os efeitos da clínica.

Cada monstro é um produto ou aparelho de clínica que ganhou vida com o caco do fragmento, e todo
golpe tem um aviso antes e um jeito claro de escapar (o mesmo combinado do resto da campanha):

- Máscara de Argila: pula no herói e deixa uma poça verde que deixa lento (é só sair dela).
- Seringuinha: atira dardos de "botox" lentos; quem leva fica com a CARA CONGELADA e não usa
  a habilidade por 3 s (a agulha brilha antes: dá para desviar).
- Rolinho de Jade: rola em linha reta (a linha aparece no chão antes) e fica tonto no fim.
- Toalha Fantasma: quase invisível de longe; aparece do lado do herói (o vapor avisa onde).
- Esteti-bot: parado, gira o braço do laser rosa atrás do alvo (é lento para virar).
- Cadeira de Procedimento (elite): puxa e prende o herói ("pode deitar"); bater nela solta.
- Espelho Vivo (elite): solta o reflexo de um herói que está jogando; quebrar antes impede.
- Grampeador Vivo: rajadas de grampos em leque; depois de 3 fica de boca aberta, recarregando.
- Máquina corrompida (objetivo): enquanto está ligada, solta monstros.
- Cabo (luta do chefe): enquanto os três estão inteiros, o chefe fica HARMONIZADO.
- Daiwone: a minivilã. Não luta: digita e manda o "oi sumido" (um balão que tapa a visão de um
  herói por 2 s). Bater nela enquanto digita cancela. Com 3 acertos ela foge e quem deu o último
  ganha almas. Aparece no máximo uma vez por masmorra e não conta para limpar a sala.
"""
import math
import random

import pygame

from . import config
from .data import WeaponStats
from .entities import Entity, Particle, hostile
from .projectiles import Projectile, _unit

CLEPA = (255, 110, 190)
CLEPA_D = (184, 56, 128)
CLEPA_L = (255, 192, 226)
CLAY = (128, 168, 92)
CACO = (170, 90, 230)
BOTOX_FREEZE = 3 * config.FPS          # cara congelada: sem habilidade por 3 s
DAIWONE_HITS = 3
DAIWONE_SOULS = 15
DAIWONE_LINES = ("DEPOIS A GENTE CONVERSA", "TÔ OCUPADA", "ME ESQUECE", "VISUALIZEI, TÁ?")
NOTICE_FRAMES = 2 * config.FPS


def _w(name, kind, damage, speed=0, cooldown=16, reach=0, style=""):
    return WeaponStats(name, kind, damage, bullet_speed=speed, cooldown=cooldown, reach=reach, style=style)


def creature_stats():
    """As criaturas da clínica (entram em enemies.CREATURES)."""
    from .enemies import EnemyStats
    return {
        "mascara_argila": EnemyStats(
            "mascara_argila", "Máscara de Argila", 34, 2.6, CLAY, "", "",
            (_w("Gosma", "melee", 6, cooldown=40, reach=28),), "mascara_argila",
            radius=13, drop_chance=0.10),
        "seringuinha": EnemyStats(
            "seringuinha", "Seringuinha", 40, 2.3, CLEPA, "", "",
            (_w("Dardo de Botox", "ranged", 7, speed=5.5, cooldown=90, style="botox"),), "seringuinha",
            drop_chance=0.14),
        "rolinho_jade": EnemyStats(
            "rolinho_jade", "Rolinho de Jade", 36, 3.1, (92, 178, 132), "", "",
            (_w("Rolada", "melee", 5, cooldown=40, reach=24),), "rolinho_jade",
            radius=12, drop_chance=0.10),
        "toalha_fantasma": EnemyStats(
            "toalha_fantasma", "Toalha Fantasma", 38, 2.8, (236, 234, 230), "", "",
            (_w("Toalhada", "melee", 8, cooldown=34, reach=30),), "toalha_fantasma",
            drop_chance=0.12),
        "esteti_bot": EnemyStats(
            "esteti_bot", "Esteti-bot", 70, 0.0, CLEPA, "", "",
            (_w("Laser Rosa", "ranged", 6, speed=10, cooldown=6),), "esteti_bot",
            radius=18, knock_resist=1.0, drop_chance=0.16),
        "cadeira": EnemyStats(
            "cadeira", "Cadeira de Procedimento", 230, 1.9, CLEPA, "", "",
            (_w("Apoio de Braço", "melee", 12, cooldown=50, reach=44),), "cadeira",
            radius=20, elite=True, knock_resist=0.85, drop_chance=0.6),
        "espelho_vivo": EnemyStats(
            "espelho_vivo", "Espelho Vivo", 200, 0.0, (226, 186, 92), "", "",
            (_w("Reflexo", "melee", 0, cooldown=60, reach=10),), "espelho_vivo",
            radius=18, elite=True, knock_resist=1.0, drop_chance=0.6),
        "grampeador": EnemyStats(
            "grampeador", "Grampeador Vivo", 42, 2.6, (200, 204, 214), "", "",
            (_w("Grampos", "ranged", 4, speed=9, cooldown=6, style="grampo"),), "grampeador",
            radius=12, drop_chance=0.14),
        "maquina": EnemyStats(
            "maquina", "Máquina Corrompida", 260, 0.0, CACO, "", "",
            (_w("Choque", "melee", 0, cooldown=60, reach=10),), "maquina",
            radius=20, elite=True, knock_resist=1.0, drop_chance=0.6),
        "cabo": EnemyStats(
            "cabo", "Cabo da Máquina", 90, 0.0, CACO, "", "",
            (_w("Choque", "melee", 0, cooldown=60, reach=10),), "cabo",
            radius=14, knock_resist=1.0, drop_chance=0.0),
        "daiwone": EnemyStats(
            "daiwone", "Daiwone", 999, 3.0, CLEPA_L, "", "",
            (_w("Celular", "melee", 0, cooldown=60, reach=10),), "daiwone",
            radius=10, drop_chance=0.0),
    }


BIG = ("cadeira", "espelho_vivo", "maquina")
STATIC = ("esteti_bot", "espelho_vivo", "maquina", "cabo")      # não andam (nem são empurrados)


# ─────────────────────────────────────────────
#  Projéteis
# ─────────────────────────────────────────────
class BotoxDart(Projectile):
    """Dardo de botox da Seringuinha: lento e brilhando rosa. Quem leva fica com a CARA
    CONGELADA: a habilidade só volta a carregar daqui a 3 s."""

    def on_hit(self, target, match):
        if getattr(target, "ability", None) is not None and hasattr(target, "ability_cd"):
            target.ability_cd = max(target.ability_cd, BOTOX_FREEZE)
            target.botox_timer = BOTOX_FREEZE
            match.popup(target.x, target.y - 62, "CARA CONGELADA", CLEPA_L)
        match.burst(target.x, target.y - 18, CLEPA, 6, speed=2)

    def update(self, match):
        super().update(match)
        if self.age % 3 == 0:
            match.particles.append(Particle(self.x, self.y, 0, 0, CLEPA_L, 10, 2))

    def draw(self, surf, camera):
        dx, dy = _unit(self.vx, self.vy)
        hx, hy = self.x - camera.x, self.y - camera.y
        tail = (round(hx - dx * 12), round(hy - dy * 12))
        pygame.draw.line(surf, (230, 236, 244), tail, (round(hx), round(hy)), 4)
        pygame.draw.line(surf, CLEPA, tail, (round(hx - dx * 4), round(hy - dy * 4)), 2)
        surf.fill((255, 255, 255), (round(hx) - 1, round(hy) - 1, 2, 2))


class PaperShot(Projectile):
    """Boleto (Albeguinio Corrompido): papel girando no ar, com o código de barras."""

    def draw(self, surf, camera):
        cx, cy = round(self.x - camera.x), round(self.y - camera.y)
        img = _paper(self.age // 3 % 4)
        surf.blit(img, img.get_rect(center=(cx, cy)))

    def on_wall(self, wall, match):
        match.burst(self.x, self.y, (240, 238, 230), 5, speed=2)
        return False


_PAPERS = {}


def _paper(frame):
    if frame not in _PAPERS:
        s = pygame.Surface((14, 10), pygame.SRCALPHA)
        s.fill((40, 34, 40), (0, 0, 14, 10))
        s.fill((246, 244, 236), (1, 1, 12, 8))
        for k in range(2, 12, 2):
            s.fill((40, 40, 48), (k, 5, 1, 3))
        s.fill(CLEPA, (2, 2, 6, 1))
        _PAPERS[frame] = pygame.transform.rotate(s, frame * 90 + 20)
    return _PAPERS[frame]


class StapleShot(Projectile):
    """Grampo do Grampeador Vivo: risquinho de metal."""

    def draw(self, surf, camera):
        dx, dy = _unit(self.vx, self.vy)
        hx, hy = self.x - camera.x, self.y - camera.y
        pygame.draw.line(surf, (60, 64, 76), (round(hx - dx * 6), round(hy - dy * 6)), (round(hx), round(hy)), 3)
        pygame.draw.line(surf, (226, 230, 240), (round(hx - dx * 5), round(hy - dy * 5)), (round(hx), round(hy)), 1)


def register_projectiles(table):
    table.update({"botox": BotoxDart, "boleto": PaperShot, "grampo": StapleShot})


def _register():
    from .projectiles import PROJECTILES
    register_projectiles(PROJECTILES)


_register()


# ─────────────────────────────────────────────
#  Efeitos
# ─────────────────────────────────────────────
class ClayPuddle(Entity):
    """Poça de argila da Máscara: quem pisa fica lento. Some sozinha."""

    LIFE = 4 * config.FPS
    flat = True

    def __init__(self, x, y, radius=34):
        super().__init__(x, y)
        self.radius = radius
        self.age = 0

    def update(self, match):
        self.age += 1
        if self.age >= self.LIFE:
            self.alive = False
            return
        if self.age % 6:
            return
        for f in match.fighters:
            if f.team != 1 and f.alive_in_match and f.lift <= 0 and math.hypot(f.x - self.x, (f.y - self.y) * 2) < self.radius:
                f.slow(20)

    def draw(self, surf, camera):
        fade = min(1.0, (self.LIFE - self.age) / 40)
        r = self.radius
        layer = pygame.Surface((r * 2, r), pygame.SRCALPHA)
        pygame.draw.ellipse(layer, (84, 120, 60, round(170 * fade)), (0, 0, r * 2, r))
        pygame.draw.ellipse(layer, (176, 210, 130, round(200 * fade)), (r // 2, r // 4, r, r // 3))
        surf.blit(layer, (round(self.x - camera.x - r), round(self.y - camera.y + 14 - r // 2)))


class Stamp(Entity):
    """Carimbo gigante (Albeguinio Corrompido): o retângulo do carimbo aparece no chão e, no fim,
    desce com tudo: machuca e deixa tonto quem estiver embaixo, e fica a marca PAGO ou VENCIDO."""

    def __init__(self, owner, x, y, frames, damage, radius=70, word=None, stun=30):
        super().__init__(x, y)
        self.owner = owner
        self.frames = self.left = max(1, frames)
        self.damage = damage
        self.radius = radius
        self.word = word or random.choice(("PAGO", "VENCIDO"))
        self.stun_frames = stun
        self.after = 50

    def update(self, match):
        if self.left > 0:
            self.left -= 1
            if self.left == 0:
                self._slam(match)
            return
        self.after -= 1
        if self.after <= 0:
            self.alive = False

    def _slam(self, match):
        for f in match.fighters:
            if not hostile(self.owner, f) or not f.alive_in_match:
                continue
            if abs(f.x - self.x) < self.radius + f.radius * 0.5 and abs(f.y - self.y) < self.radius * 0.6 + f.radius * 0.5:
                if f.take_damage(self.damage, self.x, self.y, attacker=self.owner, match=match):
                    f.stun(self.stun_frames)
        match.burst(self.x, self.y, (220, 60, 70), 18, speed=5)
        match.dust(self.x, self.y + 10, 12)
        match.camera.shake(7)
        match.assets.play("carimbo", 0.6)

    def draw(self, surf, camera):
        cx, cy = round(self.x - camera.x), round(self.y - camera.y + 10)
        w, h = self.radius * 2, round(self.radius * 1.2)
        rect = pygame.Rect(0, 0, w, h)
        rect.center = (cx, cy)
        red = (220, 60, 70)
        if self.left > 0:
            t = 1 - self.left / self.frames
            layer = pygame.Surface(rect.size, pygame.SRCALPHA)
            layer.fill((*red, round(30 + 60 * t)))
            surf.blit(layer, rect)
            blink = (self.left // 4) % 2 == 0 or t > 0.7
            pygame.draw.rect(surf, red if blink else (120, 30, 40), rect, 3)
            # o carimbo descendo (a sombra dele encolhendo)
            drop = round((1 - t) * 60)
            body = pygame.Rect(0, 0, w // 2, h // 3)
            body.midbottom = (cx, cy - drop)
            surf.fill((70, 40, 30), body)
            surf.fill((150, 96, 60), (body.x + body.w // 3, body.y - 14, body.w // 3, 14))
            return
        alpha = max(0, min(255, self.after * 6))
        layer = pygame.Surface(rect.size, pygame.SRCALPHA)
        pygame.draw.rect(layer, (*red, alpha), layer.get_rect(), 4)
        surf.blit(layer, rect)
        _stamp_word(surf, self.word, (cx, cy), alpha)


_WORDS = {}


def _stamp_word(surf, word, center, alpha):
    """Escreve PAGO/VENCIDO em blocos (sem fonte: o efeito é desenhado no mundo)."""
    key = word
    if key not in _WORDS:
        font = pygame.font.Font(None, 30)
        _WORDS[key] = font.render(word, True, (220, 60, 70))
    img = _WORDS[key].copy()
    img.set_alpha(alpha)
    surf.blit(img, img.get_rect(center=center))


class Notice:
    """O balão do "oi sumido": uma notificação gigante em cima de um herói, por 2 s. Fica na tela
    (não no mundo), por cima de tudo, tapando a visão em volta dele."""

    def __init__(self, target, text="oi sumido", frames=NOTICE_FRAMES):
        self.target = target
        self.text = text
        self.frames = self.left = frames

    @property
    def alive(self):
        return self.left > 0

    def update(self):
        self.left -= 1

    def draw(self, screen, cam, ui):
        from . import theme
        sx, sy = cam.to_screen(self.target.x, self.target.y - 30)
        grow = min(1.0, (self.frames - self.left) / 8)
        fade = min(1.0, self.left / 12)
        w, h = round(300 * grow), round(130 * grow)
        if w < 10:
            return
        box = pygame.Rect(0, 0, w, h)
        box.center = (round(sx), round(sy))
        layer = pygame.Surface((w, h + 18), pygame.SRCALPHA)
        a = round(245 * fade)
        pygame.draw.rect(layer, (250, 248, 252, a), (0, 0, w, h), border_radius=18)
        pygame.draw.polygon(layer, (250, 248, 252, a), [(w // 2 - 14, h - 2), (w // 2 + 14, h - 2), (w // 2, h + 16)])
        pygame.draw.rect(layer, (*CLEPA, a), (0, 0, w, h), 3, border_radius=18)
        screen.blit(layer, box.topleft)
        if grow < 1:
            return
        ui.text(screen, "DAIWONE", theme.XS, CLEPA_D, (box.x + 20, box.y + 22), anchor="midleft")
        ui.text(screen, "agora", theme.XS, (150, 140, 160), (box.right - 20, box.y + 22), anchor="midright")
        ui.text(screen, self.text, theme.M, (40, 30, 44), (box.centerx, box.y + 70))
        pygame.draw.circle(screen, CLEPA, (box.x + 24, box.y + 70), 8)       # foto (bolinha rosa)


# ─────────────────────────────────────────────
#  Cérebros
# ─────────────────────────────────────────────
def brains():
    """Cérebros das criaturas da clínica (entram em enemies.BRAINS)."""
    from . import enemies as en

    class MascaraAI(en.EnemyAI):
        """Chega pulando; perto do alvo encolhe (aviso verde) e dá um salto que deixa a poça."""

        reaction = 6
        WINDUP = 20

        def __init__(self, difficulty="normal"):
            super().__init__(difficulty)
            self.leap_cd = random.randint(60, 140)
            self.leaping = False

        def act(self, me, match, target):
            if self.leaping:
                if me.charge_timer <= 0:
                    self.leaping = False
                    match.add_effect(ClayPuddle(me.x, me.y))
                    match.assets.play("gosma", 0.3)
                return
            self.leap_cd -= 1
            if me.windup > 0:
                me.steer(0, 0)
                me.face(target)
                if me.windup == 1:
                    me.start_charge(me.direction_to(target), round(8 * me.damage_bonus))
                    me.charge_timer = 12
                    self.leaping = True
                return
            me.steer(*self.move)
            d = me.distance_to(target)
            if self.leap_cd <= 0 and 60 < d < 180 and not match.arena.blocks_segment((me.x, me.y), (target.x, target.y)):
                self.leap_cd = round(random.randint(130, 190) / self.aggression)
                me.start_windup(self.WINDUP, (176, 210, 130))
            elif d < me.weapon.reach + target.radius + 4:
                me.attack(match, target)

    class SeringaAI(en.EsqueletoAI):
        """Como o arqueiro: mantém distância, a agulha brilha (aviso) e o dardo sai devagar."""

        AIM = 34

        def act(self, me, match, target):
            if me.windup > 0:
                me.steer(0, 0)
                me.face(target)
                if me.windup == 1:
                    me.attack(match, target)
                return
            me.steer(*self.move)
            d = me.distance_to(target)
            if me.attack_cd <= 0 and d < 520 and not match.arena.blocks_segment((me.x, me.y), (target.x, target.y)):
                if random.random() < 0.04 * self.aggression:
                    me.start_windup(round(self.AIM / max(0.8, self.aggression)), CLEPA_L)

    class RolinhoAI(en.DroneAI):
        """Rola em linha reta pela sala (a linha verde aparece no chão antes) e fica tonto no fim."""

        COLOR = (120, 220, 160)
        SOUND = "rolo"
        DIVE = 26
        WINDUP = 30

    class ToalhaAI(en.EnemyAI):
        """Quase invisível de longe. De tempos em tempos some e reaparece do lado do alvo: uma nuvem
        de vapor marca o lugar antes. Perto, fica visível e dá a toalhada."""

        reaction = 6
        WARN = 36

        def __init__(self, difficulty="normal"):
            super().__init__(difficulty)
            self.jump_cd = random.randint(120, 200)
            self.spot = None
            self.warn = 0

        def act(self, me, match, target):
            d = me.distance_to(target)
            want = 0.0 if d < 150 or me.windup > 0 else 0.75
            me.cloak += (want - me.cloak) * 0.1
            if self.warn > 0:
                self.warn -= 1
                me.steer(0, 0)
                if self.warn % 4 == 0:
                    match.burst(self.spot[0], self.spot[1] - 10, (240, 240, 246), 3, speed=1.5)
                if self.warn == 0:
                    me.x, me.y = self.spot
                    match.arena.resolve(me)
                    me.cloak = 0.0
                    me.face(target)
                    me.start_windup(14, (240, 240, 246))
                return
            if me.windup > 0:
                me.steer(0, 0)
                if me.windup == 1:
                    me.attack(match, target)
                return
            self.jump_cd -= 1
            me.steer(*self.move)
            if self.jump_cd <= 0 and d > 160:
                self.jump_cd = round(random.randint(170, 240) / self.aggression)
                a = random.uniform(0, math.tau)
                self.spot = match.arena.free_spot(target.x + math.cos(a) * 60, target.y + math.sin(a) * 60, me.radius)
                self.warn = round(self.WARN / max(0.8, self.aggression))
                match.assets.play("vapor", 0.2)
            elif d < me.weapon.reach + target.radius + 4:
                me.attack(match, target)

    class EstetiBotAI(en.TorretaAI):
        """O laser rosa da cabine: parado, gira devagar e solta a rajada onde a mira encostar."""

        COLOR = CLEPA
        BURST = 3
        TURN = 0.024

    class CadeiraAI(en.EnemyAI):
        """Anda devagar. Mira (linha rosa no chão), puxa o herói até ela e prende: enquanto preso,
        ele não anda e leva dano de pouquinho. Bater na cadeira (o preso ou os amigos) solta."""

        reaction = 8
        WINDUP = 40
        HOLD = 150
        RELEASE = 3                     # acertos que soltam o preso

        def __init__(self, difficulty="normal"):
            super().__init__(difficulty)
            self.grab_cd = 100
            self.held = None
            self.hold = 0
            self.hits = 0
            self.last_hp = None
            self.dir = (1.0, 0.0)

        def _release(self, me, match, text="SOLTOU!"):
            if self.held is not None:
                self.held.root_timer = 0
                match.popup(self.held.x, self.held.y - 70, text, (240, 240, 200))
            self.held = None
            self.grab_cd = round(220 / self.aggression)

        def act(self, me, match, target):
            hit = me.hp < (me.max_hp if self.last_hp is None else self.last_hp)
            self.last_hp = me.hp
            if self.held is not None:
                me.steer(0, 0)
                if hit:
                    self.hits += 1
                self.hold -= 1
                h = self.held
                if not h.alive_in_match or self.hits >= self.RELEASE or self.hold <= 0:
                    self._release(me, match)
                    return
                h.root(4)
                h.x += (me.x + me.facing[0] * 34 - h.x) * 0.3
                h.y += (me.y + 6 - h.y) * 0.3
                match.arena.resolve(h)
                if self.hold % 24 == 0:
                    h.take_damage(max(1, round(3 * me.damage_bonus)), me.x, me.y, attacker=me, match=match)
                    h.knock = [0.0, 0.0]
                return
            self.grab_cd -= 1
            if me.windup > 0:
                me.steer(0, 0)
                if me.windup == 1:
                    self._grab(me, match)
                return
            me.steer(*self.move)
            d = me.distance_to(target)
            if (self.grab_cd <= 0 and 70 < d < 260
                    and not match.arena.blocks_segment((me.x, me.y), (target.x, target.y))):
                self.dir = me.direction_to(target)
                me.face(target)
                frames = round(self.WINDUP / max(0.8, self.aggression))
                me.start_windup(frames, CLEPA)
                match.add_effect(en.AimLine(me.x, me.y, *self.dir, 270, frames, color=CLEPA, width=3, grow=4))
            elif d < me.weapon.reach + target.radius:
                me.attack(match, target)

        def _grab(self, me, match):
            """Quem estiver na linha é puxado e preso."""
            dx, dy = self.dir
            best, best_t = None, 999
            for p in match.alive_players:
                px, py = p.x - me.x, p.y - me.y
                t = px * dx + py * dy
                side = abs(px * dy - py * dx)
                if 0 < t < 290 and side < 34 + p.radius and t < best_t and not p.invulnerable:
                    best, best_t = p, t
            if best is None:
                self.grab_cd = round(120 / self.aggression)
                return
            self.held = best
            self.hold = self.HOLD
            self.hits = 0
            self.last_hp = me.hp
            best.pull(me.x + dx * 34, me.y + dy * 34 + 6, 10)
            best.root(self.HOLD)
            match.popup(best.x, best.y - 70, "PODE DEITAR", CLEPA_L)
            match.assets.play("cadeira", 0.5)

    class EspelhoAI(en.EnemyAI):
        """Parado. De tempos em tempos o vidro pisca rosa e sai o reflexo de um herói do grupo
        (no máximo um vivo por espelho). Quebrar o espelho antes impede."""

        reaction = 6
        WINDUP = 60

        def __init__(self, difficulty="normal"):
            super().__init__(difficulty)
            self.cd = random.randint(90, 160)
            self.copy = None

        def decide(self, me, match, target):
            self.move = (0.0, 0.0)

        def act(self, me, match, target):
            me.steer(0, 0)
            me.face(target)
            if me.windup > 0:
                if me.windup == 1:
                    self._reflect(me, match)
                return
            self.cd -= 1
            alive = self.copy is not None and self.copy.alive_in_match
            if self.cd <= 0 and not alive and match.alive_players:
                self.cd = round(random.randint(300, 400) / self.aggression)
                me.start_windup(round(self.WINDUP / max(0.8, self.aggression)), CLEPA)
                match.assets.play("espelho", 0.4)

        def _reflect(self, me, match):
            hero = random.choice(match.alive_players)
            x, y = match.arena.free_spot(me.x + random.uniform(-60, 60), me.y + 50, config.PLAYER_RADIUS + 4)
            self.copy = match.spawn_now(f"reflexo:{hero.stats.key}", x, y)
            match.burst(me.x, me.y - 30, CLEPA_L, 16, speed=4)

    class GrampeadorAI(en.EnemyAI):
        """Fica a meia distância e cospe 3 rajadas de grampos em leque (a boca abre antes).
        Depois fica RECARREGANDO de boca aberta: leva mais dano."""

        reaction = 7
        AIM = 22
        BURSTS = 3
        RELOAD = 80

        def __init__(self, difficulty="normal"):
            super().__init__(difficulty)
            self.bursts = 0
            self.reload = 0
            self.cd = random.randint(40, 90)

        def decide(self, me, match, target):
            d = me.distance_to(target)
            if match.arena.blocks_segment((me.x, me.y), (target.x, target.y)) or d > 330:
                self.move = self.chase(me, match, target.x, target.y)
            elif d < 170:
                self.move = self.chase(me, match, target.x, target.y, away=True)
            else:
                ax, ay = me.direction_to(target)
                self.move = (-ay * self.strafe * 0.6, ax * self.strafe * 0.6)

        def act(self, me, match, target):
            if self.reload > 0:
                self.reload -= 1
                me.steer(0, 0)
                if self.reload == 0:
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
            if self.cd <= 0 and me.distance_to(target) < 460 and not match.arena.blocks_segment((me.x, me.y), (target.x, target.y)):
                me.start_windup(round(self.AIM / max(0.8, self.aggression)), (226, 230, 240))

        def _fan(self, me, match, target):
            dx, dy = me.direction_to(target)
            w = me.weapon
            for a in (-0.22, 0.0, 0.22):
                c, s = math.cos(a), math.sin(a)
                match.spawn_projectile(me, w, (dx * c - dy * s, dx * s + dy * c), round(w.damage * me.damage_bonus))
            match.assets.play("grampo", 0.35)
            self.bursts += 1
            if self.bursts >= self.BURSTS:
                self.bursts = 0
                self.reload = self.RELOAD
                me.vulnerability = 1.5
                match.popup(me.x, me.y - 50, "RECARREGANDO", (226, 230, 240))
            self.cd = round(30 / self.aggression) if self.bursts else 20

    class MaquinaAI(en.EnemyAI):
        """Parada. Enquanto está ligada, de tempos em tempos as luzes piscam e sai um monstro dela
        (no máximo dois dela vivos ao mesmo tempo)."""

        reaction = 6
        WINDUP = 50
        KINDS = ("mascara_argila", "mascara_argila", "seringuinha")

        def __init__(self, difficulty="normal"):
            super().__init__(difficulty)
            self.cd = random.randint(120, 220)
            self.made = []

        def decide(self, me, match, target):
            self.move = (0.0, 0.0)

        def act(self, me, match, target):
            me.steer(0, 0)
            self.made = [e for e in self.made if e.alive_in_match]
            if me.windup > 0:
                if me.windup == 1:
                    x, y = match.arena.free_spot(me.x + random.uniform(-50, 50), me.y + 60, config.PLAYER_RADIUS + 4)
                    self.made.append(match.spawn_now(random.choice(self.KINDS), x, y))
                return
            self.cd -= 1
            if self.cd <= 0 and len(self.made) < 2:
                self.cd = round(random.randint(260, 340) / self.aggression)
                me.start_windup(self.WINDUP, CACO)

    class CaboAI(en.EnemyAI):
        """Só pulsa: quem corta os três tira o brilho do chefe."""

        def decide(self, me, match, target):
            self.move = (0.0, 0.0)

        def act(self, me, match, target):
            me.steer(0, 0)
            if match.frame % 10 == 0:
                match.particles.append(Particle(me.x + random.uniform(-6, 6), me.y - 20, 0, -0.8, CACO, 18, 3))

    class DaiwoneAI(en.EnemyAI):
        """Foge de quem chega perto e, de tempos em tempos, para e digita (DIGITANDO... em cima
        dela). Se terminar, manda o "oi sumido" para um herói. Apanhar enquanto digita cancela.
        No 3º acerto ela solta uma fala e vai embora."""

        reaction = 5
        TYPE = 80

        def __init__(self, difficulty="normal"):
            super().__init__(difficulty)
            self.cd = random.randint(70, 120)
            self.typing = 0
            self.hits = 0
            self.last_hp = None
            self.leaving = 0

        def decide(self, me, match, target):
            d = me.distance_to(target)
            if d < 240:
                self.move = self.chase(me, match, target.x, target.y, away=True)
            elif d > 380:
                self.move = self.chase(me, match, target.x, target.y)
            else:
                ax, ay = me.direction_to(target)
                self.move = (-ay * self.strafe * 0.8, ax * self.strafe * 0.8)

        def update(self, me, match):
            if self.leaving:
                self._leave(me, match)
                return
            super().update(me, match)

        def act(self, me, match, target):
            hit = me.hp < (me.max_hp if self.last_hp is None else self.last_hp)
            self.last_hp = me.hp
            if hit:
                self.hits += 1
                if self.hits >= DAIWONE_HITS:
                    self.flee(me, match, me.last_attacker)
                    return
                if self.typing > 0:
                    self.typing = 0
                    me.phase_label = ""
                    match.popup(me.x, me.y - 50, "CANCELOU!", CLEPA_L)
                    self.cd = round(150 / self.aggression)
            if self.typing > 0:
                me.steer(0, 0)
                self.typing -= 1
                if self.typing == 0:
                    me.phase_label = ""
                    victims = match.alive_players
                    if victims:
                        match.add_notice(Notice(random.choice(victims)))
                        match.assets.play("notificacao", 0.6)
                    self.cd = round(random.randint(240, 320) / self.aggression)
                return
            self.cd -= 1
            me.steer(*self.move)
            if self.cd <= 0:
                self.typing = round(self.TYPE / max(0.8, self.aggression))
                me.start_windup(self.typing, CLEPA)
                me.phase_label = "DIGITANDO..."
                match.assets.play("teclado", 0.25)

        def flee(self, me, match, killer=None):
            """Vai embora (nunca morre): a fala, as almas para quem deu o último acerto e some."""
            if self.leaving:
                return
            self.leaving = 70
            me.phase_label = ""
            me.windup = 0
            me.invulnerable_timer = 999
            match.popup(me.x, me.y - 60, random.choice(DAIWONE_LINES), CLEPA_L)
            if killer is not None and killer in match.players:
                match.run.earn(killer.slot, DAIWONE_SOULS)
                match.popup(killer.x, killer.y - 70, f"+{DAIWONE_SOULS} ALMAS", killer.color)
                match.assets.play("alma", 0.4)

        def _leave(self, me, match):
            self.leaving -= 1
            room = match.arena.room
            exit_x = room.x if me.x < room.centerx else room.right
            me.steer(1.0 if exit_x > me.x else -1.0, 0.0)
            me.cloak = min(1.0, me.cloak + 0.02)
            if self.leaving % 5 == 0:
                match.burst(me.x, me.y - 10, CLEPA_L, 2, speed=1.5)
            if self.leaving <= 0:
                match.vanish(me)

    return {"mascara_argila": MascaraAI, "seringuinha": SeringaAI, "rolinho_jade": RolinhoAI,
            "toalha_fantasma": ToalhaAI, "esteti_bot": EstetiBotAI, "cadeira": CadeiraAI,
            "espelho_vivo": EspelhoAI, "grampeador": GrampeadorAI, "maquina": MaquinaAI, "cabo": CaboAI,
            "daiwone": DaiwoneAI}
