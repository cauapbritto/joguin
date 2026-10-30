"""Armas forjadas: a fusão do ferreiro junta as três armas do jogador numa arma nova.

A receita é a família que mais aparece nas três (corte, impacto, flecha, explosão, gelo, fogo, raio
ou alma). Com armas comuns a forjada sai no +0; com uma rara, no +1; com uma roubada, no +2 e já
encantada. Ela entra na vaga da arma rara, as duas armas do herói voltam ao +0 e ela não entra em
outra fusão. São as armas mais fortes do jogo; contra o chefão de armadura de sombra, o efeito
especial vale metade.
"""
import math
import random

import pygame

from . import config, progress
from .data import RARE_WEAPONS, WeaponStats
from .entities import Entity, Explosion, Particle, hostile

FUSION_COST = 150

# família de cada arma (a das comuns e a das raras); o que não está aqui conta como "corte"
FAMILIES = {
    "corte": ("Espada", "Faca", "Katana", "Garras", "Espadão", "Sabre", "Machado do Lenhador"),
    "impacto": ("Maça", "Capacete", "Martelo", "Notebook", "Punho Mecânico", "Corrente", "Cabo de Rede", "Cajado",
                "Teclado Mecânico", "Manopla do Exo", "Punho Corrompido"),
    "flecha": ("Arco", "Besta", "Arco de Espinhos", "Shuriken", "Estrela", "Disquete", "Bumerangue", "Rifle",
               "Pistola", "Lança", "Rifle de Plasma"),
    "explosao": ("Granada", "Canhão de Mão", "Colmeia", "Canhão de Pulso", "Drone de Bolso"),
    "gelo": ("Cristal", "Estalactites", "Bola de Neve", "Espelho de Cristal"),
    "fogo": ("Lança-chamas",),
    "raio": ("Cajado do Raio", "Cajado do Raio Supremo", "Pendrive", "Taser de Rede", "Escudo de Choque"),
    "alma": ("Orbe", "Foice", "Foice Espectral", "Lanterna das Almas", "Crânio Uivante"),
}
FAMILY_OF = {name: family for family, names in FAMILIES.items() for name in names}
FAMILY_NAMES = {"corte": "CORTE", "impacto": "IMPACTO", "flecha": "FLECHA", "explosao": "EXPLOSÃO",
                "gelo": "GELO", "fogo": "FOGO", "raio": "RAIO", "alma": "ALMA"}
# a roubada já sai encantada: o encanto que combina com a família
FAMILY_ENCHANT = {"corte": "fogo", "impacto": "raio", "flecha": "gelo", "explosao": "fogo", "gelo": "gelo",
                  "fogo": "fogo", "raio": "raio", "alma": "raio"}


def _forged(name, kind, damage, style, note, **extra):
    return WeaponStats(name, kind, damage, style=style, note=note, rare=True, forjada=True, **extra)


FORGED = {
    "lamina_solar": _forged("Lâmina Solar", "melee", 40, "solar", reach=82, cooldown=18,
                            note="Cada golpe solta uma onda de fogo que atravessa tudo; o 3º gira."),
    "martelo_trovao": _forged("Martelo do Trovão Eterno", "melee", 46, "trovao", reach=72, cooldown=30,
                              note="Raio em cada inimigo perto; o 3º golpe arremessa o martelo atrás de 3 inimigos e ele volta."),
    "arco_mil_almas": _forged("Arco das Mil Almas", "ranged", 14, "mil_almas", bullet_speed=9, cooldown=40,
                              charge=True, note="Segure e solte: 12 flechas de alma, uma em cada inimigo."),
    "canhao_vazio": _forged("Canhão do Vazio", "ranged", 40, "vazio", bullet_speed=7, cooldown=50, mag=2,
                            reload=120, close_bonus=False,
                            note="Buraco negro que puxa todo mundo por 2 s e explode no fim."),
    "coracao_inverno": _forged("Coração do Inverno", "ranged", 16, "inverno", bullet_speed=12, cooldown=14,
                               mag=12, reload=70,
                               note="Três tiros viram estátua de gelo; o próximo golpe estoura em volta."),
    "lanca_dragao": _forged("Lança do Dragão", "ranged", 20, "dragao", bullet_speed=6, cooldown=40, mag=1,
                            reload=150, close_bonus=False,
                            note="Um dragão de fogo serpenteia por 3 s queimando quem toca."),
    "cetro_tempestade": _forged("Cetro da Tempestade", "ranged", 8, "tempestade", bullet_speed=0, cooldown=6,
                                close_bonus=False,
                                note="Raio contínuo que pula em todos; segurando, fica mais forte."),
    "foice_ceifador": _forged("Foice do Ceifador", "melee", 34, "ceifador", reach=76, cooldown=16,
                              note="Cada inimigo derrotado cura 10% e dá +5% de dano (até +50%)."),
}
RECIPES = {"corte": "lamina_solar", "impacto": "martelo_trovao", "flecha": "arco_mil_almas",
           "explosao": "canhao_vazio", "gelo": "coracao_inverno", "fogo": "lanca_dragao",
           "raio": "cetro_tempestade", "alma": "foice_ceifador"}
RARE_WEAPONS.update(FORGED)          # entram na vaga da rara (e no salvo) como as do baú


def family(weapon):
    return FAMILY_OF.get(weapon.name, "corte")


def recipe(weapons):
    """A forjada que sai destas armas: (chave, nível inicial, encanto). A família que mais aparece
    decide; no empate, vale a da arma mais rara (a rara do baú vem por último na lista)."""
    count = {}
    for w in weapons:
        count[family(w)] = count.get(family(w), 0) + 1
    rank = lambda w: (count[family(w)], 2 if w.roubada else 1 if w.rare else 0)
    best = family(max(weapons, key=rank))
    if any(w.roubada for w in weapons):
        return RECIPES[best], 2, FAMILY_ENCHANT[best]
    return RECIPES[best], 1 if any(w.rare for w in weapons) else 0, None


def discovered():
    return set(progress.load().get("forjadas", []))


def discover(key):
    data = progress.load()
    known = set(data.get("forjadas", []))
    if key not in known:
        data["forjadas"] = sorted(known | {key})
        progress.save(data)


def special(target, match):
    """Quanto do efeito especial vale neste alvo (o chefão de armadura de sombra leva metade)."""
    if target is getattr(match, "boss", None) and target.vulnerability < 1:
        return 0.5
    return 1.0


# ─────────────────────────────────────────────
#  Armas de perto (chamado a cada golpe)
# ─────────────────────────────────────────────
def on_swing(fighter, weapon, match, hits, damage):
    style = weapon.style
    if style == "solar":
        fighter.forged_count += 1
        from .projectiles import projectile_class
        fx, fy = fighter.facing
        wave = projectile_class("onda_solar")(fighter, weapon, fighter.x + fx * 20, fighter.y - 8 + fy * 20,
                                              fx, fy, 10, round(damage * 0.6))
        match.bullets.append(wave)
        if fighter.forged_count % 3 == 0:            # golpe giratório: acerta todo mundo em volta
            for other in match.opponents_of(fighter):
                if other.alive_in_match and other not in hits and fighter.distance_to(other) < weapon.reach + 40:
                    other.take_damage(damage, fighter.x, fighter.y, attacker=fighter, match=match)
            for k in range(16):
                a = k * math.tau / 16
                match.particles.append(Particle(fighter.x + math.cos(a) * 30, fighter.y - 10 + math.sin(a) * 18,
                                                math.cos(a) * 4, math.sin(a) * 3, (255, 190, 80), 16, 4))
    elif style == "trovao":
        from .projectiles import LightningArc
        fighter.forged_count += 1
        if fighter.forged_count % 3 == 0 and not any(getattr(b.weapon, "style", "") == "trovao" and
                                                     b.owner is fighter for b in match.bullets):
            from .projectiles import projectile_class      # o 3º golpe arremessa o martelo, que volta
            fx, fy = fighter.facing
            hammer = projectile_class("martelo_trovao")(fighter, weapon, fighter.x + fx * 24, fighter.y - 10 + fy * 24,
                                                        fx, fy, 14, round(damage * 0.8))
            hammer.pick_targets(match)
            match.bullets.append(hammer)
            match.popup(fighter.x, fighter.y - 70, "ARREMESSO!", (246, 214, 70))
        for other in match.opponents_of(fighter):
            if other.alive_in_match and fighter.distance_to(other) < 230:
                k = special(other, match)
                if other.take_damage(round(24 * k), attacker=fighter, match=match):
                    other.stun(round(30 * k))
                match.add_effect(LightningArc([(other.x + random.uniform(-20, 20), other.y - 240),
                                               (other.x, other.y - 40), (other.x, other.y)]))
        match.camera.shake(6)
        match.dust(fighter.x + fighter.facing[0] * 30, fighter.y + 14, 10)
        match.assets.play("explosion", 0.3)
    elif style == "ceifador":
        boss = getattr(match, "boss", None)
        if boss is not None and boss in hits and boss.vulnerability < 1:
            boss.vulnerability = 1.0             # o golpe arranca a armadura de sombra (até ela voltar)
            match.popup(boss.x, boss.y - 100, "ARMADURA ARRANCADA", (200, 150, 250))


def on_kill(attacker, victim, match):
    """Foice do Ceifador na mão: o inimigo derrotado cura e dá dano até o fim da masmorra."""
    if match is None or getattr(attacker.weapon, "style", "") != "ceifador":
        return
    attacker.hp = min(attacker.max_hp, attacker.hp + round(attacker.max_hp * 0.1))
    attacker.reaper = min(0.5, attacker.reaper + 0.05)
    match.popup(attacker.x, attacker.y - 70, f"+{round(attacker.reaper * 100)}% DANO", (200, 150, 250))
    for _ in range(6):
        match.particles.append(Particle(victim.x, victim.y - 20, (attacker.x - victim.x) / 20,
                                        (attacker.y - victim.y) / 20, (200, 170, 255), 20, 3))


# ─────────────────────────────────────────────
#  Projéteis
# ─────────────────────────────────────────────
def _make_projectiles():
    from .projectiles import LightningArc, Orb, Projectile

    class SoulArrow(Orb):
        """Flecha de alma do Arco das Mil Almas: persegue o seu inimigo."""
        TURN = 0.16
        LIFE = 110

        @classmethod
        def launch(cls, match, owner, weapon, direction, damage, target=None, power=1.0, explosive=False):
            foes = sorted((f for f in match.opponents_of(owner) if f.alive_in_match), key=owner.distance_to)
            n = 12 if power >= 1 else 4 + round(8 * power)
            base = math.atan2(direction[1], direction[0])
            out = []
            for k in range(n):
                a = base + (k - (n - 1) / 2) * 0.16
                t = foes[k % len(foes)] if foes else None
                p = cls(owner, weapon, owner.x + math.cos(a) * 18, owner.y + math.sin(a) * 18 - 4,
                        math.cos(a), math.sin(a), weapon.bullet_speed, damage, t, power)
                out.append(p)
            match.assets.play("arco", 0.4)
            return out

        def draw(self, surf, camera):
            sx, sy = round(self.x - camera.x), round(self.y - camera.y)
            ang = math.atan2(self.vy, self.vx)
            tail = (sx - math.cos(ang) * 12, sy - math.sin(ang) * 12)
            pygame.draw.line(surf, (120, 90, 200), tail, (sx, sy), 4)
            pygame.draw.line(surf, (230, 214, 255), tail, (sx, sy), 2)
            pygame.draw.circle(surf, (255, 255, 255), (sx, sy), 2)

    class VoidShot(Projectile):
        """Canhão do Vazio: a bala vira um buraco negro onde para."""
        LIFE = 40

        def survives_hit(self):
            return False

        def _open(self, match):
            if not getattr(self, "opened", False):
                self.opened = True
                match.add_effect(VoidHole(self.owner, self.x, self.y, self.damage))

        def on_hit(self, target, match):
            self._open(match)

        def on_wall(self, wall, match):
            self._open(match)
            return False

        def update(self, match):
            super().update(match)
            if self.age >= self.LIFE:
                self.alive = False
                self._open(match)

        def draw(self, surf, camera):
            sx, sy = round(self.x - camera.x), round(self.y - camera.y)
            pygame.draw.circle(surf, (160, 90, 240), (sx, sy), 9)
            pygame.draw.circle(surf, (10, 4, 16), (sx, sy), 6)

    class IceHeart(Projectile):
        """Coração do Inverno: três tiros congelam; o próximo estoura a estátua."""

        def on_hit(self, target, match):
            if target.frozen_timer > 0:
                target.frozen_timer = target.stun_timer = 0
                match.add_effect(Explosion(self.owner, target.x, target.y, round(40 * special(target, match)), 120))
                match.burst(target.x, target.y - 20, (200, 236, 250), 30, speed=6)
                match.popup(target.x, target.y - 80, "ESTOUROU", (200, 236, 250))
                return
            target.ice_stacks = getattr(target, "ice_stacks", 0) + 1
            target.slow(30)
            if target.ice_stacks >= 3:
                target.ice_stacks = 0
                if target.freeze(round(2.5 * config.FPS * special(target, match))):
                    match.popup(target.x, target.y - 80, "ESTÁTUA DE GELO", (200, 236, 250))

        def draw(self, surf, camera):
            sx, sy = round(self.x - camera.x), round(self.y - camera.y)
            pts = [(sx, sy - 6), (sx + 5, sy), (sx, sy + 6), (sx - 5, sy)]
            pygame.draw.polygon(surf, (120, 190, 240), pts)
            pygame.draw.polygon(surf, (240, 250, 255), [(sx, sy - 3), (sx + 2, sy), (sx, sy + 3), (sx - 2, sy)])

    class Dragon(Projectile):
        """Lança do Dragão: um dragão de fogo que serpenteia pela arena por 3 s."""
        ghost = True
        LIFE = 3 * config.FPS

        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.body = []
            self.radius = 14

        def survives_hit(self):
            return True

        def on_wall(self, wall, match):
            return True

        def on_hit(self, target, match):
            target.burn(self.owner, max(1, round(5 * special(target, match))), 2 * config.FPS)

        def update(self, match):
            foes = [f for f in match.opponents_of(self.owner) if f.alive_in_match]
            speed = math.hypot(self.vx, self.vy) or 6
            if foes:
                t = min(foes, key=self.distance_to)
                dx, dy = t.x - self.x, t.y - 10 - self.y
                d = math.hypot(dx, dy) or 1
                wiggle = math.sin(self.age * 0.25) * 0.8
                tx, ty = dx / d - dy / d * wiggle, dy / d + dx / d * wiggle
                self.vx += (tx * speed - self.vx) * 0.08
                self.vy += (ty * speed - self.vy) * 0.08
                k = speed / (math.hypot(self.vx, self.vy) or 1)
                self.vx, self.vy = self.vx * k, self.vy * k
            if self.age % 30 == 0:
                self.hit.clear()                  # volta a queimar quem ainda está no caminho
            self.body.insert(0, (self.x, self.y))
            del self.body[14:]
            super().update(match)
            self.x = max(10, min(match.arena.width - 10, self.x))
            self.y = max(10, min(match.arena.height - 10, self.y))
            self.alive = self.age < self.LIFE
            if self.age % 2 == 0:
                match.particles.append(Particle(self.x, self.y, random.uniform(-0.5, 0.5), -0.8,
                                                random.choice(((255, 140, 40), (255, 210, 90))), 14, 3))

        def draw(self, surf, camera):
            from .rare_fx import glow
            body = list(reversed(self.body))
            g = glow(18, (255, 110, 30), 0.35)
            for x, y in body[::3]:                    # o corpo em brasa ilumina o chão
                surf.blit(g, g.get_rect(center=(round(x - camera.x), round(y - camera.y))),
                          special_flags=pygame.BLEND_ADD)
            for i, (x, y) in enumerate(body):
                r = 4 + round(8 * (i + 1) / max(1, len(body)))
                sx, sy = round(x - camera.x), round(y - camera.y)
                pygame.draw.circle(surf, (120, 24, 16), (sx, sy), r + 1)
                pygame.draw.circle(surf, (230, 90, 30) if i % 2 else (250, 150, 50), (sx, sy), r)
                surf.fill((255, 220, 140), (sx - r // 3, sy - r // 2, max(1, r // 3), max(1, r // 4)))   # escama
            sx, sy = round(self.x - camera.x), round(self.y - camera.y)
            ang = math.atan2(self.vy, self.vx)
            head = glow(26, (255, 170, 60), 0.6)
            surf.blit(head, head.get_rect(center=(sx, sy)), special_flags=pygame.BLEND_ADD)
            for side in (-1, 1):                      # chifres
                a = ang + math.pi + side * 0.6
                pygame.draw.line(surf, (255, 240, 200), (sx, sy), (sx + math.cos(a) * 13, sy + math.sin(a) * 13), 3)
            ca, sa = math.cos(ang), math.sin(ang)
            snout = [(sx + ca * 14, sy + sa * 14), (sx - sa * 7 - ca * 2, sy + ca * 7 - sa * 2),
                     (sx + sa * 7 - ca * 2, sy - ca * 7 - sa * 2)]          # focinho apontando para a frente
            pygame.draw.polygon(surf, (150, 30, 20), snout)
            pygame.draw.polygon(surf, (255, 190, 80), [((x - sx) * 0.8 + sx, (y - sy) * 0.8 + sy) for x, y in snout])
            pygame.draw.line(surf, (255, 240, 200), (sx, sy), (round(sx + ca * 10), round(sy + sa * 10)), 2)
            for side in (-1, 1):                      # olhos
                ex, ey = sx - sa * 4 * side, sy + ca * 4 * side
                surf.fill((255, 250, 210), (round(ex) - 1, round(ey) - 1, 2, 2))

    class StormBolt(Projectile):
        """Cetro da Tempestade: acerta na hora e pula entre todos os inimigos; segurando, cresce."""

        @classmethod
        def launch(cls, match, owner, weapon, direction, damage, target=None, power=1.0, explosive=False):
            proj = cls(owner, weapon, owner.x, owner.y, 0, 0, 0, damage, target)
            proj.alive = False
            if match.frame - owner.storm_last <= weapon.cooldown + 4:
                owner.storm_hold += match.frame - owner.storm_last
            else:
                owner.storm_hold = 0
            owner.storm_last = match.frame
            growth = 1 + min(1.5, owner.storm_hold / 90)
            foes = [f for f in match.opponents_of(owner) if f.alive_in_match and owner.distance_to(f) < 900]
            points = [(owner.x + direction[0] * 16, owner.y - 18)]
            last, hit = owner, []
            while foes:
                nxt = min(foes, key=last.distance_to)
                if last.distance_to(nxt) > (460 if last is owner else 300):
                    break
                foes.remove(nxt)
                hit.append(nxt)
                points.append((nxt.x, nxt.y - 20))
                last = nxt
            for f in hit:
                f.take_damage(max(1, round(damage * growth * special(f, match))), attacker=owner, match=match)
            if len(points) > 1:
                match.add_effect(LightningArc(points))
            return proj

    class ThunderHammer(Projectile):
        """Martelo do Trovão Eterno arremessado: vai girando atrás de até três inimigos, um depois do
        outro (teleguiado), cai um raio em cada um que ele bate e volta para a mão do dono, acertando
        de novo no caminho de volta. Sem ninguém por perto, vai reto e longe antes de voltar."""
        ghost = True
        sprite = "Martelo do Trovão Eterno"
        OUT = 40                 # quadros indo reto (sem alvo) antes de voltar
        TARGETS = 3              # inimigos que ele persegue, um depois do outro
        RANGE = 700              # distância do dono até o primeiro alvo
        HOP = 520                # distância de um alvo até o próximo
        CHASE = 60               # quadros perseguindo um alvo antes de desistir dele
        LIFE = 6 * config.FPS    # se não conseguir voltar, some

        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.radius = 18
            self.returning = False
            self.targets = []
            self.chase = 0

        def pick_targets(self, match):
            """A fila de alvos: o mais perto do dono (de preferência na frente) e, a partir dele, o
            mais perto de cada um."""
            o = self.owner
            foes = [f for f in match.opponents_of(o) if f.alive_in_match]
            fx, fy = o.facing

            def first(f):
                d = o.distance_to(f) or 1.0
                return d * (1.6 - 0.6 * ((f.x - o.x) * fx + (f.y - o.y) * fy) / d)
            last, reach, key = o, self.RANGE, first
            while foes and len(self.targets) < self.TARGETS:
                nxt = min(foes, key=key)
                if last.distance_to(nxt) > reach:
                    break
                foes.remove(nxt)
                self.targets.append(nxt)
                last, reach, key = nxt, self.HOP, nxt.distance_to

        def survives_hit(self):
            return True

        def on_wall(self, wall, match):
            if not self.returning and not self.targets:
                self._turn()
            return True

        def _turn(self):
            self.returning = True
            self.targets = []
            self.hit.clear()                         # na volta acerta de novo

        def on_hit(self, target, match):
            k = special(target, match)
            target.stun(round(24 * k))
            match.add_effect(LightningArc([(target.x + random.uniform(-20, 20), target.y - 240),
                                           (target.x, target.y - 40), (target.x, target.y)]))
            match.camera.shake(4)

        def _steer(self, x, y):
            dx, dy = x - self.x, y - self.y
            d = math.hypot(dx, dy) or 1
            speed = math.hypot(self.vx, self.vy) or 13
            self.vx, self.vy = dx / d * speed, dy / d * speed
            return d

        def update(self, match):
            while self.targets and (self.targets[0] in self.hit or not self.targets[0].alive_in_match
                                    or self.chase > self.CHASE):
                self.targets.pop(0)                  # acertou (ou perdeu) este: vai para o próximo
                self.chase = 0
                if not self.targets:
                    self._turn()
            if self.targets:
                t = self.targets[0]
                self.chase += 1
                self._steer(t.x, t.y - 10)
            elif not self.returning and self.age >= self.OUT:
                self._turn()
            if self.returning:
                o = self.owner
                if self._steer(o.x, o.y - 10) < 26 or o.hp <= 0:
                    self.alive = False
                    if o.hp > 0:
                        match.burst(o.x, o.y - 14, (246, 214, 70), 8, speed=3)
                    return
            super().update(match)
            if self.age > self.LIFE:
                self.alive = False
            if self.age % 3 == 0:
                match.particles.append(Particle(self.x + random.uniform(-8, 8), self.y + random.uniform(-8, 8),
                                                random.uniform(-1, 1), random.uniform(-1, 1),
                                                random.choice(((246, 214, 70), (200, 220, 255))), 10, 2))

        def draw(self, surf, camera):
            self.draw_sprite(surf, camera, angle=(self.age * 40) % 360)

    class SolarWave(Projectile):
        """Onda de fogo da Lâmina Solar: atravessa paredes e todos os inimigos."""
        ghost = True
        LIFE = 34

        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.radius = 16

        def survives_hit(self):
            return True

        def on_wall(self, wall, match):
            return True

        def on_hit(self, target, match):
            target.burn(self.owner, max(1, round(4 * special(target, match))), config.FPS)

        def update(self, match):
            super().update(match)
            if self.age > self.LIFE:
                self.alive = False
            if self.age % 2 == 0:
                match.particles.append(Particle(self.x + random.uniform(-10, 10), self.y + random.uniform(-10, 10),
                                                self.vx * 0.1, -0.6, random.choice(((255, 190, 80), (255, 120, 40))),
                                                14, 4))

        def draw(self, surf, camera):
            from .rare_fx import glow
            sx, sy = round(self.x - camera.x), round(self.y - camera.y)
            ang = math.atan2(self.vy, self.vx)
            fade = max(0.0, 1 - self.age / self.LIFE)
            g = glow(30, (255, 140, 40), 0.35 + 0.35 * fade)
            surf.blit(g, g.get_rect(center=(sx, sy)), special_flags=pygame.BLEND_ADD)
            # meia-lua de fogo: cada camada é mais fina e mais quente que a de fora
            for r, thick, color in ((20, 9, (190, 50, 20)), (18, 6, (255, 140, 40)), (17, 3, (255, 236, 170))):
                outer, inner = [], []
                for k in range(-6, 7):
                    a = ang + k * 0.2
                    bend = (1 - abs(k) / 6) * thick
                    outer.append((sx + math.cos(a) * r, sy + math.sin(a) * r))
                    inner.append((sx + math.cos(a) * (r - bend), sy + math.sin(a) * (r - bend)))
                pygame.draw.polygon(surf, color, outer + inner[::-1])

    return {"onda_solar": SolarWave, "mil_almas": SoulArrow, "vazio": VoidShot, "inverno": IceHeart, "dragao": Dragon,
            "tempestade": StormBolt, "martelo_trovao": ThunderHammer}


class VoidHole(Entity):
    """Buraco negro do Canhão do Vazio: puxa os inimigos por 2 s e explode."""

    FRAMES = 2 * config.FPS
    RADIUS = 320

    def __init__(self, owner, x, y, damage):
        super().__init__(x, y)
        self.owner = owner
        self.damage = damage
        self.age = 0

    def update(self, match):
        self.age += 1
        for f in match.fighters:
            if not hostile(self.owner, f) or not f.alive_in_match:
                continue
            d = f.distance_to(self)
            if 12 < d < self.RADIUS:
                pull = 3.2 * special(f, match) * (1 - getattr(f, "knock_resist", 0) * 0.5)
                f.knock = [(self.x - f.x) / d * pull, (self.y - f.y) / d * pull]
        if self.age % 2 == 0:
            a = random.uniform(0, math.tau)
            r = random.uniform(60, self.RADIUS * 0.6)
            match.particles.append(Particle(self.x + math.cos(a) * r, self.y + math.sin(a) * r,
                                            -math.cos(a) * r / 18, -math.sin(a) * r / 18, (150, 90, 230), 18, 3))
        if self.age >= self.FRAMES:
            self.alive = False
            match.add_effect(Explosion(self.owner, self.x, self.y, self.damage, 160))
            match.assets.play("explosion", 0.5)
            match.camera.shake(8)

    def draw(self, surf, camera):
        sx, sy = round(self.x - camera.x), round(self.y - camera.y)
        k = self.age / self.FRAMES
        r = 14 + round(10 * k) + (2 if (self.age // 3) % 2 else 0)
        pygame.draw.circle(surf, (110, 50, 190), (sx, sy), r + 8, 3)
        pygame.draw.circle(surf, (60, 20, 100), (sx, sy), r + 3)
        pygame.draw.circle(surf, (4, 0, 8), (sx, sy), r)


def register_projectiles(table):
    table.update(_make_projectiles())


def preview_text(key, known):
    w = FORGED[key]
    if key in known:
        return w.name.upper(), w.note
    return "???", "receita ainda não descoberta"

