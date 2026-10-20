import random

from otree.api import *

doc = """
Role Games with real people: a modified N-player stag hunt played at tables of 3–5.

Tables are re-formed at the start of every game. Within a game a table keeps its seats
(label, color, and tag), and replacement changes who sits in one seat. Newcomers come from
the bench if anyone is sitting out, otherwise from another table (see replace_players).
"""


class C(BaseConstants):
    NAME_IN_URL = 'rolegames'
    PLAYERS_PER_GROUP = None     # Regroup sets the groups every round
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
    # Same palette as the Streamlit Play page
    PLAYER_COLORS = ['#4878CF', '#6ACC65', '#D65F5F', '#e5a917', '#9b59b6']
    TAG_COLORS = {'red': '#e57373', 'blue': '#64b5f6'}
    ANON_COLOR = '#9E9E9E'
    ACTION_EMOJI = {'stag': '🦌', 'hare': '🐇'}

    INTRO_TIMEOUT = 90
    SUMMARY_TIMEOUT = 60
    COMP_STAG_CORRECT = 1
    COMP_PAYOFF_CORRECT = 1
    COMP_GROUPS_CORRECT = 1


class Subsession(BaseSubsession):
    pass


class Group(BaseGroup):
    table = models.IntegerField(initial=0)               # 0 = the bench
    condition = models.StringField(initial='')
    stag_count = models.IntegerField()
    group_total = models.IntegerField()
    replaced_seat = models.IntegerField(initial=0)       # seat whose occupant changed this round
    replaced_tag = models.StringField(initial='')
    replacement_source = models.StringField(initial='')  # newcomer came from 'bench' or 'other_table'


class Player(BasePlayer):
    game = models.IntegerField()
    round_in_game = models.IntegerField()
    condition = models.StringField()
    on_bench = models.BooleanField(initial=False)
    table = models.IntegerField(initial=0)
    seat = models.IntegerField(initial=0)
    tag = models.StringField(initial='')
    joined_table = models.BooleanField(initial=False)    # took over a seat mid-game this round
    left_table = models.BooleanField(initial=False)      # moved from a table to the bench this round
    choice = models.StringField(choices=['stag', 'hare'])
    timed_out = models.BooleanField(initial=False)
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
            [2, 'You stay in the same group for the whole study'],
            [3, 'Groups are reshuffled every round'],
        ],
        widget=widgets.RadioSelect,
    )


# ─── Settings and payoff ─────────────────────────────────────────────────────

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
    """Same payoff as role_games.game._group_total in the model code."""
    return (4 if actions.count('stag') >= 2 else 0) + actions.count('hare')


def tags_for_table(n):
    """Same split as the model: 3 → 1 red/2 blue, 4 → 2/2, 5 → 2/3."""
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


# ─── Seating: new tables, carry-over, replacement ────────────────────────────
#
# A table is {seat: [tag, player]}. Seats keep their label and tag for the whole game;
# replacement only changes the player in a seat.

def new_tables(players, n, condition):
    order = list(players)
    random.shuffle(order)
    # people who have sat out more rounds get seats first (sort is stable, so ties stay random)
    order.sort(key=lambda p: -p.participant.rounds_benched)
    k = len(order) // n
    tables = {}
    for t in range(1, k + 1):
        members = order[(t - 1) * n:t * n]
        tags = tags_for_table(n) if condition == 'tag_based' else [''] * n
        tables[t] = {seat: [tags[seat - 1], p] for seat, p in enumerate(members, start=1)}
    return tables, order[k * n:]


def carry_over(players):
    tables, bench = {}, []
    for p in players:
        prev = p.in_round(p.round_number - 1)
        if prev.on_bench:
            bench.append(p)
        else:
            tables.setdefault(prev.table, {})[prev.seat] = [prev.tag, p]
    random.shuffle(bench)
    bench.sort(key=lambda p: p.participant.bench_since)   # longest waiting first
    return tables, bench


def replace_players(tables, bench, rate):
    """Each table independently gets a newcomer in one random seat with probability `rate`.

    If anyone is on the bench, newcomers form a chain: the longest-waiting person takes the
    first open seat, the person they replace moves to the next drawn table, and so on; the
    last person replaced goes to the bench. With nobody on the bench, the drawn tables pass
    one player each around a circle. Either way every drawn table gets exactly one newcomer.
    A lone drawn table with no bench has nobody to receive, so it pairs with an undrawn table
    half the time, which keeps the average rate right. Mutates tables and bench.
    Returns ({table: event}, ids of people who ended up on the bench).
    """
    events = {}
    hit = [t for t in tables if random.random() < rate]
    random.shuffle(hit)

    def replace(t, arriving, source):
        seat = random.choice(list(tables[t]))
        tag, leaving = tables[t][seat]
        tables[t][seat] = [tag, arriving]
        events[t] = dict(seat=seat, tag=tag, source=source, newcomer=arriving.id_in_subsession)
        return leaving

    if bench:
        waiting = {p.id_in_subsession for p in bench}
        queue = list(bench)   # longest waiting first; people replaced join the end
        for t in hit:
            arriving = queue.pop(0)
            source = 'bench' if arriving.id_in_subsession in waiting else 'other_table'
            queue.append(replace(t, arriving, source))
        leavers = {p.id_in_subsession for p in queue} - waiting
        bench[:] = queue
        return events, leavers

    if len(hit) == 1:
        undrawn = [u for u in tables if u not in hit]
        if not undrawn or random.random() < 0.5:
            return events, set()
        hit.append(random.choice(undrawn))
    if len(hit) >= 2:
        # everyone moving is chosen before anyone is seated, so nobody moves twice
        movers = []
        for t in hit:
            seat = random.choice(list(tables[t]))
            movers.append((t, seat, tables[t][seat][1]))
        for i, (t, seat, _) in enumerate(movers):
            arriving = movers[i - 1][2]   # from the previous table in the circle
            tag = tables[t][seat][0]
            tables[t][seat] = [tag, arriving]
            events[t] = dict(seat=seat, tag=tag, source='other_table',
                             newcomer=arriving.id_in_subsession)
    return events, set()


def assign_seats(subsession):
    s = config(subsession.session)
    rnd = subsession.round_number
    game, round_in_game = game_and_round(rnd, s['rounds_per_game'])
    condition = condition_for_game(s, game)
    players = subsession.get_players()

    if round_in_game == 1:
        tables, bench = new_tables(players, s['n'], condition)
        events, leavers = {}, set()
    else:
        tables, bench = carry_over(players)
        events, leavers = replace_players(tables, bench, s['replacement_rate'])

    assignments = {}
    newcomers = {e['newcomer'] for e in events.values()}
    for t, seats in tables.items():
        for seat, (tag, p) in seats.items():
            iis = p.id_in_subsession
            assignments[iis] = dict(table=t, seat=seat, tag=tag, on_bench=False,
                                    joined_table=iis in newcomers, left_table=False)
    for p in bench:
        iis = p.id_in_subsession
        assignments[iis] = dict(table=0, seat=0, tag='', on_bench=True,
                                joined_table=False, left_table=iis in leavers)

    matrix = [[tables[t][seat][1] for seat in sorted(tables[t])] for t in sorted(tables)]
    if bench:
        matrix.append(bench)
    subsession.set_group_matrix(matrix)

    # set_group_matrix reloads players and recreates groups, so set fields afterwards
    for p in subsession.get_players():
        a = assignments[p.id_in_subsession]
        p.game, p.round_in_game, p.condition = game, round_in_game, condition
        p.table, p.seat, p.tag, p.on_bench = a['table'], a['seat'], a['tag'], a['on_bench']
        p.joined_table, p.left_table = a['joined_table'], a['left_table']
        if p.on_bench:
            was_benched = round_in_game > 1 and p.in_round(rnd - 1).on_bench
            if not was_benched:
                p.participant.bench_since = rnd
            p.participant.rounds_benched += 1

    for g in subsession.get_groups():
        g.table = g.get_players()[0].table
        g.condition = condition
        event = events.get(g.table)
        if event:
            g.replaced_seat = event['seat']
            g.replaced_tag = event['tag']
            g.replacement_source = event['source']


# ─── What each player sees ───────────────────────────────────────────────────

def table_members(player):
    return sorted(player.group.get_players(), key=lambda p: p.seat)


def table_total(player, *, include_current):
    """Points scored by this player's table so far in the current game."""
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


def score_rows(n):
    rows = []
    for stags in range(n + 1):
        rows.append(dict(
            stags=stags, hares=n - stags, total=group_total(['stag'] * stags + ['hare'] * (n - stags)),
            best=stags == 2, worst=stags == 1,
        ))
    return rows


def condition_cards(conditions):
    seen = []
    for c in conditions:
        if c not in seen:
            seen.append(c)
    return [dict(icon=C.CONDITION_INFO[c][0], name=C.CONDITIONS[c], text=C.CONDITION_INFO[c][1]) for c in seen]


def count_label(k, noun):
    return f'{k} {noun}' + ('' if k == 1 else 's')


def group_intro(player, members):
    """One line describing the player's new group at the start of a game."""
    start = f"You're in a new group of {len(members)}."
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

class Consent(Page):
    form_model = 'player'
    form_fields = ['consent']

    @staticmethod
    def is_displayed(player):
        return player.round_number == 1

    @staticmethod
    def error_message(player, values):
        if not values.get('consent'):
            return 'You must consent to take part in order to continue.'


class Comprehension(Page):
    form_model = 'player'
    form_fields = ['comp_stag', 'comp_payoff', 'comp_groups']

    @staticmethod
    def is_displayed(player):
        return player.round_number == 1

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
                'Not quite. You are placed in a new group at the start of every game.'
            )
        return errors


class Instructions(Page):
    @staticmethod
    def is_displayed(player):
        return player.round_number == 1

    @staticmethod
    def get_timeout_seconds(player):
        return config(player.session)['instructions_timeout'] or None

    @staticmethod
    def vars_for_template(player):
        s = config(player.session)
        num_players = len(player.subsession.get_players())
        cards = condition_cards(s['conditions'])
        return dict(
            n=s['n'],
            games_label=count_label(s['num_games'], 'game'),
            rounds_per_game=s['rounds_per_game'],
            score_rows=score_rows(s['n']),
            conditions=cards,
            multiple_conditions=len(cards) > 1,
            has_replacement=s['replacement_rate'] > 0,
            has_bench=num_players % s['n'] != 0,
            choice_timeout=s['choice_timeout'],
            instructions_timeout=s['instructions_timeout'],
        )


class Regroup(WaitPage):
    wait_for_all_groups = True

    @staticmethod
    def is_displayed(player):
        return in_play(player)

    @staticmethod
    def vars_for_template(player):
        if player.round_number == 1:
            return dict(
                title_text='Waiting for everyone to join',
                body_text='The game starts as soon as everyone has read the instructions.',
            )
        prev = player.in_round(player.round_number - 1)
        if prev.on_bench:
            if prev.left_table:
                body = ('Someone new has taken your seat, so you are sitting out for now. '
                        'You will rejoin when a seat opens up or when the next game starts.')
            else:
                body = ('There are more players than seats, so a few people sit out at a time. '
                        'You will join when a seat opens up or when the next game starts.')
            return dict(title_text='You are sitting out for now', body_text=body)
        return dict(title_text='Please wait', body_text='Waiting for the other groups to finish this round.')

    @staticmethod
    def after_all_players_arrive(subsession):
        assign_seats(subsession)


class GameIntro(Page):
    timeout_seconds = C.INTRO_TIMEOUT

    @staticmethod
    def is_displayed(player):
        return in_play(player) and player.round_in_game == 1

    @staticmethod
    def vars_for_template(player):
        s = config(player.session)
        icon, text = C.CONDITION_INFO[player.condition]
        members = [] if player.on_bench else table_members(player)
        return dict(
            num_games=s['num_games'],
            condition_icon=icon,
            condition_name=C.CONDITIONS[player.condition],
            condition_text=text,
            intro=group_intro(player, members) if members else '',
            players=players_html(player) if members else '',
        )


class Choose(Page):
    form_model = 'player'
    form_fields = ['choice']

    @staticmethod
    def is_displayed(player):
        return in_play(player) and not player.on_bench

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
        return in_play(player) and not player.on_bench

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
        return in_play(player) and not player.on_bench

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
            total=0 if player.on_bench else table_total(player, include_current=True),
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
    Consent, Comprehension, Instructions, Regroup, GameIntro, Choose, Compute,
    Results, GameSummary, Final,
]


# ─── Data export (admin → Data → "custom export") ───────────────────────────

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
            continue   # rounds after the last game
        g = p.group
        cfg = p.session.config
        first = p.in_round(1)
        yield [
            p.session.code, p.participant.code, p.participant.label or '', p.round_number,
            p.game, p.round_in_game, p.condition, cfg.get('players_per_table'),
            cfg.get('replacement_rate'), p.on_bench, p.table, p.seat, p.tag,
            p.field_maybe_none('choice') or '', p.timed_out, g.field_maybe_none('stag_count'),
            g.field_maybe_none('group_total'), p.joined_table, p.left_table,
            g.replaced_seat, g.replacement_source,
            first.field_maybe_none('consent'),
            first.field_maybe_none('comp_stag'),
            first.field_maybe_none('comp_payoff'),
            first.field_maybe_none('comp_groups'),
        ]
