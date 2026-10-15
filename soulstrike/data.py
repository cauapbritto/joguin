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
    style: str = ""         # tipo do projétil (ver projectiles.PROJECTILES); "" = tiro comum
    mag: int = 0            # tiros por pente (0 = sem limite)
    reload: int = 0         # quadros para recarregar o pente
    regen: int = 0          # armas mágicas: um tiro volta a cada tantos quadros (em vez de recarregar)
    charge: bool = False    # segurar para tensionar (arco)
    note: str = ""          # o que a arma tem de especial (mostrado na seleção e no celular)
    close_bonus: bool = True  # tiro de perto causa mais dano (o lança-chamas não: ele já é de perto)
    rare: bool = False      # arma rara do baú da campanha

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


def _ranged(name, damage, speed, cooldown, style="", mag=0, reload=0, regen=0, charge=False, note="", **extra):
    return WeaponStats(name, "ranged", damage, bullet_speed=speed, cooldown=cooldown, style=style, mag=mag,
                       reload=reload, regen=regen, charge=charge, note=note, **extra)


def _melee(name, damage, reach):
    return WeaponStats(name, "melee", damage, reach=reach)


CHARACTERS = (
    CharacterStats("guerreiro", "Guerreiro", 150, 3, (72, 112, 206),
                   "Investida", "Avança contra o inimigo e causa 30 de dano.",
                   (_ranged("Arco", 10, 9, 22, "flecha", mag=6, reload=80, charge=True,
                            note="Segure para tensionar: a flecha tensa atravessa."), _melee("Espada", 22, 70)), "guerreiro"),
    CharacterStats("atirador", "Atirador", 105, 4, (70, 182, 190),
                   "Rajada", "Dispara 5 balas em leque.",
                   (_ranged("Rifle", 8, 14, 12, "bala", mag=18, reload=65,
                            note="Pente grande e tiro rápido."), _melee("Faca", 16, 50)), "atirador"),
    CharacterStats("tanque", "Tanque", 230, 2, (128, 136, 150),
                   "Muralha", "Ergue uma barreira que bloqueia tiros por 4s.",
                   (_ranged("Lança", 14, 9, 34, "lanca", mag=4, reload=70,
                            note="Arremesso que atravessa e empurra."), _melee("Maça", 26, 60)), "tanque"),
    CharacterStats("ninja", "Ninja", 95, 4.2, (64, 168, 124),
                   "Shuriken", "Lança 3 shurikens de dano alto.",
                   (_ranged("Shuriken", 9, 11, 18, "shuriken", mag=10, reload=50,
                            note="Gira e ricocheteia na parede."), _melee("Katana", 19, 65)), "ninja"),
    CharacterStats("velocista", "Velocista", 115, 4.5, (236, 198, 64),
                   "Turbo", "Fica 2x mais rápido por 4s.",
                   (_ranged("Estrela", 9, 11, 14, "estrela", mag=12, reload=55,
                            note="Acertar dá embalo (mais velocidade)."), _melee("Garras", 17, 50)), "velocista"),
    CharacterStats("aryel", "Aryel", 130, 3, (234, 132, 64),
                   "Explosão", "Solta 8 bombas em volta de si.",
                   (_ranged("Granada", 12, 9, 24, "granada", mag=5, reload=90,
                            note="Vai por cima das paredes e explode."), _melee("Martelo", 24, 55)), "aryel"),
    CharacterStats("fantasma", "Fantasma", 110, 4, (156, 104, 214),
                   "Teletransporte", "Some e reaparece em outro ponto da arena.",
                   (_ranged("Orbe", 10, 7, 20, "orbe", mag=6, regen=45,
                            note="Persegue o alvo e atravessa paredes."), _melee("Foice", 20, 60)), "fantasma"),
    CharacterStats("tita", "Titã", 180, 2, (216, 170, 66),
                   "Invulnerável", "Não recebe dano por 3s.",
                   (_ranged("Corrente", 12, 10, 36, "corrente", mag=3, reload=75,
                            note="Bola de ferro: empurra e atordoa."), _melee("Espadão", 24, 70)), "tita"),
    CharacterStats("pirata", "Pirata", 140, 3.3, (186, 58, 70),
                   "Gancho", "Lança um gancho que puxa o inimigo para perto e o atordoa.",
                   (_ranged("Pistola", 16, 13, 30, "pistola", mag=2, reload=85,
                            note="Dois tiros fortes; recarga lenta."), _melee("Sabre", 21, 65)), "pirata"),
    CharacterStats("geada", "Geada", 100, 3.8, (150, 212, 240),
                   "Nevasca", "Onda de gelo: dano em volta e o inimigo fica lento por 2,5s.",
                   (_ranged("Cristal", 9, 12, 16, "cristal", mag=8, regen=32,
                            note="Deixa o alvo lento."), _melee("Cajado", 17, 72)), "geada"),
    # liberado ao zerar a campanha (fica sempre por último, para os índices não mudarem)
    CharacterStats("aryel_corrompido", "Aryel Corrompido", 135, 3.2, (150, 70, 210),
                   "Chuva Sombria", "Faz chover 5 bombas sombrias em cima e em volta do inimigo.",
                   (_ranged("Granada", 12, 9, 24, "granada", mag=5, reload=90,
                            note="Vai por cima das paredes e explode."), _melee("Martelo", 24, 55)), "aryel"),
)
# Armas raras: o baú escondido no acampamento da campanha dá uma para cada jogador (vira a 3ª arma)
RARE_WEAPONS = {
    "besta": _ranged("Besta", 22, 15, 40, "virote", mag=4, reload=90, rare=True,
                     note="Virote pesado que atravessa dois inimigos."),
    "lanca_chamas": _ranged("Lança-chamas", 4, 6.5, 4, "chama", mag=45, reload=110, rare=True,
                            close_bonus=False, note="Jato de fogo curto que atravessa todo mundo."),
    "bumerangue": _ranged("Bumerangue", 15, 11, 28, "bumerangue", mag=2, reload=60, rare=True,
                          note="Vai e volta, acertando na ida e na volta."),
    "cajado_raio": _ranged("Cajado do Raio", 14, 0, 34, "raio", mag=5, regen=55, rare=True,
                           note="Raio na hora, que pula para mais dois inimigos."),
    "canhao": _ranged("Canhão de Mão", 26, 9, 50, "canhao", mag=2, reload=110, rare=True,
                      note="Bala de canhão que explode e empurra."),
}

UNLOCKABLE = "aryel_corrompido"
SHADOW_CHARACTERS = {"aryel_corrompido"}     # usam a versão sombria do sprite (campo "sprite")


def roster():
    """Personagens que dá para escolher agora (o Aryel Corrompido só depois de zerar a campanha)."""
    from . import progress
    if progress.campaign_cleared():
        return CHARACTERS
    return tuple(c for c in CHARACTERS if c.key != UNLOCKABLE)

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
            "weapons": [{"name": w.name, "melee": w.is_melee, "damage": w.damage, "mag": w.mag,
                         "note": w.note} for w in c.weapons],
        }
        for c in roster()
    ]
