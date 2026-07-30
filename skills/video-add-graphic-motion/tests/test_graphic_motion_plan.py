"""Focused graphic-motion plan and Project Protocol tests."""

import copy
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "scripts"), str(ROOT.parent / "video-understand" / "scripts")]

import graphic_motion_plan
import projectlib


MIT_LICENSE = b"""MIT License

Copyright (c) 2026 nexu-io contributors

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""


class GraphicMotionPlanTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        for directory in (
            "work/understand",
            "work/cache/graphic-motion/source/gm-001",
            "work/cache/graphic-motion/hyperframes/gm-001",
            "work/cache/graphic-motion/rendered/gm-001",
            "work/graphic-motion",
            "review/00-video-understanding",
            "review/04-graphic-motion",
        ):
            (self.root / directory).mkdir(parents=True, exist_ok=True)

        self.timeline = {
            "schema_version": 1,
            "timeline_id": "main",
            "source_duration_s": 8.0,
            "program_duration_s": 8.0,
            "fps": {"num": 30000, "den": 1001},
            "clips": [{
                "id": "clip-001",
                "source_range": {"start_s": 0.0, "end_s": 8.0},
                "program_range": {"start_s": 0.0, "end_s": 8.0},
                "speed": 1.0,
                "decision_ref": "source",
            }],
        }
        self.transcript = {"duration": 8.0, "segments": [{
            "id": "segment-001", "start": 1.0, "end": 1.4, "text": "signal",
            "words": [{"word": "signal", "start": 1.0, "end": 1.4}],
        }]}
        self.understanding = {"schema_version": 1, "summary": "A signal becomes visible."}
        self._json("work/timeline.json", self.timeline)
        self.media = {
            "schema_version": 1,
            "duration_s": 8.0,
            "width": 16,
            "height": 9,
            "fps": {"num": 30000, "den": 1001},
        }
        self.analysis = {
            "schema_version": 1,
            "timeline_id": "source",
            "speech": {"duration_s": 8.0},
            "moments": [],
        }
        self._json("work/understand/media.json", self.media)
        self._json("work/understand/transcript.json", self.transcript)
        self._json("work/understand/analysis.json", self.analysis)
        self._json("work/understand/understanding.json", self.understanding)
        for name in ("contact-sheet.jpg", "transcript.srt", "video-summary.md"):
            (self.root / "review/00-video-understanding" / name).write_bytes(name.encode())
        understanding_contact_sheet = self.root / "review/00-video-understanding/contact-sheet.jpg"
        mapped_word = projectlib.map_transcript_to_timeline(
            self.transcript, self.timeline,
        )["segments"][0]["words"][0]

        self.project = {
            "schema_version": 1,
            "active_sequence": "main",
            "sequences": {"main": {"timeline": "timeline.json", "operations": [
                "cut", "b-roll", "content-cards", "captions",
            ]}},
            "operations": [
                {"id": "understanding", "skill": "video-understand", "revision": 1,
                 "status": "verified", "depends_on": [], "based_on": {},
                 "target": {"sequence": "main", "scope": "understanding"},
                 "effects": {"changes_timeline": False, "changes_geometry": False,
                             "changes_video_pixels": False, "changes_audio": False},
                 "check": {"status": "pass", "report": "../review/00-video-understanding/video-summary.md"}},
                self._operation("cut", 2),
                self._operation("b-roll", 3),
                self._operation("content-cards", 4),
                self._operation("captions", 5),
            ],
            "render": {"status": "verified"},
        }
        self._json("work/project.json", self.project)

        source = self._file("work/cache/graphic-motion/source/gm-001/original.html", b"<div class='signal'></div>")
        license_file = self._file(
            "work/cache/graphic-motion/source/gm-001/LICENSE",
            MIT_LICENSE,
        )
        source_preview = self._image(
            "work/cache/graphic-motion/source/gm-001/source-preview.png"
        )
        port = self._file(
            "work/cache/graphic-motion/hyperframes/gm-001/index.html",
            b"<div data-composition-id='gm-001'><div class='signal'></div></div>",
        )
        patch = self._file("work/cache/graphic-motion/hyperframes/gm-001/adaptation.patch", b"bind cue time\n")
        runtime = self._file("work/cache/graphic-motion/hyperframes/gm-001/gsap.min.js", b"local runtime")
        frames = [
            self._image(
                f"work/cache/graphic-motion/rendered/gm-001/frame_{index:06d}.png",
                rgba=True,
            )
            for index in range(1, 61)
        ]
        composite_first = self._image("review/04-graphic-motion/composite-first.png")
        composite_middle = self._image("review/04-graphic-motion/composite-middle.png")
        composite_last = self._image("review/04-graphic-motion/composite-last.png")
        check_report = self._json("review/04-graphic-motion/hyperframes-check.json", {
            "status": "pass", "composition_id": "gm-001",
        })
        snapshots = [self._image(f"review/04-graphic-motion/snapshot-{index}.png") for index in range(1, 5)]
        source_fidelity = self._source_fidelity(
            "review/04-graphic-motion/source-fidelity.png", source_preview, snapshots[1],
        )
        review_evidence = {
            "source_fidelity": self._binding(source_fidelity),
            "composite_first": self._binding(composite_first),
            "composite_middle": self._binding(composite_middle),
            "composite_last": self._binding(composite_last),
            "hyperframes_check": self._binding(check_report),
            "hyperframes_snapshots": [
                {"pose": pose, "at_s": at_s, "file": self._binding(item)}
                for pose, at_s, item in zip(
                    ("first-visible", "key-interaction", "final-minus-hold", "final"),
                    (0.2, 0.8, 1.5, 1.8),
                    snapshots,
                )
            ],
            "source_fidelity_inputs": {
                "source_preview": self._binding(source_preview),
                "port_snapshot": self._binding(snapshots[1]),
                "normalized_time": 0.4,
            },
        }
        review_rationale = "The port matches the source and reads over final pixels."
        receipt = self._json("review/04-graphic-motion/review.json", {
            "status": "approved",
            "mode": "agent",
            "actor": "test-agent",
            "rationale": review_rationale,
            "evidence": review_evidence,
        })
        input_bindings = [
            self._binding(self.root / "work/timeline.json"),
            self._binding(self.root / "work/understand/transcript.json"),
            self._binding(self.root / "work/understand/understanding.json"),
            self._binding(self.root / "work/understand/media.json"),
            self._binding(understanding_contact_sheet),
        ]
        bindings = [
            *input_bindings,
            *[self._binding(item) for item in (
                source, license_file, source_preview, port, patch, runtime,
            )],
            *[self._binding(item) for item in frames],
            *[review_evidence[key] for key in graphic_motion_plan.REVIEW_IMAGE_KEYS],
            review_evidence["hyperframes_check"],
            *[snapshot["file"] for snapshot in review_evidence["hyperframes_snapshots"]],
            self._binding(receipt),
        ]

        self.plan = {
            "schema_version": 2,
            "timeline_id": "main",
            "timebase": "program",
            "program_duration_s": 8.0,
            "fps": {"num": 30000, "den": 1001},
            "dependencies": ["understanding", "cut", "b-roll"],
            "based_on": {"understanding": 1, "cut": 2, "b-roll": 3},
            "input_hashes": {
                "timeline_sha256": self._digest(self.root / "work/timeline.json"),
                "transcript_sha256": self._digest(self.root / "work/understand/transcript.json"),
                "understanding_sha256": self._digest(self.root / "work/understand/understanding.json"),
                "media_sha256": self._digest(self.root / "work/understand/media.json"),
                "contact_sheet_sha256": self._digest(understanding_contact_sheet),
            },
            "decision": {"mode": "agent", "actor": "test-agent", "rationale": "The signal benefits from motion."},
            "delivery_bindings": bindings,
            "cues": [{
                "id": "gm-001",
                "status": "verified",
                "program_range": {"start_s": 1.0, "end_s": 3.0},
                "source_ranges": [{"clip_id": "clip-001", "start_s": 1.0, "end_s": 3.0}],
                "intent": {
                    "authored_at": "2026-07-28T00:00:00Z",
                    "content": "An abstract signal becomes ordered.",
                    "purpose": "Make the signal transformation concrete.",
                    "motion_family": "pulse",
                    "interaction_model": "finite activation",
                    "timing_rationale": "The cue begins on the word signal and resolves before the next idea.",
                    "compositing_mode": "transparent-overlay",
                    "search_queries": ["licensed css signal pulse animation"],
                },
                "evidence": {
                    "transcript_words": [mapped_word],
                    "visual_refs": [{
                        "path": "review/00-video-understanding/contact-sheet.jpg",
                        "sha256": self._digest(understanding_contact_sheet),
                        "note": "The center safe area is clear during the cue.",
                    }],
                },
                "search": {
                    "searched_at": "2026-07-28T00:05:00Z",
                    "queries": ["licensed css signal pulse animation"],
                    "candidates": [
                        {
                            "id": "candidate-selected",
                            "catalog_id": "motion-anything",
                            "url": "https://github.com/nexu-io/motion-anything/blob/0123456789abcdef/recipes/signal/original.html",
                            "license": "MIT",
                            "popularity_evidence": "Curated recipe with a verified upstream source.",
                            "decision": "selected",
                            "reason": "Best semantic and visual match with a minimal CSS timing port.",
                        },
                        {
                            "id": "candidate-rejected",
                            "catalog_id": "anime-examples",
                            "url": "https://github.com/juliangarnier/anime/blob/abcdef0123456789/examples/particles.html",
                            "license": "MIT",
                            "popularity_evidence": "Popular upstream animation library.",
                            "decision": "rejected",
                            "reason": "Particle density would cover the speaker's face.",
                        },
                    ],
                    "selected_candidate_id": "candidate-selected",
                    "selection_rationale": "The selected recipe preserves the clear safe area and communicates ordering.",
                },
                "source": {
                    "candidate_id": "candidate-selected",
                    "catalog_id": "motion-anything",
                    "runtime": "css",
                    "url": "https://github.com/nexu-io/motion-anything/blob/0123456789abcdef/recipes/signal/original.html",
                    "revision": "0123456789abcdef",
                    "license": "MIT",
                    "license_url": "https://github.com/nexu-io/motion-anything/blob/0123456789abcdef/recipes/signal/LICENSE",
                    "license_file": self._binding(license_file),
                    "preview": self._binding(source_preview),
                    "attribution": "MIT License, copyright nexu-io contributors.",
                    "retrieved_at": "2026-07-28T00:06:00Z",
                    "files": [
                        self._binding(source),
                        self._binding(license_file),
                        self._binding(source_preview),
                    ],
                },
                "port": {
                    "composition_id": "gm-001",
                    "motion_model": "css",
                    "files": [self._binding(port)],
                    "adaptation_patch": self._binding(patch),
                    "change_categories": ["timing", "local-assets"],
                    "runtime_assets": [self._binding(runtime)],
                },
                "render": {
                    "kind": "overlay",
                    "asset": "cache/graphic-motion/rendered/gm-001",
                    "asset_type": "image-sequence",
                    "pattern": "frame_%06d.png",
                    "start_number": 1,
                    "fps": {"num": 30000, "den": 1001},
                    "start_s": 1.0,
                    "duration_s": 2.0,
                    "frames": [self._binding(item) for item in frames],
                },
                "review": {
                    "status": "approved",
                    "mode": "agent",
                    "actor": "test-agent",
                    "rationale": review_rationale,
                    "evidence": review_evidence,
                    "receipt": self._binding(receipt),
                },
            }],
        }

    def tearDown(self):
        self.temp.cleanup()

    def _file(self, relative, payload):
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(payload)
        return path

    def _image(self, relative, *, rgba=False):
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        mode = "RGBA" if rgba else "RGB"
        digest = hashlib.sha256(str(relative).encode("utf-8")).digest()
        color = (0, 0, 0, 0) if rgba else tuple(digest[:3])
        image = Image.new(mode, (16, 9), color)
        if rgba:
            image.putpixel((8, 4), (255, 255, 255, 192))
        image.save(path)
        return path

    def _source_fidelity(self, relative, source_path, port_path):
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        with Image.open(source_path) as source_image, Image.open(port_path) as port_image:
            source = source_image.convert("RGB")
            port = port_image.convert("RGB")
            image = Image.new(
                "RGB", (source.width + port.width, max(source.height, port.height)), "black",
            )
            image.paste(source, (0, 0))
            image.paste(port, (source.width, 0))
            image.save(path)
        return path

    @staticmethod
    def _operation(operation_id, revision):
        return {
            "id": operation_id,
            "revision": revision,
            "status": "verified",
            "depends_on": [],
            "based_on": {},
            "target": {"sequence": "main", "scope": operation_id},
            "effects": {
                "changes_timeline": False,
                "changes_geometry": False,
                "changes_video_pixels": True,
                "changes_audio": False,
            },
        }

    def _json(self, relative, value):
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value) + "\n", encoding="utf-8")
        return path

    @staticmethod
    def _digest(path):
        return hashlib.sha256(path.read_bytes()).hexdigest()

    def _binding(self, path):
        return {"path": path.relative_to(self.root).as_posix(), "sha256": self._digest(path)}

    def test_requires_completed_video_understand_before_search(self):
        self.assertEqual([], graphic_motion_plan.validate_prerequisite(self.root))
        project = copy.deepcopy(self.project)
        project["operations"][0]["status"] = "approved"
        self._json("work/project.json", project)
        self.assertIn("finish video-understand first", graphic_motion_plan.validate_prerequisite(self.root))

    def test_registration_rechecks_video_understand_state(self):
        project = copy.deepcopy(self.project)
        project["operations"][0]["status"] = "draft"
        project["operations"][0]["check"]["status"] = "pending"
        self.assertIn(
            "finish video-understand first",
            graphic_motion_plan.validate_plan(
                self.plan, self.timeline, project=project,
                project_root=self.root, verify_files=True,
            ),
        )
        with self.assertRaisesRegex(ValueError, "finish video-understand first"):
            graphic_motion_plan.register_operation(project, self.plan, self.timeline, self.root)

    def test_prerequisite_rejects_malformed_evidence_json(self):
        self._json("work/understand/analysis.json", [])
        self.assertIn("finish video-understand first", graphic_motion_plan.validate_prerequisite(self.root))

    def test_prerequisite_rejects_empty_evidence_objects(self):
        for path, original in (
            ("work/understand/media.json", self.media),
            ("work/understand/transcript.json", self.transcript),
            ("work/understand/analysis.json", self.analysis),
        ):
            with self.subTest(path=path):
                self._json(path, {})
                self.assertIn(
                    "finish video-understand first",
                    graphic_motion_plan.validate_prerequisite(self.root),
                )
                self._json(path, original)

    def test_validates_and_registers_verified_overlays_in_canonical_order(self):
        self.assertEqual([], graphic_motion_plan.validate_plan(
            self.plan, self.timeline, project=self.project, project_root=self.root, verify_files=True,
        ))
        registered = graphic_motion_plan.register_operation(self.project, self.plan, self.timeline, self.root)
        self.assertEqual(
            ["cut", "b-roll", "graphic-motion", "content-cards", "captions"],
            registered["sequences"]["main"]["operations"],
        )
        operation = next(item for item in registered["operations"] if item.get("id") == "graphic-motion")
        self.assertEqual("video-add-graphic-motion", operation["skill"])
        self.assertEqual(self.plan["cues"][0]["render"], operation["render"][0])
        self.assertEqual("draft", registered["render"]["status"])
        self.assertEqual(registered, graphic_motion_plan.register_operation(registered, self.plan, self.timeline, self.root))

    def test_registration_cannot_bypass_plan_validation(self):
        plan = copy.deepcopy(self.plan)
        plan["cues"][0]["source"]["license"] = "Hippocratic-2.1"
        with self.assertRaisesRegex(ValueError, "source license is not permitted"):
            graphic_motion_plan.register_operation(self.project, plan, self.timeline, self.root)

    def test_port_must_preserve_selected_source_runtime(self):
        plan = copy.deepcopy(self.plan)
        plan["cues"][0]["source"]["runtime"] = "anime"
        plan["cues"][0]["port"]["motion_model"] = "waapi"
        self.assertIn(
            "gm-001 port motion model does not match source runtime adapter",
            graphic_motion_plan.validate_plan(plan, self.timeline),
        )

    def test_source_runtime_maps_to_hyperframes_adapter(self):
        plan = copy.deepcopy(self.plan)
        plan["cues"][0]["source"]["runtime"] = "canvas"
        plan["cues"][0]["port"]["motion_model"] = "hf-seek"
        self.assertEqual([], graphic_motion_plan.validate_plan(plan, self.timeline))

    def test_schema_v1_plan_requires_regeneration(self):
        plan = copy.deepcopy(self.plan)
        plan["schema_version"] = 1
        self.assertIn(
            "plan schema_version must be 2; regenerate and re-review schema v1 plans",
            graphic_motion_plan.validate_plan(plan, self.timeline),
        )

    def test_source_fidelity_requires_bound_inputs(self):
        plan = copy.deepcopy(self.plan)
        plan["cues"][0]["review"]["evidence"].pop("source_fidelity_inputs")
        self.assertIn(
            "gm-001 source fidelity inputs are invalid",
            graphic_motion_plan.validate_plan(
                plan, self.timeline, project=self.project,
                project_root=self.root, verify_files=True,
            ),
        )

    def test_source_fidelity_must_match_bound_pixels(self):
        fidelity_path = self.root / self.plan["cues"][0]["review"]["evidence"]["source_fidelity"]["path"]
        Image.new("RGB", (32, 9), "white").save(fidelity_path)
        self.assertIn(
            "gm-001 source fidelity comparison does not match bound pixels",
            graphic_motion_plan.validate_plan(
                self.plan, self.timeline, project=self.project,
                project_root=self.root, verify_files=True,
            ),
        )

    def test_source_runtime_and_preview_are_required(self):
        plan = copy.deepcopy(self.plan)
        plan["cues"][0]["source"].pop("runtime")
        plan["cues"][0]["source"].pop("preview")
        errors = graphic_motion_plan.validate_plan(
            plan, self.timeline, project=self.project,
            project_root=self.root, verify_files=True,
        )
        self.assertIn("gm-001 source runtime is required", errors)
        self.assertIn("gm-001 frozen source preview is required", errors)

    def test_source_preview_must_be_a_real_image(self):
        plan = copy.deepcopy(self.plan)
        source = plan["cues"][0]["source"]
        preview_path = self.root / source["preview"]["path"]
        preview_path.write_bytes(b"not an image")
        preview = self._binding(preview_path)
        source["preview"] = preview
        source["files"][-1] = preview
        source_index = next(
            index for index, item in enumerate(plan["delivery_bindings"])
            if item["path"] == preview["path"]
        )
        plan["delivery_bindings"][source_index] = preview
        self.assertIn(
            "gm-001 frozen source preview is invalid",
            graphic_motion_plan.validate_plan(
                plan, self.timeline, project=self.project,
                project_root=self.root, verify_files=True,
            ),
        )

    def test_rejects_unlicensed_remote_or_nondeterministic_ports(self):
        plan = copy.deepcopy(self.plan)
        plan["cues"][0]["source"]["license"] = "Hippocratic-2.1"
        self.assertIn("gm-001 source license is not permitted", graphic_motion_plan.validate_plan(plan, self.timeline))

        port = self.root / self.plan["cues"][0]["port"]["files"][0]["path"]
        port.write_text("requestAnimationFrame(loop); fetch('https://example.com')", encoding="utf-8")
        errors = graphic_motion_plan.validate_plan(
            self.plan, self.timeline, project=self.project, project_root=self.root, verify_files=True,
        )
        self.assertIn("gm-001 port file SHA-256 is stale", errors)
        self.assertIn("gm-001 port contains nondeterministic or remote runtime code", errors)

    def test_selected_source_requires_an_html_entry_point(self):
        plan = copy.deepcopy(self.plan)
        binding = {"path": "work/cache/graphic-motion/source/gm-001/styles.css", "sha256": "b" * 64}
        plan["cues"][0]["source"]["files"] = [binding]
        source_index = next(
            index for index, item in enumerate(plan["delivery_bindings"])
            if item["path"].endswith("original.html")
        )
        plan["delivery_bindings"][source_index] = binding
        self.assertIn(
            "gm-001 source requires an HTML entry point",
            graphic_motion_plan.validate_plan(plan, self.timeline),
        )

        plan = copy.deepcopy(self.plan)
        url = plan["cues"][0]["source"]["url"].replace("original.html", "README.md")
        plan["cues"][0]["source"]["url"] = url
        plan["cues"][0]["search"]["candidates"][0]["url"] = url
        self.assertIn(
            "gm-001 selected source URL must name HTML",
            graphic_motion_plan.validate_plan(plan, self.timeline),
        )

        plan = copy.deepcopy(self.plan)
        plan["cues"][0]["search"]["candidates"][1]["url"] = (
            "https://github.com/juliangarnier/anime/blob/abcdef0123456789/README.md"
        )
        self.assertIn(
            "gm-001 search receipt is incomplete",
            graphic_motion_plan.validate_plan(plan, self.timeline),
        )

    def test_review_receipt_authority_must_match_plan(self):
        plan = copy.deepcopy(self.plan)
        receipt_path = self.root / plan["cues"][0]["review"]["receipt"]["path"]
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        receipt["actor"] = "different-agent"
        self._json(plan["cues"][0]["review"]["receipt"]["path"], receipt)
        binding = self._binding(receipt_path)
        plan["cues"][0]["review"]["receipt"] = binding
        plan["delivery_bindings"][-1] = binding
        self.assertIn(
            "gm-001 review receipt authority does not match plan",
            graphic_motion_plan.validate_plan(
                plan, self.timeline, project=self.project, project_root=self.root, verify_files=True,
            ),
        )

    def test_rejects_incorrect_fps_dependencies_and_overlapping_cues(self):
        plan = copy.deepcopy(self.plan)
        plan["fps"] = {"num": 30, "den": 1}
        plan["based_on"]["cut"] = 99
        duplicate = copy.deepcopy(plan["cues"][0])
        duplicate["id"] = "gm-002"
        duplicate["program_range"] = {"start_s": 2.0, "end_s": 4.0}
        plan["cues"].append(duplicate)
        errors = graphic_motion_plan.validate_plan(plan, self.timeline, project=self.project)
        self.assertIn("plan fps does not match timeline", errors)
        self.assertIn("plan based_on does not match current revisions", errors)
        self.assertIn("gm-002 program range overlaps gm-001", errors)

    def test_dependency_revisions_must_be_positive_integers(self):
        for revision in (None, True, 0, -1, 1.5, "1"):
            with self.subTest(revision=revision):
                project = copy.deepcopy(self.project)
                project["operations"][0]["revision"] = revision
                plan = copy.deepcopy(self.plan)
                plan["based_on"]["understanding"] = revision
                self.assertIn(
                    "dependency revisions must be positive integers",
                    graphic_motion_plan.validate_plan(plan, self.timeline, project=project),
                )

    def test_source_ranges_must_match_program_time_mapping(self):
        plan = copy.deepcopy(self.plan)
        plan["cues"][0]["source_ranges"][0]["start_s"] = 1.25
        self.assertIn(
            "gm-001 source_ranges do not match timeline",
            graphic_motion_plan.validate_plan(plan, self.timeline),
        )

    def test_plan_requires_video_evidence_and_search_comparison(self):
        plan = copy.deepcopy(self.plan)
        del plan["cues"][0]["evidence"]
        del plan["cues"][0]["search"]
        del plan["cues"][0]["intent"]["authored_at"]
        errors = graphic_motion_plan.validate_plan(plan, self.timeline)
        self.assertIn("gm-001 video evidence is incomplete", errors)
        self.assertIn("gm-001 search receipt is incomplete", errors)
        self.assertIn("gm-001 search must happen after motion intent", errors)

    def test_verified_cue_requires_mapped_transcript_words(self):
        plan = copy.deepcopy(self.plan)
        plan["cues"][0]["evidence"]["transcript_words"] = []
        self.assertIn(
            "gm-001 video evidence is incomplete",
            graphic_motion_plan.validate_plan(plan, self.timeline),
        )

    def test_source_retrieval_cannot_precede_search(self):
        plan = copy.deepcopy(self.plan)
        plan["cues"][0]["source"]["retrieved_at"] = "2026-07-27T23:59:00Z"
        self.assertIn(
            "gm-001 source retrieval must happen after search",
            graphic_motion_plan.validate_plan(plan, self.timeline),
        )

    def test_rejects_timer_driven_port(self):
        plan = copy.deepcopy(self.plan)
        port_path = self.root / plan["cues"][0]["port"]["files"][0]["path"]
        port_path.write_text("setTimeout(advance, 16)", encoding="utf-8")
        binding = self._binding(port_path)
        plan["cues"][0]["port"]["files"][0] = binding
        index = next(
            index for index, item in enumerate(plan["delivery_bindings"])
            if item["path"] == binding["path"]
        )
        plan["delivery_bindings"][index] = binding
        self.assertIn(
            "gm-001 port contains nondeterministic or remote runtime code",
            graphic_motion_plan.validate_plan(
                plan, self.timeline, project=self.project, project_root=self.root, verify_files=True,
            ),
        )

    def test_compiler_repeats_domain_validation(self):
        registered = graphic_motion_plan.register_operation(
            self.project, self.plan, self.timeline, self.root,
        )
        operation = next(
            item for item in registered["operations"] if item.get("id") == "graphic-motion"
        )
        forged = copy.deepcopy(self.plan)
        forged["cues"][0]["source"]["license"] = "Hippocratic-2.1"
        forged["cues"][0]["search"]["candidates"][0]["license"] = "Hippocratic-2.1"
        operation["plan_sha256"] = graphic_motion_plan.canonical_sha256(forged)
        errors = []
        projectlib._validate_graphic_motion_plan(
            forged, operation, operation["render"], self.timeline, errors, self.root,
            project=registered,
        )
        self.assertIn("graphic-motion gm-001 source license is not permitted", errors)

    def test_source_requires_official_immutable_catalog_and_frozen_license(self):
        plan = copy.deepcopy(self.plan)
        source = plan["cues"][0]["source"]
        source["url"] = "https://evil.example/latest/original.html"
        source["license_url"] = "https://evil.example/latest/LICENSE"
        source["revision"] = "main"
        source.pop("license_file")
        plan["cues"][0]["search"]["candidates"][0]["url"] = source["url"]
        errors = graphic_motion_plan.validate_plan(plan, self.timeline)
        self.assertIn("gm-001 source URL does not match its catalog and revision", errors)
        self.assertIn("gm-001 frozen license file is required", errors)

    def test_frozen_license_bytes_must_match_declared_spdx(self):
        for payload in (b"ALL RIGHTS RESERVED\n", b"MIT License\nCopyright (c) example\n"):
            with self.subTest(payload=payload):
                plan = copy.deepcopy(self.plan)
                source = plan["cues"][0]["source"]
                license_path = self.root / source["license_file"]["path"]
                license_path.write_bytes(payload)
                binding = self._binding(license_path)
                source["license_file"] = binding
                source["files"][1] = binding
                index = next(
                    index for index, item in enumerate(plan["delivery_bindings"])
                    if item["path"] == binding["path"]
                )
                plan["delivery_bindings"][index] = binding
                self.assertIn(
                    "gm-001 frozen license does not match declared SPDX license",
                    graphic_motion_plan.validate_plan(
                        plan, self.timeline, project=self.project,
                        project_root=self.root, verify_files=True,
                    ),
                )
        license_path.write_bytes(MIT_LICENSE)

    def test_motion_anything_requires_recipe_specific_license(self):
        plan = copy.deepcopy(self.plan)
        plan["cues"][0]["source"]["license_url"] = (
            "https://github.com/nexu-io/motion-anything/blob/0123456789abcdef/LICENSE"
        )
        self.assertIn(
            "gm-001 motion-anything license must be recipe-specific",
            graphic_motion_plan.validate_plan(plan, self.timeline),
        )

    def test_port_preflight_rejects_remote_and_undeclared_assets(self):
        plan = copy.deepcopy(self.plan)
        port_path = self.root / plan["cues"][0]["port"]["files"][0]["path"]
        port_path.write_text('<script src="//evil.example/remote.js"></script>', encoding="utf-8")
        binding = self._binding(port_path)
        plan["cues"][0]["port"]["files"][0] = binding
        index = next(
            index for index, item in enumerate(plan["delivery_bindings"])
            if item["path"] == binding["path"]
        )
        plan["delivery_bindings"][index] = binding
        errors = graphic_motion_plan.validate_port(plan["cues"][0], self.root)
        self.assertIn("gm-001 port contains nondeterministic or remote runtime code", errors)

        port_path.write_text('<link rel="stylesheet" href="extra.css">', encoding="utf-8")
        self._file("work/cache/graphic-motion/hyperframes/gm-001/extra.css", b".signal {}")
        errors = graphic_motion_plan.validate_port(plan["cues"][0], self.root)
        self.assertIn("gm-001 port contains undeclared files", errors)

    def test_port_preflight_fails_closed_on_invalid_utf8_and_hidden_loaders(self):
        plan = copy.deepcopy(self.plan)
        cue = plan["cues"][0]
        port_path = self.root / cue["port"]["files"][0]["path"]
        port_path.write_bytes(b'fetch("https://evil.example")\xff')
        cue["port"]["files"][0] = self._binding(port_path)
        self.assertIn(
            "gm-001 port text asset is not valid UTF-8",
            graphic_motion_plan.validate_port(cue, self.root),
        )

        outside = self._file(
            "work/cache/graphic-motion/hyperframes/outside.js", b"postMessage('stolen')",
        )
        for loader in (
            "new Worker('../outside.js')",
            "new SharedWorker('../outside.js')",
            "importScripts('../outside.js')",
            "CSS.paintWorklet.addModule('../outside.js')",
            "<object data='../outside.js'></object>",
        ):
            with self.subTest(loader=loader):
                port_path.write_text(loader, encoding="utf-8")
                cue["port"]["files"][0] = self._binding(port_path)
                self.assertIn(
                    "gm-001 port references undeclared assets",
                    graphic_motion_plan.validate_port(cue, self.root),
                )
        self.assertTrue(outside.is_file())

    def test_port_preflight_checks_srcset_references(self):
        cue = copy.deepcopy(self.plan["cues"][0])
        port_path = self.root / cue["port"]["files"][0]["path"]
        outside = self._file(
            "work/cache/graphic-motion/hyperframes/outside.png", b"outside",
        )
        for attribute in ("srcset", "imagesrcset"):
            with self.subTest(attribute=attribute):
                port_path.write_text(
                    f'<img {attribute}="../outside.png 1x">', encoding="utf-8",
                )
                cue["port"]["files"][0] = self._binding(port_path)
                self.assertIn(
                    "gm-001 port references undeclared assets",
                    graphic_motion_plan.validate_port(cue, self.root),
                )
        self.assertTrue(outside.is_file())

    def test_bindings_must_use_project_relative_paths(self):
        cue = copy.deepcopy(self.plan["cues"][0])
        cue["port"]["files"][0]["path"] = str(
            (self.root / cue["port"]["files"][0]["path"]).resolve()
        )
        self.assertIn(
            "gm-001 port file path must be project-relative",
            graphic_motion_plan.validate_port(cue, self.root),
        )

        plan = copy.deepcopy(self.plan)
        plan["delivery_bindings"][0]["path"] = str(
            (self.root / plan["delivery_bindings"][0]["path"]).resolve()
        )
        operation = {
            "id": "graphic-motion",
            "plan_sha256": graphic_motion_plan.canonical_sha256(plan),
            "depends_on": plan["dependencies"],
            "based_on": plan["based_on"],
            "delivery_bindings": plan["delivery_bindings"],
        }
        errors = []
        projectlib._validate_graphic_motion_plan(
            plan, operation, [plan["cues"][0]["render"]], self.timeline,
            errors, self.root, project=self.project,
        )
        self.assertIn("graphic-motion bound file path must be project-relative", errors)

        plan["delivery_bindings"][0]["path"] = []
        operation["delivery_bindings"] = plan["delivery_bindings"]
        errors = []
        projectlib._validate_graphic_motion_plan(
            plan, operation, [plan["cues"][0]["render"]], self.timeline,
            errors, self.root, project=self.project,
        )
        self.assertIn("graphic-motion bound file binding is invalid", errors)

    def test_port_preflight_rejects_live_interaction_and_browser_randomness(self):
        cue = copy.deepcopy(self.plan["cues"][0])
        port_path = self.root / cue["port"]["files"][0]["path"]
        for source in (
            ".button:hover { transform: scale(1.1) }",
            "addEventListener('pointermove', update)",
            "addEventListener('click', activate)",
            "const seed = crypto.getRandomValues(new Uint32Array(1))",
            "const worker = new Worker('worker.js')",
            "navigator.credentials.get({password: true})",
        ):
            with self.subTest(source=source):
                port_path.write_text(source, encoding="utf-8")
                cue["port"]["files"][0] = self._binding(port_path)
                self.assertIn(
                    "gm-001 port contains nondeterministic or remote runtime code",
                    graphic_motion_plan.validate_port(cue, self.root),
                )

    def test_render_requires_complete_rgba_frame_sequence(self):
        plan = copy.deepcopy(self.plan)
        plan["cues"][0]["render"]["frames"].pop()
        errors = graphic_motion_plan.validate_plan(
            plan, self.timeline, project=self.project,
            project_root=self.root, verify_files=True,
        )
        self.assertIn("gm-001 render frames do not match exact frame sequence", errors)

    def test_render_rejects_fake_or_wrong_size_png(self):
        plan = copy.deepcopy(self.plan)
        frame = self.root / plan["cues"][0]["render"]["frames"][0]["path"]
        frame.write_bytes(b"png")
        self.assertIn(
            "gm-001 render frame is not an RGBA PNG at timeline dimensions",
            graphic_motion_plan.validate_plan(
                plan, self.timeline, project=self.project,
                project_root=self.root, verify_files=True,
            ),
        )

        Image.new("RGBA", (8, 8), (0, 0, 0, 0)).save(frame)
        self.assertIn(
            "gm-001 render frame is not an RGBA PNG at timeline dimensions",
            graphic_motion_plan.validate_plan(
                plan, self.timeline, project=self.project,
                project_root=self.root, verify_files=True,
            ),
        )

    def test_transparent_overlay_requires_visible_and_transparent_pixels(self):
        plan = copy.deepcopy(self.plan)
        for binding in plan["cues"][0]["render"]["frames"]:
            Image.new("RGBA", (16, 9), (0, 0, 0, 0)).save(self.root / binding["path"])
        self.assertIn(
            "gm-001 render sequence has no usable alpha",
            graphic_motion_plan.validate_plan(
                plan, self.timeline, project=self.project,
                project_root=self.root, verify_files=True,
            ),
        )

    def test_review_requires_structured_visual_and_hyperframes_evidence(self):
        plan = copy.deepcopy(self.plan)
        plan["cues"][0]["review"]["evidence"] = [
            self._binding(self.root / "review/04-graphic-motion/source-fidelity.png"),
        ]
        errors = graphic_motion_plan.validate_plan(
            plan, self.timeline, project=self.project,
            project_root=self.root, verify_files=True,
        )
        self.assertIn("gm-001 review evidence contract is invalid", errors)

    def test_review_rejects_fake_images_and_check_receipts(self):
        plan = copy.deepcopy(self.plan)
        evidence = plan["cues"][0]["review"]["evidence"]
        (self.root / evidence["composite_middle"]["path"]).write_bytes(b"review")
        (self.root / evidence["hyperframes_check"]["path"]).write_bytes(b"pass")
        errors = graphic_motion_plan.validate_plan(
            plan, self.timeline, project=self.project,
            project_root=self.root, verify_files=True,
        )
        self.assertIn("gm-001 review image is invalid", errors)
        self.assertIn("gm-001 HyperFrames check receipt is invalid", errors)

    def test_review_artifacts_and_snapshot_poses_must_be_distinct(self):
        plan = copy.deepcopy(self.plan)
        cue = plan["cues"][0]
        evidence = cue["review"]["evidence"]
        self.assertEqual(
            [],
            graphic_motion_plan.validate_plan(
                plan, self.timeline, project=self.project,
                project_root=self.root, verify_files=True,
            ),
        )

        shared = evidence["source_fidelity"]
        for key in graphic_motion_plan.REVIEW_IMAGE_KEYS:
            evidence[key] = shared
        for snapshot in evidence["hyperframes_snapshots"]:
            snapshot["file"] = shared
        evidence["hyperframes_snapshots"][2]["at_s"] = 0.8
        self.assertIn(
            "gm-001 review visual evidence must use distinct images",
            graphic_motion_plan._review_evidence_errors(
                "gm-001", evidence, self.root, True, (16, 9), 2.0,
            ),
        )
        self.assertIn(
            "gm-001 HyperFrames snapshot poses or times are invalid",
            graphic_motion_plan._review_evidence_errors(
                "gm-001", evidence, self.root, True, (16, 9), 2.0,
            ),
        )

    def test_human_review_receipt_must_repeat_explicit_user_action(self):
        plan = copy.deepcopy(self.plan)
        review = plan["cues"][0]["review"]
        review["mode"] = "human"
        review["explicit_user_action"] = True
        receipt_path = self.root / review["receipt"]["path"]
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        receipt["mode"] = "human"
        receipt_path.write_text(json.dumps(receipt) + "\n", encoding="utf-8")
        binding = self._binding(receipt_path)
        review["receipt"] = binding
        plan["delivery_bindings"][-1] = binding
        self.assertIn(
            "gm-001 review receipt authority does not match plan",
            graphic_motion_plan.validate_plan(
                plan, self.timeline, project=self.project,
                project_root=self.root, verify_files=True,
            ),
        )

    def test_malformed_nested_values_return_errors(self):
        plan = copy.deepcopy(self.plan)
        plan["cues"][0]["search"] = []
        self.assertIn(
            "gm-001 search receipt is incomplete",
            graphic_motion_plan.validate_plan(plan, self.timeline),
        )

        project = copy.deepcopy(self.project)
        project["operations"].append([])
        self._json("work/project.json", project)
        self.assertIn("finish video-understand first", graphic_motion_plan.validate_prerequisite(self.root))

        errors = []
        projectlib._validate_graphic_motion_plan(
            [], {}, [], self.timeline, errors, self.root, project=self.project,
        )
        self.assertIn("graphic-motion plan must be an object", errors)

    def test_malformed_source_urls_return_errors_instead_of_crashing(self):
        plan = copy.deepcopy(self.plan)
        plan["cues"][0]["source"]["url"] = "https://[::1"
        plan["cues"][0]["search"]["candidates"][0]["url"] = "https://[::1"
        errors = graphic_motion_plan.validate_plan(plan, self.timeline)
        self.assertIn("gm-001 source URLs must use HTTPS", errors)
        self.assertIn("gm-001 selected source URL must name HTML", errors)

    def test_compiler_reports_null_cues_instead_of_crashing(self):
        plan = copy.deepcopy(self.plan)
        plan["cues"] = None
        operation = {
            "id": "graphic-motion",
            "plan_sha256": graphic_motion_plan.canonical_sha256(plan),
            "depends_on": plan["dependencies"],
            "based_on": plan["based_on"],
            "delivery_bindings": plan["delivery_bindings"],
        }
        errors = []
        projectlib._validate_graphic_motion_plan(
            plan, operation, [], self.timeline, errors, self.root,
            project=self.project,
        )
        self.assertIn("graphic-motion cues must be a list", errors)

    def test_malformed_candidate_id_is_reported_instead_of_crashing(self):
        plan = copy.deepcopy(self.plan)
        plan["cues"][0]["search"]["candidates"][0]["id"] = []
        self.assertIn(
            "gm-001 search receipt is incomplete",
            graphic_motion_plan.validate_plan(plan, self.timeline),
        )

    def test_malformed_enum_values_are_reported_instead_of_crashing(self):
        cases = (
            (("search", "candidates", 0, "catalog_id"), "gm-001 search receipt is incomplete"),
            (("search", "candidates", 0, "decision"), "gm-001 search receipt is incomplete"),
            (("source", "catalog_id"), "gm-001 source catalog is not permitted"),
            (("source", "license"), "gm-001 source license is not permitted"),
            (("intent", "compositing_mode"), "gm-001 motion intent is incomplete"),
            (("port", "motion_model"), "gm-001 port composition or motion model is invalid"),
            (("port", "change_categories", 0), "gm-001 change categories are invalid"),
            (("review", "mode"), "gm-001 review receipt is invalid"),
        )
        for keys, message in cases:
            with self.subTest(keys=keys):
                plan = copy.deepcopy(self.plan)
                value = plan["cues"][0]
                for key in keys[:-1]:
                    value = value[key]
                value[keys[-1]] = []
                self.assertIn(message, graphic_motion_plan.validate_plan(plan, self.timeline))

        plan = copy.deepcopy(self.plan)
        plan["decision"]["mode"] = []
        self.assertIn("decision receipt is invalid", graphic_motion_plan.validate_plan(plan, self.timeline))

    def test_malformed_license_fails_closed(self):
        plan = copy.deepcopy(self.plan)
        plan["cues"][0]["source"]["license"] = []
        self.assertIn(
            "gm-001 source license is not permitted",
            graphic_motion_plan.validate_plan(
                plan, self.timeline, project=self.project,
                project_root=self.root, verify_files=True,
            ),
        )

    def test_malformed_review_bindings_fail_closed(self):
        for key in ("path", "sha256"):
            with self.subTest(key=key):
                plan = copy.deepcopy(self.plan)
                plan["cues"][0]["review"]["evidence"]["source_fidelity"][key] = []
                self.assertIn(
                    "gm-001 review image binding is invalid",
                    graphic_motion_plan.validate_plan(
                        plan, self.timeline, project=self.project,
                        project_root=self.root, verify_files=True,
                    ),
                )

    def test_malformed_input_hashes_are_reported_instead_of_crashing(self):
        plan = copy.deepcopy(self.plan)
        plan["input_hashes"] = []
        self.assertIn(
            "input evidence binding is invalid",
            graphic_motion_plan.validate_plan(plan, self.timeline),
        )

    def test_malformed_cue_file_lists_are_reported_instead_of_crashing(self):
        plan = copy.deepcopy(self.plan)
        plan["cues"][0]["source"]["files"] = None
        self.assertIn(
            "gm-001 source files are required",
            graphic_motion_plan.validate_plan(plan, self.timeline),
        )

    def test_malformed_frame_list_is_reported_instead_of_crashing(self):
        plan = copy.deepcopy(self.plan)
        plan["cues"][0]["render"]["frames"] = [None]
        self.assertIn(
            "gm-001 render frames do not match exact frame sequence",
            graphic_motion_plan.validate_plan(plan, self.timeline),
        )

    def test_shipped_report_covers_prior_art_and_catalog_evidence(self):
        report = (ROOT / "reference/source-catalog.md").read_text(encoding="utf-8")
        for phrase in (
            "Prior Art",
            "motion-anything",
            "html-video",
            "transitions.dev",
            "iart-ai/motion-skills",
            "71,539",
            "11,687",
            "HyperFrames",
            "https://github.com/nexu-io/motion-anything",
            "https://github.com/juliangarnier/anime",
            "https://github.com/uiverse-io/galaxy",
            "https://github.com/codrops",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, report)

    def test_skill_requires_agent_search_and_high_craft_sources(self):
        skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("Do not ask the user to find candidates", skill)
        self.assertIn("high-craft", skill)
        self.assertIn("hyperframes-keyframes", skill)
        self.assertIn("only before\nsource selection", skill)
        self.assertIn("Load the selected runtime's `hyperframes-animation` adapter", skill)

    def test_shipped_hyperframes_port_fixture_declares_seekable_rgba_contract(self):
        fixture = ROOT / "examples/hyperframes-port/index.html"
        self.assertTrue(fixture.is_file())
        html = fixture.read_text(encoding="utf-8")
        self.assertIn('data-composition-id="graphic-motion-port-fixture"', html)
        self.assertIn("data-no-timeline", html)
        self.assertIn('data-fps="30000/1001"', html)
        self.assertIn('id="signal-field"', html)
        self.assertIn("animation-iteration-count: 1", html)
        self.assertNotIn("http://", html)
        self.assertNotIn("https://", html)

    def test_shipped_example_matches_current_evidence_contract(self):
        example = json.loads(
            (ROOT / "examples/example-graphic-motion-plan.json").read_text(encoding="utf-8")
        )
        self.assertEqual(
            [
                "work/timeline.json",
                "work/understand/transcript.json",
                "work/understand/understanding.json",
                "work/understand/media.json",
                "review/00-video-understanding/contact-sheet.jpg",
            ],
            [binding["path"] for binding in example["delivery_bindings"][:5]],
        )
        cue = example["cues"][0]
        self.assertEqual(2, example["schema_version"])
        self.assertEqual(
            example["input_hashes"]["contact_sheet_sha256"],
            cue["evidence"]["visual_refs"][0]["sha256"],
        )
        self.assertEqual(
            cue["source"]["candidate_id"],
            cue["search"]["selected_candidate_id"],
        )
        self.assertEqual(2, len(cue["search"]["candidates"]))
        self.assertIn(cue["source"]["license_file"], cue["source"]["files"])
        self.assertIn(cue["source"]["preview"], cue["source"]["files"])
        self.assertEqual(
            cue["source"]["preview"],
            cue["review"]["evidence"]["source_fidelity_inputs"]["source_preview"],
        )
        self.assertIn("/recipes/signal/LICENSE", cue["source"]["license_url"])
        self.assertEqual(12, len(cue["render"]["frames"]))
        self.assertEqual(
            {
                *graphic_motion_plan.REVIEW_IMAGE_KEYS,
                "hyperframes_check", "hyperframes_snapshots", "source_fidelity_inputs",
            },
            set(cue["review"]["evidence"]),
        )
        evidence = cue["review"]["evidence"]
        snapshots = evidence["hyperframes_snapshots"]
        self.assertEqual(list(graphic_motion_plan.SNAPSHOT_POSES), [item["pose"] for item in snapshots])
        self.assertEqual(sorted(item["at_s"] for item in snapshots), [item["at_s"] for item in snapshots])
        visual_bindings = [
            *[evidence[key] for key in graphic_motion_plan.REVIEW_IMAGE_KEYS],
            *[item["file"] for item in snapshots],
        ]
        self.assertEqual(8, len({item["path"] for item in visual_bindings}))
        self.assertEqual(8, len({item["sha256"] for item in visual_bindings}))

    def test_all_skipped_plan_is_a_valid_noop(self):
        plan = copy.deepcopy(self.plan)
        plan["cues"] = [{
            "id": "gm-001", "status": "skipped",
            "program_range": {"start_s": 1.0, "end_s": 3.0},
            "skip_reason": "No exact permissively licensed source matched the intent.",
        }]
        plan["delivery_bindings"] = copy.deepcopy(self.plan["delivery_bindings"][:5])
        self.assertEqual([], graphic_motion_plan.validate_plan(plan, self.timeline, project=self.project))
        self.assertEqual(self.project, graphic_motion_plan.register_operation(self.project, plan, self.timeline, self.root))

    def test_compiler_hook_rejects_plan_or_bound_file_mutation(self):
        registered = graphic_motion_plan.register_operation(self.project, self.plan, self.timeline, self.root)
        operation = next(item for item in registered["operations"] if item.get("id") == "graphic-motion")
        errors = []
        projectlib._validate_graphic_motion_plan(
            self.plan, operation, operation["render"], self.timeline, errors, self.root,
        )
        self.assertEqual([], errors)

        changed = copy.deepcopy(self.plan)
        changed["decision"]["rationale"] = "mutated"
        errors = []
        projectlib._validate_graphic_motion_plan(
            changed, operation, operation["render"], self.timeline, errors, self.root,
        )
        self.assertIn("graphic-motion plan SHA-256 is stale", errors)

        bound_path = self.root / next(
            item["path"] for item in self.plan["delivery_bindings"]
            if item["path"].endswith("original.html")
        )
        bound_path.write_bytes(b"mutated")
        errors = []
        projectlib._validate_graphic_motion_plan(
            self.plan, operation, operation["render"], self.timeline, errors, self.root,
        )
        self.assertIn("graphic-motion bound file SHA-256 is stale", errors)

    def test_build_render_plan_rejects_mutated_bound_file(self):
        (self.root / "input").mkdir()
        (self.root / "final").mkdir()
        (self.root / "work/render").mkdir()
        source = self._file("input/source.mp4", b"source")
        self._file("review/04-graphic-motion/graphic-motion-summary.md", b"verified")
        plan = copy.deepcopy(self.plan)
        plan["dependencies"] = ["understanding"]
        plan["based_on"] = {"understanding": 1}
        project = {
            "schema_version": 1,
            "project_id": "graphic-motion-fixture",
            "source": {
                "path": "../input/source.mp4",
                "fingerprint": {
                    "size": source.stat().st_size,
                    "modified_ns": source.stat().st_mtime_ns,
                    "duration_s": 8.0,
                },
            },
            "active_sequence": "main",
            "sequences": {"main": {"timeline": "timeline.json", "operations": []}},
            "operations": [copy.deepcopy(self.project["operations"][0])],
            "render": {
                "plan": "render/render-plan.json",
                "output": "../final/final-video.mp4",
                "status": "draft",
            },
            "reviews": [],
        }
        project = graphic_motion_plan.register_operation(project, plan, self.timeline, self.root)
        self._json("work/graphic-motion/graphic-motion-plan.json", plan)
        compiled = projectlib.build_render_plan(project, self.root)
        self.assertEqual("graphic-motion", compiled["contributions"][0]["operation"])

        bound_path = self.root / next(
            item["path"] for item in plan["delivery_bindings"]
            if item["path"].endswith("understanding.json")
        )
        bound_path.write_text('{"schema_version":1,"summary":"mutated"}\n', encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "graphic-motion bound file SHA-256 is stale"):
            projectlib.build_render_plan(project, self.root)

        operation = next(item for item in project["operations"] if item.get("id") == "graphic-motion")
        operation["skill"] = "renamed-skill"
        with self.assertRaises(ValueError) as caught:
            projectlib.build_render_plan(project, self.root)
        self.assertIn("graphic-motion operation skill is invalid", str(caught.exception))
        self.assertIn("graphic-motion bound file SHA-256 is stale", str(caught.exception))

        operation["id"] = "renamed-motion"
        operation["skill"] = "video-add-graphic-motion"
        project["sequences"]["main"]["operations"] = ["renamed-motion"]
        with self.assertRaises(ValueError) as caught:
            projectlib.build_render_plan(project, self.root)
        self.assertIn("renamed-motion operation id is invalid", str(caught.exception))
        self.assertIn("renamed-motion bound file SHA-256 is stale", str(caught.exception))

    def test_build_render_plan_rejects_noncanonical_pixel_order(self):
        (self.root / "input").mkdir()
        (self.root / "final").mkdir()
        (self.root / "work/render").mkdir()
        source = self._file("input/source.mp4", b"source")
        self._file("review/04-graphic-motion/graphic-motion-summary.md", b"verified")
        plan = copy.deepcopy(self.plan)
        plan["dependencies"] = ["understanding", "b-roll"]
        plan["based_on"] = {"understanding": 1, "b-roll": 2}
        broll = self._operation("b-roll", 2)
        broll.update({
            "skill": "fixture-b-roll",
            "depends_on": ["understanding"],
            "based_on": {"understanding": 1},
            "render": {"kind": "output-constraint"},
        })
        project = {
            "schema_version": 1,
            "project_id": "graphic-motion-order-fixture",
            "source": {
                "path": "../input/source.mp4",
                "fingerprint": {
                    "size": source.stat().st_size,
                    "modified_ns": source.stat().st_mtime_ns,
                    "duration_s": 8.0,
                },
            },
            "active_sequence": "main",
            "sequences": {"main": {"timeline": "timeline.json", "operations": ["b-roll"]}},
            "operations": [copy.deepcopy(self.project["operations"][0]), broll],
            "render": {
                "plan": "render/render-plan.json",
                "output": "../final/final-video.mp4",
                "status": "draft",
            },
            "reviews": [],
        }
        project = graphic_motion_plan.register_operation(project, plan, self.timeline, self.root)
        self._json("work/graphic-motion/graphic-motion-plan.json", plan)
        project["sequences"]["main"]["operations"] = ["graphic-motion", "b-roll"]
        with self.assertRaisesRegex(ValueError, "canonical pixel order"):
            projectlib.build_render_plan(project, self.root)


if __name__ == "__main__":
    unittest.main()
