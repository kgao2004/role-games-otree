# Setup guide: Role Games (Study 1) on oTree

Send this file with the project code. It covers local install, Heroku deploy via oTree Hub, and Prolific.

## What this project is

Multiplayer stag hunt for **Study 1**:

- Six treatments (separate Prolific links / rooms):
  - 3 players × Anonymous / Identity / Tag-based
  - 5 players × Anonymous / Identity / Tag-based
- `replacement_rate = 0.0` (no mid-game replacement)
- Flow: **Consent → comprehension → instructions → wait until the table is full → game**
- Tables **auto-start** when `players_per_table` people are active on the match wait page
- Partners stay together for the whole session; parallel tables do not wait on each other

## 1. Local install

Requirements: Python 3.9+ (3.13 works with oTree 6.0.15).

```bash
cd role-games-otree
python3 -m venv venv
./venv/bin/pip install -r requirements.txt
./venv/bin/pip install requests          # needed for otree test
PATH="$(pwd)/venv/bin:$PATH" otree resetdb --noinput
PATH="$(pwd)/venv/bin:$PATH" otree devserver
```

Open http://localhost:8000.

### Local smoke test (auto-start)

1. On the demo page, open **Study 1: 3 players · Identity**.
2. Open **3** participant links in separate browser windows (or incognito windows).
3. In each window: consent → quiz (correct answers) → instructions → wait.
4. When the third person reaches the wait page, all three should enter the game together.

Bot test:

```bash
PATH="$(pwd)/venv/bin:$PATH" otree test study1_3_identity 3
```

## 2. Deploy on oTree Hub → Heroku (not Sites)

**Sites** (`on.otree.org`) does **not** accept `.otreezip` uploads. Use **Heroku server deployment**.

1. Create / log in to [Heroku](https://signup.heroku.com) and [otreehub.com](https://www.otreehub.com).
2. On Hub, open **Heroku server deployment** and connect the Heroku account.
3. From the project folder:

```bash
PATH="$(pwd)/venv/bin:$PATH" otree zip
```

4. Upload the `.otreezip` on Hub → Deploy. Wait for a green build.
5. Attach **Heroku Postgres** (required for multiplayer). Confirm `DATABASE_URL` starts with `postgres`.
6. Set config vars:
   - `OTREE_ADMIN_PASSWORD` — choose a password
   - `OTREE_AUTH_LEVEL` = `STUDY`
   - `OTREE_SECRET_KEY` — long random string
7. **Reset DB** after first deploy (and after any model / page_sequence changes).
8. Open `/server_check` on the live site — it must report Postgres, not SQLite.

Participant room example:

`https://YOUR-APP.herokuapp.com/room/play_3_identity`

SQLite will crash when two people play at once (`database is locked`). Always use Postgres online.

### Cost note

Heroku dynos + Postgres are paid (often a few dollars if you run a study for a day then scale dynos to 0). There is no reliable free multiplayer host for this zip on Hub.

## 3. Create a live session (per treatment)

Each treatment has its own room:

| Treatment | Room URL path | Session config |
|---|---|---|
| 3 · Anonymous | `/room/play_3_anonymous` | `study1_3_anonymous` |
| 3 · Identity | `/room/play_3_identity` | `study1_3_identity` |
| 3 · Tag-based | `/room/play_3_tag_based` | `study1_3_tag_based` |
| 5 · Anonymous | `/room/play_5_anonymous` | `study1_5_anonymous` |
| 5 · Identity | `/room/play_5_identity` | `study1_5_identity` |
| 5 · Tag-based | `/room/play_5_tag_based` | `study1_5_tag_based` |

Steps:

1. Admin → **Rooms** → open the room for that treatment.
2. Create a session with the matching config and **enough slots** (e.g. 30–100). Extra people wait until a full table of 3 or 5 forms.
3. Participants join the room link, finish intro pages, then wait. When N arrive, that table starts.
4. Keep **Monitor** open. Wait pages inside a table still need “Advance slowest participants” if someone drops mid-game (no auto-kill). Analyze incomplete tables up to dropout.

Use `prodserver` on Heroku (Hub does this). Do not use `devserver` for real participants.

## 4. Prolific + oTree HR

This project already has:

- `PARTICIPANT_FIELDS`: includes `finished`, consent/quiz fields
- `SESSION_FIELDS`: `prolific_completion_url`
- Final page completion link when HR sets the URL

Recommended flow:

1. Deploy as above with Postgres.
2. In [oTree HR](https://hr.otreehub.com/), connect the Heroku site and the session.
3. Create **one Prolific study per treatment** (six studies for Study 1).
4. Study URL pattern (URL parameters → `participant_label`):

`https://YOUR-APP.herokuapp.com/room/play_3_identity?participant_label={{%PROLIFIC_PID%}}`

5. Before launch: replace placeholder IRB text in `intro/Consent.html`.
6. After the session: custom export (`rolegames_custom.csv`), confirm `finished`, use HR bonus list if paying bonuses.

Base Prolific pay is set in Prolific. oTree `participation_fee` is `0.00`. Bonus conversion uses `real_world_currency_per_point` (default `0.01`).

## 5. Updating the code later

```bash
PATH="$(pwd)/venv/bin:$PATH" otree zip
```

Upload the new zip on Hub.

- Template / copy-only changes: upload **without** resetting the DB.
- Model field or `page_sequence` changes: upload **and** Reset DB (wipes old sessions on that site).

## 6. Dropout policy (Study 1, no replacement)

If a player leaves mid-game, the rest of that table can stall on a wait page. Use Monitor → Advance slowest participants. Treat the table as incomplete and analyze data up to the dropout. There is no automatic “kill game” logic yet.
