"""O lutador controlado por um jogador ou pela CPU."""
import math
import random

import pygame

from . import config, theme
from .abilities import create_ability
from .data import shot_sound
from .entities import Entity, Particle, hostile
from . import forged, gadgets, rare_fx
from .market import BURN_TICK, FORGE_DAMAGE, FORGE_MAG, enchant_hit
from . import weapon_art

ACCELERATION = 0.3          # quanto da velocidade-alvo é alcançada por quadro
TURN_ACCELERATION = 0.5     # virar para o lado oposto responde mais rápido
FRICTION = 0.24             # frenagem ao soltar o direcional
MOVE_SCALE = 1.15
FEET = 22            # distância do centro de colisão até os pés do sprite
TURN_MARGIN = 1.3    # para trocar de "de lado" para "de frente" (e vice-versa) o novo eixo tem que ganhar com folga
AIM_HOLD = 18        # quadros olhando para o alvo depois de atacar (andar e atirar sem o sprite piscar)
FALL_FRAMES = 12     # duração da queda ao ser derrotado
BREATH = 36          # meio ciclo da respiração parado (quadros)
IDLE_RELOAD = 80     # tanto tempo sem atirar com o pente incompleto: recarrega sozinho
BOW_FULL = 26        # quadros segurando o ataque para o arco ficar tenso
BOW_RECOVER = 12     # pausa depois de soltar a flecha
BOW_SLOW = 0.6       # tensionando o arco anda mais devagar
HASTE_MULT = 1.25    # embalo da Estrela
THROWN = {"lanca", "shuriken", "estrela", "granada", "cristal", "orbe", "bumerangue",
          "disquete", "pendrive"}   # sem munição, a mão fica vazia
BOSS_HACK = 0.4      # o chefão fica hackeado por menos tempo
EXO_DAMAGE = 0.5     # de exoesqueleto leva metade do dano
EXO_SCALE = 1.12     # e fica um pouco maior
EXO_THROW = 22       # golpe de exoesqueleto arremessa longe
WALL_STUN = 50       # arremessado contra a parede: fica tonto
VIRUS_TICK = 15      # vírus do pendrive: um pouquinho de dano a cada tantos quadros
RUSH_MULT = 2.2      # 100 metros (Cauanzera): corre muito
MOTO_FRAMES = 18     # grau de moto (Aryel): esquiva mais longa
MOTO_COOLDOWN = 1.3  # ... e demora mais para voltar
MOTO_RIDE = 14       # o Aryel fica sentado em cima da moto


def proximity_damage(dist, base):
    """Tiros disparados de muito perto causam mais dano."""
    if dist <= config.MELEE_BONUS_RANGE:
        t = 1.0 - dist / config.MELEE_BONUS_RANGE
        return min(int(base + (config.MAX_BULLET_DAMAGE - base) * t), config.MAX_BULLET_DAMAGE)
    return base


def draw_aura(surf, img, rect, color, ticks, k=2):
    """Sombra escura espalhada atrás do corpo + contorno que pulsa (almas corrompidas)."""
    mask = pygame.mask.from_surface(img)
    smoke = mask.to_surface(setcolor=(8, 2, 14, 255), unsetcolor=(0, 0, 0, 0))
    smoke.set_alpha(110)
    for dx, dy in ((-2 * k, -k), (2 * k, -k), (0, -2 * k), (-k, k), (k, k)):
        surf.blit(smoke, rect.move(dx, dy))
    edge = mask.to_surface(setcolor=(*color, 255), unsetcolor=(0, 0, 0, 0))
    edge.set_alpha(round(150 + 70 * math.sin(ticks * 0.12)))
    for dx, dy in ((-k, 0), (k, 0), (0, -k), (0, k)):
        surf.blit(edge, rect.move(dx, dy))


_MOTO = {}


def _moto_image():
    """Moto do Aryel em pixel art (de lado, virada para a direita), já ampliada 2x."""
    if "img" not in _MOTO:
        s = pygame.Surface((32, 16), pygame.SRCALPHA)
        dark, grey, red, red_d = (30, 30, 36), (150, 154, 166), (204, 52, 48), (130, 30, 30)
        for cx in (6, 25):                                         # rodas: pneu, aro claro e cubo
            pygame.draw.circle(s, dark, (cx, 11), 4)
            pygame.draw.circle(s, (120, 124, 136), (cx, 11), 3, 1)
            pygame.draw.circle(s, (210, 214, 224), (cx, 11), 1)
        s.fill(grey, (1, 9, 6, 1))                                 # escapamento
        s.fill(red, (6, 6, 15, 4))                                 # carenagem
        s.fill(red_d, (6, 9, 15, 1))
        s.fill(red, (13, 4, 7, 3))                                 # tanque
        s.fill((240, 120, 110), (14, 4, 4, 1))
        s.fill(dark, (6, 4, 7, 2))                                 # banco
        pygame.draw.line(s, grey, (21, 4), (25, 11))               # garfo
        s.fill(dark, (19, 2, 4, 1))                                # guidão
        s.fill((255, 226, 120), (26, 5, 2, 2))                     # farol
        out = pygame.Surface((34, 18), pygame.SRCALPHA)
        line = pygame.mask.from_surface(s).to_surface(setcolor=(20, 14, 22, 255), unsetcolor=(0, 0, 0, 0))
        for dx, dy in ((0, 1), (2, 1), (1, 0), (1, 2)):
            out.blit(line, (dx, dy))
        out.blit(s, (1, 1))
        _MOTO["img"] = pygame.transform.scale(out, (68, 36))
    return _MOTO["img"]


def draw_moto(surf, cx, ground, right, wheelie):
    """Desenha a moto com as rodas no chão, empinando ``wheelie`` graus (a roda da frente sobe)."""
    img = _moto_image()
    if not right:
        img = pygame.transform.flip(img, True, False)
    if wheelie:
        img = pygame.transform.rotate(img, wheelie if right else -wheelie)
    rect = img.get_rect(midbottom=(cx, ground + 2))
    rect.x += -6 if right else 6                                   # a roda de trás fica embaixo dele
    surf.blit(img, rect)


def draw_laptop(surf, cx, cy, ticks, progress, back=False):
    """Notebook aberto na frente do Albeguinio (na altura da cintura, abaixo do rosto), com código
    correndo na tela e a barra do hack. De costas aparece só a tampa."""
    cx, cy = round(cx), round(cy)
    w, h = 24, 14
    screen = pygame.Rect(cx - w // 2, cy - h, w, h)
    if back:
        pygame.draw.rect(surf, (20, 16, 24), screen.inflate(4, 4))
        surf.fill((150, 154, 166), screen.inflate(2, 2))
        surf.fill((200, 204, 214), (cx - 2, screen.centery - 2, 4, 4))           # logo
        if (ticks // 6) % 2:
            surf.fill((120, 255, 150), (cx - 1, screen.bottom - 3, 2, 1))        # luzinha
        return
    pygame.draw.rect(surf, (20, 16, 24), screen.inflate(4, 4))
    surf.fill((52, 56, 66), screen.inflate(2, 2))
    surf.fill((10, 26, 16), screen)
    rng = random.Random(ticks // 4)
    for row in range(3):                                   # linhas de código
        lw = rng.randint(5, w - 6)
        surf.fill((90, 230, 120) if row % 2 else (170, 250, 190), (screen.x + 3, screen.y + 2 + row * 3, lw, 1))
    bar = pygame.Rect(screen.x + 3, screen.bottom - 4, w - 6, 2)
    surf.fill((30, 60, 40), bar)
    surf.fill((120, 255, 150), (bar.x, bar.y, round(bar.w * max(0.0, min(1.0, progress))), bar.h))
    base = pygame.Rect(cx - w // 2 - 4, cy + 1, w + 8, 4)          # teclado
    pygame.draw.rect(surf, (20, 16, 24), base.inflate(2, 2))
    surf.fill((150, 154, 166), base)
    surf.fill((96, 100, 112), (base.x, base.bottom - 1, base.w, 1))
    if (ticks // 3) % 2:
        surf.fill((230, 230, 236), (cx - 6 + (ticks * 5) % 12, base.y + 1, 2, 1))    # dedos digitando


class Clip:
    """Pente de uma arma de tiro."""

    __slots__ = ("ammo", "reload_timer", "reload_total", "regen_timer")

    def __init__(self, ammo):
        self.ammo = ammo
        self.reload_timer = 0
        self.reload_total = 1
        self.regen_timer = 0


_NO_CLIP = Clip(0)              # arma sem munição (corpo a corpo): sempre vazio e parado


class Fighter(Entity):
    def __init__(self, stats, slot, x, y, sprites, label, color, team=None, weapon_index=0, is_cpu=False):
        super().__init__(x, y)
        self.radius = self.base_radius = config.PLAYER_RADIUS
        self.stats = stats
        self.speed = stats.speed        # no futebol e no basquete fica mais perto da média (config.ball_mode_speed)
        self.slot = slot
        self.label = label              # "P1", "CPU"...
        self.color = color              # cor da etiqueta acima da cabeça
        self.ring_color = color         # anel no chão (no futebol, a cor do time)
        self.team = team
        self.is_cpu = is_cpu
        self.sprites = sprites
        self.max_hp = stats.max_hp      # pode crescer com melhorias (campanha)
        self.hp = self.max_hp
        self.weapon_index = weapon_index
        self.loadout = None             # duelo com escolha de armas: (de tiro, de perto) deste round
        self.ability = create_ability(stats)
        self.on_moto = False            # esquiva de moto em andamento
        self.moto_timer = 0             # grau de moto no futebol (Aryel): anda de moto e atropela

        self.vx = self.vy = 0.0
        self.input = (0.0, 0.0)
        self.facing = (1.0, 0.0) if x < 800 else (-1.0, 0.0)
        self.moving = False

        # tempos (em quadros)
        self.attack_cd = 0
        self.ability_cd = 0
        self.dash_timer = 0
        self.dash_cd = 0
        self.dash_dir = (0.0, 0.0)
        self.dodged = False             # esta esquiva já foi perfeita (só vale uma vez)
        self.perfect_flash = 0
        self.charge_timer = 0
        self.charge_dir = (0.0, 0.0)
        self.charge_damage = 0
        self.charge_stun = 0            # Investida do Guerreiro: quem leva fica tonto
        self.speed_timer = 0
        self.invulnerable_timer = 0
        self.super_cd = 0
        self.kick_cd = 0
        self.stun_timer = 0
        self.fury_timer = 0
        self.giant_timer = 0
        self.tackle_timer = 0
        self.sprint_timer = 0
        self.magic_timer = 0            # drible mágico (Faísca) e o instante da caneta (Ginga)
        self.nose_timer = 0             # faro de gol (Matador)
        self.zaga_timer = 0             # zagueirão (Guerreiro): não cai, rouba encostando, a bola morre no pé
        self.cut_timer = 0              # corte em andamento: cutuca a bola de quem encostar
        self.hack_timer = 0             # hackeado (Albeguinio): travado, sem andar, atirar nem usar nada
        self.type_timer = 0             # digitando no notebook (Albeguinio): parado
        self.virus_timer = 0            # vírus do pendrive: perde vida aos poucos
        self.virus_damage = 0
        self.virus_owner = None
        self.exo_timer = 0              # exoesqueleto (Borba Jr)
        self.exo_base = None            # sprites de antes da armadura
        self.rush_timer = 0             # 100 metros (Cauanzera): corre muito e atropela
        self.rush_damage = 0
        self.rush_hit = set()
        self.thrown_timer = 0           # arremessado pelo exoesqueleto: se bater na parede, fica tonto
        self.thrown_by = None
        self.kit = None                 # time do uniforme (futebol)
        self.ghost_walk = False         # atravessa paredes (investida sombria do chefão)
        self.root_timer = 0             # enraizado (Arco de Espinhos): não anda, mas ataca
        self.fear_timer = 0             # com medo (Crânio Uivante): foge e não ataca
        self.fear_from = (x, y)
        self.frozen_timer = 0           # congelado (Estalactites): travado no gelo
        self.slow_timer = 0             # lento (Nevasca da Geada)
        self.pull_timer = 0             # sendo puxado (Gancho do Pirata)
        self.pull_to = (x, y)
        self.block_timer = 0            # carrinho de bloqueio (futebol)
        self.block_hit = False
        self.clear_timer = 0            # chutão armado (futebol)
        self.clear_lock = False
        self.sprint_held = False        # segurando CORRER (futebol)
        self.stamina = 1.0              # fôlego da corrida, 0..1
        self.exhausted = False
        self.marking = False            # segurando MARCAR (futebol)
        # bônus (melhorias da campanha e dificuldade dos inimigos)
        self.damage_bonus = 1.0
        self.speed_mult = 1.0
        self.cd_mult = 1.0              # recarga da habilidade
        self.dash_cd_mult = 1.0         # recarga da esquiva
        self.pierce = 0                 # tiros atravessam tantos inimigos
        self.lifesteal = 0.0            # parte do dano que vira vida
        self.shield = 0                 # escudo que absorve dano
        self.draw_scale = 1.0           # tamanho do desenho (chefão)
        if self.ability.body_scale != 1.0:          # Baixinho (Aryel): menor e mais difícil de acertar
            self.draw_scale = self.ability.body_scale
            self.radius = self.base_radius = round(config.PLAYER_RADIUS * self.ability.body_scale)
        self.overlay = "full"           # o que mostrar acima da cabeça: full, hp ou none
        self.knock_resist = 0.0         # 1 = não é empurrado por golpes (golem, chefão)
        self.aura = None                # brilho em volta (almas corrompidas)
        self.windup = 0                 # preparando um golpe (inimigos brilham antes de atacar)
        self.windup_total = 1
        self.windup_color = (255, 255, 255)
        self.kind = None                # tipo do inimigo (campanha)
        self.unstoppable = False        # não é atordoado nem puxado (chefão)
        self.vulnerability = 1.0        # dano recebido é multiplicado por isso (chefão cansado)
        self.lift = 0                   # altura do desenho acima do chão (pulo do chefão)
        self.spin = 0                   # giro do desenho em graus (cambalhota da enterrada)
        self.sport_pose = None          # pose do esporte escolhida pela partida neste quadro: (pose, índice)
        self.celebrate = 0              # comemorando (braços para cima, pulinho) depois de cesta ou gol
        self.release_t = 0              # quadros desde que soltou o arremesso (mão dobrada)
        self.swat_t = 0                 # tapa do toco
        self.last_attacker = None
        self.kills = 0
        self.power = None               # poder do futebol (definido pela partida)
        self.kicked_dust = False
        self.knock = [0.0, 0.0]
        self.dribbling = False
        self.carrying_close = False
        self.carry_dir = (1.0, 0.0)
        self.kick_charge = 0            # quadros segurando CHUTE
        self.kick_kind = None           # último toque na bola: chute ou cabeça (para a animação)
        self.last_stick = (0.0, 0.0)    # analógico no quadro (domínio orientado, curva)
        self.give_go = None             # tabela: (companheiro, quadros que faltam) depois de passar
        self.diving = 0                 # goleiro: quadros da ponte (segura a bola em vez de rebater)
        self.pass_charge = 0            # quadros segurando PASSE
        self.prev_pos = (x, y)
        self.dash_len = config.DASH_FRAMES
        self.armed = True               # no futebol ninguém carrega arma
        self.age = 0
        self.aim_timer = 0              # olhando para o alvo do último ataque
        self._dir = "direita" if self.facing[0] >= 0 else "esquerda"
        # munição das armas de tiro: um pente por arma (pente, recarga e o arco tensionando)
        self.relic = None               # arma rara do baú (campanha): vira a 3ª arma
        self.forge = {}                 # ferreiro (campanha): nome da arma -> [nível, encanto]
        self.burn_timer = 0             # encanto de fogo: queima aos poucos
        self.burn_damage = 0
        self.burn_owner = None
        self.forged_count = 0           # golpes da Lâmina Solar (o 3º gira)
        self.combo_count = 0            # golpes seguidos (Teclado Mecânico e Manopla do Exo: o 3º é especial)
        self.combo_timer = 0
        self.guard_frames = 0           # segurando o Escudo de Choque
        self.storm_hold = self.storm_last = 0   # Cetro da Tempestade: há quanto tempo segura
        self.reaper = 0.0               # Foice do Ceifador: dano a mais até o fim da masmorra
        self.ammo_mult = 1.0            # melhoria da campanha: pente maior
        self.reload_mult = 1.0          # e recarga mais rápida
        self.clips = {}                 # arma → Clip
        self.idle_shot = 0              # quadros desde o último tiro
        self.bow_draw = 0               # quadros tensionando o arco
        self.bow_target = None
        self._attack_held = False
        self.dry_click = 0
        self.haste_timer = 0            # embalo (acertou com a Estrela)
        self.chain_ball = None          # bola da Corrente em voo
        self.down_age = 0               # quadros desde que caiu (animação da queda)
        self.fade = 1.0                 # transparência do corpo caído (inimigo sumindo)
        self.breath_phase = random.randrange(BREATH * 2)

        # efeitos visuais
        self.anim_frame = 0
        self.anim_timer = 0
        self.hit_flash = 0
        self.melee_flash = 0
        self.shoot_flash = 0
        self.teleport_flash = 0
        self.trail = []

        # estatísticas da partida
        self.damage_dealt = 0
        self.hits = 0
        self.goals = 0

    # ── propriedades ─────────────────────────
    @property
    def base_weapons(self):
        """As armas do personagem, ou as que o jogador escolheu antes do round (duelo)."""
        return self.loadout or self.stats.weapons

    @property
    def weapons(self):
        if self.relic is not None:
            return self.base_weapons + (self.relic,)
        return self.base_weapons

    @property
    def weapon(self):
        weapons = self.weapons
        return weapons[self.weapon_index % len(weapons)]

    def give_relic(self, weapon):
        """Arma rara do baú: entra como 3ª arma (troca a anterior, se tinha) e já vem na mão."""
        old = self.relic
        if old is not None:
            self.clips.pop(old, None)
        self.relic = weapon
        self.weapon_index = len(self.weapons) - 1
        self.bow_draw = 0
        return old

    def mag_of(self, weapon):
        """Tiros num pente cheio desta arma (0 = sem limite)."""
        if weapon is None or weapon.is_melee or weapon.mag <= 0:
            return 0
        level = self.forge.get(weapon.name, (0,))[0]
        return max(1, round(weapon.mag * getattr(self, "ammo_mult", 1.0) * (1 + FORGE_MAG * level)))

    def weapon_mult(self, weapon):
        """Dano a mais do ferreiro nesta arma (+15% por nível)."""
        return 1 + FORGE_DAMAGE * self.forge.get(weapon.name, (0,))[0] + self.reaper

    def burn(self, owner, damage, frames):
        """Encanto de fogo: perde ``damage`` de vida a cada BURN_TICK quadros, por ``frames``."""
        if self.invulnerable or self.hp <= 0:
            return False
        self.burn_timer = max(self.burn_timer, frames)
        self.burn_damage = max(self.burn_damage if self.burn_timer else 0, damage)
        self.burn_owner = owner
        return True

    def clip(self, weapon):
        clip = self.clips.get(weapon)
        if clip is None:
            clip = self.clips[weapon] = Clip(self.mag_of(weapon))
        return clip

    @property
    def gun(self):
        """A arma de tiro em foco: a da mão, se for de tiro; senão a de tiro do personagem."""
        w = self.weapon
        if not w.is_melee:
            return w
        for w in self.base_weapons:
            if not w.is_melee:
                return w
        return None

    @property
    def mag(self):
        """Tiros num pente cheio da arma em foco (0 = arma sem limite de tiros)."""
        return self.mag_of(self.gun)

    def _focus(self):
        gun = self.gun
        return self.clip(gun) if self.mag_of(gun) else _NO_CLIP

    @property
    def ammo(self):
        return self._focus().ammo

    @ammo.setter
    def ammo(self, value):
        clip = self._focus()
        if clip is not _NO_CLIP:
            clip.ammo = value

    @property
    def reload_timer(self):
        return self._focus().reload_timer

    @reload_timer.setter
    def reload_timer(self, value):
        clip = self._focus()
        if clip is not _NO_CLIP:
            clip.reload_timer = value

    @property
    def reload_total(self):
        return self._focus().reload_total

    @property
    def reloading(self):
        return self.reload_timer > 0

    @property
    def reload_ratio(self):
        clip = self._focus()
        return 1 - clip.reload_timer / clip.reload_total if clip.reload_timer > 0 else 1.0

    def _start_reload(self, weapon):
        clip = self.clip(weapon)
        mag = self.mag_of(weapon)
        if not mag or clip.reload_timer > 0 or clip.ammo >= mag or weapon.regen:
            return False
        clip.reload_total = clip.reload_timer = max(1, round(weapon.reload * self.reload_mult))
        if weapon is self.weapon:
            self.bow_draw = 0
        return True

    def start_reload(self):
        """Começa a recarregar o pente da arma em foco (armas mágicas não recarregam: a carga volta)."""
        gun = self.gun
        return self._start_reload(gun) if self.mag_of(gun) else False

    def refill_ammo(self, extra=1.0):
        """Enche o pente de todas as armas de tiro na hora (item de munição: ``extra`` > 1 sobra munição)."""
        done = False
        for w in self.weapons:
            mag = self.mag_of(w)
            if mag:
                clip = self.clip(w)
                clip.reload_timer = 0
                clip.ammo = max(clip.ammo, round(mag * extra))
                done = True
        return done

    @property
    def alive_in_match(self):
        return self.hp > 0

    @property
    def invulnerable(self):
        return self.invulnerable_timer > 0 or self.dash_timer > 0

    @property
    def ability_ready(self):
        return self.ability_cd <= 0

    @property
    def ability_cooldown(self):
        return max(1, round(config.ABILITY_COOLDOWN * self.cd_mult * self.ability.cooldown_mult))

    @property
    def ability_ratio(self):
        return 1 - self.ability_cd / self.ability_cooldown

    @property
    def sprinting(self):
        """Correndo de verdade: segurando CORRER, com fôlego e andando."""
        return self.sprint_held and not self.exhausted and self.stamina > 0 and self.moving

    @property
    def max_speed(self):
        base = self.speed * MOVE_SCALE
        if self.sprint_timer > 0:
            return base * 1.8
        if self.moto_timer > 0:
            return base * config.MOTO_SPEED
        if self.sprinting:
            base *= config.SPRINT_MULT
        elif self.carrying_close and not (self.power is not None and self.power.glued_carry):
            base *= 0.9            # conduzir colado custa um pouco de velocidade (menos para o Ginga)
        if self.magic_timer > 0:
            base *= 1.15           # drible mágico
        if self.nose_timer > 0:
            base *= 1.2            # faro de gol
        if self.zaga_timer > 0:
            base *= 1.1            # zagueirão
        if self.slow_timer > 0:
            base *= config.SLOW_MULT
        if self.bow_draw > 0:
            base *= BOW_SLOW
        if self.haste_timer > 0:
            base *= HASTE_MULT
        if self.rush_timer > 0:
            base *= RUSH_MULT
        return base * (2 if self.speed_timer > 0 else 1) * self.speed_mult

    def slow(self, frames):
        """Fica lento (gelo). Invulnerável e zagueirão não são afetados."""
        if self.invulnerable or self.zaga_timer > 0:
            return False
        self.slow_timer = max(self.slow_timer, frames)
        return True

    def pull(self, x, y, frames=10):
        """É puxado até (x, y) em alguns quadros (gancho)."""
        if self.invulnerable or self.unstoppable or self.exo_timer > 0:
            return False
        self.pull_to = (x, y)
        self.pull_timer = frames
        self.dash_timer = self.charge_timer = 0
        return True

    def update_stamina(self):
        """Gasta fôlego correndo e recupera andando (chamado pela partida de futebol)."""
        if self.sprinting:
            self.stamina = max(0.0, self.stamina - 1 / (config.SPRINT_SECONDS * config.FPS))
            if self.stamina == 0:
                self.exhausted = True
        else:
            self.stamina = min(1.0, self.stamina + 1 / (config.SPRINT_RECOVER_SECONDS * config.FPS))
            if self.exhausted and self.stamina >= config.SPRINT_RESUME:
                self.exhausted = False

    @property
    def stunned(self):
        return self.stun_timer > 0

    @property
    def damage_mult(self):
        return (config.FURY_MULT if self.fury_timer > 0 else 1.0) * self.damage_bonus

    def stun(self, frames=config.STUN_FRAMES):
        if (self.invulnerable or self.unstoppable or self.magic_timer > 0 or self.exo_timer > 0 or self.lift > 0
                or self.zaga_timer > 0):
            return False
        self.stun_timer = max(self.stun_timer, frames)
        self.charge_timer = 0
        self.kick_charge = self.pass_charge = 0
        return True

    @property
    def hacked(self):
        return self.hack_timer > 0

    def root(self, frames):
        """Enraizado: preso no lugar (ainda ataca). Chefão e invulnerável escapam."""
        if self.invulnerable or self.unstoppable or self.hp <= 0:
            return False
        self.root_timer = max(self.root_timer, frames)
        return True

    def scare(self, frames, x, y):
        """Medo: foge de (x, y) e não ataca."""
        if self.invulnerable or self.unstoppable or self.hp <= 0 or self.exo_timer > 0:
            return False
        self.fear_timer = max(self.fear_timer, frames)
        self.fear_from = (x, y)
        return True

    def freeze(self, frames):
        """Congelado num bloco de gelo (fica tonto, com o gelo desenhado em volta)."""
        if not self.stun(frames):
            return False
        self.frozen_timer = max(self.frozen_timer, frames)
        return True

    def hack(self, frames):
        """Hackeado (Albeguinio): trava tudo por ``frames``. Pega até quem não fica tonto (exoesqueleto,
        chefão — este por menos tempo); só escapa quem está invulnerável, no ar ou de zagueirão."""
        if self.hp <= 0 or self.invulnerable_timer > 0 or self.lift > 0 or self.magic_timer > 0 or self.zaga_timer > 0:
            return False
        if self.unstoppable:
            frames = round(frames * BOSS_HACK)
        self.hack_timer = max(self.hack_timer, frames)
        self.stun_timer = max(self.stun_timer, frames)
        self.charge_timer = self.dash_timer = self.rush_timer = self.type_timer = 0
        self.kick_charge = self.pass_charge = self.bow_draw = 0
        return True

    def infect(self, owner, damage, frames):
        """Vírus do pendrive: perde ``damage`` de vida a cada VIRUS_TICK quadros, por ``frames``."""
        if self.invulnerable or self.hp <= 0:
            return False
        self.virus_timer = max(self.virus_timer, frames)
        self.virus_damage = damage
        self.virus_owner = owner
        return True

    def start_exo(self, frames, sprites=None):
        """Monta o exoesqueleto (Borba Jr)."""
        if self.exo_base is None:
            self.exo_base = self.sprites
        if sprites is not None:
            self.sprites = sprites
        self.exo_timer = frames
        self.radius = round(self.base_radius * 1.15)
        self.knock = [0.0, 0.0]

    def end_exo(self):
        self.exo_timer = 0
        if self.exo_base is not None:
            self.sprites = self.exo_base
            self.exo_base = None
        if self.giant_timer == 0:
            self.radius = self.base_radius

    def melee_reach(self, weapon=None):
        """Alcance do golpe (o Cauanzera, alto, alcança mais)."""
        weapon = weapon or self.weapon
        return weapon.reach * self.ability.reach_mult

    @property
    def busy(self):
        """Não pode atacar nem usar nada (tonto, hackeado ou digitando)."""
        return self.stunned or self.type_timer > 0 or self.fear_timer > 0

    def reset_round(self, x, y, facing):
        """Volta ao estado inicial para um novo round (mantém as estatísticas da partida)."""
        self.x, self.y = x, y
        self.facing = facing
        self.hp = self.max_hp
        self.vx = self.vy = 0.0
        self.input = (0.0, 0.0)
        self.knock = [0.0, 0.0]
        for name in ("attack_cd", "ability_cd", "dash_timer", "dash_cd", "charge_timer", "speed_timer",
                     "invulnerable_timer", "stun_timer", "fury_timer", "hit_flash", "melee_flash",
                     "shoot_flash", "teleport_flash", "slow_timer", "pull_timer", "windup", "aim_timer",
                     "down_age", "bow_draw", "haste_timer", "idle_shot", "hack_timer", "type_timer",
                     "virus_timer", "rush_timer", "thrown_timer", "root_timer", "fear_timer", "frozen_timer",
                     "perfect_flash", "burn_timer", "combo_timer", "combo_count", "guard_frames"):
            setattr(self, name, 0)
        self.end_exo()
        self.clips.clear()                            # pentes cheios de novo
        self.chain_ball = None
        self.ability.reset()
        self.trail.clear()

    # ── comandos ─────────────────────────────
    def steer(self, dx, dy):
        mag = math.hypot(dx, dy)
        if mag > 1:
            dx, dy = dx / mag, dy / mag
        self.input = (dx, dy)
        if mag > 0.1 and self.aim_timer <= 0:
            self.facing = (dx / mag, dy / mag)

    def face(self, target):
        d = self.direction_to(target)
        if d != (0.0, 0.0):
            self.facing = d

    def dash(self, direction=None, frames=None, cooldown=config.DASH_COOLDOWN):
        if self.dash_cd > 0 or self.charge_timer > 0 or self.busy:
            return False
        self.on_moto = frames is None and self.ability.moto          # só a esquiva normal vira moto
        if frames is None:
            frames = MOTO_FRAMES if self.on_moto else config.DASH_FRAMES
        dx, dy = direction or self.input
        if not (dx or dy):
            dx, dy = self.facing
        mag = math.hypot(dx, dy) or 1
        self.dash_dir = (dx / mag, dy / mag)
        self.dash_timer = frames
        self.dash_len = frames
        moto = MOTO_COOLDOWN if self.on_moto else 1.0         # a moto vai mais longe: recarga maior
        self.dash_cd = round(cooldown * self.dash_cd_mult * moto)
        self.dodged = False
        self.kicked_dust = True
        return True

    def perfect_dodge(self, match):
        """Esquivou no meio de um golpe de verdade: a esquiva volta na hora e a habilidade carrega
        um pouco. Vale uma vez por esquiva (no duelo e na campanha)."""
        if self.dash_timer <= 0 or self.dodged or self.hp <= 0 or match.session.soccer:
            return False
        if self.dash_len - self.dash_timer >= config.PERFECT_DODGE_WINDOW:
            return False                # só no comecinho da esquiva (a moto do Aryel não ganha mais)
        self.dodged = True
        self.dash_cd = 0
        self.ability_cd = max(0, self.ability_cd - round(self.ability_cooldown * config.PERFECT_DODGE_CHARGE))
        self.perfect_flash = 18
        match.popup(self.x, self.y - 60, "ESQUIVA PERFEITA!", (240, 248, 255))
        match.burst(self.x, self.y - 14, (230, 244, 255), 12, speed=4)
        match.assets.play("click", 0.5)
        return True

    def start_charge(self, direction, damage, stun=0):
        self.charge_dir = direction
        self.charge_timer = 20
        self.charge_damage = damage
        self.charge_stun = stun
        self.facing = direction

    def start_windup(self, frames, color):
        """Começa a preparar um golpe: o sprite brilha até ``windup`` chegar a zero."""
        self.windup = self.windup_total = max(1, frames)
        self.windup_color = color

    def switch_weapon(self):
        if len(self.weapons) < 2:
            return False
        self.weapon_index = (self.weapon_index + 1) % len(self.weapons)
        self.attack_cd = max(self.attack_cd, 10)
        self.bow_draw = 0
        return True

    def attack(self, match, target):
        self._attack_held = True
        if self.attack_cd > 0 or target is None or self.busy:
            return False
        weapon = self.weapon
        if not weapon.is_melee and self.mag:
            if self.ammo <= 0:
                # pente vazio: clique seco e recarrega (dá para trocar para a arma de perto enquanto isso)
                self.start_reload()
                if self.dry_click <= 0:
                    self.dry_click = 30
                    match.assets.play("click", 0.2)
                return False
            self.reload_timer = 0                     # atirar com bala no pente cancela a recarga
        self.face(target)
        if weapon.special == "escudo":
            return gadgets.shield_hold(self, match)
        if weapon.charge:
            # arco: segurar tensiona; solta ao largar o botão ou quando fica tenso
            self.bow_target = target
            self.aim_timer = max(AIM_HOLD, BOW_FULL)
            self.bow_draw += 1
            if self.bow_draw >= BOW_FULL:
                self._release_bow(match)
            return True
        self.aim_timer = max(AIM_HOLD, weapon.cooldown + 8)    # continua virado para o alvo entre um tiro e outro
        dist = self.distance_to(target)
        if weapon.is_melee:
            self.melee_flash = 12
            self.attack_cd = weapon.cooldown
            match.assets.play("golpe", 0.45)
            self._deflect_bullets(match)
            rare_fx.on_attack(self, weapon, match, rare_fx.weapon_tip(self, weapon))
            # acerta todos os adversários ao alcance na frente (no duelo, só existe um)
            fx, fy = self.facing
            reach = self.melee_reach(weapon)
            hits = []
            damage = round(weapon.damage * self.damage_mult * self.weapon_mult(weapon))
            for other in match.opponents_of(self):
                if not other.alive_in_match:
                    continue
                dx, dy = other.x - self.x, other.y - self.y
                d = math.hypot(dx, dy)
                in_front = weapon.spin or other is target or d < other.radius + 6 or (dx * fx + dy * fy) > -0.2 * d
                if d <= reach + other.radius and in_front:
                    if other.take_damage(damage, self.x, self.y, attacker=self, match=match):
                        hits.append(other)
                        enchant_hit(self, weapon, other, match, damage)
                        if self.exo_timer > 0:
                            other.throw_from(self, match)
            if weapon.forjada:
                forged.on_swing(self, weapon, match, hits, damage)
            gadgets.on_melee(self, weapon, match, damage)
            return True
        base = proximity_damage(dist, weapon.damage) if weapon.close_bonus else weapon.damage
        damage = round(base * self.damage_mult * self.weapon_mult(weapon))
        # armas antigas sem estilo (chefão): a granada do Aryel continua explodindo
        explosive = not weapon.style and self.stats.key in ("aryel", "aryel_corrompido")
        match.spawn_projectile(self, weapon, self.facing, damage, target, explosive=explosive)
        self._spend_ammo()
        self.attack_cd = weapon.cooldown
        self.shoot_flash = 5
        rare_fx.on_attack(self, weapon, match, rare_fx.weapon_tip(self, weapon))
        match.assets.play(shot_sound(weapon, match.frame), 0.3)
        return True

    def _spend_ammo(self):
        self.idle_shot = 0
        weapon = self.weapon
        if self.mag_of(weapon):
            clip = self.clip(weapon)
            clip.ammo -= 1
            if clip.ammo <= 0:
                self._start_reload(weapon)

    def _release_bow(self, match):
        """Solta a flecha: quanto mais tensionado, mais forte, mais rápida (e tensa atravessa)."""
        power = min(1.0, self.bow_draw / BOW_FULL)
        self.bow_draw = 0
        target = self.bow_target
        if target is not None and getattr(target, "alive_in_match", True):
            self.face(target)
        weapon = self.weapon
        damage = round(weapon.damage * (0.7 + 1.2 * power) * self.damage_mult * self.weapon_mult(weapon))
        match.spawn_projectile(self, weapon, self.facing, damage, target, power=power)
        self._spend_ammo()
        self.attack_cd = BOW_RECOVER
        self.shoot_flash = 5
        rare_fx.on_attack(self, weapon, match, rare_fx.weapon_tip(self, weapon))
        self.aim_timer = max(self.aim_timer, AIM_HOLD)
        sound = "arco" if weapon.style in ("flecha", "") else shot_sound(weapon)
        match.assets.play(sound, 0.45 if power >= 1 else 0.3)

    def throw_from(self, attacker, match):
        """Golpe do exoesqueleto: voa longe (e se bater na parede fica tonto)."""
        force = EXO_THROW * (1 - self.knock_resist)
        if force < 2 or self.exo_timer > 0:
            return
        ux, uy = attacker.direction_to(self)
        if not (ux or uy):
            ux, uy = attacker.facing
        self.knock = [ux * force, uy * force]
        self.thrown_timer = 18
        self.thrown_by = attacker
        match.popup(self.x, self.y - 62, "ARREMESSADO", (120, 190, 255))
        match.camera.shake(5)

    def _deflect_bullets(self, match):
        """O golpe corpo a corpo rebate os tiros que chegam pela frente."""
        self.deflect_front(match, self.weapon.reach + 14)       # (a passiva de alto não aumenta a defesa)

    def deflect_front(self, match, reach):
        fx, fy = self.facing
        blocked = 0
        for b in match.bullets:
            if not hostile(b.owner, self) or not b.alive:
                continue
            dx, dy = b.x - self.x, b.y - self.y
            dist = math.hypot(dx, dy)
            if dist < reach and (dx * fx + dy * fy) > 0.2 * dist:
                b.alive = False
                b.explosive = False
                blocked += 1
                match.burst(b.x, b.y, (250, 240, 200), 6, speed=3)
        if blocked:
            match.popup(self.x, self.y - 46, "DEFESA", theme.SKY)
            match.assets.play("barrier", 0.35)

    def use_ability(self, match, target):
        if not self.ability_ready or self.busy:
            return False
        self.ability_cd = self.ability_cooldown
        self.ability.use(self, match, target)
        return True

    def take_damage(self, amount, sx=None, sy=None, attacker=None, match=None):
        if self.invulnerable or self.hp <= 0:
            if (amount > 0 and match is not None and attacker is not None and attacker is not self
                    and self.invulnerable_timer <= 0):
                self.perfect_dodge(match)
            return False
        if self.vulnerability != 1.0:
            amount = max(1, round(amount * self.vulnerability))
        if self.exo_timer > 0:
            amount = max(1, round(amount * EXO_DAMAGE))         # a armadura segura metade
        if self.shield > 0:
            absorbed = min(self.shield, amount)
            self.shield -= absorbed
            amount -= absorbed
            if match is not None and absorbed:
                match.burst(self.x, self.y - 14, (150, 212, 240), 6, speed=3)
            if amount <= 0:
                self.hit_flash = 3
                return True
        dealt = min(amount, self.hp)
        self.hp -= dealt
        if self.hp <= 0 and match is not None and match.last_breath(self):
            self.hp = 1                                          # segurou o golpe que derrubaria
        if attacker is not None and attacker.lifesteal > 0 and attacker.hp > 0:
            attacker.hp = min(attacker.max_hp, attacker.hp + max(1, round(dealt * attacker.lifesteal)))
        self.hit_flash = 6
        if sx is not None:
            dx, dy = self.x - sx, self.y - sy
            mag = math.hypot(dx, dy)
            if mag:
                force = min(11.0, 3 + amount * 0.22) * (1 - self.knock_resist)    # golpe forte empurra mais
                if self.exo_timer > 0 or self.rush_timer > 0:
                    force = 0.0                                  # armadura / correndo os 100 metros
                self.knock = [dx / mag * force, dy / mag * force]
        if attacker is not None:
            attacker.damage_dealt += dealt
            attacker.hits += 1
            self.last_attacker = attacker
            if self.hp <= 0:
                attacker.kills += 1
                forged.on_kill(attacker, self, match)
        if match is not None:
            match.popup(self.x, self.y - 46 * self.draw_scale, str(amount), theme.BONE if amount < 20 else theme.BRASS)
            match.burst(self.x, self.y - 10, (236, 230, 220), 5, speed=3)
            match.hit_feedback(self, amount)
            match.assets.play("hit", 0.4)
        return True

    # ── simulação ────────────────────────────
    def _move(self, match, dx, dy):
        """Anda em passos de no máximo 8 px para não atravessar paredes finas em alta velocidade.
        Devolve True se bateu em alguma parede."""
        if self.ghost_walk:                          # atravessando paredes (investida do chefão)
            self.x += dx
            self.y += dy
            return False
        steps = max(1, math.ceil(max(abs(dx), abs(dy)) / 8))
        hit = False
        for _ in range(steps):
            self.x += dx / steps
            self.y += dy / steps
            if match.arena.resolve(self):
                hit = True
        return hit

    def update(self, match):
        self.age += 1
        self.ability.tick(self)
        rare_fx.emit_held(self, match)
        for name in ("attack_cd", "ability_cd", "dash_cd", "speed_timer", "invulnerable_timer",
                     "super_cd", "kick_cd", "stun_timer", "fury_timer", "giant_timer", "sprint_timer",
                     "magic_timer", "nose_timer", "zaga_timer", "moto_timer", "cut_timer", "hack_timer",
                     "type_timer", "rush_timer", "thrown_timer", "root_timer", "fear_timer", "frozen_timer",
                     "slow_timer", "windup", "aim_timer", "haste_timer", "dry_click",
                     "hit_flash", "melee_flash", "shoot_flash", "teleport_flash", "perfect_flash",
                     "celebrate", "release_t", "swat_t"):
            value = getattr(self, name)
            if value > 0:
                setattr(self, name, value - 1)
        if self.exo_timer > 0:
            self.exo_timer -= 1
            if self.exo_timer == 0:
                self.end_exo()
        if self.giant_timer == 0 and self.exo_timer == 0 and self.radius != self.base_radius:
            self.radius = self.base_radius
        if self.virus_timer > 0:
            self._virus(match)
        if self.burn_timer > 0:
            self._burn(match)
        if self.kicked_dust:
            self.kicked_dust = False
            match.dust(self.x, self.y + FEET, 6)

        if self.hp <= 0:
            self.down_age += 1
            if self.down_age == FALL_FRAMES:
                match.dust(self.x, self.y + FEET, 8)        # bateu no chão
            self.vx *= 0.85
            self.vy *= 0.85
            self.x += self.vx
            self.y += self.vy
            match.arena.resolve(self)
            return

        self.down_age = 0
        self.fade = 1.0
        self._update_ammo(match)
        moving_fast = False
        if self.dash_timer > 0:
            # arranca forte e desacelera (mesma distância total de antes)
            t = 1 - self.dash_timer / self.dash_len
            self.dash_timer -= 1
            if self.on_moto:                                           # fumaça do escapamento
                dx, dy = self.dash_dir
                back = -1 if (dx if abs(dx) > 0.2 else self.facing[0]) >= 0 else 1
                for _ in range(2):
                    match.particles.append(Particle(self.x + back * 30, self.y + 16 + random.uniform(-3, 3),
                                                    back * random.uniform(0.4, 1.2) - dx * 0.5, random.uniform(-0.9, -0.3),
                                                    random.choice(((150, 146, 150), (190, 186, 186), (120, 116, 122))),
                                                    random.randint(24, 40), 9, -0.01))
            step = self.stats.speed * config.DASH_SPEED_MULT * (1.5 - t)
            self._move(match, self.dash_dir[0] * step, self.dash_dir[1] * step)
            # ao terminar, sai andando na mesma direção em vez de parar seco
            self.vx, self.vy = self.dash_dir[0] * self.max_speed, self.dash_dir[1] * self.max_speed
            moving_fast = True
        elif self.pull_timer > 0:
            # puxado pelo gancho: chega ao ponto em poucos quadros (para em paredes)
            tx, ty = self.pull_to
            k = 1 / self.pull_timer
            self.pull_timer -= 1
            self.vx = self.vy = 0.0
            self.knock = [0.0, 0.0]
            self._move(match, (tx - self.x) * k, (ty - self.y) * k)
            moving_fast = True
        elif self.charge_timer > 0:
            self.charge_timer -= 1
            step = self.stats.speed * 4
            if self._move(match, self.charge_dir[0] * step, self.charge_dir[1] * step):
                self.charge_timer = 0
                match.camera.shake(4)
            for other in match.opponents_of(self):
                if other.alive_in_match and self.distance_to(other) < self.radius + other.radius + 6:
                    other.take_damage(self.charge_damage, self.x, self.y, attacker=self, match=match)
                    if self.charge_stun:
                        other.stun(self.charge_stun)
                    self.charge_timer = 0
            moving_fast = True
        else:
            ix, iy = (0.0, 0.0) if self.stunned or self.type_timer > 0 or self.root_timer > 0 else self.input
            if self.fear_timer > 0 and not self.stunned:
                fx, fy = self.x - self.fear_from[0], self.y - self.fear_from[1]
                fd = math.hypot(fx, fy) or 1.0
                ix, iy = fx / fd, fy / fd                # com medo: foge
            if self.rush_timer > 0 and math.hypot(ix, iy) < 0.3 and not self.stunned:
                ix, iy = self.facing                     # 100 metros: não para de correr
            was_fast = math.hypot(self.vx, self.vy) > self.speed * 0.8
            self.moving = abs(ix) > 0.05 or abs(iy) > 0.05
            if self.moving:
                turning = ix * self.vx + iy * self.vy < 0
                k = TURN_ACCELERATION if turning else ACCELERATION
                self.vx += (ix * self.max_speed - self.vx) * k
                self.vy += (iy * self.max_speed - self.vy) * k
                if turning and match.frame % 4 == 0 and math.hypot(self.vx, self.vy) > 1.5:
                    match.dust(self.x, self.y + FEET, 1)
            else:
                self.vx *= 1 - FRICTION
                self.vy *= 1 - FRICTION
                if abs(self.vx) < 0.1:
                    self.vx = 0.0
                if abs(self.vy) < 0.1:
                    self.vy = 0.0
            if was_fast and not self.moving and match.frame % 3 == 0:
                match.dust(self.x, self.y + FEET, 1)       # derrapada
            hit_wall = self._move(match, self.vx + self.knock[0], self.vy + self.knock[1])
            if self.thrown_timer > 0:
                if hit_wall and math.hypot(*self.knock) > 4:
                    self._hit_wall(match)
                self.knock[0] *= 0.9                     # arremessado voa mais longe
                self.knock[1] *= 0.9
            else:
                self.knock[0] *= 0.8
                self.knock[1] *= 0.8
            moving_fast = (self.speed_timer > 0 or self.sprint_timer > 0 or self.rush_timer > 0) and self.moving
            if self.rush_timer > 0:
                self._rush_over(match)

        # rastro (turbo / esquiva / investida)
        if moving_fast and match.frame % 2 == 0 and not (self.on_moto and self.dash_timer > 0):
            self.trail.append((self.x, self.y, self._direction(), *self._pose()))
        if len(self.trail) > 4 or (self.trail and not moving_fast and match.frame % 2 == 0):
            self.trail.pop(0)

        # animação de caminhada (passos mais rápidos correndo)
        if self.moving or moving_fast:
            steps = self.sprites.walk_len
            period = max(4.0, 11 - math.hypot(self.vx, self.vy) * 1.3) * 4 / steps
            self.anim_timer += 1
            if self.anim_timer >= period:
                self.anim_timer -= period
                self.anim_frame = (self.anim_frame + 1) % steps
        else:
            self.anim_frame = 0
            self.anim_timer = 0

    def _hit_wall(self, match):
        """Arremessado pelo exoesqueleto bateu na parede: tonto e machucado."""
        self.thrown_timer = 0
        self.knock = [0.0, 0.0]
        self.take_damage(6, attacker=self.thrown_by, match=match)
        self.stun(WALL_STUN)
        match.popup(self.x, self.y - 74, "NA PAREDE!", theme.BRASS)
        match.burst(self.x, self.y - 10, (220, 220, 230), 12, speed=4)
        match.camera.shake(6)

    def _rush_over(self, match):
        """100 metros: quem estiver no caminho é atropelado (uma vez por corrida)."""
        for other in match.opponents_of(self):
            if other in self.rush_hit or not other.alive_in_match:
                continue
            if self.distance_to(other) < self.radius + other.radius + 6:
                self.rush_hit.add(other)
                if other.take_damage(self.rush_damage, self.x, self.y, attacker=self, match=match):
                    ux, uy = self.direction_to(other)
                    if other.stun(30):
                        other.knock = [ux * 9 * (1 - other.knock_resist), uy * 9 * (1 - other.knock_resist)]
                    match.popup(other.x, other.y - 74, "ATROPELOU", theme.BONE)

    def _burn(self, match):
        self.burn_timer -= 1
        if self.hp <= 0:
            self.burn_timer = 0
            return
        if match.frame % 3 == 0:
            match.particles.append(Particle(self.x + random.uniform(-10, 10), self.y - random.uniform(0, 30),
                                            0, -1.0, random.choice(((250, 140, 60), (255, 210, 110))), 14, 3))
        if self.burn_timer % BURN_TICK == 0 and self.take_damage(self.burn_damage, attacker=self.burn_owner):
            match.popup(self.x + 14, self.y - 46, str(self.burn_damage), (250, 140, 60))

    def _virus(self, match):
        """Vírus do pendrive: dano pequeno de tempos em tempos (sem empurrão nem pausa)."""
        self.virus_timer -= 1
        if self.hp <= 0:
            self.virus_timer = 0
            return
        if self.virus_timer % VIRUS_TICK == 0 and self.take_damage(self.virus_damage, attacker=self.virus_owner):
            match.popup(self.x + 14, self.y - 46, str(self.virus_damage), (110, 230, 120))
            match.burst(self.x, self.y - 20, (110, 230, 120), 3, speed=2, size=3)

    def _update_ammo(self, match):
        """Arco (soltar ao largar o botão), recarga do pente e carga que volta nas armas mágicas."""
        held, self._attack_held = self._attack_held, False
        if self.combo_timer > 0:
            self.combo_timer -= 1
        if self.guard_frames > 0 and (not held or self.stunned or self.weapon.special != "escudo"):
            if self.weapon.special == "escudo" and not self.stunned:
                gadgets.shield_release(self, match)
            self.guard_frames = 0
        if self.bow_draw > 0:
            if self.stunned or not self.weapon.charge or not getattr(match, "active", True):
                self.bow_draw = 0
            elif not held:
                self._release_bow(match)
        self.idle_shot += 1
        for weapon in self.weapons:
            mag = self.mag_of(weapon)
            if not mag:
                continue
            clip = self.clip(weapon)
            if weapon.regen:
                if clip.ammo < mag:
                    clip.regen_timer += 1
                    if clip.regen_timer >= max(1, round(weapon.regen * self.reload_mult)):
                        clip.regen_timer = 0
                        clip.ammo += 1
                else:
                    clip.regen_timer = 0
            elif clip.reload_timer > 0:
                clip.reload_timer -= 1
                if clip.reload_timer == 0:
                    clip.ammo = max(clip.ammo, mag)
                    if weapon is self.weapon:
                        match.assets.play("click", 0.3)
            elif clip.ammo < mag and (clip.ammo <= 0 or self.idle_shot > IDLE_RELOAD):
                if not (weapon is self.weapon and self.bow_draw > 0):
                    self._start_reload(weapon)

    # ── desenho ──────────────────────────────
    def _direction(self):
        """Direção do sprite. Perto da diagonal ele mantém a que já estava (o eixo novo precisa
        ganhar com folga), senão o polegar tremendo no analógico faz o desenho piscar."""
        dx, dy = self.facing
        ax, ay = abs(dx), abs(dy)
        side = self._dir in ("direita", "esquerda")
        if side and ay > ax * TURN_MARGIN:
            side = False
        elif not side and ax > ay * TURN_MARGIN:
            side = True
        if side:
            if dx:
                self._dir = "direita" if dx > 0 else "esquerda"
            elif self._dir not in ("direita", "esquerda"):
                self._dir = "direita"
        else:
            if dy:
                self._dir = "costas" if dy < 0 else "frente"
            elif self._dir not in ("costas", "frente"):
                self._dir = "frente"
        return self._dir

    def _pose(self):
        """Pose do sprite neste quadro: (andar | parado | ataque | dano | esquiva, índice), ou uma
        das poses do esporte (pulo, arremesso, enterrada, toco, chute, carrinho, comemora)."""
        if self.sport_pose is not None and not self.stunned:
            return self.sport_pose
        if self.celebrate > 0 and not self.moving and not self.stunned:
            return "comemora", (self.celebrate // 8) % 2
        if (self.dash_timer > 0 or self.charge_timer > 0 or self.pull_timer > 0 or self.lift > 0
                or self.tackle_timer > 0 or self.block_timer > 0):
            return "esquiva", 0
        if self.stunned or self.hit_flash > 0:
            return "dano", 0
        if self.melee_flash > 0:
            t = 1 - self.melee_flash / 12
            return "ataque", 0 if t < 0.2 else 1 if t < 0.6 else 2
        if self.windup > 0:
            return "ataque", 0                       # inimigo preparando o golpe
        if self.kick_cd > 6:
            return "ataque", 1 if self.kick_cd > 10 else 2     # chute / cabeçada no futebol
        if self.shoot_flash > 0 and not self.moving:
            return "ataque", 1 if self.shoot_flash > 2 else 2  # parado, o tiro mexe o corpo todo
        if self.bow_draw > 0 and not self.moving:
            return "ataque", 0                       # puxando a corda
        if self.moving or self.trail:
            return "andar", self.anim_frame
        return "parado", ((self.age + self.breath_phase) // BREATH) % 2

    def weapon_art_name(self):
        """Qual desenho da arma vai na mão agora (None = mão vazia).

        Arco: vazio depois de soltar ou recarregando, com a flecha encaixada e cada vez mais
        puxado enquanto tensiona. Armas de arremesso somem da mão quando acaba a munição, e a
        Corrente some enquanto a bola está no ar."""
        w = self.weapon
        if w.is_melee or not self.mag:
            return w.name
        if w.charge:
            if self.reloading or self.ammo <= 0 or (self.attack_cd > 0 and self.bow_draw == 0):
                stage = "Vazio"
            elif self.bow_draw <= 0:
                return w.name
            else:
                t = self.bow_draw / BOW_FULL
                stage = None if t < 0.34 else "Puxado" if t < 0.75 else "Tenso"
            name = f"{w.name} {stage}" if stage else w.name
            return name if weapon_art.icon(name) is not None else w.name
        if w.style in THROWN and self.ammo <= 0:
            return None
        if w.style == "corrente" and self.chain_ball is not None and self.chain_ball.alive:
            return None
        return w.name

    def draw(self, surf, camera):
        ticks = self.age
        art = self.weapon_art_name()
        show_weapon = self.armed and art is not None and self.type_timer <= 0    # digitando: mãos no notebook
        sx, sy = round(self.x - camera.x), round(self.y - camera.y)
        feet = sy + FEET
        direction = self._direction()

        # sombra e anel de identificação (caído: só a sombra, que some junto com o corpo)
        shrink = max(0.45, 1 - self.lift / 260)          # no ar, a sombra encolhe
        shadow = pygame.Rect(0, 0, round(38 * self.radius // config.PLAYER_RADIUS * shrink), round(12 * shrink))
        shadow.center = (sx, feet)
        if self.hp > 0 or self.fade > 0.5:
            pygame.draw.ellipse(surf, (10, 8, 14), shadow)
        if self.hp > 0:
            pygame.draw.ellipse(surf, self.ring_color, shadow.inflate(6, 4), 2)

        if self.hp <= 0:
            self._draw_fallen(surf, sx, feet)
            return

        for i, (tx, ty, tdir, tkind, tframe) in enumerate(self.trail):
            ghost = self.sprites.flash(tdir, tframe, tkind).copy()
            ghost.fill((*self.stats.color, 255), special_flags=pygame.BLEND_RGBA_MULT)
            ghost.set_alpha(40 + 25 * i)
            surf.blit(ghost, ghost.get_rect(midbottom=(round(tx - camera.x), round(ty - camera.y) + FEET + 2)))

        flash = self.hit_flash > 0 and self.hit_flash % 2 == 0
        scale = self.draw_scale * (1.5 if self.giant_timer > 0 else 1.0) * (EXO_SCALE if self.exo_timer > 0 else 1.0)
        kind, index = self._pose()
        dodging_moto = self.on_moto and self.dash_timer > 0
        riding = dodging_moto or self.moto_timer > 0     # esquiva de moto ou grau de moto (futebol)
        ride = MOTO_RIDE if riding else 0
        base = (sx, feet + 2 - round(self.lift) - ride)  # meio de baixo do sprite

        spot = self.sprites.hand(direction, kind, index)
        if spot is None:
            # arte antiga, sem a mão marcada: posição fixa por direção
            hand = weapon_art.hand_point(sx, sy, direction, -1 if kind == "andar" and index % 2 else 0)
            if scale != 1.0:
                hand = (sx + (hand[0] - sx) * scale, feet + (hand[1] - feet) * scale - self.lift)
        else:
            hand = (base[0] + spot[0] * scale, base[1] + spot[1] * scale)
        swinging = self.melee_flash > 0 and self.weapon.is_melee
        swing = 1 - self.melee_flash / 12 if swinging else None
        recoil = 3 if self.shoot_flash > 2 else 0
        if self.reloading and not self.weapon.is_melee and (self.reload_timer // 8) % 2:
            recoil = 2                               # mexendo na arma para recarregar
        if show_weapon:
            vx, vy = self.facing if swinging else weapon_art.DIRECTION_VECTORS[direction]
            half = weapon_art.weapon_length(art) / 2
            rare_fx.draw_held(surf, self.weapon, (hand[0] + vx * half, hand[1] + vy * half), ticks)
        if self.guard_frames > 0:
            gadgets.draw_guard(surf, camera, self)
        if show_weapon and direction == "costas" and not swinging:
            weapon_art.draw_weapon(surf, art, hand, direction, self.facing, recoil=recoil)

        if flash and self.aura is None:
            img = self.sprites.flash(direction, index, kind)
        else:
            img = self.sprites.pose(direction, kind, index)
        if scale != 1.0:
            img = pygame.transform.scale(img, (round(img.get_width() * scale), round(img.get_height() * scale)))
        rect = img.get_rect(midbottom=base)
        if self.spin:
            img = pygame.transform.rotate(img, self.spin)
            rect = img.get_rect(center=rect.center)
        if self.aura is not None:
            self._draw_aura(surf, img, rect, ticks)
        surf.blit(img, rect)
        if riding:                                     # a moto na frente das pernas (ele vai sentado)
            if dodging_moto:
                t = 1 - self.dash_timer / max(1, self.dash_len)
                right = self.dash_dir[0] > 0 if abs(self.dash_dir[0]) > 0.2 else self.facing[0] >= 0
                wheelie = 20 * math.sin(math.pi * min(1.0, t * 1.2))
            else:
                right = self.facing[0] >= 0
                wheelie = 10 + 6 * math.sin(self.age * 0.18) if self.moving else 4
            draw_moto(surf, sx, feet + 2, right, wheelie)
        if flash and self.aura is not None:
            # as sombras só clareiam um pouco ao levar dano (não viram um vulto branco)
            hit = pygame.mask.from_surface(img).to_surface(setcolor=(200, 170, 230, 255), unsetcolor=(0, 0, 0, 0))
            hit.set_alpha(90)
            surf.blit(hit, rect)

        if self.windup > 0:
            # aviso do golpe: pisca cada vez mais forte até atacar
            t = 1 - self.windup / self.windup_total
            if (ticks // (3 if t < 0.6 else 2)) % 2 == 0:
                glow = pygame.mask.from_surface(img).to_surface(setcolor=(*self.windup_color, 255),
                                                                unsetcolor=(0, 0, 0, 0))
                glow.set_alpha(round(60 + 110 * t))
                surf.blit(glow, rect)

        if self.fury_timer > 0 and (ticks // 3) % 3 == 0:
            glow = self.sprites.flash(direction, index, kind).copy()
            glow.fill((255, 70, 50, 110), special_flags=pygame.BLEND_RGBA_MULT)
            surf.blit(glow, glow.get_rect(midbottom=rect.midbottom))

        if self.root_timer > 0:                        # raízes subindo pelas pernas
            for k, ox in enumerate((-10, -4, 3, 9)):
                h = 10 + (k * 5) % 9
                pygame.draw.line(surf, (70, 52, 30), (sx + ox, feet + 2), (sx + ox + (2 if k % 2 else -2), feet - h), 3)
                surf.fill((90, 160, 70), (sx + ox - 1, feet - h, 3, 2))
        if self.frozen_timer > 0:                      # bloco de gelo
            ice = pygame.Surface((rect.w + 10, rect.h + 6), pygame.SRCALPHA)
            ice.fill((170, 225, 250, 110))
            pygame.draw.rect(ice, (230, 248, 255, 200), ice.get_rect(), 2)
            ice.fill((255, 255, 255, 160), (4, 4, 3, rect.h // 2))
            surf.blit(ice, (rect.x - 5, rect.y - 4))
        if self.fear_timer > 0 and (ticks // 6) % 2 == 0:
            surf.fill((20, 14, 22), (sx + 12, rect.top - 14, 6, 12))   # "!" de medo
            surf.fill((180, 255, 200), (sx + 13, rect.top - 13, 4, 7))
            surf.fill((180, 255, 200), (sx + 13, rect.top - 4, 4, 2))
        if self.hack_timer > 0 or self.virus_timer > 0:
            self._draw_glitch(surf, img, rect, ticks, strong=self.hack_timer > 0)
        if self.type_timer > 0:
            draw_laptop(surf, sx + round(self.facing[0] * 8), rect.top + rect.h * 0.8, ticks,
                        self.ability_progress(), back=direction == "costas")
        if self.stun_timer > 0 and self.hack_timer <= 0 and self.frozen_timer <= 0:
            for k in range(3):
                a = ticks * 0.15 + k * math.tau / 3
                px = sx + math.cos(a) * 14
                py = rect.top - 4 + math.sin(a) * 4
                pygame.draw.rect(surf, (250, 226, 120), (round(px) - 2, round(py) - 2, 4, 4))

        if self.slow_timer > 0:
            # gelo: azulado e com cristais caindo
            frost = self.sprites.flash(direction, index, kind).copy()
            frost.fill((150, 212, 240, 110), special_flags=pygame.BLEND_RGBA_MULT)
            surf.blit(frost, rect)
            for k in range(3):
                fx = sx - 10 + ((ticks * 2 + k * 9) % 20)
                fy = rect.top + ((ticks + k * 13) % rect.h)
                surf.fill((230, 246, 255), (fx, fy, 2, 2))

        if self.perfect_flash > 0:
            # esquiva perfeita: um contorno branco que some
            shine = self.sprites.flash(direction, index, kind).copy()
            shine.fill((255, 255, 255, 12 * self.perfect_flash), special_flags=pygame.BLEND_RGBA_MULT)
            surf.blit(shine, rect)
            r = 22 + (18 - self.perfect_flash)
            pygame.draw.circle(surf, (230, 244, 255), (sx, rect.centery), r, 2)

        if self.invulnerable_timer > 0 and (ticks // 4) % 2 == 0:
            glow = self.sprites.flash(direction, index, kind).copy()
            glow.fill((255, 210, 90, 120), special_flags=pygame.BLEND_RGBA_MULT)
            surf.blit(glow, rect)

        if show_weapon and (direction != "costas" or swinging):
            tip = weapon_art.draw_weapon(surf, art, hand, direction, self.facing,
                                         swing=swing, recoil=recoil)
            if self.weapon.style == "pulso" and self.bow_draw > 0:
                # carregando: a energia cresce na boca do canhão
                t = min(1.0, self.bow_draw / BOW_FULL)
                r = 2 + round(6 * t) + ((ticks // 2) % 2 if t >= 1 else 0)
                tx, ty = round(tip[0]), round(tip[1])
                pygame.draw.circle(surf, (40, 90, 170), (tx, ty), r + 2)
                pygame.draw.circle(surf, (90, 170, 255), (tx, ty), r)
                pygame.draw.circle(surf, (220, 245, 255), (tx, ty), max(1, r - 3))
            elif self.bow_draw >= BOW_FULL * 0.75 and (ticks // 3) % 2 == 0:
                # flecha tensa: a ponta (encostada no arco) brilha
                vx, vy = weapon_art.DIRECTION_VECTORS[direction]
                surf.fill((255, 236, 170), (round(hand[0] + vx * 5) - 2, round(hand[1] + vy * 5) - 2, 4, 4))
            if self.shoot_flash > 0 and not self.weapon.charge:
                fx, fy = round(tip[0]), round(tip[1])
                r = 1 + self.shoot_flash
                pygame.draw.rect(surf, rare_fx.accent(self.weapon) or (255, 236, 170), (fx - r, fy - r, r * 2, r * 2))
                pygame.draw.rect(surf, (255, 255, 255), (fx - r // 2, fy - r // 2, r, r))

        if swinging:
            rare = rare_fx.accent(self.weapon)          # rara: o rastro tem a cor e o brilho da arma
            color = rare or self.stats.color
            if self.weapon.spin:                       # giro: o rastro dá a volta inteira
                for k in range(4):
                    a = swing * math.tau + k * math.pi / 2
                    weapon_art.draw_slash(surf, (sx, sy - 12), (math.cos(a), math.sin(a)),
                                          weapon_art.weapon_length(self.weapon.name) + 14, swing, color,
                                          glow=rare is not None)
            else:
                weapon_art.draw_slash(surf, hand, self.facing, weapon_art.weapon_length(self.weapon.name) + 2,
                                      swing, color, glow=rare is not None)

        if self.teleport_flash > 0:
            r = 14 + (20 - self.teleport_flash) * 2
            pygame.draw.circle(surf, self.stats.color, (sx, sy - 14), r, 2)

    def ability_progress(self):
        """Quanto da digitação (Hack) já foi (0..1)."""
        total = getattr(self.ability, "TYPING", 0) or 1
        if self.power is not None and hasattr(self.power, "TYPING"):
            total = self.power.TYPING
        return 1 - self.type_timer / total

    def _draw_glitch(self, surf, img, rect, ticks, strong):
        """Hackeado (verde, com faixas da imagem deslocadas) ou com vírus (só piscando verde)."""
        if not strong and (ticks // 4) % 3:
            return
        tint = pygame.mask.from_surface(img).to_surface(setcolor=(90, 240, 120, 255), unsetcolor=(0, 0, 0, 0))
        tint.set_alpha(110 if strong else 70)
        surf.blit(tint, rect)
        if not strong:
            return
        rng = random.Random(ticks // 3 + id(self) % 97)
        for _ in range(3):                                # faixas "pixeladas" fora do lugar
            y = rng.randrange(0, max(1, rect.h - 4))
            h = rng.randint(2, 5)
            off = rng.choice((-5, -3, 3, 5))
            band = img.subsurface((0, y, rect.w, min(h, rect.h - y)))
            surf.blit(band, (rect.x + off, rect.y + y))
        for k in range(2):                                # bits subindo
            bx = rect.centerx - 14 + ((ticks * 3 + k * 17) % 28)
            by = rect.top - 4 - ((ticks + k * 9) % 14)
            surf.fill((120, 255, 150), (bx, by, 2, 3 if (ticks + k) % 2 else 2))

    def _draw_aura(self, surf, img, rect, ticks):
        """Contorno brilhante que pulsa (almas corrompidas e o chefão)."""
        draw_aura(surf, img, rect, self.aura, ticks, max(2, round(2 * self.draw_scale)))

    def _draw_fallen(self, surf, sx, feet):
        """Cai de lado em alguns quadros, fica cinza e, se for um inimigo, vai sumindo (fade)."""
        right = self.facing[0] >= 0
        t = min(1.0, self.down_age / FALL_FRAMES)
        ease = t * t                                     # começa devagar e acelera, como uma queda
        key = ("caido", right, self.draw_scale)
        img = self.sprites.cache.get(key) if t >= 1 else None
        if img is None:
            img = self.sprites.pose("direita" if right else "esquerda", "dano", 0)
            if self.draw_scale != 1.0:
                img = pygame.transform.scale(img, (round(img.get_width() * self.draw_scale),
                                                   round(img.get_height() * self.draw_scale)))
            img = pygame.transform.rotate(img, (90 if right else -90) * ease)
            gray = tuple(round(255 - (255 - c) * t) for c in (150, 140, 150))
            img.fill((*gray, 255), special_flags=pygame.BLEND_RGBA_MULT)
            if t >= 1:
                self.sprites.cache[key] = img
        if self.fade < 1.0:
            img = img.copy()
            img.set_alpha(round(255 * max(0.0, self.fade)))
        surf.blit(img, img.get_rect(midbottom=(sx, feet + round(4 * ease))))

    def draw_overlay(self, surf, camera, ui, show_hp=True):
        """Etiqueta e vida acima da cabeça, desenhadas na tela (fora do zoom)."""
        if self.hp <= 0 or self.overlay == "none":
            return
        sx, sy = camera.to_screen(self.x, self.y - 50 * self.draw_scale - self.lift)
        sx, sy = round(sx), round(sy)
        if self.overlay == "hp":
            # inimigo comum: só uma barrinha, e só depois de levar dano
            if self.hp < self.max_hp:
                ratio = self.hp / self.max_hp
                ui.bar(surf, (sx - 14, sy - 2, 28, 5), ratio, theme.BLOOD if ratio < 0.4 else theme.EMBER)
            return
        tag = ui.assets.text(self.label, theme.XS, self.color)
        tr = tag.get_rect(midbottom=(sx, sy - (8 if show_hp else 2)))
        surf.fill(theme.SHADOW, tr.inflate(6, 4))
        surf.blit(tag, tr)
        if not show_hp and self.stamina < 0.995:
            # barra de fôlego da corrida (futebol)
            bar = pygame.Rect(0, 0, max(28, tr.w), 4)
            bar.midtop = (sx, tr.bottom + 3)
            surf.fill(theme.SHADOW, bar.inflate(2, 2))
            fill = bar.copy()
            fill.w = round(bar.w * self.stamina)
            color = (200, 90, 70) if self.exhausted else (120, 200, 110)
            surf.fill(color, fill)
        if show_hp:
            ratio = self.hp / self.max_hp
            color = theme.MOSS if ratio > 0.5 else theme.BRASS if ratio > 0.25 else theme.BLOOD
            ui.bar(surf, (sx - 18, sy - 6, 36, 6), ratio, color)
            if self.shield > 0:
                surf.fill((150, 212, 240), (sx - 18, sy - 9, round(36 * min(1, self.shield / 40)), 2))
            self._draw_ammo(surf, sx, sy + 1)

    def _draw_ammo(self, surf, cx, y):
        """Munição embaixo da vida: um tracinho por tiro (dourado = munição extra do item)
        ou a barra da recarga enchendo."""
        mag = self.mag
        if not mag or (self.weapon.is_melee and not self.reloading):
            return
        if self.reloading:
            w = 36
            surf.fill(theme.SHADOW, (cx - w // 2 - 1, y - 1, w + 2, 5))
            surf.fill((58, 44, 22), (cx - w // 2, y, w, 3))
            surf.fill(theme.BRASS, (cx - w // 2, y, round(w * self.reload_ratio), 3))
            return
        cap = max(mag, self.ammo)
        pip = max(1, min(4, (36 - (cap - 1)) // cap))
        total = cap * pip + cap - 1
        x = cx - total // 2
        surf.fill(theme.SHADOW, (x - 1, y - 1, total + 2, 5))
        for i in range(cap):
            if i >= self.ammo:
                color = (44, 40, 54)
            elif i >= mag:
                color = theme.BRASS
            else:
                color = (226, 220, 200)
            surf.fill(color, (x + i * (pip + 1), y, pip, 3))
