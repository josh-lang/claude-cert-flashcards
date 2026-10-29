# AnkiWeb Sync — paths and hard rules

Goal: after cards are generated/added, get them onto AnkiWeb (and thus mobile)
without manual steps. There is **no official AnkiWeb HTTP API**.

## Hard rules (non-negotiable)

- **Never scrape or browser-automate the ankiweb.net login.**
- **Never write credentials anywhere** — not to disk, logs, shell history, the
  session file, or output; never hardcode; never echo back. The only permitted
  channels are the `ANKIWEB_USERNAME` / `ANKIWEB_PASSWORD` environment
  variables and a no-echo interactive prompt inside `headless_sync.py`.
- Never run `headless_sync.py` unprompted — it is strictly **opt-in** and
  operates on the user's real collection.
- Browsing/downloading shared decks and other richer AnkiWeb interaction is
  out of scope for v1 (possible future extension).

## Primary path — AnkiConnect `sync` (Anki running; preferred)

The desktop app pushes to AnkiWeb using its **already-stored** credentials —
the skill never touches a password.

1. After a successful `ankiconnect.py push …`, offer:
   `python3 ${CLAUDE_SKILL_DIR}/scripts/ankiconnect.py sync`
   (fires `{"action": "sync", "version": 6}`; the script allows this action up
   to 120 s — large first syncs can be slow; conflicts are resolved in the app).
2. Multi-profile users: `ankiconnect.py profiles` lists profiles;
   `ankiconnect.py profiles --load NAME` switches before pushing.
3. Requires the AnkiConnect add-on (code **2055492159**) and, on first contact,
   the user clicking "allow" in Anki's permission dialog.

## Manual fallback (no add-on, or user prefers)

Import the generated `.tsv`/`.apkg` in desktop Anki, press **Sync** (or ⌘Y).
Mobile devices pull on their next sync. Recommend **File → Create Backup**
before large imports into a mature collection.

## Secondary path — headless sync without the GUI (opt-in only)

`scripts/headless_sync.py` syncs a **closed** local collection straight to
AnkiWeb via the official `anki` Python package (verified against
`anki==26.8.1`, 2026-08; its API churns across releases — re-verify before
upgrading). Not installed by default: the script prints
`python3 -m pip install anki` (a large package) and exits if missing.

What it does, in order — all guards are hard requirements:

1. **Refuses to run if Anki appears to be running** (process check; the
   collection's SQLite lock is a second line of defense).
2. Locates the profile under the Anki2 base dir
   (macOS: `~/Library/Application Support/Anki2`); `--profile NAME` if several.
3. Reads credentials from `ANKIWEB_USERNAME`/`ANKIWEB_PASSWORD`, else prompts
   interactively without echoing. Missing + non-interactive → clean exit.
4. Warns that opening the collection with a **newer library than the installed
   desktop app can upgrade the collection schema** (desktop would then demand
   an update); requires confirmation (`--yes` to skip in scripts).
5. **Creates a timestamped backup** (`Collection.create_backup`) into the
   profile's `backups/` dir before syncing.
6. Logs in (`sync_login`), checks `sync_status`; a required **one-way full
   sync is never performed** — the script bails and directs the user to do
   that deliberately in desktop Anki (upload vs download is destructive).
7. Runs a normal `sync_collection`; `--media` also syncs media (waits for the
   background media sync to finish before closing).

Example:

```bash
ANKIWEB_USERNAME=you@example.com ANKIWEB_PASSWORD=… \
  python3 ${CLAUDE_SKILL_DIR}/scripts/headless_sync.py --profile "User 1" --yes
```

When in doubt, prefer the AnkiConnect path — it cannot corrupt anything and
never sees a credential.
