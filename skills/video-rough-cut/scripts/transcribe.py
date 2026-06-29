"""Transcribe audio with word-level timestamps using faster-whisper (CPU/int8 + VAD).

Usage: python transcribe.py <audio_or_video_path> <out_prefix> [model] [--lang CODE]
Outputs: <out_prefix>.json  (segments + words)  and  <out_prefix>.srt

  model    Whisper model (default base.en). For any non-English language pass a
           MULTILINGUAL model — the .en models are English-only (e.g. `medium`).
  --lang   ISO language code passed to the model (default en). Use with a
           multilingual model, e.g.:  transcribe.py a.wav out medium --lang zh
"""
import sys, json, datetime

def fmt_ts(t):
    td = datetime.timedelta(seconds=float(t))
    total_ms = int(td.total_seconds() * 1000)
    h, rem = divmod(total_ms, 3600_000)
    m, rem = divmod(rem, 60_000)
    s, ms = divmod(rem, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

def parse_args(argv):
    """positional: audio, out_prefix, [model];  option: --lang CODE (default en)."""
    lang = "en"
    pos = []
    i = 0
    while i < len(argv):
        if argv[i] == "--lang":
            lang = argv[i + 1]; i += 2
        else:
            pos.append(argv[i]); i += 1
    audio = pos[0]
    out_prefix = pos[1]
    model_name = pos[2] if len(pos) > 2 else "base.en"
    return audio, out_prefix, model_name, lang

def main():
    audio, out_prefix, model_name, lang = parse_args(sys.argv[1:])

    from faster_whisper import WhisperModel
    print(f"[transcribe] loading model={model_name} lang={lang} (cpu/int8)", flush=True)
    model = WhisperModel(model_name, device="cpu", compute_type="int8")

    print(f"[transcribe] transcribing {audio} ...", flush=True)
    segments, info = model.transcribe(
        audio,
        language=lang,
        word_timestamps=True,
        vad_filter=True,
        vad_parameters=dict(min_silence_duration_ms=500),
        beam_size=5,
        condition_on_previous_text=True,
    )

    seg_list = []
    srt_lines = []
    idx = 0
    for seg in segments:
        words = []
        if seg.words:
            for w in seg.words:
                words.append({"start": round(w.start, 3), "end": round(w.end, 3),
                              "word": w.word, "prob": round(w.probability, 3)})
        seg_d = {"id": seg.id, "start": round(seg.start, 3), "end": round(seg.end, 3),
                 "text": seg.text, "words": words}
        seg_list.append(seg_d)
        idx += 1
        srt_lines.append(f"{idx}\n{fmt_ts(seg.start)} --> {fmt_ts(seg.end)}\n{seg.text.strip()}\n")
        # progress every ~30 segments
        if idx % 30 == 0:
            print(f"[transcribe] ... {idx} segments, t={seg.end:.0f}s", flush=True)

    out = {
        "audio": audio,
        "model": model_name,
        "duration": round(info.duration, 3),
        "language": info.language,
        "language_probability": round(info.language_probability, 3),
        "segments": seg_list,
    }
    with open(out_prefix + ".json", "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    with open(out_prefix + ".srt", "w", encoding="utf-8") as f:
        f.write("\n".join(srt_lines))

    n_words = sum(len(s["words"]) for s in seg_list)
    print(f"[transcribe] DONE: {len(seg_list)} segments, {n_words} words, "
          f"audio_dur={info.duration:.1f}s -> {out_prefix}.json/.srt", flush=True)

if __name__ == "__main__":
    main()
