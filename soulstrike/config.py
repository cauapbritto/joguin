"""Caminhos, tamanho de tela e constantes de jogabilidade."""
import sys
from pathlib import Path

# No executável (PyInstaller) os arquivos ficam na pasta temporária _MEIPASS
ROOT = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent))
ASSETS_DIR = ROOT / "assets"
CHAR_DIR = ASSETS_DIR / "characters"
TILES_DIR = ASSETS_DIR / "tiles"
SOUNDS_DIR = ASSETS_DIR / "sounds"
FONT_PATH = ASSETS_DIR / "font" / "PressStart2P-Regular.ttf"
WEB_DIR = ROOT / "web"

TITLE = "Soul Strike"
SCREEN_W, SCREEN_H = 960, 540
FPS = 60
WEB_PORT = 5000

# ── Personagens ──
SPRITE_HEIGHT = 64          # altura do sprite no mundo (px)
PLAYER_RADIUS = 15

# ── Combate ──
ABILITY_COOLDOWN = 10 * FPS
MELEE_BONUS_RANGE = 80      # tiros disparados de perto causam mais dano
MAX_BULLET_DAMAGE = 30
EXPLOSION_RADIUS = 60
DASH_FRAMES = 12
DASH_COOLDOWN = 45
DASH_SPEED_MULT = 5
DOUBLE_TAP_MS = 300
DEATH_ANIM_FRAMES = 90

# ── Rounds do duelo ──
ROUNDS_TO_WIN = 2           # melhor de 3
MAX_ROUNDS = 5              # empates de round não contam; para depois disso
ROUND_SECONDS = 60
ROUND_INTRO_FRAMES = 90     # "ROUND 1" ... "LUTEM!"
ROUND_END_FRAMES = 130      # K.O. / TEMPO
STUN_FRAMES = 50
SLOW_MULT = 0.5             # lento (Nevasca da Geada): metade da velocidade

# ── Itens na arena ──
PICKUP_FIRST = 8 * FPS
PICKUP_EVERY = (10 * FPS, 15 * FPS)
PICKUP_LIFETIME = 12 * FPS
PICKUP_MAX = 2
HEAL_AMOUNT = 40
AMMO_PICKUP_EXTRA = 2       # item de munição: pente cheio + um pente extra
FURY_FRAMES = 6 * FPS
FURY_MULT = 1.5

# ── Futebol ──
WIN_SCORE = 3
GOAL_FREEZE = 120
BALL_RADIUS = 12
BALL_FRICTION = 0.989       # rolando: a bola perde 1,1% da velocidade por quadro (no ar, 0,4%)
BALL_MAX_SPEED = 13.5
BALL_AIR_MAX_SPEED = 15     # no ar ela pode ir mais rápido (lançamento longo)
KICK_POWER = 10.5           # chute rasteiro (rola uns 900 px; no campo antigo eram uns 640)
LOFT_KICK_POWER = (9.0, 15.0)   # chute alto: força com pouca carga e com a carga cheia (cai a ~750 px)
PASS_POWER = 6.2
LOB_SPACE = (380, 900)      # passe alto para o espaço: distância com pouca carga e com a carga cheia
LOB_MAX_FRAMES = 72         # passe alto para o espaço fica no máximo isso no ar (~1,2 s)
LOB_MATE_MAX_FRAMES = 96    # lançamento para o companheiro do outro lado do campo pode subir mais
PASS_HOMING_FORCE = 0.15
PASS_HOMING_FRAMES = 45
# bola no alto
GRAVITY = 0.32
BOUNCE = 0.55               # quanto da velocidade vertical sobra depois do quique
BOUNCE_ROLL = 0.78          # e quanto da velocidade para a frente (a grama segura a bola)
BODY_HEIGHT = 26            # bola acima disso passa por cima dos jogadores
HEAD_RANGE = (22, 62)       # altura em que dá para cabecear
CROSSBAR = 50               # acima disso, passa por cima do gol
LOFT_FRAMES = 12            # segurar CHUTE/PASSE por isso = bola alta
MAX_CHARGE = 36
# posse de bola
TRAP_SPEED = 7.5            # bola mais lenta que isso (em relação ao jogador) pode ser dominada
CARRY_GAIN = 0.3            # quão rápido a bola volta para a frente do pé (condução normal)
CLOSE_GAIN = 0.55           # conduzindo colado (botão CONDUZIR)
CARRY_TURN = 0.16           # quão rápido a bola acompanha a mudança de direção
CLOSE_TURN = 0.32
LOSE_DISTANCE = 26          # bola mais longe que isso do pé = perdeu a posse
STEAL_FRAMES = 14           # adversário mais perto da bola por esse tempo rouba
NO_TRAP_FRAMES = 12         # depois de chutar, não domina de novo na hora
# correr e marcar
SPRINT_MULT = 1.4           # CORRER: velocidade extra
SPRINT_SECONDS = 3.5        # fôlego cheio dura isso correndo
SPRINT_RECOVER_SECONDS = 5  # e enche de novo em tanto tempo sem correr
SPRINT_RESUME = 0.3         # fôlego acabou: só volta a correr com isso de fôlego
SPRINT_CARRY_AHEAD = 10     # correndo com a bola, ela vai mais solta à frente
SPRINT_STEAL_FRAMES = 8     # e é mais fácil de roubar
MARK_SPEED = 0.9            # MARCAR anda um pouco mais devagar que o normal
GOALKEEPER_ZONE = 430       # bola mais perto que isso do meu gol: MARCAR vira posição de goleiro
# cruzamento (2x2)
WING_OFFSET = 240           # tão longe assim do meio do campo (no sentido da lateral) = está na ponta
CROSS_HEIGHT = 38           # altura em que o cruzamento alto chega no companheiro (cabeçada)
CROSS_LOW_POWER = 8.0       # cruzamento rasteiro
# defesa
BLOCK_SPEED = 6.5           # bola mais rápida que isso batendo no corpo = bloqueio (espirra para o lado)
BLOCK_DAMP = 0.4            # quanto da velocidade sobra depois do bloqueio
BLOCK_REACH = 12            # alcance extra do corpo durante o carrinho de bloqueio
BLOCK_FRAMES = 16           # duração do carrinho de bloqueio
BLOCK_MISS_STUN = 28        # errou o carrinho: fica no chão esse tempo
CLEAR_REACH = 30            # alcance extra do chutão (o chute normal usa 15)
CLEAR_POWER = 13.5
CLEAR_LIFT = 9.0
CLEAR_WINDOW = 10           # apertou CHUTE um pouco antes da bola chegar: ainda vale
SUPER_SHOT_POWER = 16
# craques do futebol
THUNDER_SPEED = 16          # chute trovão (Trovão)
FINISHER_CONE = 45          # Matador na área: chute até tanto fora do gol é corrigido para o gol
FINISHER_POWER = 1.15
NOSE_RANGE = 280            # faro de gol: puxa a bola solta até essa distância
NOSE_PULL = 0.45
SUPER_HOMING_FORCE = 0.35
SUPER_HOMING_FRAMES = 120
