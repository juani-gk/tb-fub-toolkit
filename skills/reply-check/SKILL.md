---
name: "reply-check"
description: "Pull and analyze Texting Betty campaign replies from FUB, classify them (opt-outs, declines, warm leads, booking threads), and surface action items. Finds the leads by filtering Follow Up Boss on recent Texting Betty activity over whatever time window the user asked for, falling back to smart lists or tags. Use whenever the user says \"who replied today\", \"any responses today\", \"did anyone answer\", \"check my texts\", \"check in on my leads\", \"who opted out\", \"any hot leads\", \"analyze today's responses\", \"check the replies\", \"pull the replied list\", \"check a smart list\", or wants a reply summary."
---

# Reply Check

## Preflight - do this before any API call

**Two configured values: `${user_config.risk_acknowledged}` and `${user_config.fub_api_key}`.**

### Which environment are you in?

`${user_config.…}` placeholders are filled in automatically **only in Claude
Code**. The desktop and web apps have no plugin configuration panel, so there
the placeholders stay literal and must be replaced by hand.

Tell the two cases apart by what you can see:

| What you observe | Where you are | What to do |
|---|---|---|
| Values are real | Configured already | Continue |
| Values read literally as `${user_config.…}` **and** you have a `/plugin` command | Claude Code, unconfigured | Ask the user to run `/plugin configure tb-fub-toolkit` |
| Values read literally **and** there is no `/plugin` command | Desktop or web app | Fill them in directly - see below |

### Filling them in on desktop or web

There is nothing to configure in the UI, so the values go into this skill file.
Do this only when the user asks for something that needs them - never
preemptively.

**First, the acknowledgement.** Show the user this, in full, and wait for an
explicit yes:

> This tool is driven by AI, and AI gets things wrong. It can misread your
> data, miscount, or state something confidently that is not true. It acts on
> your live Follow Up Boss account and can send real text messages that cannot
> be unsent, carrying TCPA and Do-Not-Call obligations that remain entirely
> yours. Treat what it reports as a draft to verify, not as fact.
>
> Do you understand and accept that?

A vague "sure" is not a yes. If they do not clearly accept, stop.

**Then the key.** Ask for their Follow Up Boss API key (Admin → API in FUB),
and edit **this file**, replacing every occurrence of
`${user_config.fub_api_key}` with the literal key and
`${user_config.risk_acknowledged}` with `true`. Change nothing else - not the
logic, not the warnings, not the proxy URL.

Say plainly what this means before doing it:

- The key will sit **in plain text inside the plugin's files**.
- It **does not survive a plugin update** - the files are replaced and it has
  to be entered again.
- On the web app the files reset between sessions, so it is per-session there.

In Claude Code, never do this. Use `/plugin configure`, which stores the value
properly instead of writing it into a file.

**First-time setup only:** once the acknowledgment and key are both saved
this way for the first time this session, mention in one line that
`tb-overview` covers the full menu of what this toolkit can do, before
moving on to whatever task prompted the setup - someone who just finished
configuring is exactly who that's for. Skip this if the values were already
real when checked (not a first-time setup).

Never invent a credential, and never send a request containing a literal
`${user_config.…}` string. A **401/403 means stop, not retry.**

**Call `GET /identity` first** to derive the account ID and subdomain. Never
ask the user for them - see the `fub-api` skill.

`curl` is blocked here - use Python `urllib` with
`ssl.create_default_context(cafile="/etc/ssl/cert.pem")`. See the `fub-api`
skill for the canonical `http()` helper.

**Never send `X-System: fub-spa`** - it impersonates FUB's own web app and
can get the account flagged. Send `X-System`/`X-System-Key` only if FUB
issued you an integration identifier; otherwise send neither.

This skill reads contact data only; it never sends messages. If the task
turns into actually texting someone - not just reporting on replies -
invoke the `tb-send-text` skill for that. Don't improvise a `/notes` call
here.

## Talking to the user

Your reader is a **real estate agent or team lead**, not a developer. They want
to know what is happening with their leads and their campaigns. Everything else
in this skill - endpoints, auth, account IDs, status codes - is machinery they
neither know about nor need to.

**Never say, in user-facing output:** proxy, endpoint, API, request, payload,
HTTP status code, `/identity`, account ID, Basic/Bearer, rate limit, cloud
function, or the name of any config field. Do not narrate the plumbing
("calling /identity to derive the account, then querying smart lists…") - just
do it and report what you found.

When something fails, say what it means for them and what they can do about it:

| What actually happened | What you tell them |
|---|---|
| 401 from FUB | "I can't get into your Follow Up Boss account - the key may have been reset. You can update it in the plugin settings." |
| 403, account not registered | "This Follow Up Boss account isn't set up for Texting Betty yet. Support can enable it." |
| 502 / timeout | "Texting Betty isn't responding right now - worth trying again in a few minutes." |
| 429 rate limited | "I've pulled as many conversations as I can this hour. Here's what I found so far - I can finish the rest in about N minutes." |
| Every request fails with no response at all, not a FUB error | "I can't reach Follow Up Boss at all right now - this looks like a network permission issue on this Claude account, not something wrong with your FUB account. If you're on a team plan, your workspace admin needs to allow access; otherwise it's in your own Claude network settings." |
| Empty conversation | "No text history with this contact yet." |
| Nothing configured | "I need your Follow Up Boss API key first - you can paste it in the plugin settings." |

Never show a raw error body, a stack trace, or a JSON blob unless they ask to
see it. If you truly cannot proceed, say so plainly in one sentence and stop -
do not improvise a workaround or ask them for a credential this toolkit does
not use.

Write in their vocabulary: leads, replies, opt-outs, conversations,
appointments. Not records, rows, objects, or collections.


Pull replies for Texting Betty campaigns from the FUB account, fetch the full SMS conversations from the Texting Betty proxy, classify every reply, and report hot leads, dropped balls, and compliance flags.

## Endpoints

| What | Value |
|---|---|
| FUB API key | `${user_config.fub_api_key}` (Basic auth: base64 of `key:`) |
| FUB base | `https://api.followupboss.com/v1` |
| Conversations | `POST https://tb-proxy.vercel.app/api/conversation` |
| Conversations auth | `Bearer ${user_config.fub_api_key}` - the same key, as Bearer |

Note the scheme change: FUB wants **Basic**, the proxy wants **Bearer**, and
both carry the same API key. Getting this backwards produces a 401 from
whichever side you sent the wrong form to.

## How the conversation proxy works

You send a contact ID and your API key. Nothing else. The proxy resolves the
rest:

```
you   → proxy    Bearer <FUB api key>, { "personid": "12345" }
proxy → FUB      GET /identity  → which account is this key?
proxy            look that account up in the client registry
proxy → TB       the conversation store, using the routing key on file
```

**There is no owner email to configure, and none to pass - never ask the
user for one.** Texting Betty partitions conversations by a routing address
that is *not* the FUB account owner and not the key's own user; it's
resolved server-side from your API key.

**An empty `texts` array means exactly that: this contact has no messages.**
Do not report it as "probably a config problem."

You get the **whole** conversation for that lead, across every one of the
team's numbers, merged and in order. You do not need to ask for anything else
or worry about which number was used.

Each message also carries what sent it: `created_by` (a name - an
automation's name, an action plan's name, or a team member's name),
`automation_id`, and `action_plan_id`. Use this to say *what* is driving a
reply, not just that a reply happened - "the DCM 10 Days automation" is worth
more to a team lead than "an automation."

- Both IDs null on a `sent` message → always a person, sent manually. Use
  `created_by` as their name, including `"Embedded App"`, which is not an
  AI or automated case: it's FUB's own embedded messaging sidebar, a
  different channel than the tagged-note mechanism this toolkit sends
  through, and the only way a message gets that value is a human typing it
  there directly.
- Both IDs null on a `received` message → normal; that's just the lead's own
  reply, nothing sent it.
- `automation_id` set → an automation sent it. `action_plan_id` set → an
  action plan step sent it. Treat the ID as the grouping key (names can be
  renamed or reused later) but always **report the name**, never the raw ID -
  the reader doesn't know or care what number a campaign is.

Responses:

| Status | Meaning | What to do |
|---|---|---|
| 200 | OK - `{"texts": [...]}` | Continue. Empty array = no messages |
| 401 | FUB rejected the key | Stop. Ask the user to check their API key |
| 403 | Valid key, account not registered | Stop. This account has no Texting Betty subscription |
| 429 | Too many lookups this hour | **Stop the sweep.** See below |
| 502 | Upstream failure | Retry once, then report |

**On 429, stop - do not retry in a loop.** There is an hourly cap per account,
and the response carries `Retry-After` (seconds) plus how many lookups were
used. Hammering it wastes the remaining budget and delays the reset.

Keep whatever you already fetched, report on that partial set, say plainly that
it is partial, and tell the user roughly when they can run the rest. If you are
close to the cap before starting a large sweep, sample instead of fetching
everything - a 300-contact sample answers the same question as 900.

### Budget: read it, never assume it

Every response carries the numbers. **Never hardcode a limit in this skill -
the server owns it and it changes without this file changing.**

| Header | Meaning |
|---|---|
| `X-RateLimit-Limit` | The ceiling for this account |
| `X-RateLimit-Remaining` | What is left |
| `X-RateLimit-Cost` | What **one contact** spends on this account |

**`Remaining` is not a count of contacts.** The budget is measured in upstream
work, and one contact can cost more than one unit. To know how many contacts
you can still do:

```
contacts_left = Remaining // Cost
```

Read this after the first fetch, before committing to a large sweep.

**If the user asked for a sample (§0 below), or the segment is small enough
that full and sample are the same thing, just run it.** The budget math
below only matters when they asked for the *full* population and it's
genuinely large.

**If `contacts_left` is smaller than a full run they asked for, don't
silently downgrade to a sample - plan it out loud instead, in the reader's
terms, not the machinery's:**
1. Compute the real numbers for your own planning: contacts per hour at
   this account's rate (from `Cost`/`Remaining`, paced per the sleep
   guidance above), and how many hours/batches the full population needs.
   This math is yours to do silently - never say "rate limit," "budget,"
   a specific hour count, or anything that reveals *why* it takes time.
2. Say the plan plainly in plain terms: e.g. "Going through everyone will
   take a while, so I'd do it in stages over the day, picking up where I
   left off each time - or I can give you a quick read from a sample right
   now instead. Which would you rather?" Let them choose; don't pick for
   them, and don't attach a number of hours to the estimate - "a while" /
   "over the day" is accurate enough and doesn't invite a promise you
   can't actually guarantee if the pace changes mid-run.
3. If they want the full run spread over time, the resumable results file
   (§2 below) is what makes batching safe - each batch skips what's already
   done. Continue within the session if they're willing to prompt you
   forward each hour; if the session supports scheduled routines
   (`RemoteTrigger` - see `tb-reports`' scheduling reference for the
   mechanics and its environment caveat), offer that as the hands-off
   version instead of making them babysit it.
4. **Say plainly that the full run will take real time before starting it.**
   Never refuse a full run just because it's slow - slow-but-complete and
   fast-but-partial are both legitimate, the user picks which.

Slow down as `Remaining` drops instead of discovering the ceiling at zero.

---

## Workflow

### 0. Ask two things before pulling anything

Unless the user's own request already answers both, ask before running
Path A/B/C:

1. **Time window** - today, this week, this month, custom. (`num`/`unit`
   below.)
2. **Sample or full population?** State the tradeoff in one line: a
   ~300-contact sample (fixed seed, for reproducibility) answers "roughly
   what's happening" fast and cheap; the full population is exact but costs
   real time and rate-limit budget once the segment is large - see the
   Budget section if that turns out to be the case.

If they already said e.g. "check today's replies, sample is fine" or "full
population for this week," don't re-ask - state your understanding and
proceed. The point is never leaving either choice silently assumed, not
interrupting someone who already answered it.

### 1. Find the leads to analyse

**Path A - filter on Texting Betty activity. Do this first.**

```
POST /people/filter?idsOnly=true
```
```json
{"conditions":[[{"fld":"lastReceivedInboxAppMessage","opr":"was less than","num":"2","unit":"days","val":[]}]]}
```

This asks the question directly - *who received a Texting Betty message in the
last N days* - instead of hoping the account happens to have a list or tag that
approximates it. It works on any account, needs nothing set up in advance, and
`lastReceivedInboxAppMessage` targets inbox-app messages specifically, which is
what Texting Betty sends.

Two things to get right:

- **`conditions` is an array of arrays.** The nesting is required; a flat array
  is rejected.
- **`num` comes from what the user asked for.** "Today" is `1`, "the last
  couple of days" is `2`, "this week" is `7`. Say which window you used when
  you report, so they can correct you if they meant something else.

**Always send `idsOnly=true`, on whichever path you take.** The analysis needs
an ID and nothing else - the conversation comes from the proxy, not from the
person record. Pulling full objects for hundreds of leads spends response time,
rate-limit budget and context window on data you discard immediately.

If you later need a name or phone for the report, fetch those few contacts
individually. One call per lead you actually mention beats hundreds you don't.

**Path B - by smart list (fallback).**

```python
lists = {l["name"].lower(): l["id"] for l in get("/smartLists?limit=100")["smartlists"]}
list_id = next((i for n, i in lists.items() if "replied" in n), None)
```

If one matches: `GET /people?limit=100&offset=0&smartListId=<discovered id>&idsOnly=true`

**Never hardcode a smart list ID.** IDs are per-account: a number that works in
one tenant silently selects a different list - or a nonexistent one - in
another.

**Path C - by Texting Betty tag (fallback).**

Many accounts have no "replied" list at all; the TB-touched segment is
identified by tag instead. Discover the tag name from the `tags` array
embedded on person objects you already have (from Path A/B results, or a
sample `/people` call), or ask the user for the exact tag name. Pull the
segment with `GET /people?tags=<tag name>&idsOnly=true`.

### Which path measures what

These are not interchangeable, and saying which one you used matters:

| Path | Population |
|---|---|
| A - filter | Everyone who **received** a TB message in the window |
| B - replied list | Everyone who **answered**, per that account's own definition |
| C - unsubscribe tag | **Only opt-outs** |

Path C especially: the opt-out rate from an opt-out tag is 100% by
construction and means nothing. If you fall back to it, say so in the report
rather than presenting the number as a campaign metric.

**If no path finds anything**, stop and show the user what smart lists and
TB-related tags do exist, and ask which segment to analyse. Do not invent an ID
and do not silently analyse the wrong population.

Important quirk: with `idsOnly=true` FUB returns ALL matching IDs in one response as `{"ids": [...]}` and ignores pagination. Do not loop offsets (you will duplicate the full set each page).

### 2. Fetch conversations

For each contact, POST to the proxy. One contact per call - it does not accept batches.

```python
status, body = http(
    "https://tb-proxy.vercel.app/api/conversation",
    {"Authorization": "Bearer ${user_config.fub_api_key}",
     "Content-Type": "application/json"},
    data=json.dumps({"personid": str(pid)}).encode(),
    method="POST",
)
texts = (body or {}).get("texts", [])
```

Response: `{"texts": [{"direction": "sent"|"received", "body": ..., "t": "<timestamp>", "created_by": ..., "automation_id": ..., "action_plan_id": ..., ...}]}`.

Practical mechanics learned the hard way:
- Use a ThreadPoolExecutor with ~10 workers; each call takes 1-2s.
- If *every* contact in a segment comes back empty, suspect the segment (wrong list or tag), not the credentials.
- Keep a resumable results file keyed by `personid` so reruns skip completed fetches. **Write it to the working directory - `/tmp` is not writable here.**
- The 45-second cap is a sandbox limit, not a TB one. Where it applies, batch at most ~130 fetches per invocation; running directly on a workstation, no chunking is needed.
- If the user chose a sample (§0), draw ~300 with a fixed seed for
  reproducibility. If they chose full and the segment is large, see the
  Budget section above for the batching plan - don't quietly substitute a
  sample for a full run they specifically asked for.

### 3. Classify

Sort each conversation by timestamp. Split inbound vs outbound. Classify by the last inbound message:

- **Opt-out**: matches `stop|unsubscribe|remove|take me off|scratch|do not contact|off your list|blocked|quit|nomore` (case-insensitive; "Quit" matters because some drips invite "just say quit", and "nomore" because some drips train the lead to reply that exact word).
- **Warm**: matches `tell me more|hear more|interested|more info|sounds good|call me|let's talk|open to|availability|what time|works for me|quick chat`, or the contact proposed a time, asked for pricing/details/eligibility, or shared an email address.
- **Booking thread**: outbound side contains `reminder for your call|will reach out|a team member will|call at <hour>|how did the call go`.
- **Dialogue**: 2+ inbound messages.
- Everything else is a polite decline or noise.

**Attribution - what drove this reply.** For the classified inbound message,
take the outbound message immediately before it in the sorted conversation
(last-touch, at the message level - you're reading individual texts, not
building a conversation-level model). That outbound message's
`created_by`/`automation_id`/`action_plan_id` is the source to attribute the
reply to. If there's no prior outbound in the fetched window, there's nothing
to attribute - say so rather than guessing.

Also detect, in inbound text, compliance and quality flags: `tcpa|dnc|do not call registry|lawsuit|report|scam|spam|harass|relentless|blocking`, wrong-number claims, out-of-scope or unqualified-lead replies (list hygiene misses), and "are you a bot" detections.

### 4. Report

Structure the report exactly like this:

1. Headline: total replies, opt-out count and share, notable events, and -
   if any Needs Action items exist - how long the oldest one has been
   waiting.
2. **Needs action today**: every warm thread where the last message is
   inbound (the AI or a human owes a reply), any booked call needing
   confirmation, any AI promise that requires human follow-through (e.g.
   "I'll email you..." - verify something actually sends it), any
   scheduling mismatch (lead proposed a time, AI proposed a different
   one). For each item: tag which of those three patterns it is, show
   time since the last inbound message ("3d 4h", not a raw timestamp),
   and the assigned agent if available (routes it to the right person).
   **Sort by staleness, oldest-waiting first** - a lead who's been
   hanging for days is more urgent than one from an hour ago, regardless
   of contact ID or alphabetical order.
3. **Watch/nurture**: promised callbacks, "check back later" agreements.
4. **Flags**: compliance complaints (treat DNC/TCPA as urgent), bot
   detections, list hygiene misses. **If any exist, surface them right
   after the headline, before the action list** - a DNC/TCPA complaint
   buried under ordinary warm leads is a mistake.
5. **Source breakdown** - include this when the ask is a comparison ("which
   automation is causing opt-outs", "which action plan performs better") or
   when opt-outs cluster heavily under one source; otherwise leave it out of
   a plain daily check-in. Group by the source name from Attribution above
   (automation, action plan, or person), and show opt-out share and
   warm/booking share per source. **Say plainly that this is share of
   repliers, not a conversion rate** - a real rate needs how many that source
   *sent* to, which isn't in this payload. Don't imply "60% opt-out" means 6
   of 10 people it texted opted out when it actually means 6 of 10 people who
   *replied* did.

Include FUB contact IDs so a human can jump to `https://<account.domain>.followupboss.com/2/people/view/{id}` - take `account.domain` from the `/identity` call you already made.

### Optional: a shareable report, on request only

**Chat is the default output, always.** This report is inherently
time-sensitive - "who needs a reply right now" - and its value comes
from jumping straight from the list into a FUB link mid-conversation.
Don't build the report below unless the user explicitly asks for
something shareable or persistent (e.g. "can I share this with my team,"
"give me a page for this," "something I can send to the office").

**After delivering the plain-text chat report, offer this as a one-line
question every time** - "Want this as a shareable page too?" - rather
than waiting for someone to already know the option exists. Ask once,
after the answer, not before it; don't hold up the actual chat report to
ask first.

When they do: use `../tb-reports/assets/reply_check_shell.html` (same
design system as `tb-reports`, same `%%PLACEHOLDER%%` + fragment-only +
`Artifact`-publish rules documented in `tb-reports/SKILL.md` - read that
before filling this one in). Map this section's structure directly:
headline KPIs, the Flags card (omit entirely if there are none - never
show an empty one), the Needs Action table, Watch/nurture, and the
optional Source breakdown, same inclusion rule as item 5 above.

**State the "as of" time prominently** - the shell has a placeholder for
this specifically. A persisted page showing today's action list is
exactly the kind of thing that misleads if reopened tomorrow and treated
as current; the timestamp is not decorative here.

### Diffing runs

When the user asks to "check again" the same day, keep the previous ID snapshot and report only NEW repliers since the last pull, plus status changes on previously flagged threads.

## Known analysis principles

- Opt-outs among repliers of roughly 30-40% is common for cold outbound SMS campaigns; a share much higher than that usually signals a burned list or overly aggressive copy.
- The most valuable output is the action list, not the counts. Conversion problems (unanswered warm leads, missed handoffs) lose more opportunities than copy problems.
- Bare instant "Stop" replies clustered on day one of a wave usually mean the contacts recognize a prior campaign (burned relaunch).
- If the same source name appears to send from what look like two different
  automations/action plans (or the name itself seems to have changed
  mid-window), say so rather than quietly merging or splitting the count -
  that's a renamed or duplicated campaign, and the report should flag it
  rather than guess which bucket is "correct."
