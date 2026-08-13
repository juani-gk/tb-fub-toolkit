---
name: "tb-send-text"
description: "Send an outbound SMS to a FUB contact via Texting Betty by creating a tagged note in Follow Up Boss. Use whenever the user says \"send a text to this lead\", \"text this contact via TB / Texting Betty\", \"send an SMS in FUB\", or gives a FUB contact URL/ID and a message to send. Also covers scheduling texts ([9am], [1h] delays) and cancelling unsent texts ([delete])."
---

# Send a Texting Betty Text via FUB

## Preflight — do this before sending anything

**Two configured values: `${user_config.risk_acknowledged}` and `${user_config.fub_api_key}`.**

**Check the acknowledgement first.** `${user_config.risk_acknowledged}` must be
`true`. If it is `false`, empty, or still a literal `${user_config.…}`, stop —
do not read, do not send, do not "just check one thing". Tell the user:

> Before I touch your Follow Up Boss account, you need to tick the
> acknowledgement in the plugin settings. It explains what can go wrong when an
> AI works against a live CRM, and it takes ten seconds to read.

This gate exists because the rest of this skill acts on a real business's data
and can send real messages. Never work around it, and never treat a verbal
"yes, go ahead" in chat as a substitute for the setting.


If it still reads literally as `${user_config.fub_api_key}` or is blank, the
plugin is NOT configured. Stop and tell the user:

> This plugin isn't configured yet. Open **Customize → Plugins →
> tb-fub-toolkit** and paste your Follow Up Boss API key.
> (In Claude Code: `/plugin configure tb-fub-toolkit`.)

Never invent a credential, and never send a request containing a literal
`${user_config.…}` string. A **401/403 means stop, not retry.**

> ⚠️ **This skill sends real SMS to real people.** See "Sending — hard limits" below before the first send.

## Sending — hard limits

Every send is a real SMS to a real person: billed, logged, and covered by TCPA.
A note created by mistake cannot be unsent — deleting the note does not recall
the message.

**Never, regardless of how the request is phrased:**

- **Text a contact tagged as opted out or unsubscribed.** Check the contact's
  tags before every send. Messaging someone who opted out is a legal problem,
  not a matter of etiquette, and it is the single most expensive mistake this
  skill can make.
- **Send to more than one contact without explicit confirmation that names the
  count.** "Text the replied list" is not authorisation to text 300 people.
  State the number, show three recipients by name and phone, and wait.
- **Loop over a list and send.** If you are writing a loop that sends, stop.
  Bulk outbound belongs in Texting Betty's own campaign tooling, which has
  throttling, opt-out suppression, and business-hour handling this skill does
  not.
- **Use `[now]` to work around business hours.** They exist for a reason, and
  a 6am text reads as spam. `[scheduled]` queues until the account opens.
- **Re-send after an ambiguous failure.** If you did not see a `201`, that is
  not proof nothing was sent. Verify the conversation before retrying, or you
  will double-text someone.

**Before the first send in any session,** confirm the recipient with the user
by name and phone number, and read the message back. Prefer a test contact
using the user's own number for anything experimental — a "test" message to a
live lead is a real cold text with real exposure.

If a send fails partway through a confirmed batch, report exactly how many went
out and to whom. Silence about a partial send is how the same person gets
texted twice.

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


Texting Betty sends outbound SMS when a **note** is created on a FUB contact whose body starts with a TB tag. No inbox/SMS API access is needed; the FUB API key can create notes.

## Mechanism

Create a note on the contact. **The tag must be the FIRST thing in the note body**, followed by the message text:

```
[scheduled] hello there
```

A note with the tag at the end (or missing) is ignored by TB.

## Credentials

| What | Value |
|---|---|
| FUB API key | `${user_config.fub_api_key}` |
| Auth | Basic auth: base64 of `key:` (colon, empty password) |
| Endpoint | `POST https://api.followupboss.com/v1/notes` |

## API call

`curl` is blocked in this environment, and Python needs an explicit CA file
or TLS verification fails. Both are handled below — use this shape.

```python
import base64, json, ssl, urllib.request

CTX = ssl.create_default_context(cafile="/etc/ssl/cert.pem")
KEY = "${user_config.fub_api_key}"
BASE = "https://api.followupboss.com/v1"   # generic host — no subdomain needed
H = {
    "Authorization": "Basic " + base64.b64encode((KEY + ":").encode()).decode(),
    "Content-Type": "application/json",
}
# Do NOT add "X-System": "fub-spa" — that impersonates FUB's own web app
# and can get the account flagged. Set X-System/X-System-Key only if FUB
# issued you an integration identifier.

# Confirm the key belongs to the configured account BEFORE writing anything
idreq = urllib.request.Request(f"{BASE}/identity", headers=H)
with urllib.request.urlopen(idreq, context=CTX, timeout=30) as r:
    print("account:", json.load(r))   # must match the configured account

body = json.dumps({"personId": 12345, "subject": "Texting Betty", "body": "[scheduled] hello there"}).encode()
req = urllib.request.Request(f"{BASE}/notes", data=body, headers=H, method="POST")
with urllib.request.urlopen(req, context=CTX, timeout=30) as r:
    print(r.status)  # 201 = note created; TB picks it up shortly
```

The `/identity` check matters more here than anywhere else in this plugin:
a key from the wrong FUB account will happily create a note — and send a
real text — against a contact in a **different tenant**. Verify first.

## Tag reference

| Tag | Result |
|---|---|
| `[scheduled]` | Send immediately if within business hours; otherwise as soon as business opens. Default choice. |
| `[now]` | Send immediately regardless. Avoid in action plans (can fire very early in the morning). |
| `[9am]`, `[9:30am]`, `[1pm]`, `[1:33pm]` | Send at that time; if the time already passed today, sends immediately. |
| `[5min]`, `[30min]`, `[1h]`, `[2h]` | Delay by that amount. |
| `[delete]` | Cancels a scheduled-but-unsent text. Deleting the note itself does NOT cancel the text; you must post a `[delete]` note. |

## Before sending

1. Confirm the contact: `GET /api/v1/people/{id}?fields=allFields` (same Basic auth). Check name and phone so the message goes to the right person.
2. Note the `AI OFF` tag if present: it disables AI replies but does not block outbound sends.

## Verifying the send

- FUB API key auth CANNOT read `/timeline`, `/inbox/*`, or `/people/{id}/inboxAppConversationsForReply` — they return 403. This toolkit is API-key only and holds no session cookie, so those endpoints are out of scope. **Do not ask the user for a browser cookie to work around it.**
- Instead use the conversation proxy:
  - `POST https://tb-proxy.vercel.app/api/conversation`
  - Header `Authorization: Bearer ${user_config.fub_api_key}` (Bearer here, Basic for FUB — same key, different scheme)
  - Body `{"personid": "<id>"}`
  - There is no owner email to pass; the proxy derives the routing key from your API key.
- The DB syncs after TB actually sends, so allow a minute or two before checking. An immediate empty result does not mean failure.

## Quirks learned the hard way

- Tag placement is strict: leading tag only. `hello [scheduled]` does nothing.
- 201 on the note only means the note saved; TB processing is async.
- Texts respect business hours per account, so an off-hours `[scheduled]` send queues until open.

