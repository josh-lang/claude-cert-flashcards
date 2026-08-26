#!/usr/bin/env python3
"""Build a self-contained Anki .apkg (with media) from a cards doc (JSON).

Part of the flashcard-deck-generator skill. Requires genanki >= 0.13.0
(two-field CLOZE_MODEL). Model IDs are baked constants generated once at
skill build time; deck ids derive deterministically from the deck name.
Exit codes: 0 ok | 1 unexpected error | 2 bad input | 3 missing dependency.
"""

import argparse
import hashlib
import json
import os
import re
import secrets
import sys

# Baked at skill build (2026-08) via random.randrange(1 << 30, 1 << 31).
BASIC_MODEL_ID = 1893207705
BASIC_REV_MODEL_ID = 1921666369

DEFAULT_CSS = (
    ".card { font-family: -apple-system, 'Helvetica Neue', Arial, sans-serif;"
    " font-size: 20px; text-align: center; color: black; background-color: white; }"
)

NOTETYPES = {
    "basic": "Basic",
    "basic-reversed": "Basic (and reversed card)",
    "cloze": "Cloze",
}
FIELD_NAMES = {
    "basic": ("Front", "Back"),
    "basic-reversed": ("Front", "Back"),
    "cloze": ("Text", "Back Extra"),
}


def fail(msg, code=2):
    print(f"error: {msg}", file=sys.stderr)
    sys.exit(code)


def warn(msg):
    print(f"warning: {msg}", file=sys.stderr)


def guid_for(card, salt=""):
    k = card["guid_key"]
    key = f"{k['source']}|{k['slug']}|{k['ordinal']}"
    if salt:
        key = f"{key}|{salt}"
    return hashlib.sha1(key.encode("utf-8")).hexdigest()


def html_newlines(value):
    return value.replace("\r\n", "\n").replace("\r", "\n").replace("\n", "<br>")


def field_values(card, idx):
    names = FIELD_NAMES[card["type"]]
    fields = card.get("fields")
    if not isinstance(fields, dict):
        fail(f"card #{idx}: 'fields' must be an object keyed by field name")
    unknown = sorted(set(fields) - set(names))
    if unknown:
        fail(
            f"card #{idx} ({card['type']}): unknown field(s) {unknown}; "
            f"expected {list(names)}"
        )
    first = fields.get(names[0], "")
    second = fields.get(names[1], "")
    if not isinstance(first, str) or not isinstance(second, str):
        fail(f"card #{idx}: field values must be strings")
    if not first.strip():
        fail(f"card #{idx}: first field ('{names[0]}') is empty")
    return first, second


def check_tags(tags, where):
    if not isinstance(tags, list):
        fail(f"{where}: 'tags' must be a list")
    for t in tags:
        if not isinstance(t, str) or not t:
            fail(f"{where}: tags must be non-empty strings")
        if re.search(r"\s", t):
            fail(f"{where}: tag '{t}' contains whitespace (use :: hierarchies)")


def load_doc(path):
    try:
        with open(path, encoding="utf-8") as f:
            doc = json.load(f)
    except FileNotFoundError:
        fail(f"no such file: {path}")
    except json.JSONDecodeError as e:
        fail(f"{path} is not valid JSON: {e}")
    if not isinstance(doc, dict):
        fail("cards doc must be a JSON object")
    if doc.get("schema_version") != 1:
        fail("cards doc schema_version must be 1")
    cards = doc.get("cards")
    if not isinstance(cards, list) or not cards:
        fail("cards doc has no cards")
    check_tags(doc.get("tags", []), "doc")
    for i, card in enumerate(cards, 1):
        if not isinstance(card, dict):
            fail(f"card #{i}: must be an object")
        ctype = card.get("type")
        if ctype not in NOTETYPES:
            fail(f"card #{i}: unknown type '{ctype}' (expected {sorted(NOTETYPES)})")
        gk = card.get("guid_key")
        if (
            not isinstance(gk, dict)
            or not isinstance(gk.get("source"), str)
            or not gk["source"]
            or not isinstance(gk.get("slug"), str)
            or not gk["slug"]
            or not isinstance(gk.get("ordinal"), int)
        ):
            fail(
                f"card #{i}: guid_key must be {{source: str, slug: str, ordinal: int}}"
            )
        first, _ = field_values(card, i)
        joined = first + (card["fields"].get(FIELD_NAMES[ctype][1]) or "")
        if ctype == "cloze" and "{{c" not in first:
            fail(f"card #{i}: cloze card has no {{{{c1::…}}}} deletion in 'Text'")
        if ctype != "cloze" and "{{c" in joined:
            warn(f"card #{i}: looks like a cloze but type is '{ctype}'")
        check_tags(card.get("tags", []), f"card #{i}")
        media = card.get("media", [])
        if not isinstance(media, list) or any(not isinstance(m, str) for m in media):
            fail(f"card #{i}: 'media' must be a list of paths")
    return doc


def slugify(name):
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower().replace("::", "-")).strip("-")
    return slug or "deck"


def deck_id_for(deck_name):
    digest = hashlib.sha1(deck_name.encode("utf-8")).digest()
    return (1 << 30) + int.from_bytes(digest[:8], "big") % (1 << 30)


def collect_media(doc, cards_json_path):
    media_dir = doc.get("media_dir") or "."
    base = os.path.dirname(os.path.abspath(cards_json_path))
    root = media_dir if os.path.isabs(media_dir) else os.path.join(base, media_dir)
    by_basename = {}
    for i, card in enumerate(doc["cards"], 1):
        joined = "".join(card.get("fields", {}).values())
        for rel in card.get("media", []):
            path = rel if os.path.isabs(rel) else os.path.join(root, rel)
            path = os.path.abspath(path)
            if not os.path.isfile(path):
                fail(f"card #{i}: media file not found: {path}")
            name = os.path.basename(path)
            if by_basename.get(name, path) != path:
                fail(
                    f"two different files share the media basename '{name}' — "
                    "Anki media is a flat namespace; rename one"
                )
            by_basename[name] = path
            if name not in joined:
                warn(f"card #{i}: media '{name}' is not referenced by any field")
    return sorted(by_basename.values())


def main():
    ap = argparse.ArgumentParser(
        description="cards doc (JSON) -> .apkg via genanki (bundles media)"
    )
    ap.add_argument("cards_json", help="path to the cards doc")
    ap.add_argument("--out", help="output .apkg path (default: <deck-slug>.apkg)")
    ap.add_argument("--deck", help="override the doc's deck name")
    ap.add_argument(
        "--fresh",
        action="store_true",
        help="salt every guid so re-import creates new notes instead of updating",
    )
    args = ap.parse_args()

    try:
        import genanki
    except ImportError:
        print("error: genanki is not installed.", file=sys.stderr)
        print("install: python3 -m pip install genanki", file=sys.stderr)
        sys.exit(3)
    cloze_fields = [f["name"] for f in genanki.CLOZE_MODEL.fields]
    if len(cloze_fields) < 2:
        fail(
            "this genanki is too old (one-field CLOZE_MODEL); "
            "install: python3 -m pip install --upgrade 'genanki>=0.13.0'",
            code=3,
        )

    doc = load_doc(args.cards_json)
    deck_name = args.deck or doc.get("deck")
    if not deck_name or not isinstance(deck_name, str):
        fail("no deck name (set 'deck' in the doc or pass --deck)")

    salt = secrets.token_hex(4) if args.fresh else ""
    cards = doc["cards"]
    guids = [guid_for(c, salt) for c in cards]
    seen = {}
    for c, g in zip(cards, guids):
        if g in seen:
            fail(
                "duplicate guid_key: "
                f"'{seen[g]['guid_key']['slug']}' and '{c['guid_key']['slug']}' "
                "resolve to the same guid (make slug/ordinal distinct)"
            )
        seen[g] = c

    basic_model = genanki.Model(
        BASIC_MODEL_ID,
        "Basic (FlashcardGen)",
        fields=[{"name": "Front"}, {"name": "Back"}],
        templates=[
            {
                "name": "Card 1",
                "qfmt": "{{Front}}",
                "afmt": '{{FrontSide}}<hr id="answer">{{Back}}',
            }
        ],
        css=DEFAULT_CSS,
    )
    basic_rev_model = genanki.Model(
        BASIC_REV_MODEL_ID,
        "Basic and reversed (FlashcardGen)",
        fields=[{"name": "Front"}, {"name": "Back"}],
        templates=[
            {
                "name": "Card 1",
                "qfmt": "{{Front}}",
                "afmt": '{{FrontSide}}<hr id="answer">{{Back}}',
            },
            {
                "name": "Card 2",
                "qfmt": "{{Back}}",
                "afmt": '{{FrontSide}}<hr id="answer">{{Front}}',
            },
        ],
        css=DEFAULT_CSS,
    )
    models = {
        "basic": basic_model,
        "basic-reversed": basic_rev_model,
        "cloze": genanki.CLOZE_MODEL,
    }

    global_tags = doc.get("tags", [])
    deck = genanki.Deck(deck_id_for(deck_name), deck_name)
    for i, (card, guid) in enumerate(zip(cards, guids), 1):
        v1, v2 = field_values(card, i)
        note = genanki.Note(
            model=models[card["type"]],
            fields=[html_newlines(v1), html_newlines(v2)],
            tags=list(dict.fromkeys(global_tags + card.get("tags", []))),
            guid=guid,
        )
        deck.add_note(note)

    package = genanki.Package(deck)
    package.media_files = collect_media(doc, args.cards_json)

    out = args.out or f"{slugify(deck_name)}.apkg"
    package.write_to_file(out)

    counts = {}
    for c in cards:
        counts[c["type"]] = counts.get(c["type"], 0) + 1
    breakdown = ", ".join(f"{v} {k}" for k, v in sorted(counts.items()))
    print(
        f"wrote {out} ({len(cards)} notes: {breakdown}; deck '{deck_name}', "
        f"deck_id {deck.deck_id}, {len(package.media_files)} media file(s))"
    )
    if salt:
        print(f"fresh mode: guid salt {salt} — re-importing creates NEW notes")
    else:
        print("stable guids: re-importing updates existing notes in place")
    print("import in Anki: File -> Import (or double-click the .apkg)")


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except KeyboardInterrupt:
        sys.exit(130)
    except Exception as e:  # never a traceback
        print(f"error: unexpected: {e}", file=sys.stderr)
        sys.exit(1)
