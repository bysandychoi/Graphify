import unittest

from generator._util import effective_lot_count, eligible_eqp_count, round_half_up, scaled_count


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


if __name__ == "__main__":
    unittest.main()
