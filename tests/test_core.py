import unittest

from gpu_carfax import grade, parse_capture

HEADER = (
    "timestamp, name, serial, temperature.gpu, power.draw [W], power.limit [W], clocks.sm [MHz], clocks.max.sm [MHz], "
    "utilization.gpu [%], fan.speed [%], ecc.errors.corrected.volatile.total, ecc.errors.uncorrected.volatile.total, retired_pages.pending"
)


def capture(temp, power, clock, fan, ecc_c=0, ecc_u=0, n=10):
    rows = [HEADER]
    for i in range(n):
        rows.append(
            f"2026/10/24 10:00:{i:02d}, NVIDIA GeForce RTX 3090, 0324, {temp}, {power} W, 350.00 W, {clock} MHz, 2100 MHz, "
            f"99 %, {fan} %, {ecc_c}, {ecc_u}, No"
        )
    return "\n".join(rows)


class Tests(unittest.TestCase):
    def test_parse_units(self):
        rows = parse_capture(capture(70, 340, 1950, 60))
        self.assertEqual(rows[0]["power.draw"], 340.0)
        self.assertEqual(rows[0]["retired_pages.pending"], 0.0)
        self.assertEqual(rows[0]["name"], "NVIDIA GeForce RTX 3090")

    def test_healthy_card(self):
        r = grade(capture(70, 340, 1950, 60), market_price=800)
        self.assertEqual(r.grade, "A")
        self.assertEqual(r.fair_price, 800)

    def test_cooked_ex_mining_card(self):
        r = grade(capture(91, 250, 1500, 100, ecc_c=40), hours=30000, mining=True, market_price=800)
        self.assertIn(r.grade, {"D", "F"})
        reasons = " ".join(x for x, _ in r.deductions)
        for needle in (
            "throttling",
            "SM clock",
            "power limit",
            "fan maxed",
            "corrected ECC",
            "power-on hours",
            "mining",
        ):
            self.assertIn(needle, reasons)
        self.assertLess(r.fair_price, 500)

    def test_uncorrected_ecc_is_severe(self):
        self.assertLessEqual(grade(capture(70, 340, 1950, 60, ecc_u=2)).score, 60)

    def test_report_id_stable(self):
        c = capture(70, 340, 1950, 60)
        self.assertEqual(grade(c).report_id, grade(c).report_id)

    def test_seller_cannot_get_a_grade_from_an_empty_idle_or_stripped_capture(self):
        idle = capture(40, 60, 300, 30).replace(" 99 %,", " 3 %,")
        stripped = "\n".join(
            ",".join(cell for i, cell in enumerate(line.split(",")) if i not in (10, 11))
            for line in capture(70, 340, 1950, 60, ecc_u=9).splitlines()
        )
        for label, text in (("empty", ""), ("header only", HEADER), ("too short", capture(70, 340, 1950, 60, n=2))):
            with self.subTest(label), self.assertRaises(ValueError):
                grade(text)
        with self.assertRaisesRegex(ValueError, "load"):
            grade(idle)
        with self.assertRaisesRegex(ValueError, "missing fields"):
            grade(stripped)

    def test_multi_gpu_capture_is_refused_not_averaged(self):
        a = capture(70, 340, 1950, 60)
        b = capture(95, 200, 1200, 100, ecc_u=5).replace(", 0324,", ", 0999,")
        with self.assertRaisesRegex(ValueError, "2 GPUs"):
            grade(a + "\n" + "\n".join(b.splitlines()[1:]))

    def test_hours_and_price_must_be_finite(self):
        for kw in ({"hours": float("inf")}, {"hours": -5}, {"market_price": float("nan")}):
            with self.subTest(kw=kw), self.assertRaises(ValueError):
                grade(capture(70, 340, 1950, 60), **kw)


if __name__ == "__main__":
    unittest.main()
