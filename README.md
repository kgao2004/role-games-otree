# Role Games (oTree) — Study 1

Multiplayer stag hunt for Prolific. Tables of 3 or 5 auto-start when enough people arrive.

**Full setup (local, Heroku, Prolific):** see [SETUP.md](SETUP.md).

## Study 1 treatments

| Config | Room | Table size | Condition |
|---|---|---|---|
| `study1_3_anonymous` | `/room/play_3_anonymous` | 3 | Anonymous |
| `study1_3_identity` | `/room/play_3_identity` | 3 | Identity |
| `study1_3_tag_based` | `/room/play_3_tag_based` | 3 | Tag-based |
| `study1_5_anonymous` | `/room/play_5_anonymous` | 5 | Anonymous |
| `study1_5_identity` | `/room/play_5_identity` | 5 | Identity |
| `study1_5_tag_based` | `/room/play_5_tag_based` | 5 | Tag-based |

All use `replacement_rate=0.0`. Partners stay together for the session.

## Session flow

1. Consent → comprehension → instructions (`intro` app).
2. Wait until `players_per_table` people are ready (`Match` with `group_by_arrival_time`).
3. Play `num_games` × `rounds_per_game` with that fixed group.
4. Final page (Prolific completion link when oTree HR sets it).

## Quick local run

```bash
cd role-games-otree
python3 -m venv venv
./venv/bin/pip install -r requirements.txt
PATH="$(pwd)/venv/bin:$PATH" otree resetdb --noinput
PATH="$(pwd)/venv/bin:$PATH" otree devserver
```

Open http://localhost:8000. For a 3-player config, open 3 links and walk each through instructions — the game starts when the third person reaches the wait page.

```bash
PATH="$(pwd)/venv/bin:$PATH" otree test study1_3_identity 3
```

## Settings

| Setting | Default | Meaning |
|---|---|---|
| `players_per_table` | 3 or 5 | Fixed per Study 1 config |
| `num_games` | 3 | Games with the same partners |
| `rounds_per_game` | 10 | |
| `conditions` | one of anonymous / identity / tag_based | |
| `replacement_rate` | 0.0 | Study 1 has no replacement |
| `choice_timeout` | 60 | Seconds to choose (0 = no limit) |
| `results_timeout` | 30 | |
| `instructions_timeout` | 180 | |
| `real_world_currency_per_point` | 0.01 | Bonus scale for oTree HR |

## Data

Admin → Data → **custom export** (`rolegames_custom.csv`): one row per person per round, plus consent and comprehension answers from the intro.

## Dropouts

With no replacement, a mid-game dropout can stall that table on a wait page. Use Monitor → **Advance slowest participants**. Analyze incomplete tables up to the dropout.
