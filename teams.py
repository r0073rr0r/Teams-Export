#!/usr/bin/env python3
"""teams.py - a tool to read YOUR OWN Microsoft Teams desktop cache on YOUR OWN computer.

Methods:

  export   Snapshot the Teams IndexedDB cache and build a readable log.  [RECOMMENDED]
           Works whether Teams is running or not; nothing is sent anywhere.
  doctor   Environment check (Teams install, cache folders, dependencies).

All outputs go to  export/  (which is NOT committed). Examples:
  python teams.py export
  python teams.py export --since 2026-09-22T21:00
  python teams.py export --profile personal
"""
import argparse
import os
import sys


def cmd_export(a):
    from teamskit import snapshot, extract, output
    events = []
    profiles = ["personal", "work"] if a.profile == "all" else [a.profile]
    for p in profiles:
        snap = snapshot.run(p)
        if snap:
            ev = extract.run(snap, p)
            print(f"  [{p}] {len(ev)} messages")
            events.extend(ev)
    events.sort(key=lambda e: e["time"])
    output.write(output.filter_since(events, a.since))


def cmd_doctor(a):
    from teamskit import config
    print("== doctor ==")
    found = "(exists)" if os.path.isdir(config.EBWEBVIEW) else "(NOT found - is the new Teams app installed?)"
    print(f"  Teams app dir  : {config.EBWEBVIEW}  {found}")
    for p in config.PROFILES:
        d = config.leveldb_dir(p)
        size = sum(os.path.getsize(os.path.join(d, f)) for f in os.listdir(d)) if os.path.isdir(d) else 0
        shown = '%.1f MB' % (size / 1048576) if size >= 1048576 else '%d KB (practically empty)' % (size // 1024)
        print(f"  {p:8s} cache : {shown if size else '(empty / not found)'}")
    print(f"  export dir     : {config.EXPORT_DIR}")
    for mod in ("ccl_chromium_reader", "snappy"):
        try:
            __import__(mod)
            print(f"  dep {mod:19s}: ok")
        except Exception:
            print(f"  dep {mod:19s}: MISSING")


def main():
    p = argparse.ArgumentParser(
        description="Read your own Microsoft Teams desktop cache (see README.md).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__)
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("export", help="snapshot the cache and build the log [recommended]")
    s.add_argument("--profile", choices=("personal", "work", "all"), default="all",
                   help="personal = private Microsoft account, work = work/school account")
    s.add_argument("--since", default=None, help="only messages from this local time, e.g. 2026-09-22T21:00")
    s.set_defaults(func=cmd_export)

    s = sub.add_parser("doctor", help="environment check")
    s.set_defaults(func=cmd_doctor)

    args = p.parse_args()
    # UTF-8 output on the Windows console
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    args.func(args)


if __name__ == "__main__":
    main()
