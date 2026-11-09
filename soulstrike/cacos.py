"""CACOS: a moeda da loja da Casa (os caquinhos do cristal da IARA que sobram depois da aventura).

Diferente das almas (que são o dinheiro de dentro da fase e somem quando a campanha acaba), os cacos
ficam no progresso salvo do computador, num pote só da turma. Só compram coisa de enfeite (skins):
nada na loja muda dano, vida, energia ou arma.

Como ganhar:
- zerar a campanha inteira (começando do capítulo 1, fora a Reunião dos Corrompidos) paga pouco,
  conforme a dificuldade (REWARD), e paga o dobro na primeira vez em cada dificuldade;
- um cupom vale uma vez por save. O jogo guarda só a impressão digital (hash) de cada código, nunca o
  código escrito. Para criar cupom novo: ``python tools/novo_cupom.py CODIGO CACOS [skin]``.
"""
import hashlib
import unicodedata

from . import progress

KEY = "cacos"
REWARD = {"facil": 5, "normal": 10, "dificil": 15, "ibrahim": 20, "borba": 30}
SALT = "soulstrike-cacos-v1:"
MAX_TRIES = 5                 # erros seguidos antes de esperar
WAIT_FRAMES = 30 * 60         # 30 s esperando depois de MAX_TRIES erros

# impressão digital do código -> (cacos, skin que vem junto ou None)
COUPONS = {
    "4475ad932e56cf7f": (1000, "albeguinio_hacker"),
    "eacee0ca8307cba3": (1000, "cauanzera_cristal"),
    "dc315796ec08150b": (1000, "aryel_fogo"),
    "0dbd4e942cde0cde": (1000, "borba_ouro"),
}


def normalize(code):
    """Maiúsculas, sem acento, sem espaço nem pontuação: "Pão de Mel!" vira "PAODEMEL"."""
    text = unicodedata.normalize("NFD", str(code or ""))
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    return "".join(ch for ch in text.upper() if ch.isalnum())


def fingerprint(code):
    return hashlib.sha256((SALT + normalize(code)).encode("utf-8")).hexdigest()[:16]


# ── o pote ───────────────────────────────────
def _box(data):
    box = data.get(KEY)
    if not isinstance(box, dict):
        box = {}
        data[KEY] = box
    return box


def balance():
    box = progress.load().get(KEY)
    if not isinstance(box, dict):
        return 0
    try:
        return max(0, int(box.get("saldo", 0)))
    except (TypeError, ValueError):
        return 0


def add(amount):
    data = progress.load()
    box = _box(data)
    box["saldo"] = max(0, int(box.get("saldo", 0) or 0)) + max(0, int(amount))
    progress.save(data)
    return box["saldo"]


def spend(amount):
    """Tira ``amount`` do pote. False (sem mexer em nada) se não tiver o bastante."""
    data = progress.load()
    box = _box(data)
    have = max(0, int(box.get("saldo", 0) or 0))
    if amount > have:
        return False
    box["saldo"] = have - amount
    progress.save(data)
    return True


def reward_for(difficulty, first):
    base = REWARD.get(difficulty, REWARD["normal"])
    return base * 2 if first else base


def pay_campaign(difficulty):
    """Campanha inteira zerada: soma os cacos da dificuldade (o dobro na primeira vez nela).
    Devolve quanto ganhou."""
    data = progress.load()
    box = _box(data)
    paid = box.setdefault("dificuldades", [])
    first = difficulty not in paid
    if first:
        paid.append(difficulty)
    gain = reward_for(difficulty, first)
    box["saldo"] = max(0, int(box.get("saldo", 0) or 0)) + gain
    progress.save(data)
    return gain


# ── skins ─────────────────────────────────────
def owned():
    box = progress.load().get(KEY)
    skins = box.get("skins") if isinstance(box, dict) else None
    return set(skins) if isinstance(skins, list) else set()


def give_skin(skin):
    data = progress.load()
    box = _box(data)
    skins = box.setdefault("skins", [])
    if skin not in skins:
        skins.append(skin)
    progress.save(data)


def worn(hero):
    """A skin que o herói está usando (ou None)."""
    box = progress.load().get(KEY)
    wear = box.get("vestidas") if isinstance(box, dict) else None
    skin = wear.get(hero) if isinstance(wear, dict) else None
    return skin if skin in owned() else None


def wear(hero, skin):
    """Veste ``skin`` no herói (None tira)."""
    data = progress.load()
    box = _box(data)
    wear_ = box.setdefault("vestidas", {})
    if skin is None:
        wear_.pop(hero, None)
    else:
        wear_[hero] = skin
    progress.save(data)


# ── cupons ────────────────────────────────────
def redeem(code):
    """Usa o cupom. Devolve (situação, cacos, skin): situação "ok", "usado" ou "invalido"."""
    key = fingerprint(code)
    if not normalize(code) or key not in COUPONS:
        return "invalido", 0, None
    data = progress.load()
    box = _box(data)
    used = box.setdefault("cupons", [])
    if key in used:
        return "usado", 0, None
    amount, skin = COUPONS[key]
    used.append(key)
    box["saldo"] = max(0, int(box.get("saldo", 0) or 0)) + amount
    if skin:
        skins = box.setdefault("skins", [])
        if skin not in skins:
            skins.append(skin)
    progress.save(data)
    return "ok", amount, skin
