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

from . import config, hud, theme
from .ai import FighterAI
from .entities import Particle, Pickup
from .enemies import BIG_KINDS, CREATURES, SHADOW_AURA, SMOKE, Portal, spawn_enemy
from .arena import MAPS_BY_KEY
from .matches import Match, Result, _separate
from .net.remote import hub
from .ui import darken
from .data import PHASE_RELICS, RARE_WEAPONS, common_weapon, duel_arsenal, rarity_color
from .dungeon import Campfire, Chest, ExitDoor, Gate, GroundWeapon, RelicDrop
from .hazards import make_hazard
from .lobbies import cells_rect
from .market import CURSE_HP, CURSE_SPEED, CURSES, ENCHANTS, MAX_LEVEL, MAX_REROLLS, SOUL_COLOR, MarketMenu, Stall, soul_split
from .upgrades import apply_all

PLAYERS, ENEMIES = 0, 1
CONTINUES = 3
PHASE_HEAL = 0.35             # entre uma fase e outra, recupera esse tanto da vida
REVIVE_FRAMES = 120           # tempo perto de um companheiro caído para levantá-lo
REVIVE_RADIUS = 56
REVIVE_HP = 0.4
CONTINUE_HP = 0.5
LAST_BREATH_FRAMES = 90       # invencível depois do último fôlego (campanha solo)
LEASH_X, LEASH_Y = 1500, 700  # quão longe os jogadores podem ficar uns dos outros (cabe na câmera a 50%)
LEASH_PULL_FRAMES = 3 * config.FPS  # forçando o limite por tanto tempo: aparece ao lado do grupo
INTRO_FRAMES = 150
BETWEEN_FRAMES = 110
CLEAR_FRAMES = 200
DOWN_FRAMES = 150
GAMEOVER_FRAMES = 220
CORPSE_FRAMES = 80
CORPSE_FADE = 32              # últimos quadros do corpo: vai sumindo
SOLO_DAMAGE = 0.85
WEAPON_DROP = 0.04             # chance de um inimigo comum derrubar a arma de outro herói
ELITE_WEAPON_DROP = 0.4       # ... e de um elite (golem, sombra)
MAX_GROUND = 6                # armas no chão ao mesmo tempo (a mais velha some)

# dificuldade da campanha: (vida dos inimigos, dano dos inimigos)
DIFFICULTY = {"facil": (0.75, 0.7), "normal": (1.0, 1.0), "dificil": (1.3, 1.25)}


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


@dataclass(frozen=True)
class Phase:
    """Uma fase: o acampamento (lobby, no tema da fase) e duas masmorras.

    Caminho: acampamento → masmorra 1 → acampamento (baú escondido) → masmorra 2 → portal."""
    key: str
    name: str
    theme: str                # tema do acampamento (floresta, calabouco, templo_gelado, lag_...)
    dungeons: tuple
    chapter: int = 1          # capítulo 1: Templo Gelado; capítulo 2: Lag Lobby

    @property
    def lobby(self):
        return f"acampamento_{self.theme}"


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
)
CHAPTER_START = {ch: next(i for i, p in enumerate(PHASES) if p.chapter == ch) for ch in (1, 2)}
CHAPTER2_SOULS = 120          # começando do capítulo 2: almas para a loja da primeira fase
CHAPTER2_UPGRADES = 2         # ... e melhorias sorteadas (mais a escolhida antes de entrar)

# etapas de uma fase (CampaignRun.stage)
LOBBY_START, DUNGEON_1, LOBBY_BACK, DUNGEON_2 = range(4)
STAGE_REVIVE = 0.3            # quem estava caído ao fim de uma masmorra volta com essa vida


def is_elite(kind):
    return kind == "chefe" or kind.startswith("sombra:") or CREATURES[kind].elite


def scaled_count(kind, base, players):
    """Mais jogadores, mais inimigos: +50% dos comuns por jogador a mais (os fortes ganham vida)."""
    if is_elite(kind):
        return base
    return max(1, round(base * (1 + 0.5 * (players - 1))))


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
        self.continues = CONTINUES
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
        self._snapshot = None

    @property
    def phase(self):
        return PHASES[self.phase_index]

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

    def start_at_chapter(self, chapter):
        """Começa direto num capítulo já liberado: almas e melhorias sorteadas para compensar."""
        from .upgrades import choices
        self.start_chapter = chapter
        self.phase_index = CHAPTER_START[chapter]
        if chapter > 1:
            for s in self.slots:
                self.souls[s] += CHAPTER2_SOULS
                for _ in range(CHAPTER2_UPGRADES):
                    self.upgrades[s].append(random.choice(choices(self.upgrades[s])))

    def _state(self):
        return {k: copy.deepcopy(getattr(self, k))
                for k in ("phase_index", "continues", "upgrades", "hp_ratio", "kills", "damage", "frames",
                          "stage", "chest_open", "relics", "held", "loadouts", "souls", "forge", "rerolls",
                          "fused_phase", "curse", "start_chapter")}

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
        """Começa a fase no acampamento e guarda como tudo estava (para TENTAR DE NOVO)."""
        self.stage = LOBBY_START
        self.chest_open = False
        self._snapshot = self._state()

    def retry_phase(self):
        if self._snapshot is not None:
            for k, v in copy.deepcopy(self._snapshot).items():
                setattr(self, k, v)
        self.continues = max(self.continues, 1)
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
            fighter.give_relic(relic)
        fighter.weapon_index = min(self.held.get(fighter.slot, 0), len(fighter.weapons) - 1)
        fighter.hp = max(1, round(fighter.max_hp * self.hp_ratio.get(fighter.slot, 1.0)))

    def carry(self, match):
        """Fim de uma etapa: vida, arma na mão, arma rara e as contas passam para a próxima."""
        for f in match.players:
            self.hp_ratio[f.slot] = f.hp / f.max_hp if f.hp > 0 else STAGE_REVIVE
            self.kills[f.slot] += f.kills
            self.damage[f.slot] += f.damage_dealt
            self.held[f.slot] = f.weapon_index
            self.relics[f.slot] = relic_key(f.relic)
            self.loadouts[f.slot] = [w.name for w in f.loadout] if f.loadout else None
        self.frames += match.frame

    def finish_phase(self, match):
        """Fim da fase (portal): leva tudo e ainda recupera um pouco da vida."""
        for f in match.players:
            if f.hp <= 0:
                f.hp = 0
        self.carry(match)
        for f in match.players:
            ratio = f.hp / f.max_hp if f.hp > 0 else 0.0
            self.hp_ratio[f.slot] = min(1.0, ratio + PHASE_HEAL)

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
            run.continues = max(1, int(state["continues"]))
            run.frames = int(state["frames"])
            run.kills = {s: int(v) for s, v in run.kills.items()}
            run.damage = {s: int(v) for s, v in run.damage.items()}
            run.held = {s: int(v) for s, v in run.held.items()}
            loadouts = {int(s): v for s, v in state.get("loadouts", {}).items()}   # saves antigos não têm
            for s in run.slots:
                names = loadouts.get(s)
                if names is not None:
                    weapons = [common_weapon(n) for n in names]
                    if len(weapons) != 2 or None in weapons or [w.is_melee for w in weapons] != [False, True]:
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
            run.start_chapter = 2 if int(state.get("start_chapter", 1)) == 2 else 1
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


class CoopMatch(Match):
    """Base das etapas da campanha (acampamento e masmorra): os jogadores do mesmo time,
    a mira, levantar quem caiu, os itens, o escurecer entre uma etapa e outra e o HUD."""

    min_zoom = 0.5            # bem de longe, a pixel art fica no tamanho original (2 por 1)
    lobby = False

    def __init__(self, game, run, map_key, starts, facing):
        self.run = run
        self.phase = run.phase
        super().__init__(game, run.session, map_key)
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
        return [(p.x, p.y - 20) for p in self.players]

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
        herói do mesmo tipo (de tiro ou de perto). A que ele tinha fica no lugar."""
        near = [g for g in self.ground if g.alive and g.can_pick(f)]
        if not near:
            return False
        item = min(near, key=f.distance_to)
        item.alive = False
        self.ground.remove(item)
        if item.weapon.rare:
            self.give_relic(f, item.weapon, drop_at=(item.x, item.y))
        else:
            self.give_common(f, item.weapon, drop_at=(item.x, item.y))
        return True

    def give_relic(self, fighter, weapon, drop_at=None):
        """Arma rara na mão. Só dá para ter uma: a que ele tinha cai no chão (ATACAR pega de volta)."""
        old = fighter.give_relic(weapon)
        self.run.relics[fighter.slot] = relic_key(weapon)
        if old is not None and old is not weapon:
            self.drop_weapon(fighter, old, drop_at)
        self._got_weapon(fighter, weapon)

    def give_common(self, fighter, weapon, drop_at=None):
        """Arma de outro herói: entra no lugar da de mesmo tipo e já vem na mão."""
        base = list(fighter.base_weapons)
        i = next(k for k, w in enumerate(base) if w.is_melee == weapon.is_melee)
        old = base[i]
        base[i] = weapon
        fighter.loadout = None if tuple(base) == fighter.stats.weapons else tuple(base)
        fighter.clips.pop(old, None)
        fighter.weapon_index = i
        fighter.bow_draw = 0
        self.run.loadouts[fighter.slot] = [w.name for w in fighter.loadout] if fighter.loadout else None
        self.drop_weapon(fighter, old, drop_at)
        self._got_weapon(fighter, weapon)

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
            old = self.ground.pop(0)
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
            return
        f.steer(*inp.axis())
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
        if inp.pressed("switch") and f.switch_weapon():
            self.assets.play("click", 0.4)
        direction = None
        if inp.pressed("dodge"):
            direction = f.input if any(f.input) else f.facing
        elif inp.double_tap:
            direction = inp.double_tap
        if direction and f.dash(direction):
            self.assets.play("dash", 0.3)

    def _separate_bodies(self):
        bodies = [f for f in self.fighters if f.alive_in_match and f.lift <= 0]
        for i, a in enumerate(bodies):
            for b in bodies[i + 1:]:
                _separate(a, b)
        for f in bodies:
            self.arena.resolve(f)

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
        if len(self.players) < 2:
            return
        for p in self.players:
            if not p.alive_in_match:
                self.strain[p] = 0
                continue
            others = [q for q in self.players if q is not p]
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
    """Uma masmorra: ondas de inimigos saem de portais. Limpou a 1ª, abre a porta de volta para o
    acampamento; limpou a 2ª, aparece na tela o botão TELETRANSPORTE DE FASE: quando todos
    confirmam (ATACAR no teclado, o botão no celular ou clique), o grupo vai para a próxima fase."""

    def __init__(self, game, run):
        self.dungeon_index = run.dungeon_index
        self.dungeon = run.dungeon
        super().__init__(game, run, self.dungeon.map_key, self.dungeon.starts, self.dungeon.facing)
        self.enemy_hp, self.enemy_dmg = DIFFICULTY.get(run.session.difficulty, (1.0, 1.0))
        if run.players == 1:
            self.enemy_dmg *= SOLO_DAMAGE         # sozinho não tem quem levante: inimigos batem menos
        self.corpses = {}
        self.breath_used = False        # último fôlego (campanha solo): uma vez por masmorra
        self.state = "intro"
        self.state_timer = INTRO_FRAMES
        self.slain_boss = False
        self.exit = None                # porta de volta (só na masmorra 1)
        self.votes = set()              # quem já confirmou o teletransporte (masmorra 2)
        self.vote_button = None         # retângulo do botão na tela (para o clique)
        self.hazard = make_hazard(self.dungeon.hazard, self.arena)   # laser no chão, vento...
        hub_vote(self, 0)

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
        return None

    @property
    def voting(self):
        return self.state == "vote"

    @property
    def wants_cursor(self):
        return self.voting                  # o botão do teletransporte também aceita clique

    @property
    def objective_text(self):
        if self.state == "teleport":
            return "TELETRANSPORTANDO..."
        if self.voting:
            alive = self.alive_players
            ready = sum(1 for p in alive if p in self.votes)
            return f"TELETRANSPORTE DE FASE: TODOS CONFIRMAM ({ready}/{len(alive)})"
        if self.exit is not None:
            return "VOLTEM PELA PORTA PARA O ACAMPAMENTO"
        return ""

    def step(self):
        if self.state_timer > 0:
            self.state_timer -= 1
        super().step()

    def update_stage(self):
        if self.hazard is not None and self.state in ("fight", "between"):
            self.hazard.update(self)
        self._update_portals()
        self._update_corpses()
        self._update_downed()
        self._update_state()

    # ── ondas e inimigos ─────────────────────
    def _start_wave(self, index):
        self.wave = index
        self.wave_banner = 100
        delay = 0
        for kind, count in self.waves[index]:
            for _ in range(scaled_count(kind, count, len(self.players))):
                x, y = self._spawn_spot(kind)
                self.portals.append(Portal(x, y, kind, delay))
                delay += 14
        self.assets.play("ability", 0.4)

    def _spawn_spot(self, kind):
        if kind == "chefe" and self.dungeon.boss_spot:
            return self.dungeon.boss_spot
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
            expanded += [kind] * (scaled_count(kind, 1, players) if kind in ("diabrete", "drone") else 1)
        for i, kind in enumerate(expanded):
            a = i * math.tau / len(expanded) + random.uniform(-0.3, 0.3)
            r = random.uniform(150, 240)
            x, y = self.arena.free_spot(near.x + math.cos(a) * r, near.y + math.sin(a) * r, config.PLAYER_RADIUS + 6)
            self.portals.append(Portal(x, y, kind, i * 10))

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
        """Jogando sozinho não tem quem levante: o primeiro golpe fatal da masmorra deixa com 1 de vida."""
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
            prog = self.revive_progress[p]
            if helpers:
                prog += (1 + 0.5 * (len(helpers) - 1)) / REVIVE_FRAMES
                if self.frame % 6 == 0:
                    self.burst(p.x, p.y, p.color, 1, speed=2)
            else:
                prog = max(0.0, prog - 1 / 240)
            self.revive_progress[p] = prog
            if prog >= 1:
                self._revive(p, REVIVE_HP)
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
                self._start_wave(0)
                self.state = "fight"
            return
        if state in ("fight", "between") and not self.alive_players:
            self.state, self.state_timer = "down", DOWN_FRAMES
            self._set_banner("TODOS CAÍRAM", None, theme.BLOOD)
            return
        if state == "fight":
            if self.portals or self.alive_enemies:
                return
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
        elif state in ("exit", "vote") and self.banner and self.banner[3] > 130:
            self.banner = None
        if state == "exit":
            if self.group_near(self.exit.x, self.exit.y, ExitDoor.RADIUS + 40):
                self.state = "leaving"
                self.leave()
        elif state == "vote":
            alive = self.alive_players
            self.votes &= set(alive)
            if self.frame % 6 == 0:
                for p in self.players:
                    hub_vote_slot(p, 2 if p in self.votes else 1)
            if alive and all(p in self.votes for p in alive):
                self.state, self.state_timer = "teleport", TELEPORT_FRAMES
                hub_vote(self, 0)
                self.assets.play("teletransporte", 0.6)
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
        self.state, self.state_timer = "clear", EXIT_DELAY
        self.bullets.clear()
        for p in self.players:
            if not p.alive_in_match:
                self._revive(p, STAGE_REVIVE)
        if self.last:
            title = ("FASE CONCLUÍDA!" if not self.slain_boss else
                     "O FRAGMENTO SE PARTIU!" if self.dungeon.boss == "borba" else "O CRISTAL ESTÁ LIVRE!")
            self._set_banner(title, self.phase.name, theme.MOSS)
            self.assets.stop_music(1500)
            self.assets.play("victory", 0.5)
        else:
            self._set_banner("MASMORRA LIMPA!", self.dungeon.name, theme.MOSS)
            self.assets.play("select", 0.6)

    def _open_exit(self):
        if self.last:
            self.state = "vote"            # o botão TELETRANSPORTE DE FASE aparece na tela
            self.votes = set()
            hub_vote(self, 1)
            self.assets.play("ability", 0.5)
            return
        x, y = self.arena.free_spot(*self.dungeon.exit_spot, 40)
        self.exit = ExitDoor(x, y)
        self.state = "exit"
        self.popup(x, y - 100, "SAÍDA", theme.BRASS)
        self.props.append(self.exit)
        self.assets.play("ability", 0.5)

    def vote(self, f):
        """Um jogador confirmou o teletransporte."""
        if self.voting and f.alive_in_match and f not in self.votes:
            self.votes.add(f)
            self.burst(f.x, f.y - 20, (200, 170, 255), 12, speed=3)
            self.popup(f.x, f.y - 70, "PRONTO", theme.MOSS)
            self.assets.play("select", 0.4)
            hub_vote_slot(f, 2)
            return True
        return False

    def interact(self, f):
        if self.voting:
            self.vote(f)
            return True
        return self.pick_ground(f)

    def click(self, pos):
        """Clique no botão da tela: confirma o próximo jogador do teclado que ainda não confirmou."""
        if not self.voting or self.vote_button is None or not self.vote_button.collidepoint(pos):
            return False
        phones = self.game.connected_slots()          # celular e controle confirmam no botão deles
        for f in self.players:
            if f.alive_in_match and f not in self.votes and f.slot not in phones:
                return self.vote(f)
        return False

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
        if self.voting:
            self.vote_button = hud.draw_teleport_vote(screen, ui, self)
        else:
            self.vote_button = None
        if self.state == "teleport":
            self._draw_teleport(screen, cam)

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


def hub_vote(match, value):
    """Avisa o celular de cada jogador: 0 = sem votação, 1 = falta confirmar, 2 = já confirmou."""
    for p in match.players:
        hub_vote_slot(p, value)


def hub_vote_slot(fighter, value):
    if fighter.slot and not fighter.is_cpu:
        hub.publish_slot(fighter.slot, vote=value)


class LobbyMatch(CoopMatch):
    """Acampamento (lobby) da fase: sem batalha, com a fogueira que recupera vida, a entrada
    das duas masmorras e, na volta da primeira, o baú escondido com as armas raras."""

    lobby = True
    music = "camp"

    def __init__(self, game, run):
        cfg = MAPS_BY_KEY[run.phase.lobby]
        markers = cfg.markers
        self.back = run.stage == LOBBY_BACK
        self.style = "lag" if run.phase.chapter == 2 else None     # cofre e bancas da Lag Lobby
        starts = markers["a"] if self.back else markers["S"]
        starts = _spread(starts, len(run.session.slots))
        super().__init__(game, run, cfg.key, starts, (0.0, -1.0))
        self.state = "explore"
        self.gates = {}
        for number in (1, 2):
            rect = cells_rect(markers[str(number)])
            if number == 1:
                state = "done" if self.back else "open"
            else:
                state = "locked"
            self.gates[number] = Gate(number, rect, state)
        for gate in self.gates.values():
            gate.sync_wall(self.arena)
        fx, fy = _center(markers["F"])
        self.campfire = Campfire(fx, fy)
        self.arena.walls.append(self.campfire.wall)
        self.props += list(self.gates.values()) + [self.campfire]
        self.chest = None
        if self.back and not run.chest_open:
            cx, cy = markers["C"][0]
            self.chest = Chest(cx, cy, self.style)
            self.arena.walls.append(self.chest.wall)
            self.props.append(self.chest)
        self.target_gate = 2 if self.back else 1
        self.stalls = []
        if not self.back:                   # na chegada: o altar das maldições (desafio opcional)
            x, y = self.arena.free_spot(fx + 230, fy + 150, 40)
            altar = Stall("altar", x, y, self.style)
            self.stalls.append(altar)
            self.arena.walls.append(altar.wall)
            self.props.append(altar)
        if self.back:                       # na volta da Masmorra 1: o mercado, perto da fogueira
            for kind, dx in (("loja", -260), ("ferreiro", 260)):
                x, y = self.arena.free_spot(fx + dx, fy + 170, 40)
                stall = Stall(kind, x, y, self.style)
                self.stalls.append(stall)
                self.arena.walls.append(stall.wall)
                self.props.append(stall)
        hub_vote(self, 0)
        for p in self.players:              # chegando (teletransporte ou saindo da masmorra)
            self.burst(p.x, p.y - 20, (200, 180, 255), 14, speed=3)

    @property
    def objective_text(self):
        if self.back and self.gates[2].state != "open":
            return "A MASMORRA 2 ESTÁ ABRINDO..."
        if self.back and self.chest is not None and self.chest.state == "closed":
            hidden = "UM COFRE" if self.style == "lag" else "UM BAÚ"
            return f"TEM {hidden} ESCONDIDO POR AQUI · ENTRE NA MASMORRA 2"
        return f"ACAMPAMENTO · ENTREM NA MASMORRA {self.target_gate}"

    def objective(self):
        gate = self.gates[self.target_gate]
        return gate.entrance

    def update_stage(self):
        if self.back and self.frame == 50:
            self.gates[2].open()
            self.assets.play("barrier", 0.5)
            self.camera.shake(3)
        if self.frame == 1:
            name = self.arena.cfg.name.upper()
            if self.back:
                self._set_banner("ACAMPAMENTO", f"DE VOLTA · {name}", theme.BRASS)
            else:
                self._set_banner(f"FASE {self.run.phase_index + 1}", f"{self.phase.name} · {name}", theme.BRASS)
        if self.banner and self.banner[3] > 110:
            self.banner = None
        if self.leaving:
            return
        gate = self.gates[self.target_gate]
        if gate.state == "open" and gate.bars <= 0:
            ex, ey = gate.entrance
            inside = any(gate.rect.inflate(20, 30).collidepoint(p.x, p.y) for p in self.alive_players)
            if inside and self.group_near(ex, ey - 20, 170):
                self.leave()

    def interact(self, f):
        if self.chest is not None and self.chest.can_open(f):
            self.chest.open(self)
            self.run.chest_open = True
            return True
        stall = next((s for s in self.stalls if s.can_use(f)), None)
        if stall is not None:
            self.menus[f] = MarketMenu(self, f, stall)
            self.assets.play("loja", 0.45)
            return True
        return self.pick_ground(f)

    def launch_relics(self, chest):
        """O baú solta uma arma rara para cada jogador: armas diferentes entre si e, se der, que
        ninguém do grupo já tenha (a que cada um tinha fica no chão)."""
        held = {p.relic for p in self.players if p.relic is not None}
        # quem tem forjada também ganha uma rara do baú, e escolhe com qual fica (a outra fica no chão)
        phase = [RARE_WEAPONS[k] for k in PHASE_RELICS.get(self.run.phase.key, RARE_WEAPONS)]
        pool = [w for w in phase if w not in held]
        random.shuffle(pool)
        for p in self.players:
            choices = [w for w in pool if w is not p.relic] or \
                [w for w in phase if w is not p.relic] or \
                [w for w in RARE_WEAPONS.values() if w is not p.relic and not w.forjada]
            weapon = choices[0]
            if weapon in pool:
                pool.remove(weapon)
            self.props.append(RelicDrop(chest, p, weapon))

    def next_scene(self):
        from .scenes.campaign import next_stage
        return next_stage(self.game, self.run, DUNGEON_2 if self.back else DUNGEON_1)

    def draw_screen_layer(self, screen, ui):
        cam = self.camera
        for gate in self.gates.values():
            gate.draw_label(screen, cam, ui, self.frame)
        if self.chest is not None:
            near = any(self.chest.can_open(p) for p in self.alive_players)
            self.chest.draw_prompt(screen, cam, ui, self.frame, near)
        self.draw_ground(screen, cam, ui)
        for stall in self.stalls:
            near = any(stall.can_use(p) and p not in self.menus for p in self.alive_players)
            stall.draw_prompt(screen, cam, ui, self.frame, near)
        for f, menu in self.menus.items():
            menu.draw(screen, ui, cam.to_screen(f.x, f.y))
        gate = self.gates[self.target_gate]
        alive = self.alive_players
        inside = [p for p in alive if gate.rect.inflate(20, 30).collidepoint(p.x, p.y)]
        if inside and len(inside) < len(alive):
            # alguém já está na entrada: avisa quem falta
            waiting = " ".join(p.label for p in alive if p not in inside)
            sx, sy = cam.to_screen(*gate.entrance)
            ui.text(screen, f"ESPERANDO {waiting}", theme.XS, theme.BRASS, (round(sx), round(sy) + 24))


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

STORY = {
    "prologo": ("PRÓLOGO", "templo_gelado", (
        (CRYSTAL, None, "No alto do Templo Gelado fica o Cristal das Almas. Ele guarda a força de todos "
                        "os lutadores da arena."),
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
        ("miliciano", None, "Mas um pedaço do cristal sumiu. Homens de colete cinza, com o logo da LAG LOBBY "
                            "no braço, recolheram o fragmento e fugiram num carro preto."),
        ("aryel", "ARYEL", "Lag Lobby? É a empresa onde o Borba Jr trabalha... Precisamos ir até lá."),
    )),
    "recepcao": ("CAPÍTULO 2 · FASE 4 · RECEPÇÃO DA LAG LOBBY", "lag_saguao", (
        (FRAGMENT, None, "A Lag Lobby é a maior empresa de tecnologia da cidade. A milícia Patrulha Cinza tomou "
                         "o prédio e levou o fragmento do cristal lá para dentro."),
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
        ("sombra:borba_exo", "BORBA JR CORROMPIDO", "Eu criei o exo para ajudar as pessoas. Agora ele só obedece "
                                                    "ao fragmento."),
    )),
    "final": ("FIM", "lag_diretor", (
        (BROKEN, None, "O fragmento se parte. A luz roxa some dos cabos e as máquinas da fábrica de exos param."),
        ("borba", "BORBA JR", "Minha cabeça... Valeu, pessoal. Me ajudem a desligar o resto da fábrica."),
        ("sombra:borba_exo", None, "A sombra do Borba Jr ficou do lado dos heróis: BORBA JR CORROMPIDO está "
                                   "liberado no duelo."),
    )),
}
