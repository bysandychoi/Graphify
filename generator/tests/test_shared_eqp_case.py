import random
import unittest

from generator._util import eligible_eqp_count
from generator.shared_eqp_case import (
    find_shared_eqp_combinations,
    has_shared_eqp_multi_resource,
    inject_shared_eqp_cases,
)

# P0001/S0001: M0001이 R0001과 R0002 둘 다에 나타남 (shared 조합,
# eligible_eqp_count 2: M0001, M0002). P0002/S0001: 설비가 서로
# 겹치지 않음 (non-shared, eligible_eqp_count 2: M0003, M0004).
EQP_STEP_ROWS = [
    {"process_id": "P0001", "step_id": "S0001", "resource_id": "R0001", "eligible_eqp_ids": ["M0001", "M0002"]},
    {"process_id": "P0001", "step_id": "S0001", "resource_id": "R0002", "eligible_eqp_ids": ["M0001"]},
    {"process_id": "P0002", "step_id": "S0001", "resource_id": "R0001", "eligible_eqp_ids": ["M0003"]},
    {"process_id": "P0002", "step_id": "S0001", "resource_id": "R0002", "eligible_eqp_ids": ["M0004"]},
]


class TestHasSharedEqpMultiResource(unittest.TestCase):
    def test_true_when_same_eqp_appears_with_two_distinct_resources(self):
        pairs = [
            {"eqp": "M0001", "resource": "R0001"},
            {"eqp": "M0001", "resource": "R0002"},
        ]
        self.assertTrue(has_shared_eqp_multi_resource(pairs))

    def test_false_when_every_eqp_has_one_resource(self):
        pairs = [
            {"eqp": "M0001", "resource": "R0001"},
            {"eqp": "M0002", "resource": "R0002"},
        ]
        self.assertFalse(has_shared_eqp_multi_resource(pairs))

    def test_false_when_duplicate_pair_repeats_same_resource(self):
        # 같은 (eqp, resource) 쌍이 두 번 있어도 resource 종류는
        # 하나뿐이므로 "여러 resource"가 아니다 — 단순 등장 횟수가
        # 아니라 서로 다른 resource 개수를 세야 한다.
        pairs = [
            {"eqp": "M0001", "resource": "R0001"},
            {"eqp": "M0001", "resource": "R0001"},
        ]
        self.assertFalse(has_shared_eqp_multi_resource(pairs))

    def test_false_for_empty_pairs(self):
        self.assertFalse(has_shared_eqp_multi_resource([]))


class TestFindSharedEqpCombinations(unittest.TestCase):
    def test_only_returns_combinations_that_actually_have_the_property(self):
        combos = find_shared_eqp_combinations(
            ["P0001", "P0002"], ["S0001"], EQP_STEP_ROWS
        )
        self.assertEqual(combos, [("P0001", "S0001")])

    def test_empty_when_no_combination_qualifies(self):
        rows = [
            {"process_id": "P0001", "step_id": "S0001", "resource_id": "R0001", "eligible_eqp_ids": ["M0001"]},
        ]
        self.assertEqual(find_shared_eqp_combinations(["P0001"], ["S0001"], rows), [])


class TestInjectSharedEqpCases(unittest.TestCase):
    def _lots(self, n=10, eligible_count=2):
        # 기본 candidate_pairs는 non-shared 조합(P0002/S0001)에서 온
        # 것으로, eligible_eqp_count가 딱 2인 상태에서 시작한다.
        pairs = [{"eqp": "M0003", "resource": "R0001"}, {"eqp": "M0004", "resource": "R0002"}]
        if eligible_count == 1:
            pairs = [{"eqp": "M0003", "resource": "R0001"}]
        elif eligible_count == 0:
            pairs = []
        return [
            {"lot_id": f"LOT_V{i:04d}", "current_step": "S0001",
             "candidate_pairs": list(pairs), "attributes": {}}
            for i in range(1, n + 1)
        ]

    def test_zero_target_returns_unchanged_copy(self):
        lots = self._lots()
        result = inject_shared_eqp_cases(
            lots, process_ids=["P0001", "P0002"], step_ids=["S0001"],
            eqp_step_rows=EQP_STEP_ROWS, target_count=0, rng=random.Random(0),
        )
        self.assertEqual(result, lots)
        self.assertIsNot(result, lots)

    def test_injects_exactly_the_deficit_when_none_already_qualify(self):
        lots = self._lots(n=10)
        self.assertEqual(
            sum(1 for lot in lots if has_shared_eqp_multi_resource(lot["candidate_pairs"])), 0
        )
        result = inject_shared_eqp_cases(
            lots, process_ids=["P0001", "P0002"], step_ids=["S0001"],
            eqp_step_rows=EQP_STEP_ROWS, target_count=3, rng=random.Random(0),
        )
        matching = [lot for lot in result if has_shared_eqp_multi_resource(lot["candidate_pairs"])]
        self.assertEqual(len(matching), 3)

    def test_does_not_touch_lots_that_already_qualify(self):
        # target_count가 자연 발생분보다 작거나 같으면 아무것도 바꾸지
        # 않는다 — 이미 만족하는 lot을 또 골라 덮어쓰며 예산을
        # 낭비하지 않는다(이전 버전의 결함).
        lots = self._lots(n=10)
        lots[0]["candidate_pairs"] = [
            {"eqp": "M0001", "resource": "R0001"}, {"eqp": "M0001", "resource": "R0002"},
        ]
        result = inject_shared_eqp_cases(
            lots, process_ids=["P0001", "P0002"], step_ids=["S0001"],
            eqp_step_rows=EQP_STEP_ROWS, target_count=1, rng=random.Random(0),
        )
        self.assertEqual(result, lots)

    def test_preserves_each_injected_lots_eligible_eqp_count(self):
        # T016이 T015의 eligible_eqp_count 분포를 깨지 않는다는 것의
        # 핵심 확인: eligible_eqp_count=1짜리 lot에 주입해도 여전히 1.
        lots = self._lots(n=5, eligible_count=1)
        result = inject_shared_eqp_cases(
            lots, process_ids=["P0001", "P0002"], step_ids=["S0001"],
            eqp_step_rows=EQP_STEP_ROWS, target_count=5, rng=random.Random(0),
        )
        for lot in result:
            self.assertTrue(has_shared_eqp_multi_resource(lot["candidate_pairs"]))
            self.assertEqual(eligible_eqp_count(lot["candidate_pairs"]), 1)
            # eligible_eqp_count==1이면서 shared려면 그 하나의 eqp가
            # 정확히 M0001(P0001/S0001에서 R0001,R0002 둘 다와 짝지어짐)
            # 이어야 한다 — 다른 eqp는 이 조건을 만족할 수 없다.
            self.assertEqual({p["eqp"] for p in lot["candidate_pairs"]}, {"M0001"})

    def test_does_not_touch_lots_with_eligible_eqp_count_zero(self):
        lots = self._lots(n=5, eligible_count=0)
        with self.assertRaises(ValueError):
            # eligible_count 0짜리만 있으면 후보가 하나도 없어 부족분을
            # 채울 수 없다 — 조용히 0-lot을 건드리는 대신 에러를 낸다.
            inject_shared_eqp_cases(
                lots, process_ids=["P0001", "P0002"], step_ids=["S0001"],
                eqp_step_rows=EQP_STEP_ROWS, target_count=2, rng=random.Random(0),
            )

    def test_does_not_mutate_original_list_or_lot_dicts(self):
        lots = self._lots()
        original_pairs = [lot["candidate_pairs"] for lot in lots]
        inject_shared_eqp_cases(
            lots, process_ids=["P0001", "P0002"], step_ids=["S0001"],
            eqp_step_rows=EQP_STEP_ROWS, target_count=5, rng=random.Random(0),
        )
        self.assertEqual([lot["candidate_pairs"] for lot in lots], original_pairs)

    def test_injected_lots_only_use_real_eqp_step_pairs(self):
        real_pairs = set()
        for row in EQP_STEP_ROWS:
            for eqp_id in row["eligible_eqp_ids"]:
                real_pairs.add((eqp_id, row["resource_id"]))
        lots = self._lots()
        result = inject_shared_eqp_cases(
            lots, process_ids=["P0001", "P0002"], step_ids=["S0001"],
            eqp_step_rows=EQP_STEP_ROWS, target_count=10, rng=random.Random(0),
        )
        for lot in result:
            for pair in lot["candidate_pairs"]:
                self.assertIn((pair["eqp"], pair["resource"]), real_pairs)

    def test_raises_when_target_exceeds_lot_count(self):
        lots = self._lots(n=3)
        with self.assertRaises(ValueError):
            inject_shared_eqp_cases(
                lots, process_ids=["P0001", "P0002"], step_ids=["S0001"],
                eqp_step_rows=EQP_STEP_ROWS, target_count=5, rng=random.Random(0),
            )

    def test_raises_when_no_qualifying_combination_exists(self):
        rows = [
            {"process_id": "P0001", "step_id": "S0001", "resource_id": "R0001", "eligible_eqp_ids": ["M0001"]},
        ]
        lots = self._lots()
        with self.assertRaises(ValueError):
            inject_shared_eqp_cases(
                lots, process_ids=["P0001"], step_ids=["S0001"],
                eqp_step_rows=rows, target_count=1, rng=random.Random(0),
            )

    def test_reproducible_with_same_seed(self):
        lots = self._lots()
        a = inject_shared_eqp_cases(
            lots, process_ids=["P0001", "P0002"], step_ids=["S0001"],
            eqp_step_rows=EQP_STEP_ROWS, target_count=4, rng=random.Random(3),
        )
        b = inject_shared_eqp_cases(
            lots, process_ids=["P0001", "P0002"], step_ids=["S0001"],
            eqp_step_rows=EQP_STEP_ROWS, target_count=4, rng=random.Random(3),
        )
        self.assertEqual(a, b)


if __name__ == "__main__":
    unittest.main()
