import contextlib
import io
import json
import os
import tempfile
import unittest

from gpuvitals.__main__ import main
from gpuvitals.calibrate import calibrate, load_cards, load_multipliers
from gpuvitals.core import grade
from tests.synth import capture, make_cards


def run(*argv):
    out = io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
        code = main(list(argv))
    return code, out.getvalue()


class CalibrateTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = self.tmp.name

    def tearDown(self):
        self.tmp.cleanup()

    def test_learns_which_signs_matter_and_wins_out_of_sample(self):
        labels = make_cards(self.dir, ecc_effect=0.45, clock_effect=0.0)
        res = calibrate(load_cards(labels))
        m = res["multipliers"]
        self.assertEqual(m["low_clock"], 0.0)  # harmless in this fleet, though the built-in points punish it
        self.assertEqual(m["runs_hot"], 0.0)
        self.assertGreater(m["ecc_corrected"], 0)
        self.assertEqual(sorted(res["backwards_signs"]), ["low_clock", "runs_hot"])
        self.assertTrue(res["recommended"])
        self.assertGreater(res["auc_calibrated_cv"], res["auc_default"] + 0.05)
        self.assertEqual(m["retired_pages"], 1.0)  # never seen: unchanged

    def test_when_defaults_are_already_right_it_says_keep_them(self):
        labels = make_cards(self.dir, ecc_effect=0.35, clock_effect=0.25)
        res = calibrate(load_cards(labels))
        self.assertFalse(res["recommended"])
        self.assertLess(res["multipliers"]["runs_hot"], 1.0)  # still learns the harmless sign is overweighted

    def test_multipliers_change_the_grade(self):
        text = capture("SN1", 80, 0.75, 0)  # runs hot, slow clocks, no memory errors
        before = grade(text)
        after = grade(text, multipliers={"runs_hot": 0.0, "low_clock": 0.0})
        self.assertLess(before.score, after.score)
        self.assertEqual(after.score, 100)
        self.assertEqual(after.deductions, [])
        self.assertEqual(set(before.signals), {"runs_hot", "low_clock"})

    def test_bad_inputs_are_refused(self):
        labels = make_cards(self.dir, n=10)
        with self.assertRaisesRegex(ValueError, "at least 20"):
            calibrate(load_cards(labels))
        bad = os.path.join(self.dir, "bad.csv")
        for body, msg in (
            ("capture,failed\nmissing.csv,no\n", "cannot read"),
            ("capture,failed\ncard000.csv,maybe\n", "yes or no"),
        ):
            with open(bad, "w", encoding="utf-8") as fh:
                fh.write(body)
            with self.assertRaisesRegex(ValueError, msg):
                load_cards(bad)
        cal = os.path.join(self.dir, "cal.json")
        for doc in ({"multipliers": {"warp_drive": 1}}, {"multipliers": {"runs_hot": -1}}):
            with open(cal, "w", encoding="utf-8") as fh:
                json.dump(doc, fh)
            with self.assertRaises(ValueError):
                load_multipliers(cal)

    def test_cli_round_trip(self):
        labels = make_cards(self.dir, ecc_effect=0.45, clock_effect=0.0)
        cal = os.path.join(self.dir, "cal.json")
        code, out = run("calibrate", labels, "--out", cal)
        self.assertEqual(code, 0, out)
        self.assertIn("calibration: use it", out)
        code, out = run("report", os.path.join(self.dir, "card000.csv"), "--calibration", cal)
        self.assertEqual(code, 0, out)
        self.assertIn("Grade", out)


if __name__ == "__main__":
    unittest.main()
