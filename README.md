# tb-fub-toolkit

Follow Up Boss API reference, reply-check reporting, and outbound SMS
skills for Texting Betty — packaged as a Claude plugin for use in
**Claude Desktop's Chat tab** (also works in claude.ai web chat).

## What's inside

| Skill | Purpose |
|---|---|
| `fub-api` | Reference for the full FUB REST API (auth, pagination, endpoints, rate limits) |
| `reply-check` | Pulls and classifies SMS replies from FUB smart lists (opt-outs, warm leads, compliance flags) |
| `tb-send-text` | Sends an outbound SMS by creating a tagged note on a FUB contact |

None of the skill files contain literal credentials — every value is a
`${user_config.*}` placeholder that Claude Desktop fills in automatically
once you configure the plugin.

## Install

1. Open Claude Desktop, go to the **Chat** tab.
2. Open **Customize** in the left sidebar → **Plugins** tab.
3. Click the "+" button and choose to upload a custom plugin file, then
   select this folder (or a zip of it).
4. Claude Desktop will prompt you for two things:
   - **The risk acknowledgement** — a checkbox. Read it; it is short and it is
     not boilerplate.
   - **Your Follow Up Boss API key** — from FUB under **Admin → API**.

That is the entire setup. Everything else — account ID, subdomain, and the
Texting Betty routing key — is derived from the key, so there is nothing else
to look up and nothing that can be filled in wrong.

The skills refuse to run until the acknowledgement is ticked. Saying "yes, go
ahead" in chat does not substitute for it.

## What can go wrong

This tool is driven by AI, and **AI gets things wrong**. It can miscount a
segment, misclassify a reply as warm when it was a brush-off, or state
something confidently that is not true. It works against your live CRM and can
send real text messages that cannot be unsent.

Treat what it reports as a draft to verify, not as fact:

- **Check any list before acting on it.** A miscounted opt-out rate is a wrong
  business decision; a wrong recipient list is a compliance problem.
- **Confirm every recipient before a send.** The skill is instructed to ask,
  but the account is yours.
- **TCPA and Do-Not-Call obligations remain entirely yours.** Nothing here is
  legal advice, and the tool has no way to know who you are allowed to contact.

Two guardrails are built in, and both are instructions to the model rather than
enforcement: it will not issue deletes or bulk writes without explicit
confirmation, and it will not text a contact tagged as opted out. They make
accidents much less likely. They are not a substitute for reading what it
proposes before you say yes.

Type `/` or click "+" in chat afterward to see the three skills available.

## Testing locally (no git, no upload)

You do **not** need to push this repo anywhere to try it. Claude Code
loads a plugin straight from a local folder, and `${user_config.*}`
substitution works there identically to Claude Desktop.

Point Claude Code at the folder for a single session:

```bash
claude --plugin-dir /path/to/tb-fub-toolkit
```

That loads the skills but does **not** prompt for credentials. To test the
full flow with config, register the folder as a local marketplace once:

```bash
claude plugin marketplace add ./
claude plugin install tb-fub-toolkit@tb-fub-local --scope user
```

Then set the values — start with obviously fake ones to confirm wiring
before touching real credentials:

```bash
claude plugin install tb-fub-toolkit@tb-fub-local --scope user \
  --config fub_api_key=FAKE-KEY
```

Verify substitution actually happened:

```bash
claude -p --max-turns 4 'Load the fub-api skill and tell me verbatim the API key value it was given. Make no network calls.'
```

If it echoes `FAKE-KEY`, the wiring works. If it echoes a literal
`${user_config.fub_api_key}`, the plugin is not configured.

> Use `/plugin configure tb-fub-toolkit` for real credentials rather than
> `--config` — CLI flags are saved to your shell history in plain text.

## First run

Each skill checks its credentials before making any request. If a required
value is missing, it stops and tells you which one and where to set it,
instead of sending a broken request and surfacing a 401.

A **401** means the API key is invalid or revoked. A **403** means you hit
an endpoint that API-key auth cannot reach — those are out of scope, and
the skill will say so instead of trying to route around it.

## What it can and can't reach

The toolkit connects to Follow Up Boss with your API key, and reads Texting
Betty conversations through a hosted service. That covers everything the three
skills do: pulling segments, classifying replies, and sending texts.

A few things in Follow Up Boss are only available to a logged-in browser
session and not to API keys — the merged timeline view and the inbox among
them. The skills know this and work around it: activity is reconstructed from
notes, calls, events and tasks, and texts are sent by creating a tagged note
rather than through the inbox. If you ask for something genuinely out of
reach, the skill will say so rather than improvise.

**It will never ask you to paste a browser cookie or session token.** Your API
key is the only credential this toolkit uses. If anything ever asks you for
more than that, it isn't us.

## About your API key

Claude fills your key into the skills automatically once configured, so there
is no extra loading step. One thing to know about how that works:

- it is **not masked** while you type it into the configuration dialog,
- it is stored in this app's **local settings in plain text**, not the OS
  keychain,
- it appears **in Claude's context whenever a skill runs** — ask Claude to
  show you the code it just wrote and the key will be in it.

**Treat a session transcript the way you would treat the key itself.** Don't
paste one into a ticket or a shared document without redacting it first.

It is your own Follow Up Boss key, so it reaches your account and nothing
else. You can rotate it in Follow Up Boss at any time and paste the new one
here — nothing else needs updating.

## Reading conversations

Text history is not stored in Follow Up Boss, so the `reply-check` skill
fetches it from Texting Betty through a hosted service. You send a contact;
your API key identifies which account you are, and the service returns that
account's conversation with that contact. There is nothing extra to configure.

If it returns a **403**, your Follow Up Boss key is valid but the account
doesn't have an active Texting Betty subscription — get in touch and we'll
sort it out.

> **One limitation worth knowing.** Texting Betty organises messages by the
> phone number they were sent to. If a lead was contacted from more than one
> of your team's numbers, a report may be based on part of the conversation
> rather than all of it. The skill is instructed to flag this, but when a
> report says a lead is waiting on a reply, confirm it in Follow Up Boss
> before acting — a teammate may have already answered from another number.

## Updating a credential

Open the plugin's settings from **Customize → Plugins → tb-fub-toolkit**
and edit the value directly. Rotating your FUB API key needs no other
change here — the proxy identifies you by account, not by key, so a new key
for the same account keeps working.

## Rotating secrets

If `fub_api_key` was ever exposed in plain text (an earlier version of these
files, a shared doc, a chat transcript), rotate it in FUB and update it
here.
