# QA log: golden path

Method: scripted text conversation via the ElevenLabs Conversations API (`conversations create` + `send_message`), 5 fixed user turns, after a fresh `scripts/seed.py`. Transcript (incl. tool calls and node transitions) and intervals.icu read back after each run. Model: DeepSeek Flash (`deepseek-v41-flash`) for Brick and Coach.

| Run | Result | What failed | What changed after |
|---|---|---|---|
| 1 | FAIL | Briefing named the webhook bug but not the release: the Jira integration's default search only returns To Do issues, so the In Progress release never reached Brick. Coach proposed "Friday morning" / "this evening" (vague), then moved the bike to 12:00; also said "I'm the Coach". Everything else passed (transition, refusal, 2 correct moves, intervals.icu, pool follow-up, Brick summary, goodbye + end_call). | Brick: call `jira_search_issues` twice (no status + status "In Progress"); always name a release in progress and every Highest/High issue. Coach: never introduce itself or mention a handover; always give exact times in the proposal. |
| 2 | FAIL | No `end_call` after "Thanks, bye" (Brick said goodbye only). Coach gave an invented reason ("keeps a rest day before the simulation"; Saturday has an easy run). Fixed from run 1: release + bug mentioned, exact times, no self-introduction. | Brick: any goodbye ends the call, end_call in the same turn every time, don't wait on earlier offers. Coach: only give reasons that are true in the plan/playbook. |
| 3 | FAIL | Brick ended the briefing with "Want me to go through the rest of the open issues?" instead of offering the coach. All other criteria passed (incl. end_call). | Brick goal 1: if a workout conflicts with his day, end the briefing by offering the coach and nothing else. |
| 4 | FAIL | Again no `end_call` after "Thanks, bye" (2 of 4 runs), despite the explicit prompt rule. Everything else passed, incl. the coach offer. | Gave the built-in `end_call` tool a description (it was empty): call it in the same turn as the goodbye, even after an earlier question. |
| 5 | FAIL | end_call fixed. But: Coach moved the bike to Friday 18:00 (breaks the explicit "no bike at/after 17:00" hard constraint), said "Let me bring your coach in" (handover talk, explicitly forbidden), and Brick said the release was the only open issue. Root cause of the Jira miss: both searches returned only the release because Jira's search index lags right after seeding (also explains run 1). | Harness: runner now waits until Jira search returns all 4 seeded issues with final statuses before starting. Model: DeepSeek Flash broke a different explicit instruction in runs 2, 3 and 5 with stable prompts, so switched Brick + Coach to Gemini 2.5 Flash, thinking off (pre-approved). No prompt changes in this step, to isolate the model effect. |
| 6 | FAIL | Model change fixed the Coach's rule-following (bike Friday 12:00, no handover talk, rule-based refusal, 2 correct moves) and the briefing passed (release + bug, coach offer). New: Coach said "I'll hand you back to Brick" but never triggered the transition, so Brick didn't summarize and the Coach answered the goodbye. Coach also proposed a move before fetching workouts. | Coach step 1: first turn = summary + list_workouts and google_calendar_list_events; never propose before both results. Step 7: trigger the transition back to Brick in the same turn as the confirmation. |
| 7 | FAIL | Gemini: wrong reasoning ("moving to Friday would be two High days in a row", then proposed Friday). Transition fired before the Coach's confirmation, so Brick voiced it ("I will hand you back to Brick"), with no pool follow-up and no proper summary. Long goodbye. Moves and intervals.icu correct. | Reverted Brick + Coach to DeepSeek Flash: Gemini broke the workflow handoff in 2/2 runs, while DeepSeek handed off correctly in 5/5, and its remaining failures (end_call, Jira) are now fixed. Coach: in a swap each session keeps its own time of day; silent pre-check of each move (bike before 17:00, no appointment overlap, no back-to-back High, no High the day before a Race / Test); explicitly never say "let me bring in your coach". Kept step 1/7 changes from run 6. |
| 8 | PASS | All criteria met. Note: Brick called the webhook fix "Highest priority" (it's High; the release is Highest), a minor factual slip outside the criteria. Conversation `status` reads `failed` in runs 7–9 although it ended normally (termination "Turn completed", successful end_call, no error): looks like a platform status for text conversations closed by end_call. | None (config frozen to test 3 in a row). |
| 9 | FAIL | Outcome fully correct (same swap, 2 correct moves, intervals.icu, pool, handback, Brick summary, short goodbye + end_call). But the Coach walked through the rules aloud and garbled the day logic ("Friday can't carry a High session… so the bike can't go to Friday… the only clean slot is Friday"), and floated a swap before fetching data. 3 in a row no longer reachable within budget. | Coach: don't walk through rules out loud; at most one reason per decision (refusal: key session within seven days of the Race / Test), then the proposal with exact days/times. |
| 10 | PASS | All criteria met. Coach gave one short reason ("can't be skipped or pushed past Saturday", slightly loose but not wrong). Same minor slip as run 8: Brick called the webhook fix "Highest priority". | Budget reached (10 runs); stopped. |

## Round 2 (approved: up to 4 more runs, only change = Jira priority wording)

| Run | Result | Notes | What changed after |
|---|---|---|---|
| — | — | Before run 11: Brick goal 1 now says to name each issue "with its exact priority as Jira reports it". Pushed and verified by read-back. | — |
| 11 | PASS | Priorities correct (release Highest, webhook fix High). Coach: summary first, fetched data before proposing, one reason, swap bike Fri 12:00 / swim Thu 18:00, 2 correct moves, pool follow-up, handback, Brick one-sentence summary, short goodbye + end_call. intervals.icu matches. | None |
| 12 | PASS | Same as run 11; refusal cited the key session within seven days of the race simulation. | None |
| 13 | PASS | Same; Brick also mentioned the Medium/Low items correctly. | None, goal reached |

**Goal reached: 3 passes in a row (runs 11, 12, 13)** on DeepSeek Flash, 13 runs total. The 4th approved run was not needed.

## Round 1 outcome

Not achieved: 3 passes in a row. Final tally: runs 8 and 10 pass, 9 fails (correct outcome, wrong spoken reasoning). The run-9 fix (one reason, no rules walkthrough) was tested once (run 10, pass).

Open issues:
- Brick misstates Jira priorities (called the High webhook fix "Highest" in runs 8 and 10). Not covered by the criteria, but it's a factual error.
- Coach reasoning out loud is the least stable part; the run-10 fix needs more runs to confirm.
- Conversation `status` reads `failed` for normally ended text conversations (runs 7–10); platform-side, not agent behavior.
- The Coach queries the knowledge base via RAG in some runs although the playbook is attached in full (`usage_mode: prompt`); harmless.

Runner: `scripts/qa_golden_path.py`.
