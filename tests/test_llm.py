import unittest
from stoic_shorts.llm import _validate_script


class LLMValidationTests(unittest.TestCase):
    def valid(self):
        narration = (
            "जब कोई तुम्हारी बात काटता है, तो तुरंत जवाब देने का मन करता है। "
            "लेकिन हर प्रतिक्रिया तुम्हारे लिए सही नहीं होती। Stoic practice कहती है "
            "कि पहले situation को समझो, फिर अपना response चुनो। मान लो किसी दोस्त ने "
            "message का जवाब देर से दिया। बिना facts जाने नाराज़ होना तुम्हारी energy "
            "खर्च करेगा। एक छोटा pause लो, अपनी assumption check करो और ज़रूरत हो "
            "तो calmly बात करो। आज किसी एक मुश्किल moment में यही practice अपनाओ।"
        )
        return {
            "title": "Pause Before You React",
            "hook": "Har baat ka turant jawab dena zaroori nahi.",
            "scenes": ["Pause first", "Check the facts", "Choose your response"],
            "narration": narration,
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

    def test_rejects_title_over_eight_words(self):
        data = self.valid()
        data["title"] = "One Two Three Four Five Six Seven Eight Nine"
        with self.assertRaises(ValueError):
            _validate_script(data, "2026-11-22")


if __name__ == "__main__":
    unittest.main()
