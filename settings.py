from os import environ

SESSION_CONFIG_DEFAULTS = dict(
    # Base Prolific reward is set in Prolific / oTree HR, not here.
    # Points are group totals each round; 0.01 → 100 points = $1.00 bonus. Override per session.
    real_world_currency_per_point=0.01,
    participation_fee=0.00,
    players_per_table=3,
    num_games=3,
    rounds_per_game=10,
    conditions='identity',
    replacement_rate=0.0,
    choice_timeout=60,
    results_timeout=30,
    instructions_timeout=180,
    doc="",
)

def _study1(name, display_name, n, condition):
    return dict(
        name=name,
        display_name=display_name,
        app_sequence=['intro', 'rolegames'],
        num_demo_participants=n,
        players_per_table=n,
        conditions=condition,
        replacement_rate=0.0,
        doc=f'Study 1: {n}-player tables, {condition}, no replacement. Auto-starts when {n} arrive.',
    )


SESSION_CONFIGS = [
    _study1('study1_3_anonymous', 'Study 1: 3 players · Anonymous', 3, 'anonymous'),
    _study1('study1_3_identity', 'Study 1: 3 players · Identity', 3, 'identity'),
    _study1('study1_3_tag_based', 'Study 1: 3 players · Tag-based', 3, 'tag_based'),
    _study1('study1_5_anonymous', 'Study 1: 5 players · Anonymous', 5, 'anonymous'),
    _study1('study1_5_identity', 'Study 1: 5 players · Identity', 5, 'identity'),
    _study1('study1_5_tag_based', 'Study 1: 5 players · Tag-based', 5, 'tag_based'),
]

# One room per treatment so each Prolific study has a stable /room/... link.
ROOMS = [
    dict(name='play_3_anonymous', display_name='Study 1: 3 · Anonymous'),
    dict(name='play_3_identity', display_name='Study 1: 3 · Identity'),
    dict(name='play_3_tag_based', display_name='Study 1: 3 · Tag-based'),
    dict(name='play_5_anonymous', display_name='Study 1: 5 · Anonymous'),
    dict(name='play_5_identity', display_name='Study 1: 5 · Identity'),
    dict(name='play_5_tag_based', display_name='Study 1: 5 · Tag-based'),
]

PARTICIPANT_FIELDS = [
    'rounds_benched', 'bench_since', 'finished',
    'consent', 'comp_stag', 'comp_payoff', 'comp_groups',
]
SESSION_FIELDS = ['prolific_completion_url']

LANGUAGE_CODE = 'en'
REAL_WORLD_CURRENCY_CODE = 'USD'
USE_POINTS = True

ADMIN_USERNAME = 'admin'
ADMIN_PASSWORD = environ.get('OTREE_ADMIN_PASSWORD')

DEMO_PAGE_INTRO_HTML = """
Role Games Study 1: 3- or 5-player tables in Anonymous, Identity, or Tag-based.
Tables auto-start when enough people arrive.
"""

SECRET_KEY = environ.get('OTREE_SECRET_KEY', '8876369626541')
