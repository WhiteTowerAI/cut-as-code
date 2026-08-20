import importlib.util
import json
import threading
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory


SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
APPLY_PATH = SCRIPTS / "apply_cards_review.py"
spec = importlib.util.spec_from_file_location("apply_cards_review", APPLY_PATH)
apply_cards_review = importlib.util.module_from_spec(spec)
spec.loader.exec_module(apply_cards_review)


class ApplyCardsReviewLeaseTests(unittest.TestCase):
    def test_cli_keeps_authoritative_plan_lease_through_review_validation(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            plan = root / "work" / "content-cards" / "cards-plan.json"
            plan.parent.mkdir(parents=True)
            plan.write_text(json.dumps({"brief": {"theme": "air"}, "cards": []}), encoding="utf-8")
            review = root / "review.json"
            review.write_text(json.dumps({"schema_version": 1, "cards": []}), encoding="utf-8")
            ready_to_write = threading.Event()
            continue_write = threading.Event()
            completed = threading.Event()
            errors = []
            original_write = apply_cards_review.write_json_atomic

            def pause_before_write(*args, **kwargs):
                ready_to_write.set()
                self.assertTrue(continue_write.wait(timeout=2))

            apply_cards_review.write_json_atomic = pause_before_write
            try:
                def run_cli():
                    try:
                        apply_cards_review.main([str(plan), str(review)])
                    except BaseException as error:
                        errors.append(error)
                    finally:
                        completed.set()

                writer = threading.Thread(
                    target=run_cli
                )
                writer.start()
                self.assertTrue(ready_to_write.wait(timeout=2))
                lease = apply_cards_review.build_cards_plan.projectlib.acquire_project_lease(
                    root, blocking=False
                )
                try:
                    self.assertIsNone(lease)
                finally:
                    if lease is not None:
                        apply_cards_review.build_cards_plan.projectlib.release_project_lease(lease)
                    continue_write.set()
                    writer.join(timeout=2)
                self.assertTrue(completed.is_set())
                self.assertFalse(writer.is_alive())
                self.assertEqual([], errors)
            finally:
                apply_cards_review.write_json_atomic = original_write

    def test_authoritative_replace_keeps_shared_lease_until_completion(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            plan = root / "work" / "content-cards" / "cards-plan.json"
            plan.parent.mkdir(parents=True)
            plan.write_text(json.dumps({"cards": []}), encoding="utf-8")
            staged = threading.Event()
            continue_replace = threading.Event()
            finished = threading.Event()
            errors = []
            original_replace = apply_cards_review.os.replace

            def pause_before_authoritative_replace(source, destination):
                if Path(destination).resolve() == plan.resolve():
                    staged.set()
                    self.assertTrue(continue_replace.wait(timeout=2))
                return original_replace(source, destination)

            apply_cards_review.os.replace = pause_before_authoritative_replace
            try:
                def write_plan():
                    try:
                        apply_cards_review.write_json_atomic(plan, {"cards": ["approved"]})
                    except BaseException as error:
                        errors.append(error)
                    finally:
                        finished.set()

                writer = threading.Thread(
                    target=write_plan
                )
                writer.start()
                self.assertTrue(staged.wait(timeout=2))
                lease = apply_cards_review.build_cards_plan.projectlib.acquire_project_lease(
                    root, blocking=False
                )
                try:
                    self.assertIsNone(lease)
                finally:
                    if lease is not None:
                        apply_cards_review.build_cards_plan.projectlib.release_project_lease(lease)
                    continue_replace.set()
                    writer.join(timeout=2)
                self.assertTrue(finished.is_set())
                self.assertFalse(writer.is_alive())
                self.assertEqual([], errors)
            finally:
                apply_cards_review.os.replace = original_replace


if __name__ == "__main__":
    unittest.main()
