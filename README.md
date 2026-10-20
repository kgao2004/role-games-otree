# Role Games (oTree)

The multiplayer version of Role Games: real people play the modified stag hunt in groups
("tables") of 3–5, in the Anonymous, Identity, and Tag-based conditions. The screens follow
the Streamlit Play page.

## How a session works

1. Everyone consents, answers a short comprehension check, reads the instructions,
   then waits until all players are ready.
2. The session runs `num_games` games of `rounds_per_game` rounds. At the start of every game,
   people are shuffled into new tables.
3. Each round: choose Stag or Hare, wait for the rest of the table, see the results.
4. From round 2 of each game, each table has probability `replacement_rate` of one seat getting
   a newcomer. The seat keeps its label, color, and tag, and the others see the same messages
   as on the Play page ("Player 3 has been replaced!" and so on).
   - If anyone is sitting out (more people than seats), newcomers come from them first. The
     person replaced moves to the next table that needs someone, and the last one sits out.
   - If nobody is sitting out, the tables that need newcomers pass one player each around a
     circle. With only one table and nobody sitting out, replacement can't happen.
   - Either way, each table gets a newcomer at the set rate on average.
5. If time runs out on the choice screen (`choice_timeout`), a random choice is made and
   recorded as `timed_out`.

## Settings

Change these in `settings.py`, or on the admin page when you create a session:

| Setting | Default | Meaning |
|---|---|---|
| `players_per_table` | 3 | 3, 4, or 5. Tags split 1R/2B, 2R/2B, or 2R/3B as in the model. |
| `num_games` | 3 | New tables at the start of each game. |
| `rounds_per_game` | 10 | |
| `conditions` | `identity` | Comma-separated. Game k uses the k-th entry, cycling. |
| `replacement_rate` | 0.0 | Per table, per round. |
| `choice_timeout` | 60 | Seconds to choose (0 = no limit). |
| `results_timeout` | 30 | Seconds on the results screen (0 = no limit). |
| `instructions_timeout` | 180 | Seconds on the instructions screen before advancing (0 = no limit). |
| `real_world_currency_per_point` | 0.01 | Converts group-total points to a dollar bonus for oTree HR (100 pts = $1). Base Prolific pay is set in Prolific, not here. |

## Run it on your computer

From the `Role Games` folder:

```bash
cd role-games-otree
python3 -m venv venv
./venv/bin/pip install -r requirements.txt
PATH="$(pwd)/venv/bin:$PATH" otree resetdb --noinput   # after model changes
PATH="$(pwd)/venv/bin:$PATH" otree devserver
```

Then open http://localhost:8000. Click a session type on the demo page to get one link per
player, and open each link in its own browser window to play every seat yourself.

## Test it with bots

```bash
cd role-games-otree && PATH="$(pwd)/venv/bin:$PATH" otree test role_games_test 7
```

The bots choose with the Fictitious Play agents from `../role-games-model` (they choose at
random if that folder is missing). Add `--export somefolder` to save their data.

## Data

Admin → Data → **custom export** (`rolegames_custom.csv`) gives one row per person per round:
game, condition, table, seat, tag, whether they were sitting out, their choice, whether it
timed out, the table's score, any replacement (which seat, and whether the newcomer came
from the `bench` or an `other_table`), plus consent and the three comprehension answers
copied from round 1.

## Playing with other people

Everyone uses the room link, `/room/play`. People can open it early and wait there. Once
everyone has arrived, create the session in the admin **Rooms** tab with the number of people
who showed up.

Use `otree prodserver` (not `devserver`) when others are connecting. It applies time limits
even if someone closes their tab, and it requires an admin password:

```bash
export OTREE_ADMIN_PASSWORD='choose-a-password'
export OTREE_AUTH_LEVEL=STUDY
cd role-games-otree && PATH="$(pwd)/venv/bin:$PATH" otree prodserver 8000
```

- **Same Wi-Fi:** others go to `http://<your computer's local IP>:8000/room/play`.
- **Different places:** the server has to be reachable from the internet. Either use a tunnel
  from your computer, or host it (for example, oTree Hub). Both need an account that you set up.

If someone gets stuck or leaves, the admin **Monitor** tab has "Advance slowest participants".
Wait pages (`Regroup` after instructions, and `Compute` after each choice) cannot time out on
their own. For a live Prolific session, keep the Monitor tab open and advance anyone who
drops out, or the rest of the session can stall.

## Prolific via oTree HR

This project is set up for [oTree HR](https://otree.readthedocs.io/en/latest/mturk.html):
`finished` is a participant field, `prolific_completion_url` is a session field, and the
final page links participants back to Prolific.

1. Deploy to oTree Hub / Heroku. Set `DATABASE_URL` (Postgres), `OTREE_ADMIN_PASSWORD`,
   `OTREE_AUTH_LEVEL=STUDY`, and `OTREE_SECRET_KEY`. `psycopg2-binary` is in `requirements.txt`.
2. Participants join the room `/room/play`. They can wait there before a session exists.
3. When enough people have arrived, create the session in the admin **Rooms** tab.
4. Connect that session in oTree HR. HR sets `prolific_completion_url` and sends
   Prolific IDs as `participant_label`.
5. Launch the study from HR → Prolific.
6. After the session: export **custom export** (`rolegames_custom.csv`) for analysis;
   use HR’s payment list for bonuses; confirm completers have `finished` set.

Replace the placeholder consent wording in `rolegames/Consent.html` with your IRB-approved
text before you launch. On the last page, people who finish see a Prolific completion
button; a local demo without a completion URL still says they can close the window.

oTree `participation_fee` stays `0.00` because the base reward is paid on Prolific.
Adjust `real_world_currency_per_point` per session if you want a different bonus scale.
