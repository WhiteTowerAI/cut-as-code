import copy
import inspect
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


SKILL_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SKILL_ROOT / "scripts"))
sys.path.insert(0, str(SKILL_ROOT.parent / "video-understand" / "scripts"))

import broll_plan
import normalize_broll
import speaker_inset


class NormalizeFrameCountTests(unittest.TestCase):
    @staticmethod
    def _probe(duration):
        return {
            "duration_s": duration,
            "width": 320,
            "height": 180,
            "fps": {"num": 30, "den": 1},
            "sar": "1:1",
            "codec": "h264",
            "pix_fmt": "yuv420p",
            "has_audio": False,
            "has_subtitles": False,
            "has_data": False,
        }

    def _source_direct_fixture(self, root, count):
        candidates_dir = root / "work/cache/b-roll/candidates"
        normalized_dir = root / "work/cache/b-roll/normalized"
        candidates_dir.mkdir(parents=True)
        normalized_dir.mkdir(parents=True)
        candidates = []
        segments = []
        for index in range(count):
            source = candidates_dir / f"source-{index + 1}.mp4"
            source.write_bytes(f"source-{index + 1}".encode("ascii"))
            candidate_id = f"asset-{index + 1}"
            candidates.append({
                "id": candidate_id,
                "media_type": "video",
                "cache_path": source.relative_to(root / "work").as_posix(),
                "sha256": broll_plan.sha256_file(source),
                "probe": {"duration_s": 10.0},
            })
            segments.append({
                "candidate_id": candidate_id,
                "source_range": {"start_s": 0.25, "end_s": 1.25},
                "program_range": {"start_s": float(index), "end_s": float(index + 1)},
                "playback_rate": 1.0,
            })
        shot = {
            "id": "shot",
            "status": "selected",
            "program_range": {"start_s": 0.0, "end_s": float(count)},
            "candidates": candidates,
            "selected": {"segments": segments},
        }
        timeline = {
            "width": 320,
            "height": 180,
            "fps": {"num": 30, "den": 1},
            "program_duration_s": float(count),
        }
        return candidates, shot, timeline, normalized_dir / f"broll-{count:03d}.mp4"

    @staticmethod
    def _mock_ffmpeg(command, *args, **kwargs):
        if (command[0] == "ffmpeg" and command[-1].endswith(".mp4")
                and not ("-f" in command and command[command.index("-f") + 1] == "null")):
            Path(command[-1]).write_bytes(b"normalized-video")
        return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

    def test_one_to_three_segments_use_one_source_direct_filtergraph(self):
        for count in (1, 2, 3):
            with self.subTest(count=count), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                candidates, shot, timeline, output = self._source_direct_fixture(root, count)
                commands = []

                def record(command, *args, **kwargs):
                    commands.append(command)
                    return self._mock_ffmpeg(command, *args, **kwargs)

                with (
                    mock.patch.object(normalize_broll.subprocess, "run", side_effect=record),
                    mock.patch.object(
                        normalize_broll, "_probe", side_effect=lambda path: self._probe(
                            1.0 if "-segment-" in Path(path).name else float(count)
                        ),
                    ),
                ):
                    result = normalize_broll.normalize_selection(
                        candidates, shot, timeline, output,
                    )

                encoders = [
                    command for command in commands
                    if command[0] == "ffmpeg" and "-filter_complex" in command
                ]
                self.assertEqual(1, len(encoders), commands)
                command = encoders[0]
                graph = command[command.index("-filter_complex") + 1]
                self.assertEqual(count, command.count("-i"))
                inputs = [
                    command[index + 1] for index, value in enumerate(command)
                    if value == "-i"
                ]
                for index, candidate in enumerate(candidates):
                    source = root / "work" / candidate["cache_path"]
                    self.assertTrue(any(os.path.samefile(source, value) for value in inputs))
                    self.assertIn(f"[{index}:v]trim=start=", graph)
                    self.assertIn("setpts=(PTS-STARTPTS)/1", graph)
                    self.assertIn("scale=320:180:force_original_aspect_ratio=increase", graph)
                    self.assertIn("crop=320:180", graph)
                    self.assertIn("fps=30/1:round=up", graph)
                    self.assertIn("trim=end_frame=30", graph)
                if count == 1:
                    self.assertNotIn("concat=", graph)
                    self.assertEqual("[v0]", command[command.index("-map") + 1])
                else:
                    self.assertIn(f"concat=n={count}:v=1:a=0", graph)
                for value in ("-c:v", "libx264", "-crf", "18", "-preset", "medium",
                              "-pix_fmt", "yuv420p", "-movflags", "+faststart"):
                    self.assertIn(value, command)
                self.assertEqual(normalize_broll.INTERMEDIATE_PROFILE, result["intermediate_profile"])
                self.assertEqual(count, len(result["source_segments"]))
                self.assertNotIn("segments", result)
                self.assertFalse(any(output.parent.glob(f"{output.stem}-segment-*")))

    def test_delivery_profile_is_fixed_and_review_composite_stays_default(self):
        self.assertEqual({
            "schema_version": 1,
            "container": "mp4",
            "encoder": "libx264",
            "codec": "h264",
            "crf": 18,
            "preset": "medium",
            "pix_fmt": "yuv420p",
            "audio": "none",
            "movflags": "+faststart",
        }, normalize_broll.INTERMEDIATE_PROFILE)
        self.assertEqual(
            ["-c:v", "libx264", "-crf", "18", "-preset", "medium",
             "-pix_fmt", "yuv420p", "-movflags", "+faststart"],
            normalize_broll.delivery_encoder_args(),
        )
        self.assertIn(
            "delivery_encoder_args",
            inspect.signature(speaker_inset.render_delivery_composite).parameters,
        )
        review_command = speaker_inset._composite_encoder_command(
            320, 180, 30, 1, Path("review.part.mp4"),
        )
        delivery_command = speaker_inset._composite_encoder_command(
            320, 180, 30, 1, Path("delivery.part.mp4"),
            encoder_args=normalize_broll.delivery_encoder_args(),
        )
        self.assertNotIn("-crf", review_command)
        self.assertNotIn("-preset", review_command)
        self.assertEqual("18", delivery_command[delivery_command.index("-crf") + 1])
        self.assertEqual("medium", delivery_command[delivery_command.index("-preset") + 1])

    def test_source_direct_failures_remove_part_and_preserve_existing_target(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            candidates, shot, timeline, output = self._source_direct_fixture(root, 2)
            sentinel = b"last-good-output"
            real_hash = broll_plan.sha256_file

            def render_failure(command, *args, **kwargs):
                if "-filter_complex" in command:
                    raise subprocess.CalledProcessError(1, command)
                return self._mock_ffmpeg(command, *args, **kwargs)

            def decode_failure(command, *args, **kwargs):
                if "-filter_complex" in command:
                    Path(command[-1]).write_bytes(b"new-output")
                elif command[0] == "ffmpeg":
                    raise subprocess.CalledProcessError(1, command)
                return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

            def hash_failure(path):
                if Path(path).name.endswith(".part.mp4"):
                    raise OSError("hash read failed")
                return real_hash(path)

            cases = (
                (
                    "filtergraph", subprocess.CalledProcessError,
                    mock.patch.object(
                        normalize_broll.subprocess, "run", side_effect=render_failure,
                    ),
                    mock.patch.object(
                        normalize_broll, "_probe", side_effect=lambda path: self._probe(
                            1.0 if "-segment-" in Path(path).name else 2.0
                        ),
                    ),
                    mock.patch.object(broll_plan, "sha256_file", wraps=real_hash),
                ),
                (
                    "probe", ValueError,
                    mock.patch.object(
                        normalize_broll.subprocess, "run", side_effect=self._mock_ffmpeg,
                    ),
                    mock.patch.object(
                        normalize_broll, "_probe", side_effect=ValueError("probe failed"),
                    ),
                    mock.patch.object(broll_plan, "sha256_file", wraps=real_hash),
                ),
                (
                    "decode", subprocess.CalledProcessError,
                    mock.patch.object(
                        normalize_broll.subprocess, "run", side_effect=decode_failure,
                    ),
                    mock.patch.object(
                        normalize_broll, "_probe", side_effect=lambda path: self._probe(
                            1.0 if "-segment-" in Path(path).name else 2.0
                        ),
                    ),
                    mock.patch.object(broll_plan, "sha256_file", wraps=real_hash),
                ),
                (
                    "hash", OSError,
                    mock.patch.object(
                        normalize_broll.subprocess, "run", side_effect=self._mock_ffmpeg,
                    ),
                    mock.patch.object(
                        normalize_broll, "_probe", side_effect=lambda path: self._probe(
                            1.0 if "-segment-" in Path(path).name else 2.0
                        ),
                    ),
                    mock.patch.object(broll_plan, "sha256_file", side_effect=hash_failure),
                ),
            )
            for name, error, run_patch, probe_patch, hash_patch in cases:
                with self.subTest(name=name):
                    output.write_bytes(sentinel)
                    output.with_suffix(".part.mp4").write_bytes(b"stale-part")
                    with run_patch, probe_patch, hash_patch, self.assertRaises(error):
                        normalize_broll.normalize_selection(
                            candidates, shot, timeline, output,
                        )
                    self.assertEqual(sentinel, output.read_bytes())
                    self.assertFalse(output.with_suffix(".part.mp4").exists())
                    self.assertFalse(any(output.parent.glob(f"{output.stem}-segment-*")))

    def test_canonical_segment_pads_to_exact_timeline_frame_count(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            candidates = root / "work/cache/b-roll/candidates"
            normalized = root / "work/cache/b-roll/normalized"
            candidates.mkdir(parents=True)
            normalized.mkdir(parents=True)
            source = candidates / "24fps-between-frames.mp4"
            subprocess.run([
                "ffmpeg", "-y", "-loglevel", "error",
                "-f", "lavfi", "-i", "testsrc2=size=128x96:rate=24",
                "-t", "10", "-an", "-c:v", "libx264", "-pix_fmt", "yuv420p",
                "-video_track_timescale", "24", str(source),
            ], check=True, capture_output=True)

            expected_frames = 311
            duration = expected_frames / 60
            candidate = {
                "id": "asset", "media_type": "video",
                "cache_path": source.relative_to(root / "work").as_posix(),
                "sha256": broll_plan.sha256_file(source),
                "probe": {"duration_s": 10.0},
            }
            shot = {
                "id": "shot", "status": "selected",
                "program_range": {"start_s": 0.0, "end_s": duration},
                "candidates": [candidate],
                "selected": {"segments": [{
                    "candidate_id": "asset",
                    "source_range": {
                        "start_s": 1.0,
                        "end_s": 1.0 + duration * 1.5,
                    },
                    "program_range": {"start_s": 0.0, "end_s": duration},
                    "playback_rate": 1.5,
                }]},
            }
            timeline = {
                "width": 128, "height": 96,
                "fps": {"num": 60, "den": 1},
                "program_duration_s": duration,
            }
            output = normalized / "broll-001.mp4"

            normalize_broll.normalize_shot(candidate, shot, timeline, output)

            probe = subprocess.run([
                "ffprobe", "-v", "error", "-count_frames", "-select_streams", "v:0",
                "-show_entries", "stream=nb_read_frames", "-of", "json", str(output),
            ], check=True, capture_output=True, text=True)
            self.assertEqual(
                expected_frames,
                int(json.loads(probe.stdout)["streams"][0]["nb_read_frames"]),
            )


if __name__ == "__main__":
    unittest.main()
