import type { ClipView, EditorProjectView, EditorSelection, TrackView } from './editor-model'

export type TimelineTrimEdge = 'start' | 'end'

export type TimelineRipple = Readonly<{
  boundaryS: number
  deltaS: number
}>

export type TimelineEditCommand =
  | Readonly<{ type: 'split'; clipId: string; atS: number }>
  | Readonly<{ type: 'delete'; clipId: string }>
  | Readonly<{ type: 'trim'; clipId: string; edge: TimelineTrimEdge; sourceS: number }>
  | Readonly<{ type: 'restore-bounds'; clipId: string }>
  | Readonly<{ type: 'set-range'; clipId: string; startS: number; endS: number }>
  | Readonly<{ type: 'join'; leftClipId: string; rightClipId: string }>
  | Readonly<{ type: 'insert'; index: number; clip: ClipView }>

export type TimelineEditResult = Readonly<{
  project: EditorProjectView
  inverse: TimelineEditCommand
  selection: EditorSelection
}>

const TIME_PRECISION = 9
const RANGE_EPSILON = 1e-7

function rounded(value: number) {
  return Number(value.toFixed(TIME_PRECISION))
}

function frameDurationS(project: EditorProjectView) {
  const { numerator, denominator } = project.fps
  return numerator > 0 && denominator > 0 ? denominator / numerator : 1 / 30
}

function snapProgramTime(project: EditorProjectView, timeS: number) {
  const frame = frameDurationS(project)
  return rounded(Math.round(timeS / frame) * frame)
}

function videoTrack(project: EditorProjectView) {
  return project.tracks.find((track) => track.kind === 'video')
}

function videoClips(project: EditorProjectView) {
  return [...(videoTrack(project)?.clips ?? [])]
}

function reflow(clips: readonly ClipView[]) {
  let programStartS = 0
  return clips.map((clip) => {
    const speed = clip.speed && clip.speed > 0 ? clip.speed : 1
    const durationS = (clip.sourceRange.endS - clip.sourceRange.startS) / speed
    const programEndS = rounded(programStartS + durationS)
    const updated = {
      ...clip,
      speed,
      programRange: { startS: rounded(programStartS), endS: programEndS },
    }
    programStartS = programEndS
    return updated
  })
}

function clipDurationS(clip: ClipView) {
  const speed = clip.speed && clip.speed > 0 ? clip.speed : 1
  return (clip.sourceRange.endS - clip.sourceRange.startS) / speed
}

function rippleOrNull(boundaryS: number, deltaS: number): TimelineRipple | null {
  return Number.isFinite(boundaryS) && Number.isFinite(deltaS) && Math.abs(deltaS) > RANGE_EPSILON
    ? { boundaryS: rounded(boundaryS), deltaS: rounded(deltaS) }
    : null
}

/** Return the program-time shift applied to elements at or after the edit point. */
export function timelineRippleForCommand(project: EditorProjectView, command: TimelineEditCommand) {
  const clips = videoClips(project)
  if (command.type === 'delete') {
    const clip = clips.find((candidate) => candidate.id === command.clipId)
    return clip ? rippleOrNull(clip.programRange.endS, -clipDurationS(clip)) : null
  }
  if (command.type === 'insert') {
    const index = Math.min(Math.max(command.index, 0), clips.length)
    const boundaryS = clips[index]?.programRange.startS ?? project.durationS
    return rippleOrNull(boundaryS, clipDurationS(command.clip))
  }
  if (command.type === 'restore-bounds') {
    const clip = clips.find((candidate) => candidate.id === command.clipId)
    const bounds = clip ? trimSourceBounds(project, clip.id, 'start') : null
    const endBounds = clip ? trimSourceBounds(project, clip.id, 'end') : null
    return clip && bounds && endBounds
      ? rippleForSourceRange(clip, bounds.minimum, endBounds.maximum)
      : null
  }
  if (command.type === 'set-range') {
    const clip = clips.find((candidate) => candidate.id === command.clipId)
    return clip ? rippleForSourceRange(clip, command.startS, command.endS) : null
  }
  if (command.type !== 'trim') return null

  const clip = clips.find((candidate) => candidate.id === command.clipId)
  if (!clip) return null
  const oldDurationS = clipDurationS(clip)
  const sourceRange = command.edge === 'start'
    ? { ...clip.sourceRange, startS: command.sourceS }
    : { ...clip.sourceRange, endS: command.sourceS }
  const speed = clip.speed && clip.speed > 0 ? clip.speed : 1
  const newDurationS = (sourceRange.endS - sourceRange.startS) / speed
  const deltaS = newDurationS - oldDurationS
  const boundaryS = command.edge === 'start'
    ? clip.programRange.startS + Math.max(0, -deltaS)
    : clip.programRange.endS
  return rippleOrNull(boundaryS, deltaS)
}

function rippleForSourceRange(clip: ClipView, startS: number, endS: number) {
  const oldDurationS = clipDurationS(clip)
  const speed = clip.speed && clip.speed > 0 ? clip.speed : 1
  const deltaS = (endS - startS) / speed - oldDurationS
  const startChanged = Math.abs(startS - clip.sourceRange.startS) > RANGE_EPSILON
  const boundaryS = startChanged
    ? clip.programRange.startS + Math.max(0, -deltaS)
    : clip.programRange.endS
  return rippleOrNull(boundaryS, deltaS)
}

function shiftedRange(range: Readonly<{ startS: number; endS: number }>, ripple: TimelineRipple | null) {
  if (!ripple || range.startS < ripple.boundaryS - RANGE_EPSILON) return range
  return {
    startS: rounded(range.startS + ripple.deltaS),
    endS: rounded(range.endS + ripple.deltaS),
  }
}

function shiftedClip(clip: ClipView, ripple: TimelineRipple | null) {
  const programRange = shiftedRange(clip.programRange, ripple)
  return programRange === clip.programRange ? clip : { ...clip, programRange }
}

function shiftProgramTiming(value: unknown, ripple: TimelineRipple | null): unknown {
  if (!ripple || value === null || typeof value !== 'object') return value
  if (Array.isArray(value)) return value.map((entry) => shiftProgramTiming(entry, ripple))

  const next = { ...(value as Record<string, unknown>) }
  const programRange = next.program_range
  if (programRange && typeof programRange === 'object' && !Array.isArray(programRange)) {
    const range = programRange as Record<string, unknown>
    if (typeof range.start_s === 'number' && typeof range.end_s === 'number'
      && range.start_s >= ripple.boundaryS - RANGE_EPSILON) {
      next.program_range = {
        ...range,
        start_s: rounded(range.start_s + ripple.deltaS),
        end_s: rounded(range.end_s + ripple.deltaS),
      }
    }
  } else if (typeof next.program_start_s === 'number' && typeof next.duration_s === 'number'
    && next.program_start_s >= ripple.boundaryS - RANGE_EPSILON) {
    next.program_start_s = rounded(next.program_start_s + ripple.deltaS)
  }
  return Object.fromEntries(Object.entries(next).map(([key, entry]) => [
    key,
    key === 'program_range' || key === 'program_start_s' ? entry : shiftProgramTiming(entry, ripple),
  ]))
}

function nextSplitId(clips: readonly ClipView[], clipId: string, atS: number, project: EditorProjectView) {
  const frame = Math.round(atS / frameDurationS(project))
  const base = `${clipId}:split-${frame}`
  let id = base
  let suffix = 2
  const ids = new Set(clips.map((clip) => clip.id))
  while (ids.has(id)) id = `${base}-${suffix++}`
  return id
}

function updateTracks(project: EditorProjectView, clips: readonly ClipView[], ripple: TimelineRipple | null) {
  const previousVideoIds = new Set(videoClips(project).map((clip) => clip.id))
  const tracks = project.tracks.map((track): TrackView => {
    if (track.kind === 'video') return { ...track, clips }
    if (track.kind !== 'audio' || !(track.clips?.length)) return track

    const isLinkedAudio = track.clips.length === 1 || track.clips.every((clip) => {
      const videoId = clip.id.endsWith(':audio') ? clip.id.slice(0, -6) : ''
      return previousVideoIds.has(videoId)
    })
    if (!isLinkedAudio) return {
      ...track,
      clips: track.clips?.map((clip) => shiftedClip(clip, ripple)),
    }
    return {
      ...track,
      clips: clips.map((clip) => ({
        ...clip,
        id: `${clip.id}:audio`,
        trackId: track.id,
        displayName: track.clips?.[0]?.displayName ?? clip.displayName,
      })),
    }
  })
  const durationS = clips.at(-1)?.programRange.endS ?? 0
  return {
    ...project,
    durationS,
    tracks: tracks.map((track) => track.kind === 'video' || track.kind === 'audio'
      ? track
      : { ...track, clips: track.clips?.map((clip) => shiftedClip(clip, ripple)) }),
    layers: project.layers?.map((layer) => ({ ...layer, programRange: shiftedRange(layer.programRange, ripple) })),
    operations: project.operations?.map((operation) => ({
      ...operation,
      fields: shiftProgramTiming(operation.fields, ripple) as Readonly<Record<string, unknown>>,
    })),
  }
}

export function trimSourceBounds(project: EditorProjectView, clipId: string, edge: TimelineTrimEdge) {
  const clips = videoClips(project)
  const index = clips.findIndex((clip) => clip.id === clipId)
  if (index < 0) return null
  const clip = clips[index]
  const minimumSourceDurationS = frameDurationS(project) * (clip.speed && clip.speed > 0 ? clip.speed : 1)
  if (edge === 'start') {
    return {
      minimum: clips[index - 1]?.sourceRange.endS ?? 0,
      maximum: clip.sourceRange.endS - minimumSourceDurationS,
    }
  }
  return {
    minimum: clip.sourceRange.startS + minimumSourceDurationS,
    maximum: clips[index + 1]?.sourceRange.startS ?? project.sourceDurationS ?? clip.sourceRange.endS,
  }
}

export function trimSourceAtProgramDelta(
  project: EditorProjectView,
  clipId: string,
  edge: TimelineTrimEdge,
  deltaProgramS: number,
) {
  const clip = videoClips(project).find((candidate) => candidate.id === clipId)
  const bounds = trimSourceBounds(project, clipId, edge)
  if (!clip || !bounds) return null
  const speed = clip.speed && clip.speed > 0 ? clip.speed : 1
  const initial = edge === 'start' ? clip.sourceRange.startS : clip.sourceRange.endS
  const frameSourceDurationS = frameDurationS(project) * speed
  const unsnapped = initial + deltaProgramS * speed
  const snapped = Math.round(unsnapped / frameSourceDurationS) * frameSourceDurationS
  return rounded(Math.min(Math.max(snapped, bounds.minimum), bounds.maximum))
}

export function canSplitClip(project: EditorProjectView, clipId: string, atS: number) {
  const clip = videoClips(project).find((candidate) => candidate.id === clipId)
  if (!clip) return false
  const frame = frameDurationS(project)
  const snappedAtS = snapProgramTime(project, atS)
  return snappedAtS >= clip.programRange.startS + frame && snappedAtS <= clip.programRange.endS - frame
}

export function applyTimelineEdit(project: EditorProjectView, command: TimelineEditCommand): TimelineEditResult {
  const clips = videoClips(project)
  const ripple = timelineRippleForCommand(project, command)
  if (!clips.length && command.type !== 'insert') throw new Error('The video track has no editable clips')

  if (command.type === 'split') {
    const index = clips.findIndex((clip) => clip.id === command.clipId)
    if (index < 0 || !canSplitClip(project, command.clipId, command.atS)) {
      throw new Error('Move the playhead inside the selected clip before splitting')
    }
    const clip = clips[index]
    const splitAtS = snapProgramTime(project, command.atS)
    const speed = clip.speed && clip.speed > 0 ? clip.speed : 1
    const sourceSplitS = rounded(clip.sourceRange.startS + (splitAtS - clip.programRange.startS) * speed)
    const rightId = nextSplitId(clips, clip.id, splitAtS, project)
    const left = { ...clip, sourceRange: { ...clip.sourceRange, endS: sourceSplitS } }
    const right = {
      ...clip,
      id: rightId,
      sourceRange: { ...clip.sourceRange, startS: sourceSplitS },
    }
    const next = reflow([...clips.slice(0, index), left, right, ...clips.slice(index + 1)])
    return {
      project: updateTracks(project, next, ripple),
      inverse: { type: 'join', leftClipId: left.id, rightClipId: right.id },
      selection: { kind: 'video', id: right.id },
    }
  }

  if (command.type === 'delete') {
    const index = clips.findIndex((clip) => clip.id === command.clipId)
    if (index < 0) throw new Error('The selected clip no longer exists')
    const removed = clips[index]
    const next = reflow([...clips.slice(0, index), ...clips.slice(index + 1)])
    const selected = next[Math.min(index, next.length - 1)]
    return {
      project: updateTracks(project, next, ripple),
      inverse: { type: 'insert', index, clip: removed },
      selection: selected ? { kind: 'video', id: selected.id } : null,
    }
  }

  if (command.type === 'trim') {
    const index = clips.findIndex((clip) => clip.id === command.clipId)
    if (index < 0) throw new Error('The selected clip no longer exists')
    const clip = clips[index]
    const bounds = trimSourceBounds(project, clip.id, command.edge)
    if (!bounds || command.sourceS < bounds.minimum - 1e-7 || command.sourceS > bounds.maximum + 1e-7) {
      throw new Error('The trim would overlap another source range')
    }
    const oldSourceS = command.edge === 'start' ? clip.sourceRange.startS : clip.sourceRange.endS
    const sourceRange = command.edge === 'start'
      ? { ...clip.sourceRange, startS: rounded(command.sourceS) }
      : { ...clip.sourceRange, endS: rounded(command.sourceS) }
    const next = reflow(clips.map((candidate, clipIndex) => clipIndex === index ? { ...candidate, sourceRange } : candidate))
    return {
      project: updateTracks(project, next, ripple),
      inverse: { type: 'trim', clipId: clip.id, edge: command.edge, sourceS: oldSourceS },
      selection: { kind: 'video', id: clip.id },
    }
  }

  if (command.type === 'restore-bounds' || command.type === 'set-range') {
    const index = clips.findIndex((clip) => clip.id === command.clipId)
    if (index < 0) throw new Error('The selected clip no longer exists')
    const clip = clips[index]
    const bounds = trimSourceBounds(project, clip.id, 'start')
    const endBounds = trimSourceBounds(project, clip.id, 'end')
    const sourceRange = command.type === 'restore-bounds'
      ? { startS: bounds!.minimum, endS: endBounds!.maximum }
      : { startS: command.startS, endS: command.endS }
    const minimumDurationS = frameDurationS(project) * (clip.speed && clip.speed > 0 ? clip.speed : 1)
    if (!bounds || !endBounds
      || sourceRange.startS < bounds.minimum - RANGE_EPSILON
      || sourceRange.endS > endBounds.maximum + RANGE_EPSILON
      || sourceRange.endS - sourceRange.startS < minimumDurationS - RANGE_EPSILON) {
      throw new Error('The range would overlap another source range')
    }
    const next = reflow(clips.map((candidate, clipIndex) => clipIndex === index
      ? { ...candidate, sourceRange: { startS: rounded(sourceRange.startS), endS: rounded(sourceRange.endS) } }
      : candidate))
    return {
      project: updateTracks(project, next, timelineRippleForCommand(project, command)),
      inverse: { type: 'set-range', clipId: clip.id, startS: clip.sourceRange.startS, endS: clip.sourceRange.endS },
      selection: { kind: 'video', id: clip.id },
    }
  }

  if (command.type === 'join') {
    const index = clips.findIndex((clip) => clip.id === command.leftClipId)
    const left = clips[index]
    const right = clips[index + 1]
    if (!left || right?.id !== command.rightClipId || Math.abs(left.sourceRange.endS - right.sourceRange.startS) > 1e-7) {
      throw new Error('Only adjacent split clips can be joined')
    }
    const joined = { ...left, sourceRange: { ...left.sourceRange, endS: right.sourceRange.endS } }
    const next = reflow([...clips.slice(0, index), joined, ...clips.slice(index + 2)])
    return {
      project: updateTracks(project, next, ripple),
      inverse: { type: 'split', clipId: left.id, atS: right.programRange.startS },
      selection: { kind: 'video', id: left.id },
    }
  }

  const index = Math.min(Math.max(command.index, 0), clips.length)
  if (clips.some((clip) => clip.id === command.clip.id)) throw new Error('The clip already exists')
  const next = reflow([...clips.slice(0, index), command.clip, ...clips.slice(index)])
  return {
    project: updateTracks(project, next, ripple),
    inverse: { type: 'delete', clipId: command.clip.id },
    selection: { kind: 'video', id: command.clip.id },
  }
}
