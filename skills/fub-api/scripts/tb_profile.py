#!/usr/bin/env python3
"""Compute this account's own distributions, so thresholds are not guessed.

Shared by `reply-check` and `tb-reports`. Reads a local conversations file -
no API key, no network.

  python3 tb_profile.py suggest --convs conversations.json
  python3 tb_profile.py save  --account 12345 --from profile.json
  python3 tb_profile.py load  --account 12345 --convs conversations.json

shared_pipeline.md §8 and §11 both say the same thing: never carry a number
from another account, compute this one's real distribution first. That is
arithmetic, and doing it by reading messages in context is slow and
approximate. This script does the arithmetic and prints a sample for the
parts that genuinely need judgement.

**It suggests; it does not decide.** §8 requires you to state the floor you
land on and how many rows it excludes, and to confirm a recalibration with
the user rather than silently picking one. The candidate table below gives
you exactly those numbers - the choice, and saying it out loud, is still
yours. The same goes for the length threshold: "long for this account" is a
judgement about its writing style, informed by the percentiles here.

The sampled messages are for deriving this account's greeting, sign-off and
opt-out wording (§4, §7). Read them; do not assume another account's shapes.

`save` and `load` keep what you derived, so a second run in the same session
does not repeat the reading. This is a cache of *judgement*, which makes it
more dangerous than a cache of data: a profile that no longer matches how the
account writes produces a report that is wrong and looks fine. So `load`
refuses quietly-stale profiles - it warns past --max-age-days, and it compares
the stored population shape against the current one and flags a large drift.
Whatever it prints as "calibration:" belongs in the report's own text, so a
reader can see how old the numbers behind it are.
"""

import argparse
import collections
import json
import os
import random
import re
import statistics
import sys
from datetime import date, datetime


def announce():
    here = os.path.dirname(os.path.abspath(__file__))
    manifest = os.path.normpath(os.path.join(here, "..", "..", "..",
                                             ".claude-plugin", "plugin.json"))
    try:
        with open(manifest) as f:
            v = json.load(f).get("version", "?")
    except Exception:
        v = "unknown (no plugin.json above %s)" % here
    print("tb-fub-toolkit %s  -  %s" % (v, __file__), file=sys.stderr)


def load(path):
    with open(path) as f:
        data = json.load(f)
    out = {}
    for pid, v in data.items():
        # tb_fetch writes {id: [texts]}; tolerate an older {id: {"texts": [...]}}
        out[pid] = v if isinstance(v, list) else (v or {}).get("texts") or []
    return out


def is_drip(m):
    """shared_pipeline §5: automated only if it carries one of the two ids."""
    return m.get("automation_id") is not None or m.get("action_plan_id") is not None


def pct(values, p):
    if not values:
        return 0
    values = sorted(values)
    k = max(0, min(len(values) - 1, int(round((p / 100.0) * (len(values) - 1)))))
    return values[k]


def cmd_suggest(args):
    convs = load(args.convs)
    sent = [m for t in convs.values() for m in t if m.get("direction") == "sent"]
    recv = [m for t in convs.values() for m in t if m.get("direction") == "received"]
    drip = [m for m in sent if is_drip(m)]
    manual = [m for m in sent if not is_drip(m)]

    print("\n== population ==")
    print("  contacts %d | sent %d | received %d" % (len(convs), len(sent), len(recv)))
    print("  drip sends %d | manual sends %d" % (len(drip), len(manual)))

    # §5 wants the manual tally stated in the report, by created_by.
    if manual:
        tally = collections.Counter((m.get("created_by") or "(unnamed)") for m in manual)
        print("\n== manual sends, by sender (§5 - state this in the report) ==")
        for name, n in tally.most_common(12):
            print("  %6d  %s" % (n, name))
        if len(tally) > 12:
            print("  %6d  (%d more senders)" % (sum(n for _, n in tally.most_common()[12:]), len(tally) - 12))

    # §11 - "long for this account" is relative to its own writing.
    lens = [len(m.get("body") or "") for m in drip]
    if lens:
        print("\n== drip message length (§11 - 'runs long' is relative to this) ==")
        print("  median %d | p75 %d | p90 %d | p95 %d | max %d"
              % (statistics.median(lens), pct(lens, 75), pct(lens, 90), pct(lens, 95), max(lens)))
        print("  a 'runs long' flag at p90 would flag %d of %d sends"
              % (sum(1 for x in lens if x >= pct(lens, 90)), len(lens)))

    # §8 - the send-count distribution per source, and what each floor costs.
    by_source = collections.Counter()
    for m in drip:
        key = m.get("automation_id") or m.get("action_plan_id")
        by_source[key] += 1
    counts = sorted(by_source.values(), reverse=True)
    if counts:
        print("\n== sends per source (§8 - check before applying any floor) ==")
        print("  sources %d | biggest %d | median %d | smallest %d"
              % (len(counts), counts[0], statistics.median(counts), counts[-1]))
        print("\n  floor   sources kept   excluded   sends excluded")
        for f in (3, 5, 10, 20, 40, 50):
            kept = [c for c in counts if c >= f]
            exc = [c for c in counts if c < f]
            flag = "   <- excludes everything" if not kept else ""
            print("  %5d   %11d   %8d   %14d%s" % (f, len(kept), len(exc), sum(exc), flag))
        print("\n  Pick the floor from this table, say which one you picked, and"
              "\n  say how many rows and how many sends it drops (§8).")

    # §7 - short inbound messages are where opt-out wording shows up.
    shorts = collections.Counter()
    for m in recv:
        b = re.sub(r"\s+", " ", (m.get("body") or "")).strip()
        if 0 < len(b) <= 25:
            shorts[b.lower()] += 1
    if shorts:
        print("\n== most common short replies (§7 - derive opt-out wording from these) ==")
        for b, n in shorts.most_common(15):
            print("  %4d  %r" % (n, b))

    # §4 - the shapes that need a human read, not arithmetic.
    if drip:
        rng = random.Random(args.seed)
        sample = rng.sample(drip, min(args.sample, len(drip)))
        print("\n== %d sampled drip sends (§4 - read these for greeting/sign-off shape) ==" % len(sample))
        for m in sample:
            b = re.sub(r"\s+", " ", (m.get("body") or "")).strip()
            print("  - %s" % (b[:220] + ("…" if len(b) > 220 else "")))

    print("\nNothing above is a decision. State the floor and the length"
          "\nthreshold you chose, and what they exclude, in the report itself.")


# --------------------------------------------------------------------------
# Saved profiles - a cache of judgement, handled accordingly.

PROFILE_DIR = ".tb-profile"
REQUIRED = ("account_id", "derived_on")


def profile_path(account):
    return os.path.join(PROFILE_DIR, "%s.json" % account)


def cmd_save(args):
    with open(args.source) as f:
        prof = json.load(f)

    prof["account_id"] = str(args.account)
    prof.setdefault("derived_on", date.today().isoformat())

    # A regex that does not compile would fail much later, inside an
    # analysis, where the cause is far from the symptom.
    for k, v in prof.items():
        if k.endswith("_re") and isinstance(v, str):
            try:
                re.compile(v)
            except re.error as e:
                sys.exit("%s is not a valid regex: %s" % (k, e))

    os.makedirs(PROFILE_DIR, exist_ok=True)
    with open(profile_path(args.account), "w") as f:
        json.dump(prof, f, indent=1, sort_keys=True)
    print("saved %s (derived_on %s)" % (profile_path(args.account), prof["derived_on"]))


def cmd_load(args):
    path = profile_path(args.account)
    if not os.path.exists(path):
        print("no saved profile for account %s - derive one with `suggest`, "
              "then `save` it." % args.account)
        sys.exit(2)

    with open(path) as f:
        prof = json.load(f)
    for k in REQUIRED:
        if k not in prof:
            sys.exit("%s is missing %r - treat it as unusable and re-derive." % (path, k))

    stale = False
    try:
        age = (date.today() - datetime.fromisoformat(prof["derived_on"]).date()).days
    except ValueError:
        sys.exit("%s has an unreadable derived_on (%r)." % (path, prof["derived_on"]))

    if age > args.max_age_days:
        stale = True
        print("STALE: calibrated %d days ago (limit %d). Re-derive with "
              "`suggest` before using these numbers, or say plainly in the "
              "report that the calibration is this old." % (age, args.max_age_days))

    # A profile can also go stale because the account changed, not the clock.
    if args.convs and "derived_from" in prof:
        convs = load(args.convs)
        now_drip = sum(1 for t in convs.values() for m in t
                       if m.get("direction") == "sent" and is_drip(m))
        was = (prof["derived_from"] or {}).get("drip_sends")
        if was and now_drip:
            drift = abs(now_drip - was) / float(was)
            if drift >= args.max_drift:
                stale = True
                print("DRIFT: %d drip sends now vs %d when calibrated (%.0f%%). "
                      "The account's volume moved enough that the floors may "
                      "no longer fit - re-check §8." % (now_drip, was, 100 * drift))

    print("calibration: account %s, derived %s (%d days old)%s"
          % (prof["account_id"], prof["derived_on"], age, " - STALE" if stale else ""))
    print(json.dumps(prof, indent=1, sort_keys=True))
    sys.exit(1 if stale else 0)


def main():
    announce()
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("suggest")
    p.add_argument("--convs", required=True)
    p.add_argument("--sample", type=int, default=20)
    p.add_argument("--seed", type=int, default=42)
    p.set_defaults(fn=cmd_suggest)

    p = sub.add_parser("save")
    p.add_argument("--account", required=True)
    p.add_argument("--from", dest="source", required=True,
                   help="JSON file holding what you derived")
    p.set_defaults(fn=cmd_save)

    p = sub.add_parser("load")
    p.add_argument("--account", required=True)
    p.add_argument("--convs", help="compare stored population shape against this")
    p.add_argument("--max-age-days", type=int, default=7)
    p.add_argument("--max-drift", type=float, default=0.5)
    p.set_defaults(fn=cmd_load)

    args = ap.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
