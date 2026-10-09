"""Dados dos personagens e armas. Sem dependência de pygame (usado também pelo servidor web)."""
from dataclasses import dataclass


@dataclass(frozen=True)
class WeaponStats:
    name: str
    kind: str               # "ranged" ou "melee"
    damage: int
    bullet_speed: float = 0
    cooldown: int = 16      # frames entre ataques
    reach: int = 0          # alcance (só corpo a corpo)

    @property
    def is_melee(self):
        return self.kind == "melee"


@dataclass(frozen=True)
class CharacterStats:
    key: str                # identificador da habilidade e do sprite
    name: str
    max_hp: int
    speed: float
    color: tuple
    ability_name: str
    ability_desc: str
    weapons: tuple
    sprite: str             # prefixo dos arquivos em assets/characters


def _ranged(name, damage, speed, cooldown):
    return WeaponStats(name, "ranged", damage, bullet_speed=speed, cooldown=cooldown)


def _melee(name, damage, reach):
    return WeaponStats(name, "melee", damage, reach=reach)


CHARACTERS = (
    CharacterStats("guerreiro", "Guerreiro", 150, 3, (72, 112, 206),
                   "Investida", "Avança contra o inimigo e causa 30 de dano.",
                   (_ranged("Arco", 10, 9, 22), _melee("Espada", 22, 70)), "guerreiro"),
    CharacterStats("atirador", "Atirador", 105, 4, (70, 182, 190),
                   "Rajada", "Dispara 5 balas em leque.",
                   (_ranged("Rifle", 8, 14, 12), _melee("Faca", 16, 50)), "atirador"),
    CharacterStats("tanque", "Tanque", 230, 2, (128, 136, 150),
                   "Muralha", "Ergue uma barreira que bloqueia tiros por 4s.",
                   (_ranged("Lança", 14, 8, 34), _melee("Maça", 26, 60)), "tanque"),
    CharacterStats("ninja", "Ninja", 95, 4.2, (64, 168, 124),
                   "Shuriken", "Lança 3 shurikens de dano alto.",
                   (_ranged("Shuriken", 9, 11, 18), _melee("Katana", 19, 65)), "ninja"),
    CharacterStats("velocista", "Velocista", 115, 4.5, (236, 198, 64),
                   "Turbo", "Fica 2x mais rápido por 4s.",
                   (_ranged("Estrela", 9, 11, 14), _melee("Garras", 17, 50)), "velocista"),
    CharacterStats("aryel", "Aryel", 130, 3, (234, 132, 64),
                   "Explosão", "Solta 8 bombas em volta de si.",
                   (_ranged("Granada", 12, 8, 24), _melee("Martelo", 24, 55)), "aryel"),
    CharacterStats("fantasma", "Fantasma", 110, 4, (156, 104, 214),
                   "Teletransporte", "Some e reaparece em outro ponto da arena.",
                   (_ranged("Orbe", 10, 10, 20), _melee("Foice", 20, 60)), "fantasma"),
    CharacterStats("tita", "Titã", 180, 2, (216, 170, 66),
                   "Invulnerável", "Não recebe dano por 3s.",
                   (_ranged("Corrente", 12, 8, 32), _melee("Espadão", 24, 70)), "tita"),
)

MAX_HP = max(c.max_hp for c in CHARACTERS)
MAX_SPEED = max(c.speed for c in CHARACTERS)
MAX_DAMAGE = max(w.damage for c in CHARACTERS for w in c.weapons)


def roster_for_web():
    """Resumo dos personagens enviado ao controle do celular."""
    return [
        {
            "name": c.name,
            "color": list(c.color),
            "hp": c.max_hp,
            "speed": c.speed,
            "ability": c.ability_name,
            "ability_desc": c.ability_desc,
            "weapons": [{"name": w.name, "melee": w.is_melee, "damage": w.damage} for w in c.weapons],
        }
        for c in CHARACTERS
    ]
