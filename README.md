# voice-agent

Brick — an ElevenLabs voice agent ("chief of staff" for a triathlete with a full-time job), managed as code with the ElevenLabs CLI (`agent_configs/`, `tool_configs/`, `test_configs/`).

## Seeding the demo

`scripts/seed.py` resets the demo Google Calendar (`brick.voice.demo@gmail.com`) and the demo intervals.icu athlete's calendar to a known scenario, with dates relative to the day it runs (timezone `America/Bogota`).

On both, it deletes **every** event from 3 days ago through 21 days ahead (including anything Brick created during rehearsals), then creates the scenario events. Google events are tagged with `extendedProperties.private.brick_seed=true`; intervals.icu events get an `external_id` starting with `brick-seed-`. It refuses to run against any Google calendar other than the demo account. intervals.icu needs `INTERVALS_API_KEY` and `INTERVALS_ATHLETE_ID` in `.env`.

Setup (once):

```sh
python3 -m venv .venv
.venv/bin/pip install -r scripts/requirements.txt
cp .env.example .env   # then fill in values
```

The service-account key goes in `secrets/gcal-seeder.json` (gitignored) and must be shared on the demo calendar with "Make changes to events".

Run:

```sh
.venv/bin/python scripts/seed.py --dry-run    # show what would change
.venv/bin/python scripts/seed.py              # wipe + seed
.venv/bin/python scripts/seed.py --wipe-only  # just clear the window
```

Edit `SCENARIO` at the top of the script to change the events. New sources (e.g. Jira) go in as another `seed_<name>()` function. Run it from the repo root (paths in `.env` are relative to it).
