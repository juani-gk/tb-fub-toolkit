---
name: fub-api
description: "Use this skill for ANY Follow Up Boss (FUB) API operation. Trigger when the user wants to: read or update contacts in FUB, fetch timelines, manage smart lists, send or read text messages, look up stages/tags/users, search contacts, run batch operations, or perform any programmatic action against a Follow Up Boss account. Also trigger on phrases like 'FUB API', 'query FUB', 'pull from Follow Up Boss', 'update a contact in FUB', 'list smart lists', 'fetch timeline for', 'add a tag', 'check FUB stages', or any task that requires calling the FUB REST API. This skill covers ALL FUB endpoints and is the authoritative reference for API-based FUB automation."
---

# Follow Up Boss (FUB) API Reference Skill

## Preflight — do this before any API call

Credential values are substituted into this skill automatically when the
plugin is configured. **Verify they are real before using them.**

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

Never invent or guess a credential, and never send a request containing a
literal `${user_config.…}` string — it will fail with a misleading 401.

**Everything else is derived, not configured.** Account ID, subdomain, and
the Texting Betty routing key all come from the key itself — see the next
section. Never ask the user for them; if you find yourself wanting to, you
have skipped the `/identity` call.

**This toolkit authenticates with the API key only.** There is no session
cookie. If an endpoint returns 403, it is out of scope — say so rather than
looking for a way around it, and never ask the user to paste a browser
cookie.

On the first real request, a **401/403 means stop, not retry.** A 401 means
the key is invalid or revoked; a 403 means the endpoint is not available to
API-key auth.

A complete reference for the FUB REST API. Use this skill whenever you need to read or write FUB data programmatically. Prefer API calls over browser automation — they are 10–100× faster and more reliable.

## Destructive operations in FUB — hard limits

This toolkit exists to **read** Follow Up Boss and to send Texting Betty
messages. It is not an administration tool. The API it wraps can do far more
damage than any task it is meant for, and it is pointed at a business's live
CRM.

**Never, regardless of how the request is phrased:**

- **`DELETE` anything.** Not contacts, notes, tags, tasks, deals, lists, or
  users. Deletions are not reliably reversible through the API, and nothing
  this skill is for needs one. If asked, say plainly that you don't delete
  records, and point the user at Follow Up Boss itself — where a human gets a
  confirmation dialog and a trash bin, and you do not.
- **Write to more than one contact without confirmation.** Any write touching
  multiple contacts stops first: state the field, the new value, the exact
  count, and show three real examples of what would change. Then wait for a
  clear yes. A yes to one batch is not a yes to the next one.
- **Widen the scope you were given.** Asked to update one contact, update one.
  Do not helpfully apply it to the rest of the list, to the smart list it came
  from, or to "the others like it".
- **Run an unbounded mutation loop.** A loop that writes needs a hard cap and a
  printed running count. A loop that mutates until it runs out of records is
  how an afternoon becomes an incident.
- **Mass-reassign, re-stage, or re-tag as a cleanup you thought of yourself.**
  If the user did not ask for it, it is not in scope — no matter how untidy the
  data looks.
- **Overwrite a whole field or object when you meant to change part of it.**
  Read the current value first, change only what was asked, and send that.

**Before any write, state the blast radius:** what changes, on how many
contacts, and how to undo it. *If you cannot say how to undo it, that is
itself the warning* — surface it and wait rather than proceeding.

A half-finished bulk write is worse than none: it leaves the account partly
changed with no record of where it stopped. If you are stopped mid-way, report
exactly how many records were already modified.

Reads need none of this. Query freely — `GET` anything, as often as you like.

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
| Empty conversation | "No text history with this contact yet." |
| Nothing configured | "I need your Follow Up Boss API key first — you can paste it in the plugin settings." |

Never show a raw error body, a stack trace, or a JSON blob unless they ask to
see it. If you truly cannot proceed, say so plainly in one sentence and stop —
do not improvise a workaround or ask them for a credential this toolkit does
not use.

Write in their vocabulary: leads, replies, opt-outs, conversations,
appointments. Not records, rows, objects, or collections.


---

## HTTP transport — read this before writing any request

**`curl` is blocked in this environment. Use Python `urllib`.** And Python
here does not find the system trust store on its own, so every request must
pass an explicit CA file or it fails with `CERTIFICATE_VERIFY_FAILED`.

This is the canonical helper. Use it for every call in this skill:

```python
import json, ssl, urllib.request

CTX = ssl.create_default_context(cafile="/etc/ssl/cert.pem")

def http(url, headers, data=None, method="GET"):
    """Returns (status, parsed_body). Never raises on HTTP error status."""
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, context=CTX, timeout=30) as r:
            body = r.read()
            return r.status, (json.loads(body) if body else None)
    except urllib.error.HTTPError as e:
        body = e.read()
        try:
            return e.code, json.loads(body)
        except Exception:
            return e.code, body.decode(errors="replace")
```

Never disable verification (`ssl._create_unverified_context`) to work around
a cert error — pass the `cafile` instead.

---

## Authentication

> ⛔ **Never send `X-System: fub-spa`.** That value is FUB's own web app
> identifier. Sending it from an integration claims to *be* their
> first-party client, which is grounds for having the account flagged or
> the key revoked. The same applies to any other internal client
> identifier, including `x-fub-js-version`.
>
> `X-System` is a legitimate header **only** when it carries an identifier
> FUB issued to you for a registered integration, paired with its
> `X-System-Key`. If you have one, set both. If you do not, **send
> neither** — the requests work fine without them, just at the default
> rate limit.
>
> This ban is about *identity claims*, not about headers in general. It
> covers values that assert you are FUB's own client (`fub-spa`,
> `x-fub-js-version`). It does **not** cover generic web headers like
> `X-Requested-With`, `Accept`, or `Content-Type` — those are standard,
> carry no identity claim, and some are functionally required. Do not strip
> them.

```python
BASE_HEADERS = {}   # add {"X-System": ..., "X-System-Key": ...} only if registered
```

### API Key Auth (programmatic/server-to-server)

```python
import base64
key = "${user_config.fub_api_key}"
headers = {
    **BASE_HEADERS,
    "Authorization": "Basic " + base64.b64encode((key + ":").encode()).decode(),
    "Content-Type": "application/json",
}
```

**This toolkit is API-key only. Never ask the user for a session cookie, or
suggest copying one from DevTools, as a workaround for a 403.** If an
endpoint is not reachable with the API key, treat it as unavailable and use
one of the alternatives below — or tell the user plainly that this toolkit
cannot do it.

**How this toolkit covers activity, sending, and reading conversations:**

- **A contact's activity:** pull `/events`, `/tasks`, `/notes`, `/calls`,
  `/textMessages`, `/emails` — all accepting `?personId={id}` — in one
  `POST /batch` and merge client-side by date. **Texting Betty SMS will not
  appear** in any of them; TB messages come from the cloud function. For a
  quick view instead of full history, `GET /people/{id}` already carries
  `lastCommunication`, `textsSent`/`textsReceived`, and
  `lastSentInboxAppMessageBody` / `lastReceivedInboxAppMessageBody` — the
  most recent message each way.
- **Sending a text:** invoke the `tb-send-text` skill. It creates the
  tagged note with the mechanics this reference doesn't cover (tag
  placement, timing tags, the opt-out check) — don't hand-roll a
  `POST /notes` call here.
- **Reading a conversation:** invoke the `reply-check` skill. It calls the
  Texting Betty cloud function and classifies the result — this toolkit's
  own endpoints can't reach conversation history at all.

---

## Bootstrap — derive the account from the key

**Call `/identity` first, before any other request.** One cheap call, and it
supplies every value this toolkit used to ask the user to type.

```python
status, me = http(f"{BASE}/identity", headers)
```

Response shape (values below are placeholders):

```json
{
  "account": {
    "id": 1234567890,
    "domain": "yourcompany",
    "name": "Your Account Name",
    "owner": { "name": "...", "email": "owner@example.com" }
  },
  "user": {
    "id": 1, "name": "...", "email": "user@example.com",
    "fuid": "fau_xxxxxxxxxxx", "role": "Broker",
    "isOwner": true, "isAdmin": true, "isLender": false
  }
}
```

What to take from it:

| Need | Field |
|---|---|
| Account ID (sanity checks) | `account.id` |
| Subdomain, for **human-facing links only** | `account.domain` |
| Who this key belongs to | `user.email`, `user.role` |

> ⚠️ Use `account.domain`, **never** `account.name`. `domain` is the
> subdomain in the URL; `name` is a display label, and the two routinely
> differ — an account can be named one thing and live at an entirely
> different subdomain.

`user` is the identity the **API key** belongs to. It is not necessarily the
account owner, and it is *not* the Texting Betty routing key. Do not infer
one from the other.

**On 401/403 → stop, do not retry.** The key is invalid or revoked. There is
nothing else to try and no fallback credential.

---

## Base URL & Account

```
BASE = "https://api.followupboss.com/v1"
```

**Use the generic host for every API call.** It requires no subdomain, which
is what lets this toolkit run from a single configured value. The
`{subdomain}.followupboss.com` form works too, but you would have to call
`/identity` just to learn the subdomain first — pointless when the generic
host serves the same API.

The subdomain (`account.domain` from `/identity`) is needed for exactly one
thing: building **human-facing links**, e.g.
`https://<account.domain>.followupboss.com/2/people/view/{id}`.

Every response includes:
- `FUB-Account-ID: <account.id>`
- `FUB-User-ID: <authenticated user id>`

---

## Rate Limiting

Response headers on every call:
```
X-RateLimit-Window: 10
X-RateLimit-Limit: 125
X-RateLimit-Remaining: <n>
X-RateLimit-Context: global
```

**The real ceiling for API-key auth is 125 requests per 10-second window —
about 12 per second, account-wide (`context: global`).** Do not trust a
much larger number seen elsewhere; those came from browser-session auth,
which this toolkit no longer uses.

Consequences worth planning around:

- The budget is **shared across everything using that key.** A bulk job at
  full speed starves every other call on the same account.
- At ~12/s, a 300-contact sweep needs ≥24s of rate-limit budget on its own.
- Read `X-RateLimit-Remaining` from responses and slow down as it drops,
  rather than waiting for the 429.

**Best practice:** sleep 0.5s between requests (~2/s, comfortably under the
ceiling and leaves room for other traffic). On HTTP 429, back off
exponentially:

```python
import time, urllib.request, json

def fub_get(url, headers):
    for attempt in range(3):
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, context=CTX, timeout=30) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code == 429:
                time.sleep(4 * (attempt + 1))
            else:
                raise                      # 401/403: stop, do not retry
    return None
```

Retry **only** on 429. A 401 or 403 will not fix itself, and retrying a
write endpoint after an ambiguous failure risks sending a text twice.

### Environment constraints

Two things about *where this code runs*, not about FUB — check them before
designing a batching strategy, because they change what is possible:

- **`/tmp` is not writable.** Do not hardcode it for resumable state. Write
  to the current working directory, or to a path the user gives you. If a
  write fails, say so instead of silently losing progress.
- **The 45-second per-call limit is a sandbox restriction, not a FUB one.**
  It applies when running inside a bash tool with a timeout, and it is why
  large jobs get split into chunks. Running the same script directly on a
  workstation, no chunking is needed — do not carve a 500-contact job into
  ten pieces if nothing is imposing a timeout.

Where a timeout *does* apply: at ~0.5s per request, keep each invocation
under ~55 contacts and accumulate results in a resumable file keyed by
contact ID, so a rerun skips what is already done.

---

## Pagination

All list endpoints return a `_metadata` envelope:

```json
{
  "_metadata": {
    "collection": "people",
    "offset": 0,
    "limit": 30,
    "total": 110228,
    "next": "eyJvZmZzZXQiOjMwfQ",
    "nextLink": "https://...?limit=30&next=eyJvZmZzZXQiOjMwfQ"
  }
}
```

**Paginate with offset:**
```python
all_items = []
offset = 0
limit = 100
while True:
    data = fub_get(f"{BASE}/people?limit={limit}&offset={offset}&smartListId={list_id}&fields=allFields", headers)
    all_items.extend(data["people"])
    if len(all_items) >= data["_metadata"]["total"]:
        break
    offset += limit
    time.sleep(0.3)
```

---

## People

### List People

```
GET /people
```

| Param | Example | Notes |
|---|---|---|
| `limit` | `100` | Max per page |
| `offset` | `0` | Offset pagination |
| `sort` | `-lastCommunication` | Prefix `-` = descending |
| `fields` | `allFields` | Return all fields (use this; partial field lists can 400) |
| `smartListId` | `130` | Filter by smart list |
| `idsOnly` | `true` | Return only IDs (fast for counting) |
| `includePonds` | `true` | Include pond assignments |
| `q` | `jane doe` | Full-text search by name/email/phone |

**Key person fields:**
```json
{
  "id": 12345,
  "name": "Jane Doe",
  "firstName": "Jane",
  "lastName": "Doe",
  "stage": "Lead",
  "stageId": 33,
  "type": "Buyer",
  "source": "<unspecified>",
  "assignedUserId": 15,
  "assignedTo": "Agent Name",
  "assignedPonds": [{ "id": 5, "name": "Example Team" }],
  "tags": [{ "id": 2, "name": "Import" }],
  "emails": [{ "value": "...", "type": "home", "status": "Valid", "isPrimary": 1 }],
  "phones": [{ "value": "5555550100", "type": "mobile", "status": "Valid", "isPrimary": 1,
               "normalized": "5555550100", "isLandline": false }],
  "lastCommunication": "2026-06-09T13:06:45Z",
  "lastSentInboxAppMessageBody": "Hi, this is ...",
  "lastReceivedInboxAppMessageBody": "Thanks, I'll think about it",
  "textsReceived": 2,
  "textsSent": 3,
  "contacted": 1,
  "lastActivity": "2026-06-09T13:06:45Z"
}
```

**Extract team name:**
```python
team = person.get("assignedPonds", [{}])[0].get("name") or person.get("assignedTo") or "Unassigned"
```

**Contact URL:**
```
https://<account.domain>.followupboss.com/2/people/view/{id}
```

---

### Get Single Person

```
GET /people/{id}
```

Returns the full person object plus:
- `publishedInboxAppsForContact` — active embedded app conversations
- `mostRecentMessagePublishedInboxAppId`
- All `last*` communication timestamps
- `callsDuration`, `firstCall`, `lastCall`
- `background`, `picture`, `socialData`
- `timeframeId`, `timeframeStatus`, `timeframeDateRange`

---

### Get Person Summary (Lightweight)

```
GET /people/{id}/summary
```

Returns: name, stage, phones, emails, assigned agent, embedded apps list. Use when you don't need the full object.

---

### AI Smart Message Chips

```
GET /people/{id}/insights/smartMessageChips
```

Returns suggested message topics (introduction, follow-up, still-buying, nurture, custom).

---

### Log Recent View

```
POST /people/recent
Body: { "id": 12345, "name": "Jane Doe" }
```

Marks a person as recently viewed; returns the last 10 recently viewed people.

---

## Filtering People

```
POST /people/filter?idsOnly=true
```
```json
{"conditions":[[{"fld":"lastReceivedInboxAppMessage","opr":"was less than","num":"2","unit":"days","val":[]}]]}
```

Answers a question directly instead of relying on a smart list existing that
happens to encode it. **Prefer this over discovering a list by name** when you
know the condition you actually want.

`conditions` is an **array of arrays** — the nesting is required.

Useful fields, same vocabulary as smart list conditions (see below):

| `fld` | Meaning |
|---|---|
| `lastReceivedInboxAppMessage` | Last inbound Texting Betty message |
| `lastCommunication` | Any channel |
| `inboxAppMessagesReceived` | Count of inbound TB messages |
| `tags` | Tag membership |
| `stage` | Stage |

Pair `fld` with an `opr` such as `was less than` / `was more than` plus `num`
and `unit`, or `is equal to` / `include any of` plus `val`.

**Send `idsOnly=true` by default.** Omit it only when you have already decided
which fields you need and why.

The reasoning is not cosmetic. A filter over a few hundred leads returns a few
hundred full person objects — every custom field, every phone, every timestamp —
and in this toolkit the very next step usually only needs the ID to fetch a
conversation. That payload costs response time, rate-limit budget, and context
window, for data that is discarded a line later.

If you find you need a field after all, fetch that one contact with
`GET /people/{id}`. One extra call beats hundreds of unused objects.

The pagination quirk applies here too: all IDs come back in one response and
offsets are ignored.

---

## Smart Lists

### List All Smart Lists

```
GET /smartLists?limit=100
```

Returns only lists visible to the authenticated user. To find ALL lists (including team-specific ones): scan IDs 1–250 individually — most will 404, which is fine.

**Never hardcode a smart list ID.** IDs are per-account: the same number is
a different list in another tenant, and most lists do not exist at all in a
given account. Always discover by name:

```python
status, data = http(f"{BASE}/smartLists?limit=100", headers)
lists = {l["name"].lower(): l["id"] for l in data.get("smartlists", [])}
match = next((i for n, i in lists.items() if "replied" in n), None)
```

If nothing matches, **do not guess an ID and do not fall back to a number
from another account.** Show the user the lists that do exist and ask which
one to use.

**A matching list may not exist at all.** Not every account has "replied"
lists — segmentation is often done by *tag* instead. When list discovery
comes up empty, check tags before concluding there is no data:

```python
status, data = http(f"{BASE}/tags?limit=2000", headers)
tb = [t for t in data.get("tags", []) if "texting" in t["name"].lower()]
```

Tags whose names encode TB state (engagement, unsubscribe) identify the
contacts with messaging history. Filter people by tag with
`GET /people?tags=<name>&idsOnly=true`. For a full reply-analysis task,
invoke the `reply-check` skill instead of reimplementing this filter +
classify workflow here — it already has both paths built.

**Response shape:**
```json
{
  "id": 130,
  "name": "Replied Today",
  "isFub2": true,
  "shared": false,
  "createdById": 1,
  "conditions": [
    {
      "fld": "lastCommunication",
      "opr": "was more than",
      "num": 0,
      "unit": "days",
      "val": null
    }
  ]
}
```

**Common condition fields (`fld`):**
- `tags` — operators: `include any of`, `do not include any of` (val = array of tag IDs)
- `stage` — `is equal to` (val = array of stage IDs)
- `lastCommunication` — `was more than` (num = days, unit = "days")
- `assignedUserId` — `is any of` (val = array of user IDs)
- `phone` — `is not bad`
- `inboxAppMessagesReceived` — `is less than`

---

### Get Single Smart List

```
GET /smartLists/{id}
```

---

### Smart List Groups & Defaults

```
GET /smartListGroups
GET /defaultSmartLists
```

---

## Tags

### List All Tags

```
GET /tags?limit=2000
```

```json
{
  "tags": [
    {
      "id": 9584,
      "name": "Referral",
      "peopleCount": 14287,
      "trashedPeopleCount": 63
    }
  ]
}
```

Tags are account-specific — pull the current list live via the endpoint
above rather than hardcoding tag IDs or names in a skill. Common built-in
or convention-based tags include things like `Import` (imported contact),
an "engaged with the SMS platform" tag, and an "AI messaging disabled"
tag, but exact names and IDs vary per account.

---

## Stages

### List All Stages

```
GET /stages
```

```json
{
  "stages": [
    {
      "id": 33,
      "name": "Lead",
      "orderWeight": 3000,
      "isProtected": false,
      "peopleCount": 666,
      "actionPlans": [{ "id": 21, "name": "Follow-Up Sequence" }]
    }
  ]
}
```

Stages are fully account-specific and reflect whatever pipeline the
account owner has configured (e.g. `Lead`, `Contacted`, `Qualified`,
`Under Contract`, `Closed`, or a custom funnel for another use case).
Always pull the current list live via `GET /stages` rather than assuming
particular stage names or IDs.

---

## Custom Fields

### List Custom Fields

```
GET /customFields
```

```json
{
  "customfields": [
    {
      "id": 47,
      "name": "customFollowUpDate",
      "label": "Follow Up Date",
      "type": "date",
      "orderWeight": 43000,
      "hideIfEmpty": true,
      "readOnly": false,
      "isRecurring": false
    }
  ]
}
```

Field types: `date`, `number`, `text`

Custom field values appear on person objects using their `name` as the key (e.g., `person["customFollowUpDate"]`).

---

## Users

### Get User by ID

```
GET /users/{id}
```

```json
{
  "id": 1,
  "name": "Jane Doe",
  "email": "jane@example.com",
  "phone": "5555550100",
  "role": "Broker",
  "status": "Active",
  "timezone": "America/New_York",
  "calling": { "enabled": false },
  "lastWebLogin": "2026-06-09T13:04:01Z",
  "notifyBy": ["email", "sms"]
}
```

To see all users on an account, use `GET /users?limit=100` and cache the
result — user IDs and names are account-specific and should be looked up
live, not hardcoded in a skill.

---

## Shared Inboxes

### List Shared Inboxes

```
GET /sharedInboxes?showAllBypass=true&limit=20
```

```json
{
  "sharedInboxes": [
    {
      "id": 34,
      "name": "Example Team",
      "status": "Active",
      "phones": [{ "phone": "5555550100", "canText": true }],
      "users": [{ "id": 37, "name": "Example Team", "role": "Agent" }]
    }
  ]
}
```

Shared inboxes are account-specific — always pull the current list live via
the endpoint above rather than hardcoding names, IDs, or phone numbers in
a skill.

---

## Text Message Templates

### List Templates

```
GET /textMessageTemplates
```

```json
{
  "textmessagetemplates": [
    {
      "id": 19,
      "name": "Agent > Client + Lender intro",
      "message": "%greeting_time% %lender_first_name%, %contact_first_name% is a client...",
      "isShared": true,
      "totalSent": 0,
      "totalReplies": 0,
      "effectivenessScore": null,
      "categories": [{ "id": 3, "name": "Follow Up Boss" }]
    }
  ]
}
```

**Template variables:** `%greeting_time%`, `%contact_first_name%`, `%agent_first_name%`, `%company_name%`, `%lender_first_name%`, `%inquiry_address%`

---

## Events / Appointments

```
GET /events?personId={id}&limit=100
```

Returns calendar events/appointments for a person.

---

## Tasks, Action Plans, Attachments

```
GET /tasks?personId={id}&limit=100&offset=0
GET /actionPlansPeople?personId={id}&limit=100&offset=0
GET /personAttachments?personId={id}&limit=100&offset=0
```

---

## Scheduled Emails

```
GET /scheduledEmails?personId={id}&status=10&limit=100&offset=0
```

`status=10` = pending.

---

## Website Activity

```
GET /websiteActivity?personId={id}
```

---

## Deals / Pipelines

```
GET /pipelines
GET /deals?personId={id}&limit=100&offset=0
```

---

## Saved Property Searches

```
GET /savedPropertySearches?personId={id}
```

---

## Agent Relationships

```
GET /myAgentRelationships/unified?personId={id}&limit=100&offset=0
```

---

## Reference Data

```
GET /ponds
GET /teams
GET /groups
GET /leadSources
GET /categories
GET /timeframes
GET /callLists
GET /blockedIdentifiers
```

---

## Batch API

Execute multiple requests in one HTTP call — use this when loading a contact's full context.

```
POST /batch
```

```json
{
  "batch": [
    { "relativeUrl": "/v1/appointments?limit=100&offset=0&personId=12345", "name": "appts", "method": "GET" },
    { "relativeUrl": "/v1/tasks?limit=100&personId=12345&offset=0", "name": "tasks", "method": "GET" },
    { "relativeUrl": "/v1/actionPlansPeople?personId=12345&limit=100&offset=0", "name": "plans", "method": "GET" },
    { "relativeUrl": "/v1/personAttachments?personId=12345&limit=100&offset=0", "name": "files", "method": "GET" }
  ]
}
```

**Response:** Array of results per name:
```json
[
  {
    "code": 200,
    "body": { "_metadata": { "collection": "appointments", "total": 0 }, "appointments": [] },
    "name": "appts"
  }
]
```

---

## Common Python Patterns

### Fetch All Contacts from a Smart List

```python
import base64, json, ssl, time, urllib.request

CTX = ssl.create_default_context(cafile="/etc/ssl/cert.pem")
BASE = "https://api.followupboss.com/v1"   # generic host — no subdomain needed
key = "${user_config.fub_api_key}"
headers = {
    "Authorization": "Basic " + base64.b64encode((key + ":").encode()).decode(),
}

def get(path):
    req = urllib.request.Request(f"{BASE}{path}", headers=headers)
    with urllib.request.urlopen(req, context=CTX, timeout=30) as r:
        return json.load(r)

# 1. Validate the key belongs to the configured account
me = get("/identity")
print("authenticated against:", me)

# 2. Discover the list by name — never hardcode an ID
lists = {l["name"].lower(): l["id"] for l in get("/smartLists?limit=100")["smartlists"]}
list_id = next((i for n, i in lists.items() if "replied" in n), None)
if list_id is None:
    raise SystemExit(f"No matching list. Available: {sorted(lists)}")

# 3. IDs only — the default. No pagination loop needed: idsOnly returns
#    every match in one response.
ids = get(f"/people?smartListId={list_id}&idsOnly=true")["ids"]
print(f"{len(ids)} contacts")
```

**Only page through full objects when you actually need fields.** Reach for
this when you need names, phones or stages for the leads you will report on —
not as the default way to enumerate a segment:

```python
all_people = []
offset, limit = 0, 100
while True:
    data = get(f"/people?smartListId={list_id}&limit={limit}&offset={offset}&fields=allFields")
    all_people.extend(data["people"])
    if len(all_people) >= data["_metadata"]["total"]:
        break
    offset += limit
    time.sleep(0.3)
print(f"Fetched {len(all_people)} contacts")
```

`fields=allFields` is about *how* to ask when you do want fields — a hand-picked
list often 400s. It is not a reason to fetch fields you do not need.

### Batch Activity Fetch (Rate-Limited, Resumable)

Pull the individual collections and merge them client-side.

```python
import os

# /tmp is NOT writable here — keep state in the working directory
results_file = "fub_results.json"
results = json.load(open(results_file)) if os.path.exists(results_file) else {}

contact_ids = [p["id"] for p in all_people]

for pid in contact_ids:
    if str(pid) in results:
        continue  # already processed
    for attempt in range(3):
        try:
            batch = {"batch": [
                {"relativeUrl": f"/v1/notes?personId={pid}&limit=100", "name": "notes", "method": "GET"},
                {"relativeUrl": f"/v1/calls?personId={pid}&limit=100", "name": "calls", "method": "GET"},
                {"relativeUrl": f"/v1/events?personId={pid}&limit=100", "name": "events", "method": "GET"},
            ]}
            data = post("/batch", batch)
            results[str(pid)] = data
            break
        except Exception as e:
            if "429" in str(e):
                time.sleep(4 * (attempt + 1))
            else:
                results[str(pid)] = []
                break
    time.sleep(0.5)

with open(results_file, "w") as f:
    json.dump(results, f)
print(f"Done: {len(results)}/{len(contact_ids)}")
```

---

## Common Errors

| Error | Cause | Fix |
|---|---|---|
| `CERTIFICATE_VERIFY_FAILED` | Python can't find the system trust store | Pass `cafile="/etc/ssl/cert.pem"` — never disable verification |
| `curl: command not found` / blocked | `curl` is unavailable in this environment | Use Python `urllib` with the canonical `http()` helper |
| Data looks wrong but every call returns 200 | API key belongs to a **different FUB account** | Call `/identity` and confirm `account.name`/`account.domain` are the account you expect |
| HTTP 400 on `/people` | `fields=id,name,...` list too long | Use `fields=allFields` |
| HTTP 401 | API key invalid or revoked | Stop — do not retry. Ask the user to check the key |
| HTTP 403 | Endpoint not available to this integration | Out of scope. Use the documented alternative; never ask for a cookie |
| HTTP 429 | Rate limit hit | Sleep 4s, exponential backoff, lower concurrency |
| Account flagged / key revoked | Sent `X-System: fub-spa` or other first-party client headers | Never impersonate FUB's own web app; register an integration instead |
| HTML login page instead of JSON | Called an endpoint this integration can't reach | That endpoint is out of scope — use the API-key alternative |
| HTTP 404 on smart list | Hardcoded an ID from another account | Discover by name via `/smartLists`; IDs are per-account |
| No "replied" list exists | Account segments by tag, not by list | Fall back to the tag path (`/tags`, then `/people?tags=`) |
| `Read-only file system: '/tmp/…'` | `/tmp` is not writable here | Write state to the working directory instead |
| Bash 45s timeout | Sandbox limit, not a FUB limit | Chunk to ≤55 contacts per call — only when a timeout applies |

---

## Field Reference

**Phone `status`:** `Valid`, `Invalid`, `Landline`, `Bad`  
**Email `status`:** `Valid`, `Invalid`, `Unsubscribed`  
**`contacted` field:** `0` = never contacted, `1` = has been contacted  
**`createdVia`:** `"Manually"`, `"Import"`, `"API"`, etc.  
**Delivery statuses:** `delivered`, `sent`, `pending`, `failed`, `undelivered`, `error`
