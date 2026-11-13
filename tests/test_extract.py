"""Unit tests for de-duplication, event building and log formatting. Synthetic samples only."""
from teamskit import extract, output


def _msg(**kw):
    base = {"conversationId": "19:chat", "id": "1", "clientMessageId": "c1", "version": "1",
            "messageType": "RichText/Html", "content": "<p>hi</p>", "originalArrivalTime": 1_758_600_000_000,
            "imDisplayName": "Alice Example", "creator": "8:live:alice", "isSentByCurrentUser": False,
            "properties": {}}
    base.update(kw)
    return base


def test_pick_latest_merges_local_and_server_copy():
    local = _msg(id="local", version="1")
    server = _msg(id="server", version="5", content="<p>hi (final)</p>")
    kept = extract.pick_latest([local, server])
    assert len(kept) == 1 and kept[0]["id"] == "server"


def test_pick_latest_keeps_distinct_messages():
    assert len(extract.pick_latest([_msg(clientMessageId="a"), _msg(clientMessageId="b")])) == 2


def test_build_events_names_one_to_one_chat_after_other_person():
    ev = extract.build_events([_msg()], names={}, topics={}, group_ids=set(), profile="personal")
    assert ev[0]["peer"] == "Alice Example" and ev[0]["direction"] == "IN" and not ev[0]["is_group"]


def test_build_events_group_chat_and_deleted():
    msgs = [_msg(conversationId="19:grp"), _msg(conversationId="19:grp", clientMessageId="c2",
                                                  properties={"deletetime": "123"})]
    ev = extract.build_events(msgs, {}, {"19:grp": "Project Team"}, {"19:grp"}, "personal")
    assert all(e["is_group"] and e["peer"] == "Project Team" for e in ev)
    assert sorted(e["text"] for e in ev) == ["[deleted]", "hi"]


def test_build_events_decodes_one_byte_string_content():
    # V8 one-byte (Latin-1) strings come back from the reader as bytes; they must not be dropped.
    ev = extract.build_events([_msg(content=b"<p>it\xb4s\xa0here</p>")], {}, {}, set(), "personal")
    assert ev[0]["text"] == "it´s here"


def test_build_events_names_chat_from_members_when_only_i_wrote():
    mine = _msg(conversationId="19:solo", isSentByCurrentUser=True, creator="8:me", imDisplayName="Me")
    members = {"19:solo": ["8:me", "8:live:bob", "8:skypeuser"]}
    ev = extract.build_events([mine], {"8:live:bob": "Bob Example"}, {}, set(), "personal", members)
    assert ev[0]["peer"] == "8:skypeuser, Bob Example" and ev[0]["direction"] == "OUT"


def test_format_line_and_filter_since():
    e = {"time": "2026-09-23 10:00:00", "direction": "OUT", "is_group": False, "peer": "Alice Example",
         "author": "Me", "text": "line one\nline two", "edited": True, "reactions": "👍1"}
    assert output.format_line(e) == \
        "[2026-09-23 10:00:00] OUT -> Alice Example: line one\n    line two (edited) [👍1]"
    older = dict(e, time="2026-09-22 20:59:59")
    assert output.filter_since([older, e], "2026-09-22T21:00") == [e]
