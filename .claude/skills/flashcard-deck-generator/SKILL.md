---
name: flashcard-deck-generator
description: >-
  Turn source files in the current directory — markdown, notes, plain text,
  PDFs, source code, images — into high-quality Anki flashcard decks by
  applying evidence-based spaced-repetition rules (atomic cards, cloze
  deletions, no binary questions). Emits an Anki-importable TSV by default,
  a self-contained .apkg when media is involved, or inserts live via
  AnkiConnect, and can sync to AnkiWeb. Use whenever the user wants to make
  flashcards, build an Anki deck, create study cards or quiz material,
  memorize notes/a paper/a chapter, turn notes or a PDF into cards, or says
  things like "make flashcards from this", "turn this into an Anki deck",
  "help me study this", or "let's go through this material together and make
  cards" (interactive card-by-card mode with resume).
license: MIT
metadata:
  version: "1.0.0"
  source: built from flashcard-skill-research-report.md (2026-08)
allowed-tools: Bash(python3 ${CLAUDE_SKILL_DIR}/scripts/*)
# argument-hint is Claude Code-only: REMOVE the next line if this skill is
# ever uploaded to claude.ai or the Skills API (unknown fields hard-error there).
argument-hint: "[interactive|batch] [paths...]"
---

# Flashcard Deck Generator

Convert source material into Anki decks whose cards actually stick, by enforcing
an evidence-based formulation rubric (Wozniak's 20 Rules, Matuschak, Nielsen).
**Always load `references/srs-rubric.md` before drafting any cards.** Load
`references/anki-formats.md` when hand-checking TSV/cloze syntax or debugging an
import. Load `references/ankiweb-sync.md` when the user mentions AnkiWeb,
mobile, or syncing.

## Modes and output formats

| Situation | Do this |
|---|---|
| "make cards / a deck from X" | **Batch mode** (below) |
| "let's go through this together", "one section at a time", `/flashcard-deck-generator interactive` | **Interactive mode** (below) |
| `.flashcard-session.json` exists in cwd | Offer to **resume** before anything else |
| Default output | TSV via `build_tsv.py` |
| Any card references an image/audio file | **Escalate to `.apkg`** (TSV cannot bundle media) or AnkiConnect |
| User wants a single self-contained file | `.apkg` via `build_apkg.py` |
| User wants cards inserted into a running Anki | `ankiconnect.py check` first; only push if it succeeds |
| User mentions AnkiWeb / phone / sync | After output, offer sync per `references/ankiweb-sync.md` |

## Batch workflow

1. **Gather sources.** Use paths from `$ARGUMENTS` if given; otherwise enumerate
   the cwd (ls/Glob), propose the plausible source files, and confirm the
   selection. Ingest by type:
   - markdown / plain text / source code → Read directly
   - images (png/jpg/webp/gif) → Read natively (multimodal)
   - PDFs → `python3 ${CLAUDE_SKILL_DIR}/scripts/extract_pdf.py FILE.pdf`; if it
     prints `SCANNED PAGE n — Read this image: <path>` lines, Read those images
2. **Confirm the knobs once** — a single compact question with defaults
   pre-filled (see Defaults). Do not interrogate. Knobs: deck name, notetype
   mix, tags, target card count, output format, update-vs-fresh.
3. **Understand first.** Skim the whole source before carding (rubric: "learn
   before you memorize"). Skip material the source doesn't actually explain.
4. **Draft cards** applying `references/srs-rubric.md`: atomic; precise; ~90%
   answerable; contextualized (source, and date for volatile facts); cloze for
   facts embedded in sentences, Q&A for discrete items; sets/enumerations →
   overlapping clozes; no binary questions; no orphans; 1–5 cards per concept,
   favoring fewer high-value cards.
5. **Self-critique pass.** Run every draft back through the rubric's reject
   list; fix or drop failures before emitting. Say how many were cut.
6. **Write the cards doc** to `.flashcard-cards.json` in the cwd (contract
   below). If updating an existing deck, first load the previous cards doc /
   session file and **reuse its `guid_key` values** so re-import updates
   instead of duplicating.
7. **Emit**:
   - TSV: `python3 ${CLAUDE_SKILL_DIR}/scripts/build_tsv.py .flashcard-cards.json`
   - .apkg: `python3 ${CLAUDE_SKILL_DIR}/scripts/build_apkg.py .flashcard-cards.json`
   - Live: `python3 ${CLAUDE_SKILL_DIR}/scripts/ankiconnect.py push .flashcard-cards.json`
8. **Report**: output path, card counts by type, how to import (File → Import;
   keep "Existing notes: Update" to update by GUID), and that
   `.flashcard-cards.json` remains for inspection/reuse. Offer AnkiWeb sync if
   relevant.

## The cards doc (shared JSON contract)

Every emitter consumes the same JSON file. All three notetypes have exactly two
fields; canonical field keys are `Front`/`Back` (basic, basic-reversed) and
`Text`/`Back Extra` (cloze). Field content is HTML (`#html:true`): escape
literal `<`, `>`, `&` that aren't markup; emitters convert newlines to `<br>`.

```json
{
  "schema_version": 1,
  "deck": "Flashcards::Ch3 Notes",
  "default_notetype": "basic",
  "tags": ["source::ch3-notes"],
  "media_dir": ".",
  "cards": [
    {"type": "basic",
     "fields": {"Front": "In the Krebs cycle, what does one acetyl-CoA yield?",
                "Back": "3 NADH, 1 FADH2, 1 GTP"},
     "tags": ["topic::metabolism"],
     "guid_key": {"source": "ch3-notes.md", "slug": "krebs-yield", "ordinal": 1},
     "media": []},
    {"type": "cloze",
     "fields": {"Text": "The Krebs cycle occurs in the {{c1::mitochondrial matrix}}.",
                "Back Extra": "Source: ch3-notes.md"},
     "tags": [],
     "guid_key": {"source": "ch3-notes.md", "slug": "krebs-location", "ordinal": 1},
     "media": []}
  ]
}
```

Rules:
- `type`: `basic` | `basic-reversed` | `cloze`. Use `basic-reversed` only for
  genuinely bidirectional pairs (vocabulary).
- `guid_key` (`source` + `slug` + `ordinal`) is the card's **stable identity**:
  guid = sha1 of `"source|slug|ordinal"`. Keep slugs short, kebab-case,
  concept-based (not wording-based) so edits update rather than duplicate.
  `ordinal` distinguishes sibling cards of one concept (1, 2, …).
- `media`: paths relative to `media_dir`; reference **basenames only** inside
  fields (`<img src="fig1.png">`). Any media ⇒ don't emit plain TSV.
- Tags never contain spaces; use `::` hierarchies (`topic::x`, `source::y`).

## Interactive mode (flagship)

Trigger: `/flashcard-deck-generator interactive [paths...]`, or naturally when
the user wants to work through material together.

**Setup.** List candidate sources; confirm selection and reading order; confirm
deck name, notetype mix, tags, output format. If `.flashcard-session.json`
exists and is `in-progress`, summarize it (deck, cards accepted, next chunk)
and offer to resume instead. Otherwise create `.flashcard-session.json`: a
cards doc plus a `session` object:

```json
{"schema_version": 1, "skill": "flashcard-deck-generator",
 "deck": "…", "default_notetype": "basic", "tags": [], "media_dir": ".",
 "cards": [],
 "session": {
   "status": "in-progress", "created": "<iso8601>", "updated": "<iso8601>",
   "output": {"format": "tsv", "path": "<deck-slug>.tsv"},
   "target_count": null,
   "sources": [{"path": "ch3.md", "kind": "markdown", "sha1": "<file sha1>",
                "chunks": [{"id": "h:Intro", "label": "Intro", "loc": "lines 1-38"}]}],
   "cursor": {"source_idx": 0, "chunk_idx": 0},
   "rejected_topics": [],
   "personalization_last_chunk": 0}}
```

**Chunking.** Split each source once at setup and persist the chunk list;
show a mini table of contents. Chunk ids are stable: markdown `h:<heading path>`
(dedupe with ` #2`), PDFs `p:<n>` or `p:<a-b>`, code `mod:<path>` /
`sym:<TopLevelName>`, plain text `sec:<n>`, images `img:<basename>`. `loc` is
only a re-reading hint. Aim for chunks a person can hold in mind (a section,
1–2 pages, a module).

**Per-chunk loop.**
1. Orient in 1–3 sentences (learn before you memorize).
2. If the material is dense, *offer* a short explanation first — ask, don't
   lecture ("do not learn if you do not understand").
3. Propose 1–5 numbered candidate cards, each with its type and a one-line
   rubric justification.
4. Accept commands:

   | Command | Effect |
   |---|---|
   | `all` | accept every proposed card |
   | `1,3` | accept only those numbers |
   | `edit 2: <new text>` | apply the user's wording; keep the same `guid_key` |
   | `drop 2` | reject; add its topic to `rejected_topics` (never re-propose) |
   | `add: <topic or draft>` | draft one more card on that |
   | `rewrite 1 as cloze` | convert the card's type |
   | `skip` | move on, accepting nothing |
   | `back` | return to the previous chunk |
   | `settings <change>` | adjust deck/tags/format/count mid-run |
   | `stop` | flush everything and end (resume later) |

5. **Personalization (sparingly).** Every ~3–4 chunks (track via
   `personalization_last_chunk`) or on request, invite a personal example,
   mnemonic image, or emotional anchor for one hard card, and fold the user's
   wording in **verbatim**. This elicitation is the point of interactive mode —
   never invent personal details on the user's behalf.
6. **Flush after EVERY chunk (hard rule):** rewrite `.flashcard-session.json`
   (cards, cursor, settings, rejected topics, `updated`), then regenerate the
   output file by running the chosen emitter **on the session file itself**
   (emitters ignore the `session` key), e.g.
   `python3 ${CLAUDE_SKILL_DIR}/scripts/build_tsv.py .flashcard-session.json --out <path>`.
   A crash or `stop` must lose nothing.

**Resume.** On `interactive resume` (or detecting the file): validate
`skill`/`schema_version`/`status`, compare each source's sha1 (if changed, warn
and offer continue vs re-chunk from cursor), summarize, continue at `cursor`.

**Wrap-up.** Totals by type; orphan check (offer a companion card for any lone
topic — no orphans); set `session.status` to `"complete"`; final emit; then, if
`ankiconnect.py check` succeeds, offer push and AnkiWeb sync.

## Scripts

All are pre-approved via `allowed-tools`. Uniform exit codes: **0** ok ·
**1** unexpected error · **2** bad input / Anki unreachable · **3** missing
dependency (the script prints the exact install one-liner — relay it and ask
before installing anything).

| Invocation | Purpose |
|---|---|
| `python3 ${CLAUDE_SKILL_DIR}/scripts/build_tsv.py CARDS_JSON [--out F] [--deck N] [--fresh]` | `#`-headered UTF-8 TSV with guid column (stdlib only) |
| `python3 ${CLAUDE_SKILL_DIR}/scripts/build_apkg.py CARDS_JSON [--out F] [--deck N] [--fresh]` | self-contained `.apkg`, bundles media (needs genanki) |
| `python3 ${CLAUDE_SKILL_DIR}/scripts/ankiconnect.py check` | probe 127.0.0.1:8765; degrades gracefully when Anki is closed |
| `python3 ${CLAUDE_SKILL_DIR}/scripts/ankiconnect.py push CARDS_JSON [--allow-duplicate]` | createDeck → storeMediaFile → canAddNotes → addNotes |
| `python3 ${CLAUDE_SKILL_DIR}/scripts/ankiconnect.py sync` | ask the running Anki to sync with AnkiWeb |
| `python3 ${CLAUDE_SKILL_DIR}/scripts/ankiconnect.py profiles [--load NAME]` | list/switch Anki profiles |
| `python3 ${CLAUDE_SKILL_DIR}/scripts/extract_pdf.py FILE.pdf [--pages A-B]` | PDF → per-page text; scanned pages → page images to Read |
| `python3 ${CLAUDE_SKILL_DIR}/scripts/headless_sync.py [--profile P] [--media]` | **opt-in** AnkiWeb sync without the GUI (see ankiweb-sync.md; never run unprompted) |

`--fresh` deliberately breaks guid stability (salts every guid) so a re-import
creates new notes instead of updating — only when the user asks for a fresh
copy.

## Defaults (offer these, let the user override)

- Deck: `Flashcards::<Source Title>` (shallow `::` hierarchy). Output file:
  `<deck-slug>.tsv` / `.apkg` in the cwd.
- Tags: `source::<source-stem>` globally; `topic::<slug>` per card where natural.
- Count: as warranted — 1–5 per concept; fewer, higher-value cards over
  completionism. Suggest a target only if asked.
- Format: TSV; auto-escalate to `.apkg` on media. Update-by-guid (no `--fresh`).
- Notetype: judgment per rubric; `default_notetype: basic`.

## Known limitations (state honestly when relevant)

- **Image occlusion**: Anki's built-in IO notetype stores occlusion geometry in
  an internal format that is fragile to generate externally — this skill does
  not create IO notes. Fallback: embed the image on a Basic/Cloze card
  (`.apkg` media or `storeMediaFile`) and cloze/ask around it. Possible future
  extension.
- **Cloze** uses the real two-field model (`Text`, `Back Extra`); it cannot
  gain extra templates and cannot be built from a regular notetype.
- **Plain TSV cannot bundle media** — escalate to `.apkg`/AnkiConnect, or the
  user must copy files into `collection.media` manually.
- **AnkiConnect cannot set GUIDs** — `push` is insert-with-duplicate-skip;
  wording updates to pushed notes need a TSV/apkg re-import or desktop edits.
- **AnkiWeb has no official HTTP API** — never scrape or browser-automate
  ankiweb.net; never handle AnkiWeb credentials outside `headless_sync.py`'s
  documented env-var path. Richer AnkiWeb interaction (browsing shared decks)
  is out of scope for v1.
- Localized (non-English) Anki installs rename built-in notetypes; `push` maps
  fields positionally via `modelFieldNames` to tolerate this, but TSV import
  may need the user to pick the notetype in the import dialog.

## Import instructions (tell the user)

Anki: **File → Import**, select the file. Check the preview — especially that
the notetype was honored — and keep **Existing notes: Update** so guid-matched
rows update in place (scheduling is preserved). For big updates to a mature
deck, suggest **File → Create Backup** first. `.apkg`: import directly or
double-click; media is bundled.
