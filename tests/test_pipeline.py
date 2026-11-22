import unittest
from stoic_shorts.pipeline import assert_not_already_uploaded


class PipelineSafetyTests(unittest.TestCase):
    def test_blocks_second_upload_on_same_day(self):
        history = {"videos": [{"date": "2026-11-22", "youtube_video_id": "abc123"}]}
        with self.assertRaises(RuntimeError):
            assert_not_already_uploaded("2026-11-22", history, "new-hash")

    def test_blocks_recent_duplicate_content(self):
        history = {"videos": [{"date": "2026-11-20", "content_hash": "same-hash"}]}
        with self.assertRaises(RuntimeError):
            assert_not_already_uploaded("2026-11-22", history, "same-hash")

    def test_allows_first_upload_of_day(self):
        history = {"videos": [{"date": "2026-11-21", "youtube_video_id": "old-id"}]}
        assert_not_already_uploaded("2026-11-22", history, "new-hash")


if __name__ == "__main__":
    unittest.main()
