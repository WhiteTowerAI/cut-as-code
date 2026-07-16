"""Transcribe media to canonical word-timestamp JSON and SRT files."""

import datetime
import json
import sys


def fmt_ts(value):
    total_ms = int(datetime.timedelta(seconds=float(value)).total_seconds() * 1000)
    hours, remainder = divmod(total_ms, 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    seconds, milliseconds = divmod(remainder, 1000)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d},{milliseconds:03d}"


def parse_args(argv):
    language = "en"
    cache_dir = None
    positional = []
    index = 0
    while index < len(argv):
        if argv[index] == "--lang":
            if index + 1 >= len(argv):
                raise ValueError("--lang requires a language code")
            language = argv[index + 1]
            index += 2
        elif argv[index] == "--cache-dir":
            if index + 1 >= len(argv):
                raise ValueError("--cache-dir requires a path")
            cache_dir = argv[index + 1]
            index += 2
        else:
            positional.append(argv[index])
            index += 1
    if len(positional) not in (2, 3):
        raise ValueError(
            "usage: transcribe.py AUDIO OUT_PREFIX [MODEL] "
            "[--lang CODE|auto] [--cache-dir PATH]"
        )
    return (
        positional[0], positional[1],
        positional[2] if len(positional) == 3 else "base.en",
        language, cache_dir,
    )


def transcribe(audio, model_name, language, cache_dir=None):
    from faster_whisper import WhisperModel

    model = WhisperModel(
        model_name, device="cpu", compute_type="int8", download_root=cache_dir
    )
    segments, info = model.transcribe(
        audio,
        language=None if language == "auto" else language,
        word_timestamps=True,
        vad_filter=True,
        vad_parameters={"min_silence_duration_ms": 500},
        beam_size=5,
        condition_on_previous_text=True,
    )
    output_segments = []
    srt_blocks = []
    for index, segment in enumerate(segments, 1):
        words = [
            {
                "start": round(word.start, 3),
                "end": round(word.end, 3),
                "word": word.word,
                "prob": round(word.probability, 3),
            }
            for word in (segment.words or [])
        ]
        output_segments.append(
            {
                "id": segment.id,
                "start": round(segment.start, 3),
                "end": round(segment.end, 3),
                "text": segment.text,
                "words": words,
            }
        )
        srt_blocks.append(
            f"{index}\n{fmt_ts(segment.start)} --> {fmt_ts(segment.end)}\n{segment.text.strip()}\n"
        )
    return {
        "audio": audio,
        "model": model_name,
        "duration": round(info.duration, 3),
        "language": info.language,
        "language_probability": round(info.language_probability, 3),
        "segments": output_segments,
    }, "\n".join(srt_blocks)


def main(argv=None):
    audio, out_prefix, model_name, language, cache_dir = parse_args(
        sys.argv[1:] if argv is None else argv
    )
    data, srt = transcribe(audio, model_name, language, cache_dir)
    with open(out_prefix + ".json", "w", encoding="utf-8") as handle:
        json.dump(data, handle, ensure_ascii=False, indent=1)
    with open(out_prefix + ".srt", "w", encoding="utf-8") as handle:
        handle.write(srt)


if __name__ == "__main__":
    main()
