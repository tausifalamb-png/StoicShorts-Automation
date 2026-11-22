import unittest
from stoic_shorts.llm import _validate_script


class LLMValidationTests(unittest.TestCase):
    def valid(self):
        return {
            "title": "Pause Before You React",
            "hook": "Har baat ka turant jawab dena zaroori nahi.",
            "scenes": ["Pause first", "Check the facts", "Choose your response"],
            "narration": " ".join(["Stoic practice teaches a useful pause between an event and your response."] * 8),
        }

    def test_valid_script_gets_stable_id_and_source_note(self):
        item = _validate_script(self.valid(), "2026-11-22")
        self.assertEqual(item["id"], "ai-20261122")
        self.assertEqual(len(item["scenes"]), 3)
        self.assertIn("not a direct quotation", item["source"])

    def test_rejects_wrong_scene_count(self):
        data = self.valid()
        data["scenes"] = ["Only one scene"]
        with self.assertRaises(ValueError):
            _validate_script(data, "2026-11-22")

    def test_rejects_too_short_narration(self):
        data = self.valid()
        data["narration"] = "Too short."
        with self.assertRaises(ValueError):
            _validate_script(data, "2026-11-22")


if __name__ == "__main__":
    unittest.main()
