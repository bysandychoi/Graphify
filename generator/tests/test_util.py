import unittest

from generator._util import (
    effective_lot_count,
    eligible_eqp_count,
    resolve_ratio_or_count,
    round_half_up,
    scaled_count,
)


class TestRoundHalfUp(unittest.TestCase):
    def test_exact_half_rounds_up(self):
        self.assertEqual(round_half_up(2.5), 3)
        self.assertEqual(round_half_up(13.5), 14)

    def test_below_half_rounds_down(self):
        self.assertEqual(round_half_up(2.4), 2)

    def test_does_not_round_up_a_value_that_is_actually_below_half(self):
        # math.floor(value + 0.5) 방식은 부동소수 덧셈 오차로 이 값을
        # 잘못 1로 올렸다(이 값 자체는 0.5보다 작다).
        self.assertEqual(round_half_up(0.49999999999999994), 0)

    def test_differs_from_bankers_rounding(self):
        # 표준 round()는 2.5를 짝수인 2로 내린다 — 이 규칙과 다르다.
        self.assertNotEqual(round_half_up(2.5), round(2.5))


class TestScaledCount(unittest.TestCase):
    def test_decimal_multiplication_avoids_float_error(self):
        # 1500 * 0.009를 그냥 float로 곱하면 13.5가 아닐 수 있어 반올림이
        # 13으로 잘못 나올 수 있다. Decimal 경유로 정확히 13.5를 얻어야 한다.
        self.assertEqual(scaled_count(0.009, 1500), 14)
        self.assertEqual(scaled_count(0.009, 3500), 32)
        self.assertEqual(scaled_count(0.018, 750), 14)


class TestEffectiveLotCount(unittest.TestCase):
    def test_no_factor_returns_lot_count(self):
        self.assertEqual(effective_lot_count({"scale": {"lot_count": 10000}}), 10000)

    def test_factor_applied_with_correct_rounding(self):
        self.assertEqual(
            effective_lot_count({"scale": {"lot_count": 1500, "factor": 0.009}}), 14
        )

    def test_rejects_non_positive_factor(self):
        for bad in (0, -0.1, True):
            with self.assertRaises(ValueError):
                effective_lot_count({"scale": {"lot_count": 100, "factor": bad}})

    def test_rejects_result_rounding_to_zero(self):
        with self.assertRaises(ValueError):
            effective_lot_count({"scale": {"lot_count": 10, "factor": 0.001}})


class TestEligibleEqpCount(unittest.TestCase):
    def test_counts_unique_eqp_only(self):
        pairs = [{"eqp": "M01", "resource": "R01"}, {"eqp": "M01", "resource": "R02"}]
        self.assertEqual(eligible_eqp_count(pairs), 1)

    def test_empty_pairs_is_zero(self):
        self.assertEqual(eligible_eqp_count([]), 0)


class TestResolveRatioOrCount(unittest.TestCase):
    def test_plain_number_is_a_ratio(self):
        self.assertEqual(resolve_ratio_or_count(0.05, 10000), 500)

    def test_ratio_only_object(self):
        self.assertEqual(resolve_ratio_or_count({"ratio": 0.05}, 10000), 500)

    def test_min_count_only_object_ignores_ratio(self):
        self.assertEqual(resolve_ratio_or_count({"min_count": 20}, 10000), 20)

    def test_ratio_below_min_count_uses_min_count(self):
        # 0.001 * 10000 = 10 < min_count 20 -> 20으로 끌어올림.
        self.assertEqual(resolve_ratio_or_count({"ratio": 0.001, "min_count": 20}, 10000), 20)

    def test_ratio_above_min_count_uses_ratio(self):
        self.assertEqual(resolve_ratio_or_count({"ratio": 0.05, "min_count": 20}, 10000), 500)

    def test_rejects_empty_object(self):
        with self.assertRaises(ValueError):
            resolve_ratio_or_count({}, 10000)

    def test_rejects_negative_ratio_or_min_count(self):
        with self.assertRaises(ValueError):
            resolve_ratio_or_count({"ratio": -0.1}, 10000)
        with self.assertRaises(ValueError):
            resolve_ratio_or_count({"min_count": -1}, 10000)

    def test_rejects_bool(self):
        with self.assertRaises(ValueError):
            resolve_ratio_or_count(True, 10000)

    def test_rejects_bool_min_count(self):
        with self.assertRaises(ValueError):
            resolve_ratio_or_count({"min_count": True}, 10000)

    def test_rejects_non_integer_min_count(self):
        with self.assertRaises(ValueError):
            resolve_ratio_or_count({"min_count": 2.7}, 10000)

    def test_rejects_ratio_above_one(self):
        with self.assertRaises(ValueError):
            resolve_ratio_or_count(5, 10000)
        with self.assertRaises(ValueError):
            resolve_ratio_or_count({"ratio": 1.5}, 10000)

    def test_rejects_bool_ratio(self):
        with self.assertRaises(ValueError):
            resolve_ratio_or_count({"ratio": True}, 10000)

    def test_rejects_unknown_keys(self):
        with self.assertRaises(ValueError):
            resolve_ratio_or_count({"ratio": 0.1, "mincount": 50}, 10000)


if __name__ == "__main__":
    unittest.main()
