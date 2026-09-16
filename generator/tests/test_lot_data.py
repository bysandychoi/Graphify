import random
import unittest

from generator._util import eligible_eqp_count
from generator.eqp_step import generate_eqp_step, generate_process_ids, generate_step_ids
from generator.lot_data import build_candidate_pairs, generate_lot_data

EQP_STEP_ROWS = [
    {"process_id": "P01", "step_id": "S01", "resource_id": "R01", "eligible_eqp_ids": ["M01", "M02"]},
    {"process_id": "P01", "step_id": "S01", "resource_id": "R02", "eligible_eqp_ids": ["M03"]},
    {"process_id": "P02", "step_id": "S01", "resource_id": "R01", "eligible_eqp_ids": ["M02", "M04"]},
    {"process_id": "P01", "step_id": "S02", "resource_id": "R03", "eligible_eqp_ids": ["M05"]},
]


class TestBuildCandidatePairs(unittest.TestCase):
    def test_only_uses_rows_matching_process_and_step(self):
        pairs = build_candidate_pairs("P01", "S02", EQP_STEP_ROWS)
        self.assertEqual(pairs, [{"eqp": "M05", "resource": "R03"}])

    def test_different_process_same_step_gives_different_pairs(self):
        # 이게 T014의 핵심 결정이다: step_id만으로 묶지 않고 (process,step)로
        # 묶으므로, 같은 step이라도 process를 바꾸면 결과가 달라진다.
        p01_pairs = build_candidate_pairs("P01", "S01", EQP_STEP_ROWS)
        p02_pairs = build_candidate_pairs("P02", "S01", EQP_STEP_ROWS)
        self.assertNotEqual(
            {(p["eqp"], p["resource"]) for p in p01_pairs},
            {(p["eqp"], p["resource"]) for p in p02_pairs},
        )

    def test_does_not_imply_unlisted_pairs(self):
        # 완료 기준: (M01,R01),(M02,R02) 존재해도 (M01,R02)가 암시되지 않음.
        rows = [
            {"process_id": "P01", "step_id": "S01", "resource_id": "R01", "eligible_eqp_ids": ["M01"]},
            {"process_id": "P01", "step_id": "S01", "resource_id": "R02", "eligible_eqp_ids": ["M02"]},
        ]
        pairs = build_candidate_pairs("P01", "S01", rows)
        self.assertEqual(
            sorted(pairs, key=lambda p: p["eqp"]),
            [{"eqp": "M01", "resource": "R01"}, {"eqp": "M02", "resource": "R02"}],
        )
        self.assertNotIn({"eqp": "M01", "resource": "R02"}, pairs)

    def test_eligible_eqp_count_matches_lot_data_md_worked_example(self):
        # lot_data.md의 예시 그대로: (M03,R01),(M03,R02) -> eligible_eqp_count는
        # 2가 아니라 1이다(M03 하나뿐). 재구현이 아니라 문서의 리터럴 값을 박아
        # 둔다 — eligible_eqp_count() 자체가 잘못돼도 이 테스트는 이를 잡는다.
        rows = [
            {"process_id": "P01", "step_id": "S01", "resource_id": "R01", "eligible_eqp_ids": ["M03"]},
            {"process_id": "P01", "step_id": "S01", "resource_id": "R02", "eligible_eqp_ids": ["M03"]},
        ]
        pairs = build_candidate_pairs("P01", "S01", rows)
        self.assertEqual(eligible_eqp_count(pairs), 1)

    def test_dedupes_pairs_within_same_process_and_step(self):
        rows = [
            {"process_id": "P01", "step_id": "S01", "resource_id": "R01", "eligible_eqp_ids": ["M01", "M02"]},
            {"process_id": "P01", "step_id": "S01", "resource_id": "R01", "eligible_eqp_ids": ["M01"]},
        ]
        pairs = build_candidate_pairs("P01", "S01", rows)
        keys = [(p["eqp"], p["resource"]) for p in pairs]
        self.assertEqual(len(keys), len(set(keys)))

    def test_empty_when_no_matching_row(self):
        self.assertEqual(build_candidate_pairs("P99", "S99", EQP_STEP_ROWS), [])


class TestGenerateLotData(unittest.TestCase):
    def _config(self, lot_count=50, factor=None):
        scale = {"lot_count": lot_count}
        if factor is not None:
            scale["factor"] = factor
        return {"seed": 1, "scale": scale}

    def _full_coverage_rows(self, process_count=2, step_count=3, seed=1):
        # 실제 파이프라인처럼 모든 (process,step) 조합에 최소 1개
        # resource/eqp가 있는 eqp_step 행 집합.
        process_ids = generate_process_ids(process_count)
        step_ids = generate_step_ids(step_count)
        return process_ids, step_ids, generate_eqp_step(
            process_ids=process_ids, step_ids=step_ids,
            resource_ids=["R0001", "R0002", "R0003"], eqp_ids=["M0001", "M0002", "M0003"],
            rng=random.Random(seed),
        )

    def test_lot_count_matches_effective_lot_count(self):
        process_ids, step_ids, rows = self._full_coverage_rows()
        data = generate_lot_data(
            self._config(lot_count=200, factor=0.1),
            process_ids=process_ids, step_ids=step_ids, eqp_step_rows=rows,
        )
        self.assertEqual(len(data["lot_data"]), 20)

    def test_lot_ids_unique(self):
        process_ids, step_ids, rows = self._full_coverage_rows()
        data = generate_lot_data(
            self._config(lot_count=100), process_ids=process_ids, step_ids=step_ids,
            eqp_step_rows=rows,
        )
        ids = [lot["lot_id"] for lot in data["lot_data"]]
        self.assertEqual(len(ids), len(set(ids)))

    def test_lot_id_width_stable_across_scale(self):
        process_ids, step_ids, rows = self._full_coverage_rows()
        small = generate_lot_data(
            self._config(lot_count=8), process_ids=process_ids, step_ids=step_ids,
            eqp_step_rows=rows, rng=random.Random(0),
        )
        large = generate_lot_data(
            self._config(lot_count=8000), process_ids=process_ids, step_ids=step_ids,
            eqp_step_rows=rows, rng=random.Random(0),
        )
        self.assertEqual(small["lot_data"][0]["lot_id"], large["lot_data"][0]["lot_id"])

    def test_every_lot_has_non_empty_candidate_pairs_with_full_coverage(self):
        # 모든 (process,step) 조합에 행이 있으면, 어떤 process/step을
        # 뽑아도 candidate_pairs가 비어 있으면 안 된다. 이 함수가
        # 항상 []을 반환하도록 망가지면 이 테스트가 잡는다.
        process_ids, step_ids, rows = self._full_coverage_rows()
        data = generate_lot_data(
            self._config(lot_count=100), process_ids=process_ids, step_ids=step_ids,
            eqp_step_rows=rows,
        )
        for lot in data["lot_data"]:
            self.assertGreater(len(lot["candidate_pairs"]), 0)

    def test_lots_show_more_than_one_distinct_candidate_pairs_set(self):
        # process_count x step_count 조합이 여러 개면, lot마다 서로 다른
        # candidate_pairs가 나올 수 있어야 한다(step만으로 묶으면 이
        # 다양성이 step_count 종류로 눌린다).
        process_ids, step_ids, rows = self._full_coverage_rows(process_count=3, step_count=4)
        data = generate_lot_data(
            self._config(lot_count=200), process_ids=process_ids, step_ids=step_ids,
            eqp_step_rows=rows,
        )
        distinct = {
            tuple(sorted((p["eqp"], p["resource"]) for p in lot["candidate_pairs"]))
            for lot in data["lot_data"]
        }
        self.assertGreater(len(distinct), len(step_ids))

    def test_every_lot_eligible_eqp_count_matches_its_pairs(self):
        process_ids, step_ids, rows = self._full_coverage_rows()
        data = generate_lot_data(
            self._config(lot_count=100), process_ids=process_ids, step_ids=step_ids,
            eqp_step_rows=rows,
        )
        for lot in data["lot_data"]:
            unique_eqp = {p["eqp"] for p in lot["candidate_pairs"]}
            self.assertEqual(eligible_eqp_count(lot["candidate_pairs"]), len(unique_eqp))

    def test_current_step_is_one_of_given_step_ids(self):
        process_ids, step_ids, rows = self._full_coverage_rows()
        data = generate_lot_data(
            self._config(lot_count=50), process_ids=process_ids, step_ids=step_ids,
            eqp_step_rows=rows,
        )
        for lot in data["lot_data"]:
            self.assertIn(lot["current_step"], step_ids)

    def test_current_step_never_encodes_process_id(self):
        process_ids, step_ids, rows = self._full_coverage_rows()
        data = generate_lot_data(
            self._config(lot_count=50), process_ids=process_ids, step_ids=step_ids,
            eqp_step_rows=rows,
        )
        for lot in data["lot_data"]:
            self.assertNotIn(lot["current_step"], process_ids)

    def test_reproducible_with_same_seed(self):
        process_ids, step_ids, rows = self._full_coverage_rows()
        a = generate_lot_data(
            self._config(), process_ids=process_ids, step_ids=step_ids, eqp_step_rows=rows,
            rng=random.Random(1),
        )
        b = generate_lot_data(
            self._config(), process_ids=process_ids, step_ids=step_ids, eqp_step_rows=rows,
            rng=random.Random(1),
        )
        self.assertEqual(a, b)

    def test_rejects_empty_process_or_step_ids(self):
        with self.assertRaises(ValueError):
            generate_lot_data(self._config(), process_ids=[], step_ids=["S01"], eqp_step_rows=[])
        with self.assertRaises(ValueError):
            generate_lot_data(self._config(), process_ids=["P01"], step_ids=[], eqp_step_rows=[])

    def test_rejects_duplicate_process_or_step_ids(self):
        with self.assertRaises(ValueError):
            generate_lot_data(
                self._config(), process_ids=["P01", "P01"], step_ids=["S01"], eqp_step_rows=[]
            )
        with self.assertRaises(ValueError):
            generate_lot_data(
                self._config(), process_ids=["P01"], step_ids=["S01", "S01"], eqp_step_rows=[]
            )


if __name__ == "__main__":
    unittest.main()
