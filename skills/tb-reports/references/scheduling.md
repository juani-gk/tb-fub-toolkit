# Scheduling these reports

These reports are useful once, but the whole point of most of them is
tracking change over time - so offer to schedule a recurring run rather
than treating every request as one-off.

**Environment requirement, check this first:** scheduling only works in a
Claude Code app/web session backed by Anthropic's hosted infrastructure -
that's what actually runs the routine on a timer. A bare local terminal
session has nothing to run it on. Confirm the `RemoteTrigger` tool is
reachable (`ToolSearch` if it's still deferred) before offering to
schedule anything. If it isn't there, say plainly that scheduling isn't
available in this session - don't fall back to a local cron tool and
call it equivalent; it dies with the session and silently stops "recurring."

## How to schedule (the `RemoteTrigger` tool)

Use `RemoteTrigger` with `action: "create"` (and `list`/`get`/`update`/`run`
to manage it afterward). **Never** use local cron tools (`CronCreate` etc.)
for anything meant to recur beyond this session.

Each scheduled firing starts a **fresh session** with no memory of this
conversation, so the body's prompt must be a complete, standalone
instruction: which report, which account context, which time window, and
what to do with the output (e.g. "produce the report and publish it as an
Artifact" - a fresh session needs to be told explicitly, since there's no
"this conversation" to send it back into).

**Cadence is a starting suggestion, never silently applied** - confirm the
actual cadence with the user when setting up each scheduled task, per
report type:

| Report | Suggested default | Why |
|---|---|---|
| Opt-Outs vs. Replies | Weekly | A trend report - daily runs mostly repaint the same sparse window; weekly gives enough new data to be worth a fresh look |
| Message Detail / Template Performance | Weekly or monthly | Per-template volume accumulates slowly on smaller accounts; check the account's actual send rate (shared_pipeline §8) before suggesting - a high-volume account might reasonably want this weekly, a low-volume one monthly |

When proposing a schedule, say the suggested cadence AND why, then let the
user confirm or override - don't just create the trigger with the default
silently baked in.

## What NOT to do
- Don't schedule a report before the user has seen at least one manual run
  and confirmed the format/thresholds/population are right for their
  account - a bad threshold choice repeated daily is worse than one bad
  one-off.
- Don't bake a specific API key into a scheduled task's prompt text in
  plain language asking a fresh session to "use this key" - the fresh
  session will hit the same preflight/configuration step this skill
  documents; let it go through that normally rather than smuggling
  credentials through the trigger prompt.
