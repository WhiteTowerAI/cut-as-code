# B-Roll Rules

## Editorial Selection

- Use the `dynamic-social` profile. Begin planned coverage with a complete A-roll scan, then
  hand-author chronological, non-overlapping transcript-backed intervals.
- Treat `0.40` to `0.70` planned coverage as a soft target. Below `0.40`, make a second pass that
  only adds or extends defensible intervals. Above `0.70`, conduct an internal A-roll concealment
  review. Never add irrelevant filler or weaken eligibility to hit the target.
- Prefer literal nouns, actions, products, locations, and processes. Reject generic mood
  footage, loose topical matches, and repeated or near-identical visuals.
- Preserve the first or last spoken beat when the speaker's face carries the meaning.
- Keep proposed ranges positive, half-open, chronological, non-overlapping, and supported by
  exact mapped transcript words.
- Require `brief.search_context` with a concrete `topic`, `visual_direction`, and `1-12 unique
  keywords`. Give every search shot a `semantic_role`: `direct`, `supportive`, or `atmospheric`.
- Write two or three layered narrow literal queries per shot: `direct subject/action`,
  `defensible context/process`, and, when useful, a `theme-enhancing variant`. Do not search full
  transcript sentences or abstract adjectives. Generic topical terms such as `tech` or
  `entertainment` may refine queries only; they never replace the per-shot visible relationship.
- Skip a moment when no candidate fits its meaning, quality, duration, framing, and license.

## Sources And Provenance

- Supported sources are validated local media and direct Pexels results acquired by
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

## Candidate Collection And Analysis

- Keep two or three narrow literal queries per shot. Preserve each query and its original Pexels
  order, merge results round-robin, deduplicate by positive `provider_id`, and analyze at most
  eight unique Pexels videos per shot.
- Keep separate Pexels `analysis_variant` and `delivery_variant` records. The analysis variant is
  the smallest orientation-matched file with a short edge of at least 480 pixels, or the largest
  valid matching file when none qualifies. The delivery variant is the highest-resolution
  orientation-matched file and is downloaded only for the ranked shortlist.
- Never promote analysis media to a delivery candidate. Bind both variants' provider/file IDs,
  dimensions, direct URLs, acquisition records, byte counts, probes, and SHA-256 values.
- Analyze an already imported local or externally generated candidate from its exact frozen cache
  file. Do not create a provider wrapper or a second acquisition system for it.
- Extract exactly five frames at 10, 30, 50, 70, and 90 percent. Preserve frame/crop paths,
  dimensions, SHA-256 values, luma/clipping/edge/motion metrics, center-crop simulations, and fixed
  perceptual hashes. Every number must be finite and JSON-safe.
- Hard-reject only invalid provenance or URL identity, path escape, unsafe or incomplete download,
  invalid video metadata, failed full decode, insufficient duration beyond one timeline-frame
  tolerance, failed five-frame sampling, or an exact provider/byte/frame duplicate.
- Treat low resolution, crop loss, unusual luma or clipping, low edge detail, unusual sampled-frame
  change, suspected compression/noise/shake/text/logo/watermark, and non-exact perceptual similarity
  as warnings. Uncalibrated metrics must not reject intentional night, static, shallow-focus, or
  high-motion footage.
- Classify duration as reject when `candidate_duration + one timeline frame < shot_duration`, warn
  when it covers the shot with less than one second of trim padding, and pass otherwise.
- Build project-wide exact identity groups from matching provider candidate identity, provider and
  delivery file identity, analysis or delivery SHA-256, or an equivalent frozen local path, byte
  count, and SHA-256. Keep every cross-shot instance analyzable so semantic scoring decides the
  strongest placement; do not reject by encounter order.
- Keep the five-frame perceptual-hash average threshold at `6`. Treat it as a strict near-identical
  signal, not a same-series classifier. Do not widen it to cover visually related shoots.
- Record same-provider, same-creator, nearby provider ID, shared source-title terms, or partial
  perceptual overlap as `possible_series` evidence only. A possible-series hint never changes
  eligibility or ranking by itself.

## Agent Scoring And Ranking

- Agent ranking requires actual delegated authority, `mode: "agent"`, the real actor name, a
  timezone-aware timestamp, a non-empty overall rationale, and a concrete rationale for every
  analyzable candidate. Ranking is advisory and is never human approval.
- Score `semantic_fit`, `context_fit`, `composition_fit`, and `style_fit` from visible frozen-frame
  evidence with integers from 0 through 4: 0 mismatch/unusable, 1 weak, 2 acceptable with concerns,
  3 strong, and 4 unusually strong. Record `text_logo_risk` from 0 through 4 or `uncertain`; never
  claim OCR from sampled frames.
- Both `semantic_fit == 0` and `context_fit == 0` are retained hard ineligibility protections.
  Mark a candidate ineligible when either applies, a hard check fails, it clearly violates
  `brief.avoid`, or its primary subject cannot be identified in the target framing.
  `semantic_fit == 0` rejects a semantic mismatch; `context_fit == 0` rejects unsupported context.
  A `semantic_fit` of 1 is an eligible `weak_semantic_match` when it passes the context and other
  independent gates; it ranks below semantic 2-4 matches.
- Confirm project-wide near-duplicate groups from provider identity, exact/perceptual evidence, and
  visible comparison across the frozen five-frame sets. Record the real Agent actor, timezone-aware
  timestamp, member shot and candidate IDs, match type, and a concrete reason the footage would
  repeat across the named transcript moments. Never confirm from creator identity alone.
- Rank eligible candidates in semantic-first lexicographic order: `semantic_fit`, then
  `context_fit`, then the combined `composition_fit + style_fit` score, fewer deterministic
  warnings, then stable `provider_id` and candidate ID. Preserve the base order before global
  allocation.
  Preserve every sub-score and rationale instead of an opaque total.
- Allocate every exact or Agent-confirmed duplicate component to its strongest semantic/context
  placement across all shots. Suppress the other members, refill from each shot's next independent
  eligible candidate, and preserve the keep, suppress, and refill reasons. Never use a duplicate
  fallback to reach three candidates.
- Return at most three candidates. Return fewer when fewer qualify. Record
  `no_eligible_candidates` when none qualify; never invent a weak third choice or fallback media.
- Hash-bind search order, analysis media, sampled frames, deterministic evidence, Agent scoring,
  ranking, shortlist, acquired delivery bytes, plan binding, and exact-candidate review.

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
- Use the readable mapped A-roll transcript as the primary timing context. Keep the A-roll frame
  as secondary visual context. Retain exact word timing, clip mapping, literal stock queries, and
  complete provenance in the immutable payload, but place those technical details behind collapsed
  disclosures. Present candidate provenance as a concise source, creator, dimensions, duration,
  license, source-link, and terms-link summary rather than raw JSON.
- Keep the current immutable page's insert start and end independently within their original
  values plus or minus two seconds, further limited by the timeline, adjacent shots, valid source
  mapping, and a minimum duration of one rational timeline frame. Move each visible control by
  0.5 seconds per action, display time values with at most two decimal places, and snap exported
  values to frame boundaries without replacing untouched canonical values with display rounding.
- Choose `ordinary` or `speaker-inset` once in Agent chat before publishing the first candidate
  page. Candidate, skip, program/source timing, segment boundary/order/speed, Fit to A-roll, and
  Ken Burns edits made with that page's controls do not request a revision.
- With `Modification notes` empty, explicit Approve exports the current exact configuration.
  Use `submission_intent: approve` for the ordinary route and `approve_selection` with
  `approval_scope: "b-roll-selection"` for the speaker-inset route. Python must revalidate the
  exact page, bindings, media, timeline, transcript, timing, segments, and source coverage before
  applying the configuration directly.
- Preserve non-empty natural-language `Modification notes` exactly and use them only for requested
  changes the page controls cannot express. They select Request changes and export
  `submission_intent: request_revision`; Empty Request changes is invalid. Reject it in
  `apply_review()` before any plan or receipt write, then use the existing validation,
  revision/rebuild, and new immutable page flow. The rebuilt proposal carries the first route
  binding forward; do not ask the user to choose ordinary or speaker-inset again. The
  `presentation-decision.json` receipt remains unchanged, and its candidate-manifest and
  review-video bindings remain mandatory. Never convert revision notes into human authority.
- Candidate selection and speaker composite approval remain separate. The first page approves B-roll
  content; it never approves the later exact speaker composite.
- Human mode requires an explicit user `Copy` or `Download JSON` action. Both controls must use one
  receipt builder, the same validation, and the same JSON bytes while the form is unchanged. Copy
  keeps a readonly textarea fallback when clipboard access fails. The controls record explicit
  approval but do not mutate the plan until the transferred receipt is validated and applied.
- Delegated Agent mode requires actual delegated
  authority, the real actor name, exact decisions, and a non-empty rationale. Never fabricate
  human approval.
- Select an explicit video trim or still motion for every selected shot; explicitly skip all
  others. Missing, rejected, or unrecoverable candidates stay skipped without random fallback.
- Keep full global keep, suppress, and refill audit in the candidate-analysis summary. On exact
  candidate cards, show only unresolved cross-shot similarity that directly helps selection, with
  the other shot ID and candidate ID. Do not show internal suppression notes on cards.
- Show the analysis summary and exact full-candidate page together, then stop. Do not apply review,
  normalize, compile, or render until the user explicitly copies, downloads, or approves exact
  selections.
- After successful validation and application, the candidate UUID page is consumed as immutable
  evidence. Keep it on disk but must not present it again, reopen its convenience alias, or ask for
  confirmation of the same B-roll decision. Reopen or republish only for an invalid or stale
  export, an explicit candidate `request_revision`, changed hash-bound inputs, or an explicit user
  request. Retrying Copy/Download is receipt transfer, not editorial reapproval.

## Speaker Inset Review

- After candidates are frozen and before publishing any review page, the current Agent must present
  a recommendation for `ordinary` or `speaker-inset` in chat and obtain an explicit user choice.
  Persist the actual user response, recommendation, rationale, plan, candidate-manifest, and
  review-video bindings in `work/b-roll/presentation-decision.json` with
  `rationale_source: "agent_chat_explicit_action"`. The plan binds that receipt by SHA-256. This
  chat decision selects a route only; it cannot impersonate a `review_ui_explicit_action` or replace
  either webpage approval. A candidate revision may change the unapproved proposal's timing and
  segment defaults while preserving the first route binding. Do not ask the user to choose ordinary
  or speaker-inset again. The `presentation-decision.json` receipt remains unchanged. A changed
  candidate manifest or review video still requires a new chat choice.
- An `ordinary` choice removes `speaker_inset_style` and uses the existing one-page workflow. A
  `speaker-inset` choice installs the default style. When enabled, require
  `shape: "rounded-rectangle"`, `width_ratio: 0.39`, `aspect_ratio: 0.80`, a 3px `#9E9E9E` border,
  `corner_radius_ratio: 0.10`, `margin_ratio: 0.04`, and `reserved_bottom_ratio: 0.20`. Keep only
  common appearance in this project-level style; preset and anchor belong to the Agent input.
- The first-page `approve_selection` action writes the approved `broll-selection.json`, binds the
  consumed candidate page by UUID and SHA-256, and moves selected shots to `composite_pending` only
  while new speaker presentation evidence is pending. The selected B-roll content is already
  authoritative and is not approved again on the composite page. An all-skipped selection is an
  approved no-op and does not create a composite page.
- Split every selected program range at canonical clip discontinuities and conservative FFmpeg
  scene candidates. Align boundaries and keyframes to rational timeline frames. Never interpolate
  a ROI across a cut or infer identity across cuts.
- Build temporal A-roll evidence from the hash-bound upstream review video. Include entry, middle,
  exit, adjacent frames, transcript context, frame path, dimensions, program time, and SHA-256.
  A single still is insufficient evidence for a current speaker in a multi-person shot.
- When the baseline bursts cannot isolate one current speaker, request one or more frame-aligned
  supplemental points inside that subshot. Extract a denser adjacent-frame burst, rebuild the
  analysis ID/hash, and inspect it before using `ambiguous`. Never carry an old Agent input across
  the rebuilt analysis.
- Use the delegated Agent only for visual speaker judgment, sparse normalized ROI annotation, and
  composition review. Do not install or invoke a face detector, person segmentation/tracking model,
  or external identity service.
- In `speaker-inset-agent-input.json`, require one `project_layout_strategy` with a primary preset,
  one or two used presets by default, and a specific rationale. Require one
  `layout_recommendation` per selected shot with preset, fixed anchor, high/medium/low confidence,
  rationale, and pass/warn/fail assessments for all three presets. A low-confidence recommendation
  requires one non-failing alternate; recommendation never grants approval.
- Use `focused-panel` when the exact B-roll benefits from a distinct upper presentation area. Build
  the frame from a blurred full-frame copy plus a crisp cover-scaled panel at normalized bounds
  `x=0.04`, `y=0.08`, `width=0.92`, `height=0.40`, surrounded by a 3px `#9E9E9E` border; place the
  speaker at `lower-center` directly above the subtitle-safe area.
- Use `full-bleed-wash` for atmospheric or supporting B-roll that tolerates lower contrast. Keep it
  full-frame, apply one uniform white layer at opacity `0.30`, and place the speaker at
  `upper-center`. Do not use this preset for text, charts, interfaces, or required fine detail.
- Use `corner-pip` for information-dense B-roll that must remain full-frame and full-contrast. Keep
  B-roll unchanged and choose exactly one shot-level `top-left` or `top-right` anchor. Only upper
  corners are supported so the subtitle-safe lower area remains clear.
- Default every shot to the project primary preset. Use a secondary preset only when the primary is
  warn/fail for that exact shot and the secondary passes with a visible benefit. Three presets need
  three distinct documented shot needs and approval of the exact previews. Keep one preset and one
  anchor for the complete shot; never switch corners inside a shot.
- Require `confirmed`, `ambiguous`, `absent`, or `occluded` for every subshot and a specific
  evidence-based rationale. A distant, full-body, side, back, or briefly turning speaker is not
  automatically `occluded`. Use continuous frames, stage or lectern position, clothing outline,
  motion continuity, and transcript timing to confirm identity. Use `occluded` only when the
  person disappears or is fully blocked, `ambiguous` when identity remains uncertain after dense
  supplemental evidence, and `absent` when no speaker is present. Never guess identity to increase
  inset coverage.
- Only confirmed tracks may enable the Agent-input window. Every other status must use
  `pure_broll`, no anchor, and no keyframes. A confirmed Agent-input track must remain `enabled`
  until exact previews exist; final-size quality fallback belongs to clearance, not identity
  classification.
- For every confirmed subshot, first create stable ROI keyframes that cover its full frame-aligned
  range. The hard constraint at every keyframe and after cover crop, border, and rounded mask is a
  complete head outline: top of head, visible forehead, chin or lower edge, and reasonable
  headroom. Preserve a necessary gesture, upper body, lectern, or stage relationship only after
  satisfying that constraint. If a tight crop cannot do both, expand to a stable speaking-region
  ROI. Never crop the head to gain apparent sharpness or a larger subject.
- Keep ROI values finite, positive, inside the A-roll frame, strictly ordered, frame aligned, and
  covering the complete subshot. Interpolate only within that subshot and never across a scene or
  timeline cut.
- Fit each speaker ROI into the configured window with an aspect-preserving cover crop, centered
  horizontally and anchored to the top. Never resize speaker pixels non-uniformly. Preserve the
  complete head, forehead, face, chin, and visible headroom before lower-body coverage. If that
  framing still removes important subject content, revise and reapprove the ROI instead of
  stretching it.
- Render the user's exact B-roll bytes, trims, segment order, speeds, timeline geometry, rational
  FPS, and selected LUT. Read speaker pixels from the already graded upstream review video; never
  apply the LUT to those pixels again.
- Apply the recommended B-roll treatment to every frame, including a `pure_broll` subshot; only the
  speaker pixels toggle. Freeze the exact recommended composite, every supported anchor preview for
  that preset, and the single required low-confidence alternate. Agent clearance must inspect these
  composited pixels, not isolated A-roll and B-roll sources.
- For every confirmed subshot, call `build_pixel_budget()` against the current analysis, Agent
  input, and exact preview. Preserve source crop pixels, output inset pixels, each scale factor,
  maximum scale, and the selection, analysis, Agent-input, preview, style, and review-video hashes.
  Label the maximum scale `low` at `<=1.5x`, `medium` above `1.5x` through `3.0x`, and `high` above
  `3.0x`. This label is a warning that increases scrutiny; it never changes `display_mode`.
- Inspect final-size pixels at the canonical entry, middle, and exit frames. Also choose the
  frame-aligned in-subshot point where subject motion, turning, gesture, or camera motion presents
  the greatest extra risk, with a non-empty selection reason and observation. If no extra point
  exists, record `motion_risk: not_applicable` with a reason. Bind every legibility check directly
  to the current exact preview SHA-256. Do not substitute original A-roll stills.
- Record `subject_legibility: pass` only when a normal viewer can immediately recognize an active
  speaker at final size: the complete head survives border and mask, the silhouette separates from
  the background, at least one of gesture/lectern/stage relationship is readable, tracking remains
  stable, and scaling does not cause sustained severe blocking, smear, or silhouette fusion. Facial
  detail is not required and distance alone is not failure.
- Use the clearance matrix strictly: confirmed + enabled + pass requires `clearance_status: pass`;
  confirmed + pure B-roll + `not_applicable` requires `no_safe_position` and every allowed anchor;
  confirmed + pure B-roll + fail requires `subject_illegible`, no final anchor, a specific
  legibility rationale, retained ROI/keyframes, pixel budget, and preview-bound checks. A
  non-confirmed speaker remains pure B-roll with `not_applicable` and clearance `pass`. Reject
  enabled+fail and any fail disguised as `pass` or `no_safe_position`.
- Treat one or two blurred turning/motion frames as observations, not automatic failure. When only
  a sustained later portion is unreadable, split at a legal frame boundary and fall back only for
  that subshot. Use `subject_illegible` only when the complete subshot remains unreadable after the
  stable-region ROI attempt.
- When the user asks for a larger or smaller speaker, translate the request into one explicit
  numeric `width_ratio`, state it, and invalidate every style-bound artifact and approval before
  rebuilding. Do not silently change one shot.
- Record one continuity assessment per shot. Derive `short_flash` when an enabled run is shorter
  than 1.5 seconds and is followed by a longer pure-B-roll run. Resolve it by independently
  confirming and extending the later subshot, disabling the whole shot inset, or explicitly
  justifying an intentional transition. Do not use a fade or a guessed identity to mask it.
- `pass` binds the recommended enabled anchor actually checked. `no_safe_position` must list every
  anchor and resolve the subshot to `pure_broll`; `subject_illegible` must bind the checked
  recommended final-size preview. Never shrink the project style, cover focal B-roll content,
  replace the selected B-roll, crop a complete head, or invent a fallback speaker image.
- The second immutable page must show temporal evidence, ROI keyframes, project strategy,
  recommendation rationale, three assessments, exact recommended composite, supported anchor
  previews, optional alternate, common style, merged speaker/final display status, pixel budget and
  risk, all four legibility checks, and clearance reasoning. Keep the locked B-roll as read-only,
  default-collapsed context. Do not expose candidate selection, skip, timing, segment, or speed
  controls, and do not emit candidate `shots` in the composite receipt. Approval requires
  `approval_scope: "speaker-inset-composite"`, `review_stage: composite`, and current selection,
  analysis, Agent input, preview, clearance, and style hashes. It approves only ROI, layout,
  clearance, continuity, style, and exact composite pixels.
- A candidate revision creates a new candidate UUID page and approved selection receipt before
  speaker artifacts are rebuilt while preserving the first ordinary or speaker-inset route. A
  composite-only revision creates a new composite UUID page while
  preserving `selection_sha256`; it cannot change candidate IDs, order, timing, source ranges, or
  speed. Rebuild preview, clearance, and the composite page; rebuild analysis or Agent input only
  when requested evidence or ROI judgment actually changes. If the request changes a candidate,
  timing, segment order, or speed, return to the candidate-revision flow. Derive the durable
  candidate decision manifest from the approved selection after composite approval.
- After composite approval, normalize a reusable pure B-roll base and precompose the preset
  treatment plus clearance-effective speaker pixels into the one existing per-shot overlay. Bind
  selection, analysis, Agent input, preview, clearance, style, review video, and composite review
  UUID by SHA-256. Verification stills, contact sheet, and boundary reel must read this final
  composite, never the base.
- Pre-register the verified final composite as the existing approved/pending overlay, render final
  delivery once, then inspect the actual normalized and final pixels. In addition to the ordinary
  checks, keep the final visual review mandatory and require `speaker_layout_fidelity`,
  `speaker_legibility`, and `broll_focal_clearance` before final registration becomes verified.

## Segment Timing And Playback

- Store every new selected video as one to three ordered canonical `segments`. Each segment names a
  unique candidate from the shot's hash-bound Top 3 and includes complete `source_range`,
  `program_range`, and `playback_rate` fields. Accept only `0.5`, `1.0`, `1.5`, or `2.0`.
- Allocate program time in integer timeline frames. One segment occupies the complete shot. Split two
  or three new segments evenly and give any remainder frames to the last segment. Keep every segment
  at least one frame, continuous, non-overlapping, and collectively equal to the shot program range.
- Keep allocation with its segment when reordering. Recompute its program start/end from the new
  order without changing its duration, source range, or speed. Moving a boundary adds frames to one
  neighbor and removes the same number from the other.
- Keep user adjustment size separate from canonical precision. Clip start uses a `0.1s` input step.
  A normal Boundary click moves `max(1, round(0.1 / frame_duration))` timeline frames; `Alt` on
  Windows/Linux or `Option` on macOS moves one frame. Every resulting program allocation remains
  integer-frame aligned, continuous, non-overlapping, and collectively equal to the shot range.
- Treat A-roll program allocation as controlling. Compute required source duration as
  `program_duration * playback_rate` and source end as `source_start + required_source_duration`.
  In the new review page, make source end read-only and recalculate it after source-start, rate,
  allocation, reorder, or fit changes.
- Validate source coverage immediately in the page. When a trim is illegal, highlight only related
  timing controls and show actionable English guidance with the required and available source,
  shortage, latest legal start, feasible playback rates, and Boundary/candidate alternatives.
  Use stable reason codes and numeric facts for page logic; keep both those diagnostics and their
  display text out of the review receipt and B-roll plan. Never hide a repair in Copy,
  `apply_review()`, or normalization.
- Make `Fit to A-roll` explicit. First satisfy a segment from its remaining source duration, then
  redistribute unavailable frames from the end toward earlier segments that have capacity. Preserve
  playback rates, segment identity, and segment count. Show the proposed ranges before export and
  disable Copy/Download when no legal fit exists.
- Require `source_duration = source_end - source_start`,
  `effective_duration = source_duration / playback_rate`, and
  `program_duration = program_end - program_start` to differ by no more than one frame derived from
  `timeline.fps.den / timeline.fps.num` for every segment.
- Render every canonical one-to-three-segment video selection directly from its frozen original
  candidates in one FFmpeg filtergraph and one encoder call. Apply each segment's reviewed source
  trim, playback rate, scale/crop, SAR, rational FPS, exact program-frame allocation, and optional
  LUT in its own chain, then hard-concat two or three chains in program order; map a single chain
  directly. Bind each candidate ID, source path and SHA-256, source/program range, playback rate,
  optional grade hashes, final asset hash, and probe. Never create, read, or recover per-segment
  normalized MP4 files or sidecars. Do not add transitions, loop, repeat, silently truncate,
  auto-change speed, delete a segment, or select fallback media.
- Encode every new ordinary overlay, speaker B-roll base, and delivery speaker composite with the
  exact versioned profile: MP4, libx264/H.264, CRF 18, preset medium, yuv420p, `+faststart`, and no
  audio. Command tests and the durable profile prove CRF and preset; FFprobe proves only the
  observable container, codec, pixel format, streams, geometry, FPS, and duration. Keep candidate,
  context, and anchor previews, boundary reels, and the shared final renderer on their existing
  encoding paths.
- Write each current-shot asset to a same-directory `.part.mp4`; publish it with `os.replace` only
  after probe, full decode, geometry, FPS, duration, silence, and SHA-256 checks. Write the canonical
  plan through its own `.part.json` and do not describe the two files as one transaction. On any
  failure, keep the current shot `selected`, remove this attempt's parts and newly generated assets
  not referenced by the canonical plan, and preserve every previously completed shot, record,
  asset byte, and hash. Retry the entire current shot from the original candidates.
- Validate existing component-based records against their recorded component facts as legacy
  read-only evidence. Do not add the new profile to them or report them as source-direct.
- Read legacy `selected.candidate_id + source_trim` without rewriting the file. Record both a long
  legacy requested trim and its effective source range so old normalized output remains recoverable;
  reject a legacy trim that cannot cover the program duration. Never emit an ambiguous legacy trim
  from a new review page.

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
