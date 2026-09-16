import random
import unittest

from generator.pipeline import _merge_disjoint, generate
from generator.master import generate_master_data
from generator.eqp_step import generate_eqp_step_data
from generator.lot_data import generate_lot_data

CONFIG = {
    "seed": 42,
    "scale": {
        "lot_count": 200,
        "eqp_count": 8,
        "resource_count": 5,
        "floor_count": 3,
        "location_count": 5,
        "process_count": 2,
        "step_count": 4,
    },
}


class TestMergeDisjoint(unittest.TestCase):
    def test_merges_non_overlapping_tables(self):
        self.assertEqual(_merge_disjoint({"a": 1}, {"b": 2}), {"a": 1, "b": 2})

    def test_rejects_overlapping_keys(self):
        with self.assertRaises(ValueError):
            _merge_disjoint({"a": 1}, {"a": 2})


class TestPipeline(unittest.TestCase):
    def test_returns_all_expected_tables_with_correct_sizes(self):
        data = generate(CONFIG)
        self.assertEqual(set(data.keys()), {"eqp_floor", "resources", "eqp_step", "lot_data"})
        self.assertEqual(len(data["eqp_floor"]), 8)
        self.assertEqual(len(data["resources"]), 5)
        self.assertEqual(len(data["lot_data"]), 200)

    def test_eqp_step_only_references_master_ids(self):
        data = generate(CONFIG)
        eqp_ids = {r["eqp_id"] for r in data["eqp_floor"]}
        resource_ids = {r["resource_id"] for r in data["resources"]}
        for row in data["eqp_step"]:
            self.assertIn(row["resource_id"], resource_ids)
            for eqp_id in row["eligible_eqp_ids"]:
                self.assertIn(eqp_id, eqp_ids)

    def test_lot_data_pairs_only_reference_master_ids_and_are_non_empty(self):
        data = generate(CONFIG)
        eqp_ids = {r["eqp_id"] for r in data["eqp_floor"]}
        resource_ids = {r["resource_id"] for r in data["resources"]}
        for lot in data["lot_data"]:
            self.assertGreater(len(lot["candidate_pairs"]), 0)
            for pair in lot["candidate_pairs"]:
                self.assertIn(pair["eqp"], eqp_ids)
                self.assertIn(pair["resource"], resource_ids)

    def test_eqp_step_rng_continues_from_master_rng(self):
        # master가 rng에서 먼저 뽑아 쓴 뒤, eqp_step이 "이어서" 뽑아야
        # 한다. 두 단계 모두 각자 새 random.Random(seed)로 독립적으로
        # 돌리면(공유 안 함) 다른 결과가 나와야 공유가 실제로 일어난
        # 것이다.
        shared = generate(CONFIG)

        master_isolated = generate_master_data(CONFIG, rng=random.Random(CONFIG["seed"]))
        eqp_ids = [r["eqp_id"] for r in master_isolated["eqp_floor"]]
        resource_ids = [r["resource_id"] for r in master_isolated["resources"]]
        eqp_step_isolated = generate_eqp_step_data(
            CONFIG, eqp_ids=eqp_ids, resource_ids=resource_ids,
            rng=random.Random(CONFIG["seed"]),
        )
        self.assertNotEqual(shared["eqp_step"], eqp_step_isolated["eqp_step"])

    def test_lot_data_rng_continues_from_eqp_step_rng(self):
        # 위와 같은 이유로, lot_data에도 eqp_step까지 소비한 뒤의 rng를
        # 그대로 넘겨야 한다. 여기서는 process_ids/step_ids/eqp_step_rows를
        # 실제 파이프라인과 "완전히 동일하게" 고정해 두고 rng만 공유
        # 여부를 바꿔서, 다른 입력 때문이 아니라 rng 공유 자체가
        # 차이를 만드는지 확인한다.
        rng = random.Random(CONFIG["seed"])
        master = generate_master_data(CONFIG, rng=rng)
        eqp_ids = [r["eqp_id"] for r in master["eqp_floor"]]
        resource_ids = [r["resource_id"] for r in master["resources"]]
        eqp_step_result = generate_eqp_step_data(
            CONFIG, eqp_ids=eqp_ids, resource_ids=resource_ids, rng=rng
        )

        shared_lot_data = generate_lot_data(
            CONFIG,
            process_ids=eqp_step_result["process_ids"],
            step_ids=eqp_step_result["step_ids"],
            eqp_step_rows=eqp_step_result["eqp_step"],
            rng=rng,  # eqp_step까지 소비한 바로 그 rng를 이어서 씀
        )
        fresh_seed_lot_data = generate_lot_data(
            CONFIG,
            process_ids=eqp_step_result["process_ids"],
            step_ids=eqp_step_result["step_ids"],
            eqp_step_rows=eqp_step_result["eqp_step"],
            rng=random.Random(CONFIG["seed"]),  # 처음부터 다시 시작(버그 재현)
        )
        self.assertNotEqual(shared_lot_data["lot_data"], fresh_seed_lot_data["lot_data"])

    def test_generate_matches_manual_shared_rng_composition(self):
        # 위 두 테스트는 "rng를 공유하면 결과가 달라진다"는 일반적 사실만
        # 보여줄 뿐, generate() 자체가 실제로 공유하는지는 확인하지 못한다
        # (각 단계 함수를 직접 호출하기 때문). 여기서는 generate(CONFIG)의
        # 출력을, "하나의 rng를 만들어 세 단계에 순서대로 그대로 넘긴"
        # 수동 조합과 직접 비교한다 — pipeline.py 내부가 이 조합에서
        # 조금이라도 벗어나면(예: 특정 단계에 새 rng를 만들어 넘기면)
        # 이 등식이 깨진다.
        rng = random.Random(CONFIG["seed"])
        master = generate_master_data(CONFIG, rng=rng)
        eqp_ids = [r["eqp_id"] for r in master["eqp_floor"]]
        resource_ids = [r["resource_id"] for r in master["resources"]]
        eqp_step_result = generate_eqp_step_data(
            CONFIG, eqp_ids=eqp_ids, resource_ids=resource_ids, rng=rng
        )
        lot_data = generate_lot_data(
            CONFIG,
            process_ids=eqp_step_result["process_ids"],
            step_ids=eqp_step_result["step_ids"],
            eqp_step_rows=eqp_step_result["eqp_step"],
            rng=rng,
        )
        expected = _merge_disjoint(master, {"eqp_step": eqp_step_result["eqp_step"]}, lot_data)
        self.assertEqual(generate(CONFIG), expected)

    def test_reproducible_end_to_end(self):
        self.assertEqual(generate(CONFIG), generate(CONFIG))


if __name__ == "__main__":
    unittest.main()
