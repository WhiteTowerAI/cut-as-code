import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from tests.protocol_testlib import ROOT, load_script


projectlib = load_script(
    "skills/video-understand/scripts/projectlib.py", "understanding_projectlib"
)
analyze = load_script("skills/video-understand/scripts/analyze.py", "understanding_analyze")
probe = load_script("skills/video-understand/scripts/probe.py", "understanding_probe")
transcribe = load_script(
    "skills/video-understand/scripts/transcribe.py", "understanding_transcribe"
)


def transcript_fixture():
    segments = [
        {
            "id": 0,
            "start": 0.0,
            "end": 2.0,
            "text": "I'm Alice from Acme.",
            "words": [
                {"start": 0.0, "end": 0.3, "word": " I'm", "prob": 0.99},
                {"start": 0.4, "end": 0.8, "word": " Alice", "prob": 0.99},
                {"start": 0.9, "end": 1.2, "word": " from", "prob": 0.99},
                {"start": 1.3, "end": 1.8, "word": " Acme.", "prob": 0.99},
            ],
        },
        {
            "id": 1,
            "start": 3.0,
            "end": 5.0,
            "text": "There are three steps and 200 customers.",
            "words": [
                {"start": 3.0, "end": 3.2, "word": " There", "prob": 0.98},
                {"start": 3.3, "end": 3.5, "word": " are", "prob": 0.98},
                {"start": 3.6, "end": 3.9, "word": " three", "prob": 0.98},
                {"start": 4.0, "end": 4.3, "word": " steps", "prob": 0.98},
                {"start": 4.4, "end": 4.9, "word": " 200 customers.", "prob": 0.98},
            ],
        },
        {
            "id": 2,
            "start": 6.0,
            "end": 7.5,
            "text": "Why does this matter?",
            "words": [
                {"start": 6.0, "end": 6.3, "word": " Why", "prob": 0.97},
                {"start": 6.4, "end": 6.7, "word": " does", "prob": 0.97},
                {"start": 6.8, "end": 7.0, "word": " this", "prob": 0.97},
                {"start": 7.1, "end": 7.5, "word": " matter?", "prob": 0.97},
            ],
        },
    ]
    return {
        "audio": "audio.wav",
        "model": "base.en",
        "duration": 8.0,
        "language": "en",
        "language_probability": 0.99,
        "segments": segments,
    }


def understanding_fixture():
    return {
        "schema_version": 1,
        "timeline_id": "source",
        "overview": {
            "title": "Acme steps",
            "content_type": "talking-head",
            "summary": "Alice explains three steps.",
            "primary_language": "en",
        },
        "chapters": [
            {
                "id": "chapter-001",
                "start_s": 0.0,
                "end_s": 8.0,
                "title": "Three steps",
                "summary": "The complete explanation.",
                "confidence": 0.9,
                "evidence_refs": ["segment:0", "segment:1"],
            }
        ],
        "entities": [
            {
                "id": "entity-001",
                "name": "Alice",
                "type": "person",
                "confidence": 0.95,
                "evidence_refs": ["segment:0"],
            }
        ],
        "moments": [
            {
                "id": "moment-001",
                "kind": "stat",
                "start_s": 4.4,
                "end_s": 4.9,
                "summary": "200 customers",
                "confidence": 0.9,
                "evidence_refs": ["segment:1"],
            }
        ],
        "transcript_corrections": [],
        "uncertainties": [],
    }


class AnalysisTests(unittest.TestCase):
    def test_analysis_emits_stable_candidate_ids(self):
        result = analyze.analyze_transcript(transcript_fixture())
        self.assertEqual(
            [f"moment-{index:03d}" for index in range(1, len(result["moments"]) + 1)],
            [moment["id"] for moment in result["moments"]],
        )

    def test_analysis_detects_list_stat_and_question(self):
        kinds = {moment["kind"] for moment in analyze.analyze_transcript(transcript_fixture())["moments"]}
        self.assertTrue({"list", "stat", "question"}.issubset(kinds))

    def test_analysis_evidence_resolves_to_transcript_segments(self):
        moments = analyze.analyze_transcript(transcript_fixture())["moments"]
        refs = {f"segment:{segment['id']}" for segment in transcript_fixture()["segments"]}
        self.assertTrue(all(set(moment["evidence_refs"]) <= refs for moment in moments))

    def test_analysis_reports_silence_and_speaking_ratio(self):
        speech = analyze.analyze_transcript(transcript_fixture())["speech"]
        self.assertEqual(2, speech["silence_count_ge_0_8s"])
        self.assertGreater(speech["speaking_ratio"], 0)
        self.assertLess(speech["speaking_ratio"], 1)


class UnderstandingValidationTests(unittest.TestCase):
    def test_valid_understanding_has_no_errors(self):
        self.assertEqual(
            [], projectlib.validate_understanding(understanding_fixture(), transcript_fixture())
        )

    def test_semantic_evidence_must_resolve(self):
        understanding = understanding_fixture()
        understanding["moments"][0]["evidence_refs"] = ["segment:missing"]
        errors = projectlib.validate_understanding(understanding, transcript_fixture())
        self.assertTrue(any("segment:missing" in error for error in errors))

    def test_confidence_must_be_between_zero_and_one(self):
        understanding = understanding_fixture()
        understanding["entities"][0]["confidence"] = 2
        self.assertTrue(
            any("confidence" in error for error in projectlib.validate_understanding(understanding, transcript_fixture()))
        )

    def test_ranges_must_fit_transcript_duration(self):
        understanding = understanding_fixture()
        understanding["moments"][0]["end_s"] = 9.0
        self.assertTrue(
            any("range" in error for error in projectlib.validate_understanding(understanding, transcript_fixture()))
        )

    def test_ids_are_unique_across_semantic_items(self):
        understanding = understanding_fixture()
        understanding["moments"][0]["id"] = "entity-001"
        self.assertTrue(
            any("duplicate semantic id" in error for error in projectlib.validate_understanding(understanding, transcript_fixture()))
        )


class UtilityTests(unittest.TestCase):
    def test_probe_parses_fractional_frame_rate(self):
        self.assertEqual({"num": 30000, "den": 1001}, probe.parse_rate("30000/1001"))

    def test_probe_rejects_invalid_frame_rate(self):
        with self.assertRaises(ValueError):
            probe.parse_rate("0/0")

    def test_transcribe_timestamp_format(self):
        self.assertEqual("01:02:03,456", transcribe.fmt_ts(3723.456))

    def test_transcribe_arguments_support_multilingual_model(self):
        self.assertEqual(
            ("a.wav", "out", "medium", "zh", None),
            transcribe.parse_args(["a.wav", "out", "medium", "--lang", "zh"]),
        )

    def test_transcribe_arguments_support_auto_language_and_project_cache(self):
        self.assertEqual(
            ("a.wav", "out", "small", "auto", "work/cache/faster-whisper"),
            transcribe.parse_args(
                [
                    "a.wav", "out", "small", "--lang", "auto",
                    "--cache-dir", "work/cache/faster-whisper",
                ]
            ),
        )

    def test_transcribe_preserves_word_json_and_srt_contract(self):
        word = SimpleNamespace(start=0.1, end=0.4, word=" Hello", probability=0.9876)
        segment = SimpleNamespace(
            id=7, start=0.1, end=0.8, text=" Hello world.", words=[word]
        )
        info = SimpleNamespace(
            duration=1.0, language="en", language_probability=0.999
        )

        class FakeModel:
            def __init__(self, model_name, device, compute_type, download_root=None):
                self.model_name = model_name
                self.download_root = download_root

            def transcribe(self, audio, **kwargs):
                self.kwargs = kwargs
                return iter([segment]), info

        with patch.dict(sys.modules, {"faster_whisper": SimpleNamespace(WhisperModel=FakeModel)}):
            data, srt = transcribe.transcribe(
                "audio.wav", "small", "auto", "work/cache/faster-whisper"
            )
        self.assertEqual(7, data["segments"][0]["id"])
        self.assertEqual("en", data["language"])
        self.assertEqual(
            {"start": 0.1, "end": 0.4, "word": " Hello", "prob": 0.988},
            data["segments"][0]["words"][0],
        )
        self.assertIn("00:00:00,100 --> 00:00:00,800", srt)

    def test_analysis_and_understanding_validator_clis(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            transcript_path = tmp / "transcript.json"
            analysis_path = tmp / "analysis.json"
            understanding_path = tmp / "understanding.json"
            transcript_path.write_text(json.dumps(transcript_fixture()), encoding="utf-8")
            understanding_path.write_text(json.dumps(understanding_fixture()), encoding="utf-8")
            subprocess.run(
                [
                    "python", str(ROOT / "skills/video-understand/scripts/analyze.py"),
                    str(transcript_path), str(analysis_path),
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            validated = subprocess.run(
                [
                    "python", str(ROOT / "skills/video-understand/scripts/validate.py"),
                    "understanding", str(understanding_path), str(transcript_path),
                ],
                capture_output=True,
                text=True,
            )
            self.assertEqual(0, validated.returncode, validated.stderr)
            self.assertTrue(json.loads(analysis_path.read_text(encoding="utf-8"))["moments"])


if __name__ == "__main__":
    unittest.main()
