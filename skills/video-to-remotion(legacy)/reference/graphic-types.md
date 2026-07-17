# Graphic types — what the video's content triggers

`analyze_content.py` scans the transcript (and optional scene cuts) and emits
*opportunities*. Each opportunity type maps to one Remotion component. This is
the decision table the analyzer encodes and the agent prunes.

| type          | what triggers it (in the content)                                  | component        | props                          | default dur |
|---------------|--------------------------------------------------------------------|------------------|--------------------------------|-------------|
| `lower-third` | a self-introduction — "I'm X", "it's X from Y", "my name is X"      | `LowerThird`     | `{ name, org? }`               | 4.5s        |
| `stat`        | a number worth flagging — `%`, `$`, `4,334 frames`, `3x`, ≥10      | `StatCallout`    | `{ value, label }`             | 4.0s        |
| `list`        | an enumeration — "three ways", "first … second …"                  | `ListReveal`     | `{ count, title, items[] }`    | count×4s    |
| `keypoint`    | a question or punchy line worth pinning                            | `KeypointCallout`| `{ text }`                     | 6.0s        |
| `section`     | a topic boundary — a long pause (≥1.8s) and/or a scene cut          | `SectionCard`    | `{ title, index? }`            | 3.0s        |

## `almanac` theme cards (hand-placed; no detector)

The `almanac` theme (see `SKILL.md` → Themes) adds a cream/serif card language derived from
launch-video design research (`docs/design-research/`). These are **hand-placed** in
`FinalEdit`'s `CUES` like `Intro`/`Outro` — the analyzer emits no opportunity for them. Two
exceptions reuse existing detector output: point a `list` cue at `Checklist` and a `keypoint`
cue at `ReframeCard` when running `THEME="almanac"` (same content, themed renderer — an author
choice, not an automatic swap). All read `T`, so they inherit the cream card + coral
accent + Newsreader automatically.

| component      | props                                                                      | notes |
|----------------|----------------------------------------------------------------------------|-------|
| `TitleBumper`  | `{ title, kicker? }`                                                       | full-bleed cream takeover (footage hidden); the signature moment |
| `BeforeAfter`  | `{ before, after, beforeLabel?, afterLabel?, beforeSub?, afterSub? }`      | 2-col cream card; left strikethrough + "BEFORE", right ink + "AFTER" (labels overridable) |
| `Checklist`    | `{ items[], kicker? }`                                                     | coral `01/02/03` numerals; the themed `ListReveal` (reuses `list`) |
| `CommandChips` | `{ items[{cmd,desc}], kicker? }`                                           | mono cmd chip (system-mono fallback) + serif desc |
| `PromptCard`   | `{ segments[{t,hl?}], kicker? }`                                           | quoted prompt; `hl:true` segments render coral |
| `ReframeCard`  | `{ instead, avoid?, kicker? }`                                            | "INSTEAD SAY" + coral line; the themed `KeypointCallout` (reuses `keypoint`) |
| `Outro`        | `{ title, sub?, small? }`                                                 | re-skin: full-bleed cream, centered CSS coral diamond + wordmark |

`TitleBumper` and the `almanac` `Outro` are full-bleed (opaque cream, footage gone) — a
momentary cutaway, anchor-agnostic. The rest ride a solid cream card and honor `ANCHOR`.

## content.json schema
```jsonc
{
  "source": "work/transcript.json",
  "duration_s": 70.0,
  "fps": 24,
  "n_opportunities": 7,
  "opportunities": [
    {
      "type": "lower-third",        // one of the types above
      "at": 1.2,                    // seconds; word-accurate from the transcript
      "dur": 4.5,                   // suggested on-screen duration (seconds)
      "props": { "name": "Jordan Reyes", "org": "Field Research" },
      "quote": "it's Jordan from the Field Research team"  // the line it came from
    }
  ]
}
```

## Notes on the heuristics
- **Detection is a draft, not a verdict.** Names, stats and sections are regex /
  pause heuristics; the agent must read `quote` and confirm before keeping a cue.
- `items` for a `list` is left empty by the analyzer — it only knows the *count*.
  The agent fills the actual items from the surrounding transcript.
- `section` titles are taken from the segment at/after the boundary and trimmed
  to ~6 words; rewrite them into real chapter titles.
- To add a new graphic type: add a detector in `analyze_content.py`, a row here,
  a component under `examples/components/`, and an entry in `FinalEdit`'s
  `COMPONENTS` map.
