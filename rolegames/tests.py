import random
import sys
from pathlib import Path

from otree.api import Bot, Submission
from otree.database import db

from . import (
    Choose, Final, GameIntro, GameSummary, Results, config, in_play, total_rounds,
)

MODEL_DIR = Path(__file__).resolve().parents[2] / 'role-games-model'
sys.path.insert(0, str(MODEL_DIR))
try:
    from role_games.conditions import Condition
    from role_games.models import FictitiousPlay
except ImportError:
    FictitiousPlay = None

TAU, DISCOUNT = 0.05, 0.90
_agents = {}


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
    cases = ['fp', 'timeouts']

    def play_round(self):
        db.expire_all()
        player = self.player
        if not in_play(player):
            return
        if player.round_in_game == 1:
            yield GameIntro
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
