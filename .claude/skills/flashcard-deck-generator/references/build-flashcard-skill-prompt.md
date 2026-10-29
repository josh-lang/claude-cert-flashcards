# Build and install the `flashcard-deck-generator` skill

You are in a directory containing `flashcard-skill-research-report.md`. **Read it in full before writing anything** — it is the design spec (SRS card-formulation rubric, exact Anki import syntax, genanki/AnkiConnect API detail, and skill-authoring conventions). Build the skill described in its "SYNTHESIS — Recommended Architecture" section, extended by the requirements below. Where these instructions add scope beyond the report, these instructions win.

## Deliverable

A personal skill installed at `~/.claude/skills/flashcard-deck-generator/`, invocable from **any** directory (auto-triggered or via `/flashcard-deck-generator`), that turns arbitrary source files in the current working directory — markdown, plain text, source code, PDFs, and images — into high-quality Anki-importable decks by applying the report's card-quality rubric (items 1–6, including "Vivid & emotionally anchored").

### Layout

```
~/.claude/skills/flashcard-deck-generator/
├── SKILL.md                 # <500 lines: workflow, batch + interactive modes, command grammar
├── references/
│   ├── srs-rubric.md        # Topic 1 distilled: 20 Rules + Matuschak/Nielsen + full accept/reject rubric
│   ├── anki-formats.md      # exact TSV header syntax, cloze syntax, note types, escaping, media rules
│   └── ankiweb-sync.md      # AnkiWeb sync paths + credential security rules (Extension 1)
├── scripts/
│   ├── build_tsv.py         # emit #-headered UTF-8 TSV incl. guid column
│   ├── build_apkg.py        # genanki wrapper: stable model/deck ids, CLOZE_MODEL, media bundling
│   ├── ankiconnect.py       # JSON client incl. sync; degrades gracefully when Anki isn't running
│   └── extract_pdf.py       # PDF → text; fall back to pdftoppm page images for scanned PDFs
└── assets/
    └── deck-template.tsv
```

### Frontmatter

Stick to the portable fields — `name: flashcard-deck-generator` (must match the folder), `description`, `license: MIT`, `metadata` — plus `allowed-tools` pre-approving `Bash(python3 ${CLAUDE_SKILL_DIR}/scripts/*)`. Make the description a little **pushy** to combat under-triggering: what it does + explicit trigger contexts ("make flashcards", "Anki deck", "study cards", "turn these notes into cards", "quiz material", "let's go through this together and make cards"), per the report's description guidance. You may optionally add the Claude-Code-only `argument-hint: "[interactive|batch] [paths...]"`, with a comment noting it must be removed if the skill is ever uploaded to claude.ai.

## Core behavior (from the report — implement all of it)

1. **Ingestion**: take explicit paths as arguments, otherwise enumerate the cwd and confirm the selection. Read markdown/text/code directly; read images natively (multimodal); PDFs via `extract_pdf.py`.
2. **Card drafting**: apply the rubric — atomic, precise/consistent, effortful-yet-tractable (~90% answerable), contextualized (source + date for volatile facts), understood-first, vivid where natural. Prefer cloze for facts embedded in sentences, Q&A for discrete items; convert sets/enumerations to overlapping clozes; no binary questions; no orphan cards; 1–5 cards per concept, favoring fewer high-value cards over completionism.
3. **Self-critique pass** before emitting: run every card back through the rubric's reject list; fix or drop failures.
4. **Outputs** (user-selectable, TSV default):
   - TSV with `#separator:tab`, `#html:true`, `#notetype:`, `#deck:`, `#columns:`, `#tags:`, `#guid column:` — exact syntax is in the report; put it in `anki-formats.md`.
   - `.apkg` via genanki when media is involved or the user wants a self-contained file.
   - AnkiConnect live insertion when Anki is running (requestPermission → createDeck → canAddNotes → addNotes → storeMediaFile as needed; always `"version": 6`).
5. **Stable identity**: GUIDs must hash a stable per-card key — e.g., `sha1(source-path + concept-slug + ordinal)` — **not** the full field text, so wording edits update existing notes on re-import instead of duplicating. Generate one random `model_id`/`deck_id` pair per note type **once during this build** (`random.randrange(1 << 30, 1 << 31)`) and bake the constants into `build_apkg.py`.
6. **Customization knobs**: deck name (`::` hierarchy), note type(s), target card count, tags (hierarchical `topic::x`, `source::y`), output format, update-vs-fresh behavior. Ask once up front with sensible defaults; don't interrogate.

## Extension 1 — AnkiWeb integration

Goal: after cards are generated/added, get them onto AnkiWeb (and thus mobile) without manual steps.

- **Primary path — AnkiConnect `sync`**: after a successful `addNotes`, offer to call the `sync` action (`{"action": "sync", "version": 6}`) so the running desktop app pushes to AnkiWeb using its already-stored credentials — the skill never touches a password. Support `getProfiles`/`loadProfile` for multi-profile users. Verify exact action names/params against current AnkiConnect docs (canonical: foosoft.net/projects/anki-connect and git.sr.ht/~foosoft/anki-connect — the GitHub repo is archived).
- **Secondary path — headless sync (opt-in only)**: for use without the GUI, optionally sync a *closed* local collection via the official `anki` pip package, reading `ANKIWEB_USERNAME`/`ANKIWEB_PASSWORD` from environment variables (or prompting interactively without echoing). Make a timestamped backup of the collection first and hard-fail with a clear message if Anki appears to be running. The package's sync API changes across releases — **look up the current API before implementing** and pin the version you test against. If it proves too fragile, ship the AnkiConnect path only and document the limitation.
- **Hard rules**: there is no official AnkiWeb HTTP API — do **not** scrape or browser-automate the ankiweb.net login. Never write credentials to disk, logs, shell history, or the session file; never hardcode them; never echo them back. Richer AnkiWeb interaction (browsing shared decks, etc.) is out of scope for v1 — note it as a possible future extension in SKILL.md.

## Extension 2 — Interactive mode (the flagship feature)

Trigger: `/flashcard-deck-generator interactive [paths...]`, or naturally when the user says something like "let's go through this material together." Encode this protocol in SKILL.md:

1. **Setup**: list candidate sources; confirm selection and reading order; confirm deck name, note-type mix, tags, output format; create `.flashcard-session.json` in the cwd — or offer to resume if one already exists.
2. **Chunking**: split each source into linear sections (markdown headings, PDF pages, code modules, one image at a time) and show a mini table of contents so the user knows the shape of the journey.
3. **Per-chunk loop**:
   - 1–3 sentence orientation of the chunk ("learn before you memorize").
   - If the material is dense, *offer* a short explanation before carding ("do not learn if you do not understand") — ask, don't lecture.
   - Propose 1–5 numbered candidate cards, each tagged with its type (cloze / basic / reversed) and a one-line rubric justification.
   - Accept a compact command grammar: `all` · `1,3` · `edit 2: <new text>` · `drop 2` · `add: <topic or draft>` · `rewrite 1 as cloze` · `skip` · `back` · `settings <change>` · `stop`.
   - **Personalization prompts** (sparingly — every few chunks or on request): invite a personal example, mnemonic image, or emotional anchor for a hard card (rules 14–15) and fold the user's wording in verbatim. This elicitation is the point of interactive mode — never invent personal details on the user's behalf.
4. **Persistence**: after *every* chunk, update the session file (sources, cursor position, settings, accepted cards + GUIDs, and rejected topics so they aren't re-proposed) **and** flush accepted cards to the growing output file. A crash or `stop` must lose nothing; `interactive resume` continues from the cursor.
5. **Wrap-up**: totals by type, an orphan check (offer a companion card for any lone topic), emit the final output — and, if AnkiConnect is reachable, offer to push and then sync to AnkiWeb.

## Known hard bits (handle honestly)

- **Image occlusion**: the built-in IO note type stores occlusion data in a special internal format that is hard to generate externally. Investigate briefly; if fragile, fall back to embedding the image on a Basic/Cloze card (media via `.apkg` or `storeMediaFile`) and say so in SKILL.md rather than shipping broken IO notes.
- **Media in TSV**: plain TSV cannot bundle media — the skill must automatically escalate to `.apkg`/AnkiConnect when cards reference images or audio, or warn clearly.
- **Cloze note type**: cannot gain extra templates; use the real two-field model (`genanki.CLOZE_MODEL`, ≥ v0.13.0, fields Text + Extra).

## Build, test, install — do all of this now

1. Create the tree and write every file. Keep SKILL.md lean; push exact syntax into `references/` (progressive disclosure). Reference each bundled file from SKILL.md with guidance on when to load or run it.
2. Dependency checks, not crashes: scripts should detect missing `genanki`/`pypdf` and print the install one-liner. Tell me before installing anything.
3. **Smoke test** in a temp directory: write a small sample markdown; run `build_tsv.py` and `build_apkg.py` end to end; assert the TSV headers are well-formed and the `.apkg` is a valid zip containing a collection database; run `ankiconnect.py --check` and confirm it degrades gracefully when nothing is listening on 127.0.0.1:8765.
4. **Verify against current docs while building** (search the web as needed): the Anki text-import header set, the current genanki version and CLOZE_MODEL fields, the AnkiConnect action list, and the `anki` package sync API if you implement headless sync.
5. **Trigger check**: after installing, run two or three realistic test prompts against the skill (e.g., "turn ch3-notes.md into an Anki deck", "let's go through this PDF together and make cards") and confirm it triggers and behaves; tighten the description if it under- or over-triggers.
6. Finish by printing: the installed tree, the final frontmatter, every default you chose, and three usage examples — batch TSV from markdown notes; batch `.apkg` from a folder with images; an interactive session including `resume` and an AnkiWeb sync.

Ask me questions only if something genuinely blocks you; otherwise pick sensible defaults per the report and list them all at the end.
