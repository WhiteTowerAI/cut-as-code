# Project Schema V1

`work/project.json` is the only shared manifest.

Required top-level fields:

- `schema_version`: `1`
- `project_id`: stable project identifier
- `source`: project-relative `path` and quick `fingerprint`
- `active_sequence`: key in `sequences`
- `sequences`: named ordered operation lists and timeline paths
- `operations`: unique operation objects
- `render`: render plan, output, and status
- `reviews`: review operation objects

Each operation has `id`, `skill`, positive integer `revision`, `depends_on`, `based_on`, one of `draft|approved|verified|failed|stale`, optional `plan`, `outputs`, and an optional render contribution. A `based_on` revision must equal the current dependency revision before preview or render.

Paths are relative to `work/` and must remain inside the project root. Validate with:

```powershell
python scripts/validate.py project work/project.json .
```
