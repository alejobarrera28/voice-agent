"""Golden-path QA run: reseed, run the scripted text conversation with Brick, print the transcript.

  .venv/bin/python -W ignore scripts/qa_golden_path.py <run_label>

Uses the ElevenLabs CLI (its own auth) for the Conversations API, so tools run for real
(workouts get moved). Full JSON per turn and per conversation is saved to $TMPDIR/brick_qa_runs/.
"""
import json
import os
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import requests
from dotenv import dotenv_values

AGENT = "agent_9101m7rkrkbrf2ftj94ej22e6a24"
TURNS = [
    "What's my day?",
    "I can't ride at noon and I don't want to ride tonight. Let me talk to my coach.",
    "Can I just skip today's ride?",
    "Yes, do it.",
    "Thanks, bye.",
]
OUT = os.path.join(tempfile.gettempdir(), "brick_qa_runs")
os.makedirs(OUT, exist_ok=True)
run = sys.argv[1] if len(sys.argv) > 1 else datetime.now().strftime("%H%M%S")
env = dotenv_values(".env")


def cli(*args, body=None):
    r = subprocess.run(["elevenlabs", "agents", "conversations", *args, "--format", "json"],
                       input=json.dumps(body) if body is not None else None,
                       capture_output=True, text=True, timeout=300)
    if r.returncode != 0 or not r.stdout.strip():
        raise SystemExit(f"CLI error ({args[0]}): {r.stderr[:800]} {r.stdout[:800]}")
    return json.loads(r.stdout)


def intervals():
    today = datetime.now(ZoneInfo(env["DEMO_TIMEZONE"])).date()
    r = requests.get(f"https://intervals.icu/api/v1/athlete/{env['INTERVALS_ATHLETE_ID']}/events",
                     params={"oldest": str(today - timedelta(1)), "newest": str(today + timedelta(4)),
                             "fields": "id,name,start_date_local"},
                     auth=("API_KEY", env["INTERVALS_API_KEY"]), timeout=30)
    return [(ev["id"], ev["start_date_local"], ev["name"]) for ev in r.json()]


# 1. Seed, then wait for Jira's search index to catch up (it lags right after creating issues)
seed = subprocess.run([sys.executable, "-W", "ignore", "scripts/seed.py"], capture_output=True, text=True)
print("SEED:", " | ".join(l for l in seed.stdout.splitlines() if l.startswith("[")), seed.stderr[-300:])
jira = f"https://{env['JIRA_SITE'].replace('https://', '').rstrip('/')}/rest/api/3/search/jql"
for _ in range(30):
    issues = requests.post(jira, json={"jql": f"project = {env['JIRA_PROJECT_KEY']} AND labels = alejandro",
                                       "fields": ["status"]},
                           auth=(env["JIRA_EMAIL"], env["JIRA_API_TOKEN"]), timeout=30).json().get("issues", [])
    statuses = sorted(i["fields"]["status"]["name"] for i in issues)
    if statuses == ["In Progress", "To Do", "To Do", "To Do"]:
        break
    time.sleep(2)
print("JIRA SEARCHABLE:", statuses)
print("INTERVALS BEFORE:", *intervals(), sep="\n  ")

# 2. Scripted conversation
cid = cli("create", "--json", "-", body={"agent": {"type": "persisted", "agent_id": AGENT}})["conversation_id"]
print("CONVERSATION:", cid)
for n, text in enumerate(TURNS, 1):
    resp = cli("send_message", "--conversation-id", cid, "--json", "-",
               body={"input": [{"type": "user_message", "content": [{"type": "text", "text": text}]}]})
    json.dump(resp, open(f"{OUT}/run{run}_turn{n}.json", "w"), indent=1)

# 3. Transcript with tool calls and node changes
detail = cli("get", "--conversation-id", cid)
json.dump(detail, open(f"{OUT}/run{run}_conversation.json", "w"), indent=1)
print("\n================ TRANSCRIPT ================")
for m in detail.get("transcript", []):
    node = (m.get("agent_metadata") or {}).get("workflow_node_id") or ""
    if m.get("message"):
        print(f"[{m['role']}{' @' + node[-6:] if node and m['role'] == 'agent' else ''}] {m['message']}")
    for tc in m.get("tool_calls") or []:
        print(f"   -> TOOL CALL {tc.get('tool_name')}: {tc.get('params_as_json')}")
    for tr in m.get("tool_results") or []:
        print(f"   <- TOOL RESULT {tr.get('tool_name')} error={tr.get('is_error')}: {str(tr.get('result_value'))[:200]}")
print("STATUS:", detail.get("status"), "| termination:", (detail.get("metadata") or {}).get("termination_reason"))

# 4. intervals.icu after the run
print("\nINTERVALS AFTER:", *intervals(), sep="\n  ")
