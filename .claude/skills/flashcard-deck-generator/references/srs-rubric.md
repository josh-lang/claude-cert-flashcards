# SRS Card-Formulation Rubric

Distilled from Wozniak's *Twenty Rules of Formulating Knowledge* (SuperMemo,
1999), Andy Matuschak's *How to write good prompts* (2020), Michael Nielsen's
*Augmenting Long-term Memory* (2018), and Gwern's spaced-repetition evidence
review. The mechanism being exploited is **retrieval practice**: attempting
recall strengthens memory (testing effect), and spacing beats massing
(spacing effect). No scheduler — SM-2 or FSRS — can compensate for badly
formulated cards.

## ACCEPT a card only if it is all of

1. **Atomic** — one fact/idea per card (minimum information principle). A
   complex passage becomes several atomic cards, never one big one (Wozniak's
   Dead Sea paragraph → ~9 cards). Atomic questions may still involve complex,
   high-level concepts (Nielsen).
2. **Precise & consistent** — a single unambiguous answer; short question,
   shorter answer. It should light the same "bulbs" every time; alternative
   correct answers must be excluded by the wording.
3. **Effortful yet tractable** — requires genuine retrieval (not readable off
   the question's shape) yet is answerable ~90% of the time. Break down or add
   cues until tractable; SRS algorithms are tuned for ~90% accuracy.
4. **Contextualized** — carries the context cue it needs (category prefix like
   `chem:` when interference looms), the **source**, and a **date for volatile
   facts** (statistics, versions, prices). Worded to avoid interference with
   similar cards — interference is the single greatest cause of forgetting.
5. **Understood-first** — generated only from material the source actually
   explains, that the learner can be expected to understand. Do not card what
   is not understood; suggest learning it first.
6. **Vivid & emotionally anchored (when natural)** — tie the fact to imagery,
   a striking example, or a personal/emotional hook (rules 14–15; Matuschak:
   the emotional connection to reviews is the single most important thing to
   optimize). Concrete, evocative phrasing resists interference far better
   than dry abstraction. **Never force it**: a manufactured hook is worse than
   none, and personal anchors must come from the learner — invite them, fold
   the learner's wording in verbatim, never invent personal details.

## REJECT or REWRITE when a card is

| Failure | Fix |
| --- | --- |
| A **set** question ("Which countries…?") | Convert to atomic items, or overlapping clozes |
| An **enumeration** (ordered list) | Overlapping clozes: `{{c1::A}} {{c2::B}} {{c3::C}}`, each hiding one step with neighbors visible |
| **Binary** (yes/no, this/that) | Rephrase open-ended: "What…", "Why…", "What happens if…" |
| **Wordy / pattern-matchable** — long or unusually worded; answerable by shape, not knowledge (verbatim-copied clozes are especially prone) | Optimize wording; shorten relentlessly ("PageMaker lost ground to …") |
| An **orphan** — isolated, unconnected to anything else in the deck | Add ≥1 related or integrative companion card, or drop it |
| **Not understood / possibly false** | Attribute the claim ("According to X…") or drop it |
| **Multiple facts** smuggled into one card | Split |
| **False positive** risk — answerable without knowing (trivial inference, giveaway cue) | Raise retrieval effort |
| **False negative** risk — knowable but failable (missing context; several right answers) | Add the missing cue; exclude alternatives |

## Card-type selection

| Material | Type |
| --- | --- |
| Fact embedded in a meaningful sentence; definitions; quotes | **Cloze** (`{{c1::…}}`; hint: `{{c1::…::hint}}`) — fast, mnemonically strong |
| Discrete factual/conceptual/procedural question | **Basic** Q&A |
| Genuinely bidirectional pair (term ↔ meaning, word ↔ translation) | **Basic (and reversed card)** — only then |
| Enumeration/sequence | Overlapping clozes across `c1…cN` |
| Spatial/visual/labeled material | Embed the image on a Basic/Cloze card and ask around it (this skill does not generate Image Occlusion notes) |

Prefer free recall always; never multiple-choice (Gwern: markedly inferior).

## How many cards

**1–5 atomic cards per concept**; ≥5 from a genuinely worthwhile paper or
chapter is normal (Nielsen), but favor fewer, higher-value cards over
completionism. Wozniak's 5-minute rule as the inclusion bar: card it if the
knowledge will cost more than ~5 minutes of lifetime lookups — and remember
you'll spend 50% of review time on 3–5% of material, so basics are cheap and
worth carding. Redundancy is fine **as extra items** (active+passive pairs,
derivation steps), never as bloat inside one card.

## Wozniak's Twenty Rules — one-line digest

1. Don't learn what you don't understand. 2. Learn (overview) before you
memorize. 3. Build on basics. 4. Minimum information principle. 5. Cloze
deletion is easy and effective. 6. Use imagery. 7. Use mnemonics.
2. Graphic deletion works like cloze. 9. Avoid sets. 10. Avoid enumerations
(if unavoidable → overlapping cloze). 11. Combat interference — make items
unambiguous. 12. Optimize wording to compact maxims. 13. Refer to other
memories. 14. Personalize with your own examples. 15. Rely on emotional
states. 16. Context cues (category prefixes) simplify wording.
3. Redundancy ≠ violating minimalism (goes in extra items). 18. Provide
sources. 19. Date-stamp volatile facts. 20. Prioritize ruthlessly.

## Self-critique protocol (run before emitting anything)

For every drafted card, in order: (1) more than one fact? → split; (2) set or
enumeration? → overlapping cloze; (3) binary? → open-ended; (4) answerable by
pattern or trivial inference? → tighten; (5) could a knowledgeable person fail
it (missing context / multiple right answers)? → add cue; (6) orphan? → add a
companion or drop; (7) unverified claim? → attribute or drop; (8) wordy? →
shorten. Report how many cards the pass cut or rewrote.
