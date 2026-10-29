# Research Report: Building a Claude Code "Flashcard Deck Generator" Skill

## TL;DR
- A robust flashcard-generator skill rests on three well-documented pillars: (1) SRS card-quality principles from Wozniak's Twenty Rules, Matuschak, Nielsen, and Gwern, distillable into a concrete accept/reject rubric; (2) Anki's `#`-header CSV/TSV import format plus the genanki `.apkg` library and the AnkiConnect HTTP API for output; (3) the Agent Skills open standard (`SKILL.md`), where personal skills live in `~/.claude/skills/<name>/`.
- Recommended default output is a `#`-headered UTF-8 TSV with stable GUIDs (text import, zero dependencies); offer `.apkg` via genanki when media must be bundled or custom styling is needed, and AnkiConnect when Anki is running for live insertion.
- The skill should enforce the minimum-information/atomicity principle, prefer cloze or focused Q&A, reject non-atomic/set/binary/orphan cards, and let the user customize deck name, note type, card count, cloze-vs-basic, tags, and output format.

---

# TOPIC 1 — SRS Flashcard Formulation Principles

## Wozniak's Twenty Rules of Formulating Knowledge (SuperMemo, 1999)
Source: Piotr Wozniak, "Effective learning: Twenty rules of formulating knowledge," supermemo.com (also at supermemo.guru, "20 rules of knowledge formulation"). Rules are listed in order of importance; per the article's own summary, "the first 16 rules revolve around making memories simple." An underlying assumption is that you will use spaced repetition (repeat optimally, not just once).

1. **Do not learn if you do not understand.** Cramming un-understood material is astronomically slow and near-worthless (the "German history book in a language you don't speak" example).
2. **Learn before you memorize.** Build an overall picture / coherent structure before dismembering it into items. Read the chapter first (e.g., how an internal-combustion engine works), then make individual Q&As.
3. **Build upon the basics.** Simple models first; don't neglect basics. Verbatim: "Remember that usually you spend 50% of your time repeating just 3-5% of the learned material!" — basics are cheap to memorize but lapses on them are costly.
4. **Stick to the minimum information principle.** Formulate as simply as possible; both questions AND answers short. Simple items are easier to schedule and retain. The "Dead Sea" example splits one complex description into ~9 atomic Q&As.
5. **Cloze deletion is easy and effective.** Fill-in-the-blank ("Bill …[name] was the second US president to go through impeachment"). Fast to create, mnemonically strong; recommended for beginners; core of incremental reading.
6. **Use imagery.** "A picture is worth a thousand words"; graphic representation is far less volatile. Great for anatomy, geography, geometry, chemistry, history.
7. **Use mnemonic techniques.** Peg lists, mind maps (Tony Buzan). Consciously needed in only ~1–5% of items; becomes automatic with practice.
8. **Graphic deletion is as good as cloze deletion.** Occlude parts of an image; one image can yield 10–20 items. (This is the conceptual basis of image occlusion.)
9. **Avoid sets.** Asking for members of a set (e.g., "What countries belong to the EU?") is very costly; convert to enumerations. Sets with >5 members are near-unmemorizable without mnemonics.
10. **Avoid enumerations.** Also hard; if unavoidable, use **overlapping cloze deletions** (the alphabet example: "A … … … E").
11. **Combat interference.** Similar items get confused; interference is "probably the single greatest cause of forgetting" for experienced users. Make items unambiguous; detect and eliminate leeches.
12. **Optimize wording.** Reduce sentences to compact, specific maxims so the "right bulb" lights fast (the Quark/PageMaker cloze progressively shortened to "PageMaker lost ground to …").
13. **Refer to other memories.** Build items on existing memories for context and reduced interference ("shamelessly humble and supplicant" → cringing).
14. **Personalize and provide examples.** Link to your personal life ("a soft bed without arms or back, like the one at Robert's parents") — highly interference-resistant.
15. **Rely on emotional states.** Vivid/shocking examples aid recall (banter / "Mandela and de Klerk in 1992").
16. **Context cues simplify wording.** Category prefixes (e.g., `bioch:` for biochemistry) put the brain in the right context and cut typing/reading.
17. **Redundancy does not contradict the minimum information principle.** Passive+active recall pairs, reasoning cues, derivation steps, and multiple representations are welcome — the extra information goes in *extra items*.
18. **Provide sources** (except well-proven knowledge like 2+2=4). Sources help you judge reliability and update knowledge; kept out of the learned content itself.
19. **Provide date stamping.** For volatile knowledge (statistics, software versions).
20. **Prioritize.** Prioritize sources, extraction, formulation, and via the forgetting index. Effective learning is fundamentally about prioritizing.

## Andy Matuschak — "How to write good prompts" (andymatuschak.org/prompts, 2020)
The central mechanism is **retrieval practice** (the testing effect): "when you attempt to recall some knowledge from memory, the act of retrieval tends to reinforce those memories." Prompt design *is* task design. Five properties of effective retrieval-practice prompts:
- **Focused** — one detail at a time; too much detail dulls concentration and produces incomplete retrievals.
- **Precise** — vague questions elicit vague answers.
- **Consistent** — should light the same bulbs each time; inconsistent answers risk "retrieval-induced forgetting."
- **Tractable** — you can almost always answer correctly (break down / add cues); SuperMemo-family algorithms are tuned for ~90% accuracy.
- **Effortful** — must actually require retrieval, not trivial inference ("retrieval effort hypothesis," Pyc & Rawson 2009).

Prompt types: factual, procedural, conceptual, plus **open-list** and **salience** prompts (which generate new answers each time and rely on a different theory of change).
**Anti-patterns / litmus tests:**
- *Avoid binary (yes/no, this/that) prompts* — low effort, shallow understanding; rephrase as open-ended (his omelette and chicken-stock examples).
- *Discourage pattern matching* — long, unusually worded questions/clozes get answered by shape, not knowledge; keep short and simple. Cloze deletions copied from text are especially susceptible.
- *False positives*: could you answer without really knowing? *False negatives*: could you know but fail (missing context, or alternative correct answers not excluded)?
- Write and revise **iteratively** (5–10 prompts per first pass); revise on the "internal sigh." The single most important thing to optimize is the emotional connection to your reviews.

## Michael Nielsen — "Augmenting Long-term Memory" (augmentingcognition.com/ltm.html, 2018)
"Anki makes memory a choice, rather than a haphazard event." Anki is a *virtuoso skill* for deep understanding, not just rote memory. Heuristics:
- **Break things into atomic facts** — one routinely-wrong combined question becomes multiple routinely-right atomic questions; atomic questions can still involve complex, high-level concepts.
- **Build rich hierarchies of interconnections and integrative questions**; complex questions are allowed only as part of a hierarchy of atomic prompts.
- **Don't put in orphan questions** (isolated, weakly-related prompts feel like a burden and are hard to recall); write more than one question about a new subject; use **elaborative encoding** (connect facts to existing memories).
- **Use Anki in service of a personal creative project**, not to stockpile knowledge for hypothetical future use — cards tied to real work are easier to recall and connect to emotionally.
- Do the encoding yourself; add figures ("we're good at remembering the general shape"); beware committing false facts (attribute the claim when unsure).
- Reading papers: multiple passes, skipping what you don't understand at first; typically extract ≥5 questions from a worthwhile paper.

## Gwern Branwen — "Spaced Repetition for Efficient Learning" (gwern.net/spaced-repetition)
Evidence review. The **testing effect** ("the mere act of testing someone's memory will strengthen the memory") and the **spacing effect** (Ebbinghaus 1885: distributed practice >> massed "cramming") are among the most robust findings in memory research. Key practical takeaways:
- SRS is for **maintenance** of memories/skills, not acquisition of new skills — "If one is a gifted amateur when one starts reviewing, one remains a gifted amateur." New expertise comes from deliberate practice (Ericsson).
- Students and teachers grossly underestimate spacing vs. cramming.
- Avoid multiple-choice (inferior; solution: "don't use multiple choice"); use free recall.
- **The 5-minute rule**: add an item if you expect to spend >5 minutes over your lifetime looking it up (or if not knowing it costs >5 minutes). Corollary heuristic: don't bother with SRS if you need the knowledge sooner than ~5 days.

## Underpinning research (summary level)
- **Roediger & Karpicke (2006)**, "The Power of Testing Memory" — the testing effect.
- **Karpicke & Blunt (2011)** — retrieval practice produces more learning than elaborative studying with concept mapping.
- **Cepeda et al.** spacing studies; **Bjork & Bjork (1992)** "New Theory of Disuse" (desirable difficulties); **Pyc & Rawson (2009)** retrieval effort hypothesis.

## Modern Anki community best practices
- **Cloze deletion**: the built-in "Cloze" note type has fields `Text` and `Extra`; syntax `{{c1::...}}`. It is treated specially and cannot be created from a regular note type.
- **Image occlusion**: built-in natively since **Anki 23.10** — a special cloze-on-images note type ("hide all, guess one" and "hide one, guess one" modes).
- **Atomicity, avoiding orphan cards, minimal formatting** — echo Wozniak and Nielsen.
- **Deck organization philosophy — fewer decks, more tags.** Decks control study boundaries and scheduling; tags describe content. Use `::` for a shallow subdeck hierarchy; prefer tags for cross-cutting classification (`source::…`, `topic::…`), applied at the note level.
- **FSRS (Free Spaced Repetition Scheduler)**: default in Anki 23.10+, with FSRS-6 in newer versions. It replaces SM-2's ease factor with trained parameters (stability, difficulty, retrievability) and exposes one main knob — **desired retention**. Per the fsrs4anki tutorial, "90% should work fine for most people" (80–95% reasonable); higher retention raises workload non-linearly. Optimization data requirements have relaxed over versions: "In Anki 24.04, at least 400 reviews are required; in older versions, at least 1000 reviews are required… In Anki 24.06+, there is no minimum number of reviews required for optimization." **Card-formulation advice does NOT change under FSRS** — the FSRS documentation itself recommends reading Wozniak's 20 Rules, noting that poor encoding/card formulation still tanks retention and merely optimizing parameters "encourages users to continue their bad habits." The design target is the **desirable difficulty** principle: review at the edge of forgetting.

## Synthesis — Card-Quality Rubric (for an AI generating cards)
**Accept / generate when a card is:**
1. **Atomic** — one fact/idea per card (minimum information principle).
2. **Precise & consistent** — single unambiguous answer; short question, shorter answer.
3. **Effortful & tractable** — requires genuine recall yet is ~90% answerable.
4. **Contextualized** — category cue, source, and date (if volatile); worded to avoid interference.
5. **Understood-first** — generated only from material the source actually explains.
6. **Vivid & emotionally anchored (when natural)** — where the material allows, ties the fact to imagery, a striking example, or a personal/emotional hook (Wozniak rules 14–15; cf. Matuschak: the emotional connection to reviews is the single most important thing to optimize). Concrete, evocative phrasing resists interference far better than dry abstraction — but don't force it: a manufactured hook is worse than none, and personal anchors should come from the learner rather than be invented on their behalf.

**Reject or rewrite when a card is:**
- A **set/enumeration** → convert to atomic items or overlapping clozes.
- **Binary** (yes/no, this/that) → convert to open-ended.
- **Wordy / long / pattern-matchable** → optimize wording; shorten.
- An **orphan** → add ≥1 related or integrative card.
- **Not understood** or a possibly-false fact → attribute the claim or drop it.

**How many cards per concept:** typically **1–5 atomic cards per concept** (Wozniak's Dead Sea paragraph → ~9 cards; Gwern/Nielsen: ≥5 per worthwhile paper). Prefer fewer, higher-value cards; avoid completionism.

**When to use which type:**
- **Cloze** — facts embedded in meaningful sentences, definitions, enumerations (overlapping), quotes (multiple clozes). Fast and mnemonically strong.
- **Q&A (Basic)** — discrete factual/conceptual/procedural questions; use Basic-and-reversed only for genuinely bidirectional pairs (e.g., vocabulary).
- **Image occlusion / graphic deletion** — spatial/visual/labeled material (anatomy, diagrams, maps).

---

# TOPIC 2 — Anki Import Formats & Deck Generation

## Text (CSV/TSV) import — current Anki (2.1.54+ through 25.x)
Requirements (official manual, docs.ankiweb.net/importing/text-files.html):
- **Plain text, UTF-8.** `.txt`/`.csv`; other formats (xls/rtf/doc) must be converted first.
- Field count is set by the first non-comment line; rows with fewer fields → missing treated as blank; extra fields dropped.
- Separator is auto-detected (comma/semicolon/tab) unless forced by a header.

### File headers (Anki 2.1.54+)
`#key:value` pairs, each on its own line at the top of the file. Because they begin with `#`, older clients ignore them. Supported keys:

| Key | Allowed values | Behaviour |
|---|---|---|
| `#separator:` | `Comma`,`Semicolon`,`Tab`,`Space`,`Pipe`,`Colon` or the literal character | Field separator |
| `#html:` | `true`/`false` | Treat field content as HTML |
| `#tags:` | space-separated tags | Adds these tags to every imported note |
| `#columns:` | names separated by the chosen separator | Column names / count |
| `#notetype:` | note type name or id | Presets note type (if it exists) |
| `#deck:` | deck name or id | Presets deck (if it exists) |
| `#notetype column:` | `1`,`2`,… | Which column holds the note type per row |
| `#deck column:` | `1`,`2`,… | Which column holds the deck per row |
| `#tags column:` | `1`,`2`,… | Which column holds tags per row |
| `#guid column:` | `1`,`2`,… | Which column holds the GUID per row |

Example (TSV):
```
#separator:tab
#html:true
#notetype:Basic
#deck:MyDeck::Subdeck
#tags:imported source-x
#columns:Front	Back	tags
What is X?	X is Y.	topic-a
```
(When a `#notetype column` or `#deck column` is present, the first "regular" column maps to the note type's first field, the second regular column to the second field, and so on — allowing mixed note types/decks in one file.)

### Field mapping, escaping, media
- Columns map to note fields in order; a column can be mapped to tags.
- **Escaping**: wrap fields containing the separator or newlines in double quotes; escape a literal `"` by doubling it (`""`). LibreOffice does this automatically (recommended over Excel for UTF-8).
- **Multi-line fields**: quoted newlines OR HTML `<br>` (requires `#html:true`). Quoted multi-line breaks clozes that span lines — use `<br>` for those.
- **HTML entities** when not treating content as HTML: `&lt;`, `&gt;`, `&amp;`.
- **Media**: reference `<img src="myimage.jpg">` or `[sound:myaudio.mp3]`; the files themselves must be copied manually into the `collection.media` folder (no subdirectories). **Plain CSV/TSV cannot bundle media** — this is precisely why `.apkg` exists.

### Duplicates & updating
- The **first field** is the identity key by default; a matching first field + same note type → the existing note's other fields are updated in place, preserving scheduling. A drop-down can instead ignore duplicates or import as new.
- **Match scope**: "note type" or "note type and deck."
- **GUID column** enables round-trip updates: export with GUIDs, edit, keep the GUID, re-import to update existing notes. If a provided GUID already exists, no duplicate is created. Anki recommends putting your own IDs (e.g., `MYNOTE0001`) in the **first field**, not the internal GUID, since GUIDs are meant to be Anki-generated (Anki can dedup on either the first field or the GUID).

## Cloze syntax
- Basic: `{{c1::text}}`. With hint: `{{c1::text::hint}}`.
- Multiple clozes per note: `{{c1::…}} {{c2::…}}` → separate cards (c1, c2, …). Reusing a number (both `c1`) hides both together on a single card.
- Hold **Alt/Option** while clicking the `[...]` button to reuse the current cloze number instead of incrementing.
- Clozes need not fall on word boundaries (partial-word hints, e.g., `C[…]` for "Canberra").
- **Nested cloze deletions** supported since **Anki 2.1.56**.
- The Cloze note type has fields `Text` + `Extra` (Extra shows on the answer side); it cannot be built from a regular type (clone the Cloze type to customize), and you cannot add extra card templates to it.

## Note types
- **Basic** (Front, Back → 1 card), **Basic (and reversed card)** (2 cards), **Basic (optional reversed card)** (adds an "Add Reverse" field), **Basic (type in the answer)**, **Cloze** (Text, Extra), **Image Occlusion** (built-in 23.10+).
- Custom note types: define fields + card templates (`qfmt`/`afmt` HTML using `{{Field}}`, `{{FrontSide}}`, plus CSS).

## genanki (Python) — `.apkg` generation
Repo: github.com/kerrickstaley/genanki (MIT, author Kerrick Staley; the repo currently shows ~2.6k stars / ~198 forks, requires Python ≥3.8). Install: `pip install genanki`. Core classes: `Model`, `Note`, `Deck`, `Package`.

```python
import genanki, random, html

my_model = genanki.Model(
    1607392319,                        # model_id — hardcode a stable random 32-bit int
    'Simple Model',
    fields=[{'name': 'Question'}, {'name': 'Answer'}],
    templates=[{
        'name': 'Card 1',
        'qfmt': '{{Question}}',
        'afmt': '{{FrontSide}}<hr id="answer">{{Answer}}',
    }],
    css='.card{font-family:arial;font-size:20px;text-align:center;}')

my_note = genanki.Note(model=my_model, fields=['Capital of Argentina', 'Buenos Aires'])

my_deck = genanki.Deck(2059400110, 'Country Capitals')   # deck_id — hardcode stable random int
my_deck.add_note(my_note)

pkg = genanki.Package(my_deck)
pkg.media_files = ['sound.mp3', 'images/img.jpg']        # files in cwd; reference by basename only
pkg.write_to_file('output.apkg')
```
Key details:
- **Stable IDs**: generate once with `random.randrange(1 << 30, 1 << 31)` (`python3 -c "import random; print(random.randrange(1 << 30, 1 << 31))"`) and hardcode `model_id`/`deck_id`. Use a unique `model_id` per model to avoid duplicate note types on import.
- **GUIDs**: default GUID = hash of all field values; a note imported with the same GUID overwrites the existing note (requires the models to have the same fields). Override to hash only identity fields:
  ```python
  class MyNote(genanki.Note):
      @property
      def guid(self):
          return genanki.guid_for(self.fields[0])
  ```
- **Cloze model**: `genanki.CLOZE_MODEL`. Since v0.13.0 it has **two** fields (Text, Extra) — matching Anki's real Cloze type — so pass `fields=['{{c1::Rome}} is the capital of {{c2::Italy}}', '']` (empty second field is fine). Older versions raise a `DeprecationWarning`.
- **Media**: add a field, reference the **basename** (`<img src="img.jpg">` / `[sound:s.mp3]`) inside the *field* (NOT the template); filenames must be unique; no path in the field.
- **HTML escaping**: field data is HTML — escape literal `<`, `>`, `&` (e.g., `html.escape`), including inside LaTeX.
- `sort_field` / `sort_field_index` configurable.
- **Maintenance/limits**: genanki is the de-facto standard for programmatic deck generation but is lightly maintained; it only *writes* `.apkg` files and cannot edit a live collection except when run inside an Anki add-on (`.write_to_collection_from_addon()`).

### Alternatives (what exists)
- **`pip install anki`** — the official Anki Python package (full collection backend; heavier, tightly version-coupled).
- **apy** (lervag/apy) — CLI to add/edit a local collection directly, without Anki running.
- **AnkiPandas** (klieret) — read/analyze the collection via pandas dataframes; write-back is currently disabled and the project is seeking a maintainer.
- **AnkiConnect** — HTTP API into a running Anki (below). Higher-level tools (inka, Obsidian_to_Anki) depend on it.

## AnkiConnect HTTP API
Add-on code **2055492159**; HTTP server at **http://127.0.0.1:8765**; JSON POST; API **version 6**. Canonical docs are now at **foosoft.net/projects/anki-connect/** and the sourcehut repo **git.sr.ht/~foosoft/anki-connect** — the GitHub repo `FooSoft/anki-connect` was **archived read-only on Nov 4, 2025** (the old `amikey` GitHub mirror is stale/v5 and should not be used). Bind address is configurable via the `webBindAddress` config key (default `127.0.0.1`; restart required); optional API-key auth via the `apiKey` config key (then include `"key"` in every request). Anki must be running.

**Envelope.** Every request is `{"action": "...", "version": 6, "params": {...}}`. Every response is exactly `{"result": <value>, "error": null}` — `error` is a descriptive string on failure and `null` on success. **Omitting `version` defaults to 4, and at version ≤4 the response contains ONLY the result (no `error` field)** — always send `"version": 6`.

Core actions (all version 6):
- **requestPermission** → `{"permission":"granted","requireApiKey":false,"version":6}`. Call this first (only action allowed from any origin).
- **deckNames** → array of names. **createDeck** `{"deck":"A::B"}` → new deck id.
- **modelNames** → array; **modelFieldNames** `{"modelName":"Basic"}` → `["Front","Back"]`.
- **createModel** `{modelName, inOrderFields, css, isCloze, cardTemplates:[{Name, Front, Back}]}` → full model object (`isCloze:true` makes it a Cloze type).
- **addNote** — `params.note`:
  ```json
  {
    "deckName": "Default",
    "modelName": "Basic",
    "fields": {"Front": "front content", "Back": "back content"},
    "options": {
      "allowDuplicate": false,
      "duplicateScope": "deck",
      "duplicateScopeOptions": {"deckName": "Default", "checkChildren": false, "checkAllModels": false}
    },
    "tags": ["yomichan"],
    "picture": [{"url": "https://…/img.jpg", "filename": "black_cat.jpg", "skipHash": "…", "fields": ["Back"]}]
  }
  ```
  Returns the created note id (or `null`). `duplicateScope:"deck"` checks only the target deck; any other value checks the whole collection. `audio`/`video`/`picture` each take `filename` + one of `data` (base64) / `path` / `url`, optional `skipHash`, and `fields` (which fields to attach the media to).
- **addNotes** `{notes:[...]}` → array of ids (`null` where a note could not be created).
- **canAddNotes** `{notes:[...]}` → array of booleans; **canAddNotesWithErrorDetail** → `[{canAdd, error}]`.
- **updateNoteFields** `{note:{id, fields:{...}}}` → `null`. (Do not have the note open in the Browse editor, or the update won't apply.)
- **notesInfo** `{notes:[ids]}` → `[{noteId, modelName, tags, fields:{name:{value, order}}, ...}]`.
- **findNotes** `{query:"deck:current"}` → note ids. Anki search syntax: `deck:"A::B"`, `tag:x`, `tag:none`, `note:Basic`, `front:hello`, `is:due|new|review|suspended`, `prop:ivl>=10`, `added:7`, wildcards `*`/`_`, AND (space) / `OR` / `-` negation / parentheses.
- **storeMediaFile** `{filename, data|path|url}` (precedence data→path→url) → the stored filename string. Prefix the filename with `_` to prevent Anki from purging it as unused; `deleteExisting:false` to avoid overwriting.
- **multi** `{actions:[...]}` → batch multiple actions in one request (returns an array of results in order).

The add-on itself is still actively released on AnkiWeb (a recent version referenced by clients is 25.11.9.0, released 2025-11-02); the wire API remains version 6. Development is self-serve (features added via user PRs); community forks add extras (e.g., `answerCards`, `setDueDate`).

## Best practices for programmatically generated decks
- **Stable GUIDs** for re-import/update workflows: genanki custom `guid`, or `#guid column` / first-field ID in CSV.
- **Deck naming** with the `::` hierarchy, kept shallow.
- **Tag conventions**: hierarchical `topic::subtopic`, `source::…`, applied at note level.
- **HTML in fields**: set `#html:true` (or escape entities); genanki/AnkiConnect field data is HTML.
- **Avoid duplicate note types**: reuse one stable `model_id`/`modelName` rather than regenerating a new one each run.

## Choosing an output method
- **CSV/TSV with `#` headers** — default: zero dependencies, transparent, human-editable, updatable via GUID; **but cannot bundle media**.
- **`.apkg` (genanki)** — when bundling media, using custom note types/styling, or shipping a self-contained deck; imported via File → Import.
- **AnkiConnect** — when Anki is running and live insertion/updating (and media upload with dedup checks) is desired.

---

# TOPIC 3 — Claude Code Skill-Authoring Conventions

## SKILL.md format & the Agent Skills open standard
Skills follow the **Agent Skills open standard**, which Anthropic published at **agentskills.io on December 18, 2025** (with a specification and reference SDK). Per Anthropic's announcement, Microsoft adopted it in VS Code and GitHub, alongside coding agents such as Cursor, Goose, Amp, and OpenCode; the official agentskills.io showcase lists more than 40 skills-compatible products (including OpenAI Codex, GitHub Copilot, Cursor, Gemini CLI, and VS Code). A skill is a directory whose required entrypoint is a `SKILL.md`: YAML frontmatter + a Markdown body.

**Spec-portable frontmatter fields** — the only ones usable *outside* Claude Code (claude.ai upload, the Skills API, and `package_skill.py` packaging): `name`, `description`, `license`, `compatibility`, `metadata`, `allowed-tools`.
- **`name`** (required by spec): lowercase letters, numbers, hyphens; **max 64 chars**; **must match the folder name**.
- **`description`** (required/strongly recommended): **max 1,024 chars** (spec). State *what the skill does + when to use it*, with trigger phrases. This is the single most important field for reliable triggering — it is loaded at startup for every skill (~100 tokens each).
- **`license`**, **`compatibility`** (string ≤500 chars — e.g., intended products, required system packages/network), **`metadata`** (free-form YAML map for your own tooling), **`allowed-tools`** (experimental; pre-approve tool access).

**Claude Code-only extras** (accepted by Claude Code but cause a *hard error* if uploaded to claude.ai / the Skills API): `when_to_use`, `argument-hint`, `arguments`, `disable-model-invocation`, `user-invocable`, `disallowed-tools`, `model`, `effort`, `context` (`fork`), `agent`, `background`, `hooks`, `paths`, `shell`. In Claude Code, the combined `description` + `when_to_use` is truncated at **1,536 chars** in the skill listing, so put the key use case first.

Minimal valid skill:
```markdown
---
name: flashcard-deck-generator
description: Generate Anki-importable flashcard decks (CSV/TSV or .apkg) from source files in the working directory. Use when the user wants to make Anki cards, flashcards, or a study deck from notes, PDFs, markdown, or code.
---

# Flashcard Deck Generator
[instructions Claude follows when the skill is active]
```

## Progressive disclosure (3-tier)
1. **Metadata** (name + description) — always loaded at startup (~100 tokens/skill).
2. **SKILL.md body** — loaded when the skill triggers (or is invoked with `/name`); recommended **< 5,000 tokens** and **under 500 lines**.
3. **Bundled resources** (`references/`, `scripts/`, `assets/`) — loaded or executed only on demand.

## Recommended directory layout
```
flashcard-deck-generator/
├── SKILL.md              # required: overview + workflow (keep <500 lines)
├── references/
│   ├── srs-rubric.md     # the 20 Rules / card-quality checklist
│   └── anki-formats.md   # CSV headers, cloze syntax, genanki/AnkiConnect specs
├── scripts/
│   ├── build_apkg.py     # genanki wrapper (executed, not read into context)
│   └── ankiconnect.py    # HTTP client helper
└── assets/
    └── deck_template.tsv # header template
```
Reference the supporting files from SKILL.md so Claude knows what each contains and when to load it. Scripts are *executed* (e.g., via Bash), not read into context. Use the `${CLAUDE_SKILL_DIR}` substitution to reference bundled scripts regardless of the current working directory, and pair it with `allowed-tools: Bash(python3 ${CLAUDE_SKILL_DIR}/scripts/*)` so the script runs without a permission prompt.

## Where skills live & precedence
| Location | Path | Applies to |
|---|---|---|
| Enterprise | managed settings dir | all org users |
| **Personal** | `~/.claude/skills/<name>/SKILL.md` | all your projects |
| Project | `.claude/skills/<name>/SKILL.md` | that project only |
| Plugin | `<plugin>/skills/<name>/SKILL.md` | where the plugin is enabled |

Precedence: **enterprise > personal > project**; a skill at any of these levels also overrides a bundled skill of the same name; plugin skills are namespaced `plugin-name:skill-name`. For a **personal** skill, the command name comes from the **directory name** (the frontmatter `name` there only sets the display label). Live change detection picks up edits under `~/.claude/skills/` within a running session. Note: Cowork/cloud/routine sessions do NOT read `~/.claude/skills/` — a personal skill must be enabled for your claude.ai account (or committed to a repo's `.claude/skills/`) to run there.

## Discovery / invocation
- **Model-invoked**: Claude auto-loads a skill when the request matches its description (unless `disable-model-invocation: true`).
- **User-invoked**: `/skill-name`. Custom commands have been merged into skills; existing `.claude/commands/*.md` still work, but skills are preferred (they support supporting files, invocation control, and auto-loading).
- `disable-model-invocation: true` → manual only (use for side-effecting workflows); `user-invocable: false` → Claude-only background knowledge.
- Arguments via `$ARGUMENTS`, `$1` / `$ARGUMENTS[0]`, or named `arguments`. Dynamic context injection: `` !`command` `` runs a shell command and inlines its output before Claude sees the body.

## Skills vs. other mechanisms
- **Skill**: on-demand, filesystem-based procedure/knowledge; model- or user-invoked.
- **Slash command**: now effectively "a skill with no extra features."
- **Subagent**: a separate context/agent; a skill can run in one via `context: fork`.
- **CLAUDE.md**: always-in-context project facts (skills load on demand — cheaper for long procedures).
- **MCP**: connects the agent to external tools/data; skills tell the agent *what to do* with them. (For this task, no MCP server is required — file reading and script execution suffice.)

## anthropics/skills reference examples
The official repo (github.com/anthropics/skills) ships production document skills (`docx`, `pdf`, `pptx`, `xlsx` — source-available) and example skills (`skill-creator`, `mcp-builder`, `webapp-testing`, etc. — Apache-2.0). The `pdf`/`docx` skills exemplify the pattern: a tight description with explicit "Use when… Do NOT use for…", bundled `scripts/` (Python) plus a `LICENSE.txt`, and instructions that convert files and then read them (e.g., `pdftoppm -jpeg → page-*.jpg → Read the images`). The `template-skill` is the recommended starting point.

## Patterns for skills operating on arbitrary working-directory files (multimodal)
- **Enumerate**: instruct Claude to list candidate files in the cwd (Glob / `ls`), or accept explicit paths via `$ARGUMENTS`.
- **Read by type**: read markdown/text/code directly; read **images natively** (Claude is multimodal — pass image files to Read); extract **PDF** text via `pdftoppm` → JPEG → Read images, or a Python extractor in `scripts/`.
- **Produce output in the cwd**: write the `.csv`/`.tsv`/`.apkg` to the current working directory and report the path (mirrors the docs' codebase-visualizer pattern, which writes an HTML file to cwd and prints its path).
- **Pre-approve** the exact Bash commands the scripts need via `allowed-tools` + `${CLAUDE_SKILL_DIR}`.

---

# SYNTHESIS — Recommended Architecture for the Skill

**Install location**: `~/.claude/skills/flashcard-deck-generator/` (personal skill; the directory name becomes the command `/flashcard-deck-generator`).

**Frontmatter** (spec-portable core only, so the skill also works if uploaded to claude.ai):
```yaml
---
name: flashcard-deck-generator
description: >-
  Generate customizable, Anki-importable spaced-repetition flashcard decks from
  arbitrary source files (markdown, text, PDF, images, source code) in the working
  directory, applying evidence-based card-formulation rules. Use when the user
  wants Anki cards, flashcards, a study deck, cloze notes, or to turn notes/PDFs
  into a deck. Supports CSV/TSV, .apkg (genanki), and AnkiConnect output.
license: MIT
---
```

**SKILL.md body (workflow)**:
1. **Gather inputs** — enumerate files in the cwd or use `$ARGUMENTS` paths; identify file types.
2. **Confirm customization** — deck name, note type(s) (Basic / Cloze / Image Occlusion), target card count (or "as warranted"), tags, and output format (TSV default, `.apkg`, or AnkiConnect). Offer sensible defaults.
3. **Ingest content** — read text/markdown/code directly; read images natively; extract PDF text (bundled script or `pdftoppm` → Read).
4. **Draft cards applying the rubric** (load `references/srs-rubric.md`): atomic, minimum-information, precise/consistent/effortful; cloze for embedded facts, Q&A for discrete items, image occlusion for visuals; avoid sets/binary/orphans; add source/date cues; 1–5 cards per concept.
5. **Self-critique pass** — reject/rewrite cards failing the rubric (litmus tests: false positives/false negatives).
6. **Emit output**:
   - **TSV** (default): UTF-8 with `#separator:tab`, `#html:true`, `#notetype:`, `#deck:`, `#columns:`, `#tags:`, and a `#guid column` using a content-hashed stable ID for re-import updates.
   - **`.apkg`**: run `scripts/build_apkg.py` (genanki with hardcoded stable `model_id`/`deck_id`, `CLOZE_MODEL` support, media via `media_files`, custom `guid`).
   - **AnkiConnect**: `scripts/ankiconnect.py` — requestPermission → createDeck → (createModel) → canAddNotes → addNotes → storeMediaFile; version 6 at 127.0.0.1:8765.
7. **Report** the output file path(s) in the cwd plus import instructions.

**Customization knobs → mechanism:** deck name (`#deck:` / `Deck(...)` / `deckName`); note type (`#notetype:` / model / `modelName`); card count; cloze vs. basic vs. image-occlusion; tags (`#tags:` / `tags`); output format (TSV / `.apkg` / AnkiConnect); update behavior (stable GUIDs).

## Recommendations
1. **Default to `#`-headered UTF-8 TSV** with a GUID column — universal, dependency-free, and updatable. Switch to `.apkg` only when media or custom styling is needed, and to AnkiConnect only when the user confirms Anki is running (and permission is granted).
2. **Bake the rubric into `references/srs-rubric.md`** and have the skill apply it, then self-critique against it. This is the single biggest quality lever — no scheduler (SM-2 or FSRS) can compensate for poorly formulated cards.
3. **Keep SKILL.md under 500 lines**; push exact Anki syntax and genanki/AnkiConnect snippets into `references/` to load on demand.
4. **Use stable, hardcoded model/deck IDs and content-hashed GUIDs** so regeneration *updates* rather than *duplicates* existing notes.
5. **Write output to the cwd and print the path**; pre-approve script execution via `allowed-tools` + `${CLAUDE_SKILL_DIR}`.
6. **Benchmarks/thresholds that change the plan**: if the skill triggers on the wrong requests, tighten/narrow the `description`; if decks fail to import, verify UTF-8 encoding and header syntax; if duplicates appear on re-import, verify GUID stability; if the user needs media or offline self-contained decks, escalate from TSV to `.apkg`; if they want live/iterative insertion into an open collection, escalate to AnkiConnect.

## Caveats
- **genanki** is lightly maintained and only *writes* `.apkg` files (no live-collection edits outside an add-on); pin the version and use two-field `CLOZE_MODEL` (v0.13.0+).
- **AnkiConnect's** canonical repo moved to sourcehut (GitHub archived Nov 4, 2025); it requires Anki running and a permission grant, and a few fields (`notesInfo` extras, `canAddNotesWithErrorDetail`) vary slightly by add-on version/fork. Always send `"version": 6`.
- The **Cloze note type** cannot be created from a regular type and cannot have extra card templates.
- **Plain CSV/TSV cannot bundle media** — media must be placed in `collection.media` or shipped via `.apkg`/AnkiConnect.
- Several **SKILL.md frontmatter fields are Claude Code-only** and will hard-error if the skill is uploaded to claude.ai / the Skills API — restrict frontmatter to the six spec fields (`name`, `description`, `license`, `compatibility`, `metadata`, `allowed-tools`) for cross-platform portability.
- **FSRS** defaults/versions evolve (FSRS-6 in current Anki; optimization now needs no minimum reviews in Anki 24.06+). The stable conclusions — "~90% desired retention for most people" and "card formulation still matters" — hold, but exact parameter counts and review-count requirements may change with releases.
- The **Anki `#`-header importer** requires 2.1.54+ (default path in 2.1.55+); on 2.1.54 the new importing option must be enabled in preferences. A known open issue (ankitects/anki #4205) reports that some spreadsheet-exported files can have their `#notetype` header ignored while `#separator`/`#html`/`#deck` are honored — prefer explicitly setting note type and verifying the import preview.
