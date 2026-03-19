import os
import sys
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from Data.OS.dotSONIC.DotSonicMediaPlayer import DotSonicMediaPlayer


class TestDotSonicBalance(unittest.TestCase):
    def setUp(self):
        self.player = DotSonicMediaPlayer.__new__(DotSonicMediaPlayer)
        self.player.volume = 0.8
        self.player.balance = 0.0

    def test_center_balance_keeps_channels_equal(self):
        left, right = self.player._get_output_levels()
        self.assertAlmostEqual(left, 0.8)
        self.assertAlmostEqual(right, 0.8)

    def test_full_left_mutes_right_channel(self):
        self.player.balance = -1.0
        left, right = self.player._get_output_levels()
        self.assertAlmostEqual(left, 0.8)
        self.assertAlmostEqual(right, 0.0)

    def test_full_right_mutes_left_channel(self):
        self.player.balance = 1.0
        left, right = self.player._get_output_levels()
        self.assertAlmostEqual(left, 0.0)
        self.assertAlmostEqual(right, 0.8)

    def test_partial_right_pan_reduces_left_only(self):
        self.player.balance = 0.25
        left, right = self.player._get_output_levels()
        self.assertAlmostEqual(left, 0.6)
        self.assertAlmostEqual(right, 0.8)


if __name__ == "__main__":
    unittest.main()
