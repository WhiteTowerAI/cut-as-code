# Timeline Schema V1

`work/timeline.json` maps chronological, non-overlapping source ranges to contiguous program ranges for one source asset.

```json
{
  "schema_version": 1,
  "timeline_id": "main",
  "source_asset_id": "source",
  "fps": {"num": 30000, "den": 1001},
  "source_duration_s": 60.0,
  "program_duration_s": 20.0,
  "clips": [
    {
      "id": "clip-001",
      "source_range": {"start_s": 5.0, "end_s": 25.0},
      "program_range": {"start_s": 0.0, "end_s": 20.0},
      "speed": 1.0,
      "decision_ref": "edit-001"
    }
  ]
}
```

Ranges are half-open `[start_s, end_s)`. V1 supports only chronological clips, linear positive speed, and one-frame numerical tolerance. A source time inside a dropped range has no program-time mapping.

An editor-cleared sequence is represented by `"clips": []` and `"program_duration_s": 0`. It retains the source duration and rational FPS so the last deletion can be undone or new source ranges can be inserted. A zero-duration sequence is valid project state but is not a renderable delivery.

Validate with `python scripts/validate.py timeline work/timeline.json`.
