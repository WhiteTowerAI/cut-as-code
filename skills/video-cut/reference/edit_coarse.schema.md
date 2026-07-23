# `edit_coarse.json` — format spec + worked example

This is the **hand-written editorial decision** — the one file the model authors by
judgment. Everything downstream is mechanical. Get this right.

## Schema
```jsonc
{
  "source": "work/source.mp4",
  "title": "<short title>",
  "source_duration_s": 3978.5,          // full original duration (seconds)
  "strategy": "<2-4 sentences: what the video is, where the value is, what to drop, target length>",

  "keep": [                              // blocks to KEEP, chronological
    {"in": 6.5, "out": 18.0, "reason": "<one line: what this is + why it stays>"}
    // ...
  ],
  "drop": [                              // blocks to REMOVE, chronological
    {"in": 0.0, "out": 6.5, "reason": "<one line: what this is + why it goes>"}
    // ...
  ],
  "drop_note": "Coarse (structural) drops only. Internal pauses > SPLIT_GAP inside each KEEP block are auto-trimmed by build_edit.py and not enumerated here."
}
```

## Hard rules
1. **Tile the whole timeline.** `keep` ∪ `drop` must cover `[0, source_duration_s]`
   with **no gaps and no overlaps**. Every drop's `out` equals the next keep's `in`,
   and vice versa. (A 0.1s tiling mismatch is a real bug — check it.)
2. **Every span has `in`, `out`, and a one-line `reason`.** The reason is required —
   it is the audit trail for the edit and forces you to justify each call.
3. **Boundaries land on sentence/clause ends.** Verify with `inspect_bounds.py` and
   nudge any boundary that starts/stops mid-sentence or on a stammer onto a clean edge.
   `inspect_bounds.py` also prints `⚠ dangling exit` when a block ends on a hanging
   conjunction/preposition/article ("...I liked. Because") or splits a capitalized
   proper-noun bigram ("...too Southern" / dropped "Cross") — fix those.

   **How a word is kept (load-bearing):** `build_edit.py` keeps a word when the word's
   **center** `(start+end)/2` falls inside `[in,out]` — it does NOT clip at the raw
   timestamp. So a word is fully in or fully out, and nudging an `out` by ±0.2s flips one
   whole word across the boundary cleanly. Reason about boundary nudges in those terms.
4. **Chronological order** unless reordering clearly helps (monologues back-reference,
   so reorder cautiously).
5. Internal dead air inside a keep block is NOT your job here — `build_edit.py`
   reclaims pauses > SPLIT_GAP automatically.

## Editorial targets to hunt (the "bad-edit" spots)
- Slow/draggy intro & dead lead-in before the speaker starts.
- Platform/subscription plugs, self-promo, "why I do this" manifestos.
- Repetition / rambling / near-duplicate restatements of the same point.
- Tangents and life-lesson asides off the main topic.
- Long monologue runs >40s with no structure (from analysis.json).
- Dead air / long silences (auto-trimmed, but big ones may justify a structural drop).
Keep the substance (the actual analysis/story/value) as **large blocks**, then let the
script tighten them.

## Worked example (real — the P0 "Monday Morning Meeting" podcast)
66-min single-shot talking-head schoolboy-rugby podcast → 31-min cut (47%).
13 keep-blocks, 14 drop-spans. Excerpt (full file lives at `examples/edit_coarse.json`):

```json
{
 "source": "work/source.mp4",
 "title": "Monday Morning Meeting Podcast No.14 2026 (HS Top 200 schoolboy rugby)",
 "source_duration_s": 3978.5,
 "strategy": "66-min single-shot talking-head podcast. First ~27 min is slow preamble (intro boilerplate, subscription plugs, a self-justifying manifesto, trip logistics, a crossover-fixture wish-list) the host himself thrice calls 'way too long' -> keep only a few high-value nuggets. Real value (27-66 min) is team-by-team rugby analysis -> keep as large blocks, drop only clear tangents and let internal >1.5s pauses auto-trim. Chronological order preserved. Target ~half length.",
 "keep": [
  {"in": 6.5,   "out": 18.0,  "reason": "Cold open: host + show intro. Trims 6.7s dead lead-in; drops platform plugs that follow."},
  {"in": 362.5, "out": 388,   "reason": "Core framing in one clean bite: rankings are his blunt honest opinion, put out to be challenged."},
  {"in": 1010.5,"out": 1054,  "reason": "Best rationale nugget: ~99% of players want exposure, so he runs a Top 200 to widen it."},
  {"in": 1808,  "out": 2993,  "reason": "MAIN ANALYSIS BLOCK (30:08-49:52): team-by-team / player-by-player deep dive. Internal dead air auto-trimmed."}
 ],
 "drop": [
  {"in": 0.0,   "out": 6.5,   "reason": "Dead cold-open / silent lead-in."},
  {"in": 18.0,  "out": 362.5, "reason": "Platform & subscription plugs + self-promo + trip thanks + opening of the mission monologue. Pure preamble."},
  {"in": 388.0, "out": 1010.5,"reason": "Bulk of the mission manifesto: repetition about scouts using rankings + socials advice. One nugget kept at 6:02."}
 ],
 "drop_note": "Coarse (structural) drop spans only. Internal pauses > 1.5s inside each KEEP block are auto-trimmed by build_edit.py."
}
```

Note how keep `out`=18.0 meets drop `in`=18.0; drop `out`=362.5 meets keep `in`=362.5 —
perfect tiling. Each span carries a self-justifying reason.
