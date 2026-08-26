#!/usr/bin/env python3
"""AnkiConnect client: check | push CARDS_JSON | sync | profiles.

Part of the flashcard-deck-generator skill. Stdlib only. Talks JSON to the
AnkiConnect add-on (code 2055492159) at http://127.0.0.1:8765, API version 6.
Degrades gracefully when Anki is not running (exit 2, friendly message).
Exit codes: 0 ok | 1 unexpected error | 2 bad input / Anki unreachable | 3 missing dependency.
"""

import argparse
import hashlib
import json
import os
import re
import sys
import urllib.error
import urllib.request

DEFAULT_URL = "http://127.0.0.1:8765"

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
        if ctype == "cloze" and "{{c" not in first:
            fail(f"card #{i}: cloze card has no {{{{c1::…}}}} deletion in 'Text'")
        check_tags(card.get("tags", []), f"card #{i}")
        media = card.get("media", [])
        if not isinstance(media, list) or any(not isinstance(m, str) for m in media):
            fail(f"card #{i}: 'media' must be a list of paths")
    return doc


class AnkiConnect:
    def __init__(self, url, key=None):
        self.url = url
        self.key = key

    def invoke(self, action, timeout=15, **params):
        payload = {"action": action, "version": 6}
        if params:
            payload["params"] = params
        if self.key:
            payload["key"] = self.key
        req = urllib.request.Request(
            self.url,
            json.dumps(payload).encode("utf-8"),
            {"Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                body = json.loads(resp.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError, OSError):
            fail(
                f"Anki is not reachable at {self.url}. Start Anki with the "
                "AnkiConnect add-on (code 2055492159), or export a .tsv/.apkg "
                "instead."
            )
        except json.JSONDecodeError:
            fail(f"non-JSON response from {self.url} — is that really AnkiConnect?")
        if not isinstance(body, dict) or "error" not in body or "result" not in body:
            fail(
                "unexpected response shape from AnkiConnect "
                "(need API version 6 — update the add-on)"
            )
        if body["error"] is not None:
            fail(f"AnkiConnect: {body['error']}")
        return body["result"]

    def grant(self):
        perm = self.invoke("requestPermission")
        if not isinstance(perm, dict) or perm.get("permission") != "granted":
            fail(
                "AnkiConnect denied permission — click 'Yes' in the Anki dialog "
                "and retry"
            )
        return perm


def cmd_check(client, _args):
    client.grant()
    version = client.invoke("version")
    print(f"AnkiConnect OK (API version {version}, permission granted)")


def cmd_sync(client, _args):
    client.grant()
    client.invoke("sync", timeout=120)
    print("AnkiWeb sync triggered — check the Anki window for progress/conflicts.")


def cmd_profiles(client, args):
    client.grant()
    if args.load:
        client.invoke("loadProfile", name=args.load)
        print(f"loaded profile: {args.load}")
    else:
        for name in client.invoke("getProfiles"):
            print(name)


def cmd_push(client, args):
    doc = load_doc(args.cards_json)
    deck = args.deck or doc.get("deck")
    if not deck or not isinstance(deck, str):
        fail("no deck name (set 'deck' in the doc or pass --deck)")
    cards = doc["cards"]
    global_tags = doc.get("tags", [])

    client.grant()

    if deck not in client.invoke("deckNames"):
        client.invoke("createDeck", deck=deck)
        print(f"created deck '{deck}'")

    # Map our two canonical field values positionally onto the real field
    # names, tolerating renamed/localized notetypes.
    model_names = client.invoke("modelNames")
    real_fields = {}
    for ctype in {c["type"] for c in cards}:
        model = NOTETYPES[ctype]
        if model not in model_names:
            fail(
                f"notetype '{model}' does not exist in this collection "
                "(localized Anki? create it or rename the localized one)"
            )
        names = client.invoke("modelFieldNames", modelName=model)
        if len(names) < 2:
            fail(f"notetype '{model}' has fewer than 2 fields")
        real_fields[ctype] = names

    # Upload media before the notes that reference it.
    media_dir = doc.get("media_dir") or "."
    base = os.path.dirname(os.path.abspath(args.cards_json))
    root = media_dir if os.path.isabs(media_dir) else os.path.join(base, media_dir)
    stored = set()
    for i, card in enumerate(cards, 1):
        for rel in card.get("media", []):
            path = os.path.abspath(
                rel if os.path.isabs(rel) else os.path.join(root, rel)
            )
            if not os.path.isfile(path):
                fail(f"card #{i}: media file not found: {path}")
            name = os.path.basename(path)
            if name not in stored:
                client.invoke("storeMediaFile", filename=name, path=path)
                stored.add(name)
    if stored:
        print(f"stored {len(stored)} media file(s) in collection.media")

    notes = []
    for i, card in enumerate(cards, 1):
        v1, v2 = field_values(card, i)
        names = real_fields[card["type"]]
        notes.append(
            {
                "deckName": deck,
                "modelName": NOTETYPES[card["type"]],
                "fields": {names[0]: html_newlines(v1), names[1]: html_newlines(v2)},
                "tags": list(dict.fromkeys(global_tags + card.get("tags", []))),
                "options": {
                    "allowDuplicate": bool(args.allow_duplicate),
                    "duplicateScope": "deck",
                    "duplicateScopeOptions": {
                        "deckName": deck,
                        "checkChildren": False,
                        "checkAllModels": False,
                    },
                },
            }
        )

    addable_flags = client.invoke("canAddNotes", notes=notes)
    addable = [n for n, ok in zip(notes, addable_flags) if ok]
    skipped = len(notes) - len(addable)
    if not addable:
        print(
            f"nothing to add — all {len(notes)} notes are duplicates in "
            f"'{deck}' (use --allow-duplicate to force)"
        )
        return
    ids = client.invoke("addNotes", notes=addable)
    added = sum(1 for i in ids if i)
    failed = len(addable) - added
    print(
        f"added {added} of {len(notes)} notes to '{deck}' ({skipped} duplicate(s) skipped)"
    )
    if failed:
        fail(f"{failed} note(s) passed canAddNotes but failed to add — check Anki")
    print(
        "note: AnkiConnect cannot set GUIDs; to *update* these notes later, "
        "re-import a TSV/apkg with stable guids or edit in Anki."
    )
    print("tip: push them to AnkiWeb with: ankiconnect.py sync")


def main():
    # The build spec's smoke test calls `ankiconnect.py --check`; accept it.
    if len(sys.argv) > 1 and sys.argv[1] == "--check":
        sys.argv[1] = "check"

    ap = argparse.ArgumentParser(
        description="Talk to a running Anki via AnkiConnect (API v6)",
        epilog="exit codes: 0 ok, 1 unexpected, 2 bad input/Anki unreachable, 3 missing dep",
    )
    ap.add_argument(
        "--url", default=DEFAULT_URL, help=f"AnkiConnect URL (default {DEFAULT_URL})"
    )
    ap.add_argument("--key", help="API key, if the add-on's apiKey config is set")
    sub = ap.add_subparsers(dest="command", required=True)

    sub.add_parser(
        "check", help="probe AnkiConnect; graceful exit 2 when Anki is closed"
    )

    p_push = sub.add_parser("push", help="insert a cards doc into the running Anki")
    p_push.add_argument("cards_json", help="path to the cards doc")
    p_push.add_argument("--deck", help="override the doc's deck name")
    p_push.add_argument(
        "--allow-duplicate",
        action="store_true",
        help="insert even if a duplicate exists in the deck",
    )

    sub.add_parser("sync", help="ask Anki to sync with AnkiWeb (stored login)")

    p_prof = sub.add_parser("profiles", help="list Anki profiles")
    p_prof.add_argument("--load", metavar="NAME", help="switch to this profile")

    args = ap.parse_args()
    client = AnkiConnect(args.url, args.key)
    {"check": cmd_check, "push": cmd_push, "sync": cmd_sync, "profiles": cmd_profiles}[
        args.command
    ](client, args)


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
