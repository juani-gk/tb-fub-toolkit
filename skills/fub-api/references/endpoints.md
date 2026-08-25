# FUB endpoint reference

Lookup data for `fub-api`'s skill file: request shapes, parameters and
response fields per endpoint. Read this when you need a specific endpoint,
not on every invocation - the rules that matter regardless of endpoint
(auth, rate limiting, pagination, the destructive-operation limits) live in
`../SKILL.md` and are always loaded.

Nothing here overrides that file. In particular: never hardcode an ID that
this account is supposed to supply, and a 401/403 is a stop, not a retry.

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
- `publishedInboxAppsForContact` - active embedded app conversations
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

`conditions` is an **array of arrays** - the nesting is required.

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
hundred full person objects - every custom field, every phone, every timestamp -
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

Returns only lists visible to the authenticated user. To find ALL lists (including team-specific ones): scan IDs 1–250 individually - most will 404, which is fine.

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
lists - segmentation is often done by *tag* instead. Discover tag names from
the `tags` array embedded on person objects you already have (from
`/people`, `/people/filter`, or `GET /people/{id}`), or ask the user for the
exact tag name.

Tags whose names encode TB state (engagement, unsubscribe) identify the
contacts with messaging history. Filter people by tag with
`GET /people?tags=<name>&idsOnly=true`. For a full reply-analysis task,
invoke the `reply-check` skill instead of reimplementing this filter +
classify workflow here - it already has both paths built.

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
- `tags` - operators: `include any of`, `do not include any of` (val = array of tag IDs)
- `stage` - `is equal to` (val = array of stage IDs)
- `lastCommunication` - `was more than` (num = days, unit = "days")
- `assignedUserId` - `is any of` (val = array of user IDs)
- `phone` - `is not bad`
- `inboxAppMessagesReceived` - `is less than`

---

### Get Single Smart List

```
GET /smartLists/{id}
```

---

## Tags

Tags are account-specific. Discover them from the `tags` array embedded on
person objects (returned by `/people`, `/people/filter`, or
`GET /people/{id}`) rather than hardcoding IDs or names in a skill. Common
built-in or convention-based tags include things like `Import` (imported
contact), an "engaged with the SMS platform" tag, and an "AI messaging
disabled" tag, but exact names and IDs vary per account.

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
result - user IDs and names are account-specific and should be looked up
live, not hardcoded in a skill.

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

## Deals / Pipelines

```
GET /pipelines
GET /deals?personId={id}&limit=100&offset=0
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
GET /categories
GET /timeframes
GET /callLists
```

---
