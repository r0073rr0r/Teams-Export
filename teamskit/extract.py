"""Read messages out of a Teams IndexedDB snapshot.

Stores used (new Teams / Teams 2.x):
  Teams:replychain-manager   / replychains    -> messages (messageMap per reply chain)
  Teams:conversation-manager / conversations  -> chat names (threadProperties.topic)
  Teams:profiles             / profiles       -> MRI -> display name
"""
import datetime

from . import render

SKIP_TYPES = ("Control/", "ThreadActivity/", "InviteFreeRelationshipChanged/")
GROUP_THREAD_TYPES = ("topic", "space", "meeting", "chat")


def _s(v):
    """A string field. V8 stores pure Latin-1 strings as one-byte strings, which the reader
    returns as bytes (e.g. a message body containing only ASCII + a non-breaking space)."""
    if isinstance(v, bytes):
        return v.decode("latin-1")
    return v if isinstance(v, str) else ""


def _list(v):
    return v if isinstance(v, list) else []


def _version(m):
    v = _s(m.get("version"))
    try:
        return float(v)
    except ValueError:
        return 0.0


def dedupe_key(m):
    """The pending local copy and the server copy of a message share clientMessageId, not id."""
    return (m.get("conversationId"), _s(m.get("clientMessageId")) or m.get("id"))


def pick_latest(messages):
    """Keep one copy per message: the one with the highest version."""
    best = {}
    for m in messages:
        k = dedupe_key(m)
        if k not in best or _version(m) > _version(best[k]):
            best[k] = m
    return list(best.values())


def _db(wrapper, prefix):
    for d in wrapper.database_ids:
        if d.name.startswith(prefix):
            return wrapper[d.dbid_no]
    return None


def _live(db, store):
    if db is None or store not in db.object_store_names:
        return
    for rec in db[store].iterate_records(live_only=True):
        if isinstance(rec.value, dict):
            yield rec.value


def _raw_messages(w):
    for rc in _live(_db(w, "Teams:replychain-manager"), "replychains"):
        for m in (rc.get("messageMap") or {}).values():
            if isinstance(m, dict) and _s(m.get("messageType")) and \
                    not _s(m.get("messageType")).startswith(SKIP_TYPES):
                yield m


def build_events(messages, names, topics, group_ids, profile, members=None):
    """Turn raw message dicts into log events. Pure: no cache access, unit-tested.

    `members` maps a conversation id to its member MRIs; it names chats in which only you wrote."""
    # 1:1 chats have no topic: name them after the other participant(s) seen in the chat.
    others, me = {}, set()
    for m in messages:
        if m.get("isSentByCurrentUser"):
            me.add(_s(m.get("creator")))
            continue
        who = _s(m.get("imDisplayName")) or names.get(m.get("creator"), "") or _s(m.get("creator"))
        if who:
            others.setdefault(m.get("conversationId"), set()).add(who)

    def peer(conv):
        if topics.get(conv):
            return topics[conv]
        if others.get(conv):
            return ", ".join(sorted(others[conv]))
        rest = [x for x in (members or {}).get(conv, ()) if x not in me]
        return ", ".join(sorted(names.get(x) or x for x in rest)) or _s(conv)

    events = []
    for m in messages:
        ts = m.get("originalArrivalTime") or m.get("clientArrivalTime")
        if not isinstance(ts, (int, float)) or ts <= 0:
            continue
        conv = m.get("conversationId")
        props = m.get("properties") if isinstance(m.get("properties"), dict) else {}
        if props.get("deletetime") or isinstance(m.get("deletionInfo"), dict):
            text = "[deleted]"
        else:
            text = render.render(_s(m.get("messageType")), _s(m.get("content")), names)
            files = [f for f in render.files_from_properties(props) if f"[file: {f}]" not in text]
            if files:
                text = " ".join(filter(None, [text] + [f"[file: {f}]" for f in files]))
        if not text:
            continue
        events.append({
            "time": datetime.datetime.fromtimestamp(ts / 1000).strftime("%Y-%m-%d %H:%M:%S"),
            "direction": "OUT" if m.get("isSentByCurrentUser") else "IN",
            "is_group": conv in group_ids or bool(topics.get(conv)),
            "peer": peer(conv),
            "author": _s(m.get("imDisplayName")) or names.get(m.get("creator"), "") or _s(m.get("creator")),
            "kind": _s(m.get("messageType")),
            "text": text,
            "edited": bool(props.get("edittime")),
            "reactions": render.reactions_from_properties(props),
            "conversation_id": _s(conv),
            "profile": profile,
        })
    events.sort(key=lambda e: e["time"])
    return events


def run(snapshot, profile):
    from ccl_chromium_reader import ccl_chromium_indexeddb as idb
    w = idb.WrappedIndexDB(snapshot, None)

    names = {_s(p.get("mri")): _s(p.get("displayName")) for p in _live(_db(w, "Teams:profiles"), "profiles")
             if _s(p.get("mri")) and _s(p.get("displayName"))}

    topics, group_ids, members = {}, set(), {}
    for c in _live(_db(w, "Teams:conversation-manager"), "conversations"):
        cid = c.get("id")
        tp = c.get("threadProperties") if isinstance(c.get("threadProperties"), dict) else {}
        topics[cid] = render.plain(_s(tp.get("topic")))
        if _s(tp.get("threadType")) in GROUP_THREAD_TYPES and _s(tp.get("topic")):
            group_ids.add(cid)
        members[cid] = [_s(x.get("id")) for x in _list(c.get("members")) if isinstance(x, dict) and _s(x.get("id"))]
        # The chat list keeps names of people missing from Teams:profiles (e.g. old Skype contacts).
        title = c.get("chatTitle") if isinstance(c.get("chatTitle"), dict) else {}
        for u in _list(title.get("avatarUsersInfo")):
            if isinstance(u, dict) and _s(u.get("mri")) and _s(u.get("displayName")):
                names.setdefault(_s(u.get("mri")), _s(u.get("displayName")))

    return build_events(pick_latest(_raw_messages(w)), names, topics, group_ids, profile, members)
