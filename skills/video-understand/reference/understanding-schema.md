# Understanding Schema V1

`work/understand/understanding.json` is human-reviewed semantic evidence, not an edit plan.

Required fields:

- `schema_version`: `1`
- `timeline_id`: normally `source`
- `overview`: factual `title`, `content_type`, `summary`, and `primary_language`
- `chapters`: source-time chapters
- `entities`: people, organizations, products, places, and corrected names
- `moments`: `hook|key-point|quote|stat|list|question|cta|repetition|tangent|risk`
- `transcript_corrections`: explicit ASR corrections
- `uncertainties`: unresolved claims or names

Every semantic item has a unique stable `id`, `confidence` from 0 to 1, and `evidence_refs` such as `segment:12`. Timed items use `start_s` and `end_s` in source time. Every range must fit the transcript duration and every evidence reference must resolve.

Do not include `keep`/`drop`, card components, render instructions, or color looks.
