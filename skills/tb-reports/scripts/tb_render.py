#!/usr/bin/env python3
"""Fill a report shell with its data and write the result.

  python3 tb_render.py ../assets/message_detail_shell.html report.json out.html
  python3 tb_render.py ../assets/message_detail_shell.html report.json out.html --standalone

report.json is the %%REPORT_DATA%% object described in the shell's own header
comment. %%TITLE%% is taken from its "title" key. Any other placeholder is
supplied with --set NAME=value (repeatable) - reply_check_shell.html still
uses per-field placeholders and needs those.

The point of running this rather than editing the shell by hand is that it
fails loudly. A placeholder left unfilled is an error here; done by hand it
ships to the reader as a literal %%ROWS%% in the middle of the page.

Output is the shell content unchanged, which is what the `Artifact` tool
wants: content-only, no <!doctype>/<html>/<head>/<body> of its own. Pass
--standalone ONLY for the file fallback when Artifact is unavailable, which
needs a real document to open in a browser.
"""

import argparse
import json
import re
import sys

PLACEHOLDER = re.compile(r"%%[A-Z0-9_]+%%")


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("shell")
    ap.add_argument("data", help="JSON file for %%REPORT_DATA%% (or %%DAILY_DATA%%)")
    ap.add_argument("out")
    ap.add_argument("--set", action="append", default=[], metavar="NAME=VALUE",
                    help="fill any other placeholder, e.g. --set SUBTITLE='Last 30 days'")
    ap.add_argument("--standalone", action="store_true",
                    help="wrap in a minimal document - file fallback only, never for Artifact")
    args = ap.parse_args()

    shell = open(args.shell).read()
    raw = open(args.data).read()

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        sys.exit("%s is not valid JSON: %s" % (args.data, e))

    # The data placeholder differs by shell; fill whichever one is present.
    for name in ("%%REPORT_DATA%%", "%%DAILY_DATA%%"):
        if name in shell:
            shell = shell.replace(name, raw)
            break

    if isinstance(data, dict) and "title" in data:
        shell = shell.replace("%%TITLE%%", str(data["title"]))

    for pair in args.set:
        if "=" not in pair:
            sys.exit("--set needs NAME=VALUE, got %r" % pair)
        name, value = pair.split("=", 1)
        shell = shell.replace("%%" + name.strip().upper() + "%%", value)

    left = sorted(set(PLACEHOLDER.findall(shell)))
    if left:
        sys.exit("unfilled placeholders: %s\n"
                 "Supply each with --set NAME=VALUE." % ", ".join(left))

    if args.standalone:
        shell = ("<!doctype html><html><head><meta charset=\"utf-8\">"
                 "</head><body>" + shell + "</body></html>")

    with open(args.out, "w") as f:
        f.write(shell)
    print("wrote %s (%d bytes)" % (args.out, len(shell)))


if __name__ == "__main__":
    main()
