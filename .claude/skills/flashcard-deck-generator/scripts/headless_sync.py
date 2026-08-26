#!/usr/bin/env python3
"""OPT-IN: sync a *closed* local Anki collection with AnkiWeb, no GUI needed.

Part of the flashcard-deck-generator skill. Verified against anki==26.8.1
(2026-08); the anki package's sync API changes across releases — re-verify
before upgrading. The package is NOT installed by default.

Hard guards, in order:
  1. refuses to run while Anki appears to be running
  2. credentials only from ANKIWEB_USERNAME/ANKIWEB_PASSWORD or a no-echo
     prompt — never written, logged, or echoed
  3. requires confirmation (or --yes): opening the collection with a newer
     library than your desktop Anki can upgrade its schema
  4. creates a timestamped backup before syncing
  5. never performs a one-way full sync (upload/download) — bails instead

Exit codes: 0 ok | 1 unexpected error | 2 bad input/guard tripped | 3 missing dependency.
"""

import argparse
import getpass
import os
import subprocess
import sys


def fail(msg, code=2):
    print(f"error: {msg}", file=sys.stderr)
    sys.exit(code)


def anki_running():
    for proc_name in ("Anki", "anki"):
        try:
            result = subprocess.run(
                ["pgrep", "-x", proc_name], capture_output=True, timeout=10
            )
            if result.returncode == 0:
                return True
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False  # no pgrep — rely on the collection lock instead
    return False


def default_base():
    if sys.platform == "darwin":
        return os.path.expanduser("~/Library/Application Support/Anki2")
    if sys.platform.startswith("win"):
        return os.path.join(os.environ.get("APPDATA", ""), "Anki2")
    return os.path.expanduser("~/.local/share/Anki2")


def find_collection(args):
    if args.collection:
        if not os.path.isfile(args.collection):
            fail(f"no such collection file: {args.collection}")
        return os.path.abspath(args.collection)
    base = args.base or default_base()
    if not os.path.isdir(base):
        fail(f"Anki data dir not found: {base} (use --base or --collection)")
    profiles = sorted(
        d
        for d in os.listdir(base)
        if os.path.isfile(os.path.join(base, d, "collection.anki2"))
    )
    if not profiles:
        fail(f"no profiles with a collection.anki2 under {base}")
    if args.profile:
        if args.profile not in profiles:
            fail(f"profile '{args.profile}' not found; available: {profiles}")
        chosen = args.profile
    elif len(profiles) == 1:
        chosen = profiles[0]
    else:
        fail(f"multiple profiles found: {profiles} — pick one with --profile NAME")
    return os.path.join(base, chosen, "collection.anki2")


def get_credentials():
    username = os.environ.get("ANKIWEB_USERNAME")
    password = os.environ.get("ANKIWEB_PASSWORD")
    if username and password:
        return username, password
    if not sys.stdin.isatty():
        fail(
            "AnkiWeb credentials missing. Set ANKIWEB_USERNAME and "
            "ANKIWEB_PASSWORD environment variables (never pass them as "
            "command arguments), or run interactively to be prompted."
        )
    try:
        username = username or input("AnkiWeb username (email): ").strip()
        password = password or getpass.getpass("AnkiWeb password (not echoed): ")
    except (EOFError, KeyboardInterrupt):
        print(file=sys.stderr)
        fail("aborted")
    if not username or not password:
        fail("empty credentials")
    return username, password


def main():
    ap = argparse.ArgumentParser(
        description="Sync a CLOSED local Anki collection with AnkiWeb (opt-in; "
        "prefer 'ankiconnect.py sync' whenever Anki is running)",
        epilog="credentials: ANKIWEB_USERNAME / ANKIWEB_PASSWORD env vars, or "
        "an interactive no-echo prompt. They are never stored.",
    )
    ap.add_argument("--profile", help="Anki profile name (when several exist)")
    ap.add_argument("--base", help="Anki2 data dir (default: platform standard)")
    ap.add_argument("--collection", help="explicit path to collection.anki2")
    ap.add_argument(
        "--media", action="store_true", help="also sync media (waits for completion)"
    )
    ap.add_argument("--endpoint", help="custom sync server endpoint (self-hosted)")
    ap.add_argument(
        "--backup-dir",
        help="where to write the pre-sync backup (default: <profile>/backups)",
    )
    ap.add_argument(
        "--yes", action="store_true", help="skip the interactive confirmation"
    )
    args = ap.parse_args()

    if anki_running():
        fail(
            "Anki appears to be running. Quit Anki first, or sync through the "
            "GUI instead:  python3 <skill>/scripts/ankiconnect.py sync"
        )

    try:
        import anki.buildinfo
        from anki.collection import Collection
        from anki.sync import SyncOutput, SyncStatus
    except ImportError:
        print("error: the official 'anki' package is not installed.", file=sys.stderr)
        print(
            "install: python3 -m pip install anki   # large package (~200 MB)",
            file=sys.stderr,
        )
        sys.exit(3)

    lib_version = getattr(anki.buildinfo, "version", "unknown")
    col_path = find_collection(args)
    print(f"collection: {col_path}")
    print(f"anki library: {lib_version}")

    if not args.yes:
        if not sys.stdin.isatty():
            fail(
                "non-interactive run: pass --yes to confirm you accept that "
                "opening the collection with a newer library than your desktop "
                "Anki may upgrade its schema"
            )
        answer = (
            input(
                f"Opening this collection with anki {lib_version} may upgrade its "
                "schema if your desktop Anki is older (desktop would then require "
                "an update). A backup is made first. Proceed? [y/N] "
            )
            .strip()
            .lower()
        )
        if answer not in ("y", "yes"):
            fail("aborted by user")

    username, password = get_credentials()

    try:
        col = Collection(col_path)
    except Exception as e:
        fail(f"could not open the collection (locked or incompatible?): {e}")

    try:
        backup_dir = args.backup_dir or os.path.join(
            os.path.dirname(col_path), "backups"
        )
        os.makedirs(backup_dir, exist_ok=True)
        made = col.create_backup(
            backup_folder=backup_dir, force=True, wait_for_completion=True
        )
        print(
            f"backup: {'written to ' + backup_dir if made else 'skipped (nothing new)'}"
        )

        try:
            auth = col.sync_login(username, password, args.endpoint or None)
        except Exception as e:
            fail(f"AnkiWeb login failed: {e}")
        finally:
            password = None  # drop the reference as early as possible

        status = col.sync_status(auth)
        full_sync = getattr(SyncStatus, "FULL_SYNC", 2)
        no_changes = getattr(SyncStatus, "NO_CHANGES", 0)
        if status.new_endpoint:
            auth.endpoint = status.new_endpoint
        if status.required == full_sync:
            fail(
                "AnkiWeb requires a ONE-WAY full sync (schema change). This "
                "script never chooses upload-vs-download for you — open "
                "desktop Anki, sync once, and pick the direction deliberately."
            )
        if status.required == no_changes and not args.media:
            print("already in sync — nothing to do")
            return

        out = col.sync_collection(auth, sync_media=args.media)
        bad = {
            getattr(SyncOutput, "FULL_SYNC", 2),
            getattr(SyncOutput, "FULL_DOWNLOAD", 3),
            getattr(SyncOutput, "FULL_UPLOAD", 4),
        }
        if out.required in bad:
            fail(
                "the server now requires a one-way full sync — do it "
                "deliberately in desktop Anki (this script never will)."
            )
        if getattr(out, "server_message", ""):
            print(f"AnkiWeb says: {out.server_message}")

        if args.media:
            import time

            print("waiting for media sync…", flush=True)
            deadline = time.time() + 600
            while time.time() < deadline:
                st = col.media_sync_status()
                if not getattr(st, "active", False):
                    break
                progress = getattr(st, "progress", None)
                if progress is not None:
                    print(
                        f"  media: checked {getattr(progress, 'checked', '?')}, "
                        f"added {getattr(progress, 'added', '?')}, "
                        f"removed {getattr(progress, 'removed', '?')}",
                        flush=True,
                    )
                time.sleep(2)
            else:
                print(
                    "warning: media sync still running after 10 min — it may "
                    "finish on the next desktop sync",
                    file=sys.stderr,
                )
    finally:
        col.close()

    print("collection synced with AnkiWeb ✓")


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except KeyboardInterrupt:
        sys.exit(130)
    except Exception as e:  # never a traceback (and never a credential)
        print(f"error: unexpected: {e}", file=sys.stderr)
        sys.exit(1)
