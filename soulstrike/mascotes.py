"""Os mascotes da Casa: o gato no sofá, o cachorro caramelo na casinha do quintal e o papagaio no
poleiro perto do canto do Aryel. Liberados desde o começo e só de enfeite (não batem, não apanham).

Na Casa, ATACAR perto de um bicho em casa adota: ele passa a seguir aquele jogador (na Casa e nas
fases), do jeitinho da IARA. Cada bicho tem um dono só, guardado no progresso pelo número do
jogador (P1 a P4). ATACAR perto do cantinho dele, com ele atrás, deixa o bicho em casa de novo.

Um pet por jogador: adotar um bicho da Casa devolve o outro que ele tinha (e tira o pet da loja de
CACOS), e pegar um pet da loja no armário manda o bicho da Casa de volta para o cantinho dele."""
import math
import random

import pygame

from . import cacos, pecas, pet_falas, progress, settings, theme
from .entities import Entity, Particle
from .skins import PETS as SHOP_PETS

REACH = 70
KEY = "mascotes"
# bicho: (nome, voa?, o que ele "fala" de vez em quando)
PETS = {
    "gato": ("GATO", False, ("MIAU", "PRRR...", "MIAU?")),
    "cachorro": ("CACHORRO", False, ("AU AU!", "AU!", "*ABANA O RABO*")),
    "papagaio": ("PAPAGAIO", True, ("CURRUPACO!", "DÁ O PÉ, LOURO!", "GREEN!")),
}


def owners():
    """{bicho: número do jogador dono}."""
    data = progress.load().get(KEY)
    if not isinstance(data, dict):
        return {}
    return {k: v for k, v in data.items() if k in PETS and isinstance(v, int)}


def set_owner(pet, slot):
    data = progress.load()
    pets = data.get(KEY) if isinstance(data.get(KEY), dict) else {}
    if slot is None:
        pets.pop(pet, None)
    else:
        pets[pet] = slot
    data[KEY] = pets
    return progress.save(data)


# ── animação ─────────────────────────────────
# 6 estados (tools/gerar_pets_anim.py): cada um é uma folha com os quadros lado a lado
ANIMS = ("parado", "andando", "especial", "feliz", "susto", "dormindo")
SPEED = {"parado": 14, "andando": 6, "especial": 10, "feliz": 6, "susto": 8, "dormindo": 36}   # ticks por quadro
COUNT = {"parado": 4, "andando": 4, "feliz": 4, "susto": 2, "dormindo": 2}
SPECIAL_COUNT = {"gato": 5, "cachorro": 5, "capivara": 5, "mico": 5}                        # os outros: 6
ONESHOT_LOOPS = {"especial": 2, "feliz": 2, "susto": 3}
_SHEETS = {}


def frames(pet, anim):
    """Os quadros de um estado (lista de Surfaces), ou [] se a folha não existe."""
    key = (pet, anim)
    if key not in _SHEETS:
        sheet = pecas.image(f"pet_{pet}_{anim}")
        out = []
        if sheet is not None:
            n = SPECIAL_COUNT.get(pet, 6) if anim == "especial" else COUNT[anim]
            w, h = sheet.get_width() // n, sheet.get_height()
            out = [sheet.subsurface((i * w, 0, w, h)) for i in range(n)]
        _SHEETS[key] = out
    return _SHEETS[key]


def _frames(pet):
    sit = pecas.image(f"mascote_{pet}_sentado")
    walk = pecas.image(f"mascote_{pet}_andando")
    return sit, walk


# ── falas ─────────────────────────────────────
TALK_GAP = 20 * 60          # um pet fala no máximo uma vez a cada 20 s (no POUCAS, 40 s)
TALK_GAP_FEW = 40 * 60
BETWEEN_PETS = 6 * 60       # e os pets esperam 6 s entre a fala de um e a de outro
BUBBLE_FRAMES = 150         # o balão fica uns 2,5 s
URGENT = ("caiu", "levantou", "chefe", "vitoria", "parado")
STILL_TALK = 10 * 60        # dono parado uns 10 s: o pet faz a graça dele e fala
SLEEP_AFTER = 30 * 60       # na Casa, parado uns 30 s: o pet dorme
LOW_HP = 0.3
LOW_ENERGY = 0.15
FALAS = ("normal", "poucas", "desligadas")

# ── ajuda: busca do chão e aviso do chefe ─────
FETCH_EVERY = 4 * 60        # a cada 4 s o pet pode buscar um item caído perto do dono
FETCH_RANGE = 150           # uns 3 passos do dono
FETCH_GIVE_UP = 5 * 60
WARN_WINDUP = 30            # golpe do chefe com preparo longo (o golpe forte): o pet avisa
WARN_RANGE = 560


def talk_mode():
    mode = settings.get("falas_pets")
    return mode if mode in FALAS else "normal"


def _clock(match, pet):
    frame = getattr(match, "frame", None)
    return frame if isinstance(frame, int) else pet.age


class Pet(Entity):
    """Um mascote: em casa (parado no cantinho) ou seguindo o dono, com 6 estados de animação,
    balãozinho de fala com som e a ajuda (busca itens caídos perto do dono, avisa o golpe forte)."""

    def __init__(self, pet, home, home_sort=None):
        super().__init__(*home)
        self.pet = pet
        if pet in PETS:
            self.name, self.flies, self.lines = PETS[pet]
        else:                                       # pet da loja de CACOS
            shop = SHOP_PETS[pet]
            self.name, self.flies, self.lines = shop.name, shop.flies, shop.lines
        self.shop = pet in SHOP_PETS and pet not in PETS
        self.home = home
        self.home_sort = home_sort                  # gato no sofá: desenhado por cima do sofá
        self.target = None                          # o lutador que ele segue
        self.age = random.randrange(200)
        self.moving = 0.0
        self.facing = 1
        self.sit, self.walk = _frames(pet)
        # animação
        self.anim, self.anim_t = "parado", random.randrange(40)
        self.oneshot = None                         # estado que toca uma vez e volta (especial, feliz, susto)
        self.warn = 0                               # "!" do aviso do chefe
        # o que ele vê do dono (para saber quando falar)
        self.seen = {}
        self.still = 0
        self.last_pos = None
        self.home_nap = random.randrange(600)
        # fala
        self.bubble, self.bubble_t = None, 0
        self.next_talk = 0
        # busca
        self.fetch_cd = FETCH_EVERY
        self.fetching, self.carry, self.fetch_t = None, None, 0
        self._assets = None

    @property
    def sort_y(self):
        if self.target is None and self.home_sort is not None:
            return self.home_sort
        return self.y + (40 if self.flies and self.target is not None else 0)

    def follow(self, fighter):
        self.target = fighter
        self.seen = {}
        self.still = 0

    def stay(self):
        self.drop()
        self.target = None

    # ── animação ─────────────────────────────
    def play(self, anim):
        """Toca um estado uma vez (especial, feliz ou susto) e depois volta ao normal."""
        if frames(self.pet, anim):
            self.oneshot, self.anim, self.anim_t = anim, anim, 0

    def _base_anim(self, match):
        if self.target is None:                     # em casa: fica, cochila e às vezes faz a graça dele
            cycle = (self.age + self.home_nap) % (40 * 60)
            return "dormindo" if cycle > 26 * 60 else "parado"
        if self.moving > 0.4 or self.fetching is not None:
            return "andando"
        if self.still >= SLEEP_AFTER and getattr(match, "pets", None) is not None and self.target.alive_in_match:
            return "dormindo"                       # só na Casa (match.pets existe lá)
        if self.flies and self.pet == "papagaio":
            return "andando"                        # seguindo, o papagaio fica voando
        return "parado"

    def _animate(self, match):
        self.anim_t += 1
        if self.oneshot is not None:
            n = len(frames(self.pet, self.oneshot)) or 1
            if self.anim_t >= n * SPEED[self.oneshot] * ONESHOT_LOOPS.get(self.oneshot, 1):
                self.oneshot = None
            else:
                return
        base = self._base_anim(match)
        if base != self.anim:
            self.anim, self.anim_t = base, 0

    def image(self):
        """O quadro de agora (ou o desenho antigo, se a folha do estado não existe)."""
        fr = frames(self.pet, self.anim)
        if fr:
            return fr[(self.anim_t // SPEED[self.anim]) % len(fr)]
        return self.walk if self.anim == "andando" else self.sit

    # ── fala ─────────────────────────────────
    def say(self, match, moment):
        """Fala uma frase do momento num balãozinho, com o somzinho do bicho. Respeita o limite
        (uma fala a cada 20 s por pet, 6 s entre pets, um balão por vez) e a opção FALAS DOS PETS."""
        mode = talk_mode()
        if mode == "desligadas":
            return False
        now = _clock(match, self)
        if now < self.next_talk:
            return False
        talk = getattr(match, "_pet_talk", None)
        if talk is None:
            talk = match._pet_talk = {"next": 0, "who": None}
        if now < talk["next"] and moment not in URGENT:
            return False
        who = talk.get("who")
        if who is not None and who is not self and who.bubble is not None:
            if moment not in URGENT:
                return False
            who.bubble = None                       # um balão por vez: o urgente passa na frente
        lines = pet_falas.LINES.get(self.pet, {}).get(moment) or self.lines
        self.bubble, self.bubble_t = random.choice(lines), BUBBLE_FRAMES
        self.next_talk = now + (TALK_GAP if mode == "normal" else TALK_GAP_FEW)
        talk["next"], talk["who"] = now + BETWEEN_PETS, self
        assets = getattr(match, "assets", None)
        if assets is not None:
            assets.play(f"pet_{self.pet}_{random.randint(1, 2)}", 0.35)
        return True

    def _watch(self, match):
        """Olha o dono e a luta e decide quando falar e qual animação tocar."""
        t = self.target
        seen = self.seen
        first = not seen
        alive = t.alive_in_match
        hp = t.hp / max(1, t.max_hp)
        energy = None
        if getattr(t, "energy", None) is not None and getattr(t, "energy_max", 0):
            energy = t.energy / t.energy_max
        relic = getattr(t, "relic", None)
        boss = getattr(match, "boss", None)
        boss_on = boss is not None and boss.alive_in_match
        wins = len(getattr(match, "cleared", ()) or ()) + (1 if getattr(match, "slain_boss", False) else 0)
        casa = getattr(match, "pets", None) is not None
        # dono parado (nem andando nem batendo)
        pos = (round(t.x), round(t.y))
        if pos == self.last_pos and getattr(t, "attack_cd", 0) <= 0 and alive:
            self.still += 1
        else:
            if self.still >= SLEEP_AFTER:
                self.play("feliz")                  # acordou com o dono andando
            self.still = 0
        self.last_pos = pos
        if first:
            seen.update(alive=alive, low=hp < LOW_HP, empty=energy is not None and energy < LOW_ENERGY,
                        relic=relic, boss=boss if boss_on else None, wins=wins, start=self.age)
            return
        if self.age - seen["start"] == 120 and not casa and getattr(match, "run", None) is not None:
            self.say(match, "fase")
        if seen["alive"] and not alive:
            self.play("susto")
            self.say(match, "caiu")
        elif not seen["alive"] and alive:
            self.play("feliz")
            self.say(match, "levantou")
        seen["alive"] = alive
        low = hp < LOW_HP and alive
        if low and not seen["low"]:
            self.say(match, "vida")
        seen["low"] = low
        empty = energy is not None and energy < LOW_ENERGY and alive
        if empty and not seen["empty"]:
            self.say(match, "energia")
        seen["empty"] = empty
        if relic is not None and relic is not seen["relic"]:
            self.play("feliz")
            self.say(match, "arma")
        seen["relic"] = relic
        if boss_on and boss is not seen["boss"]:
            self.play("susto")
            self.say(match, "chefe")
            seen["boss"] = boss
        if wins > seen["wins"]:
            self.play("feliz")
            self.say(match, "vitoria")
        seen["wins"] = wins
        if self.still and self.still % (2 * STILL_TALK) == STILL_TALK and not (casa and self.still >= SLEEP_AFTER):
            self.play("especial")
            self.say(match, "casa" if casa else "parado")
        self._warn(match, boss if boss_on else None)

    def _warn(self, match, boss):
        """Golpe forte do chefe chegando: susto com um "!" um instante antes (só a animação)."""
        if boss is None:
            self.seen["windup"] = 0
            return
        w = getattr(boss, "windup", 0)
        prev = self.seen.get("windup", 0)
        self.seen["windup"] = w
        if w > prev and getattr(boss, "windup_total", 0) >= WARN_WINDUP and self.target.alive_in_match:
            if math.hypot(boss.x - self.target.x, boss.y - self.target.y) < WARN_RANGE:
                self.play("susto")
                self.warn = 40

    # ── busca ────────────────────────────────
    def _useful(self, item, owner):
        if not getattr(item, "alive", True) or getattr(item, "_pet", None) not in (None, self):
            return False
        kind = getattr(item, "kind", "")
        if kind == "orbe":
            return getattr(owner, "energy", None) is not None and owner.energy < owner.energy_max
        if kind == "vida":
            return owner.hp < owner.max_hp
        return kind in ("furia", "energia", "municao")

    def _pick_fetch(self, match):
        t = self.target
        items = getattr(match, "pickups", None)
        if not items or not t.alive_in_match or getattr(match, "pets", None) is not None:
            return
        best, best_d = None, FETCH_RANGE
        for item in items:
            d = math.hypot(item.x - t.x, item.y - t.y)
            if d < best_d and d > t.radius + item.radius + 10 and self._useful(item, t):
                best, best_d = item, d
        if best is not None:
            best._pet = self
            self.fetching, self.fetch_t = best, 0

    def drop(self):
        for item in (self.fetching, self.carry):
            if item is not None and getattr(item, "_pet", None) is self:
                item._pet = None
        self.fetching = self.carry = None

    def _fetch(self, match):
        """Indo buscar (ou trazendo) um item: devolve o ponto aonde ir, ou None se não está buscando."""
        t = self.target
        self.fetch_t += 1
        item = self.carry or self.fetching
        if item is None:
            return None
        if not item.alive or self.fetch_t > FETCH_GIVE_UP or not t.alive_in_match:
            self.drop()
            self.fetch_cd = FETCH_EVERY
            return None
        if self.carry is None:
            if math.hypot(item.x - self.x, item.y - self.y) < 14:
                self.carry, self.fetching = item, None
            return item.x, item.y
        item.x, item.y = self.x, self.y - (30 if self.flies else 14)
        if hasattr(item, "vx"):
            item.vx = item.vy = 0.0
        if math.hypot(t.x - self.x, t.y - self.y) < t.radius + 34:
            self.drop()
            self.fetch_cd = FETCH_EVERY
            item.x, item.y = t.x, t.y
            item.apply(t, match)
            if not item.alive:
                self.play("feliz")
                self.say(match, "busca")
            return None
        return t.x, t.y

    # ── quadro a quadro ──────────────────────
    def update(self, match):
        self.age += 1
        self._assets = getattr(match, "assets", None)
        goal, speed_cap = None, 7.0
        if self.target is not None:
            self._watch(match)
            goal = self._fetch(match)
            if goal is None and self.fetching is None and self.carry is None:
                self.fetch_cd -= 1
                if self.fetch_cd <= 0:
                    self.fetch_cd = 30                  # nada por perto: olha de novo daqui a pouco
                    self._pick_fetch(match)
            if goal is not None:
                speed_cap = 3.0 if self.pet in ("jabuti", "capivara") else 6.5
        if goal is not None:
            gx, gy = goal
        elif self.target is None:
            gx, gy = self.home
        else:
            t = self.target
            side = -1 if t.facing[0] >= 0 else 1    # fica atrás de quem ele segue
            gx = t.x + side * (34 if not self.flies else 26)
            gy = t.y + (6 if not self.flies else -58)
        dx, dy = gx - self.x, gy - self.y
        dist = math.hypot(dx, dy)
        if self.target is None and dist > 400:      # adotado em outra sala: aparece direto em casa
            self.x, self.y = gx, gy
            dist = 0
        step = min(dist, 1.0 + dist * 0.07, speed_cap)
        if dist > 3:
            self.x += dx / dist * step
            self.y += dy / dist * step
            if abs(dx) > 1:
                self.facing = 1 if dx > 0 else -1
        self.moving = step if dist > 3 else 0.0
        if self.target is not None and self.anim not in ("andando",) and self.moving <= 0.4:
            self.facing = 1 if self.target.x >= self.x else -1      # parado: olha para o dono
        self._animate(match)
        if self.bubble is not None:
            self.bubble_t -= 1
            if self.bubble_t <= 0:
                self.bubble = None
        if self.warn:
            self.warn -= 1
        if self.pet == "cachorro" and self.moving and self.age % 14 == 0:
            match.particles.append(Particle(self.x - self.facing * 12, self.y, 0, -0.2, (150, 130, 100), 14, 2))

    def draw(self, surf, cam):
        img = self.image()
        if img is None:
            return
        if self.facing < 0:
            img = pygame.transform.flip(img, True, False)
        sx, sy = round(self.x - cam.x), round(self.y - cam.y)
        airborne = self.flies and self.target is not None and self.anim != "dormindo"
        if airborne:
            sy += round(math.sin(self.age * 0.18) * 4)
        if not airborne:
            surf.blit(pecas.shadow(max(10, img.get_width() - 10), 8, 70), (sx - img.get_width() // 2 + 5, sy - 4))
        surf.blit(img, img.get_rect(midbottom=(sx, sy)))
        if self.anim == "dormindo" and self._assets is not None:
            z = "Z" if (self.age // 40) % 2 else "z"
            surf.blit(self._assets.text(z, theme.XS, (200, 210, 255)), (sx + 8, sy - img.get_height() - 4 - (self.age // 6) % 6))

    def draw_talk(self, screen, cam, ui):
        """Por cima de tudo (na tela): o balão de fala e o "!" do aviso."""
        if self.bubble is None and not self.warn:
            return
        img = self.image()
        top = (img.get_height() if img is not None else 30) + (8 if self.flies and self.target is not None else 2)
        sx, sy = cam.to_screen(self.x, self.y - top)
        if self.warn and (self.warn // 4) % 2 == 0:
            ui.text(screen, "!", theme.M, (255, 210, 60), (round(sx) + 18, round(sy) + 6))
        if self.bubble is not None:
            from .casa import draw_bubble
            draw_bubble(screen, ui, ui.assets, self.bubble, round(sx), round(sy))


# ── na Casa ──────────────────────────────────
def home_spots(T, OY, QY):
    """Onde cada bicho mora na Casa: (pé no chão, ordem de desenho ou None)."""
    return {
        "gato": ((18 * T + 108, OY + 11 * T + 66), OY + 11 * T + 30 + 60),     # no assento do sofá azul
        "cachorro": ((18 * T + 40, QY + 6 * T + 34), None),                       # na porta da casinha
        "papagaio": ((38 * T, OY + 2 * T - 16), OY + 2 * T + 32),                 # no poleiro
    }


def send_home(match, slot, keep=None):
    """Um pet por jogador: os bichos da Casa do jogador ``slot`` (menos ``keep``) voltam para casa."""
    for pet, owner in owners().items():
        if owner == slot and pet != keep:
            set_owner(pet, None)
    for p in getattr(match, "pets", ()):
        if p.pet != keep and p.target is not None and p.target.slot == slot:
            p.stay()


def tidy():
    """Saves antigos podiam ter vários bichos por jogador: fica só um (o pet da loja, se tiver;
    senão o primeiro bicho da Casa)."""
    seen = {s for s in range(1, 5) if cacos.pet_of(s) is not None}
    for pet in PETS:
        owner = owners().get(pet)
        if owner is None:
            continue
        if owner in seen:
            set_owner(pet, None)
        else:
            seen.add(owner)


def furnish(match, T, OY, QY, put, art):
    """Põe a casinha, o poleiro e os três bichos na Casa (cada um com o dono que tiver)."""
    spots = home_spots(T, OY, QY)
    put(art.doghouse, 18 * T, QY + 6 * T + 20, foot=((-36, -20, 72, 22),))
    put(art.perch, 38 * T, OY + 2 * T + 30, foot=((-14, -6, 28, 10),))
    match.pets = []
    tidy()
    own = owners()
    for pet, (home, sort) in spots.items():
        p = Pet(pet, home, sort)
        owner = next((f for f in match.players if f.slot == own.get(pet)), None)
        if owner is not None:
            p.follow(owner)
            p.x, p.y = owner.x - 30, owner.y + 6
        match.pets.append(p)
        match.props.append(p)


def join(match):
    """Nas fases: os bichos adotados vêm junto com os donos que estão jogando."""
    tidy()
    own = owners()
    for pet in PETS:
        owner = next((f for f in match.players if f.slot == own.get(pet)), None)
        if owner is None:
            continue
        p = Pet(pet, (owner.x - 30, owner.y + 6))
        p.follow(owner)
        match.props.append(p)
    join_shop(match)


def join_shop(match):
    """Os pets da loja de CACOS: cada jogador leva o que escolheu no armário (na Casa e nas fases)."""
    for f in match.players:
        pet = cacos.pet_of(f.slot)
        if pet is None or pet not in SHOP_PETS:
            continue
        p = Pet(pet, (f.x - 30, f.y + 6))
        p.follow(f)
        match.props.append(p)


def refresh_shop(match):
    """Trocou de pet no armário: tira os pets da loja que estavam seguindo e põe os escolhidos."""
    old = {id(p): (p.target, p.x, p.y) for p in match.props if isinstance(p, Pet) and p.shop}
    match.props[:] = [p for p in match.props if not (isinstance(p, Pet) and p.shop)]
    join_shop(match)
    for p in match.props:                       # quem já estava seguindo continua no mesmo lugar
        if isinstance(p, Pet) and p.shop:
            for target, x, y in old.values():
                if target is p.target:
                    p.x, p.y = x, y


def _home_near(match, f):
    for p in getattr(match, "pets", ()):
        hx, hy = p.home
        if math.hypot(f.x - hx, f.y - hy) < REACH:
            return p
    return None


def prompt(match, f):
    """O que ATACAR faz com o bicho perto (ou None)."""
    p = _home_near(match, f)
    if p is None:
        return None
    if p.target is None:
        owner = owners().get(p.pet)
        if owner is not None and owner != f.slot and any(q.slot == owner for q in match.players):
            return None
        return f"ATACAR: ADOTAR O {p.name}" if owner in (None, f.slot) else f"O {p.name} É DO P{owner}"
    if p.target is f:
        return f"ATACAR: DEIXAR O {p.name} EM CASA"
    return None


def interact(match, f):
    """ATACAR perto do cantinho de um bicho: adota (se não tem dono aqui) ou deixa em casa."""
    p = _home_near(match, f)
    if p is None:
        return False
    owner = owners().get(p.pet)
    if p.target is f:
        p.stay()
        set_owner(p.pet, None)
        match.popup(p.home[0], p.home[1] - 70, f"O {p.name} FICOU EM CASA", theme.BONE)
        match.assets.play("click", 0.4)
        return True
    if p.target is not None or owner not in (None, f.slot):
        return False
    send_home(match, f.slot, keep=p.pet)        # um pet por jogador
    if cacos.pet_of(f.slot) is not None:
        cacos.set_pet(f.slot, None)
        refresh_shop(match)
    p.follow(f)
    set_owner(p.pet, f.slot)
    match.popup(p.home[0], p.home[1] - 70, f"P{f.slot} ADOTOU O {p.name}!", theme.MOSS)
    match.burst(p.x, p.y - 20, (255, 200, 220), 14, speed=3)
    match.assets.play("confirm", 0.5)
    return True


def draw_prompts(match, screen, ui, free, frame):
    blink = theme.BRASS if (frame // 15) % 2 else theme.BONE
    shown = set()
    for f in free:
        text = prompt(match, f)
        p = _home_near(match, f)
        if text and p is not None and p.pet not in shown:
            shown.add(p.pet)
            sx, sy = match.camera.to_screen(p.home[0], p.home[1] - 64)
            ui.text(screen, text, theme.XS, blink if text.startswith("ATACAR") else theme.FAINT,
                    (round(sx), round(sy)))
