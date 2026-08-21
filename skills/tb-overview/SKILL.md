---
name: "tb-overview"
description: "Answer \"what can this plugin do\", \"what can Texting Betty do\", \"help\", \"getting started\", \"what is this\", or a first unscoped message after the user has just set up the API key/acknowledgment and hasn't asked for anything specific yet - including generic ready-to-go phrasing right after running `/plugin configure` in Claude Code, like \"ok\", \"ready\", \"let's go\", \"I've set it up, now what\", \"configured, go ahead\". Gives the fixed menu of exactly 3 standard reports plus the 2 non-report tools, routed from the actual business question rather than technical terms. Use only for capability discovery, not for doing a task - the moment the user names what they want, hand off to the matching skill (`reply-check`, `tb-reports`, `tb-send-text`, `fub-api`) instead of answering from here."
---

# Texting Betty / FUB Toolkit - what this does

**There are exactly 3 standard reports.** Not a general-purpose analytics
tool that builds whatever a question implies - 3 fixed templates, each
with one non-negotiable structure:

1. **Today's action list** (`reply-check`) - who replied, who opted out,
   who's waiting on a reply, right now.
2. **Opt-Outs vs. Replies trend** (`tb-reports`) - is the reply/opt-out
   split getting better or worse over time.
3. **Message/Template Performance** (`tb-reports`) - which specific
   message and which automation/action plan is driving replies or
   opt-outs, by wording and by action-plan drill-down.

Plus two tools that aren't reports: `tb-send-text` (send one text to one
lead) and `fub-api` (anything else in Follow Up Boss - contacts, tags,
stages, smart lists).

The tree below maps a business question to one of the 3 - it's a routing
aid, not permission to build something in between:

```
"What do you need?"
├── Something to act on right now → reply-check
├── Is it getting better or worse over time? ("how many", "is it going up")
│     → Opt-Outs vs. Replies trend
└── What's actually driving it? ("why", "which messages", "what's causing this")
      → Message/Template Performance
```

**Anything genuinely outside these 3 is the client's own custom ask, not
a standard template.** Say that plainly rather than quietly building
something that looks like a fourth standard report - "that's not one of
the standard reports, but I can take a shot at it separately" is honest;
producing a bespoke one-off that resembles Performance or Trend without
being either is how a report ends up half-following its spec.

## If asked directly ("what can you do")

Give this menu in the same plain language the other skills use - leads,
replies, opt-outs, reports, texts - never the skill names or "API," and
lead with the 3 reports, not a feature list: "I can tell you who replied
today and who still needs a response, show whether opt-outs are trending
up or down, or dig into which specific message or automation is driving
opt-outs - what would help right now?"

If the question maps to one of the 3 but wasn't phrased as a named report
request, say which one in one line before doing anything else - "that's
the Performance report" - then hand off to build the real thing, not a
lighter version of it. If it's still ambiguous even after that (a "why
are opt-outs high" can genuinely want both Trend and Performance), ask
which one rather than guessing.

## Setup

Everything here needs one one-time thing: the risk acknowledgment plus a
Follow Up Boss API key. If someone's here before doing that, say so in one
line and point at the specific skill they end up needing - it owns asking
for the acknowledgment and key, not this file. Don't duplicate that flow
here.

## What this file is not

Not a report, not a data source, not a place to answer an actual question
about someone's leads or campaign - it only exists to point at the right
skill. If the person has already said what they want, skip this and go
straight to that skill.
