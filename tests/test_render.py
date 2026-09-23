"""Unit tests for turning raw Teams message content into text. Synthetic samples only."""
from teamskit import render


def test_plain_html_paragraphs_and_breaks():
    assert render.render("RichText/Html", "<p>first</p><p>second<br>third</p>") == "first\nsecond\nthird"


def test_html_entities_and_nbsp():
    assert render.render("RichText/Html", "<p>a &amp; b&nbsp;c</p>") == "a & b c"


def test_emoji_image_becomes_emoji():
    content = ('<p>ok <span><img itemscope itemtype="http://schema.skype.com/Emoji" itemid="smile" '
               'src="x" alt="\U0001F604" /></span></p>')
    assert render.render("RichText/Html", content) == "ok \U0001F604"


def test_other_image_becomes_placeholder():
    assert render.render("RichText/Html", '<p><img src="x" alt="image"></p>') == "[image]"


def test_reply_quote_uses_resolved_name():
    content = ('<blockquote itemscope itemtype="http://schema.skype.com/Reply" itemid="1">'
               '<strong itemprop="mri" itemid="8:live:alice">Display Name</strong>'
               '<span itemprop="time" itemid="1"></span><p itemprop="preview">see you tomorrow</p>'
               '</blockquote><p>works for me</p>')
    out = render.render("RichText/Html", content, {"8:live:alice": "Alice Example"})
    assert out == "> Alice Example: see you tomorrow\nworks for me"


def test_reply_quote_drops_display_name_placeholder():
    content = ('<blockquote itemtype="http://schema.skype.com/Reply">'
               '<strong itemprop="mri" itemid="8:unknown">Display Name</strong>'
               '<p itemprop="preview">question?</p></blockquote><p>answer</p>')
    assert render.render("RichText/Html", content) == "> question?\nanswer"


def test_call_events():
    started = ('<partlist type="started" alt=""><part identity="8:live:bob"><name>8:live:bob</name></part>'
               '</partlist><callEventType>callStarted</callEventType>')
    assert render.render("Event/Call", started, {"8:live:bob": "Bob"}) == "[call started: Bob]"
    missed = '<partlist type="missed"><part identity="a"><name>Ann</name></part></partlist>'
    assert render.render("Event/Call", missed) == "[missed call: Ann]"


def test_uriobject_kinds():
    assert render.render("RichText/UriObject", '<URIObject type="Picture.1">To view this photo</URIObject>') == \
        "[image]"
    assert render.render("RichText/Media_GenericFile",
                         '<URIObject type="File.1">x<OriginalName v="spec.docx"/></URIObject>') == "[file: spec.docx]"
    assert render.render("RichText/Media_AudioMsg",
                         '<URIObject type="Audio.1/Message.1"><Title>Voicemail</Title></URIObject>') == \
        "[voice message]"
    assert render.render("Poll", '<URIObject type="Poll">Old or new?</URIObject>') == "[poll: Old or new?]"


def test_call_transcript_and_album():
    assert render.render("RichText/Media_CallTranscript", '{"callId":"1"}') == "[call transcript]"
    assert render.render("RichText/Media_Album", "") == "[album]"


def test_files_and_reactions_from_properties():
    props = {"files": '[{"fileName": "a.pdf"}, {"title": "b.jpg"}]',
             "emotions": [{"key": "like", "users": [{"mri": "x"}, {"mri": "y"}]}, {"key": "heart", "users": []},
                          {"key": "yes-tone2", "users": [{"mri": "z"}]}, {"key": "party", "users": [{"mri": "z"}]},
                          {"key": "reactionsConsumptionHorizon", "users": [{"mri": "z"}]}]}
    assert render.files_from_properties(props) == ["a.pdf", "b.jpg"]
    assert render.reactions_from_properties(props) == "👍3 (party)1"
    assert not render.files_from_properties({"files": "not json"})
    assert render.reactions_from_properties({}) == ""


def test_plain_unescapes_topics():
    assert render.plain("IT &amp; DEV ") == "IT & DEV"
