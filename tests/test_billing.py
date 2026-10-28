"""Checkout shape: monthly plans carry the 14-day trial; Single report is one-time."""

import pathlib
import tempfile
import unittest

from gpuvitals import web


def _billing():
    env = {
        "STRIPE_SECRET_KEY": "sk_test_x",
        "STRIPE_WEBHOOK_SECRET": "whsec_test",
        "STRIPE_PRICES": "single=price_single,seller=price_seller,marketplace=price_market",
        "PUBLIC_URL": "https://example.test",
    }
    tmp = tempfile.TemporaryDirectory()
    srv = web.make_server("127.0.0.1", 0, pathlib.Path(tmp.name), env=env)
    billing = srv.RequestHandlerClass.billing
    sent = {}
    billing._stripe = lambda path, form: sent.update(form) or {"url": "https://checkout.test/s"}
    return tmp, billing, sent


class TestCheckoutShape(unittest.TestCase):
    def test_monthly_checkout_is_subscription_with_14_day_trial(self):
        tmp, billing, sent = _billing()
        try:
            self.assertEqual(billing.checkout("seller"), "https://checkout.test/s")
            self.assertEqual(sent["mode"], "subscription")
            self.assertEqual(sent["subscription_data[trial_period_days]"], "14")
            self.assertEqual(sent["line_items[0][price]"], "price_seller")
        finally:
            tmp.cleanup()

    def test_single_report_checkout_is_one_time_payment_without_trial(self):
        tmp, billing, sent = _billing()
        try:
            self.assertEqual(billing.checkout("single"), "https://checkout.test/s")
            self.assertEqual(sent["mode"], "payment")
            self.assertNotIn("subscription_data[trial_period_days]", sent)
            self.assertEqual(sent["line_items[0][price]"], "price_single")
        finally:
            tmp.cleanup()

    def test_pricing_page_notes_trial_and_one_time_single(self):
        tmp, billing, _sent = _billing()
        try:
            page = web.pricing_page(billing)
            self.assertIn("14-day free trial", page)
            self.assertIn("Single report is a one-time purchase", page)
            self.assertIn("Buy once", page)
        finally:
            tmp.cleanup()


if __name__ == "__main__":
    unittest.main()
