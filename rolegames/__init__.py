import random

from otree.api import *

doc = """
Role Games with real people: a modified N-player stag hunt played at tables of 3–5.

Tables auto-start when players_per_table people arrive (group_by_arrival_time).
Partners stay together for the whole session. Parallel tables do not wait on each other.
"""


class C(BaseConstants):
    NAME_IN_URL = 'rolegames'
    PLAYERS_PER_GROUP = None     # Match forms groups of session players_per_table
    NUM_ROUNDS = 60              # upper limit on num_games × rounds_per_game

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
    PLAYER_COLORS = ['#4878CF', '#6ACC65', '#D65F5F', '#e5a917', '#9b59b6']
    TAG_COLORS = {'red': '#e57373', 'blue': '#64b5f6'}
    ANON_COLOR = '#9E9E9E'
    ACTION_EMOJI = {'stag': '🦌', 'hare': '🐇'}

    INTRO_TIMEOUT = 90
    SUMMARY_TIMEOUT = 60


class Subsession(BaseSubsession):
    pass


class Group(BaseGroup):
    table = models.IntegerField(initial=0)
    condition = models.StringField(initial='')
    stag_count = models.IntegerField()
    group_total = models.IntegerField()
    replaced_seat = models.IntegerField(initial=0)
    replaced_tag = models.StringField(initial='')
    replacement_source = models.StringField(initial='')


class Player(BasePlayer):
    game = models.IntegerField()
    round_in_game = models.IntegerField()
    condition = models.StringField()
    on_bench = models.BooleanField(initial=False)
    table = models.IntegerField(initial=0)
    seat = models.IntegerField(initial=0)
    tag = models.StringField(initial='')
    joined_table = models.BooleanField(initial=False)
    left_table = models.BooleanField(initial=False)
    choice = models.StringField(choices=['stag', 'hare'])
    timed_out = models.BooleanField(initial=False)


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
        results_timeout=int(c.get('results_timeout', 30)),
        instructions_timeout=int(c.get('instructions_timeout', 180)),
    )


def total_rounds(session):
    s = config(session)
    return s['num_games'] * s['rounds_per_game']


def in_play(player):
    return player.round_number <= total_rounds(player.session)


def game_and_round(round_number, rounds_per_game):
    return (round_number - 1) // rounds_per_game + 1, (round_number - 1) % rounds_per_game + 1


def condition_for_game(s, game):
    return s['conditions'][(game - 1) % len(s['conditions'])]


def group_total(actions):
    return (4 if actions.count('stag') >= 2 else 0) + actions.count('hare')


def tags_for_table(n):
    n_red = 1 if n == 3 else 2
    tags = ['red'] * n_red + ['blue'] * (n - n_red)
    random.shuffle(tags)
    return tags


def creating_session(subsession):
    if subsession.round_number != 1:
        return
    s = config(subsession.session)
    num = len(subsession.get_players())
    problems = []
    if not 3 <= s['n'] <= 5:
        problems.append('players_per_table must be 3, 4, or 5.')
    elif num < s['n']:
        problems.append(f"You need at least {s['n']} participants for tables of {s['n']}.")
    if s['num_games'] < 1 or s['rounds_per_game'] < 1:
        problems.append('num_games and rounds_per_game must be at least 1.')
    if s['num_games'] * s['rounds_per_game'] > C.NUM_ROUNDS:
        problems.append(f'num_games × rounds_per_game can be at most {C.NUM_ROUNDS}.')
    unknown = [x for x in s['conditions'] if x not in C.CONDITIONS]
    if not s['conditions'] or unknown:
        problems.append('conditions must be a comma-separated list of: anonymous, identity, tag_based.')
    if not 0 <= s['replacement_rate'] <= 1:
        problems.append('replacement_rate must be between 0 and 1.')
    if problems:
        raise ValueError(' '.join(problems))
    for p in subsession.get_players():
        p.participant.rounds_benched = 0
        p.participant.bench_since = 0


def group_by_arrival_time_method(subsession, waiting_players):
    """Form a table as soon as players_per_table people are waiting."""
    n = config(subsession.session)['n']
    if len(waiting_players) >= n:
        return waiting_players[:n]


def prepare_group(group):
    """Assign seats/tags within a fixed GBAT group for the current round."""
    s = config(group.session)
    players = group.get_players()
    rnd = players[0].round_number
    game, round_in_game = game_and_round(rnd, s['rounds_per_game'])
    condition = condition_for_game(s, game)
    table_id = group.id_in_subsession

    if round_in_game == 1:
        order = list(players)
        random.shuffle(order)
        tags = tags_for_table(len(order)) if condition == 'tag_based' else [''] * len(order)
        for seat, p in enumerate(order, start=1):
            p.game, p.round_in_game, p.condition = game, round_in_game, condition
            p.table, p.seat, p.tag = table_id, seat, tags[seat - 1]
            p.on_bench = False
            p.joined_table = False
            p.left_table = False
    else:
        for p in players:
            prev = p.in_round(rnd - 1)
            p.game, p.round_in_game, p.condition = game, round_in_game, condition
            p.table, p.seat, p.tag = prev.table, prev.seat, prev.tag
            p.on_bench = False
            p.joined_table = False
            p.left_table = False

    group.table = table_id
    group.condition = condition
    group.replaced_seat = 0
    group.replaced_tag = ''
    group.replacement_source = ''


# ─── What each player sees ───────────────────────────────────────────────────

def table_members(player):
    return sorted(player.group.get_players(), key=lambda p: p.seat)


def table_total(player, *, include_current):
    start = player.round_number - player.round_in_game + 1
    end = player.round_number if include_current else player.round_number - 1
    if end < start:
        return 0
    total = 0
    for sub in player.subsession.in_rounds(start, end):
        for g in sub.get_groups():
            if g.table == player.table:
                total += g.field_maybe_none('group_total') or 0
    return total


def label(p, viewer):
    if p.id == viewer.id:
        return 'You'
    if viewer.condition == 'identity':
        return f'Player {p.seat}'
    return 'Other Player'


def color(p, condition):
    if condition == 'tag_based':
        return C.TAG_COLORS.get(p.tag, '#aaa')
    if condition == 'anonymous':
        return C.ANON_COLOR
    return C.PLAYER_COLORS[(p.seat - 1) % len(C.PLAYER_COLORS)]


def circle_html(p, viewer, *, small=False):
    classes = 'rg-circle' + (' rg-circle-sm' if small else '') + (' rg-me' if p.id == viewer.id else '')
    return f'<div class="{classes}" style="--c:{color(p, viewer.condition)}"></div>'


def label_html(p, viewer):
    me = ' rg-label-me' if p.id == viewer.id else ''
    return f'<div class="rg-label{me}">{label(p, viewer)}</div>'


def person_card(p, viewer, action=None):
    me = ' rg-card-me' if p.id == viewer.id else ''
    action_html = f'<div class="rg-action">{C.ACTION_EMOJI[action]}</div>' if action else ''
    return f'<div class="rg-card{me}">{circle_html(p, viewer)}{label_html(p, viewer)}{action_html}</div>'


def group_card(title, members, viewer, *, reveal):
    circles = ''.join(
        f'<div class="rg-mini">{circle_html(p, viewer, small=True)}{label_html(p, viewer)}</div>'
        for p in members
    )
    actions = ''
    if reveal:
        choices = [p.field_maybe_none('choice') for p in members]
        emojis = C.ACTION_EMOJI['stag'] * choices.count('stag') + C.ACTION_EMOJI['hare'] * choices.count('hare')
        actions = (
            f'<div class="rg-emojis">{emojis}</div>'
            '<div class="rg-note">order does not correspond to players</div>'
        )
    return (
        f'<div class="rg-card rg-group-card" style="flex-grow:{max(len(members), 1)}">'
        f'<div class="rg-group-title">{title}</div>'
        f'<div class="rg-mini-row">{circles}</div>{actions}</div>'
    )


def players_html(viewer, *, reveal=False):
    me_first = sorted(table_members(viewer), key=lambda p: (p.id != viewer.id, p.seat))
    if viewer.condition == 'identity':
        cards = ''.join(
            person_card(p, viewer, p.field_maybe_none('choice') if reveal else None) for p in me_first
        )
    elif viewer.condition == 'anonymous':
        cards = group_card('Players', me_first, viewer, reveal=reveal)
    else:
        cards = ''
        for tag in ('red', 'blue'):
            members = [p for p in me_first if p.tag == tag]
            title = f'{tag.title()} Player' + ('' if len(members) == 1 else 's')
            cards += group_card(title, members, viewer, reveal=reveal)
    return f'<div class="rg-players">{cards}</div>'


def header_html(player, total):
    s = config(player.session)
    return (
        '<div class="rg-header">'
        f'<div><b>Round {player.round_in_game} / {s["rounds_per_game"]}</b>'
        f' &nbsp;·&nbsp; {C.CONDITIONS[player.condition]}'
        f' &nbsp;·&nbsp; <span class="rg-muted">Game {player.game} of {s["num_games"]}</span></div>'
        f'<div><b>{total} pts</b> group total</div>'
        '</div>'
    )


def replacement_message(player):
    g = player.group
    if not g.replaced_seat:
        return ''
    if player.joined_table:
        if g.replacement_source == 'other_table':
            return 'You have moved to a different group that is already playing.'
        return 'You have joined a group that is already playing.'
    if player.condition == 'anonymous':
        return 'One of the players has been replaced!'
    if player.condition == 'identity':
        return f'Player {g.replaced_seat} has been replaced!'
    return f'One of the {g.replaced_tag.title()} players has been replaced!'


def count_label(k, noun):
    return f'{k} {noun}' + ('' if k == 1 else 's')


def group_intro(player, members):
    if player.game == 1:
        start = f"You're in a group of {len(members)}."
    else:
        start = f"Same group of {len(members)}. Game {player.game} is starting."
    if player.condition == 'tag_based':
        n_red = sum(p.tag == 'red' for p in members)
        chip = (f'<span class="rg-tag-chip" style="background:{C.TAG_COLORS[player.tag]}">'
                f'{player.tag.title()}</span>')
        return (f'{start} Your tag is {chip}. The group has {count_label(n_red, "red player")} '
                f'and {count_label(len(members) - n_red, "blue player")}.')
    if player.condition == 'identity':
        return f'{start} Each player keeps the same label and color for this whole game.'
    return f'{start} Everyone looks the same here. Your circle is the one with the ring.'


# ─── Pages ───────────────────────────────────────────────────────────────────

class Match(WaitPage):
    """First page: form tables of players_per_table as people arrive."""
    group_by_arrival_time = True
    title_text = 'Waiting for your group'
    body_text = (
        'Waiting for enough people to start. Keep this tab open and active — '
        'if the page thinks you left, click to rejoin.'
    )

    @staticmethod
    def is_displayed(player):
        return player.round_number == 1

    @staticmethod
    def after_all_players_arrive(group):
        prepare_group(group)


class Prepare(WaitPage):
    """Later rounds: keep the same group; refresh seats at the start of each game."""
    title_text = 'Please wait'
    body_text = 'Waiting for the others in your group.'

    @staticmethod
    def is_displayed(player):
        return in_play(player) and player.round_number > 1

    @staticmethod
    def after_all_players_arrive(group):
        prepare_group(group)


class GameIntro(Page):
    timeout_seconds = C.INTRO_TIMEOUT

    @staticmethod
    def is_displayed(player):
        return in_play(player) and player.round_in_game == 1

    @staticmethod
    def vars_for_template(player):
        s = config(player.session)
        icon, text = C.CONDITION_INFO[player.condition]
        members = table_members(player)
        return dict(
            num_games=s['num_games'],
            condition_icon=icon,
            condition_name=C.CONDITIONS[player.condition],
            condition_text=text,
            intro=group_intro(player, members),
            players=players_html(player),
        )


class Choose(Page):
    form_model = 'player'
    form_fields = ['choice']

    @staticmethod
    def is_displayed(player):
        return in_play(player)

    @staticmethod
    def get_timeout_seconds(player):
        return config(player.session)['choice_timeout'] or None

    @staticmethod
    def vars_for_template(player):
        n = len(table_members(player))
        return dict(
            header=header_html(player, table_total(player, include_current=False)),
            players=players_html(player),
            message=replacement_message(player),
            minimum=n - 1,
            maximum=n + 2,
        )

    @staticmethod
    def before_next_page(player, timeout_happened):
        if timeout_happened:
            player.choice = random.choice(['stag', 'hare'])
            player.timed_out = True


class Compute(WaitPage):
    title_text = 'Please wait'
    body_text = 'Waiting for the others in your group to choose.'

    @staticmethod
    def is_displayed(player):
        return in_play(player)

    @staticmethod
    def after_all_players_arrive(group):
        players = group.get_players()
        actions = [p.choice for p in players]
        group.stag_count = actions.count('stag')
        group.group_total = group_total(actions)
        for p in players:
            p.payoff = group.group_total


class Results(Page):
    @staticmethod
    def is_displayed(player):
        return in_play(player)

    @staticmethod
    def get_timeout_seconds(player):
        return config(player.session)['results_timeout'] or None

    @staticmethod
    def vars_for_template(player):
        s = config(player.session)
        total = table_total(player, include_current=True)
        last = player.round_in_game == s['rounds_per_game']
        return dict(
            header=header_html(player, total),
            players=players_html(player, reveal=True),
            round_score=player.group.group_total,
            total=total,
            next_label='Finish game' if last else 'Next round',
        )


class GameSummary(Page):
    timeout_seconds = C.SUMMARY_TIMEOUT

    @staticmethod
    def is_displayed(player):
        return in_play(player) and player.round_in_game == config(player.session)['rounds_per_game']

    @staticmethod
    def vars_for_template(player):
        s = config(player.session)
        n, r = s['n'], s['rounds_per_game']
        return dict(
            is_last_game=player.game == s['num_games'],
            next_game=player.game + 1,
            total=table_total(player, include_current=True),
            best=(n + 2) * r,
            worst=(n - 1) * r,
        )


class Final(Page):
    @staticmethod
    def is_displayed(player):
        shown = player.round_number == total_rounds(player.session)
        if shown:
            player.participant.finished = True
        return shown

    @staticmethod
    def vars_for_template(player):
        s = config(player.session)
        r = s['rounds_per_game']
        rows = []
        for game in range(1, s['num_games'] + 1):
            rounds = player.in_rounds((game - 1) * r + 1, game * r)
            rows.append(dict(
                game=game,
                condition=C.CONDITIONS[condition_for_game(s, game)],
                played=sum(not p.on_bench for p in rounds),
                points=sum(int(p.payoff) for p in rounds),
            ))
        return dict(
            rows=rows,
            total=sum(row['points'] for row in rows),
            rounds_per_game=r,
            completion_url=player.session.vars.get('prolific_completion_url') or '',
        )


page_sequence = [
    Match, Prepare, GameIntro, Choose, Compute, Results, GameSummary, Final,
]


def custom_export(players):
    yield [
        'session', 'participant', 'participant_label', 'round', 'game', 'round_in_game',
        'condition', 'players_per_table', 'replacement_rate', 'on_bench', 'table', 'seat', 'tag',
        'choice', 'timed_out', 'stag_count', 'group_total', 'joined_table', 'left_table',
        'table_replaced_seat', 'table_replacement_source',
        'consent', 'comp_stag', 'comp_payoff', 'comp_groups',
    ]
    for p in players:
        if p.field_maybe_none('game') is None:
            continue
        g = p.group
        cfg = p.session.config
        part = p.participant
        yield [
            p.session.code, part.code, part.label or '', p.round_number,
            p.game, p.round_in_game, p.condition, cfg.get('players_per_table'),
            cfg.get('replacement_rate'), p.on_bench, p.table, p.seat, p.tag,
            p.field_maybe_none('choice') or '', p.timed_out, g.field_maybe_none('stag_count'),
            g.field_maybe_none('group_total'), p.joined_table, p.left_table,
            g.replaced_seat, g.replacement_source,
            getattr(part, 'consent', None),
            getattr(part, 'comp_stag', None),
            getattr(part, 'comp_payoff', None),
            getattr(part, 'comp_groups', None),
        ]
