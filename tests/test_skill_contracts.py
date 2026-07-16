import hashlib
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
GIT_SECTION_SHA256 = "f1731ab590f3093e8082a496f0e9f5e66e5298ed6d627e5828a1bc349f3800ad"


def text(path):
    return (ROOT / path).read_text(encoding="utf-8")


def git_section_hash(path):
    data = (ROOT / path).read_bytes()
    section = data[data.index(b"## Git") : data.index(b"## What this repo is")]
    return hashlib.sha256(section).hexdigest()


class SkillContractTests(unittest.TestCase):
    def test_documented_protocol_scripts_exist(self):
        paths = [
            "skills/video-understand/scripts/probe.py",
            "skills/video-understand/scripts/transcribe.py",
            "skills/video-understand/scripts/analyze.py",
            "skills/video-understand/scripts/validate.py",
            "skills/video-understand/scripts/build_timeline.py",
            "skills/video-understand/scripts/build_render_plan.py",
            "skills/video-understand/scripts/render_project.py",
            "skills/video-understand/scripts/init_project.py",
            "skills/video-rough-cut/scripts/build_edit.py",
            "skills/video-rough-cut/scripts/cut_render.py",
            "skills/video-add-content-cards/scripts/build_cards_plan.py",
            "skills/video-color-grade/scripts/gradelib.py",
            "skills/video-edit-compare/scripts/make_compare.py",
        ]
        for path in paths:
            self.assertTrue((ROOT / path).is_file(), path)

    def test_all_skill_python_script_references_resolve(self):
        pattern = re.compile(r"(?:skills/|\.\./|scripts/)[A-Za-z0-9_()/.\-]+\.py")
        for skill_file in (ROOT / "skills").glob("*/SKILL.md"):
            for reference in pattern.findall(skill_file.read_text(encoding="utf-8")):
                path = ROOT / reference if reference.startswith("skills/") else skill_file.parent / reference
                self.assertTrue(path.resolve().is_file(), f"{skill_file}: {reference}")

    def test_content_cards_uses_shared_understanding_not_legacy_analyzer(self):
        skill = text("skills/video-add-content-cards/SKILL.md")
        self.assertNotIn("video-to-remotion(legacy)/scripts/analyze_content.py", skill)
        self.assertIn("work/understand/understanding.json", skill)
        self.assertIn("scripts/build_cards_plan.py", skill)
        self.assertIn("work/content-cards/cards-plan.json", skill)
        self.assertIn("24000/1001", skill)
        self.assertIn("face_clearance", skill)
        self.assertIn('"render"', skill)

    def test_rough_cut_documents_canonical_timeline_and_legacy_adapter(self):
        skill = text("skills/video-rough-cut/SKILL.md")
        self.assertIn("work/rough-cut/edit-plan.json", skill)
        self.assertIn("work/timeline.json", skill)
        self.assertIn("video-understand/scripts/build_timeline.py", skill)
        self.assertIn("compatibility", skill.lower())

    def test_color_grade_documents_canonical_plan_and_human_choice(self):
        skill = text("skills/video-color-grade/SKILL.md")
        self.assertIn("work/color-grade/grade-plan.json", skill)
        self.assertIn("selected_look", skill)
        self.assertIn("base-video", skill)
        self.assertIn("looks.json", skill)
        self.assertIn("selection_mode", skill)
        self.assertIn("selection_rationale", skill)
        self.assertIn("selected-color-look.cube", skill)

    def test_compare_documents_only_source_time_mode(self):
        skill = text("skills/video-edit-compare/SKILL.md")
        self.assertIn("original-vs-final-source-time", skill)
        self.assertIn("TIMELINE.json SOURCE.mp4 FINAL.mp4 OUT.mp4", skill)
        self.assertNotIn("edit_final.json", skill)
        self.assertIn("work/edit-compare/compare-plan.json", skill)
        self.assertIn("comparison-summary.md", skill)

    def test_understanding_documents_protocol_review_names_and_project_cache(self):
        skill = text("skills/video-understand/SKILL.md")
        self.assertIn("contact-sheet.jpg", skill)
        self.assertIn("--cache-dir", skill)
        self.assertIn("--lang auto", skill)

    def test_repository_docs_describe_v1_project_model(self):
        for path in ("README.md", "AGENTS.md", "CLAUDE.md"):
            document = text(path)
            self.assertIn("video-understand", document, path)
            self.assertIn("project.json", document, path)
            self.assertIn("timeline.json", document, path)
            self.assertIn("revision", document, path)
            self.assertIn("optional", document.lower(), path)

    def test_agents_documents_full_shared_protocol_contract(self):
        for path in ("AGENTS.md", "CLAUDE.md"):
            document = text(path)
            self.assertIn("[start_s, end_s)", document, path)
            self.assertIn("target", document, path)
            self.assertIn("effects", document, path)
            for kind in (
                "timeline-transform", "video-filter", "audio-filter", "overlay",
                "precomputed-asset", "output-constraint",
            ):
                self.assertIn(kind, document, path)
            self.assertIn("short preview", document.lower(), path)
            self.assertIn("compatibility", document.lower(), path)

    def test_initialization_is_documented(self):
        self.assertIn("init_project.py", text("README.md"))
        self.assertIn("init_project.py", text("skills/video-understand/SKILL.md"))

    def test_readme_has_real_skill_list_without_placeholders(self):
        readme = text("README.md")
        self.assertNotIn("XXX", readme)
        for skill in (
            "video-understand", "video-rough-cut", "video-color-grade",
            "video-add-content-cards", "video-edit-compare",
        ):
            self.assertIn(f"`{skill}`", readme)

    def test_protected_git_sections_are_byte_identical(self):
        self.assertEqual(GIT_SECTION_SHA256, git_section_hash("AGENTS.md"))
        self.assertEqual(GIT_SECTION_SHA256, git_section_hash("CLAUDE.md"))


if __name__ == "__main__":
    unittest.main()
