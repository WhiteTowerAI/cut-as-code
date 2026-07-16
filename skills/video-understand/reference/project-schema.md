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

Each operation has `id`, `skill`, positive integer `revision`, `depends_on`, `based_on`, one
of `draft|approved|verified|failed|stale`, optional `plan`, `outputs`, `target`, `effects`, and
an optional `render` contribution. `target` contains a sequence and non-empty scope. `effects`
contains boolean `changes_timeline`, `changes_geometry`, `changes_video_pixels`, and
`changes_audio` flags plus nullable `adds_track`.

An optional operation `check` has `status: pending|pass|fail` and a user-facing Markdown
`report`. Do not put operation lifecycle values such as `verified` in `check.status`. A
`based_on` revision must equal the current dependency revision before preview or render.

Paths are relative to `work/` and must remain inside the project root. Validate with:

```powershell
python scripts/validate.py project work/project.json .
```
