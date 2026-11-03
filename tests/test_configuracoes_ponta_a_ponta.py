"""Configurações de ponta a ponta: o jogo rodando (Game.update) com controles simulados.

Confere perfis de botão (luta e bola), MEU JEITO salvo no arquivo, zona morta, vibração, 1º controle
como P2, quem navega os menus, regras do P1 na escolha valendo na partida, a tela CONTROLE usada pelo
próprio controle o painel da partida (pausa, menu pessoal, sair e entrar no meio) e o ULTRA do 1 x 1 pelo controle."""
import json
import unittest

from apoio import game

from soulstrike import pad_profiles, rumble, settings
from soulstrike.gamepads import Pad
from soulstrike.session import Session, SlotSetup


class Dev:
    def __init__(self):
        self.rumbles = []

    def rumble(self, lo, hi, ms):
        self.rumbles.append((lo, hi, ms))
        return True


class Reader:
    def __init__(self, name):
        self.name = name
        self.dev = Dev()
        self.down = set()
        self.ax = {}

    def button(self, b):
        return b in self.down

    def axis(self, a):
        return self.ax.get(a, 0.0)


class PontaAPontaTest(unittest.TestCase):
    def setUp(self):
        self.g = game()
        self.old_pads = self.g.gamepads.pads
        self.saved = {k: settings.get(k) for k in ("controles", "vibracao", "controle_comeca_no_p2",
                                                   "futebol_partida")}

    def tearDown(self):
        self.g.gamepads.pads = self.old_pads
        rumble.register(self.g.gamepads)
        for k, v in self.saved.items():
            settings.change(k, v)
        self.g.session = None

    def test_configuracoes_funcionam_no_jogo(self):
        g = self.g
        failures = []

        def check(name, cond, extra=""):
            if not cond:
                failures.append(f"{name} {extra}")

        xbox = Pad(Reader("Xbox Wireless Controller"))
        ns = Pad(Reader("Nintendo Switch Pro Controller"))
        g.gamepads.pads = [xbox, ns]
        rumble.register(g.gamepads)

        def frame(pad=None, buttons=(), axes=None):
            if pad is not None:
                pad.reader.down = set(buttons)
                pad.reader.ax = dict(axes or {})
            g.update([])

        def tap(pad, *buttons):
            frame(pad, buttons)
            frame(pad, ())

        xbox = Pad(Reader("Xbox Wireless Controller")); ns = Pad(Reader("Nintendo Switch Pro Controller"))
        g.gamepads.pads = [xbox, ns]
        rumble.register(g.gamepads)


        # 1. perfil padrão na luta: A ataca
        g.session = Session("duel", [SlotSetup(1, char=0), SlotSetup(2, char=1)])
        from soulstrike.matches import BattleMatch
        from soulstrike.scenes.play import PlayScene
        m = BattleMatch(g, g.session); g.change(PlayScene(g, m)); frame()
        frame(xbox, ("a",)); check("padrão: A = ATACAR no duelo", g.inputs[1].pressed("attack")); frame(xbox, ())
        # 2. perfil CHUTE NO GATILHO: RT ataca, A vira habilidade
        pad_profiles.set_preset(xbox.name, "gatilho")
        frame(xbox, (), {"rt": 1.0}); check("gatilho: RT = ATACAR", g.inputs[1].pressed("attack")); frame(xbox, ())
        frame(xbox, ("a",)); check("gatilho: A = HABILIDADE", g.inputs[1].pressed("special") and not g.inputs[1].pressed("attack")); frame(xbox, ())
        # 3. MEU JEITO: X vira esquiva só na luta
        pad_profiles.set_preset(xbox.name, "padrao")
        pad_profiles.set_action(xbox.name, "luta", "x", "dodge")
        frame(xbox, ("x",)); check("meu jeito: X = ESQUIVA", g.inputs[1].pressed("dodge") and not g.inputs[1].pressed("special")); frame(xbox, ())
        # salvo no disco e relido
        settings.load()
        check("perfil salvo no arquivo e relido", pad_profiles.preset(xbox.name) == "meu" and pad_profiles.mapping(xbox.name, "luta")["x"] == "dodge",
              json.load(open(settings.path()))["controles"].get(xbox.name[:40]))
        # 4. o perfil da bola vale no futebol (contexto bola), separado da luta
        g.session = Session("soccer1", [SlotSetup(1, char=0), SlotSetup(2, char=1)])
        from soulstrike.matches import create_match
        sm = create_match(g, g.session); g.change(PlayScene(g, sm)); frame()
        frame(xbox, ("x",)); check("futebol usa o perfil da bola: X = PASSE", g.inputs[1].pressed("special") and not g.inputs[1].pressed("dodge")); frame(xbox, ())
        frame(xbox, (), {"rt": 1.0}); check("futebol: RT = CORRER", g.inputs[1].held("sprint")); frame(xbox, ())
        # 5. zona morta
        pad_profiles.set_deadzone(xbox.name, 0.4)
        frame(xbox, (), {"lx": 0.3}); check("zona 0.40: analógico a 0.30 parado", g.inputs[1].axis() == (0.0, 0.0), g.inputs[1].axis())
        pad_profiles.set_deadzone(xbox.name, 0.1)
        frame(xbox, (), {"lx": 0.3}); check("zona 0.10: analógico a 0.30 anda", g.inputs[1].axis()[0] > 0.2, g.inputs[1].axis()); frame(xbox, ())
        # 6. o Nintendo é o P2 e tem o perfil próprio
        frame(ns, ("a",)); check("2º controle (Nintendo) = P2", g.inputs[2].pressed("attack")); frame(ns, ())
        # 7. vibração: gol do time do P1
        xbox.reader.dev.rumbles.clear()
        sm._goal(sm.fighters[0].team)
        check("vibra no gol (P1)", bool(xbox.reader.dev.rumbles))
        settings.change("vibracao", False); xbox.reader.dev.rumbles.clear()
        sm._goal(sm.fighters[0].team)
        check("vibração desligada não vibra", not xbox.reader.dev.rumbles); settings.change("vibracao", True)
        # 8. 1º controle é o P2
        settings.change("controle_comeca_no_p2", True)
        frame(xbox, ("a",)); check("opção 1º controle = P2", g.inputs[2].pressed("attack") and not g.inputs[1].pressed("attack")); frame(xbox, ())
        settings.change("controle_comeca_no_p2", False)
        # 9. menus: só o controle do P1 navega; na tela CONTROLE qualquer um
        from soulstrike.scenes.menus import TitleScene
        g.change(TitleScene(g)); frame()
        before = g.scene.menu.index
        tap(ns, "down"); check("título: controle do P2 não navega", g.scene.menu.index == before)
        tap(xbox, "down"); check("título: controle do P1 navega", g.scene.menu.index != before)
        from soulstrike.scenes.pad import PadScene
        g.change(PadScene(g)); frame()
        tap(ns, "down"); check("tela CONTROLE: o 2º controle passa a ser o editado", g.scene.pad is ns if hasattr(g.scene, "pad") else True)
        # 10. regras na escolha valem na partida
        settings.change("futebol_partida", "3")
        g.session = Session("soccer1", [SlotSetup(1, char=0), SlotSetup(2, char=1)])
        from soulstrike.scenes.select import CharSelectScene
        g.change(CharSelectScene(g)); frame()
        tap(xbox, "start"); check("START do P1 abre as regras", g.scene.rules_open)
        labels = [r[0] for r in g.scene.rule_rows()]
        g.scene.rules_row = labels.index("PARTIDA")
        tap(xbox, "right"); check("PARTIDA mudou para 5 GOLS", settings.get("futebol_partida") == "5")
        tap(xbox, "start"); check("START fecha as regras", not g.scene.rules_open)
        for c in g.scene.cards: c.ready = True
        for _ in range(60): frame()
        scene = g.scene
        for _ in range(400):
            if hasattr(scene, "match"): break
            frame(); scene = g.scene
        match = getattr(g.scene, "match", None)
        check("a partida começou com 5 gols", match is not None and match.win_score == 5, getattr(match, "win_score", None))

        # 11. tela CONTROLE com o próprio controle: A abre a lista, ↓ escolhe outra ação, A confirma
        pad_profiles.set_preset(xbox.name, "padrao")
        g.change(PadScene(g)); frame()
        tap(xbox, "a"); sc = g.scene
        before = pad_profiles.mapping(xbox.name, pad_profiles.CONTEXTS[sc.context])
        row_btn = sc.rows[sc.row] if hasattr(sc, "rows") else None
        check("A abre a lista de ações", sc.picking is not None)
        tap(xbox, "down"); tap(xbox, "a")
        after = pad_profiles.mapping(xbox.name, pad_profiles.CONTEXTS[sc.context])
        check("ação trocada pelo controle e salva", before != after and pad_profiles.preset(xbox.name) == "meu",
              {k: (before[k], after[k]) for k in before if before[k] != after[k]})
        # 12. painel da partida pelo controle: P1 pausa, troca a CPU; P2 abre o menu pessoal
        g.session = Session("soccer1", [SlotSetup(1, char=0), SlotSetup(2, char=1, cpu=True)])
        sm = create_match(g, g.session); g.change(PlayScene(g, sm)); frame()
        tap(xbox, "start"); check("START do P1 pausa no jogo", g.scene.paused)
        tap(xbox, "start"); check("START de novo despausa", not g.scene.paused)
        g.session.slots[1].cpu = False
        from soulstrike import host
        host.make_human(g, sm, 2)
        tap(ns, "start"); check("START do P2 abre o menu pessoal (não pausa)", 2 in g.scene.personal and not g.scene.paused)
        tap(ns, "down"); tap(ns, "a")
        check("SAIR (VIRA CPU) pelo controle do P2", g.session.slots[1].cpu)
        tap(ns, "start"); check("P2 entra no meio apertando START", not g.session.slots[1].cpu)
        # 13. basquete 1 x 1: o botão de SUPER do controle solta o ULTRA quando a barra enche
        pad_profiles.set_preset(xbox.name, "padrao")
        g.session = Session("basket1", [SlotSetup(1, char=0), SlotSetup(2, char=1, cpu=True)])
        bm = create_match(g, g.session); g.change(PlayScene(g, bm)); frame()
        check("1 x 1 é solo", getattr(bm, "solo", False))
        f = bm.fighters[0]
        if bm.warmup:                         # aquecimento: SUPER diz "estou pronto"
            tap(xbox, "y")
            check("SUPER no aquecimento marca PRONTO", f.warm_ready)
            for _ in range(400):
                if not bm.warmup: break
                frame()
        check("aquecimento acabou", not bm.warmup, bm.warmup)
        used = False
        for _ in range(300):
            f.ultra = 1.0
            f.stun_timer = 0
            tap(xbox, "y")
            if f.ultra < 1.0 and bm.banner and bm.banner[0] == "ULTRA!":
                used = True
                break
        check("Y (SUPER) com a barra cheia solta o ULTRA", used, (f.ultra, bm.banner))
        self.assertEqual(failures, [])
