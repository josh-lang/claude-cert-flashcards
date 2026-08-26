#!/usr/bin/env python3
"""Emit an Anki-importable #-headered UTF-8 TSV from a cards doc (JSON).

Part of the flashcard-deck-generator skill. Stdlib only.
Exit codes: 0 ok | 1 unexpected error | 2 bad input | 3 missing dependency.
"""

import argparse
import csv
import hashlib
import json
import re
import secrets
import sys

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


def main():
    ap = argparse.ArgumentParser(
        description="cards doc (JSON) -> Anki #-headered TSV with a guid column"
    )
    ap.add_argument("cards_json", help="path to the cards doc")
    ap.add_argument("--out", help="output .tsv path (default: <deck-slug>.tsv)")
    ap.add_argument("--deck", help="override the doc's deck name")
    ap.add_argument(
        "--fresh",
        action="store_true",
        help="salt every guid so re-import creates new notes instead of updating",
    )
    args = ap.parse_args()

    doc = load_doc(args.cards_json)
    deck = args.deck or doc.get("deck")
    if not deck or not isinstance(deck, str):
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

    n_media = sum(1 for c in cards if c.get("media"))
    if n_media:
        warn(
            f"{n_media} card(s) reference media files — plain TSV cannot bundle "
            "media. Use build_apkg.py or ankiconnect.py push, or copy the files "
            "into collection.media manually."
        )

    used_notetypes = {NOTETYPES[c["type"]] for c in cards}
    uniform = len(used_notetypes) == 1
    global_tags = doc.get("tags", [])
    out = args.out or f"{slugify(deck)}.tsv"

    with open(out, "w", encoding="utf-8", newline="") as f:
        f.write("#separator:tab\n#html:true\n")
        f.write(f"#deck:{deck}\n")
        if global_tags:
            f.write(f"#tags:{' '.join(global_tags)}\n")
        if uniform:
            only_type = cards[0]["type"]
            f1, f2 = FIELD_NAMES[only_type]
            f.write(f"#notetype:{NOTETYPES[only_type]}\n")
            f.write(f"#columns:guid\t{f1}\t{f2}\ttags\n")
            f.write("#guid column:1\n#tags column:4\n")
        else:
            f.write("#columns:guid\tnotetype\tfield1\tfield2\ttags\n")
            f.write("#guid column:1\n#notetype column:2\n#tags column:5\n")
        writer = csv.writer(
            f,
            delimiter="\t",
            quotechar='"',
            quoting=csv.QUOTE_MINIMAL,
            lineterminator="\n",
        )
        for i, (card, guid) in enumerate(zip(cards, guids), 1):
            v1, v2 = field_values(card, i)
            row = [guid]
            if not uniform:
                row.append(NOTETYPES[card["type"]])
            row += [
                html_newlines(v1),
                html_newlines(v2),
                " ".join(card.get("tags", [])),
            ]
            writer.writerow(row)

    counts = {}
    for c in cards:
        counts[c["type"]] = counts.get(c["type"], 0) + 1
    breakdown = ", ".join(f"{v} {k}" for k, v in sorted(counts.items()))
    print(f"wrote {out} ({len(cards)} notes: {breakdown}; deck '{deck}')")
    if salt:
        print(f"fresh mode: guid salt {salt} — re-importing creates NEW notes")
    else:
        print("stable guids: re-importing this file updates existing notes in place")
    print(
        'import in Anki: File -> Import, keep "Existing notes: Update", check the preview'
    )


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
