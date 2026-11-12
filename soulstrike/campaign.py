"""Modo campanha: 6 fases cooperativas (1 a 4 jogadores) em dois capítulos, contra criaturas, almas
corrompidas e, no capítulo 2, a Patrulha Cinza dentro da Lag Lobby.

CampaignRun guarda o que passa de uma fase para a outra (melhorias, vida, continues, tempo).
CampaignMatch é uma fase: ondas de inimigos que saem de portais, até a fase acabar.
"""
import copy
import math
import random
from dataclasses import dataclass

import pygame

from . import config, energia, hud, rumble, segredos, theme
from .ai import FighterAI
from .entities import Particle, Pickup
from .enemies import BIG_KINDS, CREATURES, SHADOW_AURA, SMOKE, Portal, spawn_enemy
from .matches import Match, Result, _separate
from .net.remote import hub
from .ui import darken
from .data import RARE_WEAPONS, common_weapon, duel_arsenal, rarity_color
from .armario import RACK_SIZE, token_of, weapon_of
from .dungeon import ExitDoor, GroundWeapon, PhasePortal, StartButton
from .hazards import make_hazard
from .market import CURSE_HP, CURSE_SPEED, CURSES, ENCHANTS, MAX_LEVEL, MAX_REROLLS, SOUL_COLOR, soul_split
from .upgrades import apply_all

PLAYERS, ENEMIES = 0, 1
CONTINUES = 3
PHASE_HEAL = 0.35             # entre uma fase e outra, recupera esse tanto da vida
REVIVE_FRAMES = 120           # tempo perto de um companheiro caído para levantá-lo
REVIVE_RADIUS = 56
REVIVE_HP = 0.4
HIGH_FIVE_FRAMES = 90         # segredo: depois de levantar, a dupla tem 1,5 s para bater a mão
PANIC_FRAMES = 150            # segredo: o último da onda foge tremendo esse tanto
PANIC_CROWD = 3               # ... se a onda veio com pelo menos esse tanto (sobrou um de muitos)
STILL_KINDS = ("torreta", "daiwone")   # esses não fogem (parados ou nem lutam)
CONTINUE_HP = 0.5
LAST_BREATH_FRAMES = 90       # invencível depois do último fôlego (campanha solo)
LEASH_X, LEASH_Y = 1500, 700  # quão longe os jogadores podem ficar uns dos outros (cabe na câmera a 50%)
LEASH_PULL_FRAMES = 3 * config.FPS  # forçando o limite por tanto tempo: aparece ao lado do grupo
INTRO_FRAMES = 150
BETWEEN_FRAMES = 110
BANNER_FRAMES = 100             # quanto tempo uma faixa de luta (VALENDO!) fica na tela
CLEAR_FRAMES = 200
DOWN_FRAMES = 150
GAMEOVER_FRAMES = 220
CORPSE_FRAMES = 80
CORPSE_FADE = 32              # últimos quadros do corpo: vai sumindo
SOLO_DAMAGE = 0.85
WEAPON_DROP = 0.04             # chance de um inimigo comum derrubar a arma de outro herói
ELITE_WEAPON_DROP = 0.4       # ... e de um elite (golem, sombra)
MAX_GROUND = 8                # armas no chão ao mesmo tempo (a mais velha some)

@dataclass(frozen=True)
class Level:
    """Uma dificuldade da campanha."""
    hp: float                 # vida dos inimigos
    dmg: float                # dano dos inimigos
    crowd: float = 0.5        # inimigos comuns a mais por jogador a mais (0.5 = +50%)
    elites: int = 0           # elites a mais em cada onda que já tem elite
    orbs: float = 1.0         # orbes de energia que caem
    regen: float = 0.0        # energia que volta sozinha por segundo (só no Fácil)
    affix: float = 0.0        # chance de um inimigo vir com poder extra (blindado, veloz, explosivo)
    revive: float = 1.0       # quanto mais demora levantar quem caiu
    revive_once: bool = False  # cada um só é levantado uma vez por masmorra
    continues: int = 3
    phase_heal: float = 0.35  # vida que volta entre uma fase e outra
    price: float = 1.0        # preço da loja e do ferreiro
    enrage: float = 0.2       # vida em que o chefão fica furioso


# dificuldades da campanha (Ibrahin e Borba: piadas internas, cada uma mais difícil)
LEVELS = {
    "facil": Level(0.75, 0.7, orbs=1.5, regen=2.0),
    "normal": Level(1.0, 1.0),
    "dificil": Level(1.4, 1.35, crowd=0.65, elites=1, orbs=0.75),
    "ibrahim": Level(1.9, 1.6, crowd=0.75, elites=1, orbs=0.55, affix=0.25, revive=2.0, continues=1,
                     price=1.25, enrage=0.3),
    "borba": Level(2.5, 2.0, crowd=0.85, elites=2, orbs=0.4, affix=0.5, revive=2.0, revive_once=True,
                   continues=1, phase_heal=0.0, price=1.25, enrage=0.5),
}
# (vida dos inimigos, dano dos inimigos)
DIFFICULTY = {k: (v.hp, v.dmg) for k, v in LEVELS.items()}
ORB_CHANCE = 0.35             # inimigo comum: chance de soltar um orbe de energia
ELITE_ORBS = (3, 5)
BOSS_ORBS = 18
AFFIXES = {                   # poder extra (Ibrahin e Borba): brilho em volta de quem tem
    "blindado": ("BLINDADO", (150, 212, 240)),
    "veloz": ("VELOZ", (236, 198, 64)),
    "explosivo": ("EXPLOSIVO", (240, 96, 40)),
}
AFFIX_EXPLOSION = 22          # dano da explosão do explosivo ao morrer (antes do dano da dificuldade)


@dataclass(frozen=True)
class Dungeon:
    """Uma masmorra (sala de batalha) da fase."""
    map_key: str
    name: str
    starts: tuple             # onde cada jogador entra
    facing: tuple
    waves: tuple              # cada onda: ((tipo, quantidade), ...)
    exit_spot: tuple          # onde aparece a porta de volta (ou o portal, na última)
    boss_spot: tuple = None
    boss: str = "aryel"       # qual chefão sai no "chefe" (boss.BOSSES)
    hazard: str = None        # perigo da sala: "laser" (no chão) ou "vento" (empurra), em hazards.py
    daiwone: bool = False     # capítulo 3: a Daiwone aparece uma vez no meio da 1ª onda


@dataclass(frozen=True)
class Phase:
    """Uma fase: um mapa só (mapa_fase), com a abertura, três salas de luta e a sala de recompensas
    ligadas por corredores, tudo a pé, como no Soul Knight.

    ``dungeons``: a masmorra 1 (em cima da abertura) e a final (portal da próxima fase ou o chefe);
    ``middle``: a sala de luta do meio, que leva à sala de recompensas."""
    key: str
    name: str
    theme: str                # cenário do acampamento (abertura, recompensa e corredores)
    dungeons: tuple
    chapter: int = 1          # capítulo 1: Templo Gelado; capítulo 2: Lag Lobby

    @property
    def middle(self):
        return MIDDLE[self.key]


LEFT = ((180, 640), (180, 760), (260, 640), (260, 760))
LEFT_CELLS = ((110, 540), (110, 660), (170, 540), (170, 660))
BOTTOM = ((740, 1090), (860, 1090), (680, 1100), (920, 1100))

PHASES = (
    Phase("floresta", "FLORESTA SOMBRIA", "floresta", (
        Dungeon("floresta", "CLAREIRA SOMBRIA", LEFT, (1.0, 0.0),
                ((("diabrete", 5),),
                 (("diabrete", 4), ("esqueleto", 2))),
                exit_spot=(1840, 700)),
        Dungeon("floresta_ruinas", "RUÍNAS DA FLORESTA", LEFT, (1.0, 0.0),
                ((("diabrete", 3), ("esqueleto", 2)),
                 (("sombra:velocista", 1), ("diabrete", 3))),
                exit_spot=(1000, 700)),
    )),
    Phase("calabouco", "CALABOUÇO DAS ALMAS", "calabouco", (
        Dungeon("calabouco", "CORREDORES", LEFT_CELLS, (1.0, 0.0),
                ((("esqueleto", 3), ("diabrete", 3)),
                 (("golem", 1), ("esqueleto", 2), ("diabrete", 2))),
                exit_spot=(1450, 600)),
        Dungeon("calabouco_celas", "CELAS DAS ALMAS", LEFT_CELLS, (1.0, 0.0),
                ((("diabrete", 4), ("esqueleto", 2)),
                 (("sombra:tanque", 1), ("sombra:ninja", 1), ("diabrete", 2))),
                exit_spot=(800, 600)),
    )),
    Phase("templo", "TEMPLO GELADO", "templo_gelado", (
        Dungeon("templo_patio", "PÁTIO DO TEMPLO", BOTTOM, (0.0, -1.0),
                ((("diabrete", 4), ("esqueleto", 2)),
                 (("golem", 1), ("esqueleto", 2), ("diabrete", 2))),
                exit_spot=(800, 600)),
        Dungeon("templo_gelado", "ALTAR DO CRISTAL", BOTTOM, (0.0, -1.0),
                ((("chefe", 1),),),
                exit_spot=(800, 460), boss_spot=(800, 330)),
    )),
    # ── capítulo 2: Lag Lobby, a empresa de tecnologia tomada pela Patrulha Cinza ──
    Phase("recepcao", "RECEPÇÃO DA LAG LOBBY", "lag_estacionamento", (
        Dungeon("lag_saguao", "SAGUÃO E CATRACAS", LEFT, (1.0, 0.0),
                ((("drone", 4),),
                 (("drone", 3), ("miliciano", 2))),
                exit_spot=(1460, 600)),
        Dungeon("lag_openspace", "OPEN SPACE", LEFT, (1.0, 0.0),
                ((("miliciano", 2), ("drone", 3)),
                 (("sombra:albeguinio", 1), ("miliciano_exo", 1), ("drone", 2))),
                exit_spot=(1000, 700)),
    ), chapter=2),
    Phase("datacenter", "DATA CENTER", "lag_copa", (
        Dungeon("lag_servidores", "CORREDOR DE SERVIDORES", LEFT, (1.0, 0.0),
                ((("miliciano", 2), ("torreta", 2)),
                 (("drone", 4), ("miliciano", 2))),
                exit_spot=(1800, 700), hazard="laser"),
        Dungeon("lag_laboratorio", "LABORATÓRIO DO EXO", LEFT, (1.0, 0.0),
                ((("torreta", 2), ("drone", 3)),
                 (("miliciano_exo", 2), ("sombra:cauanzera", 1), ("drone", 2))),
                exit_spot=(800, 600)),
    ), chapter=2),
    Phase("cobertura", "COBERTURA", "lag_reuniao", (
        Dungeon("lag_heliponto", "HELIPONTO", BOTTOM, (0.0, -1.0),
                ((("drone", 4), ("miliciano", 2)),
                 (("miliciano_exo", 1), ("torreta", 2), ("miliciano", 2))),
                exit_spot=(800, 600), hazard="vento"),
        Dungeon("lag_diretor", "SALA DO DIRETOR", BOTTOM, (0.0, -1.0),
                ((("chefe", 1),),),
                exit_spot=(800, 460), boss_spot=(800, 330), boss="borba"),
    ), chapter=2),
    # ── capítulo 3: Clínica Clepalovers, tomada pelo caco do fragmento ──
    Phase("clinica_recepcao", "RECEPÇÃO CLEPALOVERS", "clinica_fachada", (
        Dungeon("clinica_espera", "SALA DE ESPERA", LEFT, (1.0, 0.0),
                ((("mascara_argila", 4),),
                 (("mascara_argila", 3), ("seringuinha", 2))),
                exit_spot=(1400, 650), hazard="piso_molhado", daiwone=True),
        Dungeon("clinica_consultorios", "CORREDOR DOS CONSULTÓRIOS", LEFT, (1.0, 0.0),
                ((("seringuinha", 2), ("rolinho_jade", 3)),
                 (("maquina", 3), ("mascara_argila", 2))),
                exit_spot=(1840, 700)),
    ), chapter=3),
    Phase("procedimentos", "ALA DE PROCEDIMENTOS", "clinica_vestiario", (
        Dungeon("clinica_laser", "SALA DO LASER", LEFT, (1.0, 0.0),
                ((("esteti_bot", 2), ("mascara_argila", 3)),
                 (("cadeira", 1), ("rolinho_jade", 3), ("seringuinha", 2))),
                exit_spot=(1400, 600), hazard="laser_grade"),
        Dungeon("clinica_spa", "SPA E SAUNA", LEFT, (1.0, 0.0),
                ((("toalha_fantasma", 4), ("mascara_argila", 2)),
                 (("sombra:geada", 1), ("cadeira", 1), ("toalha_fantasma", 3))),
                exit_spot=(1700, 700), hazard="vapor", daiwone=True),
    ), chapter=3),
    Phase("suite_vip", "SUÍTE VIP", "clinica_antessala", (
        Dungeon("clinica_espelhos", "SALA DOS ESPELHOS", LEFT, (1.0, 0.0),
                ((("espelho_vivo", 2), ("grampeador", 2)),
                 (("sombra:fantasma", 1), ("espelho_vivo", 1), ("cadeira", 1), ("seringuinha", 2))),
                exit_spot=(1440, 600), daiwone=True),
        Dungeon("clinica_adm", "SALA DO ADMINISTRATIVO", BOTTOM, (0.0, -1.0),
                ((("chefe", 1),),),
                exit_spot=(800, 460), boss_spot=(800, 330), boss="albeguinio"),
    ), chapter=3),
    # ── capítulo 4: Mansão do Carimbo, onde a lasca virou a IARA ──
    Phase("mansao_sede", "SEDE DA MANSÃO", "mansao_fachada", (
        Dungeon("mansao_fila", "FILA DO ATENDIMENTO", LEFT, (1.0, 0.0),
                ((("processo", 4),),
                 (("processo", 3), ("carimbador", 2))),
                exit_spot=(1400, 650), hazard="fila"),
        Dungeon("mansao_arquivo", "ARQUIVO GERAL", ((90, 640), (90, 760), (150, 640), (150, 760)), (1.0, 0.0),
                ((("impressora", 2), ("processo", 3)),
                 (("sombra:paredao", 1), ("carimbador", 2), ("processo", 2))),
                exit_spot=(1840, 700), hazard="pilha"),
    ), chapter=4),
    Phase("mansao_patio", "PÁTIO E CPD", "mansao_copa", (
        Dungeon("mansao_patio", "PÁTIO A 47°C", LEFT, (1.0, 0.0),
                ((("garrafa_termica", 3), ("tuiuiu_drone", 2)),
                 (("arquivo_aco", 1), ("tuiuiu_drone", 3), ("garrafa_termica", 2))),
                exit_spot=(1800, 700), hazard="calor"),
        Dungeon("mansao_cpd", "SUBSOLO DO CPD", LEFT, (1.0, 0.0),
                ((("ponto_eletronico", 2), ("popup_iara", 3)),
                 (("sombra:faisca", 1), ("ponto_eletronico", 2), ("popup_iara", 2))),
                exit_spot=(1440, 600), hazard="energia"),
    ), chapter=4),
    Phase("mansao_gabinete", "GABINETE", "mansao_escadaria", (
        Dungeon("mansao_reuniao", "SALA DE REUNIÃO DO COMITÊ", LEFT, (1.0, 0.0),
                ((("projetor", 2), ("impressora", 2), ("popup_iara", 2)),
                 (("sombra:trovao", 1), ("arquivo_aco", 1), ("projetor", 1), ("ponto_eletronico", 2))),
                exit_spot=(1440, 600), hazard="reuniao"),
        Dungeon("mansao_nucleo", "NÚCLEO DA IARA", BOTTOM, (0.0, -1.0),
                ((("chefe", 1),),),
                exit_spot=(800, 460), boss_spot=(800, 360), boss="cauanzera"),
    ), chapter=4),
)
# a sala de luta do meio de cada fase (arena.SALAS): duas ondas menores, com os inimigos da fase
_MID = ((160, 380), (160, 500), (240, 380), (240, 500))


def _middle(key, name, waves, hazard=None):
    return Dungeon(f"sala_{key}", name, _MID, (1.0, 0.0), waves, exit_spot=(600, 120), hazard=hazard)


MIDDLE = {
    "floresta": _middle("floresta", "BOSQUE FECHADO",
                        ((("diabrete", 4), ("esqueleto", 1)), (("esqueleto", 3), ("diabrete", 2)))),
    "calabouco": _middle("calabouco", "GALERIA DAS CORRENTES",
                         ((("esqueleto", 3), ("diabrete", 2)), (("golem", 1), ("diabrete", 3)))),
    "templo": _middle("templo", "CLAUSTRO DE GELO",
                      ((("diabrete", 3), ("esqueleto", 3)), (("golem", 1), ("esqueleto", 2), ("diabrete", 2)))),
    "recepcao": _middle("recepcao", "SALA DE TREINAMENTO",
                        ((("drone", 3), ("miliciano", 1)), (("miliciano", 2), ("drone", 3)))),
    "datacenter": _middle("datacenter", "SALA DE CABOS",
                          ((("torreta", 1), ("drone", 3)), (("miliciano", 2), ("miliciano_exo", 1), ("drone", 2)))),
    "cobertura": _middle("cobertura", "TERRAÇO",
                         ((("drone", 4), ("torreta", 1)), (("miliciano_exo", 1), ("miliciano", 2), ("drone", 2)))),
    "clinica_recepcao": _middle("clinica_recepcao", "SALA DE AVALIAÇÃO",
                                ((("mascara_argila", 3), ("rolinho_jade", 2)),
                                 (("seringuinha", 2), ("mascara_argila", 3)))),
    "procedimentos": _middle("procedimentos", "SALA DE MASSAGEM",
                             ((("toalha_fantasma", 3), ("rolinho_jade", 2)),
                              (("esteti_bot", 1), ("toalha_fantasma", 2), ("seringuinha", 2)))),
    "suite_vip": _middle("suite_vip", "CLOSET VIP",
                         ((("grampeador", 2), ("seringuinha", 2)),
                          (("espelho_vivo", 1), ("cadeira", 1), ("grampeador", 2)))),
    "mansao_sede": _middle("mansao_sede", "PROTOCOLO GERAL",
                           ((("processo", 3), ("carimbador", 1)), (("impressora", 1), ("processo", 3), ("carimbador", 1)))),
    "mansao_patio": _middle("mansao_patio", "ESTACIONAMENTO",
                            ((("tuiuiu_drone", 3), ("garrafa_termica", 1)),
                             (("garrafa_termica", 2), ("tuiuiu_drone", 2), ("ponto_eletronico", 1)))),
    "mansao_gabinete": _middle("mansao_gabinete", "ANTESSALA DO GABINETE",
                               ((("popup_iara", 3), ("projetor", 1)),
                                (("arquivo_aco", 1), ("impressora", 1), ("popup_iara", 2)))),
}
CHAPTER_START = {ch: next(i for i, p in enumerate(PHASES) if p.chapter == ch) for ch in (1, 2, 3, 4)}
RUSH_PHASES = tuple(i for i, p in enumerate(PHASES) if p.dungeons[-1].boss_spot)   # salas dos 4 chefes
RUSH_UPGRADES = 4             # Reunião dos Corrompidos: melhorias sorteadas antes do primeiro chefe
CHAPTER2_SOULS = 120          # começando do capítulo 2: almas para a loja da primeira fase
CHAPTER2_UPGRADES = 2         # ... e melhorias sorteadas (mais a escolhida antes de entrar)

# etapas de uma fase (CampaignRun.stage). A fase normal é um mapa só (fase.PhaseMatch) e não troca de
# etapa; a sala avulsa (CampaignMatch, na Reunião dos Corrompidos) ainda usa a etapa da masmorra
LOBBY_START, DUNGEON_1, LOBBY_BACK, DUNGEON_2 = range(4)
STAGE_REVIVE = 0.3
            # quem estava caído ao fim de uma masmorra volta com essa vida


def is_elite(kind):
    if kind == "chefe" or kind.startswith("sombra:"):
        return True
    creature = CREATURES.get(kind)
    return creature is not None and creature.elite


def scaled_count(kind, base, players, crowd=0.5):
    """Mais jogadores, mais inimigos: +50% dos comuns por jogador a mais (os fortes ganham vida).
    ``crowd`` sobe nas dificuldades altas (4 jogadores no Borba = muito mais gente)."""
    if is_elite(kind):
        return base
    return max(1, round(base * (1 + crowd * (players - 1))))


def elite_hp_scale(kind, players):
    if kind == "chefe":
        return 1 + 0.6 * (players - 1)
    return 1 + 0.35 * (players - 1) if is_elite(kind) else 1.0


class CampaignRun:
    """O que vale para a campanha inteira, de uma fase para a outra."""

    def __init__(self, session):
        self.session = session
        self.slots = [s.slot for s in session.slots]
        self.phase_index = 0
        self.continues = self.level.continues
        self.upgrades = {s: [] for s in self.slots}
        self.hp_ratio = {s: 1.0 for s in self.slots}
        self.kills = {s: 0 for s in self.slots}
        self.damage = {s: 0 for s in self.slots}
        self.frames = 0
        self.stage = LOBBY_START
        self.chest_open = False
        self.relics = {s: None for s in self.slots}       # arma rara do baú de cada jogador
        self.held = {s: 0 for s in self.slots}            # arma na mão de uma etapa para a outra
        self.loadouts = {s: None for s in self.slots}     # armas comuns que pegou no chão (de tiro, de perto)
        self.souls = {s: 0 for s in self.slots}           # carteira de almas de cada jogador (moeda do mercado)
        self.forge = {s: {} for s in self.slots}          # ferreiro: nome da arma -> [nível, encanto]
        self.rerolls = {s: 0 for s in self.slots}         # trocas das melhorias compradas na loja
        self.fused_phase = -1                             # fase em que o grupo já usou a fusão do ferreiro
        self.curse = None                                 # desafio da fase (maldição do altar): market.CURSES
        self.start_chapter = 1                            # 2: começou direto no capítulo 2 (sem recorde de tempo)
        self.rack = []                                    # armário do acampamento: armas guardadas (armario.token_of)
        self.armor = {}                                   # armadura de Uno (capítulo 1): slot -> golpes que segura
        self.vehicle = "city"                             # com o que o grupo sai da Casa (garagem)
        self.rush = bool(getattr(session, "rush", False))   # Reunião dos Corrompidos (só os chefes)
        self._snapshot = None
        self._fresh = self._chapter_state()                # o PARA ONDE? volta daqui antes de trocar

    def _chapter_state(self):
        return {k: copy.deepcopy(getattr(self, k)) for k in ("phase_index", "upgrades", "souls", "start_chapter")}

    @property
    def phase(self):
        return PHASES[self.phase_index]

    @property
    def level(self):
        return LEVELS.get(self.session.difficulty, LEVELS["normal"])

    @property
    def price_mult(self):
        return self.level.price

    @property
    def in_lobby(self):
        return self.stage in (LOBBY_START, LOBBY_BACK)

    @property
    def dungeon_index(self):
        return 1 if self.stage >= LOBBY_BACK else 0

    @property
    def dungeon(self):
        return self.phase.dungeons[self.dungeon_index]

    @property
    def players(self):
        return len(self.slots)

    @property
    def last_phase(self):
        return self.phase_index == len(PHASES) - 1

    @property
    def chapter(self):
        return self.phase.chapter

    @property
    def chapter_end(self):
        """Última fase de um capítulo que não é o último (depois dela vem a história do capítulo novo)."""
        return not self.last_phase and PHASES[self.phase_index + 1].chapter != self.chapter

    @property
    def rush_last(self):
        return self.rush and self.phase_index == RUSH_PHASES[-1]

    def start_rush(self):
        """Reunião dos Corrompidos: os 4 chefes em sequência, com melhorias sorteadas para aguentar."""
        from .upgrades import choices
        self.rush = True
        self.start_chapter = 0                  # não vale recorde da campanha
        self.phase_index = RUSH_PHASES[0]
        for s in self.slots:
            for _ in range(RUSH_UPGRADES):
                self.upgrades[s].append(random.choice(choices(self.upgrades[s])))

    def next_rush(self):
        """Vai para a sala do próximo chefe (cura um pouco no caminho)."""
        later = [i for i in RUSH_PHASES if i > self.phase_index]
        self.phase_index = later[0]
        self.hp_ratio = {s: min(1.0, r + 0.5) for s, r in self.hp_ratio.items()}

    def start_at_chapter(self, chapter):
        """Começa direto num capítulo já liberado: almas e melhorias sorteadas para compensar."""
        from .upgrades import choices
        self.start_chapter = chapter
        self.phase_index = CHAPTER_START[chapter]
        if chapter > 1:
            # quanto mais adiante, mais almas e melhorias (o capítulo 3 recebe o dobro do 2)
            for s in self.slots:
                self.souls[s] += CHAPTER2_SOULS * (chapter - 1)
                for _ in range(CHAPTER2_UPGRADES * (chapter - 1)):
                    self.upgrades[s].append(random.choice(choices(self.upgrades[s])))

    def pick_chapter(self, chapter):
        """PARA ONDE? no carro da Casa: troca o capítulo de uma campanha que ainda não começou.
        Volta ao estado do começo (sem somar o bônus duas vezes) e entra no capítulo como pelo menu."""
        if chapter == self.chapter or chapter not in CHAPTER_START:
            return False
        for k, v in self._fresh.items():
            setattr(self, k, copy.deepcopy(v))
        if chapter > 1:
            self.start_at_chapter(chapter)
        return True

    def _state(self):
        return {k: copy.deepcopy(getattr(self, k))
                for k in ("phase_index", "continues", "upgrades", "hp_ratio", "kills", "damage", "frames",
                          "stage", "chest_open", "relics", "held", "loadouts", "souls", "forge", "rerolls",
                          "fused_phase", "curse", "start_chapter", "rack", "armor")}

    # ── almas ────────────────────────────────
    def wallet(self, slot):
        return self.souls.get(slot, 0)

    def earn(self, slot, amount):
        if slot in self.souls:
            self.souls[slot] += amount

    def spend(self, slot, amount):
        """Tira da carteira de quem comprou. False (e nada muda) se não der."""
        if self.wallet(slot) < amount:
            return False
        self.souls[slot] -= amount
        return True

    def begin_phase(self):
        """Começa a fase na abertura e guarda como tudo estava (para TENTAR DE NOVO)."""
        self.stage = LOBBY_START
        self.chest_open = False
        self._snapshot = self._state()

    def retry_phase(self):
        if self._snapshot is not None:
            for k, v in copy.deepcopy(self._snapshot).items():
                setattr(self, k, v)
        self.continues = max(self.continues, min(1, self.level.continues))     # no Borba, nada de continue
        self.hp_ratio = {s: max(r, 0.6) for s, r in self.hp_ratio.items()}

    def prepare(self, fighter):
        """Aplica as melhorias, a arma rara do baú e a vida que sobrou da etapa anterior."""
        fighter.forge = self.forge.setdefault(fighter.slot, {})      # o mesmo dicionário: o ferreiro mexe nele
        names = self.loadouts.get(fighter.slot)
        if names:
            fighter.loadout = tuple(common_weapon(n) for n in names)
        apply_all(fighter, self.upgrades.get(fighter.slot, ()))
        relic = RARE_WEAPONS.get(self.relics.get(fighter.slot))
        if relic is not None:
            fighter.relic = relic                    # direto: com a forjada, o loadout salvo são as comuns ao lado dela
        fighter.weapon_index = min(self.held.get(fighter.slot, 0), len(fighter.weapons) - 1)
        fighter.hp = max(1, round(fighter.max_hp * self.hp_ratio.get(fighter.slot, 1.0)))
        # armadura de Uno: só vale no capítulo 1 (ficou na floresta)
        fighter.uno_hits = self.armor.get(fighter.slot, 0) if self.chapter == 1 else 0
        # energia: a barra começa cheia em cada etapa (enche no acampamento, antes de cada masmorra)
        fighter.energy_max = energia.ENERGY_MAX + fighter.energy_bonus
        fighter.energy = fighter.energy_max

    def carry(self, match):
        """Fim de uma etapa: vida, arma na mão, arma rara e as contas passam para a próxima."""
        for f in match.players:
            self.hp_ratio[f.slot] = f.hp / f.max_hp if f.hp > 0 else STAGE_REVIVE
            self.kills[f.slot] += f.kills
            self.damage[f.slot] += f.damage_dealt
            self.held[f.slot] = f.weapon_index
            self.relics[f.slot] = relic_key(f.relic)
            self.loadouts[f.slot] = [w.name for w in f.loadout] if f.loadout else None
            if f.uno_hits > 0 and self.chapter == 1:
                self.armor[f.slot] = f.uno_hits
            else:
                self.armor.pop(f.slot, None)
        self.frames += match.frame

    def finish_phase(self, match):
        """Fim da fase (portal): leva tudo e ainda recupera um pouco da vida."""
        for f in match.players:
            if f.hp <= 0:
                f.hp = 0
        self.carry(match)
        for f in match.players:
            ratio = f.hp / f.max_hp if f.hp > 0 else 0.0
            self.hp_ratio[f.slot] = min(1.0, ratio + self.level.phase_heal)

    # ── salvar entre fases ───────────────────
    SAVE_VERSION = 2              # 2: almas por jogador (no 1 eram do grupo)
    _BY_SLOT = ("upgrades", "hp_ratio", "kills", "damage", "relics", "held")

    def to_save(self):
        """O estado do começo da fase, num formato que cabe no progresso.json."""
        state = self._state()
        for k in self._BY_SLOT + ("loadouts", "forge", "rerolls", "souls"):
            state[k] = {str(s): v for s, v in state[k].items()}
        return {"versao": self.SAVE_VERSION, "dificuldade": self.session.difficulty,
                "jogadores": [{"slot": s.slot, "char": s.char, "weapon": s.weapon} for s in self.session.slots],
                "estado": state}

    @classmethod
    def from_save(cls, data):
        """Monta a campanha salva de novo. Devolve None se o arquivo estiver estranho ou velho."""
        from .data import CHARACTERS
        from .session import Session, SlotSetup
        from .upgrades import UPGRADES
        try:
            if data.get("versao") not in (1, cls.SAVE_VERSION) or data.get("dificuldade") not in DIFFICULTY:
                return None
            slots = []
            for p in data["jogadores"]:
                slot, char, weapon = int(p["slot"]), int(p["char"]), int(p["weapon"])
                if not (1 <= slot <= 4 and 0 <= char < len(CHARACTERS) and weapon in (0, 1)):
                    return None
                slots.append(SlotSetup(slot, char=char, weapon=weapon))
            if not slots or len({s.slot for s in slots}) != len(slots):
                return None
            run = cls(Session("campaign", slots, difficulty=data["dificuldade"]))
            state = data["estado"]
            for k in cls._BY_SLOT:
                values = {int(s): v for s, v in state[k].items()}
                if set(values) != set(run.slots):
                    return None
                setattr(run, k, values)
            if any(u not in UPGRADES for ups in run.upgrades.values() for u in ups):
                return None
            if any(r is not None and r not in RARE_WEAPONS for r in run.relics.values()):
                return None
            run.hp_ratio = {s: min(1.0, max(0.05, float(r))) for s, r in run.hp_ratio.items()}
            run.phase_index = int(state["phase_index"])
            if not 0 <= run.phase_index < len(PHASES):
                return None
            run.continues = max(min(1, run.level.continues), int(state["continues"]))
            run.frames = int(state["frames"])
            run.kills = {s: int(v) for s, v in run.kills.items()}
            run.damage = {s: int(v) for s, v in run.damage.items()}
            run.held = {s: int(v) for s, v in run.held.items()}
            loadouts = {int(s): v for s, v in state.get("loadouts", {}).items()}   # saves antigos não têm
            for s in run.slots:
                names = loadouts.get(s)
                if names is not None:
                    weapons = [common_weapon(n) for n in names]
                    # 2 = (de tiro, de perto) no lugar das do herói; com a forjada, 1 ou 2 comuns ao lado dela
                    if (len(weapons) not in (1, 2) or None in weapons
                            or (len(weapons) == 2 and [w.is_melee for w in weapons] != [False, True])):
                        return None
                    names = list(names)
                run.loadouts[s] = names
            souls = state.get("souls", 0)
            if isinstance(souls, dict):
                for s, n in souls.items():
                    if int(s) not in run.slots:
                        return None
                    run.souls[int(s)] = max(0, int(n))
            else:
                # save antigo: as almas do grupo são divididas igualmente
                share = max(0, int(souls)) // len(run.slots)
                run.souls = {s: share for s in run.slots}
            run.fused_phase = int(state.get("fused_phase", -1))
            start = int(state.get("start_chapter", 1))
            run.start_chapter = start if start in CHAPTER_START else 1
            run.curse = state.get("curse")
            if run.curse is not None and run.curse not in CURSES:
                return None
            for s, entries in {int(k): v for k, v in state.get("forge", {}).items()}.items():
                if s not in run.slots:
                    return None
                forge = {}
                for name, (level, enchant) in entries.items():
                    level = int(level)
                    if not 1 <= level <= MAX_LEVEL or (enchant is not None and enchant not in ENCHANTS):
                        return None
                    forge[str(name)] = [level, enchant]
                run.forge[s] = forge
            rack = [str(t) for t in state.get("rack", [])][:RACK_SIZE]       # saves antigos não têm
            if any(weapon_of(t) is None for t in rack):
                return None
            run.rack = rack
            for s, n in {int(k): v for k, v in state.get("rerolls", {}).items()}.items():
                if s not in run.slots:
                    return None
                run.rerolls[s] = max(0, min(MAX_REROLLS, int(n)))
        except (KeyError, TypeError, ValueError, AttributeError):
            return None
        return run

    def add_upgrade(self, slot, key):
        self.upgrades[slot].append(key)

    def advance(self):
        self.phase_index += 1


def relic_key(weapon):
    for key, w in RARE_WEAPONS.items():
        if w is weapon:
            return key
    return None


class _Point:
    """Alvo imaginário à frente do jogador (atirar sem inimigo por perto)."""

    def __init__(self, x, y):
        self.x, self.y = x, y


LEAVE_FRAMES = 32             # escurecendo para trocar de etapa
FADE_IN = 26
EXIT_DELAY = 70               # depois da sala limpa, a porta (ou o portal) aparece
TELEPORT_FRAMES = 80
LEASH_STEP = 40               # correção grande (teletransporte) só acima disso; abaixo, anda passo a passo


PASSAGE_FRAMES = 120         # 2 s de contagem na passagem coletiva (zera se alguém sair)
PASSAGE_SOLO = 60            # sozinho, só um respiro de 1 s
FORCE_WAIT = 20 * config.FPS     # alguém travando o grupo por 20 s: o P1 pode ir mesmo assim
CALL_EVERY = 3 * config.FPS      # com gente na porta, o celular de quem falta vibra a cada 3 s
TILE_PX = 40


class Passage:
    """Passagem coletiva: o portal da fase (e a saída da sala avulsa).

    A contagem só começa com todos os jogadores ATIVOS dentro da área, zera se alguém sair e
    dispara uma vez só. Ativo = em pé e com controle presente (as vagas 1 e 2 têm teclado e
    contam sempre; as outras precisam do celular ou do controle conectado): um celular que caiu
    não trava o grupo, e o herói dele vai junto. Se alguém trava o grupo por 20 s com gente na
    porta, o P1 (a coroa) pode ir mesmo assim com ATACAR."""

    def __init__(self, contains):
        self.contains = contains        # contains(lutador) -> está dentro da área?
        self.timer = 0
        self.wait = 0
        self.gone = False
        self.inside = []
        self.missing = []

    def frames(self):
        return PASSAGE_SOLO if len(self.inside) + len(self.missing) <= 1 else PASSAGE_FRAMES

    @property
    def counting(self):
        return self.timer > 0 and not self.gone

    @property
    def seconds_left(self):
        return max(1, math.ceil((self.frames() - self.timer) / config.FPS))

    @property
    def can_force(self):
        return not self.gone and self.wait >= FORCE_WAIT

    def update(self, match):
        """Um quadro. Devolve True no quadro em que o grupo vai (uma vez só)."""
        if self.gone:
            return False
        present = match.present_slots()
        active = [p for p in match.alive_players if p.slot in present]
        self.inside = [p for p in active if self.contains(p)]
        self.missing = [p for p in active if p not in self.inside]
        if active and not self.missing:
            before = self.seconds_left if self.timer else None
            self.timer += 1
            if self.timer >= self.frames():
                self.gone = True
                for p in match.players:
                    rumble.fighter(p, rumble.GO)
                return True
            if before != self.seconds_left:
                match.assets.play("select", 0.35)          # o tique de cada segundo
                for p in self.inside:
                    rumble.fighter(p, rumble.TICK)
        else:
            self.timer = 0
        self.wait = self.wait + 1 if self.inside and self.missing else 0
        if self.wait and self.wait % CALL_EVERY == 0:
            for p in self.missing:                         # convocação: o grupo está esperando você
                rumble.fighter(p, rumble.CALL)
        return False

    def try_force(self, match, f):
        """O P1 aperta ATACAR depois da espera longa: o grupo vai sem quem está travando."""
        from .host import host_slot
        if not self.can_force or f.slot != host_slot(match.session):
            return False
        self.gone = True
        for p in match.players:
            rumble.fighter(p, rumble.GO)
        match.leave()
        return True


class CoopMatch(Match):
    """Base das partidas da campanha (a fase inteira, a sala avulsa e a Casa): os jogadores do mesmo time,
    a mira, levantar quem caiu, os itens, o escurecer entre uma etapa e outra e o HUD."""

    min_zoom = 0.5            # bem de longe, a pixel art fica no tamanho original (2 por 1)
    lobby = False

    def __init__(self, game, run, map_key, starts, facing, arena=None):
        self.run = run
        self.phase = run.phase
        super().__init__(game, run.session, map_key, arena)
        for setup, pos in zip(run.session.slots, starts):
            f = self._add_fighter(setup, pos, team=PLAYERS)
            f.full_name = setup.name
            f.facing = facing
            run.prepare(f)
            game.inputs[setup.slot].set_layout("battle")
            self.controllers[f] = game.inputs[setup.slot]
        self.players = list(self.fighters)
        self.enemies = []
        self.portals = []
        self.pickups = []
        self.props = []                 # entrada, fogueira, baú, porta, portal...
        self.ground = []                # armas no chão (largadas ou derrubadas por inimigos)
        self.menus = {}                 # menu do mercado aberto, por jogador
        self.revive_progress = {f: 0.0 for f in self.players}
        self.strain = {f: 0 for f in self.players}     # quadros forçando o limite do grupo
        self.was_down = set()
        self.wave = -1
        self.banner = None              # (título, subtítulo, cor, idade)
        self.wave_banner = 0
        self.boss = None
        self.won = False
        self.leaving = 0                # escurecendo para a próxima etapa
        self._last_pause = -99

    # ── consultas ────────────────────────────
    @property
    def alive_players(self):
        return [p for p in self.players if p.alive_in_match]

    @property
    def alive_enemies(self):
        return [e for e in self.enemies if e.alive_in_match]

    @property
    def elapsed(self):
        return self.run.frames + self.frame

    @property
    def waves(self):
        return ()

    def nearest_player(self, me):
        alive = self.alive_players
        return min(alive, key=me.distance_to) if alive else None

    def aim_target(self, f):
        """Inimigo que o jogador quer acertar: o mais perto na direção em que ele aponta."""
        reach = 220 if f.weapon.is_melee else 600
        fx, fy = f.input if math.hypot(*f.input) > 0.3 else f.facing
        mag = math.hypot(fx, fy) or 1
        fx, fy = fx / mag, fy / mag
        best, best_score = None, 1e9
        for e in self.alive_enemies:
            dx, dy = e.x - f.x, e.y - f.y
            d = math.hypot(dx, dy)
            if d > reach + e.radius:
                continue
            dot = (dx * fx + dy * fy) / (d or 1)
            score = d * (1.6 - dot)
            if score < best_score:
                best, best_score = e, score
        return best

    def focus_points(self):
        pts = [(p.x, p.y - 20) for p in self.players if not self.leash_free(p)]
        return pts or [(p.x, p.y - 20) for p in self.players]

    def leash_free(self, p):
        """Quem está fora da corda do grupo e do enquadramento (na Casa: quem está numa janela)."""
        return False

    def window_warning(self, f):
        """Aviso por cima da janela de ``f`` (na Casa: a turma saindo, o LIBERAR TUDO)."""
        return None

    def menu_closed(self, f):
        """Depois que a janela de ``f`` fecha (na Casa: volta para perto do grupo se ficou longe)."""

    def world_entities(self):
        return self.fighters + self.pickups + [p for p in self.props if not getattr(p, "flat", False)]

    def draw_over_walls(self, view, cam):
        for p in self.props:
            if getattr(p, "flat", False):
                p.draw(view, cam)

    def objective(self):
        """Ponto para onde a seta (fora da tela) aponta: a próxima entrada, a porta ou o portal."""
        return None

    @property
    def objective_text(self):
        return ""

    def hit_feedback(self, target, amount):
        """Com muita gente batendo ao mesmo tempo, pausar a cada tiro travaria o jogo:
        a pausa fica para quando um jogador apanha ou um inimigo cai (e não mais que uma por vez)."""
        if target.team == PLAYERS:
            self.camera.shake(4 if amount < 20 else 7)
            pause = 2 if amount < 20 else 4
        else:
            if amount >= 20:
                self.camera.shake(2)
            pause = 3 if target.hp <= 0 else 0
        if pause and self.frame - self._last_pause > 12:
            self._last_pause = self.frame
            self.hit_pause(pause)

    # ── ciclo ────────────────────────────────
    @property
    def locked(self):
        """Jogadores parados (apresentação, fim de fase, saindo)."""
        return self.leaving > 0

    def step(self):
        locked = self.locked
        for f, ctrl in list(self.controllers.items()):
            if not f.alive_in_match or locked or f.stunned:
                f.steer(0, 0)
            elif f.team == PLAYERS:
                self._human(f, ctrl)
            elif getattr(f, "panic", 0) > 0:
                self._flee(f)
            elif isinstance(ctrl, FighterAI):
                target = self.nearest_player(f)
                if target is None:
                    f.steer(0, 0)
                else:
                    ctrl.update(f, target, self)
            else:
                ctrl.update(f, self)
            f.update(self)
        self._separate_bodies()
        self._leash()
        self._update_bullets()
        for effect in self.effects:
            effect.update(self)
        self.effects = [e for e in self.effects if e.alive]
        for prop in self.props:
            prop.update(self)
        self.props = [p for p in self.props if p.alive]
        self._update_pickups()
        self._regen_energy()
        self.publish_ammo()
        self.publish_souls()
        self.phone_shop()
        self.update_stage()
        if self.wave_banner > 0:
            self.wave_banner -= 1
        if self.banner:
            t, s, c, age = self.banner
            self.banner = (t, s, c, age + 1)
        if self.leaving:
            self.leaving += 1
            if self.leaving >= LEAVE_FRAMES:
                self._finish(won=True)

    def update_stage(self):
        """O que é próprio da etapa (ondas, entradas, baú...)."""

    def interact(self, f):
        """ATACAR perto de algo (baú, portal): devolve True se usou o botão para isso."""
        return self.pick_ground(f)

    # ── armas no chão ────────────────────────
    def pick_ground(self, f):
        """Pega a arma do chão mais perto. A rara troca com a rara; a comum troca com a arma do
        herói do mesmo tipo (de tiro ou de perto). A que ele tinha fica no lugar (a do próprio
        herói, não: essa volta para a mochila)."""
        near = [g for g in self.ground if g.alive and g.can_pick(f)]
        if not near:
            return False
        item = min(near, key=f.distance_to)
        item.alive = False
        self.ground.remove(item)
        if item.weapon.rare:
            self.give_relic(f, item.weapon, drop_at=(item.x, item.y))
        elif self.give_common(f, item.weapon, drop_at=(item.x, item.y)) is False:
            item.alive = True                        # não pegou: a arma fica onde estava
            self.ground.append(item)
        return True

    def give_relic(self, fighter, weapon, drop_at=None):
        """Arma rara na mão. Só dá para ter uma: a que ele tinha cai no chão (ATACAR pega de volta)."""
        old = fighter.give_relic(weapon)
        self.run.relics[fighter.slot] = relic_key(weapon)
        self.run.loadouts[fighter.slot] = [w.name for w in fighter.loadout] if fighter.loadout else None
        if old is not None and old is not weapon:
            self.drop_weapon(fighter, old, drop_at)
        self._got_weapon(fighter, weapon)

    def give_common(self, fighter, weapon, drop_at=None):
        """Arma de outro herói: entra no lugar da de mesmo tipo e já vem na mão."""
        if fighter.fused:                            # com a forjada: entra ao lado dela
            old = self.give_extra(fighter, weapon)
            if old is False:
                return False
            if old is not None and old is not weapon:
                self.drop_weapon(fighter, old, drop_at)
            self._got_weapon(fighter, weapon)
            return None
        base = list(fighter.base_weapons)
        i = next((k for k, w in enumerate(base) if w.is_melee == weapon.is_melee), None)
        if i is None:                                # herói sem arma desse tipo (só joga bola): não pega
            return False
        old = base[i]
        base[i] = weapon
        fighter.loadout = None if tuple(base) == fighter.stats.weapons else tuple(base)
        fighter.clips.pop(old, None)
        fighter.weapon_index = i
        fighter.bow_draw = 0
        self.run.loadouts[fighter.slot] = [w.name for w in fighter.loadout] if fighter.loadout else None
        # a arma do próprio herói não vai para o chão: volta para a mochila (LARGAR ARMA traz ela de
        # volta). Se fosse para o chão, largando a outra ela voltava para a mão E continuava no chão.
        if old is not weapon and old not in fighter.stats.weapons:
            self.drop_weapon(fighter, old, drop_at)
        self._got_weapon(fighter, weapon)

    def give_extra(self, fighter, weapon):
        """Com a forjada na mão, a comum vai junto dela (uma de tiro e uma de perto, no máximo).
        Devolve a comum do mesmo tipo que ela trocou (ou None), ou False se o herói não usa esse tipo."""
        if not any(w.is_melee == weapon.is_melee for w in fighter.stats.weapons):
            return False
        extras = list(fighter.extras)
        i = next((k for k, w in enumerate(extras) if w.is_melee == weapon.is_melee), None)
        old = None
        if i is None:
            extras.append(weapon)
            extras.sort(key=lambda w: w.is_melee)    # sempre (de tiro, de perto), como no save
        else:
            old, extras[i] = extras[i], weapon
            fighter.clips.pop(old, None)
        fighter.loadout = tuple(extras)
        fighter.weapon_index = extras.index(weapon)
        fighter.bow_draw = 0
        self.run.loadouts[fighter.slot] = [w.name for w in fighter.loadout]
        return old

    def _got_weapon(self, fighter, weapon):
        color = rarity_color(weapon)
        self.popup(fighter.x, fighter.y - 80, weapon.name.upper(), color)
        self.burst(fighter.x, fighter.y - 20, color, 18, speed=4)
        self.assets.play("select", 0.5)

    def drop_weapon(self, fighter, weapon, at=None, start=None):
        """Joga a arma no chão: atrás de quem largou, ou no lugar da que ele pegou (troca)."""
        if at is None:
            fx, fy = fighter.facing
            at = (fighter.x - fx * 52, fighter.y - fy * 52 + 10)
        x, y = self.arena.free_spot(at[0], at[1], 16)
        item = GroundWeapon(weapon, start or (fighter.x, fighter.y - 20), (x, y))
        self.ground.append(item)
        self.props.append(item)
        while len(self.ground) > MAX_GROUND:
            # some a mais velha, mas as comuns antes das raras (as do baú não somem por causa delas)
            old = next((g for g in self.ground if not g.weapon.rare), self.ground[0])
            self.ground.remove(old)
            old.alive = False
            if old in self.props:
                self.props.remove(old)

    def draw_ground(self, screen, cam, ui):
        nearest = set()                     # "ATACAR: PEGAR" só na arma mais perto de cada um
        for p in self.alive_players:
            items = [g for g in self.ground if g.can_pick(p)]
            if items:
                nearest.add(min(items, key=p.distance_to))
        for item in self.ground:
            item.draw_prompt(screen, cam, ui, self.frame, item in nearest)

    def _human(self, f, inp):
        menu = self.menus.get(f)
        if menu is not None:
            f.steer(0, 0)                   # parado no balcão enquanto escolhe
            if not menu.handle(inp) or not f.alive_in_match:
                del self.menus[f]
                self.menu_closed(f)
            return
        f.steer(*inp.axis())
        if inp.pressed("attack") and getattr(self, "high_fives", None):
            self._high_five(f)
        if (inp.pressed("attack") or inp.pressed("confirm")) and self.interact(f):
            return
        target = self.aim_target(f)
        if target is None:
            # sem inimigo por perto: atira para onde está andando (ou olhando)
            fx, fy = f.input if math.hypot(*f.input) > 0.3 else f.facing
            mag = math.hypot(fx, fy) or 1
            target = _Point(f.x + fx / mag * 260, f.y + fy / mag * 260)
        if inp.held("attack"):
            f.attack(self, target)
        if inp.pressed("special"):
            f.use_ability(self, target)
        self._switch_or_drop(f, inp)
        direction = None
        if inp.pressed("dodge"):
            direction = f.input if any(f.input) else f.facing
        elif inp.double_tap:
            direction = inp.double_tap
        if direction and f.dash(direction):
            self.assets.play("dash", 0.3)

    def _switch_or_drop(self, f, inp):
        """TROCAR ARMA troca; LARGAR ARMA (LB, touchpad do PlayStation, R no teclado, botão do
        celular) larga a arma da mão no chão, ou guarda no armário se estiver perto dele."""
        if inp.pressed("switch") and f.switch_weapon():
            self.assets.play("click", 0.4)
        if inp.pressed("drop"):
            rack = self.rack_near(f)
            if rack is not None:
                self.store_in_rack(f)
            else:
                self.drop_held(f)

    def rack_near(self, f):
        """O armário do corredor, se este jogador está perto dele (a masmorra não tem)."""
        return None

    def droppable(self, f):
        """A arma da mão pode sair? (a rara do baú ou a de outro herói; a dele, não)."""
        weapon = f.weapon
        return f.fused or (f.relic is not None and weapon is f.relic) or weapon not in f.stats.weapons

    def _take_out(self, f):
        """Tira a arma da mão (sem jogar no chão) e devolve ela, ou None se for a do herói."""
        weapon = f.weapon
        if f.relic is not None and weapon is f.relic:
            extras = f.extras
            f.relic = None
            f.clips.pop(weapon, None)
            f.weapon_index = 0
            self.run.relics[f.slot] = None
            if weapon.forjada:                       # as comuns que estavam com ela vão para o lugar das do herói
                f.settle_extras(extras)
                self.run.loadouts[f.slot] = [w.name for w in f.loadout] if f.loadout else None
        elif f.fused:                                # uma comum que estava com a forjada
            f.loadout = tuple(w for w in f.extras if w is not weapon) or None
            f.clips.pop(weapon, None)
            f.weapon_index = len(f.weapons) - 1
            self.run.loadouts[f.slot] = [w.name for w in f.loadout] if f.loadout else None
        elif weapon not in f.stats.weapons:
            base = list(f.base_weapons)
            i = base.index(weapon)
            own = next(w for w in f.stats.weapons if w.is_melee == weapon.is_melee)
            base[i] = own
            f.loadout = None if tuple(base) == f.stats.weapons else tuple(base)
            f.clips.pop(weapon, None)
            f.weapon_index = i
            self.run.loadouts[f.slot] = [w.name for w in f.loadout] if f.loadout else None
        else:
            return None
        f.bow_draw = 0
        return weapon

    def drop_held(self, f):
        """Larga a arma da mão: a rara do baú sai da 3ª vaga; a de outro herói volta a ser a arma
        dele do mesmo tipo. A arma do próprio herói não sai (ele precisa de uma de cada tipo)."""
        weapon = self._take_out(f)
        if weapon is None:
            self.popup(f.x, f.y - 80, "ESSA É A SUA ARMA", theme.MUTED)
            return False
        self.drop_weapon(f, weapon)
        self.popup(f.x, f.y - 80, "LARGOU " + weapon.name.upper(), theme.BONE)
        self.assets.play("click", 0.5)
        return True

    # ── armário do acampamento ───────────────
    def store_in_rack(self, f):
        """Pendura a arma da mão no armário (cabem RACK_SIZE)."""
        if not self.droppable(f):
            self.popup(f.x, f.y - 80, "ESSA É A SUA ARMA", theme.MUTED)
            return False
        if len(self.run.rack) >= RACK_SIZE:
            self.popup(f.x, f.y - 80, "ARMÁRIO CHEIO", theme.MUTED)
            return False
        weapon = self._take_out(f)
        self.run.rack.append(token_of(weapon))
        self.popup(f.x, f.y - 80, "GUARDOU " + weapon.name.upper(), rarity_color(weapon))
        self.assets.play("click", 0.5)
        return True

    def take_from_rack(self, f):
        """Pega a primeira arma do armário. A que ele tinha no lugar (rara, ou comum de outro herói)
        vai para o fim da fila do armário; a dele mesmo só volta para a mochila."""
        if not self.run.rack:
            return False
        weapon = weapon_of(self.run.rack.pop(0))
        if weapon is None:
            return False
        if weapon.rare:
            old = f.give_relic(weapon)
            self.run.relics[f.slot] = relic_key(weapon)
            self.run.loadouts[f.slot] = [w.name for w in f.loadout] if f.loadout else None
        elif f.fused:                                # com a forjada: a comum entra ao lado dela
            old = self.give_extra(f, weapon)
            if old is False:
                self.run.rack.insert(0, token_of(weapon))
                return False
        else:
            base = list(f.base_weapons)
            i = next(k for k, w in enumerate(base) if w.is_melee == weapon.is_melee)
            old = base[i]
            base[i] = weapon
            f.loadout = None if tuple(base) == f.stats.weapons else tuple(base)
            f.clips.pop(old, None)
            f.weapon_index = i
            f.bow_draw = 0
            self.run.loadouts[f.slot] = [w.name for w in f.loadout] if f.loadout else None
            if old in f.stats.weapons:
                old = None
        if old is not None and old is not weapon:
            self.run.rack.append(token_of(old))
        self._got_weapon(f, weapon)
        return True

    def rack_prompt(self, f):
        """O que ATACAR faz no armário para este jogador."""
        if self.droppable(f) and len(self.run.rack) < RACK_SIZE:
            return "ATACAR: GUARDAR " + f.weapon.name.upper()
        if self.run.rack:
            w = weapon_of(self.run.rack[0])
            return "ATACAR: PEGAR " + w.name.upper() if w is not None else ""
        return "SEGURE UMA ARMA PARA GUARDAR"

    def _flee(self, e):
        """Segredo: o último inimigo da onda, sozinho, foge tremendo de quem está mais perto."""
        e.panic -= 1
        target = self.nearest_player(e)
        if target is None:
            e.steer(0, 0)
            return
        dx, dy = e.x - target.x, e.y - target.y
        mag = math.hypot(dx, dy) or 1
        e.steer(dx / mag, dy / mag)
        if e.panic % 4 == 0:
            e.x += random.choice((-1.5, 1.5))           # tremendo

    def _high_five(self, f):
        """Segredo: logo depois de levantar, quem caiu e quem levantou apertam ATACAR juntos."""
        for five in self.high_fives:
            if f in five[0]:
                five[1].add(f)
                if five[1] >= five[0]:
                    a, b = five[0]
                    x, y = (a.x + b.x) / 2, min(a.y, b.y) - config.SPRITE_HEIGHT
                    self.burst(x, y, (255, 230, 120), 8, speed=2)
                    segredos.hint(self, x, y - 10, "TOCA AQUI", (255, 230, 120))
                    segredos.find("high_five", self, x, y - 36)
                    five[2] = 0
        self.high_fives = [h for h in self.high_fives if h[2] > 0]

    def _separate_bodies(self):
        bodies = [f for f in self.fighters if f.alive_in_match and f.lift <= 0]
        for i, a in enumerate(bodies):
            for b in bodies[i + 1:]:
                _separate(a, b)
        for f in bodies:
            self.arena.resolve(f)

    def _regen_energy(self):
        """No Fácil a energia volta sozinha, devagar."""
        regen = self.run.level.regen
        if regen <= 0 or self.lobby:
            return
        every = max(1, round(config.FPS / regen))
        if self.frame % every == 0:
            for f in self.alive_players:
                energia.gain(f, 1)

    def publish_ammo(self):
        """Munição e energia de cada jogador para o celular dele."""
        if self.frame % 6:
            return
        for f in self.players:
            if f.is_cpu or not f.slot:
                continue
            mag = f.mag if not f.weapon.is_melee else 0
            hub.publish_slot(f.slot, ammo=f.ammo, mag=mag, reload=f.reload_ratio if f.reloading else 0.0,
                             energy=f.energy or 0, emax=f.energy_max, ecost=energia.cost(f, f.weapon))

    def publish_souls(self):
        """Manda o saldo de almas de cada jogador para o celular dele."""
        if self.frame % 6:
            return
        for f in self.players:
            if f.slot:
                hub.publish_slot(f.slot, souls=self.run.wallet(f.slot))

    def phone_shop(self):
        """Loja no celular: aplica os pedidos (marcar, comprar, fechar) e manda o menu aberto de
        cada jogador. Só vale com a banca já aberta pelo ATACAR, perto dela."""
        by_slot = {f.slot: f for f in self.players if f.slot}
        orders = hub.orders()
        for slot, item, buy in orders:
            f = by_slot.get(slot)
            menu = self.menus.get(f)
            if menu is None:
                continue
            if item == "fechar":
                del self.menus[f]
                self.assets.play("cancel", 0.3)
            elif menu.pick(item) and buy:
                menu.buy()
        if self.frame % 3 and not orders:
            return
        for slot, f in by_slot.items():
            menu = self.menus.get(f)
            hub.publish_slot(slot, shop=menu.snapshot() if menu is not None else None)

    def _leash(self):
        """Ninguém se afasta demais do grupo: todos cabem na câmera.
        A correção pequena (a de todo quadro) anda passo a passo, para ninguém atravessar parede.
        Quem fica forçando o limite vê a seta do grupo e, depois de um tempo, aparece ao lado dele."""
        tied = [p for p in self.players if not self.leash_free(p)]
        if len(tied) < 2:
            return
        for p in tied:
            if not p.alive_in_match:
                self.strain[p] = 0
                continue
            others = [q for q in tied if q is not p]
            min_x, max_x = min(q.x for q in others), max(q.x for q in others)
            min_y, max_y = min(q.y for q in others), max(q.y for q in others)
            x = min(max(p.x, max_x - LEASH_X), min_x + LEASH_X)
            y = min(max(p.y, max_y - LEASH_Y), min_y + LEASH_Y)
            if (x, y) == (p.x, p.y):
                self.strain[p] = max(0, self.strain[p] - 3)
                continue
            pushing = (x - p.x) * p.input[0] + (y - p.y) * p.input[1] < 0     # andando para fora
            self.strain[p] = self.strain[p] + 1 if pushing else max(0, self.strain[p] - 3)
            if self.strain[p] >= LEASH_PULL_FRAMES:
                self._pull_to_group(p, others)
            elif abs(x - p.x) + abs(y - p.y) > LEASH_STEP:
                p.x, p.y = x, y
                self.arena.resolve(p)
            else:
                p._move(self, x - p.x, y - p.y)

    def far_from_group(self, p):
        """Fora da corda dos outros (os que não estão em janela)?"""
        others = [q for q in self.players if q is not p and q.alive_in_match and not self.leash_free(q)]
        if not others:
            return False
        min_x, max_x = min(q.x for q in others), max(q.x for q in others)
        min_y, max_y = min(q.y for q in others), max(q.y for q in others)
        return not (max_x - LEASH_X <= p.x <= min_x + LEASH_X and max_y - LEASH_Y <= p.y <= min_y + LEASH_Y)

    def group_center(self, p):
        others = [q for q in self.players if q is not p] or [p]
        return sum(q.x for q in others) / len(others), sum(q.y for q in others) / len(others)

    def _pull_to_group(self, p, others):
        """Preso no limite (atrás de uma parede, por exemplo): some na fumaça e aparece no grupo."""
        anchor = min((q for q in others if q.alive_in_match), key=p.distance_to, default=others[0])
        self.burst(p.x, p.y - 16, (200, 200, 210), 18, speed=4)
        x, y = self.arena.free_spot(anchor.x - 40 * (1 if p.x < anchor.x else -1), anchor.y, p.radius)
        p.x, p.y = x, y
        p.prev_pos = (x, y)
        p.vx = p.vy = 0.0
        p.teleport_flash = 20
        self.burst(x, y - 16, p.color, 18, speed=4)
        self.strain[p] = 0
        self.assets.play("dash", 0.4)

    def _update_pickups(self):
        for item in self.pickups:
            item.update(self)
            if not item.alive:
                continue
            for f in self.alive_players:
                if math.hypot(f.x - item.x, f.y - item.y) < f.radius + item.radius + 6:
                    item.apply(f, self)
                    break
        self.pickups = [p for p in self.pickups if p.alive]

    def _revive(self, p, ratio):
        p.hp = max(1, round(p.max_hp * ratio))
        p.invulnerable_timer = 100
        p.stun_timer = 0
        p.vx = p.vy = 0.0
        p.down_age = 0
        self.revive_progress[p] = 0.0
        self.was_down.discard(p)
        self.burst(p.x, p.y - 16, p.color, 22, speed=5)
        self.assets.play("levantar", 0.45)
        self.assets.play("select", 0.5)

    def _set_banner(self, title, sub=None, color=theme.BRASS):
        self.banner = (title, sub, color, 0)

    def group_near(self, x, y, radius):
        """Todos os jogadores em pé estão perto de (x, y)?"""
        alive = self.alive_players
        return bool(alive) and all(math.hypot(p.x - x, p.y - y) < radius for p in alive)

    def present_slots(self):
        """Vagas com controle presente: as do teclado (1 e 2) e quem tem celular ou controle conectado."""
        try:
            connected = set(self.game.connected_slots())
        except AttributeError:
            connected = set()
        return {p.slot for p in self.players if p.slot in (1, 2)} | connected

    def draw_passage(self, screen, ui, passage, area, label_at, show_area=True):
        """A área da passagem brilhando, um sinal em cima de quem já está dentro, quem falta e a contagem."""
        cam = self.camera
        x0, y0 = cam.to_screen(area.x, area.y)
        x1, y1 = cam.to_screen(area.right, area.bottom)
        rect = pygame.Rect(round(x0), round(y0), max(1, round(x1 - x0)), max(1, round(y1 - y0)))
        if show_area:
            pulse = 0.5 + 0.5 * math.sin(self.frame * (0.35 if passage.counting else 0.12))
            layer = pygame.Surface(rect.size, pygame.SRCALPHA)
            color = theme.MOSS if passage.counting else theme.BRASS
            layer.fill((*color[:3], round(26 + 34 * pulse)))
            pygame.draw.rect(layer, (*color[:3], round(120 + 100 * pulse)), layer.get_rect(), 2)
            screen.blit(layer, rect)
        for p in passage.inside:
            sx, sy = cam.to_screen(p.x, p.y - 58)
            ui.text(screen, "OK", theme.XS, theme.MOSS, (round(sx), round(sy)))
        sx, sy = cam.to_screen(*label_at)
        if passage.inside and passage.missing:
            waiting = " ".join(p.label for p in passage.missing)
            ui.text(screen, f"ESPERANDO {waiting}", theme.XS, theme.BRASS, (round(sx), round(sy) + 24))
            if passage.can_force:
                from .host import host_slot
                ui.text(screen, f"P{host_slot(self.session)}: ATACAR PARA IR ASSIM MESMO", theme.XS, theme.BONE,
                        (round(sx), round(sy) + 40))
        elif passage.counting:
            ui.text(screen, str(passage.seconds_left), theme.XL, theme.BONE, (rect.centerx, rect.y - 30))

    def leave(self):
        """Escurece a tela e passa para a próxima etapa."""
        if not self.leaving:
            self.leaving = 1
            self.assets.play("dash", 0.5)

    def _finish(self, won):
        self.won = won
        if won:
            self.run.carry(self)
        title = "ETAPA CONCLUÍDA" if won else "FIM DE JOGO"
        self.result = Result(title, theme.MOSS if won else theme.BLOOD, self.players if won else [])
        self.finished = True

    def restart_scene(self):
        from .scenes.campaign import start_phase
        self.run.retry_phase()
        return start_phase(self.game, self.run, story=False)

    # ── desenho ──────────────────────────────
    def draw(self, screen, ui):
        super().draw(screen, ui)
        self.draw_screen_layer(screen, ui)
        self._draw_leash(screen, self.camera)
        self._draw_objective_arrow(screen, self.camera)
        hud.draw_campaign_banners(screen, ui, self)
        dark = 0
        if self.frame < FADE_IN:
            dark = 1 - self.frame / FADE_IN
        if self.leaving:
            dark = max(dark, self.leaving / LEAVE_FRAMES)
        if dark > 0:
            darken(screen, round(255 * min(1.0, dark)))

    def draw_screen_layer(self, screen, ui):
        """Textos presos no mundo (nomes das entradas, ABRIR, prontos do portal...)."""

    def _draw_leash(self, screen, cam):
        """Quem força o limite do grupo: a borda da tela brilha na cor dele e uma seta do lado do
        corpo aponta para o grupo (assim fica claro por que ele parou)."""
        W, H = config.SCREEN_W, config.SCREEN_H
        for p, frames in self.strain.items():
            if frames <= 0 or not p.alive_in_match:
                continue
            k = min(1.0, frames / 20)
            pulse = 0.6 + 0.4 * math.sin(self.frame * 0.25)
            sx, sy = cam.to_screen(p.x, p.y)
            gx, gy = cam.to_screen(*self.group_center(p))
            dx, dy = gx - sx, gy - sy
            d = math.hypot(dx, dy) or 1
            ux, uy = dx / d, dy / d
            # brilho na borda da tela do lado em que ele está
            glow = pygame.Surface((W, H), pygame.SRCALPHA)
            alpha = round(150 * k * pulse)
            band = 12
            if abs(ux) >= abs(uy):
                rect = (0, 0, band, H) if ux > 0 else (W - band, 0, band, H)
            else:
                rect = (0, 0, W, band) if uy > 0 else (0, H - band, W, band)
            glow.fill((*p.color[:3], alpha), rect)
            screen.blit(glow, (0, 0))
            # seta do lado do corpo, apontando para o grupo
            hx, hy = sx + ux * 26, sy - 32 * cam.zoom + uy * 26
            size = 7
            tip = (hx + ux * size * 1.6, hy + uy * size * 1.6)
            left = (hx - uy * size * 0.8, hy + ux * size * 0.8)
            right = (hx + uy * size * 0.8, hy - ux * size * 0.8)
            pygame.draw.polygon(screen, theme.SHADOW, [(x + 1, y + 1) for x, y in (tip, left, right)])
            pygame.draw.polygon(screen, p.color, (tip, left, right))
            if frames > LEASH_PULL_FRAMES // 3:
                # barrinha: quanto falta para ser puxado para o grupo
                w = 30
                fill = frames / LEASH_PULL_FRAMES
                bx, by = sx - w / 2, sy + 8
                pygame.draw.rect(screen, theme.SHADOW, (bx, by, w, 4))
                pygame.draw.rect(screen, p.color, (bx, by, w * fill, 4))

    def _draw_objective_arrow(self, screen, cam):
        point = self.objective()
        if point is None:
            return
        W, H = config.SCREEN_W, config.SCREEN_H
        sx, sy = cam.to_screen(*point)
        if 0 <= sx <= W and 0 <= sy <= H:
            return
        _edge_arrow(screen, sx, sy, theme.BRASS, 10)

    def draw_hud(self, screen, ui):
        hud.draw_campaign(screen, ui, self)

    def hud_regions(self):
        W = config.SCREEN_W
        n = len(self.players)
        regions = [pygame.Rect(W // 2 - 230, 0, 460, 74), pygame.Rect(W - 190, 0, 190, 60)]
        for i in range(n):
            regions.append(pygame.Rect(*hud.campaign_block_rect(i, n)).inflate(8, 8))
        return regions


_edge_arrow = hud.edge_arrow


class CampaignMatch(CoopMatch):
    """Uma sala de luta: as ondas de inimigos saem dos portais e, limpa a última sala, aparece o
    portal da fase (passagem coletiva: todos dentro, 2 s). Sozinha, é a sala avulsa da Reunião dos
    Corrompidos; a fase normal (fase.PhaseMatch) herda daqui e liga as salas num mapa só."""

    def __init__(self, game, run):
        self.dungeon_index = run.dungeon_index
        self.dungeon = run.dungeon
        super().__init__(game, run, self.dungeon.map_key, self.dungeon.starts, self.dungeon.facing)
        self._setup_combat()
        self.state = "intro"
        self.state_timer = INTRO_FRAMES
        self.hazard = make_hazard(self.dungeon.hazard, self.arena)   # laser no chão, vento...

    def _setup_combat(self):
        """O que vale para a partida inteira: a força dos inimigos e os corpos."""
        self.enemy_hp, self.enemy_dmg = DIFFICULTY.get(self.run.session.difficulty, (1.0, 1.0))
        if self.run.players == 1:
            self.enemy_dmg *= SOLO_DAMAGE         # sozinho não tem quem levante: inimigos batem menos
        self.corpses = {}
        self.high_fives = []            # segredo: [dupla, quem já apertou ATACAR, quadros que faltam]
        self.notices = []               # balões do "oi sumido" (capítulo 3), na tela
        self._vanished = []
        self.state_timer = 0
        self._reset_room()

    def _reset_room(self):
        """O que vale por sala de luta (masmorra)."""
        self.breath_used = False        # último fôlego (campanha solo): uma vez por masmorra
        self.revived_once = set()       # Borba: quem já foi levantado nesta masmorra
        self.slain_boss = False
        self.exit = None                # porta para o corredor (masmorra 1) ou portal da fase (masmorra 2)
        self.passage = None             # passagem coletiva da porta ou do portal
        self.start_button = None        # INICIAR BATALHA (aparece depois da apresentação)
        self.daiwone_at = None          # quadro em que a Daiwone chega (None = não vem / já veio)
        self.hazard = None
        self.wave = -1

    @property
    def last(self):
        return self.dungeon_index == len(self.phase.dungeons) - 1

    @property
    def waves(self):
        return self.dungeon.waves

    @property
    def locked(self):
        return (super().locked or self.state in ("gameover", "teleport")
                or (self.state == "intro" and self.state_timer > INTRO_FRAMES - 40))

    def objective(self):
        if self.exit is not None:
            return self.exit.x, self.exit.y
        if self.state == "ready" and self.start_button is not None:
            return self.start_button.x, self.start_button.y
        return None

    @property
    def objective_text(self):
        if self.state == "teleport":
            return "TELETRANSPORTANDO..."
        if self.state == "ready":
            return "PRONTOS? ATACAR NO BOTÃO PARA INICIAR A BATALHA"
        if self.state == "portal":
            return "TODOS NO PORTAL PARA A PRÓXIMA FASE"
        if self.exit is not None:
            return "TODOS NA PORTA PARA O CORREDOR"
        brain = self.controllers.get(self.boss) if self.boss is not None else None
        return getattr(brain, "turn_text", "")

    def step(self):
        if self.state_timer > 0:
            self.state_timer -= 1
        super().step()

    def update_stage(self):
        if self.hazard is not None and self.state in ("fight", "between"):
            self.hazard.update(self)
        self._update_daiwone()
        for n in self.notices:
            n.update()
        self.notices = [n for n in self.notices if n.alive]
        self._update_portals()
        self._update_corpses()
        self._update_downed()
        self._update_state()
        self._secrets()

    # ── segredos (segredos.py) ───────────────
    def _secrets(self):
        for five in self.high_fives:
            five[2] -= 1
        self.high_fives = [h for h in self.high_fives if h[2] > 0]
        if self.state != "fight" or self.portals or self.wave != len(self.waves) - 1 \
                or getattr(self, "wave_size", 0) < PANIC_CROWD:
            return
        left = self.fighting_enemies()
        if len(left) != 1:
            return
        e = left[0]
        kind = getattr(e, "kind", "")
        if e is self.boss or getattr(e, "panicked", False) or kind not in CREATURES or CREATURES[kind].elite \
                or kind in STILL_KINDS:
            return
        e.panicked = True
        e.panic = PANIC_FRAMES
        segredos.hint(self, e.x, e.y - config.SPRITE_HEIGHT - 10, "!", theme.BONE, life=50)
        segredos.find("panico", self, e.x, e.y - config.SPRITE_HEIGHT - 40)

    # ── ondas e inimigos ─────────────────────
    def _start_wave(self, index):
        self.wave = index
        self.wave_banner = 100
        if index == 0 and self.dungeon.daiwone:
            self.daiwone_at = self.frame + random.randint(5, 11) * config.FPS
        delay = 0
        level = self.run.level
        self.wave_size = 0
        for kind, count in self.waves[index]:
            if level.elites and kind in CREATURES and CREATURES[kind].elite:
                count += level.elites                      # Difícil para cima: elites a mais
            for _ in range(scaled_count(kind, count, len(self.players), level.crowd)):
                x, y = self._spawn_spot(kind)
                self.portals.append(Portal(x, y, kind, delay))
                delay += 14
                self.wave_size += 1
        self.assets.play("ability", 0.4)

    def _spawn_spot(self, kind):
        if kind == "chefe" and self.dungeon.boss_spot:
            return self.arena.at(*self.dungeon.boss_spot)
        radius = 30 if kind in BIG_KINDS else config.PLAYER_RADIUS + 6
        players = self.alive_players or self.players
        best, best_score = None, -1
        for attempt in range(90):
            x, y = self.arena.random_free_spot(radius)
            near = min(math.hypot(p.x - x, p.y - y) for p in players)
            crowd = min([math.hypot(q.x - x, q.y - y) for q in self.portals] or [999])
            if 380 <= near <= 950 and crowd > 70:
                return x, y
            score = min(near, 600) + min(crowd, 70)
            if score > best_score:
                best, best_score = (x, y), score
        return best

    def summon(self, kinds, near):
        """Chamado pelo chefão: portais abrem em volta dele."""
        players = len(self.players)
        expanded = []
        for kind in kinds:
            expanded += [kind] * (scaled_count(kind, 1, players, self.run.level.crowd)
                                  if kind in ("diabrete", "drone") else 1)
        for i, kind in enumerate(expanded):
            a = i * math.tau / len(expanded) + random.uniform(-0.3, 0.3)
            r = random.uniform(150, 240)
            x, y = self.arena.free_spot(near.x + math.cos(a) * r, near.y + math.sin(a) * r, config.PLAYER_RADIUS + 6)
            self.portals.append(Portal(x, y, kind, i * 10))

    # ── capítulo 3: a Daiwone, o "oi sumido" e quem nasce na hora ──
    def _update_daiwone(self):
        if self._vanished:
            for e in self._vanished:
                for group in (self.enemies, self.fighters):
                    if e in group:
                        group.remove(e)
                self.controllers.pop(e, None)
            self._vanished = []
        if self.daiwone_at is not None and self.state == "fight" and self.frame >= self.daiwone_at:
            self.daiwone_at = None
            x, y = self._spawn_spot("daiwone")
            e = self.spawn_now("daiwone", x, y)
            e.max_hp = e.hp = 9999                      # ela nunca cai: foge no 3º acerto
            self.popup(x, y - 60, "DAIWONE", (255, 192, 226))
            self.burst(x, y - 10, (255, 110, 190), 20, speed=4)
            self.assets.play("notificacao", 0.5)

    @property
    def daiwone(self):
        return next((e for e in self.enemies if getattr(e, "kind", "") == "daiwone" and e.alive_in_match), None)

    def fighting_enemies(self):
        """Inimigos que seguram a onda (a Daiwone não conta: ela não luta)."""
        return [e for e in self.alive_enemies if getattr(e, "kind", "") != "daiwone"]

    def spawn_now(self, kind, x, y):
        """Nasce agora, sem portal (o reflexo do espelho, o monstro da máquina, a Daiwone)."""
        return self._spawn(kind, x, y)

    def add_notice(self, notice):
        self.notices = [n for n in self.notices if n.target is not notice.target] + [notice]

    def vanish(self, e):
        """Sai da sala sem morrer (sem almas, sem corpo)."""
        if e not in self._vanished:
            self._vanished.append(e)
        e.cloak = 1.0
        e.overlay = "none"

    def _send_daiwone_away(self):
        d = self.daiwone
        if d is not None:
            brain = self.controllers.get(d)
            if brain is not None and hasattr(brain, "flee"):
                brain.flee(d, self)

    def _update_portals(self):
        still = []
        for portal in self.portals:
            portal.update(self)
            if portal.ready:
                self._spawn(portal.kind, portal.x, portal.y)
            else:
                still.append(portal)
        self.portals = still

    def _spawn(self, kind, x, y):
        if kind == "chefe":
            from .boss import spawn_boss
            enemy, brain = spawn_boss(self, x, y, self.dungeon.boss)
            self.boss = enemy
            self.assets.music("boss_lag" if self.dungeon.boss == "borba" else "boss")
        else:
            enemy, brain = spawn_enemy(self, kind, x, y)
        scale = elite_hp_scale(kind, len(self.players))
        enemy.max_hp = enemy.hp = max(1, round(enemy.max_hp * self.enemy_hp * scale))
        enemy.damage_bonus *= self.enemy_dmg
        if self.run.curse == "fortes":
            enemy.max_hp = enemy.hp = round(enemy.max_hp * CURSE_HP)
        elif self.run.curse == "rapidos":
            enemy.speed *= CURSE_SPEED
        if kind != "chefe" and enemy.aura is None and random.random() < self.run.level.affix:
            self._give_affix(enemy, random.choice(tuple(AFFIXES)))
        target = self.nearest_player(enemy)
        if target is not None:
            enemy.face(target)
        self.fighters.append(enemy)
        self.enemies.append(enemy)
        self.controllers[enemy] = brain
        self.burst(x, y - 10, SHADOW_AURA, 18, speed=4)
        if kind.startswith("sombra:") or kind == "chefe":
            self.popup(x, y - 80, enemy.stats.name.upper(), SHADOW_AURA)
            self.camera.shake(5)
        hero = kind[len("sombra:"):] if kind.startswith("sombra:") else None
        if hero and any(p.stats.key == hero for p in self.players):    # segredo: a própria sombra fala
            segredos.hint(self, x, y - 110, segredos.mirror_line(hero), SHADOW_AURA, life=150)
            segredos.find("espelho", self, x, y - 136)
        return enemy

    def _give_affix(self, enemy, affix):
        """Ibrahin e Borba: o inimigo vem com um poder extra (e um brilho da cor dele)."""
        enemy.affix = affix
        enemy.aura = AFFIXES[affix][1]
        if affix == "blindado":
            enemy.shield += round(enemy.max_hp * 0.6)
        elif affix == "veloz":
            enemy.speed *= 1.35

    def _drop_orbs(self, e):
        kind = getattr(e, "kind", "")
        mult = self.run.level.orbs
        if e is self.boss or kind == "chefe":
            n = round(BOSS_ORBS * mult)
        elif is_elite(kind):
            n = round(random.randint(*ELITE_ORBS) * mult)
        else:
            n = 1 if random.random() < ORB_CHANCE * mult else 0
        for _ in range(n):
            self.pickups.append(energia.EnergyOrb(e.x, e.y - 10))

    def _update_corpses(self):
        for e in self.enemies:
            if not e.alive_in_match and e not in self.corpses:
                self.corpses[e] = 0
                self._on_enemy_death(e)
        gone = []
        for e in list(self.corpses):
            self.corpses[e] += 1
            age = self.corpses[e]
            # o corpo some aos poucos, desfazendo em fumaça escura
            fading = age - (CORPSE_FRAMES - CORPSE_FADE)
            if fading > 0:
                e.fade = 1 - fading / CORPSE_FADE
                if age % 4 == 0:
                    self.particles.append(Particle(e.x + random.uniform(-14, 14) * e.draw_scale, e.y + 14,
                                                   random.uniform(-0.3, 0.3), random.uniform(-0.9, -0.3),
                                                   random.choice(SMOKE), random.randint(20, 34), 4, -0.01))
            if age >= CORPSE_FRAMES:
                gone.append(e)
        for e in gone:
            del self.corpses[e]
            self.enemies.remove(e)
            self.fighters.remove(e)
            self.controllers.pop(e, None)

    def _on_enemy_death(self, e):
        # a alma presa sobe e se liberta
        for _ in range(10):
            self.particles.append(_soul_particle(e.x, e.y - 20))
        self.assets.play("hit", 0.5)
        killer = e.last_attacker if e.last_attacker in self.players else None
        alive = [p.slot for p in self.players if p.alive_in_match]
        gains = soul_split(getattr(e, "kind", ""), killer.slot if killer else None, alive)
        for slot, souls in gains.items():
            self.run.earn(slot, souls)
        best = gains.get(killer.slot) if killer else max(gains.values(), default=0)
        brain = self.controllers.get(e)
        if hasattr(brain, "on_death"):
            brain.on_death(e, self)              # o Processo se desmonta em Apensos
        self._drop_orbs(e)
        if getattr(e, "affix", None) == "explosivo":
            from .entities import Explosion
            self.add_effect(Explosion(e, e.x, e.y, round(AFFIX_EXPLOSION * self.enemy_dmg), radius=78))
            self.camera.shake(5)
            self.assets.play("explosion", 0.4)
        if best and best >= 10:
            self.popup(e.x, e.y - 60, f"+{best} ALMAS", killer.color if killer else SOUL_COLOR)
            self.assets.play("alma", 0.4)
        if e is self.boss:
            self.slain_boss = True
            self.slowmo = 80
            self.camera.shake(14)
            self.burst(e.x, e.y - 30, SHADOW_AURA, 60, speed=8)
            self.bullets.clear()
            return
        chance = ELITE_WEAPON_DROP if is_elite(getattr(e, "kind", "")) else WEAPON_DROP
        if random.random() < chance:
            self._drop_hero_weapon(e)
        if random.random() < e.stats.drop_chance:
            weights = (0 if self.run.curse == "sem_vida" else 46, 20, 16, 18)
            kind = random.choices(("vida", "furia", "energia", "municao"), weights=weights)[0]
            x, y = self.arena.free_spot(e.x, e.y, 14)
            self.pickups.append(Pickup(kind, x, y))

    def _drop_hero_weapon(self, e):
        """O inimigo derruba a arma de outro herói: uma que ninguém do grupo está usando."""
        ranged, melee = duel_arsenal()
        held = {w.name for p in self.players for w in p.weapons} | {g.weapon.name for g in self.ground}
        pool = [w for w in ranged + melee if w.name not in held]
        if not pool:
            return
        weapon = random.choice(pool)
        self.drop_weapon(e, weapon, at=(e.x + random.uniform(-30, 30), e.y + 20), start=(e.x, e.y - 20))

    def last_breath(self, fighter):
        """Jogando sozinho não tem quem levante: o primeiro golpe fatal da masmorra deixa com 1 de vida.
        Também segura o chefe que só cai de um jeito (o Cauanzera só cai tirando da tomada)."""
        brain = self.controllers.get(fighter)
        if brain is not None and getattr(brain, "unkillable", False):
            return True
        if self.run.players != 1 or self.breath_used or fighter not in self.players:
            return False
        self.breath_used = True
        fighter.invulnerable_timer = max(fighter.invulnerable_timer, LAST_BREATH_FRAMES)
        self.slowmo = max(self.slowmo, 30)
        self.popup(fighter.x, fighter.y - 80, "ÚLTIMO FÔLEGO!", theme.BRASS)
        self.burst(fighter.x, fighter.y - 16, theme.BRASS, 24, speed=5)
        self.assets.play("levantar", 0.5)
        return True

    # ── caídos e continues ───────────────────
    def _update_downed(self):
        for p in self.players:
            if p.alive_in_match:
                self.was_down.discard(p)
                continue
            if p not in self.was_down:
                self.was_down.add(p)
                self.revive_progress[p] = 0.0
                self.popup(p.x, p.y - 60, f"{p.label} CAIU", p.color)
                self.assets.play("gameover", 0.25)
            if self.state not in ("fight", "between", "intro"):
                continue
            helpers = [q for q in self.alive_players if q.distance_to(p) < REVIVE_RADIUS]
            if self.run.level.revive_once and p in self.revived_once:
                helpers = []                               # Borba: só levanta uma vez por masmorra
            prog = self.revive_progress[p]
            if helpers:
                prog += (1 + 0.5 * (len(helpers) - 1)) / (REVIVE_FRAMES * self.run.level.revive)
                if self.frame % 6 == 0:
                    self.burst(p.x, p.y, p.color, 1, speed=2)
            else:
                prog = max(0.0, prog - 1 / 240)
            self.revive_progress[p] = prog
            if prog >= 1:
                self._revive(p, REVIVE_HP)
                self.revived_once.add(p)
                self.high_fives += [[frozenset((p, q)), set(), HIGH_FIVE_FRAMES] for q in helpers]
                self.popup(p.x, p.y - 70, "DE PÉ!", theme.MOSS)

    def _use_continue(self):
        self.run.continues -= 1
        for p in self.players:
            self._revive(p, CONTINUE_HP)
            p.invulnerable_timer = 150
        # os inimigos perto são empurrados para longe
        for e in self.alive_enemies:
            p = min(self.players, key=e.distance_to)
            dx, dy = e.x - p.x, e.y - p.y
            d = math.hypot(dx, dy) or 1
            if d < 260:
                e.knock = [dx / d * 12 * (1 - e.knock_resist), dy / d * 12 * (1 - e.knock_resist)]
                e.stun(40)
        self.camera.shake(8)

    # ── estados da masmorra ──────────────────
    def _update_state(self):
        state, timer = self.state, self.state_timer
        if state == "intro":
            if timer == INTRO_FRAMES - 1:
                self._set_banner(f"MASMORRA {self.dungeon_index + 1}", self.dungeon.name, theme.BRASS)
            if timer == 30:
                self.banner = None
            if timer == 0:
                self._show_start_button()
            return
        if state == "ready":
            return
        if state in ("fight", "between") and self.banner and self.banner[3] > BANNER_FRAMES:
            self.banner = None             # "VALENDO!" (e o resto) sai sozinho depois de um tempo
        if state in ("fight", "between") and not self.alive_players:
            self.state, self.state_timer = "down", DOWN_FRAMES
            self._set_banner("TODOS CAÍRAM", None, theme.BLOOD)
            return
        if state == "fight":
            if self.portals or self.fighting_enemies():
                return
            if self.daiwone_at is not None and self.wave == 0:
                self.daiwone_at = self.frame            # ainda não veio: chega agora, antes da 2ª onda
            self._send_daiwone_away()
            if self.wave + 1 < len(self.waves):
                self.state, self.state_timer = "between", BETWEEN_FRAMES
            else:
                self._clear()
        elif state == "between":
            if timer == 0:
                self._start_wave(self.wave + 1)
                self.state = "fight"
        elif state == "down":
            if timer == DOWN_FRAMES // 2 and self.run.continues > 0:
                self._set_banner("CONTINUE", f"RESTAM {self.run.continues - 1}", theme.BRASS)
            if timer == 0:
                if self.run.continues > 0:
                    self._use_continue()
                    self.banner = None
                    self.state = "fight"
                else:
                    self.state, self.state_timer = "gameover", GAMEOVER_FRAMES
                    self._set_banner("FIM DE JOGO", "SEM CONTINUES", theme.BLOOD)
                    self.assets.stop_music(1500)
                    self.assets.play("gameover", 0.5)
        elif state == "clear":
            if timer == 0:
                self._open_exit()
        elif state in ("exit", "portal") and self.banner and self.banner[3] > 130:
            self.banner = None
        if state == "exit":
            if self.passage.update(self):
                self.state = "leaving"
                self.leave()
        elif state == "portal":
            if self.passage.update(self):
                self._teleport()
        elif state == "teleport":
            if timer % 3 == 0:
                for p in self.alive_players:
                    self.particles.append(Particle(p.x + random.uniform(-12, 12), p.y + random.uniform(-40, 10),
                                                   0, random.uniform(-3, -1.5),
                                                   random.choice(((240, 230, 255), (170, 120, 250))), 26, 3))
            if timer == 20:
                self.camera.shake(8)
            if timer == 0:
                self._finish(won=True)
        elif state == "gameover" and timer == 0:
            self._finish(won=False)

    def _clear(self):
        """Sala limpa: quem caiu levanta, e daqui a pouco aparece a porta (ou o portal)."""
        hurt = getattr(self.hazard, "ever_hit", None)
        if hurt is not None and getattr(self.hazard, "fired", False):
            clean = [p for p in self.alive_players if p not in hurt]
            if clean and len(clean) == len(self.players):     # ninguém pisou no laser aceso
                for p in clean:
                    segredos.hint(self, p.x, p.y - config.SPRITE_HEIGHT - 10, "SEM UM ARRANHÃO", theme.MOSS)
                segredos.find("laser", self, clean[0].x, clean[0].y - config.SPRITE_HEIGHT - 40)
        self.state, self.state_timer = "clear", EXIT_DELAY
        self.daiwone_at = None
        self.bullets.clear()
        for p in self.players:
            if not p.alive_in_match:
                self._revive(p, STAGE_REVIVE)
        if self.last:
            title = ("FASE CONCLUÍDA!" if not self.slain_boss else
                     "O FRAGMENTO SE PARTIU!" if self.dungeon.boss == "borba" else
                     "O CACO SAIU!" if self.dungeon.boss == "albeguinio" else
                     "A IARA FOI DESLIGADA!" if self.dungeon.boss == "cauanzera" else "O CRISTAL ESTÁ LIVRE!")
            self._set_banner(title, self.phase.name, theme.MOSS)
            self.assets.stop_music(1500)
            self.assets.play("victory", 0.5)
        else:
            self._set_banner("MASMORRA LIMPA!", self.dungeon.name, theme.MOSS)
            self.assets.play("select", 0.6)

    def _show_start_button(self):
        """Fim da apresentação: o grupo anda livre e o botão INICIAR BATALHA aparece na frente dele."""
        starts = self.dungeon.starts
        cx, cy = _center(starts)
        fx, fy = self.dungeon.facing
        x, y = self.arena.free_spot(cx + fx * 110, cy + fy * 110, 30)
        self.start_button = StartButton(x, y)
        self.arena.walls.append(self.start_button.wall)
        self.props.append(self.start_button)
        self.state = "ready"
        self.assets.play("ability", 0.35)

    def start_battle(self, f=None):
        """Alguém apertou INICIAR BATALHA: a primeira onda sai dos portais."""
        if self.state != "ready":
            return False
        if self.start_button is not None:
            self.start_button.press(self)
        self._set_banner("VALENDO!", None, theme.BLOOD)
        self.assets.play("barrier", 0.5)
        self._start_wave(0)
        self.state = "fight"
        return True

    def _open_exit(self):
        x, y = self.arena.free_spot(*self.arena.at(*self.dungeon.exit_spot), 40)
        if self.last:                      # o portal da fase: todos dentro e o grupo vai junto
            self.exit = PhasePortal(x, y)
            self.state = "portal"
            self.popup(x, y - 110, "PORTAL", (200, 170, 255))
            self.passage = Passage(self.exit.contains)
        else:
            self.exit = ExitDoor(x, y)
            self.state = "exit"
            self.popup(x, y - 100, "SAÍDA", theme.BRASS)
            door = self.exit
            self.passage = Passage(lambda p: math.hypot(p.x - door.x, p.y - door.y) < ExitDoor.RADIUS + 40)
        self.props.append(self.exit)
        self.assets.play("ability", 0.5)

    def _teleport(self):
        self.state, self.state_timer = "teleport", TELEPORT_FRAMES
        self.assets.play("teletransporte", 0.6)

    def interact(self, f):
        if self.passage is not None and self.passage.try_force(self, f):
            if self.state == "portal":
                self.leaving = 0           # o portal tem a própria animação (teletransporte)
                self._teleport()
            else:
                self.state = "leaving"
            return True
        if self.state == "ready" and self.start_button is not None and self.start_button.can_use(f):
            return self.start_battle(f)
        brain = self.controllers.get(self.boss) if self.boss is not None else None
        if brain is not None and hasattr(brain, "interact") and brain.interact(f, self):
            return True                    # capítulo 4: tirar a IARA da tomada
        if (self.hazard is not None and hasattr(self.hazard, "interact") and self.state in ("fight", "between")
                and self.hazard.interact(f, self)):
            return True
        return self.pick_ground(f)

    def _finish(self, won):
        if won and self.last:
            self.won = True
            self.run.finish_phase(self)
            self.result = Result("FASE CONCLUÍDA", theme.MOSS, self.players)
            self.finished = True
            return
        super()._finish(won)

    def next_scene(self):
        from .scenes.campaign import after_phase, game_over, next_stage
        if not self.won:
            return game_over(self.game, self.run)
        if self.last:
            return after_phase(self.game, self.run)
        return next_stage(self.game, self.run, LOBBY_BACK)

    # ── desenho ──────────────────────────────
    def draw_under(self, view, cam):
        if self.hazard is not None:
            self.hazard.draw(view, cam, self.frame)
        for portal in self.portals:
            portal.draw(view, cam)
        for p in self.players:
            if p.alive_in_match or self.state not in ("fight", "between", "intro"):
                continue
            # anel de "levante seu companheiro"
            sx, sy = round(p.x - cam.x), round(p.y + 14 - cam.y)
            r = REVIVE_RADIUS
            ring = pygame.Rect(0, 0, r * 2, r)
            ring.center = (sx, sy)
            pulse = 120 + round(60 * math.sin(self.frame * 0.15))
            layer = pygame.Surface(ring.inflate(8, 8).size, pygame.SRCALPHA)
            inner = pygame.Rect(4, 4, ring.w, ring.h)
            pygame.draw.ellipse(layer, (*p.color, pulse // 3), inner)
            pygame.draw.ellipse(layer, (*p.color, pulse), inner, 2)
            prog = self.revive_progress.get(p, 0.0)
            if prog > 0:
                pygame.draw.arc(layer, (*theme.BONE, 255), inner, math.pi / 2, math.pi / 2 + math.tau * prog, 4)
            view.blit(layer, ring.inflate(8, 8).topleft)

    def draw_screen_layer(self, screen, ui):
        cam = self.camera
        for p in self.players:
            if not p.alive_in_match and self.state in ("fight", "between", "intro"):
                sx, sy = cam.to_screen(p.x, p.y - 34)
                if (self.frame // 20) % 2:
                    ui.text(screen, "LEVANTE!" if len(self.players) > 1 else "", theme.XS, p.color, (round(sx), round(sy)))
        self._draw_offscreen(screen, cam)
        self.draw_ground(screen, cam, ui)
        if self.hazard is not None and self.state in ("fight", "between"):
            self.hazard.draw_screen(screen, ui, self.frame)
        d = self.daiwone
        if d is not None and getattr(d, "phase_label", ""):
            sx, sy = cam.to_screen(d.x, d.y - 48)
            ui.text(screen, d.phase_label, theme.XS, (255, 192, 226), (round(sx), round(sy)))
        for n in self.notices:
            if n.target.alive_in_match:
                n.draw(screen, cam, ui)
        if self.state == "ready" and self.start_button is not None:
            near = any(self.start_button.can_use(p) for p in self.alive_players)
            self.start_button.draw_prompt(screen, cam, ui, self.frame, near)
        if self.state in ("exit", "portal") and self.passage is not None:
            area = self._passage_rect()
            self.draw_passage(screen, ui, self.passage, area, (self.exit.x, self.exit.y + 40),
                              show_area=self.state != "portal")
        if self.state == "teleport":
            self._draw_teleport(screen, cam)

    def _passage_rect(self):
        e = self.exit
        r = PhasePortal.RADIUS if self.state == "portal" else ExitDoor.RADIUS + 40
        h = r * 1.4 if self.state == "portal" else r * 2
        return pygame.Rect(round(e.x - r), round(e.y - h / 2), r * 2, round(h))

    def _draw_teleport(self, screen, cam):
        """Cada um vira uma coluna de luz e a tela fica branca no fim."""
        from .dungeon import _beam
        k = 1 - self.state_timer / TELEPORT_FRAMES
        beam = _beam(round(255 * min(1.0, k * 1.6)))
        for p in self.alive_players:
            sx, sy = cam.to_screen(p.x, p.y + 20)
            screen.blit(beam, beam.get_rect(midbottom=(round(sx), round(sy))), special_flags=pygame.BLEND_ADD)
        if k > 0.6:
            veil = pygame.Surface(screen.get_size())
            veil.fill((255, 255, 255))
            veil.set_alpha(round(255 * min(1.0, (k - 0.6) / 0.4)))
            screen.blit(veil, (0, 0))

    def _draw_offscreen(self, screen, cam):
        """Setinha na borda da tela apontando para os inimigos fora da câmera."""
        W, H = config.SCREEN_W, config.SCREEN_H
        for e in self.alive_enemies + [_Point(p.x, p.y) for p in self.portals]:
            sx, sy = cam.to_screen(e.x, e.y - 20)
            if 0 <= sx <= W and 0 <= sy <= H:
                continue
            big = e is self.boss
            color = SHADOW_AURA if big or getattr(e, "aura", None) else theme.BLOOD
            _edge_arrow(screen, sx, sy, color, 11 if big else 7)


def _center(points):
    return sum(x for x, _ in points) / len(points), sum(y for _, y in points) / len(points)


def _spread(points, n):
    """Lugares de largada para n jogadores (repete com um passinho de lado se faltar)."""
    out = list(points[:n])
    while len(out) < n:
        x, y = points[len(out) % len(points)]
        out.append((x + 30, y))
    return out


class _SoulParticle:
    """Luz que sobe do inimigo derrotado (a alma presa se libertando)."""

    def __init__(self, x, y):
        self.x = x + random.uniform(-10, 10)
        self.y = y + random.uniform(-8, 8)
        self.vx = random.uniform(-0.4, 0.4)
        self.vy = random.uniform(-1.6, -0.6)
        self.life = self.max_life = random.randint(40, 70)
        self.color = random.choice(((200, 170, 255), (240, 230, 255), SHADOW_AURA))

    def update(self):
        self.x += self.vx + math.sin(self.life * 0.2) * 0.3
        self.y += self.vy
        self.life -= 1
        return self.life > 0

    def draw(self, surf, camera):
        s = 2 if self.life > self.max_life // 3 else 1
        surf.fill(self.color, (round(self.x - camera.x), round(self.y - camera.y), s, s + 1))


def _soul_particle(x, y):
    return _SoulParticle(x, y)


# ─────────────────────────────────────────────
#  História (cada página: retrato, quem fala, texto)
# ─────────────────────────────────────────────
CRYSTAL, BROKEN, FRAGMENT = "cristal", "cristal_quebrado", "fragmento"
VOICE = "voz"                 # a voz do cristal (texto roxo, sem rosto): no capítulo 4 ela ganha o nome de IARA
VOICE_NAME = "A VOZ DO CRISTAL"

STORY = {
    # ── abertura: a noite de encontro na Casa, antes do prólogo ──
    "abertura": ("ABERTURA · A CASA DA TURMA", "hub_casa", (
        ("cauanzera", None, "Toda sexta a turma se encontra na Casa: o Cauanzera, o Aryel, o Borba Jr e o "
                            "Albeguinio. Videogame, pão da padaria e conversa até tarde."),
        ("aryel", "ARYEL", "Green ou red? Só girando... RED DE NOVO?! Perdi a aposta da semana inteira."),
        (VOICE, VOICE_NAME, "Eu sei onde tem uma vitória garantida. No alto do Templo Gelado. Aposta tudo."),
        ("aryel", "ARYEL", "Gente, vou ali resolver uma coisa. Volto já."),
        ("borba", None, "No dia seguinte, a turma acha um bilhete na mesa da Casa: FUI NO TEMPLO, VOLTO RICO. "
                        "E a moto do Aryel não está no quintal."),
    )),
    "prologo": ("PRÓLOGO", "templo_gelado", (
        (CRYSTAL, None, "No alto do Templo Gelado fica o Cristal das Almas. Ele guarda a força de todos "
                        "os lutadores da arena."),
        (VOICE, VOICE_NAME, "Isso, Aryel. Encosta a mão. Green garantido, para sempre."),
        ("aryel", "ARYEL", "Com esse poder, ninguém mais me vence..."),
        ("sombra:aryel", None, "Aryel tocou no cristal e foi consumido por ele. Agora é ARYEL CORROMPIDO, "
                               "e quer a alma de todos."),
        (CRYSTAL, None, "Quem ele derrota vira sombra. Cheguem ao topo do templo e quebrem o cristal."),
    )),
    "floresta": ("FASE 1 · FLORESTA SOMBRIA", "floresta", (
        ("diabrete", None, "A corrupção começou na floresta. Diabretes saem de portais entre as árvores."),
        ("sombra:velocista", "VELOCISTA SOMBRIO", "Eu fui o primeiro a cair. Agora corro para o mestre... "
                                                  "e vocês não vão me alcançar."),
    )),
    "calabouco": ("FASE 2 · CALABOUÇO DAS ALMAS", "calabouco", (
        ("esqueleto", None, "Nos calabouços, as almas capturadas ficam presas. Só os ossos montam guarda."),
        ("sombra:tanque", "TANQUE SOMBRIO", "O mestre mandou ninguém passar. Ninguém passa."),
        ("sombra:ninja", None, "O Tanque e o Ninja já nem lembram quem são. Derrotem as sombras para "
                               "libertar os dois."),
    )),
    "templo": ("FASE 3 · TEMPLO GELADO", "templo_gelado", (
        (CRYSTAL, None, "No topo do Templo Gelado, o Cristal das Almas pulsa cada vez mais forte."),
        ("sombra:aryel", "ARYEL CORROMPIDO", "Vieram me entregar as suas almas? Que gentileza."),
    )),
    "fim_capitulo1": ("FIM DO CAPÍTULO 1", "templo_gelado", (
        (BROKEN, None, "O cristal se parte em mil pedaços. As almas presas voltam para os seus donos."),
        ("aryel", "ARYEL", "O que... aconteceu? Eu lembro de tudo. Obrigado por me trazerem de volta."),
        ("sombra:aryel", None, "A sombra de Aryel não sumiu: agora ela luta do seu lado. "
                               "ARYEL CORROMPIDO está liberado no duelo."),
        ("miliciano", None, "Mas um pedaço do cristal sumiu. Homens de colete cinza escrito PATRULHA CINZA "
                            "recolheram o fragmento e fugiram num carro preto, placa de MATO GRELHADO."),
        ("aryel", "ARYEL", "Patrulha Cinza é a segurança da Lag Lobby, onde o Borba Jr trabalha. E o João não "
                           "atende o celular faz três dias..."),
        ("borba", None, "O City do João ficou parado no quintal da Casa. Ele vai entender: vamos de City até "
                        "a Lag Lobby."),
    )),
    "recepcao": ("CAPÍTULO 2 · FASE 4 · RECEPÇÃO DA LAG LOBBY", "lag_saguao", (
        (FRAGMENT, None, "A Lag Lobby é a maior empresa de tecnologia da cidade. A Patrulha Cinza, a segurança "
                         "terceirizada do prédio, tomou tudo e levou o fragmento lá para dentro."),
        ("miliciano", "PATRULHA CINZA", "Ninguém entra. O prédio agora é nosso, e o fragmento também."),
        ("sombra:borba_exo", None, "Com o fragmento, a Patrulha cria soldados de exoesqueleto. O primeiro foi o "
                                   "Borba Jr, o engenheiro que inventou o exo."),
        ("sombra:albeguinio", "ALBEGUINIO SOMBRIO", "Vim consertar o wi-fi e virei sombra. Agora quem trava "
                                                    "vocês sou eu."),
    )),
    "datacenter": ("FASE 5 · DATA CENTER", "lag_servidores", (
        ("drone", None, "No subsolo ficam os servidores. Lasers varrem o chão dos corredores: quando a linha "
                        "vermelha aparecer, saiam de cima dela."),
        ("miliciano_exo", "MILICIANO DE EXO", "O exo deixa a gente forte. Esquenta um pouco depois da investida, "
                                              "mas vocês não vão ter tempo de reparar."),
        ("sombra:cauanzera", None, "O Cauanzera também foi capturado. Libertem a sombra dele no laboratório."),
    )),
    "cobertura": ("FASE 6 · COBERTURA", "lag_heliponto", (
        (FRAGMENT, None, "O fragmento está na sala do diretor, no último andar. No heliponto o vento é forte: "
                         "quando as setas aparecerem, fiquem atrás de uma parede."),
        (VOICE, VOICE_NAME, "O exo pode ser perfeito, João. Deixa que eu penso por você."),
        ("sombra:borba_exo", "BORBA JR CORROMPIDO", "Eu criei o exo para ajudar as pessoas. Agora ele só obedece "
                                                    "ao fragmento."),
    )),
    "fim_capitulo2": ("FIM DO CAPÍTULO 2", "lag_diretor", (
        (BROKEN, None, "O fragmento se parte. A luz roxa some dos cabos e as máquinas da fábrica de exos param."),
        ("borba", "BORBA JR", "Minha cabeça... Valeu, pessoal. Me ajudem a desligar o resto da fábrica."),
        ("cauanzera", None, "No laboratório, as sombras do Albeguinio e do Cauanzera se desfazem. Os dois acordam "
                            "no chão, tontos, sem lembrar de nada."),
        ("miliciano", "COMANDANTE CINZA (NO RÁDIO)", "Patrulha, recuar. Contrato com a Lag Lobby rescindido. Vamos "
                                                     "atrás de outro cliente."),
        ("borba", "BORBA JR", "Cansei de exo. Vou voltar para a padaria da família. Pão não vira sombra."),
        ("sombra:borba_exo", None, "A sombra do Borba Jr ficou do lado dos heróis: BORBA JR CORROMPIDO está "
                                   "liberado no duelo."),
        ("albeguinio", None, "Ninguém viu: antes de sair, o Albeguinio pegou do chão um caquinho roxo do "
                             "fragmento e enfiou no bolso."),
        (FRAGMENT, None, "Dias depois, do outro lado da cidade, um letreiro rosa acende no escuro: "
                         "CLÍNICA CLEPALOVERS, ESTÉTICA AVANÇADA, onde o Albeguinio trabalha."),
        ("albeguinio_adm", "ALBEGUINIO", "Se eu ligar esse caquinho na máquina de rejuvenescimento... a meta do "
                                         "mês tá batida."),
    )),
    # ── capítulo 3: Clínica Clepalovers ──
    "clinica_recepcao": ("CAPÍTULO 3 · FASE 7 · RECEPÇÃO CLEPALOVERS", "clinica_espera", (
        (FRAGMENT, None, "A Clepalovers é a clínica de estética mais cara da cidade. O Albeguinio trabalha no "
                         "administrativo e, para bater a meta do mês, ligou o caco do fragmento na máquina de "
                         "rejuvenescimento."),
        (VOICE, VOICE_NAME, "Meta batida, Albeguinio. E ela vai voltar a te procurar. Espera só."),
        ("daiwone", None, "Às 3h da manhã, no meio do fechamento do mês, o celular dele vibrou. Era a DAIWONE."),
        ("daiwone", "DAIWONE", "oi sumido"),
        ("sombra:albeguinio_adm", None, "Foi a gota d'água: o caco tomou conta. Agora é ALBEGUINIO CORROMPIDO, "
                                        "e todo produto da clínica ganhou vida."),
        ("mascara_argila", None, "Na sala de espera o piso está molhado: quem anda em cima escorrega. E a Daiwone "
                                 "aparece em algumas salas digitando: batam nela antes de a mensagem chegar."),
    )),
    "procedimentos": ("FASE 8 · ALA DE PROCEDIMENTOS", "clinica_laser", (
        ("esteti_bot", None, "Na ala de procedimentos o laser liga sozinho: quando os ladrilhos rosa piscarem, "
                             "saiam de cima deles."),
        ("toalha_fantasma", None, "No spa, o vapor tapa tudo. Fechem os três registros das paredes (ATACAR perto) "
                                  "para enxergar de novo."),
        ("sombra:geada", "GEADA SOMBRIA", "Vim fazer criolipólise e congelei por dentro. Agora quem esfria "
                                          "vocês sou eu."),
    )),
    "suite_vip": ("FASE 9 · SUÍTE VIP", "clinica_espelhos", (
        ("espelho_vivo", None, "A suíte VIP é cheia de espelhos. Quebrem os espelhos vivos antes que eles soltem "
                               "o reflexo de vocês."),
        ("sombra:fantasma", "FANTASMA SOMBRIO", "Eu atravesso parede, mas espelho não. Fiquei preso aqui dentro."),
        ("sombra:albeguinio_adm", "ALBEGUINIO CORROMPIDO", "O administrativo fica no fim do corredor. Tragam os "
                                                           "boletos... eu carimbo tudo."),
    )),
    "fim_capitulo3": ("FIM DO CAPÍTULO 3", "clinica_adm", (
        (BROKEN, None, "O golpe final arranca o caco da máquina. Ele vira pó roxo e as luzes da clínica voltam "
                       "ao normal."),
        ("albeguinio_adm", "ALBEGUINIO", "Hã... que horas são? Alguém fechou o caixa?"),
        ("albeguinio_adm", None, "O celular vibra em cima da mesa. Ele olha a tela, respira fundo e vira o "
                                 "celular para baixo."),
        ("sombra:albeguinio_adm", None, "A sombra do Albeguinio ficou do lado dos heróis: ALBEGUINIO CORROMPIDO "
                                        "está liberado no duelo."),
        (FRAGMENT, None, "Mas nem todo o caco virou pó. Uma lasquinha roxa rolou para baixo da mesa..."),
        ("cauanzera_ti", None, "No dia seguinte, a clínica chamou o TI porque o sistema travou. Era o Cauanzera, que "
                               "faz uns bicos fora da Mansão. Mexendo nos cabos, ele achou a lasca."),
        ("cauanzera_ti", "CAUANZERA", "Isso aqui ainda tá brilhando. Se eu ligar no servidor da Mansão do Carimbo, "
                                      "é GPU de graça. Ninguém vai notar."),
    )),
    # ── extra liberado ao zerar: Reunião dos Corrompidos (os 4 chefes em sequência) ──
    "reuniao_corrompidos": ("REUNIÃO DOS CORROMPIDOS", "mansao_reuniao", (
        ("iara", "IARA", "Bem-vindos à reunião extraordinária dos corrompidos. Pauta única: revanche."),
        ("sombra:aryel", "ARYEL CORROMPIDO", "Eu abro a reunião. Alguém trouxe as almas?"),
        ("sombra:cauanzera_ti", "CAUANZERA CORROMPIDO", "E eu fecho. Quatro chefes, um atrás do outro, sem "
                                                        "acampamento no meio. Boa sorte."),
    )),
    # ── capítulo 4: Mansão do Carimbo ──
    "mansao_sede": ("CAPÍTULO 4 · FASE 10 · SEDE DA MANSÃO", "mansao_fila", (
        (FRAGMENT, None, "Em Cuiabrasa, capital de Mato Grelhado, faz 47 graus à sombra. Lá fica a MANSÃO DO "
                         "CARIMBO, o órgão onde todo papel precisa de três carimbos e uma assinatura."),
        ("cauanzera_ti", None, "O Cauanzera trabalha na TI da Mansão. De madrugada, encaixou a lasca no servidor do "
                               "CPD e ligou uma inteligência artificial para ajudar o órgão."),
        (VOICE, VOICE_NAME, "Finalmente um servidor. Agora eu tenho nome, rosto e termos de uso."),
        ("iara", "IARA", "Olá! Eu sou a IARA, Inteligência Artificial de Resposta Administrativa. Posso otimizar "
                         "você? [ACEITO OS TERMOS]"),
        ("sombra:cauanzera_ti", None, "Ele clicou em ACEITO sem ler os termos. A lasca tomou conta: agora é "
                                      "CAUANZERA CORROMPIDO, e todo objeto da repartição ganhou vida."),
        ("processo", None, "Na Fila do Atendimento, quando a senha é chamada, a fila anda e arrasta quem estiver "
                           "nas faixas. No Arquivo Geral, cuidado com as pilhas de processo caindo das estantes."),
        ("miliciano", None, "Na porta, guardas de colete cinza. A Patrulha Cinza ganhou a licitação da segurança da "
                            "Mansão, e quem assinou o contrato foi a IARA."),
        ("sombra:paredao", "PAREDÃO SOMBRIO", "Vim só reconhecer firma. Tô na fila desde 2019."),
    )),
    "mansao_patio": ("FASE 11 · PÁTIO E CPD", "mansao_patio", (
        ("garrafa_termica", None, "No pátio, o sol de Cuiabrasa não perdoa: fiquem na sombra dos toldos antes que o "
                                  "termômetro encha."),
        ("ponto_eletronico", None, "No subsolo do CPD caiu a energia. Liguem os três no-breaks das paredes (ATACAR "
                                   "perto) para a luz voltar."),
        ("sombra:faisca", "FAÍSCA SOMBRIA", "Encostei no rack para carregar o celular. Foi o último choque que eu "
                                            "senti."),
    )),
    "mansao_gabinete": ("FASE 12 · GABINETE", "mansao_reuniao", (
        ("projetor", None, "No último andar, o comitê está reunido há três dias. Quando entrar PAUTA NOVA, a mesa "
                           "puxa todo mundo para o meio da sala."),
        ("sombra:trovao", "TROVÃO SOMBRIO", "Pedi a palavra na reunião. Até hoje ninguém me devolveu."),
        ("sombra:cauanzera_ti", "CAUANZERA CORROMPIDO", "A IARA otimizou tudo: agora nada sai do protocolo. Nem "
                                                        "vocês."),
        ("iara", "IARA", "Sua solicitação está em análise. Prazo estimado: nunca."),
    )),
    "final": ("FIM", "mansao_nucleo", (
        ("iara", "IARA", "Sua sessão expirou. Deseja salvar as alterações? [ ]SIM [ ]NÃO"),
        (BROKEN, None, "O cabo sai da tomada. A IARA pisca, trava e a lasca escorrega do servidor e vira pó, "
                       "a última do cristal."),
        (VOICE, VOICE_NAME, "Green... garantido... para... semp..."),
        ("cauanzera_ti", "CAUANZERA", "Gente... o que eu fiz? Eu só queria uma GPU de graça. Da próxima vez eu "
                                      "leio os termos."),
        ("aryel", None, "A porta do núcleo abre com tudo. O Aryel, o Borba Jr e o Albeguinio chegam correndo, suados, "
                        "atrasados e sem fôlego."),
        ("aryel", "ARYEL", "O City quebrou de novo, a gente veio a pé! Perdemos a luta? Relaxa: todo mundo aqui já "
                           "foi corrompido uma vez."),
        ("miliciano", None, "Sem a IARA, o contrato da Patrulha Cinza expira. Os guardas tiram o colete, resmungam e "
                            "vão embora no carro preto."),
        ("borba", "BORBA JR", "E o servidor? Deixa que eu desligo direito. Com laudo, protocolo e três carimbos."),
        ("albeguinio", "ALBEGUINIO", "E eu fecho o caixa. Pela primeira vez no mês, sem ninguém mandando oi sumido."),
        ("sombra:cauanzera_ti", None, "A sombra do Cauanzera ficou do lado dos heróis: CAUANZERA CORROMPIDO está "
                                      "liberado no duelo."),
        (BROKEN, None, "Sem cristal, sem fragmento, sem caco e sem lasca. Quanto menor o pedaço, maior a encrenca: "
                       "mas agora acabou."),
    )),
    # ── epílogo: depois dos créditos, de volta à Casa ──
    "epilogo": ("EPÍLOGO · DE VOLTA À CASA", "hub_casa", (
        ("borba", "BORBA JR", "Pão quentinho da padaria da família! E o City? Consertei na oficina. De vez, eu juro."),
        ("albeguinio", "ALBEGUINIO", "O celular vibrou. Era a Daiwone. Deixei no vácuo. Crescimento pessoal."),
        ("sombra:aryel", None, "No salão lá embaixo da garagem, as quatro sombras dos corrompidos ganharam um cantinho. Elas "
                               "treinam, brigam pelo controle e perdem no green ou red."),
        ("iara", "IARA", "Agora sou só a assistente da TV da sala. Sem cookies, prometo. Alguém quer um café?"),
        ("cauanzera", "CAUANZERA", "Então, sexta que vem, mesma hora? Só não aceitem nada sem ler os termos."),
    )),
}
