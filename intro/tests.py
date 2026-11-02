from otree.api import Bot

from . import Comprehension, Consent, Instructions


class PlayerBot(Bot):
    def play_round(self):
        yield Consent, dict(consent=True)
        yield Comprehension, dict(comp_stag=1, comp_payoff=1, comp_groups=2)
        yield Instructions
