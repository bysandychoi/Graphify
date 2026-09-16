import random
import unittest
from collections import defaultdict

from generator.eqp_step import (
    generate_eqp_step,
    generate_eqp_step_data,
    generate_process_ids,
    generate_step_ids,
)

EQP_IDS = [f"M{i:04d}" for i in range(1, 11)]
RESOURCE_IDS = [f"R{i:04d}" for i in range(1, 6)]


def _make_rows(seed=1, process_count=3, step_count=4):
    process_ids = generate_process_ids(process_count)
    step_ids = generate_step_ids(step_count)
    return generate_eqp_step(
        process_ids=process_ids, step_ids=step_ids,
        resource_ids=RESOURCE_IDS, eqp_ids=EQP_IDS, rng=random.Random(seed),
    )


class TestGenerateProcessAndStepIds(unittest.TestCase):
    def test_process_id_format(self):
        self.assertEqual(generate_process_ids(3), ["P0001", "P0002", "P0003"])

    def test_step_id_format(self):
        self.assertEqual(generate_step_ids(2), ["S0001", "S0002"])

    def test_id_width_stable_across_scale(self):
        # 자릿수가 process_count/step_count 값에 따라 달라지면 서로 다른
        # 규모의 데이터셋 사이에서 같은 순번의 id가 달라진다(master.py와
        # 같은 이유). "1번" id는 항상 같은 문자열이어야 한다.
        self.assertEqual(generate_process_ids(3)[0], generate_process_ids(300)[0])
        self.assertEqual(generate_step_ids(3)[0], generate_step_ids(300)[0])


class TestGenerateEqpStep(unittest.TestCase):
    def test_unique_process_step_resource_key(self):
        rows = _make_rows()
        keys = [(r["process_id"], r["step_id"], r["resource_id"]) for r in rows]
        self.assertEqual(len(keys), len(set(keys)))

    def test_step_id_reused_across_processes(self):
        rows = _make_rows(process_count=3, step_count=4)
        step_to_processes = defaultdict(set)
        for r in rows:
            step_to_processes[r["step_id"]].add(r["process_id"])
        self.assertTrue(any(len(procs) > 1 for procs in step_to_processes.values()))

    def test_same_step_can_have_differing_eligible_sets_across_resources(self):
        # 완료 기준: 같은 step에서 resource별 가능 설비 집합이 다르게 생성될 수 있음.
        found_difference = False
        for seed in range(50):
            rows = _make_rows(seed=seed)
            by_process_step = defaultdict(list)
            for r in rows:
                by_process_step[(r["process_id"], r["step_id"])].append(r)
            for group in by_process_step.values():
                sets_ = {tuple(sorted(g["eligible_eqp_ids"])) for g in group}
                if len(sets_) > 1:
                    found_difference = True
                    break
            if found_difference:
                break
        self.assertTrue(found_difference)

    def test_only_references_given_ids(self):
        rows = _make_rows()
        for r in rows:
            self.assertIn(r["resource_id"], RESOURCE_IDS)
            for eqp_id in r["eligible_eqp_ids"]:
                self.assertIn(eqp_id, EQP_IDS)

    def test_eligible_eqp_ids_never_empty_with_default_bounds(self):
        for seed in range(50):
            for row in _make_rows(seed=seed):
                self.assertGreaterEqual(len(row["eligible_eqp_ids"]), 1)

    def test_degenerate_single_resource_and_equipment_does_not_crash(self):
        # AC는 "달라질 수 있음"(가능성)이지 "항상 달라야 함"이 아니므로,
        # resource/eqp가 1개뿐이라 모든 집합이 같아지는 것도 유효한 결과다.
        rows = generate_eqp_step(
            process_ids=["P0001"], step_ids=["S0001"],
            resource_ids=["R0001"], eqp_ids=["M0001"], rng=random.Random(0),
        )
        self.assertEqual(rows, [{
            "process_id": "P0001", "step_id": "S0001",
            "resource_id": "R0001", "eligible_eqp_ids": ["M0001"],
        }])

    def test_reproducible_with_same_seed(self):
        self.assertEqual(_make_rows(seed=7), _make_rows(seed=7))

    def test_rejects_duplicate_process_ids(self):
        with self.assertRaises(ValueError):
            generate_eqp_step(
                process_ids=["P01", "P01"], step_ids=["S01"],
                resource_ids=RESOURCE_IDS, eqp_ids=EQP_IDS, rng=random.Random(0),
            )

    def test_rejects_duplicate_step_ids(self):
        with self.assertRaises(ValueError):
            generate_eqp_step(
                process_ids=["P01"], step_ids=["S01", "S01"],
                resource_ids=RESOURCE_IDS, eqp_ids=EQP_IDS, rng=random.Random(0),
            )

    def test_rejects_duplicate_resource_ids(self):
        with self.assertRaises(ValueError):
            generate_eqp_step(
                process_ids=["P01"], step_ids=["S01"],
                resource_ids=["R1", "R1"], eqp_ids=EQP_IDS, rng=random.Random(0),
            )

    def test_rejects_duplicate_eqp_ids(self):
        with self.assertRaises(ValueError):
            generate_eqp_step(
                process_ids=["P01"], step_ids=["S01"],
                resource_ids=RESOURCE_IDS, eqp_ids=["M1", "M1"], rng=random.Random(0),
            )

    def test_rejects_empty_resource_or_eqp_ids(self):
        with self.assertRaises(ValueError):
            generate_eqp_step(
                process_ids=["P01"], step_ids=["S01"],
                resource_ids=[], eqp_ids=EQP_IDS, rng=random.Random(0),
            )
        with self.assertRaises(ValueError):
            generate_eqp_step(
                process_ids=["P01"], step_ids=["S01"],
                resource_ids=RESOURCE_IDS, eqp_ids=[], rng=random.Random(0),
            )

    def test_rejects_invalid_bounds(self):
        with self.assertRaises(ValueError):
            generate_eqp_step(
                process_ids=["P01"], step_ids=["S01"],
                resource_ids=RESOURCE_IDS, eqp_ids=EQP_IDS,
                rng=random.Random(0), resources_per_step=(5, 2),
            )
        with self.assertRaises(ValueError):
            generate_eqp_step(
                process_ids=["P01"], step_ids=["S01"],
                resource_ids=RESOURCE_IDS, eqp_ids=EQP_IDS,
                rng=random.Random(0), eqp_per_resource=(0, 2),
            )

    def test_rejects_invalid_bounds_even_when_process_or_step_ids_empty(self):
        # bounds 검증이 루프 안에서만 일어나면, process_ids/step_ids가
        # 비어 루프가 안 도는 경우 명백히 잘못된 bounds가 조용히 통과한다.
        with self.assertRaises(ValueError):
            generate_eqp_step(
                process_ids=[], step_ids=[],
                resource_ids=RESOURCE_IDS, eqp_ids=EQP_IDS,
                rng=random.Random(0), eqp_per_resource=(0, 0),
            )

    def test_rejects_lower_bound_exceeding_available_candidates(self):
        with self.assertRaises(ValueError):
            generate_eqp_step(
                process_ids=["P01"], step_ids=["S01"],
                resource_ids=["R0001"], eqp_ids=EQP_IDS,
                rng=random.Random(0), resources_per_step=(2, 3),
            )

    def test_all_id_list_args_are_keyword_only(self):
        with self.assertRaises(TypeError):
            # pylint: disable-next=too-many-function-args,missing-kwoa
            generate_eqp_step(["P01"], ["S01"], RESOURCE_IDS, EQP_IDS, random.Random(0))


class TestGenerateEqpStepData(unittest.TestCase):
    def test_ids_are_keyword_only(self):
        config = {"seed": 1, "scale": {"process_count": 2, "step_count": 2}}
        with self.assertRaises(TypeError):
            # pylint: disable-next=missing-kwoa,too-many-function-args
            generate_eqp_step_data(config, EQP_IDS, RESOURCE_IDS)

    def test_reproducible_without_explicit_rng(self):
        config = {"seed": 1, "scale": {"process_count": 2, "step_count": 2}}
        a = generate_eqp_step_data(config, eqp_ids=EQP_IDS, resource_ids=RESOURCE_IDS)
        b = generate_eqp_step_data(config, eqp_ids=EQP_IDS, resource_ids=RESOURCE_IDS)
        self.assertEqual(a, b)


if __name__ == "__main__":
    unittest.main()
