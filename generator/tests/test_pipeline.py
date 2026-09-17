import random
import unittest
from collections import Counter

from generator.pipeline import _merge_disjoint, generate
from generator.master import generate_master_data
from generator.eqp_step import generate_eqp_step_data
from generator.lot_data import generate_lot_data
from generator._util import eligible_eqp_count
from generator.rare_eqp_count_types import generate_lot_data_with_rare_types
from generator.shared_eqp_case import has_shared_eqp_multi_resource

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

    def test_case_ratios_eligible_eqp_count_distribution_controls_histogram(self):
        config = {**CONFIG, "case_ratios": {
            "eligible_eqp_count_distribution": {"1": 0.5, "2": 0.5}
        }}
        data = generate(config)
        counts = Counter(eligible_eqp_count(lot["candidate_pairs"]) for lot in data["lot_data"])
        self.assertEqual(counts, {1: 100, 2: 100})

    def test_case_ratios_rare_eligible_eqp_count_types_carves_out_exact_count(self):
        config = {**CONFIG, "case_ratios": {
            "rare_eligible_eqp_count_types": {"5": {"min_count": 3, "max_count": 6}},
            "eligible_eqp_count_distribution": {"1": 0.5, "2": 0.5},
        }}
        data = generate(config)
        counts = Counter(eligible_eqp_count(lot["candidate_pairs"]) for lot in data["lot_data"])
        self.assertEqual(counts[5], 3)
        self.assertEqual(counts[1] + counts[2], 197)

    def test_without_case_ratios_falls_back_to_t014_behavior(self):
        self.assertNotIn("case_ratios", CONFIG)
        data = generate(CONFIG)
        self.assertEqual(len(data["lot_data"]), 200)

    def _natural_shared_count(self, config):
        without = {k: v for k, v in config.items() if k != "case_ratios"}
        data = generate(without)
        return sum(
            1 for lot in data["lot_data"]
            if has_shared_eqp_multi_resource(lot["candidate_pairs"])
        )

    def test_case_ratios_shared_eqp_multi_resource_guarantees_minimum_count(self):
        # CONFIG의 eqp 풀이 작아 이 성질이 자연적으로도 꽤 나온다 —
        # min_count를 자연 발생 수보다 확실히 크게 잡아야, 주입이 실제로
        # 뭔가 하고 있다는 걸 검증할 수 있다(그러지 않으면 주입 로직을
        # 완전히 비활성화해도 이 테스트는 통과한다).
        baseline = self._natural_shared_count(CONFIG)
        target = baseline + 20
        config = {**CONFIG, "case_ratios": {
            "shared_eqp_multi_resource": {"min_count": target}
        }}
        data = generate(config)
        shared = sum(
            1 for lot in data["lot_data"]
            if has_shared_eqp_multi_resource(lot["candidate_pairs"])
        )
        self.assertGreaterEqual(shared, target)
        self.assertGreater(shared, baseline)

    def test_shared_eqp_case_combines_with_eligible_eqp_count_distribution(self):
        config_without_shared = {**CONFIG, "case_ratios": {
            "eligible_eqp_count_distribution": {"1": 0.5, "2": 0.5},
        }}
        baseline_data = generate(config_without_shared)
        baseline = sum(
            1 for lot in baseline_data["lot_data"]
            if has_shared_eqp_multi_resource(lot["candidate_pairs"])
        )
        target = baseline + 20

        config = {**CONFIG, "case_ratios": {
            "eligible_eqp_count_distribution": {"1": 0.5, "2": 0.5},
            "shared_eqp_multi_resource": {"min_count": target},
        }}
        data = generate(config)
        self.assertEqual(len(data["lot_data"]), 200)
        shared = sum(
            1 for lot in data["lot_data"]
            if has_shared_eqp_multi_resource(lot["candidate_pairs"])
        )
        self.assertGreaterEqual(shared, target)
        # T016이 T015의 히스토그램을 보존해야 한다: 주입 후에도
        # eligible_eqp_count는 여전히 1 또는 2뿐이어야 한다(값을
        # 유지한 채 shared 조합으로만 바꿔치기했다면).
        counts = Counter(eligible_eqp_count(lot["candidate_pairs"]) for lot in data["lot_data"])
        self.assertEqual(set(counts), {1, 2})
        self.assertEqual(counts, {1: 100, 2: 100})

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

    def test_rare_types_path_matches_manual_shared_rng_composition(self):
        # 위 테스트와 같은 이유로, rare_eligible_eqp_count_types 분기도
        # generate()가 실제로 rng를 이어서 쓰는지 직접 확인해야 한다 —
        # 히스토그램만 보는 테스트는 이 분기가 매번 새 rng를 만들어도
        # (T015 리뷰에서 실제로 그랬던 것처럼) 통과한다.
        config = {**CONFIG, "case_ratios": {
            "rare_eligible_eqp_count_types": {"5": {"min_count": 3, "max_count": 6}},
            "eligible_eqp_count_distribution": {"1": 0.5, "2": 0.5},
        }}
        rng = random.Random(config["seed"])
        master = generate_master_data(config, rng=rng)
        eqp_ids = [r["eqp_id"] for r in master["eqp_floor"]]
        resource_ids = [r["resource_id"] for r in master["resources"]]
        eqp_step_result = generate_eqp_step_data(
            config, eqp_ids=eqp_ids, resource_ids=resource_ids, rng=rng
        )
        lot_data = generate_lot_data_with_rare_types(
            config,
            process_ids=eqp_step_result["process_ids"],
            step_ids=eqp_step_result["step_ids"],
            eqp_step_rows=eqp_step_result["eqp_step"],
            rare_types=config["case_ratios"]["rare_eligible_eqp_count_types"],
            distribution=config["case_ratios"]["eligible_eqp_count_distribution"],
            rng=rng,
        )
        expected = _merge_disjoint(master, {"eqp_step": eqp_step_result["eqp_step"]}, lot_data)
        self.assertEqual(generate(config), expected)

    def test_rare_types_combine_with_shared_eqp_multi_resource(self):
        # config.md의 두 예시 config가 둘 다 rare_eligible_eqp_count_types와
        # shared_eqp_multi_resource를 함께 켠다 — T016이 rare로 만든
        # eligible_eqp_count(예: 5)를 보존한 채 shared를 주입할 수
        # 있어야 한다.
        config = {**CONFIG, "case_ratios": {
            "rare_eligible_eqp_count_types": {"5": {"min_count": 3, "max_count": 6}},
            "eligible_eqp_count_distribution": {"1": 0.5, "2": 0.5},
            "shared_eqp_multi_resource": {"min_count": 5},
        }}
        data = generate(config)
        counts = Counter(eligible_eqp_count(lot["candidate_pairs"]) for lot in data["lot_data"])
        self.assertEqual(counts[5], 3)
        self.assertEqual(counts[1] + counts[2], 197)
        shared = sum(
            1 for lot in data["lot_data"]
            if has_shared_eqp_multi_resource(lot["candidate_pairs"])
        )
        self.assertGreaterEqual(shared, 5)

    def test_reproducible_end_to_end(self):
        self.assertEqual(generate(CONFIG), generate(CONFIG))


if __name__ == "__main__":
    unittest.main()
