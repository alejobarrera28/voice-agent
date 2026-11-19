"""Reset the demo Google Calendar and intervals.icu calendar to a known scenario, relative to today.

  python scripts/seed.py --dry-run
  python scripts/seed.py --wipe-only
  python scripts/seed.py
"""

import argparse
import os
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import requests
from dotenv import load_dotenv
from google.oauth2 import service_account
from googleapiclient.discovery import build

DEMO_CALENDAR_ID = "brick.voice.demo@gmail.com"
INTERVALS_API = "https://intervals.icu/api/v1"

# Days are offsets from today (D).
SCENARIO = {
    # (day, start, end, title, extra fields)
    "calendar": [
        (-1, "07:00", "08:00", "Pool lane reservation - Complejo Acuático", {"description": "Pool contact via SMS"}),
        (0, "09:30", "09:45", "Team standup", {}),
        (0, "12:00", "13:00", "Dentist appointment - Dr. Restrepo", {"location": "Clínica del Country"}),
        (0, "15:00", "16:00", "Sprint planning", {}),
        (1, "10:00", "10:30", "1:1 with manager", {}),
        (1, "18:00", "19:00", "Pool lane reservation - Complejo Acuático", {"description": "Pool contact via SMS"}),
    ],
    # (day, time, category, type, name, intensity, purpose, extra fields). D+4 is a rest day (no event).
    "intervals": [
        (-1, "07:00", "WORKOUT", "Swim", "Easy swim - technique 45min", "Low",
         "Drill work to groove stroke technique without fatigue.", {"moving_time": 45 * 60}),
        (0, "12:00", "WORKOUT", "Ride", "[KEY] Bike - threshold intervals 90min", "High",
         "Key session of the week: raise FTP with sustained threshold efforts.", {"moving_time": 90 * 60}),
        (1, "18:00", "WORKOUT", "Swim", "Swim - aerobic 3km", "Low",
         "Steady aerobic volume to build swim endurance.", {}),
        (2, "07:00", "WORKOUT", "Run", "Easy run - 40min", "Low",
         "Easy aerobic run to stay fresh before the race simulation.", {"moving_time": 40 * 60}),
        (3, "07:00", "RACE_C", "Other", "Olympic distance race simulation", "High",
         "Rehearse race pacing, nutrition and transitions at Olympic distance.", {}),
    ],
}


def summary(source, dry_run, deleted, created):
    verbs = ("would delete", "would create") if dry_run else ("deleted", "created")
    print(f"[{source}] {verbs[0]} {deleted} events, {verbs[1]} {created} events")


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

    created = 0
    if not wipe_only:
        for day, t1, t2, title, extra in SCENARIO["calendar"]:
            d = today + timedelta(day)
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
            created += 1

    summary("calendar", dry_run, len(existing), created)


def seed_intervals(today, dry_run, wipe_only):
    url = f"{INTERVALS_API}/athlete/{os.environ['INTERVALS_ATHLETE_ID']}/events"
    auth = ("API_KEY", os.environ["INTERVALS_API_KEY"])

    # Wipe everything in [today-3d, today+21d] (dates are local to the athlete)
    window = {"oldest": str(today - timedelta(3)), "newest": str(today + timedelta(21))}
    r = requests.get(url, params=window, auth=auth, timeout=30)
    r.raise_for_status()
    existing = r.json()
    for ev in existing:
        print("  delete:", ev["start_date_local"], ev["category"], ev.get("name"))
        if not dry_run:
            requests.delete(f"{url}/{ev['id']}", auth=auth, timeout=30).raise_for_status()

    created = 0
    if not wipe_only:
        for day, time, category, sport, name, intensity, purpose, extra in SCENARIO["intervals"]:
            d = today + timedelta(day)
            body = {
                "category": category,
                "type": sport,
                "name": name,
                "start_date_local": f"{d}T{time}:00",
                "description": f"Intensity: {intensity}\nPurpose: {purpose}",
                "external_id": f"brick-seed-{d}-{time.replace(':', '')}",
                **extra,
            }
            print("  create:", d, time, category, name)
            if not dry_run:
                requests.post(url, json=body, auth=auth, timeout=30).raise_for_status()
            created += 1

    summary("intervals", dry_run, len(existing), created)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--wipe-only", action="store_true")
    args = parser.parse_args()

    load_dotenv(".env")
    tz = ZoneInfo(os.environ["DEMO_TIMEZONE"])
    today = datetime.now(tz).date()

    seed_calendar(today, tz, args.dry_run, args.wipe_only)
    seed_intervals(today, args.dry_run, args.wipe_only)
