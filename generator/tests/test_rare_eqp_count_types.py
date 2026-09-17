import random
import unittest
from collections import Counter

from generator._util import eligible_eqp_count
from generator.eqp_step import generate_eqp_step, generate_process_ids, generate_step_ids
from generator.rare_eqp_count_types import (
    allocate_rare_and_distribution_targets,
    generate_lot_data_with_rare_types,
)


class TestAllocateRareAndDistributionTargets(unittest.TestCase):
    def test_rare_gets_exactly_min_count_rest_goes_to_distribution(self):
        targets = allocate_rare_and_distribution_targets(
            {"5": {"min_count": 3, "max_count": 8}}, {"1": 0.5, "2": 0.5},
            100, random.Random(0), max_value=10,
        )
        counts = Counter(targets)
        self.assertEqual(counts[5], 3)
        self.assertEqual(counts[1] + counts[2], 97)
        self.assertEqual(sum(counts.values()), 100)

    def test_multiple_rare_values(self):
        targets = allocate_rare_and_distribution_targets(
            {"5": {"min_count": 2}, "7": {"min_count": 1}}, {"1": 1.0},
            50, random.Random(0), max_value=10,
        )
        counts = Counter(targets)
        self.assertEqual(counts[5], 2)
        self.assertEqual(counts[7], 1)
        self.assertEqual(counts[1], 47)

    def test_no_remaining_lots_allows_missing_distribution(self):
        targets = allocate_rare_and_distribution_targets(
            {"5": {"min_count": 10}}, {}, 10, random.Random(0), max_value=10,
        )
        self.assertEqual(Counter(targets), {5: 10})

    def test_order_is_shuffled(self):
        targets = allocate_rare_and_distribution_targets(
            {"5": {"min_count": 10}}, {"1": 1.0}, 20, random.Random(1), max_value=10,
        )
        self.assertNotEqual(targets[:10], [5] * 10)

    def test_rejects_rare_value_also_in_distribution(self):
        with self.assertRaises(ValueError):
            allocate_rare_and_distribution_targets(
                {"5": {"min_count": 1}}, {"5": 0.5, "1": 0.5},
                100, random.Random(0), max_value=10,
            )

    def test_rejects_rare_total_exceeding_lot_count(self):
        with self.assertRaises(ValueError):
            allocate_rare_and_distribution_targets(
                {"5": {"min_count": 20}}, {}, 10, random.Random(0), max_value=10,
            )

    def test_rejects_remaining_lots_with_no_distribution(self):
        with self.assertRaises(ValueError):
            allocate_rare_and_distribution_targets(
                {"5": {"min_count": 5}}, {}, 10, random.Random(0), max_value=10,
            )

    def test_rejects_empty_rare_types(self):
        with self.assertRaises(ValueError):
            allocate_rare_and_distribution_targets({}, {"1": 1.0}, 10, random.Random(0), max_value=10)

    def test_rejects_min_count_greater_than_max_count(self):
        with self.assertRaises(ValueError):
            allocate_rare_and_distribution_targets(
                {"5": {"min_count": 10, "max_count": 5}}, {}, 10, random.Random(0), max_value=10,
            )

    def test_rejects_negative_min_count(self):
        with self.assertRaises(ValueError):
            allocate_rare_and_distribution_targets(
                {"5": {"min_count": -1}}, {}, 10, random.Random(0), max_value=10,
            )

    def test_rejects_key_exceeding_max_value(self):
        with self.assertRaises(ValueError):
            allocate_rare_and_distribution_targets(
                {"11": {"min_count": 1}}, {}, 10, random.Random(0), max_value=10,
            )

    def test_rejects_missing_min_count(self):
        # min_count 없이 max_count만 있으면(또는 완전히 빈 객체면)
        # 조용히 0건으로 새는 대신 에러를 낸다.
        with self.assertRaises(ValueError):
            allocate_rare_and_distribution_targets(
                {"5": {"max_count": 5}}, {}, 10, random.Random(0), max_value=10,
            )

    def test_rejects_empty_spec_object(self):
        with self.assertRaises(ValueError):
            allocate_rare_and_distribution_targets(
                {"5": {}}, {}, 10, random.Random(0), max_value=10,
            )

    def test_rejects_unknown_spec_keys(self):
        with self.assertRaises(ValueError):
            allocate_rare_and_distribution_targets(
                {"5": {"min_count": 1, "ratio": 0.5}}, {}, 10, random.Random(0), max_value=10,
            )
        with self.assertRaises(ValueError):
            allocate_rare_and_distribution_targets(
                {"5": {"mincount": 3}}, {}, 10, random.Random(0), max_value=10,
            )

    def test_rejects_duplicate_value_under_different_key_spellings(self):
        # "5"와 "05"는 같은 값(5)을 가리킨다 — 정규화 없이 문자열로만
        # 비교하면 배타성/중복 검사를 우회할 수 있었다.
        with self.assertRaises(ValueError):
            allocate_rare_and_distribution_targets(
                {"5": {"min_count": 3}, "05": {"min_count": 2}},
                {}, 20, random.Random(0), max_value=10,
            )

    def test_rejects_rare_value_in_distribution_under_different_key_spelling(self):
        with self.assertRaises(ValueError):
            allocate_rare_and_distribution_targets(
                {"5": {"min_count": 3}}, {"05": 0.5, "1": 0.5},
                20, random.Random(0), max_value=10,
            )

    def test_validates_distribution_structure_even_when_remaining_is_zero(self):
        # rare가 lot_count 전부를 채워도(나머지 0), distribution이
        # 주어졌다면 그 구조(비율 합=1 등)는 여전히 검증해야 한다.
        with self.assertRaises(ValueError):
            allocate_rare_and_distribution_targets(
                {"5": {"min_count": 10}}, {"1": 0.3, "2": 0.3},  # 합이 1이 아님
                10, random.Random(0), max_value=10,
            )

    def test_accepts_rare_value_zero(self):
        targets = allocate_rare_and_distribution_targets(
            {"0": {"min_count": 4}}, {"1": 1.0}, 10, random.Random(0), max_value=10,
        )
        self.assertEqual(Counter(targets), {0: 4, 1: 6})

    def test_rejects_non_dict_rare_types(self):
        with self.assertRaises(ValueError):
            allocate_rare_and_distribution_targets([], {}, 10, random.Random(0), max_value=10)


class TestGenerateLotDataWithRareTypes(unittest.TestCase):
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

    def _config(self, lot_count, eqp_count=10):
        return {"seed": 1, "scale": {"lot_count": lot_count, "eqp_count": eqp_count}}

    def test_rare_type_count_is_exact_and_small(self):
        # 완료 기준: 드문 설비 수 값이 1~수 개 lot에서만 등장.
        process_ids, step_ids, rows = self._eqp_step_setup()
        data = generate_lot_data_with_rare_types(
            self._config(300),
            process_ids=process_ids, step_ids=step_ids, eqp_step_rows=rows,
            rare_types={"5": {"min_count": 3, "max_count": 8}},
            distribution={"1": 0.5, "2": 0.5},
        )
        counts = Counter(eligible_eqp_count(lot["candidate_pairs"]) for lot in data["lot_data"])
        self.assertEqual(counts[5], 3)
        self.assertEqual(counts[1] + counts[2], 297)

    def test_lot_count_matches_effective_lot_count(self):
        process_ids, step_ids, rows = self._eqp_step_setup()
        data = generate_lot_data_with_rare_types(
            self._config(200),
            process_ids=process_ids, step_ids=step_ids, eqp_step_rows=rows,
            rare_types={"5": {"min_count": 5}},
            distribution={"1": 1.0},
        )
        self.assertEqual(len(data["lot_data"]), 200)
        ids = [lot["lot_id"] for lot in data["lot_data"]]
        self.assertEqual(len(ids), len(set(ids)))

    def test_does_not_imply_pairs_beyond_target(self):
        process_ids, step_ids, rows = self._eqp_step_setup()
        real_pairs = set()
        for row in rows:
            for eqp_id in row["eligible_eqp_ids"]:
                real_pairs.add((eqp_id, row["resource_id"]))
        data = generate_lot_data_with_rare_types(
            self._config(50),
            process_ids=process_ids, step_ids=step_ids, eqp_step_rows=rows,
            rare_types={"5": {"min_count": 50}},
        )
        for lot in data["lot_data"]:
            self.assertEqual(eligible_eqp_count(lot["candidate_pairs"]), 5)
            for pair in lot["candidate_pairs"]:
                self.assertIn((pair["eqp"], pair["resource"]), real_pairs)

    def test_reproducible_with_same_seed(self):
        process_ids, step_ids, rows = self._eqp_step_setup()
        kwargs = dict(
            process_ids=process_ids, step_ids=step_ids, eqp_step_rows=rows,
            rare_types={"5": {"min_count": 3}}, distribution={"1": 1.0},
        )
        a = generate_lot_data_with_rare_types(self._config(100), rng=random.Random(9), **kwargs)
        b = generate_lot_data_with_rare_types(self._config(100), rng=random.Random(9), **kwargs)
        self.assertEqual(a, b)

    def test_rejects_duplicate_process_or_step_ids(self):
        process_ids, step_ids, rows = self._eqp_step_setup()
        with self.assertRaises(ValueError):
            generate_lot_data_with_rare_types(
                self._config(10),
                process_ids=process_ids + [process_ids[0]], step_ids=step_ids,
                eqp_step_rows=rows, rare_types={"1": {"min_count": 10}},
            )


if __name__ == "__main__":
    unittest.main()
