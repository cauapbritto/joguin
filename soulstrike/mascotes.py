"""Os mascotes da Casa: o gato no sofá, o cachorro caramelo na casinha do quintal e o papagaio no
poleiro perto do canto do Aryel. Liberados desde o começo e só de enfeite (não batem, não apanham).

Na Casa, ATACAR perto de um bicho em casa adota: ele passa a seguir aquele jogador (na Casa e nas
fases), do jeitinho da IARA. Cada bicho tem um dono só, guardado no progresso pelo número do
jogador (P1 a P4). ATACAR perto do cantinho dele, com ele atrás, deixa o bicho em casa de novo."""
import math
import random

import pygame

from . import pecas, progress, theme
from .entities import Entity, Particle

REACH = 70
KEY = "mascotes"
# bicho: (nome, voa?, o que ele "fala" de vez em quando)
PETS = {
    "gato": ("GATO", False, ("MIAU", "PRRR...", "MIAU?")),
    "cachorro": ("CACHORRO", False, ("AU AU!", "AU!", "*ABANA O RABO*")),
    "papagaio": ("PAPAGAIO", True, ("CURRUPACO!", "DÁ O PÉ, LOURO!", "GREEN!")),
}
TALK_EVERY = 900


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


def _frames(pet):
    sit = pecas.image(f"mascote_{pet}_sentado")
    walk = pecas.image(f"mascote_{pet}_andando")
    return sit, walk


class Pet(Entity):
    """Um mascote: em casa (parado no cantinho) ou seguindo o dono."""

    def __init__(self, pet, home, home_sort=None):
        super().__init__(*home)
        self.pet = pet
        self.name, self.flies, self.lines = PETS[pet]
        self.home = home
        self.home_sort = home_sort                  # gato no sofá: desenhado por cima do sofá
        self.target = None                          # o lutador que ele segue
        self.age = random.randrange(200)
        self.moving = 0.0
        self.facing = 1
        self.sit, self.walk = _frames(pet)

    @property
    def sort_y(self):
        if self.target is None and self.home_sort is not None:
            return self.home_sort
        return self.y + (40 if self.flies and self.target is not None else 0)

    def follow(self, fighter):
        self.target = fighter

    def stay(self):
        self.target = None

    def update(self, match):
        self.age += 1
        if self.target is None:
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
        step = min(dist, 1.0 + dist * 0.07, 7.0)
        if dist > 3:
            self.x += dx / dist * step
            self.y += dy / dist * step
            if abs(dx) > 1:
                self.facing = 1 if dx > 0 else -1
        self.moving = step if dist > 3 else 0.0
        if self.age % TALK_EVERY == TALK_EVERY // 2 and self.target is not None:
            match.popup(self.x, self.y - 60, random.choice(self.lines), theme.BONE)
        if self.pet == "cachorro" and self.moving and self.age % 14 == 0:
            match.particles.append(Particle(self.x - self.facing * 12, self.y, 0, -0.2, (150, 130, 100), 14, 2))

    def draw(self, surf, cam):
        img = self.walk if (self.moving > 0.4 or (self.flies and self.target is not None)) else self.sit
        if img is None:
            return
        if img is self.walk and self.facing < 0:
            img = pygame.transform.flip(img, True, False)
        sx, sy = round(self.x - cam.x), round(self.y - cam.y)
        if self.flies and self.target is not None:
            sy += round(math.sin(self.age * 0.18) * 4)
        elif img is self.walk:
            sy -= (self.age // 5) % 2                  # passinho
        if not (self.flies and self.target is not None):
            surf.blit(pecas.shadow(img.get_width() - 6, 8, 70), (sx - img.get_width() // 2 + 3, sy - 4))
        surf.blit(img, img.get_rect(midbottom=(sx, sy)))


# ── na Casa ──────────────────────────────────
def home_spots(T, OY, QY):
    """Onde cada bicho mora na Casa: (pé no chão, ordem de desenho ou None)."""
    return {
        "gato": ((18 * T + 108, OY + 11 * T + 66), OY + 11 * T + 30 + 60),     # no assento do sofá azul
        "cachorro": ((18 * T + 40, QY + 6 * T + 34), None),                       # na porta da casinha
        "papagaio": ((38 * T, OY + 2 * T - 16), OY + 2 * T + 32),                 # no poleiro
    }


def furnish(match, T, OY, QY, put, art):
    """Põe a casinha, o poleiro e os três bichos na Casa (cada um com o dono que tiver)."""
    spots = home_spots(T, OY, QY)
    put(art.doghouse, 18 * T, QY + 6 * T + 20, foot=((-36, -20, 72, 22),))
    put(art.perch, 38 * T, OY + 2 * T + 30, foot=((-14, -6, 28, 10),))
    match.pets = []
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
    own = owners()
    for pet in PETS:
        owner = next((f for f in match.players if f.slot == own.get(pet)), None)
        if owner is None:
            continue
        p = Pet(pet, (owner.x - 30, owner.y + 6))
        p.follow(owner)
        match.props.append(p)


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
