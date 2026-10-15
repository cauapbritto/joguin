"""Melhorias da campanha: no fim de cada fase, cada jogador escolhe 1 de 3 (e elas se acumulam).

Cada melhoria é uma subclasse de Upgrade (polimorfismo): a campanha só chama
``upgrade.apply(lutador)`` no começo de cada fase, sem saber qual é.
"""
import random
from abc import ABC, abstractmethod


class Upgrade(ABC):
    key = ""
    name = ""
    description = ""
    color = (228, 170, 76)
    icon = ""                 # desenho 7x7 (ver ICONS)

    @abstractmethod
    def apply(self, fighter):
        """Aplica o efeito no lutador (chamado no começo de cada fase)."""


class Vida(Upgrade):
    key, name, description, color = "vida", "VIDA", "+25 de vida máxima.", (214, 64, 64)

    def apply(self, fighter):
        fighter.max_hp += 25


class Dano(Upgrade):
    key, name, description, color = "dano", "DANO", "+15% de dano em tudo.", (234, 104, 44)

    def apply(self, fighter):
        fighter.damage_bonus *= 1.15


class Recarga(Upgrade):
    key, name, description, color = "recarga", "RECARGA", "A habilidade volta 25% mais rápido.", (110, 180, 246)

    def apply(self, fighter):
        fighter.cd_mult *= 0.75


class Velocidade(Upgrade):
    key, name, description, color = "velocidade", "VELOCIDADE", "+10% de velocidade.", (236, 198, 64)

    def apply(self, fighter):
        fighter.speed_mult *= 1.10


class Perfurar(Upgrade):
    key, name, description, color = "perfurar", "PERFURAR", "Seus tiros atravessam 1 inimigo a mais.", (200, 210, 220)

    def apply(self, fighter):
        fighter.pierce += 1


class Esquiva(Upgrade):
    key, name, description, color = "esquiva", "ESQUIVA", "A esquiva recarrega 30% mais rápido.", (120, 200, 110)

    def apply(self, fighter):
        fighter.dash_cd_mult *= 0.7


class Vampirismo(Upgrade):
    key, name, description, color = "vampirismo", "VAMPIRISMO", "5% do dano que você causa vira vida.", (176, 60, 110)

    def apply(self, fighter):
        fighter.lifesteal += 0.05


class Escudo(Upgrade):
    key, name, description, color = "escudo", "ESCUDO", "Começa cada fase com 40 de escudo.", (150, 212, 240)

    def apply(self, fighter):
        fighter.shield += 40


class Municao(Upgrade):
    key, name, description, color = ("municao", "MUNIÇÃO", "Pente 50% maior e recarga 30% mais rápida.",
                                     (226, 176, 74))

    def apply(self, fighter):
        fighter.ammo_mult *= 1.5
        fighter.reload_mult *= 0.7
        fighter.clips.clear()                 # pentes novos, já no tamanho maior


UPGRADES = {cls.key: cls() for cls in (Vida, Dano, Recarga, Velocidade, Perfurar, Esquiva, Vampirismo, Escudo,
                                       Municao)}

# desenho 7x7 de cada ícone ("#" = cor da melhoria, "+" = claro)
ICONS = {
    "vida": [".##.##.", "#######", "##+####", "#######", ".#####.", "..###..", "...#..."],
    "dano": ["...#...", "..##...", "..###..", ".##+#..", ".#++##.", ".##+##.", "..###.."],
    "recarga": ["..###..", ".#...#.", "#..#..#", "#..##.#", "#.....#", ".#...#.", "..###.."],
    "velocidade": ["....##.", "...##..", "..####.", ".####..", "..##...", ".##....", "##....."],
    "perfurar": ["...#...", "...##..", "#######", "###+###", "#######", "...##..", "...#..."],
    "esquiva": ["...##..", "..##...", ".##....", "#######", ".##....", "..##...", "...##.."],
    "vampirismo": [".#...#.", "##...##", "#######", "##+#+##", ".#####.", "..#.#..", "..#.#.."],
    "escudo": ["#######", "#+++++#", "#+###+#", "#+###+#", ".#+#+#.", "..#+#..", "...#..."],
    "municao": ["..#.#..", ".##.##.", ".##.##.", ".+#.+#.", ".##.##.", ".##.##.", "###.###"],
}


def choices(owned, rng=random, count=3):
    """Três opções diferentes para um jogador (repetir melhoria vale: elas se acumulam)."""
    keys = list(UPGRADES)
    # quem já tem muita coisa de um tipo vê um pouco menos dele
    weights = [1.0 / (1 + owned.count(k)) for k in keys]
    picked = []
    while len(picked) < count and keys:
        k = rng.choices(keys, weights=weights)[0]
        i = keys.index(k)
        keys.pop(i)
        weights.pop(i)
        picked.append(k)
    return picked


def apply_all(fighter, keys):
    for k in keys:
        UPGRADES[k].apply(fighter)
