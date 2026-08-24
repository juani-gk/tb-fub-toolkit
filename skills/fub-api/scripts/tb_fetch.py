#!/usr/bin/env python3
"""Pull FUB contact IDs and Texting Betty conversations.

Shared by `reply-check` and `tb-reports`. Run it; do not rewrite it inline.
Everything here is mechanical - no per-account judgement lives in this file,
which is why it can be a fixed script at all. Classification, thresholds and
grading stay in the skills, where they get recalibrated per account.

The API key comes from the FUB_API_KEY environment variable and is never
written to disk. Do not paste it into this file or into any file this script
produces.

  export FUB_API_KEY='...'

  # who is this key, and what account
  python3 tb_fetch.py identity

  # the population: contact ids only
  python3 tb_fetch.py ids --days 30 --field lastSentInboxAppMessage --out ids.json

  # the conversations, concurrent and resumable
  python3 tb_fetch.py convs --ids ids.json --out conversations.json

Which --field to use is the report's decision, not this script's:
lastReceivedInboxAppMessage is "who answered", lastSentInboxAppMessage is
"who did we text at all". Picking the narrow one for a template-performance
report silently drops every template that drew zero replies.

`convs` is safe to re-run: it reads --out first and skips every contact
already in it, so an interrupted sweep resumes instead of starting over.
Output is written after every batch, not only at the end.
"""

import argparse
import base64
import json
import os
import random
import ssl
import sys
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed

BASE = "https://api.followupboss.com/v1"
PROXY = "https://tb-proxy.vercel.app/api/conversation"
CTX = ssl.create_default_context(cafile="/etc/ssl/cert.pem")


def key():
    k = os.environ.get("FUB_API_KEY", "").strip()
    if not k or k.startswith("${"):
        sys.exit("FUB_API_KEY is not set. export it first; never hardcode it.")
    return k


def http(url, headers, data=None, method="GET", timeout=30):
    """(status, parsed_body, headers). Never raises on an HTTP error status."""
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, context=CTX, timeout=timeout) as r:
            body = r.read()
            return r.status, (json.loads(body) if body else None), dict(r.headers)
    except urllib.error.HTTPError as e:
        body = e.read()
        try:
            parsed = json.loads(body)
        except Exception:
            parsed = body.decode(errors="replace")
        return e.code, parsed, dict(e.headers)
    except Exception as e:
        return 0, {"error": str(e)}, {}


def fub_headers():
    return {
        "Authorization": "Basic " + base64.b64encode((key() + ":").encode()).decode(),
        "Content-Type": "application/json",
    }


def proxy_headers():
    return {"Authorization": "Bearer " + key(), "Content-Type": "application/json"}


def budget(headers):
    """contacts_left = Remaining // Cost. Never hardcode a ceiling - the
    server owns it and it changes without this file changing."""
    def n(name):
        try:
            return int(headers.get(name, ""))
        except (TypeError, ValueError):
            return None
    remaining, cost = n("X-RateLimit-Remaining"), n("X-RateLimit-Cost")
    if remaining is None or not cost:
        return None
    return remaining // cost


# --------------------------------------------------------------------------


def cmd_identity(args):
    status, me, _ = http(BASE + "/identity", fub_headers())
    if status in (401, 403):
        sys.exit("%d from FUB - the key is invalid or the account is not "
                 "enabled. Stop; do not retry." % status)
    if status != 200:
        sys.exit("identity failed: %s %s" % (status, me))
    acct = (me or {}).get("account", {})
    user = (me or {}).get("user", {})
    # account.domain, never account.name - the two routinely differ.
    print(json.dumps({"account_id": acct.get("id"),
                      "domain": acct.get("domain"),
                      "user_email": user.get("email"),
                      "user_role": user.get("role")}, indent=1))


def cmd_ids(args):
    body = json.dumps({"conditions": [[{
        "fld": args.field, "opr": "was less than",
        "num": str(args.days), "unit": "days", "val": []}]]}).encode()
    # idsOnly returns every match in one response and ignores pagination -
    # looping offsets duplicates the whole set per page.
    status, data, _ = http(BASE + "/people/filter?idsOnly=true",
                           fub_headers(), data=body, method="POST")
    if status in (401, 403):
        sys.exit("%d from FUB - stop, do not retry." % status)
    if status != 200:
        sys.exit("filter failed: %s %s" % (status, data))

    ids = (data or {}).get("ids", [])
    if args.sample and len(ids) > args.sample:
        random.Random(args.seed).shuffle(ids)
        ids = sorted(ids[:args.sample])
        print("sampled %d of %d (seed %d)" % (len(ids), len((data or {}).get("ids", [])), args.seed))

    with open(args.out, "w") as f:
        json.dump({"field": args.field, "days": args.days, "ids": ids}, f)
    print("%d contacts -> %s" % (len(ids), args.out))


def fetch_one(pid):
    status, conv, headers = http(
        PROXY, proxy_headers(),
        data=json.dumps({"personid": str(pid)}).encode(), method="POST")
    return pid, status, conv, headers


def cmd_convs(args):
    with open(args.ids) as f:
        ids = [str(i) for i in json.load(f)["ids"]]

    done = {}
    if os.path.exists(args.out):
        with open(args.out) as f:
            done = json.load(f)
        print("resuming: %d already fetched" % len(done))

    todo = [i for i in ids if i not in done]
    if not todo:
        print("nothing left to fetch (%d contacts complete)" % len(done))
        return

    print("fetching %d contacts, %d workers" % (len(todo), args.workers))
    started, stop, errors = time.time(), None, {}
    last_headers = {}

    def save():
        with open(args.out, "w") as f:
            json.dump(done, f)

    # Batched so progress lands on disk as we go and a 429 can halt the
    # sweep promptly rather than after every future has been submitted.
    for start in range(0, len(todo), args.batch):
        if stop:
            break
        chunk = todo[start:start + args.batch]
        with ThreadPoolExecutor(max_workers=args.workers) as pool:
            futures = {pool.submit(fetch_one, p): p for p in chunk}
            for fut in as_completed(futures):
                pid, status, conv, headers = fut.result()
                if status == 200:
                    done[pid] = (conv or {}).get("texts", [])
                elif status == 429:
                    # Hourly cap. Retrying in a loop burns what is left and
                    # delays the reset - keep what we have and report.
                    stop = "429 rate limited (retry-after %ss)" % headers.get("Retry-After", "?")
                elif status in (401, 403):
                    stop = "%d - key rejected or account not registered" % status
                else:
                    errors[pid] = status
                last_headers = headers or last_headers
        save()
        left = budget(last_headers)
        print("  %d/%d done%s" % (len(done), len(ids),
                                  "" if left is None else "  (room for ~%d more)" % left))

    save()
    empty = sum(1 for v in done.values() if not v)
    print("\n%d conversations in %s (%.0fs)" % (len(done), args.out, time.time() - started))
    print("  empty (no history): %d" % empty)
    if errors:
        print("  failed: %d  %s" % (len(errors), sorted(set(errors.values()))))
    if len(done) < len(ids):
        print("  NOT COMPLETE: %d of %d remain - re-run to resume" % (len(ids) - len(done), len(ids)))
    if stop:
        print("  stopped early: %s" % stop)
    # Every contact empty usually means the wrong segment, not bad credentials.
    if done and empty == len(done):
        print("  every conversation came back empty - suspect the population "
              "filter, not the key")


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    sub.add_parser("identity").set_defaults(fn=cmd_identity)

    p = sub.add_parser("ids")
    p.add_argument("--days", type=int, required=True)
    p.add_argument("--field", required=True,
                   choices=["lastReceivedInboxAppMessage", "lastSentInboxAppMessage"])
    p.add_argument("--out", default="ids.json")
    p.add_argument("--sample", type=int, help="draw N at random instead of all")
    p.add_argument("--seed", type=int, default=42)
    p.set_defaults(fn=cmd_ids)

    p = sub.add_parser("convs")
    p.add_argument("--ids", default="ids.json")
    p.add_argument("--out", default="conversations.json")
    p.add_argument("--workers", type=int, default=10)
    p.add_argument("--batch", type=int, default=100)
    p.set_defaults(fn=cmd_convs)

    args = ap.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
