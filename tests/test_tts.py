import tempfile
import unittest
from pathlib import Path
from stoic_shorts.tts import write_srt


class SubtitleTests(unittest.TestCase):
    def test_writes_timed_caption_groups(self):
        boundaries = [
            {"offset": i * 5000000, "duration": 3000000, "text": word}
            for i, word in enumerate(["आज", "अपना", "response", "सोचकर", "चुनो।"])
        ]
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "captions.srt"
            count = write_srt(boundaries, path, words_per_caption=4)
            result = path.read_text(encoding="utf-8")
            self.assertEqual(count, 2)
            self.assertIn("आज अपना response सोचकर", result)
            self.assertIn("चुनो।", result)
            self.assertIn(" --> ", result)

    def test_rejects_empty_word_timings(self):
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaises(ValueError):
                write_srt([], Path(folder) / "empty.srt")


if __name__ == "__main__":
    unittest.main()
