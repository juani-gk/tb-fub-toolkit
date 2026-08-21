# Shared data pipeline

Every report type in this skill pulls from the same three primitives. Don't
reimplement these per report - the differences between report types are in
population, classification, and aggregation, not in how data gets fetched.

**Read this before applying anything specific below.** Every account writes
its own copy - its own greeting style, its own sign-off convention, its own
opt-out phrasing, its own typical message length. Nothing in this file that
looks like a regex, a phrase list, or a number (a character-length flag, a
percentage, a volume floor) is a fixed rule to copy-paste - each is a
**worked example from one real account**, given so you know what *kind* of
pattern to look for without rediscovering the category of problem from
scratch. Before writing any pattern-matching or threshold code:

1. Pull a real sample of this account's actual sent messages (15-20 is
   usually enough to see the shape) and read them.
2. Note what's actually there - does it greet by name? How does it sign
   off, if at all? Does it ever invite an opt-out explicitly, and in what
   words? What's a typical length?
3. Write the regex/phrase-list/threshold to match *that*, using the
   examples below as a template for the kind of pattern, not its literal
   content. If this account's shape genuinely matches the example, great -
   but confirm that from its own messages, don't assume it.

This is the same discipline §8 already applies to volume thresholds,
extended to every other place a pattern or number appears in this file.

## 1. Preflight & auth
Identical to `reply-check` / `fub-api`: risk acknowledgment + API key
configuration (Claude Code: `/plugin configure tb-fub-toolkit`; desktop/web:
edit the skill file directly per that skill's instructions). Call `/identity`
first, always. Never hardcode a limit, an account ID, or a smart-list ID.

## 2. Population - pick the right FUB filter for the report's question

**Ask two things before pulling anything, unless the user's own request
already answers both:**
1. **Time window** - today, this week, this month, custom (`num`/`unit`
   below). **For Performance by Action Plan specifically (report_message_
   detail.md's action-plan drill-down), default to 30 days and always
   compute a second, longer window as well** - offered as a toggle in the
   same report, not a separate run. Slow-cadence automations can look
   almost empty in 30 days while fast ones read best there, so the report
   needs both, always, rather than picking one per account. The long
   window's start date is not a fixed day count - use the earliest send in
   this account that actually carries a non-null `automation_id`/
   `action_plan_id`; going further back than that just adds messages this
   pipeline can't attribute anyway.
2. **Sample or full population?** State the tradeoff in one line: a
   ~300-contact sample (fixed seed) gives a directional read fast and
   cheap; the full population is exact but Message Detail's population is
   *everyone sent to*, which is routinely in the thousands - say that's a
   real time/rate-limit cost before committing to it, per §3's budget
   math. Don't silently pick one; if they already said, e.g., "full
   population for last 30 days," state your understanding and proceed.

| Question the report answers | Filter field | Notes |
|---|---|---|
| Who replied / who do we need to look at | `lastReceivedInboxAppMessage` | Narrower - only contacts who sent something back |
| Who did we contact at all (for per-template volume) | `lastSentInboxAppMessage` | Broader - everyone texted, whether they replied or not. **Use this for Message Detail / template performance** - filtering on received-only silently drops every template that got zero replies, which is exactly the signal a template-performance report needs to show. |

`POST /people/filter?idsOnly=true` with `conditions` as an array of arrays.
`num`/`unit` come from whatever window the report/user asked for - say which
window you used in the output so it's correctable.

## 3. Fetch conversations
`POST https://tb-proxy.vercel.app/api/conversation`, one contact per call,
`{"personid": "<id>"}`, `Authorization: Bearer <key>`. ThreadPoolExecutor
~5-6 workers. Empty `texts` array = no history, not an error. Save a
resumable results file keyed by contact ID in the working directory (not
`/tmp`) - this is what makes batching across hours (below) safe: each batch
skips what's already fetched.

### Budget - read it, never assume it (same rules as `reply-check`)
Every response carries `X-RateLimit-Limit`/`Remaining`/`Cost`. Never
hardcode a ceiling. `contacts_left = Remaining // Cost`.

If the user chose a sample (§2), or the population is small enough that
sample and full are the same thing, just run it - this only matters when
they asked for the full population and it's genuinely large, which for
Message Detail's "everyone sent to" population is the common case, not the
edge case.

**If `contacts_left` is smaller than a full run they asked for, don't
silently downgrade to a sample - plan it out loud, in the reader's terms,
not the machinery's:** compute contacts/hour and how many hours/batches
the full population needs for your own planning only - never say "rate
limit," "budget," or a specific hour count to the user, just that it'll
take a while. Let them choose between a paced batch run over time
(resuming from the results file each time - hands-off via
`RemoteTrigger`'s scheduled routines if the session supports it, see
`references/scheduling.md`'s environment caveat, or hands-on if they'll
prompt you forward) versus a sample right now for a faster directional
read. State plainly that the full run will take a while - never refuse it
outright, and never truncate it silently.

### The date-parsing gotcha (costs real time if you skip this)
Timestamps look like `2026-07-24 14:00:58.961801+00`. The fractional
seconds and the `+00` timezone marker are BOTH after the point where a
naive `.split(".")[0]` would cut - so stripping the fraction first without
handling `+00` separately silently drops the timezone and every downstream
date comparison breaks with no error, just wrong (usually empty) results.

```python
def parse_ts(raw):
    base = raw.split(".")[0].split("+")[0]
    return datetime.datetime.strptime(base + "+0000", "%Y-%m-%d %H:%M:%S%z")
```

## 4. Template identity - strip boilerplate by shape, not by looking up names
**Don't fetch anything extra to normalize a message.** An earlier version
of this pipeline called `GET /people/{id}/summary` per contact to learn
the lead's first name and the currently-assigned agent's name, then
substituted those exact strings out of the message body. Two problems,
found running this for real: it's the second-largest chunk of API calls
in the whole pipeline after the conversation fetches themselves (one extra
request per contact - ~3,700 of them on a real run, with no batch
endpoint to shrink it), and it still misses cases substitution can't
handle - an agent reassigned after the message went out still shows the
name they had *when it was sent*, but the lookup returns whoever is
assigned *now*, so the strings never match and the row doesn't collapse.

Strip boilerplate by its shape instead - none of this needs to know a
specific name in advance. The three *kinds* of boilerplate below showed up
on one real account; sample this account's own messages first (see the
file's opening note) and confirm which of these actually apply here, in
what exact form - a different account might not sign off at all, or
might greet with "Good morning" instead of "Hey," or personalize nowhere
in the body at all, in which case there's nothing to strip for that kind:

- **Leading greeting**, if the account uses one: on the account studied,
  `^(hey|hi|hello)\s+[A-Z][a-z]+[!,.]?\s*` (case-insensitive) caught it -
  greeting word + a capitalized word + punctuation, regardless of whose
  name it is. Check this account's actual greeting words before assuming
  that list is complete.
- **Trailing signature**, if the account uses one: on the account studied,
  everything from the dash that opens a sign-off (`-Alex...`, a hyphen or
  an en/em dash before an assistant persona's name) to the end of the
  message - strip the whole tail, not just the name inside it. A
  different account might sign off with "Best, [name]" or not sign off in
  the body at all.
- **Mid-message agent mentions**, if any: on the account studied, the
  capitalized-name-shaped span immediately after "assistant for" / "for" -
  e.g. "assistant for Jordan Reyes", "for Sam Rivera" - strip the name
  span, keep the rest of the sentence around it. Look for whatever this
  account's actual phrasing is; "assistant for X" is one account's
  convention, not a standard.

Group by `automation_id ?? action_plan_id` first (§6), then by this
stripped core text. This collapses "Hey Priya, ... -Alex for Jordan
Reyes" and "Hey Marcus, ... -Alex for Sam Rivera" into the same row
without ever knowing either lead's or either agent's name - and it keeps
working even when a message shows a since-reassigned agent, which name
substitution structurally cannot handle.

## 5. Drip vs. manual sends
Only count a `direction: "sent"` message as a template/drip occurrence if
it carries a non-null `automation_id` **or** a non-null `action_plan_id` -
either one means something automated sent it. Sends where both are null are
always a person sending manually - either a staff member's own name, or
`created_by: "Embedded App"` (FUB's own embedded messaging sidebar, a
different channel than this toolkit's tagged-note mechanism; the only way a
message gets that value is a human typing it there directly, never an AI or
automated case). Either way these are manual, in-conversation messages -
they belong in a reply/conversation view, not in a per-template send tally,
and mixing them in inflates "Sent" and distorts engagement ratios.

**Don't just drop these silently - tally them by `created_by` value and
state the counts in the report's own caveat text** (e.g. "Embedded App:
119 · Follow Up Boss: 9 · [staff name]: 3"). A silent exclusion invites the
question "did you miss something"; a stated tally answers it before it's
asked.

## 6. Source attribution - the other axis besides wording
Every drip send also carries a source: `automation_id` (an automation sent
it), `action_plan_id` (an action plan step sent it), and `created_by` (its
display name). Capture all three per send, alongside the normalized
template text from §4 - every report in this skill that shows per-template
performance should also be able to roll the same sends up **by source**,
not just by wording (see report_message_detail.md).

Use `automation_id ?? action_plan_id` as the grouping key (stable across a
rename) and `created_by` as the label actually shown - same rule as
`reply-check`. Neither grouping subsumes the other: a single action plan
commonly bundles several distinct message bodies under one label (§4's
example), and less obviously, the same wording can come from more than one
source (cloned or near-identical sequences) - so a template row can have
more than one source, and a source's rollup is a sum across several
different template rows.

## 7. Classification (opt-out / engaged / noise)
```
OPT_OUT_RE = r"\b(stop|unsubscribe|remove|take me off|scratch|do not contact|off your list|blocked|quit|nomore)\b"  (case-insensitive)
NOISE_RE   = r"message not delivered|number no longer in service|not delivered"  (carrier auto-replies - never a real reply)
```
Walk each conversation chronologically. For a per-template attribution
(Message Detail), attribute each inbound message to the most recent
in-window drip send that preceded it. For a simple reply/opt-out count
(Opt-Outs vs. Replies), classify by the message itself, no attribution
needed.

## 8. Thresholds - never hardcode, always check first
Different accounts operate at wildly different volumes. A threshold that
makes a high-volume account's report meaningful (50+ sends, 8+ engaged)
can return an EMPTY report on a smaller account (a real case: the
busiest template topped out at under 20 sends in the same 30-day
window). Before applying any volume/response floor:
1. Compute the actual send-count distribution for the account in hand.
2. If the intended floor would exclude everything (or nearly everything),
   say so plainly and propose a recalibrated floor sized to what the
   account actually does - then confirm with the user rather than
   silently picking a number.
3. State whatever floor you land on, and how many rows/templates it
   excludes (with their combined volume), directly in the report's own
   text - never a silent truncation.

## 9. Sequence position (for the action-plan drill-down)
Where a message sits in a plan's actual delivery order, and the typical
gap since the previous one, is computed from the **whole automation's
run**, not just the report window - a message that's step 6 for most
contacts shouldn't read as "recent" just because the window happens to be
short.

For each contact who received a plan's messages, sort their own sends
chronologically and assign each distinct template an ordinal rank within
that contact's sequence (1st distinct message they got from this plan,
2nd, etc.). Take the **median rank** across all contacts who got that
template as its sequence position, and the **median elapsed time** since
the previous distinct template as the gap ("+27 days", "+1.8 months" -
switch to months past roughly 60 days so the label stays readable).

**Two templates sharing the same median rank means the plan branches
there** - usually a per-agent variant sent at the same point in the
sequence, not a data error. Show both, don't force one into "the" step N.

## 10. Relative-to-group grading (replaces a single global threshold)
Grade each row against **its own group's average**, not a fixed global
number - "high" for a slow, low-volume plan and "high" for the account's
biggest plan aren't the same thing. The group is the action plan for the
drill-down table, and the overall judgeable population for the
by-wording table.

Numbers below worked on one real account and are a **starting point to
recalibrate, not a universal constant** - same discipline as §8. Compute
in this order per row, stopping at the first one that applies:

1. **Not enough volume** - sends below the volume floor OR
   (engaged + opt-outs) below the response floor (§8's floors). Nothing
   else below is trustworthy at this size, so show only this and stop.
2. **No response at all** - sends comfortably above the volume floor
   (a real case used 60+) AND engaged = 0 AND opt-outs = 0. A real,
   informative outcome (it costs nothing and earns nothing), distinct from
   "not enough volume."
3. Otherwise, compare against the group average and assign every label
   that applies (not mutually exclusive - a message can be both costly
   and effective at once), worst news first:
   - **High opt-out** - opt-out rate ≥ 40% above the group average AND
     ≥ 3% absolute (the percentage floor keeps a tiny plan's noise from
     reading as alarming).
   - **More opt-outs than replies** - opt-outs ≥ engaged, on 3+ opt-outs
     (below that, it's noise, not a finding).
   - **Low engagement** - engaged rate ≥ 40% below the group average.
   - **No replies** - engaged = 0 but opt-outs > 0 (distinguish from
     "no response at all," which needs zero of both).
   - **Strong reply rate** - engaged rate ≥ 40% above the group average,
     on 3+ engaged.
   - **Zero opt-outs** - sends above a volume floor (a real case used
     40+) AND opt-outs = 0.
   - **In line with the group** - none of the above triggered; the
     neutral case, still worth a pill so an unlabeled row doesn't read as
     an oversight.

## 11. Content-aware narrative notes
One line per flagged row (skip it for "in line with the group" rows),
built from whichever of these actually apply - chain them into 1-3
sentences, don't force ones that don't apply. **The specific phrases and
the length number below are what one account's messages looked like, not
a checklist to run unmodified** - the underlying features (does it invite
an opt-out, does it ask a question, is it unusually long *for this
account's normal style*) are the reusable part; what counts as "long" or
what an opt-out invitation sounds like is account-specific and worth
confirming against a real sample first, same as §4.

- **Rate vs. group average**, when a rate label triggered: state both
  numbers ("Pulls replies well above the plan average (9.1% vs 2.1%)").
- **Losing trade**, when opt-outs ≥ engaged: "It loses N contacts to earn
  M replies, so the trade runs the wrong way."
- **Explicit opt-out invitation present** in the sent message itself -
  checking the *outbound* text for the account's own opt-out instruction
  wording (reuse whatever §7's `OPT_OUT_RE` already resolved to for this
  account, since that's the same vocabulary a lead would be told to reply
  with - "reply nomore," "say NOMORE," "I'll stop texting" is what one
  account used, confirm this account's own phrasing rather than assuming
  it): "It hands the reader an explicit exit line, which lifts both
  replies and opt-outs."
- **No question asked** - message doesn't end in `?` near its close:
  "It asks nothing, so there is no reason for the reader to type back."
- **Runs long** - message length comfortably past what's normal *for this
  account's other messages* (a real case flagged anything past ~300
  characters, but that account's typical message ran under 200 - compare
  against this account's own distribution, don't reuse 300 as a constant):
  "At N characters it runs long for a check-in text."
- **First touch** - this is the plan's sequence position 1 (§9): "First
  contact in the plan, where opt-outs naturally cluster."
- **Volume caveat**, for "not enough volume" rows: "Only N sends and M
  responses in this window, too little to read anything into."
- **Dead caveat**, for "no response at all" rows: "N sends and not one
  reply or opt-out came back. It costs nothing and earns nothing, which
  is its own verdict."

## Known gotchas checklist (re-check each new report type against this)
- [ ] Sampled this account's own sent messages before writing any
      pattern-matching regex or picking any content-feature threshold -
      never applied another account's greeting/signature/length example
      unmodified (file intro, §4, §11)
- [ ] Asked (or confirmed an already-stated answer for) time window AND
      sample-vs-full before pulling anything (§2)
- [ ] Used the right population filter for the report's actual question (§2)
- [ ] If full was chosen and the segment is large, planned the batching
      out loud instead of silently sampling or truncating (§3)
- [ ] Parsed timestamps with the split-then-append-timezone method (§3)
- [ ] Normalized template text by stripping boilerplate by shape, not by
      fetching per-contact/agent names to substitute (§4)
- [ ] Excluded sends where both `automation_id` and `action_plan_id` are
      null from any per-template or per-source tally (§5)
- [ ] Captured `automation_id`/`action_plan_id`/`created_by` per send so a
      source rollup is possible, not just a template rollup (§6)
- [ ] Excluded carrier noise from reply/engagement counts (§7)
- [ ] Checked the real volume distribution before applying any threshold (§8)
- [ ] For the action-plan drill-down: computed sequence position/gap from
      the whole automation's run, not just the window (§9)
- [ ] Graded rows against their own group's average, not a fixed global
      number, with volume/dead-case checks run first (§10)
- [ ] Every flagged row's note only states what actually applies - no
      forced sentences for conditions that didn't trigger (§11)
