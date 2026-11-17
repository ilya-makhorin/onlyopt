import asyncio
import unittest
from decimal import Decimal

from starter import recommend_price, sample_fetch_offers

D = Decimal


def source(offers, status="success"):
    async def fetch():
        return {"status": status, "offers": offers}

    return fetch


def offer(seller, price, days):
    return {"seller": seller, "price": D(price), "delivery_days": days}


class NormalCalculationTest(unittest.IsolatedAsyncioTestCase):
    async def test_sample_from_task(self):
        res = await recommend_price(
            sample_fetch_offers, current_price=D("4900.00"), min_price=D("4500.00")
        )
        self.assertEqual(res["price"], D("4728.00"))
        self.assertIsInstance(res["price"], Decimal)
        self.assertEqual(res["decision"], "APPLY")
        self.assertTrue(res["reason"])

    async def test_rounds_down_to_cent(self):
        res = await recommend_price(
            source([offer("A", "1000.99", 1)]), D("1000.00"), D("1.00")
        )
        self.assertEqual(res["price"], D("985.97"))

    async def test_min_price_floor(self):
        res = await recommend_price(
            source([offer("A", "1000.00", 1)]), D("1000.00"), D("990.00")
        )
        self.assertEqual(res["price"], D("990.00"))
        self.assertEqual(res["decision"], "APPLY")


class SourceFailureTest(unittest.IsolatedAsyncioTestCase):
    async def test_timeout_returns_hold(self):
        async def slow():
            await asyncio.sleep(10)

        res = await recommend_price(slow, D("4900.00"), D("4500.00"), timeout_s=0.05)
        self.assertEqual((res["price"], res["decision"]), (D("4900.00"), "HOLD"))

    async def test_exception_returns_hold(self):
        async def broken():
            raise ConnectionError("площадка недоступна")

        res = await recommend_price(broken, D("4900.00"), D("4500.00"))
        self.assertEqual((res["price"], res["decision"]), (D("4900.00"), "HOLD"))

    async def test_partial_status_returns_hold(self):
        fetch = source([offer("A", "4800.00", 1)], status="partial")
        res = await recommend_price(fetch, D("4900.00"), D("4500.00"))
        self.assertEqual((res["price"], res["decision"]), (D("4900.00"), "HOLD"))


class EdgeCasesTest(unittest.IsolatedAsyncioTestCase):
    async def test_no_suitable_offers_hold_even_below_min_price(self):
        fetch = source([
            offer("MyShop", "100.00", 1),
            offer("A", "100.00", None),
            offer("B", "100.00", 7),
        ])
        res = await recommend_price(fetch, D("400.00"), D("500.00"))
        self.assertEqual((res["price"], res["decision"]), (D("400.00"), "HOLD"))

    async def test_exactly_30_percent_is_apply_both_directions(self):
        cases = [
            ("1319.80", "1300.00"),
            ("710.66", "700.00"),
        ]
        for competitor, expected in cases:
            with self.subTest(competitor=competitor):
                res = await recommend_price(
                    source([offer("A", competitor, 0)]), D("1000.00"), D("1.00")
                )
                self.assertEqual(res["price"], D(expected))
                self.assertEqual(res["decision"], "APPLY")

    async def test_over_30_percent_is_review_both_directions(self):
        cases = [
            ("1319.81", "1300.01"),
            ("710.65", "699.99"),
        ]
        for competitor, expected in cases:
            with self.subTest(competitor=competitor):
                res = await recommend_price(
                    source([offer("A", competitor, 0)]), D("1000.00"), D("1.00")
                )
                self.assertEqual(res["price"], D(expected))
                self.assertEqual(res["decision"], "REVIEW")


if __name__ == "__main__":
    unittest.main()
