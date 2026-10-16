"""Habilidades especiais. Cada personagem tem uma subclasse de Ability (polimorfismo):
o lutador só chama ``ability.use(...)`` e não precisa saber qual habilidade é."""
import math
import random
from abc import ABC, abstractmethod

from . import config
from .entities import Barrier, ExoSuit, FrostNova, Hack, Hook, ShadowBomb
from .projectiles import Basketball, Volleyball


class Ability(ABC):
    sound = "ability"
    cooldown_mult = 1.0         # habilidade forte demora mais para recarregar
    reach_mult = 1.0            # alcance do golpe corpo a corpo (passiva de alto do Cauanzera)

    def __init__(self, stats):
        self.name = stats.ability_name
        self.description = stats.ability_desc

    def use(self, user, match, target):
        match.assets.play(self.sound, 0.4)
        self.activate(user, match, target)

    @abstractmethod
    def activate(self, user, match, target):
        """Efeito da habilidade."""

    def worth_using(self, user, target, dist):
        """Dica para a CPU: vale a pena usar agora?"""
        return True

    def tick(self, user):
        """Chamado todo quadro (quase todas não precisam)."""

    def reset(self):
        """Novo round: esquece o que guardou."""


def _aim(user, target):
    if target is not None:
        dx, dy = user.direction_to(target)
        if dx or dy:
            return dx, dy
    return user.facing


def _dmg(user, base):
    """Dano da habilidade com os bônus permanentes (melhorias da campanha); no duelo é o próprio valor."""
    return round(base * user.damage_bonus)


def _fan(user, match, target, count, spread_deg, speed, damage):
    damage = _dmg(user, damage)
    dx, dy = _aim(user, target)
    base = math.atan2(dy, dx)
    for i in range(count):
        t = i / (count - 1) - 0.5 if count > 1 else 0
        a = base + math.radians(spread_deg) * t
        match.spawn_bullet(user, math.cos(a), math.sin(a), speed, damage)


class Investida(Ability):
    DAMAGE = 30

    def activate(self, user, match, target):
        user.start_charge(_aim(user, target), _dmg(user, self.DAMAGE))

    def worth_using(self, user, target, dist):
        return 100 < dist < 360


class Rajada(Ability):
    def activate(self, user, match, target):
        _fan(user, match, target, 5, 30, user.weapons[0].bullet_speed, user.stats.weapons[0].damage)

    def worth_using(self, user, target, dist):
        return dist < 420


class Muralha(Ability):
    sound = "barrier"

    def activate(self, user, match, target):
        dx, dy = _aim(user, target)
        match.add_effect(Barrier(user, user.x + dx * 44, user.y + dy * 44, dx, dy, 4 * config.FPS))

    def worth_using(self, user, target, dist):
        return dist > 160


class ShurikenTripla(Ability):
    def activate(self, user, match, target):
        _fan(user, match, target, 3, 45, user.weapons[0].bullet_speed + 2, 12)

    def worth_using(self, user, target, dist):
        return dist < 380


class Turbo(Ability):
    def activate(self, user, match, target):
        user.speed_timer = 4 * config.FPS

    def worth_using(self, user, target, dist):
        return dist > 260 or user.hp < user.max_hp * 0.4


class Explosao(Ability):
    sound = "explosion"

    def activate(self, user, match, target):
        for k in range(8):
            a = k * math.pi / 4
            match.spawn_bullet(user, math.cos(a), math.sin(a), user.weapons[0].bullet_speed, _dmg(user, 25),
                               explosive=True)

    def worth_using(self, user, target, dist):
        return dist < 220


class Teletransporte(Ability):
    def activate(self, user, match, target):
        match.burst(user.x, user.y - 16, user.stats.color, 18)
        x, y = match.arena.random_free_spot(user.radius)
        user.x, user.y = x, y
        user.vx = user.vy = 0
        user.teleport_flash = 20
        match.burst(x, y - 16, user.stats.color, 18)

    def worth_using(self, user, target, dist):
        return dist < 110 or user.hp < user.max_hp * 0.3


class Invulneravel(Ability):
    def activate(self, user, match, target):
        user.invulnerable_timer = 3 * config.FPS

    def worth_using(self, user, target, dist):
        return user.hp < user.max_hp * 0.6 and dist < 400


class Gancho(Ability):
    """Pirata: o gancho puxa o inimigo para a frente do sabre."""
    sound = "shoot"

    def activate(self, user, match, target):
        dx, dy = _aim(user, target)
        user.facing = (dx, dy)
        user.shoot_flash = 4
        match.bullets.append(Hook(user, user.x + dx * 18, user.y + dy * 18 - 4, dx, dy))

    def worth_using(self, user, target, dist):
        return 130 < dist < Hook.SPEED * Hook.RANGE_FRAMES - 30


class Nevasca(Ability):
    """Geada: onda de gelo em volta dela."""
    sound = "barrier"

    def activate(self, user, match, target):
        match.add_effect(FrostNova(user, user.x, user.y, damage=_dmg(user, 10)))

    def worth_using(self, user, target, dist):
        return dist < 170


class ChuvaSombria(Ability):
    """Aryel Corrompido: bombas sombrias caem em cima do inimigo e em volta dele."""
    sound = "ability"
    DAMAGE = 18

    def activate(self, user, match, target):
        tx, ty = (target.x, target.y) if target is not None else (user.x + user.facing[0] * 200,
                                                                  user.y + user.facing[1] * 200)
        spots = [(tx, ty)]
        for k in range(4):
            a = k * math.pi / 2 + random.uniform(-0.4, 0.4)
            r = random.uniform(70, 110)
            spots.append((tx + math.cos(a) * r, ty + math.sin(a) * r))
        for i, (x, y) in enumerate(spots):
            x, y = match.arena.free_spot(x, y, 8)
            match.add_effect(ShadowBomb(user, x, y, delay=40 + i * 4, damage=_dmg(user, self.DAMAGE), radius=50))

    def worth_using(self, user, target, dist):
        return 120 < dist < 460


def _nearest_foe(user, match, target):
    if target is not None and getattr(target, "alive_in_match", False):
        return target
    foes = [f for f in match.opponents_of(user) if f.alive_in_match]
    return min(foes, key=user.distance_to) if foes else None


class Multiesportista(Ability):
    """Cauanzera: cada vez um esporte, sempre nesta ordem — basquete (bola que passa por cima das
    paredes e não erra), vôlei (saque que quica de um inimigo para outro) e atletismo (100 metros:
    corre muito e atropela). Passiva de alto: o golpe alcança mais longe."""
    SPORTS = ("BASQUETE", "VÔLEI", "ATLETISMO")
    reach_mult = 1.1
    cooldown_mult = 1.5
    RUSH = 2 * config.FPS
    RUSH_DAMAGE = 12

    def __init__(self, stats):
        super().__init__(stats)
        self.next = 0
        self.name = self.SPORTS[0]          # o HUD mostra o próximo esporte

    @property
    def sport(self):
        return self.SPORTS[self.next]

    def reset(self):
        self.next = 0
        self.name = self.SPORTS[0]

    def activate(self, user, match, target):
        sport = self.sport
        foe = _nearest_foe(user, match, target)
        if sport == "BASQUETE":
            match.bullets.append(Basketball.throw(user, foe, _dmg(user, Basketball.DAMAGE)))
            match.popup(user.x, user.y - 80, "ARREMESSO!", (240, 150, 60))
        elif sport == "VÔLEI":
            dx, dy = user.direction_to(foe) if foe is not None else user.facing
            if not (dx or dy):
                dx, dy = user.facing
            match.bullets.append(Volleyball(user, foe, dx, dy, _dmg(user, Volleyball.DAMAGE)))
            match.popup(user.x, user.y - 80, "SAQUE!", (250, 230, 120))
        else:
            user.rush_timer = self.RUSH
            user.rush_hit = set()
            user.rush_damage = _dmg(user, self.RUSH_DAMAGE)
            match.popup(user.x, user.y - 80, "100 METROS!", (240, 240, 240))
            match.dust(user.x, user.y + 20, 8)
        self.next = (self.next + 1) % len(self.SPORTS)
        self.name = self.sport

    def worth_using(self, user, target, dist):
        sport = self.sport
        if sport == "BASQUETE":
            return dist > 120
        if sport == "VÔLEI":
            return dist < 520
        return dist < 300


class Hacker(Ability):
    """Albeguinio: abre o notebook e digita por 1s (se apanhar enquanto digita, falha); depois o
    sinal de Wi-Fi sai dele e todos os adversários ficam HACKEADOS — travados por 5s."""
    sound = "barrier"
    cooldown_mult = 2.0             # 20s
    TYPING = config.FPS
    FREEZE = 5 * config.FPS

    def activate(self, user, match, target):
        match.add_effect(Hack(user, self.TYPING, self.FREEZE))

    def worth_using(self, user, target, dist):
        # longe o bastante para digitar em paz (ou com o inimigo recarregando)
        if target is None or target.stunned:
            return False
        return dist > 260 or target.reloading


class Exoesqueleto(Ability):
    """Borba Jr: as placas de metal se montam nele. Por 6s fica maior, leva metade do dano, não é
    empurrado e o golpe arremessa longe (quem bate na parede fica tonto)."""
    sound = "barrier"
    cooldown_mult = 1.3
    FRAMES = 6 * config.FPS

    def activate(self, user, match, target):
        start_exo(user, match, self.FRAMES)

    def worth_using(self, user, target, dist):
        return dist < 300 or user.hp < user.max_hp * 0.5


def start_exo(user, match, frames):
    """Monta o exoesqueleto (duelo e futebol)."""
    user.start_exo(frames, match.assets.exo_sprites(user))
    match.add_effect(ExoSuit(user, frames))


ABILITIES = {
    "guerreiro": Investida,
    "atirador": Rajada,
    "tanque": Muralha,
    "ninja": ShurikenTripla,
    "velocista": Turbo,
    "aryel": Explosao,
    "fantasma": Teletransporte,
    "tita": Invulneravel,
    "pirata": Gancho,
    "geada": Nevasca,
    "aryel_corrompido": ChuvaSombria,
    "cauanzera": Multiesportista,
    "albeguinio": Hacker,
    "borba": Exoesqueleto,
}


class SemHabilidade(Ability):
    """Inimigos da campanha: os ataques especiais ficam na IA deles."""
    sound = None

    def use(self, user, match, target):
        self.activate(user, match, target)

    def activate(self, user, match, target):
        pass

    def worth_using(self, user, target, dist):
        return False


def create_ability(stats):
    cls = ABILITIES.get(stats.key)
    if cls is None:
        return SemHabilidade(stats)
    return cls(stats)
