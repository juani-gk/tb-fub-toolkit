# Report: Opt-Outs vs. Replies

**What it answers:** over a time window, how many genuine replies came in
vs. how many were opt-outs, and how does that split trend day by day.

**Population:** `lastReceivedInboxAppMessage` filter (see shared_pipeline §2
 - this report is about who replied, so the narrower filter is correct here,
unlike Message Detail).

**Classification:** per shared_pipeline §7. Each in-window inbound message
is either an opt-out, noise (drop it), or a genuine reply.

**Source attribution:** attribute each classified reply to the drip send
immediately before it (shared_pipeline §6 - last-touch, at the message
level, same rule `reply-check` uses). Add an optional **by-source table**
below the KPI row/chart - source name, replies, opt-outs, opt-out share of
repliers - when the ask is a comparison ("which automation is causing
opt-outs") or when one source's share is noticeably off from the account-
wide number; otherwise leave it out, since this report's main point is the
day-by-day trend, not a source leaderboard (that's what Message Detail's
by-source table is for). If you do include it, the same share-of-repliers
caveat applies: it's not a conversion rate without a per-source send count.

**Aggregation:** bucket by calendar day. Two counts per day: replies,
opt-outs. Zero-activity days stay in the series as zero, not omitted -
the report should show the account's actual rhythm, including silence.

**Form:** per the dataviz skill's form heuristic, this is "trend over
time, tell distinct series apart" territory. Prefer a **bar chart over a
line chart** here specifically: at low volume (a handful of events across
a 30-day window is common), a connected line between two single-day spikes
visually implies a ramp-up/ramp-down that isn't real - one isolated
Tuesday looks like a mountain instead of a single dot. Bars keep each
day's count honestly independent. Reserve a line for accounts with dense
enough daily volume that interpolation between points is actually
meaningful.

**KPI row:** total replies, total opt-outs, opt-out share of repliers (=
opt-outs / (replies + opt-outs), not opt-outs / sends - the share is
"of the people who said something back, how many said stop," not "of
everyone contacted"). Known benchmark worth citing in the report: 30–40%
opt-out share of repliers is typical for cold outbound SMS; notably
higher usually signals a burned list or overly aggressive copy - but
don't state this as fact for an account with a small sample (say so).

**Small-sample handling:** if the window's total reply+opt-out count is in
the low double digits or less, say so plainly in the report's own text
("N contacts, M inbound messages this window - treat the daily pattern as
directional, not statistically robust") rather than letting a sparse chart
imply more confidence than the data supports.

