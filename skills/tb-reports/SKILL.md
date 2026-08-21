---
name: "tb-reports"
description: "Build Texting Betty performance reports as branded, sortable HTML - opt-outs vs. replies trend, and per-template message/drip performance broken out by both wording and by source (automation/action plan/person). Use whenever the user asks \"how's my opt-out rate looking\", \"is my opt-out rate going up\", \"check template performance\", \"which messages are earning\", \"which automation/action plan performs better\", \"opt-outs vs replies\", wants a Texting Betty report/dashboard, or asks to schedule either of these to run recurringly. For unanswered warm leads / missed follow-ups, use `reply-check` instead - it already covers that as its Needs Action list. Covers the full pipeline (FUB population filters, conversation fetch, classification, threshold calibration) plus the shared Texting Betty brand design system so every report reads as one consistent product."
---

# Texting Betty Reports

This skill produces a small family of report types, not one fixed report.
They share almost everything - data pipeline, brand styling, threshold
philosophy - and differ only in population, classification, and layout.
Read this file for the shared parts, then the one `references/report_*.md`
file for whichever report type was actually asked for.

## Report types

| User asks for... | Reference | One-line summary |
|---|---|---|
| "opt-outs vs replies", "how's my opt-out rate looking", "is it going up" - descriptive, over time | `references/report_optouts_vs_replies.md` | Daily trend of genuine replies vs. opt-outs, with a KPI summary |
| "template performance", "which messages are earning", "which automation/action plan performs better", "why are people opting out", "what's causing this" - diagnostic, attributes to a cause | `references/report_message_detail.md` | Sent/Engaged/Opt-out breakdown ranked by engaged-per-opt-out - Table 1 by message wording, Table 2 a drill-down by automation/action plan showing every step in sequence, both required |

**Routing cue:** "is it going up" / "how many" → Trend (descriptive). "why" / "which" / "what's causing" → Performance (diagnostic - it's the only one of the two that attributes to a specific message or source). If someone asks "why" without having established there's actually a problem, a quick "has it actually gone up, or does it just feel high?" before jumping to Performance is worth it.

**These two report types have exactly one structure each - there is no
lighter, informal, or "quick diagnostic" version, no matter how casually
the question was asked.** A question phrased as a one-off ("why are so
many people opting out?") gets the *exact same* report as one phrased as
a direct request ("build me the Performance report") - same tables, same
shells, same everything. This is not a style preference; it's the fix for
a real failure: asked informally, this skill once produced a bespoke
"Opt-Out Spike Diagnostic" page that borrowed pieces of the real spec
(the grading pills, the narrative notes) but skipped the entire
action-plan drill-down and used the wrong shell entirely - a flat by-
source table standing in for `performance_by_action_plan_shell.html`'s
sequence-ordered, dual-window, drill-down structure. **If the full
structure feels like overkill for how the question was asked, that
feeling is the trap, not a signal to simplify.** Build the whole thing.

**When a question maps to one of these two but wasn't phrased as a named
report request, say which one in one line before pulling any data** -
"That's answered by the Performance report - building it now." Not a
question to wait on, just a heads-up so the mapping is visible instead of
silently decided. If the request doesn't clearly match either one, ask
which report type before pulling any data - don't guess and build
something in between.

**"Missed opportunities" / "dropped leads" / "who didn't get followed up
on" is not a report type here** - that's `reply-check`'s Needs Action list
(unanswered warm reply, unfulfilled promise, scheduling mismatch, sorted by
staleness). Point there instead of building a parallel version of it.

## Preflight (identical across all report types)

Same acknowledgment + API key configuration as `reply-check` and
`fub-api` - don't duplicate that flow here, follow it as written in
those skills. Call `/identity` first, always.

## Shared pipeline

`references/shared_pipeline.md` - population filters, conversation fetch
mechanics, the date-parsing gotcha, name normalization for templates,
drip-vs-manual send detection, classification regexes, and the threshold-
calibration rule (**check the account's real volume distribution before
applying any floor - never default to numbers from a different account's
example**). Read this before writing any data-pulling code, regardless of
which report type you're building.

## Brand design system

`references/tb_design_tokens.css` - the validated Texting Betty palette
(light mode only) and reusable CSS classes (`.tb-card`, `.tb-pill-*`,
`.tb-btn-primary`, etc.), including `--tb-ratio-pos` and `.tb-pill-mid`
for the neutral "in line with the group" case (shared_pipeline §10) - a
ratio number's positive/negative reads on its own blue/red axis, kept
visually distinct from the good/critical pill pair so the two systems
don't get conflated. Two source facts worth knowing before you touch
colors:

1. **UI chrome vs. chart marks are different colors, on purpose.** The raw
   brand hues (`--tb-brand-primary` coral, `--tb-brand-accent` gold) are
   correct for buttons, pill backgrounds, and large fills - that's how the
   client's own site uses them. They are NOT safe as thin chart marks
   (bars, lines, small dots): tested against a white surface, the raw gold
   fails contrast outright. Use `--tb-series-1`/`--tb-series-2` (depth-
   stepped versions of the same two hues) for any actual data mark.
2. **The two brand hues sit close together in hue angle** (both warm:
   coral and gold). Naively darkening both by the same amount to fix
   contrast makes them collapse into indistinguishable under red-green
   colorblindness - confirmed by testing, not assumed. The chart-safe
   pair in the tokens file uses *asymmetric* depth (one barely stepped,
   one stepped much further) specifically to preserve separation. If the
   client ever sends a 3rd brand hue, re-run
   `dataviz`'s `scripts/validate_palette.js` on the new combination before
   using it in a chart - don't assume a 3rd color is automatically safe
   just because two colors were made to work.

Dark mode is deliberately **not supported** - the client's site is light-
mode only and dropping dark mode was an explicit simplification choice.
Don't add it back in without being asked.

If a fuller brand CSS file arrives later (fonts, spacing, radii), update
only the "brand source" block in `tb_design_tokens.css` and re-validate
before propagating - see the comment at the top of that file.

## Report shells (fill in, don't rebuild)

- `assets/message_detail_shell.html` - sortable Table 1 (by wording) only
- `assets/performance_by_action_plan_shell.html` - Table 2: overview table
  linking into per-plan drill-down sections (sequence order, relative
  grading, narrative notes, dual time-window toggle) - a genuinely
  different layout from a flat sortable table, which is why it's a
  separate file. Has an HTML-comment template at the bottom showing the
  exact one-plan-section markup to repeat; that comment is structural
  only, never real content from any account.
- `assets/optouts_vs_replies_shell.html` - KPI row + bar chart + table-view
  toggle for Opt-Outs vs. Replies
- `assets/reply_check_shell.html` - belongs to `reply-check`, not a
  `tb-reports` report type; lives here only because the design system
  does. `reply-check` builds this **on request only**, never by default -
  see that skill's "Optional: a shareable report" section.

All four use `%%PLACEHOLDER%%` markers. Read the file, replace every
placeholder (title, subtitle, row HTML, daily-data JSON, etc.), and render
 - these already encode the mark specs, pill conventions, sortable-column
JS, and pinned-totals-row behavior worked out against real accounts.

**All three shells are body content, not full documents** - `<title>` +
`<style>` + markup + `<script>`, deliberately with no `<!doctype>`,
`<html>`, `<head>`, or `<body>` tag of their own. That's not a stray
omission - the `Artifact` tool's own contract requires content-only,
supplying its own `<head>`/`<body>` skeleton at publish time; publishing a
shell WITH its own nested wrapper is a real, separately-observed failure
mode. Fill in placeholders on the file exactly as it is; don't add
wrapper tags before publishing.

**Every shell's font must be set on `.tb-report` itself, never on `html`
or `body`.** `--tb-font` is a custom property scoped inside `.tb-report`'s
own declaration block (`tb_design_tokens.css`'s comment above that rule
has the full explanation) - it is invisible to `html`/`body`, which are
`.tb-report`'s *ancestors*, not its descendants. A real, observed bug: two
shells referenced `var(--tb-font)` from `html, body` "for extra safety,"
which is invalid there and silently fell back to the browser's serif
default - a completely different failure from the wrapper-tag one above,
and one that survived a first attempted fix because it looked like the
same symptom. If you ever need the font set outside `.tb-report`, move
the variable to `:root` instead (visible everywhere) rather than
reaching for `html, body { font-family: var(--tb-font) }` again.

**No em-dashes in anything written into a placeholder** - title, subtitle,
headline sentence, footnote, KPI callout, any narrative text. Use a hyphen,
comma, colon, or a new sentence instead. This is a rule about what gets
generated fresh on every run, not a one-time formatting pass.

## Delivery

Published via the `Artifact` tool (load the `artifact-design` skill first,
per its own rules - it decides how much design polish a given ask
warrants), passing the filled-in shell **exactly as it is, content-only,
no added wrapper tags** - see the note above. That gets the user a link
they can reopen and re-check later; a report someone will check again is
exactly the persist-by-default case.

If `Artifact` isn't available in the session, say so and fall back to
writing a file instead - but a bare fragment isn't a valid standalone
file, so wrap the *same* filled-in content in a minimal document at that
point: `<!doctype html><html><head><meta charset="utf-8"></head><body>` +
the fragment + `</body></html>`. Do this wrapping only for the file
fallback, never for the `Artifact` path, and never bake the wrapper into
the shell files themselves.

## Scheduling

`references/scheduling.md` - how to set these up as recurring scheduled
routines via the `RemoteTrigger` tool, with a suggested (never silently
applied) default cadence per report type. **This only works in a Claude
Code app/web session backed by Anthropic's hosted infrastructure** - a
bare local terminal session has nothing to run the routine on. Check that
`RemoteTrigger` is actually reachable (`ToolSearch` if deferred) before
offering to schedule anything; if it isn't there, say plainly that
scheduling isn't available in this session rather than improvising one.
Always run at least one manual report and get the user's sign-off on
population/thresholds before offering to schedule it.

## Verification before delivering any report

- [ ] Totals row / KPI numbers cross-checked against the raw per-row data
      (sum the rows yourself, don't trust a single computed pass)
- [ ] Threshold choice stated in the report's own text, with excluded-row
      count and combined volume - never a silent cutoff
- [ ] Population filter matches the report's actual question (shared_pipeline §2)
- [ ] Rendered and screenshotted (or opened) - checked for label collisions,
      sort behavior, and that the totals row stays pinned through a sort
