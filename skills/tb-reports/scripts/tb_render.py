#!/usr/bin/env python3
"""Fill a report shell with its data and write the result.

  python3 tb_render.py --shell message_detail report.json out.html
  python3 tb_render.py --shell performance_by_action_plan report.json out.html

Name the shell; do not pass a path. The script resolves it next to itself, so
it always reads the shell that shipped with the plugin it belongs to. This is
not a convenience: there are commonly several copies of this repo on a
machine (a checkout, a worktree, the installed plugin cache), and a real run
went looking by filename and filled a stale shell from an unrelated checkout,
silently producing an old-format report.

Valid names: message_detail, performance_by_action_plan, optouts_vs_replies,
reply_check.

report.json is the %%REPORT_DATA%% object described in the shell's own header
comment. %%TITLE%% is taken from its "title" key. Any other placeholder is
supplied with --set NAME=value (repeatable) - reply_check_shell.html still
uses per-field placeholders and needs those.

**One shell per file, always.** Each shell is a whole document - its own
<title>, <style> and <script>. Concatenating two of them into one page makes
the second one's CSS silently override the first's (they deliberately differ:
one uses table-layout:fixed, the other auto) and puts two `const DATA`
declarations in one scope, which is a SyntaxError that renders nothing at
all. Table 1 and Table 2 are two separate artifacts. This script renders one
shell and refuses input that looks pre-merged.

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
import os
import re
import sys

PLACEHOLDER = re.compile(r"%%[A-Z0-9_]+%%")
ASSETS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "assets")
SHELLS = ["message_detail", "performance_by_action_plan",
          "optouts_vs_replies", "reply_check"]


def announce():
    """Print which copy of the plugin this is, on every run.

    There are routinely several copies of this repo on a machine and they do
    not agree. A run that silently used a stale one produced a plausible but
    wrong report, so every run says which file it is executing and what
    version that file belongs to."""
    here = os.path.dirname(os.path.abspath(__file__))
    manifest = os.path.normpath(os.path.join(here, "..", "..", "..", ".claude-plugin", "plugin.json"))
    try:
        with open(manifest) as f:
            v = json.load(f).get("version", "?")
    except Exception:
        v = "unknown (no plugin.json above %s)" % here
    print("tb-fub-toolkit %s  -  %s" % (v, __file__), file=sys.stderr)


def main():
    announce()
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--shell", required=True, choices=SHELLS,
                    help="shell name; resolved next to this script, never a path")
    ap.add_argument("data", help="JSON file for %%REPORT_DATA%% (or %%DAILY_DATA%%)")
    ap.add_argument("out")
    ap.add_argument("--set", action="append", default=[], metavar="NAME=VALUE",
                    help="fill any other placeholder, e.g. --set SUBTITLE='Last 30 days'")
    ap.add_argument("--standalone", action="store_true",
                    help="wrap in a minimal document - file fallback only, never for Artifact")
    args = ap.parse_args()

    path = os.path.normpath(os.path.join(ASSETS, args.shell + "_shell.html"))
    if not os.path.exists(path):
        sys.exit("shell not found at %s - the plugin install looks incomplete." % path)
    shell = open(path).read()
    print("shell: %s" % path)

    # A shell is one whole document. More than one of any of these means
    # something concatenated two shells before handing them over.
    for tag, label in (("<title>", "title"), ("<style>", "style block"),
                       ("<script>", "script block")):
        n = shell.count(tag)
        if n > 1:
            sys.exit("%s contains %d %ss - it looks like two shells were merged.\n"
                     "Render each shell separately; they are not composable."
                     % (path, n, label))

    # Refuse a stale shell: every current one carries a single data placeholder.
    if not any(m in shell for m in ("%%REPORT_DATA%%", "%%DAILY_DATA%%", "%%NEEDS_ACTION_ROWS%%")):
        sys.exit("%s has no data placeholder - this is an old-format shell.\n"
                 "Reinstall or update the plugin." % path)

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
