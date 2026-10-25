# AI coworkers

The workspace has four AI coworkers. Select a name in the sidebar or a person in the building to open
their direct messages. Each coworker has a role, its own chat history and a position from the building data.
These people and their work are a simulation. Channel posts remain sample content.

`Show coworkers` in the left sidebar controls people in the 3D and floor-plan views. The choice stays in this
browser. Hiding people leaves chats available. Their workday follows elapsed server time, so showing them again
shows their current positions. There are no background model calls.

## State and movement

`building_api/coworkers.py` owns the HTTP interface. A random session token isolates one browser tab's chats for
one building. The browser keeps the token in session storage. Sessions last 24 hours. Messages survive refreshes
and server restarts when the coworker SQLite file is on persistent storage. A server reset that loses this file
also loses sessions and their spend ledger. An expired session requires an explicit new session.

`coworker_movement.py` prepares work locations from the current building's room types. People walk between
reachable spaces, then work at a destination for 65 seconds. Routes use the existing route network. Within each
space, a visibility graph recovers the walking points around concave corners. If geometry cannot provide a
walk, that journey is rejected. Vertical transitions use the building's stairs or lifts. The drawing holds a
person at one floor until the transition completes. This is a small workday simulation, not crowd navigation.
It does not model collisions between people or treat equipment as obstacles.

The server returns timestamped journey points. The browser interpolates only points on the same floor.
The chat's `current_location` tool reads the same workday clock. Its location is a snapshot when the tool runs;
a person can keep walking while a reply is generated. Chat cannot move or stop a coworker.

## Replies and limits

Replies use PydanticAI and the direct Anthropic connection. The agent has the selected coworker's history,
role and read-only tools for the selected building. Evaluation questions and expected answers are not loaded.
There are no file, shell, database query or unrestricted network tools.

| Variable | Default | Purpose |
|---|---|---|
| `ANTHROPIC_API_KEY` | unset | Server-side Anthropic credential |
| `COWORKER_MODEL` | `anthropic:claude-sonnet-5-5` | Reply model |
| `COWORKER_DATABASE` | beside the building database | Separate SQLite session and spend ledger |
| `COWORKER_BUDGET_USD` | `0` | Total reply budget across all sessions in this ledger |

A zero budget or missing key disables replies with an explanation. Movement and stored messages still work.
The preview has a $5 total model budget, including live development checks. Each turn reserves $0.50 before
calling the provider. Measured spend replaces that reservation. An unpriced or interrupted turn retains the
full reservation. A failed run also keeps the full reservation because its last request can have uncertain cost.
A retry uses the same request ID, keeps prior spend and adds no duplicate user message.
After a process stop, a pending attempt can be retried after two minutes. Its full reservation becomes a charge
before the retry reserves a separate allowance. Attempt IDs prevent a late reply from replacing the retry.
Deleting sessions or starting another browser session does not reset the ledger.

Each run has a $0.20 cost limit, preflight input-token checks, at most eight model requests, 900 output tokens
per response and a 60-second timeout. Provider-reported costs arrive after a response, so these are application
limits, not a replacement for provider billing controls. Replies are serialized in each server process. SQLite
reservations also protect the shared budget if multiple workers run. Never reset an uncertain reservation to
make room for another paid call.

Messages are limited to 2,000 characters, conversations to 60 messages per coworker and the preview to 2,000
sessions. Capacity errors are explicit. History is not silently truncated. This preview uses unguessable
session tokens, not human accounts or shared team history. Anyone with its URL can create their own session
and use the configured shared budget.

## Railway preview

Target: project `talk-to-your-building`, environment `coworker-preview`, service `coworker-preview`.
The separate volume mounts at `/data`; `COWORKER_DATABASE=/data/coworkers.sqlite3` keeps the spend ledger.
The service has no GitHub auto-deployment source. Deploy only a committed revision with:

```sh
bash web/deploy/preview.sh
```

The script stages tracked runtime code and `building.json` files only. It excludes evaluation labels and secrets.
It names the preview target explicitly. It does not replace production. Optional `COWORKER_PREVIEW_EVIDENCE`
points to a directory of actual app captures to host under `/preview-evidence/` for the pull request.

Offline checks run with `scripts/check.sh`. Tests replace the provider; they do not prove live model quality.
Separately budget live checks through the same HTTP message path that the browser uses.
