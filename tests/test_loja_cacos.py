"""Loja de CACOS na Casa da turma: a moeda, o ganho ao zerar a campanha, os cupons (só o hash no
código), as skins (folhas, vestir/tirar, efeito) e o balcão no quintal com o menu da TV e do celular."""
import json
import unittest
from pathlib import Path

from apoio import FakeInput, game

from soulstrike import cacos, config, progress
from soulstrike.campaign import CampaignRun
from soulstrike.casa import SHOP_AT, HubMatch
from soulstrike.data import CHARACTERS
from soulstrike.loja import ShopMenu, state_of
from soulstrike.session import Session, SlotSetup
from soulstrike.skins import SKINS

KEYS = [c.key for c in CHARACTERS]
ROOT = Path(__file__).resolve().parent.parent


class _Input(FakeInput):
    def set_layout(self, name):
        pass


def casa(chars=("guerreiro", "atirador")):
    g = game()
    g.session = Session("campaign", [SlotSetup(i + 1, char=KEYS.index(c)) for i, c in enumerate(chars)])
    run = CampaignRun(g.session)
    match = HubMatch(g, run, story=False)
    inputs = {}
    for f in match.players:
        inputs[f.slot] = match.controllers[f] = _Input()
    return match, inputs


def passo(match, inputs, frames=1):
    for _ in range(frames):
        match.update()
        for inp in inputs.values():
            inp.end_frame()


class MoedaTest(unittest.TestCase):
    def setUp(self):
        progress.save({})

    def test_pote_comeca_vazio_e_nao_fica_negativo(self):
        self.assertEqual(cacos.balance(), 0)
        self.assertFalse(cacos.spend(1))
        cacos.add(50)
        self.assertTrue(cacos.spend(30))
        self.assertEqual(cacos.balance(), 20)

    def test_campanha_paga_pouco_e_o_dobro_na_primeira_vez(self):
        self.assertEqual(cacos.pay_campaign("normal"), 20)
        self.assertEqual(cacos.pay_campaign("normal"), 10)
        self.assertEqual(cacos.pay_campaign("facil"), 10)
        self.assertEqual(cacos.pay_campaign("borba"), 60)
        self.assertEqual(cacos.balance(), 100)
        self.assertEqual(cacos.REWARD, {"facil": 5, "normal": 10, "dificil": 15, "ibrahim": 20, "borba": 30})


class CupomTest(unittest.TestCase):
    def setUp(self):
        progress.save({})

    def test_codigos_nao_ficam_escritos_no_jogo(self):
        text = (ROOT / "soulstrike" / "cacos.py").read_text(encoding="utf-8").upper()
        for code in ("ALBEGUINIO", "CAUANZERA", "ARYEL", "BORBAJR"):
            self.assertNotIn(f'"{code}"', text)

    def test_os_quatro_cupons_dao_mil_cacos_e_a_skin_rara(self):
        for code, skin in (("Albeguinio", "albeguinio_hacker"), ("cauanzera", "cauanzera_cristal"),
                           ("ARYEL", "aryel_fogo"), ("Borba Jr", "borba_ouro")):
            status, amount, got = cacos.redeem(code)
            self.assertEqual((status, amount, got), ("ok", 1000, skin))
            self.assertIn(skin, cacos.owned())
        self.assertEqual(cacos.balance(), 4000)

    def test_cupom_vale_uma_vez_por_save(self):
        self.assertEqual(cacos.redeem("BORBAJR")[0], "ok")
        self.assertEqual(cacos.redeem("borba jr")[0], "usado")
        self.assertEqual(cacos.balance(), 1000)

    def test_cupom_errado(self):
        self.assertEqual(cacos.redeem("SENHAERRADA"), ("invalido", 0, None))
        self.assertEqual(cacos.redeem("  "), ("invalido", 0, None))
        self.assertEqual(cacos.balance(), 0)

    def test_normaliza_acento_espaco_e_pontuacao(self):
        self.assertEqual(cacos.normalize("Borba Jr."), "BORBAJR")
        self.assertEqual(cacos.normalize("Cauã-nzéra"), "CAUANZERA")


class SkinFolhaTest(unittest.TestCase):
    def test_cada_skin_tem_folha_retrato_e_as_poses_do_heroi(self):
        folder = config.CHAR_DIR / "skins"
        for key, skin in SKINS.items():
            for suffix in (".png", ".json", "_retrato.png"):
                self.assertTrue((folder / f"{key}{suffix}").is_file(), key + suffix)
            mine = json.loads((folder / f"{key}.json").read_text(encoding="utf-8"))
            base = json.loads((config.CHAR_DIR / f"{skin.hero}.json").read_text(encoding="utf-8"))
            self.assertEqual(mine["poses"], base["poses"], key)
            self.assertEqual(set(mine["hand"]), set(base["hand"]), key)
            self.assertIsNotNone(game().assets.skin_sprites(key), key)

    def test_skins_de_loja_e_raras(self):
        raras = [s for s in SKINS.values() if s.rarity == "rara"]
        self.assertEqual({s.hero for s in raras}, {"albeguinio", "cauanzera", "aryel", "borba"})
        self.assertTrue(all(s.price == 0 for s in raras))
        loja = [s for s in SKINS.values() if s.rarity == "loja"]
        self.assertEqual({s.hero for s in loja}, {"fantasma", "atirador", "tanque", "tita"})
        self.assertTrue(all(s.price == 300 for s in loja))


class LojaTest(unittest.TestCase):
    def setUp(self):
        progress.save({})

    def test_balcao_no_quintal_abre_com_atacar(self):
        match, inputs = casa()
        f = match.players[0]
        f.x, f.y = SHOP_AT[0], SHOP_AT[1] + 40
        self.assertTrue(match.shop.near(f))
        self.assertTrue(match.arena.is_free(f.x, f.y, 10))
        inputs[f.slot].tap("attack")
        passo(match, inputs, 2)
        self.assertIsInstance(match.menus.get(f), ShopMenu)

    def test_comprar_vestir_e_tirar(self):
        match, inputs = casa(("atirador", "guerreiro"))
        f = match.players[0]
        menu = ShopMenu(match, f)
        skin = SKINS["atirador_cangaceiro"]
        menu.pick(skin.key)
        self.assertFalse(menu.buy())                      # sem cacos
        self.assertEqual(state_of(skin), "comprar")
        cacos.add(320)
        self.assertTrue(menu.buy())
        self.assertEqual(cacos.balance(), 20)
        self.assertEqual(state_of(skin), "tirar")
        self.assertEqual(f.skin, skin.key)                # já aparece vestido na casa
        self.assertIs(f.sprites, match.assets.skin_sprites(skin.key))
        self.assertTrue(menu.buy())                       # tirar
        self.assertIsNone(f.skin)
        self.assertIs(f.sprites, match.assets.sprites["atirador"])
        self.assertTrue(menu.buy())                       # vestir de novo, sem pagar
        self.assertEqual(cacos.balance(), 20)

    def test_rara_so_com_cupom(self):
        match, _ = casa()
        menu = ShopMenu(match, match.players[0])
        menu.pick("aryel_fogo")
        cacos.add(5000)
        self.assertFalse(menu.buy())
        self.assertNotIn("aryel_fogo", cacos.owned())

    def test_cupom_pelo_celular_veste_a_skin(self):
        match, _ = casa(("cauanzera", "guerreiro"))
        f = match.players[0]
        menu = ShopMenu(match, f)
        self.assertFalse(menu.pick("cupom:Cauanzera"))
        self.assertEqual(cacos.balance(), 1000)
        self.assertEqual(f.skin, "cauanzera_cristal")
        snap = menu.snapshot()
        self.assertEqual(snap["kind"], "cacos")
        self.assertEqual(snap["unit"], "CACOS")
        self.assertEqual(snap["souls"], 1000)
        self.assertEqual(snap["picked"], "cauanzera_cristal")
        item = next(i for i in snap["items"] if i["id"] == "cauanzera_cristal")
        self.assertEqual(item["info"]["img"], "/skin/cauanzera_cristal.png")

    def test_cupom_pelo_teclado_da_tv(self):
        match, inputs = casa()
        f = match.players[0]
        menu = match.menus[f] = ShopMenu(match, f)
        inp = inputs[f.slot]
        passo(match, inputs, 2)
        menu.coupon = True                                # botão INSERIR CUPOM do topo marcado
        inp.tap("attack")                                 # abre o teclado
        passo(match, inputs, 1)
        self.assertTrue(menu.typing)
        menu.code = "ARYE"
        menu.key = (0, 0)                                 # A
        rows = menu._keys()
        menu.key = next((r, c) for r, row in enumerate(rows) for c, k in enumerate(row) if k == "L")
        menu._press_key()
        self.assertEqual(menu.code, "ARYEL")
        menu.key = (len(rows) - 1, rows[-1].index("USAR"))
        menu._press_key()
        self.assertEqual(cacos.balance(), 1000)
        self.assertFalse(menu.typing)

    def test_cinco_erros_seguidos_espera(self):
        match, _ = casa()
        menu = ShopMenu(match, match.players[0])
        for _ in range(cacos.MAX_TRIES):
            menu.redeem("NADAVER")
        self.assertGreater(menu.wait, 0)
        self.assertFalse(menu.redeem("ARYEL"))            # nem o certo passa enquanto espera
        self.assertEqual(cacos.balance(), 0)
        menu.wait = 0
        self.assertTrue(menu.redeem("ARYEL"))

    def test_skin_vale_na_fase_e_nao_no_futebol(self):
        cacos.give_skin("tita_momo")
        cacos.wear("tita", "tita_momo")
        match, _ = casa(("tita", "guerreiro"))
        self.assertEqual(match.players[0].skin, "tita_momo")
        self.assertIsNone(match.players[1].skin)
        from soulstrike.matches import SoccerMatch
        g = game()
        g.session = Session("soccer1", [SlotSetup(1, char=KEYS.index("tita")), SlotSetup(2, char=0)])
        soccer = SoccerMatch(g, g.session)
        self.assertTrue(all(p.skin is None for p in soccer.fighters))

    def test_tela_inicial_com_secoes_e_cupom_no_topo(self):
        match, inputs = casa()
        f = match.players[0]
        menu = match.menus[f] = ShopMenu(match, f)
        self.assertEqual(menu.page, "home")
        self.assertEqual(menu.current(), ("secao:skins", None))
        menu.section = 1
        self.assertFalse(menu.buy())                      # pets ainda não chegaram
        self.assertEqual(menu.page, "home")
        menu.section = 0
        self.assertTrue(menu.buy())                       # entra nas skins
        self.assertEqual(menu.page, "skins")
        self.assertIsNotNone(menu.current()[1])
        menu._move_card(0, -1)                            # sobe da primeira linha: botão do cupom
        self.assertTrue(menu.coupon)
        self.assertEqual(menu.current(), ("cupom", None))
        self.assertTrue(menu.buy())
        self.assertTrue(menu.typing)
        inp = inputs[f.slot]
        passo(match, inputs, 2)                           # o menu acabou de abrir
        for _ in range(3):                                # ESQUIVA: fecha o teclado, solta o cupom, volta
            inp.tap("dodge")
            passo(match, inputs, 1)
        self.assertEqual(menu.page, "home")
        self.assertIs(match.menus.get(f), menu)
        inp.tap("dodge")
        passo(match, inputs, 1)
        self.assertIsNone(match.menus.get(f))             # na tela inicial, ESQUIVA fecha a loja

    def test_grade_anda_para_os_lados_e_rola(self):
        from soulstrike import loja
        match, _ = casa()
        menu = ShopMenu(match, match.players[0])
        menu.page = "skins"
        n = len(menu.entries())
        menu._move_card(1, 0)
        self.assertEqual(menu.index, loja.ROWS)            # uma coluna para a direita
        menu._move_card(0, 1)
        self.assertEqual(menu.index, loja.ROWS + 1)        # desce na mesma coluna
        menu._move_card(-1, 0)
        menu._move_card(-1, 0)                             # passa da primeira: volta pela última coluna
        self.assertLess(menu.index, n)
        self.assertGreaterEqual(menu.index // loja.ROWS, (n - 1) // loja.ROWS)
        screen = game().screen
        old = loja.COLS
        try:
            loja.COLS = 2                                  # poucas colunas: a grade tem que rolar
            menu.index = n - 1
            menu.draw(screen, game().ui, (480, 400))
            self.assertGreater(menu.scroll, 0)
            menu.index = 0
            menu.draw(screen, game().ui, (480, 400))
            self.assertEqual(menu.scroll, 0)
        finally:
            loja.COLS = old

    def test_desenha_com_o_menu_aberto(self):
        cacos.give_skin("borba_ouro")
        cacos.wear("borba", "borba_ouro")
        match, inputs = casa(("borba", "guerreiro"))
        f = match.players[0]
        menu = match.menus[f] = ShopMenu(match, f)
        screen = game().screen
        for section in range(2):
            menu.section = section
            match.draw(screen, game().ui)
        menu.page = "skins"
        for i in range(len(menu.entries())):
            menu.index = i
            passo(match, inputs, 1)
            match.draw(screen, game().ui)
        menu.typing = True
        match.draw(screen, game().ui)


if __name__ == "__main__":
    unittest.main()
