"""ARENA SEM FIM, o portão do porão da Casa (abre ao zerar a campanha).

Uma sala de luta da campanha em que as ondas nunca acabam: cada uma traz os inimigos de um lugar
da campanha (floresta, Lag Lobby, clínica, mansão, em volta) e fica maior a cada volta; a cada 5
ondas vem um elite a mais. Sem continue: quando todo mundo cai, acabou. A onda em que a turma
chegou vai para o placar do portão (RECORDE). Só placar: o que a turma ganha lá dentro (almas,
armas, vida) volta como estava ao sair.
"""
from . import progress, theme
from .campaign import INTRO_FRAMES, MIDDLE, CampaignMatch, Dungeon, _MID
from .matches import Result

RECORD_KEY = "arena_recorde"
MAP_KEY = "sala_calabouco"
ORDER = ("floresta", "calabouco", "templo", "recepcao", "datacenter", "cobertura",
         "clinica_recepcao", "procedimentos", "suite_vip", "mansao_sede", "mansao_patio", "mansao_gabinete")
ELITES = ("golem", "miliciano_exo", "golem", "miliciano_exo")


def wave(index):
    """A onda ``index`` (0 = a primeira): ((tipo, quantidade), ...)."""
    place = MIDDLE[ORDER[index % len(ORDER)]]
    base = place.waves[index % 2]
    extra = index // len(ORDER) + index // 4                 # cresce a cada volta e a cada 4 ondas
    out = [(kind, count + (extra if i == 0 else extra // 2)) for i, (kind, count) in enumerate(base)]
    if index % 5 == 4:
        out.append((ELITES[(index // 5) % len(ELITES)], 1 + index // 15))
    return tuple(out)


def record():
    """O recorde salvo: {"onda", "quem"} ou None."""
    data = progress.load().get(RECORD_KEY)
    if isinstance(data, dict) and isinstance(data.get("onda"), int):
        return data
    return None


def save_record(reached, names):
    old = record()
    if old is not None and old["onda"] >= reached:
        return False
    data = progress.load()
    data[RECORD_KEY] = {"onda": int(reached), "quem": list(names)}
    progress.save(data)
    return True


class ArenaSemFimMatch(CampaignMatch):
    """As ondas sem fim. ``story`` e ``walk`` passam adiante para a Casa na volta."""

    endless = True
    fight_title = "PORÃO · ARENA SEM FIM"

    def __init__(self, game, run, story=False, walk=False):
        self.story = story
        self.walk = walk
        self._saved = run._state()                  # tudo volta como estava ao sair
        run.continues = 0
        self._waves = [wave(0), wave(1)]
        self.reached = 0
        self.new_record = False
        self._dungeon = Dungeon(MAP_KEY, "ARENA SEM FIM", _MID, (1.0, 0.0), (), exit_spot=(600, 120))
        super().__init__(game, run)
        self.dungeon_index = 0

    @property
    def dungeon(self):
        return self._dungeon

    @dungeon.setter
    def dungeon(self, value):
        """A CampaignMatch põe a masmorra da campanha aqui: na arena fica sempre a dela."""

    @property
    def waves(self):
        return self._waves

    @property
    def last(self):
        return False

    @property
    def music(self):
        return "arena"

    def _start_wave(self, index):
        while len(self._waves) <= index + 1:          # sempre tem a próxima: nunca é a última
            self._waves.append(wave(len(self._waves)))
        self.reached = index + 1
        super()._start_wave(index)

    def update_stage(self):
        super().update_stage()
        if self.state == "intro" and self.banner and self.banner[0].startswith("MASMORRA"):
            self._set_banner("ARENA SEM FIM", "ATÉ ONDE A TURMA AGUENTA?", (190, 120, 255))
        if self.state == "gameover" and self.state_timer == 200:
            names = [p.stats.name.upper() for p in self.players]
            self.new_record = save_record(self.reached, names)
            self._set_banner("RECORDE NOVO!" if self.new_record else "ACABOU",
                             f"A TURMA CHEGOU NA ONDA {self.reached}", (190, 120, 255))

    def _finish(self, won):
        self.won = False
        self.result = Result("ARENA SEM FIM", theme.MOSS, self.players)
        self.finished = True

    def give_back(self):
        """Devolve a campanha como estava antes de entrar."""
        for k, v in self._saved.items():
            setattr(self.run, k, v)

    def next_scene(self):
        from .scenes.campaign import porao_scene
        from .scenes.escada import StairsTripScene
        self.give_back()
        return StairsTripScene(self.game, lambda: porao_scene(self.game, self.run, self.story, walk=self.walk,
                                                              arrive="arena"),
                               "VOLTANDO PARA O PORÃO", accent=(190, 120, 255), door=True)

    def restart_scene(self):
        from .scenes.campaign import arena_scene
        self.give_back()
        return arena_scene(self.game, self.run, self.story, walk=self.walk)


__all__ = ("ArenaSemFimMatch", "record", "wave")
