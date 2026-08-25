---
name: fub-api
description: "Use this skill for ANY Follow Up Boss (FUB) API operation. Trigger when the user wants to: read or update contacts in FUB, fetch timelines, manage smart lists, send or read text messages, look up stages/tags/users, search contacts, run batch operations, or perform any programmatic action against a Follow Up Boss account. Also trigger on phrases like 'FUB API', 'query FUB', 'pull from Follow Up Boss', 'update a contact in FUB', 'list smart lists', 'fetch timeline for', 'add a tag', 'check FUB stages', or any task that requires calling the FUB REST API. This skill covers ALL FUB endpoints and is the authoritative reference for API-based FUB automation."
---

# Follow Up Boss (FUB) API Reference Skill

## Preflight - do this before any API call

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

Never invent or guess a credential, and never send a request containing a
literal `${user_config.…}` string - it will fail with a misleading 401.

**Everything else is derived, not configured.** Account ID, subdomain, and
the Texting Betty routing key all come from the key itself - see the next
section. Never ask the user for them; if you find yourself wanting to, you
have skipped the `/identity` call.

**This toolkit authenticates with the API key only.** There is no session
cookie. If an endpoint returns 403, it is out of scope - say so rather than
looking for a way around it, and never ask the user to paste a browser
cookie.

On the first real request, a **401/403 means stop, not retry.** A 401 means
the key is invalid or revoked; a 403 means the endpoint is not available to
API-key auth.

A complete reference for the FUB REST API. Use this skill whenever you need to read or write FUB data programmatically. Prefer API calls over browser automation - they are 10–100× faster and more reliable.

## Destructive operations in FUB - hard limits

This toolkit exists to **read** Follow Up Boss and to send Texting Betty
messages. It is not an administration tool. The API it wraps can do far more
damage than any task it is meant for, and it is pointed at a business's live
CRM.

**Never, regardless of how the request is phrased:**

- **`DELETE` anything.** Not contacts, notes, tags, tasks, deals, lists, or
  users. Deletions are not reliably reversible through the API, and nothing
  this skill is for needs one. If asked, say plainly that you don't delete
  records, and point the user at Follow Up Boss itself - where a human gets a
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
  If the user did not ask for it, it is not in scope - no matter how untidy the
  data looks.
- **Overwrite a whole field or object when you meant to change part of it.**
  Read the current value first, change only what was asked, and send that.

**Before any write, state the blast radius:** what changes, on how many
contacts, and how to undo it. *If you cannot say how to undo it, that is
itself the warning* - surface it and wait rather than proceeding.

A half-finished bulk write is worse than none: it leaves the account partly
changed with no record of where it stopped. If you are stopped mid-way, report
exactly how many records were already modified.

Reads need none of this. Query freely - `GET` anything, as often as you like.

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
| Every request fails with no response at all, not a FUB error | "I can't reach Follow Up Boss at all right now - this looks like a network permission issue on this Claude account, not something wrong with your FUB account. If you're on a team plan, your workspace admin needs to allow access; otherwise it's in your own Claude network settings." |
| Empty conversation | "No text history with this contact yet." |
| Nothing configured | "I need your Follow Up Boss API key first - you can paste it in the plugin settings." |

Never show a raw error body, a stack trace, or a JSON blob unless they ask to
see it. If you truly cannot proceed, say so plainly in one sentence and stop -
do not improvise a workaround or ask them for a credential this toolkit does
not use.

Write in their vocabulary: leads, replies, opt-outs, conversations,
appointments. Not records, rows, objects, or collections.


---

## HTTP transport - read this before writing any request

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
a cert error - pass the `cafile` instead.

**For pulling a population and its conversations, don't hand-roll any of
this - run `${CLAUDE_PLUGIN_ROOT}/skills/fub-api/scripts/tb_fetch.py`.** It ships with this skill and is what
`reply-check` and `tb-reports` both call:

```bash
export FUB_API_KEY='${user_config.fub_api_key}'   # never hardcode it in a file
python3 ${CLAUDE_PLUGIN_ROOT}/skills/fub-api/scripts/tb_fetch.py identity
python3 ${CLAUDE_PLUGIN_ROOT}/skills/fub-api/scripts/tb_fetch.py ids --days 30 --field lastSentInboxAppMessage --out ids.json
python3 ${CLAUDE_PLUGIN_ROOT}/skills/fub-api/scripts/tb_fetch.py convs --ids ids.json --out conversations.json
```

It has the concurrency, the resumable results file, the rate-limit reading
and the 429 halt already in it. The `http()` helper above stays the
reference for the *other* endpoints in this file - use it for one-off calls,
not for sweeping a population.

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
> neither** - the requests work fine without them, just at the default
> rate limit.
>
> This ban is about *identity claims*, not about headers in general. It
> covers values that assert you are FUB's own client (`fub-spa`,
> `x-fub-js-version`). It does **not** cover generic web headers like
> `X-Requested-With`, `Accept`, or `Content-Type` - those are standard,
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
one of the alternatives below - or tell the user plainly that this toolkit
cannot do it.

**How this toolkit covers activity, sending, and reading conversations:**

- **A contact's activity:** pull `/events`, `/tasks`, `/notes`, `/calls`,
  `/textMessages`, `/emails` - all accepting `?personId={id}` - individually
  and merge client-side by date. **Texting Betty SMS will not appear** in
  any of them; TB messages come from the cloud function. For a quick view
  instead of full history, `GET /people/{id}` already carries
  `lastCommunication`, `textsSent`/`textsReceived`, and
  `lastSentInboxAppMessageBody` / `lastReceivedInboxAppMessageBody` - the
  most recent message each way.
- **Sending a text:** invoke the `tb-send-text` skill. It creates the
  tagged note with the mechanics this reference doesn't cover (tag
  placement, timing tags, the opt-out check) - don't hand-roll a
  `POST /notes` call here.
- **Reading a conversation:** invoke the `reply-check` skill. It calls the
  Texting Betty cloud function and classifies the result - this toolkit's
  own endpoints can't reach conversation history at all.

---

## Bootstrap - derive the account from the key

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
> differ - an account can be named one thing and live at an entirely
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
`/identity` just to learn the subdomain first - pointless when the generic
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

**The real ceiling for API-key auth is 125 requests per 10-second window -
about 12 per second, account-wide (`context: global`).** Do not trust a
much larger number seen elsewhere; those came from browser-session auth,
which this toolkit no longer uses.

Consequences worth planning around:

- The budget is **shared across everything using that key.** A bulk job at
  full speed starves every other call on the same account.
- At ~12/s, a 300-contact sweep needs ≥24s of rate-limit budget on its own.
- Read `X-RateLimit-Remaining` from responses and slow down as it drops,
  rather than waiting for the 429.

**This ceiling governs calls to FUB's own endpoints, one at a time.** It is
not the budget for sweeping conversations: those go to the Texting Betty
proxy, which has a separate hourly allowance (`X-RateLimit-Cost` per contact)
and is fetched concurrently by `tb_fetch.py`. Do not apply the pacing below
to that sweep - it is what turns a ninety-second job into half an hour.

**For FUB endpoints called directly:** sleep 0.5s between requests (~2/s,
comfortably under the ceiling and leaves room for other traffic). On HTTP
429, back off exponentially:

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

Two things about *where this code runs*, not about FUB - check them before
designing a batching strategy, because they change what is possible:

- **Write state to the working directory, not `/tmp`.** Whether `/tmp` is
  writable depends on where this runs - it is not in some sandboxes, and is
  on a workstation, so a script that hardcodes it works until it doesn't.
  There is a second reason to avoid it regardless: these files hold real
  contact conversations, and the working directory is what this repo's
  `.gitignore` covers. A real run left a 2MB `/tmp/conversations_365.json`
  behind. Use the working directory, or a path the user gives you, and if a
  write fails, say so instead of silently losing progress.
- **The 45-second per-call limit is a sandbox restriction, not a FUB one.**
  It applies when running inside a bash tool with a timeout, and it is why
  large jobs get split into chunks. Running the same script directly on a
  workstation, no chunking is needed - do not carve a 500-contact job into
  ten pieces if nothing is imposing a timeout.

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

## Endpoints

Request shapes, parameters and response fields are in
`${CLAUDE_PLUGIN_ROOT}/skills/fub-api/references/endpoints.md`. Read it when
you need one; it is lookup data, not something to load every time. What is
covered there:

| Section | Use it for |
|---|---|
| People | List, get one, and the lightweight summary |
| Filtering People | `POST /people/filter` - the population query, `conditions` as an array of arrays |
| Smart Lists | Discover a list by name; never hardcode an ID |
| Tags | Pull a segment by tag |
| Stages, Custom Fields, Users | Account metadata and field discovery |
| Text Message Templates | Listing templates |
| Events / Appointments, Tasks / Action Plans, Deals / Pipelines | The remaining collections, all accepting `?personId=` |
| Agent Relationships, Reference Data | Assignment and enum lookups |

Two rules that hold across every one of them, and are easy to lose when
reading a single section in isolation: **`idsOnly=true` returns every match
in one response and ignores pagination** - looping offsets duplicates the
full set per page - and **Texting Betty SMS appears in none of these
collections.** Conversations come from the proxy; see `reply-check`.

## Common Python Patterns

### Fetch a population

`scripts/tb_fetch.py` already does identity plus the population filter -
see the top of this file. Discovering a smart list by name (never by
hardcoded ID) still belongs here:

```python
lists = {l["name"].lower(): l["id"] for l in get("/smartLists?limit=100")["smartlists"]}
list_id = next((i for n, i in lists.items() if "replied" in n), None)
if list_id is None:
    raise SystemExit(f"No matching list. Available: {sorted(lists)}")
ids = get(f"/people?smartListId={list_id}&idsOnly=true")["ids"]
```

`idsOnly` returns every match in one response - no pagination loop.

**Only page through full objects when you actually need fields.** Reach for
this when you need names, phones or stages for the leads you will report on -
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

`fields=allFields` is about *how* to ask when you do want fields - a hand-picked
list often 400s. It is not a reason to fetch fields you do not need.

### Activity Fetch (Rate-Limited, Resumable)

Pull the individual collections and merge them client-side.

```python
import os

# keep state in the working directory - see Environment constraints
results_file = "fub_results.json"
results = json.load(open(results_file)) if os.path.exists(results_file) else {}

contact_ids = [p["id"] for p in all_people]
COLLECTIONS = ["notes", "calls", "events"]

for pid in contact_ids:
    if str(pid) in results:
        continue  # already processed
    person_data = {}
    for attempt in range(3):
        try:
            for name in COLLECTIONS:
                person_data[name] = get(f"/{name}?personId={pid}&limit=100")
            results[str(pid)] = person_data
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
| Every request fails to connect at all (no response, no error body - not `CERTIFICATE_VERIFY_FAILED`, not a JSON error from FUB) | Claude's network egress settings don't allow the domains this toolkit needs (`api.followupboss.com`, `tb-proxy.vercel.app`). This is generic to Claude, not a FUB-specific problem - it would block any domain not on the allowlist | In Claude Code (web or desktop) settings: **Capabilities → Allow network egress → domain allowlist**. If part of a team, the org owner does this at the workspace level; on an individual account, do it yourself. Either add these two domains or select **all domains** |
| `CERTIFICATE_VERIFY_FAILED` | Python can't find the system trust store | Pass `cafile="/etc/ssl/cert.pem"` - never disable verification |
| `curl: command not found` / blocked | `curl` is unavailable in this environment | Use Python `urllib` with the canonical `http()` helper |
| Data looks wrong but every call returns 200 | API key belongs to a **different FUB account** | Call `/identity` and confirm `account.name`/`account.domain` are the account you expect |
| HTTP 400 on `/people` | `fields=id,name,...` list too long | Use `fields=allFields` |
| HTTP 401 | API key invalid or revoked | Stop - do not retry. Ask the user to check the key |
| HTTP 403 | Endpoint not available to this integration | Out of scope. Use the documented alternative; never ask for a cookie |
| HTTP 429 | Rate limit hit | Sleep 4s, exponential backoff, lower concurrency |
| Account flagged / key revoked | Sent `X-System: fub-spa` or other first-party client headers | Never impersonate FUB's own web app; register an integration instead |
| HTML login page instead of JSON | Called an endpoint this integration can't reach | That endpoint is out of scope - use the API-key alternative |
| HTTP 404 on smart list | Hardcoded an ID from another account | Discover by name via `/smartLists`; IDs are per-account |
| No "replied" list exists | Account segments by tag, not by list | Discover tag names from a person object's embedded `tags` array, then filter with `/people?tags=` |
| `Read-only file system: '/tmp/…'` | `/tmp` is read-only in some sandboxes | Write state to the working directory instead - do that everywhere, not only when this fires |
| Bash 45s timeout | Sandbox limit, not a FUB limit | Chunk to ≤55 contacts per call - only when a timeout applies |

---

## Field Reference

**Phone `status`:** `Valid`, `Invalid`, `Landline`, `Bad`  
**Email `status`:** `Valid`, `Invalid`, `Unsubscribed`  
**`contacted` field:** `0` = never contacted, `1` = has been contacted  
**`createdVia`:** `"Manually"`, `"Import"`, `"API"`, etc.  
**Delivery statuses:** `delivered`, `sent`, `pending`, `failed`, `undelivered`, `error`
