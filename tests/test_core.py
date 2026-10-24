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


if __name__ == "__main__":
    unittest.main()
