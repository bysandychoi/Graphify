import random
import unittest
from collections import Counter

from generator._util import eligible_eqp_count
from generator.eqp_count_distribution import (
    allocate_target_counts,
    generate_lot_data_with_distribution,
)
from generator.eqp_step import generate_eqp_step, generate_process_ids, generate_step_ids


class TestAllocateTargetCounts(unittest.TestCase):
    def test_matches_ratios_exactly_when_divisible(self):
        allocation = allocate_target_counts(
            {"1": 0.2, "2": 0.6, "3": 0.2}, 100, random.Random(0), max_value=10
        )
        self.assertEqual(len(allocation), 100)
        self.assertEqual(Counter(allocation), {1: 20, 2: 60, 3: 20})

    def test_largest_remainder_never_goes_negative_with_many_tied_categories(self):
        # 4개 카테고리 x 0.25, lot_count=2 -- 이전(가장 큰 카테고리에서
        # diff 보정)에는 여기서 음수가 나며 크래시했다.
        allocation = allocate_target_counts(
            {"1": 0.25, "2": 0.25, "3": 0.25, "4": 0.25}, 2, random.Random(0), max_value=10
        )
        self.assertEqual(len(allocation), 2)
        self.assertTrue(all(c in (0, 1) for c in Counter(allocation).values()))

    def test_largest_remainder_spreads_across_categories_not_just_one(self):
        # 8개 카테고리 x 0.125, lot_count=100 -- 몫은 전부 12.5, 나머지
        # 4는 여러 카테고리에 나눠져야 한다(한 카테고리에 몰리면 결함).
        distribution = {str(i): 0.125 for i in range(1, 9)}
        allocation = allocate_target_counts(distribution, 100, random.Random(0), max_value=10)
        counts = Counter(allocation)
        self.assertEqual(sum(counts.values()), 100)
        self.assertTrue(all(v in (12, 13) for v in counts.values()))
        self.assertEqual(sum(1 for v in counts.values() if v == 13), 4)

    def test_tie_break_is_deterministic_regardless_of_key_order(self):
        a = allocate_target_counts({"1": 0.5, "2": 0.5}, 7, random.Random(0), max_value=10)
        b = allocate_target_counts({"2": 0.5, "1": 0.5}, 7, random.Random(0), max_value=10)
        self.assertEqual(Counter(a), Counter(b))

    def test_order_is_shuffled_not_grouped(self):
        allocation = allocate_target_counts(
            {"1": 0.5, "2": 0.5}, 20, random.Random(1), max_value=10
        )
        # 그룹으로 뭉쳐 있으면(예: 1이 앞 10개, 2가 뒤 10개) 앞 절반이
        # 전부 같은 값일 확률이 매우 높다 — 뒤섞였다면 그렇지 않아야 한다.
        self.assertNotEqual(allocation[:10], [1] * 10)

    def test_rejects_ratios_not_summing_to_one(self):
        with self.assertRaises(ValueError):
            allocate_target_counts({"1": 0.5, "2": 0.6}, 100, random.Random(0), max_value=10)

    def test_rejects_empty_distribution(self):
        with self.assertRaises(ValueError):
            allocate_target_counts({}, 100, random.Random(0), max_value=10)

    def test_accepts_zero_as_a_value(self):
        allocation = allocate_target_counts({"0": 1.0}, 10, random.Random(0), max_value=10)
        self.assertEqual(allocation, [0] * 10)

    def test_rejects_key_exceeding_max_value(self):
        with self.assertRaises(ValueError):
            allocate_target_counts({"9": 1.0}, 10, random.Random(0), max_value=8)

    def test_rejects_non_ascii_digit_keys(self):
        for bad_key in (" 3 ", "+3", "2.5", "abc", "３"):
            with self.assertRaises(ValueError):
                allocate_target_counts({bad_key: 1.0}, 10, random.Random(0), max_value=10)


class TestGenerateLotDataWithDistribution(unittest.TestCase):
    def _eqp_step_setup(self, process_count=3, step_count=5, eqp_count=10, resource_count=5, seed=1):
        process_ids = generate_process_ids(process_count)
        step_ids = generate_step_ids(step_count)
        eqp_ids = [f"M{i:04d}" for i in range(1, eqp_count + 1)]
        resource_ids = [f"R{i:04d}" for i in range(1, resource_count + 1)]
        rows = generate_eqp_step(
            process_ids=process_ids, step_ids=step_ids,
            resource_ids=resource_ids, eqp_ids=eqp_ids, rng=random.Random(seed),
        )
        return process_ids, step_ids, rows

    def _config(self, lot_count, eqp_count=10, factor=None):
        scale = {"lot_count": lot_count, "eqp_count": eqp_count}
        if factor is not None:
            scale["factor"] = factor
        return {"seed": 1, "scale": scale}

    def test_histogram_matches_configured_distribution(self):
        process_ids, step_ids, rows = self._eqp_step_setup()
        data = generate_lot_data_with_distribution(
            self._config(300),
            process_ids=process_ids, step_ids=step_ids, eqp_step_rows=rows,
            distribution={"1": 0.2, "2": 0.6, "3": 0.2},
        )
        counts = Counter(eligible_eqp_count(lot["candidate_pairs"]) for lot in data["lot_data"])
        self.assertEqual(counts, {1: 60, 2: 180, 3: 60})

    def test_zero_target_gives_empty_candidate_pairs(self):
        process_ids, step_ids, rows = self._eqp_step_setup()
        data = generate_lot_data_with_distribution(
            self._config(10),
            process_ids=process_ids, step_ids=step_ids, eqp_step_rows=rows,
            distribution={"0": 1.0},
        )
        for lot in data["lot_data"]:
            self.assertEqual(lot["candidate_pairs"], [])
            self.assertIn(lot["current_step"], step_ids)

    def test_does_not_imply_pairs_beyond_target_count(self):
        # 목표가 1이면 candidate_pairs의 eqp 종류는 정확히 1개여야 하고,
        # 그 eqp가 갖는 pair들도 원래 eqp_step에 실제로 있던 것만이어야
        # 한다(새로 지어내지 않음).
        process_ids, step_ids, rows = self._eqp_step_setup()
        real_pairs = set()
        for row in rows:
            for eqp_id in row["eligible_eqp_ids"]:
                real_pairs.add((eqp_id, row["resource_id"]))

        data = generate_lot_data_with_distribution(
            self._config(50),
            process_ids=process_ids, step_ids=step_ids, eqp_step_rows=rows,
            distribution={"1": 1.0},
        )
        for lot in data["lot_data"]:
            self.assertEqual(eligible_eqp_count(lot["candidate_pairs"]), 1)
            for pair in lot["candidate_pairs"]:
                self.assertIn((pair["eqp"], pair["resource"]), real_pairs)

    def test_lot_ids_unique_and_count_matches_effective_lot_count(self):
        process_ids, step_ids, rows = self._eqp_step_setup()
        data = generate_lot_data_with_distribution(
            self._config(1000, factor=0.05),
            process_ids=process_ids, step_ids=step_ids, eqp_step_rows=rows,
            distribution={"1": 0.5, "2": 0.5},
        )
        self.assertEqual(len(data["lot_data"]), 50)
        ids = [lot["lot_id"] for lot in data["lot_data"]]
        self.assertEqual(len(ids), len(set(ids)))

    def test_reproducible_with_same_seed(self):
        process_ids, step_ids, rows = self._eqp_step_setup()
        kwargs = dict(
            process_ids=process_ids, step_ids=step_ids, eqp_step_rows=rows,
            distribution={"1": 0.5, "2": 0.5},
        )
        a = generate_lot_data_with_distribution(
            self._config(100), rng=random.Random(9), **kwargs
        )
        b = generate_lot_data_with_distribution(
            self._config(100), rng=random.Random(9), **kwargs
        )
        self.assertEqual(a, b)

    def test_raises_when_no_combination_can_satisfy_target(self):
        # eqp가 1대뿐이면 eligible_eqp_count=5는 어떤 (process,step)도
        # 만족할 수 없다 — 조용히 작은 값으로 낮추지 않고 에러를 낸다.
        process_ids = ["P0001"]
        step_ids = ["S0001"]
        rows = [{
            "process_id": "P0001", "step_id": "S0001",
            "resource_id": "R0001", "eligible_eqp_ids": ["M0001"],
        }]
        with self.assertRaises(ValueError):
            generate_lot_data_with_distribution(
                self._config(10, eqp_count=5),
                process_ids=process_ids, step_ids=step_ids, eqp_step_rows=rows,
                distribution={"5": 1.0},
            )

    def test_rejects_distribution_key_above_eqp_count(self):
        process_ids, step_ids, rows = self._eqp_step_setup(eqp_count=8)
        with self.assertRaises(ValueError):
            generate_lot_data_with_distribution(
                self._config(10, eqp_count=8),
                process_ids=process_ids, step_ids=step_ids, eqp_step_rows=rows,
                distribution={"9": 1.0},
            )

    def test_rejects_duplicate_process_or_step_ids(self):
        process_ids, step_ids, rows = self._eqp_step_setup()
        with self.assertRaises(ValueError):
            generate_lot_data_with_distribution(
                self._config(10),
                process_ids=process_ids + [process_ids[0]], step_ids=step_ids,
                eqp_step_rows=rows, distribution={"1": 1.0},
            )

    def test_rejects_empty_process_or_step_ids(self):
        with self.assertRaises(ValueError):
            generate_lot_data_with_distribution(
                self._config(10),
                process_ids=[], step_ids=["S0001"], eqp_step_rows=[],
                distribution={"0": 1.0},
            )


if __name__ == "__main__":
    unittest.main()
