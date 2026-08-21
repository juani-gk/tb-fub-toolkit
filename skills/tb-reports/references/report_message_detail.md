# Report: Message Detail (a.k.a. Template Performance)

**What it answers:** which specific drip messages are earning their keep
(replies per opt-out cost) vs. which are drawing opt-outs for nothing, **and**
which automation/action plan/person is behind that - two different rollups
of the same underlying sends, both a required part of this report, not an
optional extra.

**Population:** `lastSentInboxAppMessage` filter (see shared_pipeline §2 -
this is the broad "who did we text" population; using the narrower
received-only filter would silently exclude every template that drew zero
replies, which is exactly the finding this report exists to surface).

**Template identity:** normalize by stripping greeting/signature/agent-
mention boilerplate by shape (shared_pipeline §4 - no per-contact name
lookups), not by `action_plan_id` or `created_by` alone - a single action
plan commonly bundles 2-3 distinct message steps under one label (seen in
practice: `action_plan_id 369` / `created_by "A2P10DLC Verified SMS"`
covering three unrelated message bodies). Group by the stripped text
itself.

**Only count drip sends** - exclude sends where both `automation_id` and
`action_plan_id` are null from the Sent tally and both groupings below
(shared_pipeline §5).

**Attribution:** walk each conversation chronologically; the next inbound
message after a drip send (skipping carrier noise) is attributed to that
send as Engaged or Opt-out. A reply following a send that's outside the
report window doesn't count toward any template or source in-window.

**Per-send fields to keep, before any grouping happens:** the stripped
template text (shared_pipeline §4) AND the source - `automation_id ??
action_plan_id` as the key, `created_by` as the display name
(shared_pipeline §6). Every send needs both, because the two tables below
are two independent group-bys over the exact same rows.

**Shared metrics** (identical formulas, applied per template row and per
source row):
- Sent, Engaged, Opt-outs
- Engaged rate = Engaged / Sent
- Opt-out rate = Opt-outs / Sent
- Engaged / opt-out ratio = Engaged / Opt-outs (show "no opt-outs" in muted
  text, no pill, when Opt-outs = 0 - don't divide by zero or invent a ratio)

## Table 1 - by template (wording)

Grouped by normalized text. Add a **Source** column showing which
automation/action plan/person sent that wording - usually one name,
occasionally more than one (a template row with multiple sources is
itself a finding worth calling out in the report text, since it means two
different sequences converged on the same copy).

Grade each row with the relative-to-group taxonomy (shared_pipeline §10),
the group being the overall judgeable population in this table - there's
no plan grouping here, so "the group" is everything in Table 1. Skip the
sequence badge (§9) and its notes; wording has no single position, since
the same text can appear at different steps across different plans.

"Enough responses to judge" vs. "not enough" is still a two-tier split
(shared_pipeline §8 for the floor) - rows below the volume floor land in
"not enough" per §10's step 1, same mechanism as before, just folded into
the richer taxonomy instead of a separate table split.

**Sort default:** ascending by Engaged/opt-out ratio (worst performers
first). Every column sortable on click; totals row stays pinned at the
bottom through any sort. Markup: `../assets/message_detail_shell.html`
(fill in, don't rebuild).

## Table 2 - by action plan ("Performance by Action Plan")

This is the "which automation/action plan performs better" view, and it's
a drill-down, not a flat rollup: an overview table ranking every action
plan/automation by size, each row linking down to that plan's own section
showing every distinct message **in the order it's actually delivered**,
graded against that plan's own average.

**This structure applies whenever the answer to a question requires
action-plan-level attribution, including an informal question like "why
are opt-outs high" - not only when someone names "the Message Detail
report."** Falling back to a flat by-source table (Sent/Engaged/Opt-outs
per plan, no sequence, no drill-down) is Table 2's *old, replaced* shape
(see `SKILL.md`'s note on this) - it is a spec violation here, not an
acceptable shortcut for a casually-phrased ask.

**Grouped by** `automation_id ?? action_plan_id`, labeled with
`created_by`. A source that sends several different templates is one row
in the overview and one full section below, with every one of those
templates as its own row inside that section - the opposite shape from
Table 1, which is why both exist.

**Overview table** - one row per plan, sorted biggest-first by Sent:
Action plan (linked) | Steps (distinct templates) | Sent | Engaged |
Opt-outs | Eng rate | Opt rate | Eng/opt, plus a totals row. State the
excluded non-plan tally (shared_pipeline §5) in this table's intro text,
by `created_by` category and count - not just "excluded."

**Per-plan section**, for each plan in the overview:
- **Header**: plan name: sends-to-*contacts* count (distinct from raw
  sends - a contact can receive the same step more than once on
  re-enrollment, so report both numbers), distinct-message count, count
  judgeable per §8's floor.
- **One-line synthesis**, generated from the plan's own numbers - e.g.
  which step carries the largest share of the plan's opt-outs, which
  carries the largest share of its replies, how many of its messages drew
  no response at all and their combined sends. Every number in this
  sentence must be computed, never invented or estimated.
- **Plan-wide stat callouts**: Engaged, Opt-outs, Engaged/opt-out ratio.
- **Sequence table**: Step (sequence badge + gap since previous,
  shared_pipeline §9) | Message (full text) + grading pills (§10) +
  narrative note (§11) | Sent | Engaged | Opt-outs | Eng rate | Opt rate |
  Eng/opt, with a plan-total row.

**Time window**: default 30 days, always compute the longer window too
(shared_pipeline §2) and toggle between them - don't build only one.

**Legend card**: define every pill label in one place at the top of this
table's output, in plain language, before any plan section - a reader
hitting "High opt-out" for the first time needs the definition close by,
not buried in a footnote at the bottom.

**"How to read this" closing note**: state the sequence-position
methodology (median rank across contacts, §9), the not-enough-volume
floor in plain language, why two windows exist, and the attribution rule
(a reply is attributed to the last message sent before it, so a reply
arriving after a human or the AI assistant has already jumped into the
thread counts against whichever of those sent last, not the original
drip step).

**Output format:** `../assets/performance_by_action_plan_shell.html` -
overview table with anchor links into per-plan sections, a legend card,
the window toggle, and the closing note card. This is a genuinely
different layout from Table 1's flat sortable table, which is why it's a
separate shell file rather than a second table pair in the same one.
