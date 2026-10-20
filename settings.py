from os import environ

# Every session type shares SESSION_CONFIG_DEFAULTS. Any of these values can also be
# changed in the admin page when you create a session.
SESSION_CONFIG_DEFAULTS = dict(
    # Base Prolific reward is set in Prolific / oTree HR, not here.
    # Points are group totals each round; 0.01 → 100 points = $1.00 bonus. Override per session.
    real_world_currency_per_point=0.01,
    participation_fee=0.00,
    players_per_table=3,      # 3–5 people play together at each table
    num_games=3,              # new tables are formed at the start of every game
    rounds_per_game=10,
    conditions='identity',    # comma-separated; game k uses the k-th entry (cycling)
    replacement_rate=0.0,     # per table, per round, from round 2 of each game
    choice_timeout=60,        # seconds to choose before a random choice is made (0 = no limit)
    results_timeout=30,       # seconds on the results page before moving on (0 = no limit)
    instructions_timeout=180, # seconds on instructions before advancing (0 = no limit)
    doc="",
)

SESSION_CONFIGS = [
    dict(
        name='role_games_test',
        display_name='Role Games: all three conditions, with replacement',
        app_sequence=['rolegames'],
        num_demo_participants=6,
        conditions='anonymous, identity, tag_based',
        replacement_rate=0.3,
        doc="One game per condition. Players are sometimes replaced partway through a game.",
    ),
    dict(
        name='role_games_anonymous',
        display_name='Role Games: Anonymous',
        app_sequence=['rolegames'],
        num_demo_participants=6,
        conditions='anonymous',
    ),
    dict(
        name='role_games_identity',
        display_name='Role Games: Identity',
        app_sequence=['rolegames'],
        num_demo_participants=6,
        conditions='identity',
    ),
    dict(
        name='role_games_tag_based',
        display_name='Role Games: Tag-based',
        app_sequence=['rolegames'],
        num_demo_participants=6,
        conditions='tag_based',
    ),
]

# A room gives everyone one permanent link. People can open it before the session exists
# and wait there; you then create the session with however many showed up.
ROOMS = [
    dict(name='play', display_name='Role Games'),
]

PARTICIPANT_FIELDS = ['rounds_benched', 'bench_since', 'finished']
SESSION_FIELDS = ['prolific_completion_url']

LANGUAGE_CODE = 'en'
REAL_WORLD_CURRENCY_CODE = 'USD'
USE_POINTS = True

ADMIN_USERNAME = 'admin'
# Set this in an environment variable before running the server where others can reach it.
ADMIN_PASSWORD = environ.get('OTREE_ADMIN_PASSWORD')

DEMO_PAGE_INTRO_HTML = """
Role Games: a multi-player stag hunt with Anonymous, Identity, and Tag-based conditions.
"""

SECRET_KEY = environ.get('OTREE_SECRET_KEY', '8876369626541')
