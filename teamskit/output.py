"""Write the extracted messages as a readable log (.txt) and as JSON lines (.jsonl)."""
import json
import os

from . import config


def format_line(e):
    """One message as one log entry; continuation lines are indented by four spaces."""
    where = f"[{e['peer']}] " if e["is_group"] else ""
    who = e["author"] if e["is_group"] or e["direction"] == "IN" else f"-> {e['peer']}"
    body = e["text"].replace("\n", "\n    ")
    extra = (" (edited)" if e.get("edited") else "") + (f" [{e['reactions']}]" if e.get("reactions") else "")
    return f"[{e['time']}] {e['direction']:3} {where}{who}: {body}{extra}"


def filter_since(events, since):
    """Keep messages at or after `since` ('YYYY-MM-DD HH:MM[:SS]', local time)."""
    if not since:
        return list(events)
    since = since.replace("T", " ")
    return [e for e in events if e["time"] >= since]


def write(events, export_dir=None):
    export_dir = export_dir or config.EXPORT_DIR
    os.makedirs(export_dir, exist_ok=True)
    jl = os.path.join(export_dir, "teams_log.jsonl")
    tx = os.path.join(export_dir, "teams_messages.txt")
    with open(jl, "w", encoding="utf-8") as f:
        for e in events:
            f.write(json.dumps(e, ensure_ascii=False) + "\n")
    with open(tx, "w", encoding="utf-8") as f:
        f.write(f"# Teams log - {len(events)} messages\n")
        f.write("# DIR: IN=received, OUT=sent. Group chats show [chat name] and the author.\n\n")
        for e in events:
            f.write(format_line(e) + "\n")
    print(f"  wrote {len(events)} messages -> {tx}")
    return tx
