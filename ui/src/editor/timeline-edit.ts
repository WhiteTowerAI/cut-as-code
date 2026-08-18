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
  | Readonly<{ type: 'insert-with-audio'; index: number; clip: ClipView; audioClip: ClipView }>
  | Readonly<{ type: 'detach-audio'; clipId: string }>
  | Readonly<{ type: 'attach-audio'; clipId: string }>
  | Readonly<{ type: 'unlink-audio'; audioClipId: string }>
  | Readonly<{ type: 'link-audio'; audioClipId: string }>
  | Readonly<{ type: 'mute-audio'; audioClipId: string; muted: boolean }>
  | Readonly<{ type: 'mute-video-audio'; clipId: string; muted: boolean }>
  | Readonly<{ type: 'trim-audio'; audioClipId: string; edge: TimelineTrimEdge; sourceS: number }>
  | Readonly<{ type: 'move-audio'; audioClipId: string; startS: number }>
  | Readonly<{ type: 'delete-audio'; audioClipId: string }>
  | Readonly<{ type: 'insert-audio'; index: number; clip: ClipView }>
  | Readonly<{ type: 'set-audio-state'; clipId: string; audioMode: 'embedded' | 'detached' | 'muted'; audioClip?: ClipView }>
  | Readonly<{ type: 'set-audio-clip'; clip: ClipView }>

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

function audioTrack(project: EditorProjectView) {
  return project.tracks.find((track) => track.kind === 'audio')
}

function audioClips(project: EditorProjectView) {
  return [...(audioTrack(project)?.clips ?? [])]
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
  if ([
    'detach-audio', 'attach-audio', 'unlink-audio', 'link-audio', 'mute-audio',
    'mute-video-audio', 'trim-audio', 'move-audio', 'delete-audio', 'insert-audio',
    'set-audio-state', 'set-audio-clip',
  ].includes(command.type)) return null
  const clips = videoClips(project)
  if (command.type === 'delete') {
    const clip = clips.find((candidate) => candidate.id === command.clipId)
    return clip ? rippleOrNull(clip.programRange.endS, -clipDurationS(clip)) : null
  }
  if (command.type === 'insert' || command.type === 'insert-with-audio') {
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
  const tracks = project.tracks.map((track): TrackView => {
    if (track.kind === 'video') return { ...track, clips }
    if (track.kind !== 'audio' || !(track.clips?.length)) return track
    const previousVideos = videoClips(project)
    const independent = track.clips.filter((clip) => !clip.linked && !clip.implicit)
      .map((clip) => shiftedClip(clip, ripple))
    const linked = clips.flatMap((video) => {
      const previousVideo = previousVideos.find((candidate) => candidate.id === video.id)
        ?? previousVideos.find((candidate) => video.sourceRange.startS >= candidate.sourceRange.startS - RANGE_EPSILON
          && video.sourceRange.endS <= candidate.sourceRange.endS + RANGE_EPSILON)
      const existing = track.clips?.find((candidate) => candidate.linkedClipId === previousVideo?.id && candidate.linked)
      const implicit = video.audioMode !== 'detached'
      if (!implicit && !existing) return []
      return [{
        ...(existing ?? video),
        id: existing && video.id === previousVideo?.id ? existing.id : `${video.id}:${implicit ? 'embedded-audio' : 'audio'}`,
        trackId: track.id,
        displayName: existing?.displayName ?? video.displayName,
        sourceAssetId: existing?.sourceAssetId ?? video.sourceAssetId,
        sourceRange: { ...video.sourceRange },
        programRange: { ...video.programRange },
        speed: video.speed,
        linkedClipId: video.id,
        linked: true,
        implicit,
        muted: implicit && video.audioMode === 'muted' ? true : existing?.muted ?? false,
      }]
    })
    return {
      ...track,
      clips: [...linked, ...independent].sort((left, right) => left.programRange.startS - right.programRange.startS),
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

function updateAudioTrack(project: EditorProjectView, nextAudio: readonly ClipView[], nextVideo = videoClips(project)) {
  return {
    ...project,
    tracks: project.tracks.map((track) => track.kind === 'video'
      ? { ...track, clips: nextVideo }
      : track.kind === 'audio'
        ? { ...track, clips: nextAudio.slice().sort((left, right) => left.programRange.startS - right.programRange.startS) }
        : track),
  }
}

function audioSelection(clipId: string): EditorSelection {
  return { kind: 'audio', id: clipId }
}

function checkedAudioMove(project: EditorProjectView, audioClipId: string, startS: number) {
  const clips = audioClips(project)
  const index = clips.findIndex((clip) => clip.id === audioClipId)
  const clip = clips[index]
  if (!clip || clip.implicit || clip.linked) throw new Error('Unlink the audio before moving it')
  const durationS = clip.programRange.endS - clip.programRange.startS
  const frame = frameDurationS(project)
  const nextStartS = snapProgramTime(project, startS)
  const nextEndS = rounded(nextStartS + durationS)
  if (nextStartS < 0 || nextEndS > project.durationS + frame) throw new Error('The audio clip must stay inside the program')
  const overlaps = clips.some((candidate, candidateIndex) => candidateIndex !== index
    && nextStartS < candidate.programRange.endS - RANGE_EPSILON
    && nextEndS > candidate.programRange.startS + RANGE_EPSILON)
  if (overlaps) throw new Error('The audio clip would overlap another A1 clip')
  return { clips, index, clip, nextStartS, nextEndS }
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

export function trimAudioSourceAtProgramDelta(
  project: EditorProjectView,
  audioClipId: string,
  edge: TimelineTrimEdge,
  deltaProgramS: number,
) {
  const clips = audioClips(project)
  const audio = clips.find((candidate) => candidate.id === audioClipId)
  if (!audio || audio.implicit || audio.linked) return null
  const speed = audio.speed && audio.speed > 0 ? audio.speed : 1
  const frameSourceDurationS = frameDurationS(project) * speed
  const initial = edge === 'start' ? audio.sourceRange.startS : audio.sourceRange.endS
  const minimum = edge === 'start' ? 0 : audio.sourceRange.startS + frameSourceDurationS
  const maximum = edge === 'start'
    ? audio.sourceRange.endS - frameSourceDurationS
    : project.sourceDurationS ?? audio.sourceRange.endS
  const snapped = Math.round((initial + deltaProgramS * speed) / frameSourceDurationS) * frameSourceDurationS
  return rounded(Math.min(Math.max(snapped, minimum), maximum))
}

export function moveAudioStartAtProgramDelta(
  project: EditorProjectView,
  audioClipId: string,
  deltaProgramS: number,
) {
  const audio = audioClips(project).find((candidate) => candidate.id === audioClipId)
  if (!audio || audio.implicit || audio.linked) return null
  const durationS = audio.programRange.endS - audio.programRange.startS
  const frame = frameDurationS(project)
  const snapped = Math.round((audio.programRange.startS + deltaProgramS) / frame) * frame
  return rounded(Math.min(Math.max(snapped, 0), Math.max(0, project.durationS - durationS)))
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

  if (command.type === 'detach-audio') {
    const video = clips.find((candidate) => candidate.id === command.clipId)
    if (!video) throw new Error('The video clip no longer exists')
    if (video.audioMode === 'detached') throw new Error('Audio is already detached')
    const currentAudio = audioClips(project)
    const implicit = currentAudio.find((candidate) => candidate.linkedClipId === video.id && candidate.implicit)
    const detached: ClipView = {
      ...(implicit ?? video),
      id: `${video.id}:audio`,
      trackId: audioTrack(project)?.id,
      displayName: implicit?.displayName ?? video.displayName,
      sourceRange: { ...video.sourceRange },
      programRange: { ...video.programRange },
      linkedClipId: video.id,
      linked: true,
      implicit: false,
      muted: video.audioMode === 'muted',
    }
    const nextVideo = clips.map((candidate) => candidate.id === video.id
      ? { ...candidate, audioMode: 'detached' as const }
      : candidate)
    const nextAudio = currentAudio.map((candidate) => candidate.id === implicit?.id ? detached : candidate)
    if (!implicit) nextAudio.push(detached)
    return {
      project: updateAudioTrack(project, nextAudio, nextVideo),
      inverse: { type: 'set-audio-state', clipId: video.id, audioMode: video.audioMode ?? 'embedded', ...(implicit ? {} : { audioClip: undefined }) },
      selection: audioSelection(detached.id),
    }
  }

  if (command.type === 'attach-audio') {
    const video = clips.find((candidate) => candidate.id === command.clipId)
    const currentAudio = audioClips(project)
    const detached = currentAudio.find((candidate) => candidate.linkedClipId === command.clipId && !candidate.implicit)
    if (!video || video.audioMode !== 'detached' || !detached?.linked) throw new Error('Only linked detached audio can be attached')
    const implicit: ClipView = {
      ...detached,
      id: `${video.id}:embedded-audio`,
      linked: true,
      implicit: true,
      muted: false,
    }
    return {
      project: updateAudioTrack(
        project,
        currentAudio.map((candidate) => candidate.id === detached.id ? implicit : candidate),
        clips.map((candidate) => candidate.id === video.id ? { ...candidate, audioMode: 'embedded' as const } : candidate),
      ),
      inverse: { type: 'set-audio-state', clipId: video.id, audioMode: 'detached', audioClip: detached },
      selection: { kind: 'video', id: video.id },
    }
  }

  if (command.type === 'set-audio-state') {
    const video = clips.find((candidate) => candidate.id === command.clipId)
    if (!video) throw new Error('The video clip no longer exists')
    const currentAudio = audioClips(project)
    const previousAudio = currentAudio.find((candidate) => candidate.linkedClipId === video.id)
    const nextVideo = clips.map((candidate) => candidate.id === video.id
      ? { ...candidate, audioMode: command.audioMode }
      : candidate)
    const nextClip = command.audioMode === 'detached'
      ? command.audioClip ?? previousAudio
      : {
          ...(previousAudio ?? video),
          id: `${video.id}:embedded-audio`, linkedClipId: video.id, linked: true, implicit: true,
          muted: command.audioMode === 'muted', sourceRange: { ...video.sourceRange }, programRange: { ...video.programRange },
        }
    if (!nextClip) throw new Error('Detached audio state is incomplete')
    const nextAudio = currentAudio.filter((candidate) => candidate.linkedClipId !== video.id)
    nextAudio.push(nextClip)
    return {
      project: updateAudioTrack(project, nextAudio, nextVideo),
      inverse: {
        type: 'set-audio-state', clipId: video.id, audioMode: video.audioMode ?? 'embedded',
        ...(previousAudio && !previousAudio.implicit ? { audioClip: previousAudio } : {}),
      },
      selection: command.audioMode === 'detached' ? audioSelection(nextClip.id) : { kind: 'video', id: video.id },
    }
  }

  if (command.type === 'mute-video-audio') {
    const video = clips.find((candidate) => candidate.id === command.clipId)
    if (!video || video.audioMode === 'detached') throw new Error('Detached audio must be muted on A1')
    return applyTimelineEdit(project, {
      type: 'set-audio-state', clipId: video.id, audioMode: command.muted ? 'muted' : 'embedded',
    })
  }

  if (command.type === 'unlink-audio' || command.type === 'link-audio') {
    const currentAudio = audioClips(project)
    const index = currentAudio.findIndex((candidate) => candidate.id === command.audioClipId)
    const audio = currentAudio[index]
    if (!audio || audio.implicit) throw new Error('Detached audio no longer exists')
    if (command.type === 'unlink-audio') {
      if (!audio.linked) throw new Error('Audio and video are already unlinked')
      const updated = { ...audio, linked: false }
      return {
        project: updateAudioTrack(project, currentAudio.map((candidate, candidateIndex) => candidateIndex === index ? updated : candidate)),
        inverse: { type: 'set-audio-clip', clip: audio },
        selection: audioSelection(audio.id),
      }
    }
    const video = clips.find((candidate) => candidate.id === audio.linkedClipId)
    if (!video) throw new Error('The associated video clip no longer exists')
    const updated = {
      ...audio,
      linked: true,
      sourceRange: { ...video.sourceRange },
      programRange: { ...video.programRange },
      speed: video.speed,
    }
    return {
      project: updateAudioTrack(project, currentAudio.map((candidate, candidateIndex) => candidateIndex === index ? updated : candidate)),
      inverse: { type: 'set-audio-clip', clip: audio },
      selection: audioSelection(audio.id),
    }
  }

  if (command.type === 'set-audio-clip') {
    const currentAudio = audioClips(project)
    const previous = currentAudio.find((candidate) => candidate.id === command.clip.id)
    if (!previous) throw new Error('The audio clip no longer exists')
    return {
      project: updateAudioTrack(project, currentAudio.map((candidate) => candidate.id === command.clip.id ? command.clip : candidate)),
      inverse: { type: 'set-audio-clip', clip: previous },
      selection: audioSelection(command.clip.id),
    }
  }

  if (command.type === 'mute-audio') {
    const currentAudio = audioClips(project)
    const audio = currentAudio.find((candidate) => candidate.id === command.audioClipId)
    if (!audio || audio.implicit) throw new Error('Detached audio no longer exists')
    const updated = { ...audio, muted: command.muted }
    return {
      project: updateAudioTrack(project, currentAudio.map((candidate) => candidate.id === audio.id ? updated : candidate)),
      inverse: { type: 'mute-audio', audioClipId: audio.id, muted: Boolean(audio.muted) },
      selection: audioSelection(audio.id),
    }
  }

  if (command.type === 'move-audio') {
    const { clips: currentAudio, index, clip, nextStartS, nextEndS } = checkedAudioMove(project, command.audioClipId, command.startS)
    const updated = { ...clip, programRange: { startS: nextStartS, endS: nextEndS } }
    return {
      project: updateAudioTrack(project, currentAudio.map((candidate, candidateIndex) => candidateIndex === index ? updated : candidate)),
      inverse: { type: 'move-audio', audioClipId: clip.id, startS: clip.programRange.startS },
      selection: audioSelection(clip.id),
    }
  }

  if (command.type === 'trim-audio') {
    const currentAudio = audioClips(project)
    const index = currentAudio.findIndex((candidate) => candidate.id === command.audioClipId)
    const audio = currentAudio[index]
    if (!audio || audio.implicit || audio.linked) throw new Error('Unlink the audio before trimming it')
    const speed = audio.speed && audio.speed > 0 ? audio.speed : 1
    const minimum = frameDurationS(project) * speed
    const sourceS = rounded(command.sourceS)
    const sourceRange = command.edge === 'start'
      ? { ...audio.sourceRange, startS: sourceS }
      : { ...audio.sourceRange, endS: sourceS }
    if (sourceRange.startS < 0 || sourceRange.endS > (project.sourceDurationS ?? sourceRange.endS)
      || sourceRange.endS - sourceRange.startS < minimum - RANGE_EPSILON) {
      throw new Error('The audio trim is outside the source media')
    }
    const durationS = (sourceRange.endS - sourceRange.startS) / speed
    const programRange = command.edge === 'start'
      ? { startS: rounded(audio.programRange.endS - durationS), endS: audio.programRange.endS }
      : { startS: audio.programRange.startS, endS: rounded(audio.programRange.startS + durationS) }
    if (programRange.startS < 0 || programRange.endS > project.durationS + frameDurationS(project)) {
      throw new Error('The audio trim is outside the program')
    }
    const overlaps = currentAudio.some((candidate, candidateIndex) => candidateIndex !== index
      && programRange.startS < candidate.programRange.endS - RANGE_EPSILON
      && programRange.endS > candidate.programRange.startS + RANGE_EPSILON)
    if (overlaps) throw new Error('The audio trim would overlap another A1 clip')
    const oldSourceS = command.edge === 'start' ? audio.sourceRange.startS : audio.sourceRange.endS
    const updated = { ...audio, sourceRange, programRange }
    return {
      project: updateAudioTrack(project, currentAudio.map((candidate, candidateIndex) => candidateIndex === index ? updated : candidate)),
      inverse: { type: 'trim-audio', audioClipId: audio.id, edge: command.edge, sourceS: oldSourceS },
      selection: audioSelection(audio.id),
    }
  }

  if (command.type === 'delete-audio') {
    const currentAudio = audioClips(project)
    const index = currentAudio.findIndex((candidate) => candidate.id === command.audioClipId)
    const audio = currentAudio[index]
    if (!audio || audio.implicit || audio.linked) throw new Error('Unlink the audio before ripple deleting it')
    const durationS = audio.programRange.endS - audio.programRange.startS
    const next = currentAudio.filter((candidate) => candidate.id !== audio.id).map((candidate) => (
      !candidate.implicit && !candidate.linked && candidate.programRange.startS >= audio.programRange.endS - RANGE_EPSILON
        ? { ...candidate, programRange: { startS: rounded(candidate.programRange.startS - durationS), endS: rounded(candidate.programRange.endS - durationS) } }
        : candidate
    ))
    return {
      project: updateAudioTrack(project, next),
      inverse: { type: 'insert-audio', index, clip: audio },
      selection: null,
    }
  }

  if (command.type === 'insert-audio') {
    const currentAudio = audioClips(project)
    if (currentAudio.some((candidate) => candidate.id === command.clip.id)) throw new Error('The audio clip already exists')
    const durationS = command.clip.programRange.endS - command.clip.programRange.startS
    const shifted = currentAudio.map((candidate) => (
      !candidate.implicit && !candidate.linked && candidate.programRange.startS >= command.clip.programRange.startS - RANGE_EPSILON
        ? { ...candidate, programRange: { startS: rounded(candidate.programRange.startS + durationS), endS: rounded(candidate.programRange.endS + durationS) } }
        : candidate
    ))
    shifted.splice(Math.min(Math.max(command.index, 0), shifted.length), 0, command.clip)
    return {
      project: updateAudioTrack(project, shifted),
      inverse: { type: 'delete-audio', audioClipId: command.clip.id },
      selection: audioSelection(command.clip.id),
    }
  }

  if (command.type === 'insert-with-audio') {
    const index = Math.min(Math.max(command.index, 0), clips.length)
    if (clips.some((clip) => clip.id === command.clip.id)) throw new Error('The clip already exists')
    if (audioClips(project).some((clip) => clip.id === command.audioClip.id)) throw new Error('The audio clip already exists')
    const next = reflow([...clips.slice(0, index), command.clip, ...clips.slice(index)])
    const inserted = next.find((clip) => clip.id === command.clip.id)!
    const nextProject = updateTracks(project, next, ripple)
    const audio = {
      ...command.audioClip,
      linkedClipId: inserted.id,
      linked: true,
      implicit: false,
      sourceRange: { ...inserted.sourceRange },
      programRange: { ...inserted.programRange },
      speed: inserted.speed,
    }
    return {
      project: updateAudioTrack(nextProject, [...audioClips(nextProject), audio], next),
      inverse: { type: 'delete', clipId: inserted.id },
      selection: { kind: 'video', id: inserted.id },
    }
  }

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
    const removedAudio = audioClips(project).find((candidate) => candidate.linkedClipId === removed.id && !candidate.implicit)
    return {
      project: updateTracks(project, next, ripple),
      inverse: removedAudio
        ? { type: 'insert-with-audio', index, clip: removed, audioClip: removedAudio }
        : { type: 'insert', index, clip: removed },
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
