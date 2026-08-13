---
name: "reply-check"
description: "Pull and analyze Texting Betty campaign replies from FUB, classify them (opt-outs, declines, warm leads, booking threads), and surface action items. Finds the target segment by discovering smart lists by name, or by Texting Betty tag when the account has no replied list. Use whenever the user says \"analyze today's responses\", \"check the replies\", \"who replied today\", \"pull the replied list\", \"check a smart list\", or wants a reply summary."
---

# Reply Check

## Preflight — do this before any API call

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
| Values read literally **and** there is no `/plugin` command | Desktop or web app | Fill them in directly — see below |

### Filling them in on desktop or web

There is nothing to configure in the UI, so the values go into this skill file.
Do this only when the user asks for something that needs them — never
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
`${user_config.risk_acknowledged}` with `true`. Change nothing else — not the
logic, not the warnings, not the proxy URL.

Say plainly what this means before doing it:

- The key will sit **in plain text inside the plugin's files**.
- It **does not survive a plugin update** — the files are replaced and it has
  to be entered again.
- On the web app the files reset between sessions, so it is per-session there.

In Claude Code, never do this. Use `/plugin configure`, which stores the value
properly instead of writing it into a file.

Never invent a credential, and never send a request containing a literal
`${user_config.…}` string. A **401/403 means stop, not retry.**

**Call `GET /identity` first** to derive the account ID and subdomain. Never
ask the user for them — see the `fub-api` skill.

`curl` is blocked here — use Python `urllib` with
`ssl.create_default_context(cafile="/etc/ssl/cert.pem")`. See the `fub-api`
skill for the canonical `http()` helper.

**Never send `X-System: fub-spa`** — it impersonates FUB's own web app and
can get the account flagged. Send `X-System`/`X-System-Key` only if FUB
issued you an integration identifier; otherwise send neither.

This skill reads contact data only; it never sends messages.

## Talking to the user

Your reader is a **real estate agent or team lead**, not a developer. They want
to know what is happening with their leads and their campaigns. Everything else
in this skill — endpoints, auth, account IDs, status codes — is machinery they
neither know about nor need to.

**Never say, in user-facing output:** proxy, endpoint, API, request, payload,
HTTP status code, `/identity`, account ID, Basic/Bearer, rate limit, cloud
function, or the name of any config field. Do not narrate the plumbing
("calling /identity to derive the account, then querying smart lists…") — just
do it and report what you found.

When something fails, say what it means for them and what they can do about it:

| What actually happened | What you tell them |
|---|---|
| 401 from FUB | "I can't get into your Follow Up Boss account — the key may have been reset. You can update it in the plugin settings." |
| 403, account not registered | "This Follow Up Boss account isn't set up for Texting Betty yet. Support can enable it." |
| 502 / timeout | "Texting Betty isn't responding right now — worth trying again in a few minutes." |
| 429 rate limited | "I've pulled as many conversations as I can this hour. Here's what I found so far — I can finish the rest in about N minutes." |
| Empty conversation | "No text history with this contact yet." |
| Nothing configured | "I need your Follow Up Boss API key first — you can paste it in the plugin settings." |

Never show a raw error body, a stack trace, or a JSON blob unless they ask to
see it. If you truly cannot proceed, say so plainly in one sentence and stop —
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
| Conversations auth | `Bearer ${user_config.fub_api_key}` — the same key, as Bearer |

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

**There is no owner email to configure, and none to pass.** Texting Betty
partitions conversations by a routing address that is *not* the FUB account
owner and not the key's own user — in a multi-user account only one specific
address works. That value is resolved once at signup and stored server-side.

This matters for how you read results: **an empty `texts` array now means
what it says — that contact has no messages.** In earlier versions an empty
array usually meant a misconfigured owner email, and the skill told you to
suspect the config first. That failure mode no longer exists; do not report
"probably a config problem" when a contact legitimately has no history.

> ⚠️ **A conversation may be incomplete, and you cannot tell.**
>
> Texting Betty stores messages against the owner of the phone number they were
> sent to — not against the lead or the account. This skill retrieves one
> owner's slice. If a lead was contacted from more than one of the team's
> numbers, you are seeing part of the thread, with no marker that anything is
> missing.
>
> That changes what you can safely conclude. A thread that looks unanswered may
> already have been handled by a teammate from a different number; an opt-out
> that looks unprocessed may already be processed. **When you report that
> something is waiting on a reply, say it should be confirmed in Follow Up Boss
> before anyone acts on it.** Never present "nobody responded" as established
> fact.

Proxy responses:

| Status | Meaning | What to do |
|---|---|---|
| 200 | OK — `{"texts": [...]}` | Continue. Empty array = no messages |
| 401 | FUB rejected the key | Stop. Ask the user to check their API key |
| 403 | Valid key, account not registered | Stop. This account has no Texting Betty subscription |
| 429 | Too many lookups this hour | **Stop the sweep.** See below |
| 502 | Upstream failure | Retry once, then report |

**On 429, stop — do not retry in a loop.** There is an hourly cap per account,
and the response carries `Retry-After` (seconds) plus how many lookups were
used. Hammering it wastes the remaining budget and delays the reset.

Keep whatever you already fetched, report on that partial set, say plainly that
it is partial, and tell the user roughly when they can run the rest. If you are
close to the cap before starting a large sweep, sample instead of fetching
everything — a 300-contact sample answers the same question as 900.

The `X-RateLimit-Remaining` header comes back on every response. Read it and
slow down as it drops rather than discovering the wall at zero.

---

## Workflow

### 1. Find the target segment

**Never hardcode a smart list ID.** IDs are per-account, and a number that
works in one tenant silently selects a different list — or a nonexistent
one — in another. There are two paths; try them in order.

**Path A — by smart list (preferred when one exists):**

```python
lists = {l["name"].lower(): l["id"] for l in get("/smartLists?limit=100")["smartlists"]}
list_id = next((i for n, i in lists.items() if "replied" in n), None)
```

If a list matches, pull its contacts:

```
GET /people?limit=100&offset=0&smartListId=<discovered id>&idsOnly=true
```

**Path B — by Texting Betty tag (when no list matches):**

Many accounts have **no "replied" list at all** — the TB-touched segment is
identified by tag instead. This is common, not an edge case. Check tags
before reporting that there is nothing to analyze:

```python
tags = [t for t in get("/tags?limit=2000")["tags"] if "texting" in t["name"].lower()]
```

TB tags encode conversation state — engagement and unsubscribe are the
usual ones, and their `peopleCount` tells you the segment size before you
fetch anything. Pull contacts with `GET /people?tags=<tag name>&idsOnly=true`.

Note what each path measures: a *replied* list is everyone who answered,
while an *unsubscribe* tag is only the opt-out subset. If you analyze a tag
segment, say so in the report — the opt-out rate from an opt-out tag is
100% by construction and means nothing.

**If neither path finds anything**, stop and show the user the smart lists
and TB-related tags that do exist, and ask which segment to analyze. Do not
invent an ID and do not silently analyze the wrong population.

Important quirk: with `idsOnly=true` FUB returns ALL matching IDs in one response as `{"ids": [...]}` and ignores pagination. Do not loop offsets (you will duplicate the full set each page).

### 2. Fetch conversations

For each contact, POST to the proxy. One contact per call — it does not accept batches.

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

Response: `{"texts": [{"direction": "sent"|"received", "body": ..., "t": "<timestamp>", ...}]}`.

Practical mechanics learned the hard way:
- Use a ThreadPoolExecutor with ~10 workers; each call takes 1-2s.
- **An empty `texts` array means that contact has no messages.** This is now a real answer, not a symptom of misconfiguration — the routing key comes from the server, so it cannot be wrong. If *every* contact in a segment comes back empty, suspect the segment (wrong list or tag), not the credentials.
- Keep a resumable results file keyed by `personid` so reruns skip completed fetches. **Write it to the working directory — `/tmp` is not writable here.**
- The 45-second cap is a sandbox limit, not a TB one. Where it applies, batch at most ~130 fetches per invocation; running directly on a workstation, no chunking is needed.
- For a large segment (300+), analyze a random sample of ~300 with a fixed seed for reproducibility instead of fetching everything.

### 3. Classify

Sort each conversation by timestamp. Split inbound vs outbound. Classify by the last inbound message:

- **Opt-out**: matches `stop|unsubscribe|remove|take me off|scratch|do not contact|off your list|blocked|quit` (case-insensitive; "Quit" matters because some drips invite "just say quit").
- **Warm**: matches `tell me more|hear more|interested|more info|sounds good|call me|let's talk|open to|availability|what time|works for me|quick chat`, or the contact proposed a time, asked for pricing/details/eligibility, or shared an email address.
- **Booking thread**: outbound side contains `reminder for your call|will reach out|a team member will|call at <hour>|how did the call go`.
- **Dialogue**: 2+ inbound messages.
- Everything else is a polite decline or noise.

Also detect, in inbound text, compliance and quality flags: `tcpa|dnc|do not call registry|lawsuit|report|scam|spam|harass|relentless|blocking`, wrong-number claims, out-of-scope or unqualified-lead replies (list hygiene misses), and "are you a bot" detections.

### 4. Report

Structure the report exactly like this:

1. Headline: total replies, opt-out count and share, notable events.
2. **Needs action today**: every warm thread where the last message is inbound (the AI or a human owes a reply), any booked call needing confirmation, any AI promise that requires human follow-through (e.g. "I'll email you..." — verify something actually sends it), any scheduling mismatch (lead proposed a time, AI proposed a different one).
3. **Watch/nurture**: promised callbacks, "check back later" agreements.
4. **Flags**: compliance complaints (treat DNC/TCPA as urgent), bot detections, list hygiene misses.

Include FUB contact IDs so a human can jump to `https://<account.domain>.followupboss.com/2/people/view/{id}` — take `account.domain` from the `/identity` call you already made.

### Diffing runs

When the user asks to "check again" the same day, keep the previous ID snapshot and report only NEW repliers since the last pull, plus status changes on previously flagged threads.

## Known analysis principles

- Opt-outs among repliers of roughly 30-40% is common for cold outbound SMS campaigns; a share much higher than that usually signals a burned list or overly aggressive copy.
- The most valuable output is the action list, not the counts. Conversion problems (unanswered warm leads, missed handoffs) lose more opportunities than copy problems.
- Bare instant "Stop" replies clustered on day one of a wave usually mean the contacts recognize a prior campaign (burned relaunch).
