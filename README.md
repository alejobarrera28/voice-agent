# voice-agent

Brick — an ElevenLabs voice agent ("chief of staff" for a triathlete with a full-time job), managed as code with the ElevenLabs CLI (`agent_configs/`, `tool_configs/`, `test_configs/`).

## Seeding the demo

`scripts/seed.py` resets the demo Google Calendar (`brick.voice.demo@gmail.com`) to a known scenario, with dates relative to the day it runs (timezone `America/Bogota`).

It deletes **every** event from 3 days ago through 21 days ahead (including reminders Brick created during rehearsals), then creates the scenario events, each tagged with `extendedProperties.private.brick_seed=true`. It refuses to run against any calendar other than the demo account.

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

Edit `SCENARIO` at the top of the script to change the events. New sources (intervals.icu, Jira) go in as another `seed_<name>()` function. Run it from the repo root (paths in `.env` are relative to it).
