"""Turn the raw content of one Teams message into readable plain text.

Pure functions only (no dependency on the cache reader), so they are unit-tested in CI.

Teams stores message bodies as HTML (chat text), as Skype-style XML (<URIObject> for photos,
files, voice messages, polls, cards, recordings; <partlist> for calls) or, for a few system
items, as JSON. Every form is flattened here to one short line of text.
"""
import html
import json
import re

_BLOCK = re.compile(r"<\s*(br|/p|/div|/li|/blockquote|/h\d|/tr)\b[^>]*>", re.I)
_TAG = re.compile(r"<[^>]+>")
_EMOJI_IMG = re.compile(r"<img\b[^>]*itemtype=\"http://schema\.skype\.com/Emoji\"[^>]*>", re.I)
_ALT = re.compile(r"\balt=\"([^\"]*)\"", re.I)
_ANY_IMG = re.compile(r"<img\b[^>]*>", re.I)
_REPLY = re.compile(r"<blockquote\b[^>]*itemtype=\"http://schema\.skype\.com/Reply\"[^>]*>(.*?)</blockquote>",
                    re.I | re.S)
_REPLY_MRI = re.compile(r"<strong\b[^>]*itemprop=\"mri\"[^>]*itemid=\"([^\"]*)\"[^>]*>(.*?)</strong>", re.I | re.S)
_REPLY_PREVIEW = re.compile(r"<p\b[^>]*itemprop=\"preview\"[^>]*>(.*?)</p>", re.I | re.S)
_URIOBJECT = re.compile(r"<URIObject\b([^>]*)>(.*?)</URIObject>", re.I | re.S)
_ATTR_TYPE = re.compile(r"\btype=\"([^\"]*)\"", re.I)
_ORIGINAL_NAME = re.compile(r"<OriginalName\b[^>]*\bv=\"([^\"]*)\"", re.I)
_TITLE = re.compile(r"<Title>(.*?)</Title>", re.I | re.S)
_PARTLIST = re.compile(r"<partlist\b[^>]*\btype=\"([^\"]*)\"", re.I)
_PART_NAME = re.compile(r"<part\b[^>]*>\s*<name>(.*?)</name>", re.I | re.S)
_CALL_EVENT = re.compile(r"<callEventType>(.*?)</callEventType>", re.I | re.S)


def html_to_text(content):
    """Flatten chat HTML to text: emoji images become the emoji, other images [image]."""
    t = _EMOJI_IMG.sub(lambda m: (_ALT.search(m.group(0)) or [None, ""])[1], content)
    t = _ANY_IMG.sub("[image]", t)
    t = _BLOCK.sub("\n", t)
    t = _TAG.sub("", t)
    t = html.unescape(t).replace("\xa0", " ")
    lines = [ln.rstrip() for ln in t.split("\n")]
    return "\n".join(ln for ln in lines if ln.strip()).strip()


def _quote(match, names):
    inner = match.group(1)
    who = ""
    m = _REPLY_MRI.search(inner)
    if m:
        who = names.get(m.group(1), "") or html_to_text(m.group(2))
        if who == "Display Name":  # placeholder Teams writes when it had no name at hand
            who = ""
    p = _REPLY_PREVIEW.search(inner)
    preview = html_to_text(p.group(1)) if p else ""
    head = f"{who}: " if who else ""
    return "\n" + "\n".join("> " + head + ln if i == 0 else "> " + ln
                            for i, ln in enumerate(preview.split("\n") or [""])) + "\n"


def _uriobject(attrs, body):
    kind = (_ATTR_TYPE.search(attrs) or [None, ""])[1]
    name = (_ORIGINAL_NAME.search(body) or [None, ""])[1]
    title = html_to_text((_TITLE.search(body) or [None, ""])[1])
    if kind.startswith("Picture"):
        return "[image]"
    if kind.startswith("Video.2/CallRecording"):
        return f"[call recording: {title}]" if title else "[call recording]"
    if kind.startswith("Video"):
        return f"[video: {name}]" if name else "[video]"
    if kind.startswith("Audio"):
        return "[voice message]"
    if kind.startswith("File"):
        return f"[file: {name}]" if name else "[file]"
    if kind == "Poll":
        return f"[poll: {html_to_text(body)}]"
    if kind.startswith("SWIFT"):
        return "[card]"
    return f"[{name or title or 'attachment'}]"


def _call(content, names):
    event = html_to_text((_CALL_EVENT.search(content) or [None, ""])[1])
    kind = (_PARTLIST.search(content) or [None, ""])[1]
    label = {"callStarted": "call started", "callEnded": "call ended"}.get(event) or \
        {"started": "call started", "ended": "call ended", "missed": "missed call"}.get(kind, "call")
    people = []
    for raw in _PART_NAME.findall(content):
        n = html_to_text(raw)
        n = names.get(n, n)
        if n and n not in people:
            people.append(n)
    return f"[{label}: {', '.join(people)}]" if people else f"[{label}]"


def render(message_type, content, names=None):
    """Return readable text for one message. `names` maps an MRI (8:live:...) to a display name."""
    names = names or {}
    content = content or ""
    if message_type.startswith("Event/Call"):
        return _call(content, names)
    if message_type == "RichText/Media_CallTranscript":
        return "[call transcript]"
    if message_type == "RichText/Media_Album" and not content.strip():
        return "[album]"
    stripped = content.lstrip()
    if stripped.startswith(("{", "[{")):
        try:
            json.loads(stripped)
            return "[system item]"
        except ValueError:
            pass
    t = _REPLY.sub(lambda m: _quote(m, names), content)
    t = _URIOBJECT.sub(lambda m: _uriobject(m.group(1), m.group(2)), t)
    # Keep the "> " quote prefix through the HTML flattening.
    return html_to_text(t)


def files_from_properties(props):
    """File names attached to a message (properties.files, a JSON string or a list)."""
    raw = props.get("files") if isinstance(props, dict) else None
    try:
        items = json.loads(raw) if isinstance(raw, str) else (raw or [])
    except (ValueError, TypeError):
        return []
    if not isinstance(items, list):
        return []
    return [f.get("fileName") or f.get("title") or "file" for f in items if isinstance(f, dict)]


REACTION_EMOJI = {
    "like": "👍", "yes": "👍", "heart": "❤️", "laugh": "😆", "surprised": "😮", "cry": "😢",
    "sad": "😢", "angry": "😠", "cwl": "😂", "facepalm": "🤦", "bow": "🙇", "sarcastic": "😏",
    "2714_heavycheckmark": "✔️", "xmasyes": "👍", "smile": "🙂", "party": "🎉", "ok": "👌", "rock": "🤘",
    "handsinair": "🙌", "rofl": "🤣", "dance": "💃", "xmasheart": "❤️", "heartyellow": "💛",
}
_CODEPOINT_KEY = re.compile(r"^([0-9a-f]{4,6})_", re.I)


def _reaction_label(key):
    base = key.split("-tone")[0]
    if base in REACTION_EMOJI:
        return REACTION_EMOJI[base]
    cp = _CODEPOINT_KEY.match(base)  # newer keys carry the code point: 1f440_eyes, 2705_whiteheavycheckmark
    return chr(int(cp.group(1), 16)) if cp else f"({key})"


def reactions_from_properties(props):
    """Short reaction summary such as '👍2 ❤️1' from properties.emotions."""
    em = props.get("emotions") if isinstance(props, dict) else None
    if isinstance(em, str):
        try:
            em = json.loads(em)
        except ValueError:
            em = None
    if not isinstance(em, list):
        return ""
    counts = {}
    for e in em:
        key = e.get("key") if isinstance(e, dict) else None
        # reactionsConsumptionHorizon & co. are read-state bookkeeping, not reactions.
        if not isinstance(key, str) or key.startswith("reactions") or not e.get("users"):
            continue
        label = _reaction_label(key)
        counts[label] = counts.get(label, 0) + len(e["users"])
    return " ".join(f"{label}{n}" for label, n in counts.items())


def plain(text):
    """Unescape a plain-text field Teams stores HTML-escaped (chat topics, names)."""
    return html.unescape(text or "").strip()
