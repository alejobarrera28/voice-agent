"""Reset the demo Google Calendar to a known scenario, relative to today.

  python scripts/seed.py --dry-run
  python scripts/seed.py --wipe-only
  python scripts/seed.py
"""

import argparse
import os
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from dotenv import load_dotenv
from google.oauth2 import service_account
from googleapiclient.discovery import build

DEMO_CALENDAR_ID = "brick.voice.demo@gmail.com"

# (day, start, end, title, extra fields). day: "D", "D+1", "SAT" (next Saturday), "SAT+7"
SCENARIO = {
    "calendar": [
        ("D",     "09:30", "09:45", "Team standup", {}),
        ("D",     "12:00", "13:00", "Doctor appointment - Dr. Restrepo", {"location": "Clínica del Country"}),
        ("D",     "15:00", "16:00", "Sprint planning", {}),
        ("D+1",   "10:00", "10:30", "1:1 with manager", {}),
        ("D+1",   "18:00", "19:00", "Pool lane reservation - Complejo Acuático", {"description": "Pool contact via SMS"}),
        ("SAT",   "13:00", "15:00", "Sofía's birthday lunch", {"description": "Bring a gift"}),
        ("SAT+7", "11:00", "13:00", "Brunch with college friends", {}),
    ],
}


def to_date(day, today):
    next_sat = today + timedelta(days=(5 - today.weekday()) % 7 or 7)
    return {"D": today, "D+1": today + timedelta(1), "SAT": next_sat, "SAT+7": next_sat + timedelta(7)}[day]


def seed_calendar(today, tz, dry_run, wipe_only):
    calendar_id = os.environ["GCAL_CALENDAR_ID"]
    if calendar_id != DEMO_CALENDAR_ID:
        raise SystemExit(f"Refusing to run: {calendar_id} is not the demo calendar.")

    creds = service_account.Credentials.from_service_account_file(
        os.environ["GOOGLE_SERVICE_ACCOUNT_FILE"],
        scopes=["https://www.googleapis.com/auth/calendar"],
    )
    events = build("calendar", "v3", credentials=creds).events()

    # Wipe everything in [today-3d, today+21d]
    start = datetime.combine(today - timedelta(3), datetime.min.time(), tz)
    end = datetime.combine(today + timedelta(22), datetime.min.time(), tz)
    existing = events.list(calendarId=calendar_id, timeMin=start.isoformat(), timeMax=end.isoformat(),
                           singleEvents=True, maxResults=2500).execute().get("items", [])
    for ev in existing:
        print("  delete:", ev["start"].get("dateTime", ev["start"].get("date")), ev.get("summary"))
        if not dry_run:
            events.delete(calendarId=calendar_id, eventId=ev["id"]).execute()

    # Create the scenario
    created = []
    if not wipe_only:
        for day, t1, t2, title, extra in SCENARIO["calendar"]:
            d = to_date(day, today)
            body = {
                "summary": title,
                "start": {"dateTime": f"{d}T{t1}:00", "timeZone": tz.key},
                "end": {"dateTime": f"{d}T{t2}:00", "timeZone": tz.key},
                "extendedProperties": {"private": {"brick_seed": "true"}},
                **extra,
            }
            print("  create:", d, t1, title)
            if not dry_run:
                events.insert(calendarId=calendar_id, body=body).execute()
            created.append(d)

    print(f"Deleted {len(existing)} events, created {len(created)} events "
          f"({', '.join(sorted({str(d) for d in created}))})" + (" [DRY RUN]" if dry_run else ""))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--wipe-only", action="store_true")
    args = parser.parse_args()

    load_dotenv()
    tz = ZoneInfo(os.environ["DEMO_TIMEZONE"])
    today = datetime.now(tz).date()

    seed_calendar(today, tz, args.dry_run, args.wipe_only)
    # Later: seed_intervals(...), seed_jira(...)
