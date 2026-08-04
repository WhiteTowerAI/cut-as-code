"""Graphic-motion recipe plan and Project Protocol tests."""

import copy
import hashlib
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "scripts"), str(ROOT.parent / "video-understand" / "scripts")]

import graphic_motion_plan
import projectlib


class GraphicMotionPlanTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        for directory in (
            "work/understand",
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
            "fps": {"num": 10, "den": 1},
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
        self.media = {
            "schema_version": 1,
            "duration_s": 8.0,
            "width": 16,
            "height": 9,
            "fps": {"num": 10, "den": 1},
        }
        self.analysis = {
            "schema_version": 1,
            "timeline_id": "source",
            "speech": {"duration_s": 8.0},
            "moments": [],
        }
        self.understanding = {"schema_version": 1, "summary": "A signal becomes visible."}
        self._json("work/timeline.json", self.timeline)
        self._json("work/understand/media.json", self.media)
        self._json("work/understand/transcript.json", self.transcript)
        self._json("work/understand/analysis.json", self.analysis)
        self._json("work/understand/understanding.json", self.understanding)
        for name in ("contact-sheet.jpg", "transcript.srt", "video-summary.md"):
            self._file(f"review/00-video-understanding/{name}", name.encode())

        self.project = {
            "schema_version": 1,
            "active_sequence": "main",
            "sequences": {"main": {"timeline": "timeline.json", "operations": [
                "cut", "b-roll", "content-cards", "captions",
            ]}},
            "operations": [
                {
                    "id": "understanding",
                    "skill": "video-understand",
                    "revision": 1,
                    "status": "verified",
                    "depends_on": [],
                    "based_on": {},
                    "target": {"sequence": "main", "scope": "understanding"},
                    "effects": {
                        "changes_timeline": False,
                        "changes_geometry": False,
                        "changes_video_pixels": False,
                        "changes_audio": False,
                    },
                    "check": {
                        "status": "pass",
                        "report": "../review/00-video-understanding/video-summary.md",
                    },
                },
                self._operation("cut", 2),
                self._operation("b-roll", 3),
                self._operation("content-cards", 4),
                self._operation("captions", 5),
            ],
            "render": {"status": "verified"},
        }
        self._json("work/project.json", self.project)
        self.plan = self._make_plan()

    def tearDown(self):
        self.temp.cleanup()

    def _file(self, relative, payload):
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(payload)
        return path

    def _json(self, relative, value):
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value) + "\n", encoding="utf-8")
        return path

    def _image(self, relative, color, *, rgba=False):
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        mode = "RGBA" if rgba else "RGB"
        image = Image.new(mode, (16, 9), color)
        if rgba:
            image.putpixel((8, 4), (255, 255, 255, 192))
        image.save(path)
        return path

    def _source_fidelity(self, relative, source_path, port_path):
        path = self.root / relative
        with Image.open(source_path) as source_image, Image.open(port_path) as port_image:
            source = source_image.convert("RGB")
            port = port_image.convert("RGB")
            image = Image.new("RGB", (source.width + port.width, 9), "black")
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

    @staticmethod
    def _digest(path):
        return hashlib.sha256(path.read_bytes()).hexdigest()

    def _binding(self, path):
        return {"path": path.relative_to(self.root).as_posix(), "sha256": self._digest(path)}

    def _materialize_recipe(self):
        recipe_dir = ROOT / "recipes" / "web" / "decrypted-text"
        target = self.root / "work/cache/graphic-motion/hyperframes/gm-001"
        shutil.rmtree(target)
        shutil.copytree(recipe_dir / "hyperframes", target)
        shutil.copy2(recipe_dir / "recipe.motion.yaml", target / "recipe.motion.yaml")
        files = [self._binding(path) for path in sorted(target.rglob("*")) if path.is_file()]
        by_name = {Path(binding["path"]).name: binding for binding in files}
        return {
            "id": "decrypted-text",
            "composition_id": "decrypted-text",
            "manifest": by_name["recipe.motion.yaml"],
            "conversion_receipt": by_name["conversion.json"],
            "files": files,
        }

    def _make_plan(self):
        contact_sheet = self.root / "review/00-video-understanding/contact-sheet.jpg"
        mapped_word = projectlib.map_transcript_to_timeline(
            self.transcript, self.timeline,
        )["segments"][0]["words"][0]
        recipe = self._materialize_recipe()
        adaptation_files = [
            self._file(
                "work/cache/graphic-motion/adapted/gm-001/index.html",
                b'<div data-composition-id="gm-001">ORDERED SIGNAL</div>',
            ),
            self._file(
                "work/cache/graphic-motion/adapted/gm-001/motion.js",
                b"/* Preserve the recipe's scramble-to-clear choreography. */",
            ),
        ]
        adaptation = {
            "composition_id": "gm-001",
            "entry": self._binding(adaptation_files[0]),
            "files": [self._binding(path) for path in adaptation_files],
            "changes": {
                "content": "Replace demo copy with the spoken concept.",
                "layout": "Anchor the phrase in the shot's negative space.",
                "scale": "Use video-scale typography.",
                "palette": "Match the source's cool industrial neutrals.",
                "timing": "Land the decode on the word signal.",
                "choreography": "Add build, readable hold, and decisive resolve phases.",
            },
            "preserved_recipe_features": ["scramble-to-clear text progression"],
            "rationale": "The recipe supplies the decode mechanic while the shot determines the design.",
        }
        frames = [
            self._image(
                f"work/cache/graphic-motion/rendered/gm-001/frame_{index:06d}.png",
                (0, 0, 0, 0),
                rgba=True,
            )
            for index in range(1, 21)
        ]
        source_preview = self._image("review/04-graphic-motion/recipe-preview.png", (20, 30, 40))
        base_recipe_snapshot = self._image(
            "review/04-graphic-motion/base-recipe-snapshot.png", (35, 25, 15),
        )
        snapshots = [
            self._image(f"review/04-graphic-motion/snapshot-{index}.png", (index * 20, 10, 10))
            for index in range(1, 5)
        ]
        evidence = {
            "source_fidelity": self._binding(self._source_fidelity(
                "review/04-graphic-motion/source-fidelity.png", source_preview, base_recipe_snapshot,
            )),
            "adaptation_fidelity": self._binding(self._source_fidelity(
                "review/04-graphic-motion/adaptation-fidelity.png", base_recipe_snapshot, snapshots[1],
            )),
            "composite_first": self._binding(self._image(
                "review/04-graphic-motion/composite-first.png", (10, 20, 30),
            )),
            "composite_middle": self._binding(self._image(
                "review/04-graphic-motion/composite-middle.png", (30, 20, 10),
            )),
            "composite_last": self._binding(self._image(
                "review/04-graphic-motion/composite-last.png", (40, 50, 60),
            )),
            "hyperframes_check": self._binding(self._json(
                "review/04-graphic-motion/hyperframes-check.json",
                {"status": "pass", "composition_id": "gm-001"},
            )),
            "hyperframes_snapshots": [
                {"pose": pose, "at_s": at_s, "file": self._binding(path)}
                for pose, at_s, path in zip(
                    graphic_motion_plan.SNAPSHOT_POSES,
                    (0.2, 0.8, 1.5, 1.8),
                    snapshots,
                )
            ],
            "source_fidelity_inputs": {
                "source_preview": self._binding(source_preview),
                "port_snapshot": self._binding(base_recipe_snapshot),
                "normalized_time": 0.4,
            },
            "adaptation_fidelity_inputs": {
                "base_snapshot": self._binding(base_recipe_snapshot),
                "adapted_snapshot": self._binding(snapshots[1]),
            },
        }
        review = {
            "status": "approved",
            "mode": "agent",
            "actor": "test-agent",
            "rationale": "The converted recipe preserves its decode choreography and reads over final pixels.",
            "aesthetic_review": {
                "semantic_clarity": "The silent frame reads as a signal becoming ordered.",
                "composition": "The headline is anchored in clear negative space with a supporting data rule.",
                "readability": "The final phrase remains legible at normal playback size.",
                "motion_quality": "The build accelerates into a stable hold and exits without a pop.",
                "footage_integration": "Scale, color, and placement follow the industrial interview frame.",
            },
            "evidence": evidence,
        }
        review["receipt"] = self._binding(self._json(
            "review/04-graphic-motion/review.json", review,
        ))
        cue = {
            "id": "gm-001",
            "status": "verified",
            "program_range": {"start_s": 1.0, "end_s": 3.0},
            "source_ranges": [{"clip_id": "clip-001", "start_s": 1.0, "end_s": 3.0}],
            "intent": {
                "authored_at": "2026-08-03T00:00:00Z",
                "content": "An abstract signal becomes ordered.",
                "purpose": "Make the signal transformation concrete.",
                "motion_family": "decode reveal",
                "interaction_model": "finite activation",
                "timing_rationale": "The cue begins on signal and resolves before the next idea.",
                "compositing_mode": "transparent-overlay",
                "recipe_queries": ["technical text decode signal"],
            },
            "evidence": {
                "transcript_words": [mapped_word],
                "visual_refs": [{
                    "path": "review/00-video-understanding/contact-sheet.jpg",
                    "sha256": self._digest(contact_sheet),
                    "note": "The center-safe region is clear during the cue.",
                }],
            },
            "selection": {
                "query": "technical text decode signal",
                "shortlist": [
                    {
                        "recipe_id": "decrypted-text",
                        "score": 24,
                        "matched_fields": ["name", "description", "tags", "intent_keywords"],
                    },
                    {
                        "recipe_id": "count-up",
                        "score": 7,
                        "matched_fields": ["description"],
                    },
                ],
                "chosen_recipe_id": "decrypted-text",
                "agent_rationale": "The decode motion directly explains the ordered signal.",
                "field_evidence": {
                    "name": "The name identifies the exact decode treatment.",
                    "description": "The described scramble-to-text action matches the cue.",
                    "category": "Text kinetic fits a spoken technical term.",
                    "tags": "Decode, scramble, and techy match the intended action.",
                    "intent_keywords": "The manifest keywords match a decode reveal.",
                    "best_for": "This is a short technical label.",
                    "avoid_when": "This is not body copy or a calm luxury segment.",
                },
                "avoid_when_review": "No avoid_when condition applies to the cue or its footage.",
            },
            "recipe": recipe,
            "adaptation": adaptation,
            "render": {
                "kind": "overlay",
                "asset": "cache/graphic-motion/rendered/gm-001",
                "asset_type": "image-sequence",
                "pattern": "frame_%06d.png",
                "start_number": 1,
                "fps": {"num": 10, "den": 1},
                "start_s": 1.0,
                "duration_s": 2.0,
                "frames": [self._binding(path) for path in frames],
            },
            "review": review,
        }
        inputs = [
            self._binding(self.root / "work/timeline.json"),
            self._binding(self.root / "work/understand/transcript.json"),
            self._binding(self.root / "work/understand/understanding.json"),
            self._binding(self.root / "work/understand/media.json"),
            self._binding(contact_sheet),
        ]
        return {
            "schema_version": 3,
            "authoring_mode": "recipe-adaptation",
            "timeline_id": "main",
            "timebase": "program",
            "program_duration_s": 8.0,
            "fps": {"num": 10, "den": 1},
            "dependencies": ["understanding", "cut", "b-roll"],
            "based_on": {"understanding": 1, "cut": 2, "b-roll": 3},
            "input_hashes": {
                "timeline_sha256": inputs[0]["sha256"],
                "transcript_sha256": inputs[1]["sha256"],
                "understanding_sha256": inputs[2]["sha256"],
                "media_sha256": inputs[3]["sha256"],
                "contact_sheet_sha256": inputs[4]["sha256"],
            },
            "decision": {
                "mode": "agent",
                "actor": "test-agent",
                "rationale": "The signal explanation benefits from one selective motion cue.",
            },
            "delivery_bindings": [*inputs, *graphic_motion_plan._cue_bindings(cue)],
            "cues": [cue],
        }

    def test_requires_completed_video_understand(self):
        self.assertEqual([], graphic_motion_plan.validate_prerequisite(self.root))
        project = copy.deepcopy(self.project)
        project["operations"][0]["status"] = "draft"
        self._json("work/project.json", project)
        self.assertIn("finish video-understand first", graphic_motion_plan.validate_prerequisite(self.root))

    def test_validates_and_registers_local_recipe_overlay(self):
        self.assertEqual([], graphic_motion_plan.validate_plan(
            self.plan, self.timeline, project=self.project,
            project_root=self.root, verify_files=True,
        ))
        registered = graphic_motion_plan.register_operation(
            self.project, self.plan, self.timeline, self.root,
        )
        self.assertEqual(
            ["cut", "b-roll", "graphic-motion", "content-cards", "captions"],
            registered["sequences"]["main"]["operations"],
        )
        operation = next(item for item in registered["operations"] if item.get("id") == "graphic-motion")
        self.assertEqual("video-add-graphic-motion", operation["skill"])
        self.assertEqual(self.plan["cues"][0]["render"], operation["render"][0])

    def test_rejects_schema_v2_non_recipe_ids_and_incomplete_agent_judgment(self):
        plan = copy.deepcopy(self.plan)
        plan["schema_version"] = 2
        self.assertIn(
            "plan schema_version must be 3; regenerate schema v2 plans",
            graphic_motion_plan.validate_plan(plan, self.timeline),
        )
        plan = copy.deepcopy(self.plan)
        plan["cues"][0]["recipe"]["id"] = "not-local"
        plan["cues"][0]["selection"]["chosen_recipe_id"] = "not-local"
        self.assertIn(
            "gm-001 recipe is not in the local motion-anything library",
            graphic_motion_plan.validate_plan(plan, self.timeline),
        )
        plan = copy.deepcopy(self.plan)
        plan["cues"][0]["selection"]["field_evidence"].pop("avoid_when")
        self.assertIn(
            "gm-001 recipe selection must assess all seven manifest fields",
            graphic_motion_plan.validate_plan(plan, self.timeline),
        )

    def test_materialized_recipe_is_complete_and_matches_preconverted_library(self):
        plan = copy.deepcopy(self.plan)
        recipe = plan["cues"][0]["recipe"]
        recipe["files"].pop()
        self.assertIn(
            "gm-001 materialized recipe file set is incomplete",
            graphic_motion_plan.validate_plan(
                plan, self.timeline, project=self.project,
                project_root=self.root, verify_files=True,
            ),
        )
        plan = copy.deepcopy(self.plan)
        index = next(item for item in plan["cues"][0]["recipe"]["files"] if item["path"].endswith("index.html"))
        (self.root / index["path"]).write_text("mutated", encoding="utf-8")
        errors = graphic_motion_plan.validate_plan(
            plan, self.timeline, project=self.project,
            project_root=self.root, verify_files=True,
        )
        self.assertIn("gm-001 materialized recipe file SHA-256 is stale", errors)

    def test_rejects_stale_or_incomplete_project_adaptation(self):
        plan = copy.deepcopy(self.plan)
        plan["cues"][0]["adaptation"]["changes"].pop("layout")
        self.assertIn(
            "gm-001 adaptation must document all six project-level changes",
            graphic_motion_plan.validate_plan(plan, self.timeline),
        )

        plan = copy.deepcopy(self.plan)
        index = self.root / plan["cues"][0]["adaptation"]["entry"]["path"]
        index.write_text("mutated", encoding="utf-8")
        self.assertIn(
            "gm-001 adaptation file SHA-256 is stale",
            graphic_motion_plan.validate_plan(
                plan, self.timeline, project=self.project,
                project_root=self.root, verify_files=True,
            ),
        )

    def test_timing_evidence_dependencies_and_frames_fail_closed(self):
        plan = copy.deepcopy(self.plan)
        plan["fps"] = {"num": 24, "den": 1}
        plan["based_on"]["cut"] = 99
        plan["cues"][0]["source_ranges"][0]["start_s"] = 2.0
        plan["cues"][0]["render"]["frames"].pop()
        errors = graphic_motion_plan.validate_plan(plan, self.timeline, project=self.project)
        self.assertIn("plan fps does not match timeline", errors)
        self.assertIn("plan based_on does not match current revisions", errors)
        self.assertIn("gm-001 source_ranges do not match timeline", errors)
        self.assertIn("gm-001 render frames do not match exact frame sequence", errors)

    def test_review_requires_real_fidelity_pixels_and_matching_check_receipt(self):
        fidelity = self.root / self.plan["cues"][0]["review"]["evidence"]["source_fidelity"]["path"]
        Image.new("RGB", (32, 9), "white").save(fidelity)
        errors = graphic_motion_plan.validate_plan(
            self.plan, self.timeline, project=self.project,
            project_root=self.root, verify_files=True,
        )
        self.assertIn("gm-001 review image SHA-256 is stale", errors)
        self.assertIn("gm-001 source fidelity comparison does not match bound pixels", errors)

    def test_all_skipped_plan_is_a_valid_noop(self):
        plan = copy.deepcopy(self.plan)
        plan["cues"] = [{
            "id": "gm-001",
            "status": "skipped",
            "program_range": {"start_s": 1.0, "end_s": 3.0},
            "skip_reason": "No recipe fits the cue without obscuring the speaker.",
        }]
        plan["delivery_bindings"] = plan["delivery_bindings"][:5]
        self.assertEqual([], graphic_motion_plan.validate_plan(plan, self.timeline, project=self.project))
        self.assertEqual(
            self.project,
            graphic_motion_plan.register_operation(self.project, plan, self.timeline, self.root),
        )

    def test_compiler_rechecks_plan_and_bound_files(self):
        registered = graphic_motion_plan.register_operation(
            self.project, self.plan, self.timeline, self.root,
        )
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

    def test_skill_documents_recipe_only_selection_contract(self):
        skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        reference = (ROOT / "reference/recipe-selection.md").read_text(encoding="utf-8")
        combined = f"{skill}\n{reference}"
        for field in graphic_motion_plan.SELECTION_FIELDS:
            self.assertIn(field, combined)
        self.assertIn("recipe_library.mjs search", combined)
        self.assertIn("recipe_library.mjs materialize", combined)
        self.assertIn("recipe_library.mjs bind-adaptation", combined)
        self.assertIn("recipe-adaptation", combined)
        self.assertIn("semantic_clarity", combined)
        self.assertFalse((ROOT / "reference" / ("source" + "-catalog.md")).exists())
        self.assertNotIn("Search only the catalog", combined)


if __name__ == "__main__":
    unittest.main()
