import random
import sys
from pathlib import Path

from otree.api import Bot, Submission
from otree.database import db

from . import (
    Choose, Comprehension, Consent, Final, GameIntro, GameSummary, Instructions,
    Results, config, in_play, total_rounds,
)

# Bots choose with the Fictitious Play agents from role-games-model, so a bot session plays
# out like the simulation. If that folder isn't next to this project, they choose at random.
MODEL_DIR = Path(__file__).resolve().parents[2] / 'role-games-model'
sys.path.insert(0, str(MODEL_DIR))
try:
    from role_games.conditions import Condition
    from role_games.models import FictitiousPlay
except ImportError:
    FictitiousPlay = None

TAU, DISCOUNT = 0.05, 0.90
_agents = {}   # participant code -> ((game, table, seat), agent)


def fp_choice(player):
    if FictitiousPlay is None:
        return random.choice(['stag', 'hare'])
    condition = {
        'anonymous': Condition.ANONYMOUS,
        'identity': Condition.IDENTITY,
        'tag_based': Condition.TAG_BASED,
    }[player.condition]
    key = (player.game, player.table, player.seat)
    stored = _agents.get(player.participant.code)
    if stored is None or stored[0] != key or player.joined_table:
        # a new seat (new game, swap, or coming off the bench) starts from a fresh prior,
        # like a replaced agent in the model. Seats are the agent ids.
        teammates = [dict(agent_id=p.seat, tag=p.tag or None)
                     for p in player.group.get_players() if p.id != player.id]
        agent = FictitiousPlay(condition, player.tag or None, TAU, len(teammates) + 1,
                               teammates, discount=DISCOUNT)
        _agents[player.participant.code] = (key, agent)
    else:
        agent = stored[1]
        prev = player.in_round(player.round_number - 1)
        agent.update(dict(
            teammates=[dict(agent_id=p.seat, tag=p.tag or None, action=p.choice)
                       for p in prev.group.get_players() if p.id != prev.id],
            own_action=prev.choice,
            own_tag=prev.tag or None,
        ))
    return agent.decide()


class PlayerBot(Bot):
    # 'timeouts' lets about a quarter of choices run out of time, to test that path
    cases = ['fp', 'timeouts']

    def play_round(self):
        if self.round_number == 1:
            yield Consent, dict(consent=True)
            yield Comprehension, dict(comp_stag=1, comp_payoff=1, comp_groups=1)
            yield Instructions
        # Each bot has its own database session that caches rows it has already read.
        # Clear it so we see what other players did while this bot waited.
        db.expire_all()
        player = self.player
        if not in_play(player):
            return
        if player.round_in_game == 1:
            yield GameIntro
        if not player.on_bench:
            choice = fp_choice(player)
            if self.case == 'timeouts' and random.random() < 0.25:
                yield Submission(Choose, timeout_happened=True)
            else:
                yield Choose, dict(choice=choice)
            yield Results
        if player.round_in_game == config(player.session)['rounds_per_game']:
            yield GameSummary
        if player.round_number == total_rounds(player.session):
            yield Final
