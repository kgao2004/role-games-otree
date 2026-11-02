from otree.api import *

doc = """
Consent, comprehension check, and instructions before the multiplayer game.
"""


class C(BaseConstants):
    NAME_IN_URL = 'intro'
    PLAYERS_PER_GROUP = None
    NUM_ROUNDS = 1

    CONDITIONS = {
        'anonymous': 'Anonymous',
        'identity': 'Identity',
        'tag_based': 'Tag-based',
    }
    CONDITION_INFO = {
        'anonymous': ('🔒', 'You see only aggregate counts — how many chose stag and hare — not who.'),
        'identity': ('🪪', "You see each individual player's choice every round, labeled by player."),
        'tag_based': ('🏷️', 'Players have colored tags (red / blue). You see choices grouped by tag, not by individual.'),
    }
    COMP_STAG_CORRECT = 1
    COMP_PAYOFF_CORRECT = 1
    COMP_GROUPS_CORRECT = 2


class Subsession(BaseSubsession):
    pass


class Group(BaseGroup):
    pass


class Player(BasePlayer):
    consent = models.BooleanField(
        label='I have read this information and I agree to take part in this study.',
        initial=False,
    )
    comp_stag = models.IntegerField(
        label='When is the +4 stag bonus added to the group score?',
        choices=[
            [1, 'When at least 2 players choose Stag'],
            [2, 'When every player chooses Stag'],
            [3, 'When at least 1 player chooses Stag'],
        ],
        widget=widgets.RadioSelect,
    )
    comp_payoff = models.IntegerField(
        label='What points do you receive each round?',
        choices=[
            [1, "The group's total score that round"],
            [2, 'Only the points from your own action'],
            [3, 'A random number of points'],
        ],
        widget=widgets.RadioSelect,
    )
    comp_groups = models.IntegerField(
        label='How are groups formed?',
        choices=[
            [1, 'You are placed in a new group at the start of every game'],
            [2, 'You stay with the same group for the whole study'],
            [3, 'Groups are reshuffled every round'],
        ],
        widget=widgets.RadioSelect,
    )


def config(session):
    c = session.config
    conditions = [x.strip() for x in str(c.get('conditions', 'identity')).split(',') if x.strip()]
    return dict(
        n=int(c.get('players_per_table', 3)),
        num_games=int(c.get('num_games', 3)),
        rounds_per_game=int(c.get('rounds_per_game', 10)),
        conditions=conditions,
        replacement_rate=float(c.get('replacement_rate', 0.0)),
        choice_timeout=int(c.get('choice_timeout', 60)),
        instructions_timeout=int(c.get('instructions_timeout', 180)),
    )


def group_total(actions):
    return (4 if actions.count('stag') >= 2 else 0) + actions.count('hare')


def score_rows(n):
    rows = []
    for stags in range(n + 1):
        rows.append(dict(
            stags=stags,
            hares=n - stags,
            total=group_total(['stag'] * stags + ['hare'] * (n - stags)),
            best=stags == 2,
            worst=stags == 1,
        ))
    return rows


def condition_cards(conditions):
    seen = []
    for c in conditions:
        if c not in seen:
            seen.append(c)
    return [
        dict(icon=C.CONDITION_INFO[c][0], name=C.CONDITIONS[c], text=C.CONDITION_INFO[c][1])
        for c in seen
    ]


def count_label(k, noun):
    return f'{k} {noun}' + ('' if k == 1 else 's')


class Consent(Page):
    form_model = 'player'
    form_fields = ['consent']

    @staticmethod
    def error_message(player, values):
        if not values.get('consent'):
            return 'You must consent to take part in order to continue.'


class Comprehension(Page):
    form_model = 'player'
    form_fields = ['comp_stag', 'comp_payoff', 'comp_groups']

    @staticmethod
    def error_message(player, values):
        errors = {}
        if values['comp_stag'] != C.COMP_STAG_CORRECT:
            errors['comp_stag'] = (
                'Not quite. Stag is worth +4 only if at least 2 players choose it.'
            )
        if values['comp_payoff'] != C.COMP_PAYOFF_CORRECT:
            errors['comp_payoff'] = (
                'Not quite. Each round you receive the group’s total score, not just your own action.'
            )
        if values['comp_groups'] != C.COMP_GROUPS_CORRECT:
            errors['comp_groups'] = (
                'Not quite. You stay with the same group of people for the whole study.'
            )
        return errors

    @staticmethod
    def before_next_page(player, timeout_happened):
        player.participant.consent = player.consent
        player.participant.comp_stag = player.comp_stag
        player.participant.comp_payoff = player.comp_payoff
        player.participant.comp_groups = player.comp_groups


class Instructions(Page):
    @staticmethod
    def get_timeout_seconds(player):
        return config(player.session)['instructions_timeout'] or None

    @staticmethod
    def vars_for_template(player):
        s = config(player.session)
        cards = condition_cards(s['conditions'])
        return dict(
            n=s['n'],
            games_label=count_label(s['num_games'], 'game'),
            rounds_per_game=s['rounds_per_game'],
            score_rows=score_rows(s['n']),
            conditions=cards,
            multiple_conditions=len(cards) > 1,
            has_replacement=s['replacement_rate'] > 0,
            choice_timeout=s['choice_timeout'],
            instructions_timeout=s['instructions_timeout'],
        )


page_sequence = [Consent, Comprehension, Instructions]
