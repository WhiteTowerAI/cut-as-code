# B-Roll Rules

## Editorial Selection

- Default to selective use. Add B-roll only when it clarifies a claim, supplies concrete
  evidence, or hides a necessary edit without obscuring an important expression.
- Prefer literal nouns, actions, products, locations, and processes. Reject generic mood
  footage, loose topical matches, and repeated or near-identical visuals.
- Preserve the first or last spoken beat when the speaker's face carries the meaning.
- Keep proposed ranges positive, half-open, chronological, non-overlapping, and supported by
  exact mapped transcript words.
- Write two or three narrow literal queries per shot. Include the subject, action, setting,
  or useful framing. Do not search full transcript sentences or abstract adjectives.
- There is no minimum coverage. Skip a moment when no candidate fits its meaning, quality,
  duration, framing, and license.

## Sources And Provenance

- V1 sources are validated local media and direct Pexels results acquired by
  `scripts/pexels.py`. Do not introduce a provider interface, factory, broker, another stock
  source, or raw download command.
- Every candidate needs a stable ID, media type, project-cache path, positive byte count,
  SHA-256, successful media probe, and timezone-aware retrieval time.
- Local provenance requires creator, license or rights statement, retrieval time, and
  original path.
- Pexels provenance requires provider/file IDs, creator, Pexels page and media URLs,
  dimensions, duration, license and terms URLs, and retrieval time. Keep API keys out of all
  artifacts.
- Externally generated media is local import only. Record generation provider/model, prompt
  or job ID, creator, usage rights, retrieval time, and original path. Never imply the skill
  generated it or call a paid generation API.

## Stills

- A still is never a fallback for a failed video candidate.
- Use one only when the reviewed candidate is intentionally an image and the decision names
  `ken_burns.direction` as `zoom-in`, `pan-left`, or `pan-right`.
- Reject a still whose crop or motion weakens the evidence, hides essential content, or
  creates visible text/logo problems.

## Review

- Review the exact frozen candidate bytes against the exact source/program moment.
- Check semantic truth, start/end boundaries, framing, visual quality, repeated imagery,
  unwanted logos or text, and compatibility with the selected grade.
- Human mode requires an explicit user export. Delegated Agent mode requires actual delegated
  authority, the real actor name, exact decisions, and a non-empty rationale. Never fabricate
  human approval.
- Select an explicit video trim or still motion for every selected shot; explicitly skip all
  others. Missing, rejected, or unrecoverable candidates stay skipped without random fallback.

## Interrupted Work

- After a transient HTTP or network failure, rerun the exact Pexels download command with the
  same candidate and destination. The downloader owns Range, redirect/host, size, media, and
  hash validation, cleanup, and atomic publication.
- Never manually promote, rename, or delete a `.part` download. If the downloader declares
  validation or recovery failure, record it honestly and skip the candidate. Never publish
  partial bytes or substitute a generic clip.
- Rerun the normalizer or verifier after interruption. Their durable lifecycle records and
  transactions determine what is reusable; do not manufacture `normalized` or `verified`
  states.

## Delivery Gate

- With active color grade, pre-apply the exact selected LUT during normalization and bind its
  grade-plan and LUT hashes.
- Verification must cover decoding, hashes, rational FPS, dimensions, duration, silent media,
  first/middle/last stills, boundary transitions, and receipt bindings.
- Inspect the generated stills, contact sheet, boundary reel, final delivery, and
  original-versus-final source-time comparison. A machine pass without visual inspection is
  incomplete.
