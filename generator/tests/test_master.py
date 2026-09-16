import random
import unittest

from generator.master import generate_equipment_floors, generate_master_data, generate_resources


class TestGenerateEquipmentFloors(unittest.TestCase):
    def test_counts_and_uniqueness(self):
        rows = generate_equipment_floors(80, 5, random.Random(1))
        self.assertEqual(len(rows), 80)
        ids = [r["eqp_id"] for r in rows]
        self.assertEqual(len(set(ids)), 80)

    def test_id_width_stable_across_scale(self):
        # 자릿수가 eqp_count에 따라 달라지면 서로 다른 규모의 데이터셋
        # 사이에서 같은 순번의 설비가 서로 다른 id를 갖게 된다(master.py
        # 모듈 docstring 참고) — "1번" 설비는 규모와 무관하게 같은 문자열.
        small = generate_equipment_floors(8, 2, random.Random(0))
        large = generate_equipment_floors(800, 2, random.Random(0))
        self.assertEqual(small[0]["eqp_id"], large[0]["eqp_id"])

    def test_floor_range_and_full_coverage(self):
        rows = generate_equipment_floors(80, 5, random.Random(1))
        floors = {r["floor"] for r in rows}
        self.assertTrue(all(1 <= r["floor"] <= 5 for r in rows))
        self.assertEqual(floors, {1, 2, 3, 4, 5})

    def test_floor_coverage_at_smoke_scale_across_seeds(self):
        for seed in range(200):
            rows = generate_equipment_floors(8, 3, random.Random(seed))
            floors = {r["floor"] for r in rows}
            self.assertEqual(floors, {1, 2, 3}, f"seed {seed} missed a floor")

    def test_reproducible_with_same_seed(self):
        a = generate_equipment_floors(80, 5, random.Random(42))
        b = generate_equipment_floors(80, 5, random.Random(42))
        self.assertEqual(a, b)

    def test_rejects_non_positive_and_non_int(self):
        for bad in (0, -1, 3.0, True):
            with self.assertRaises(ValueError):
                generate_equipment_floors(bad, 2, random.Random(0))
            with self.assertRaises(ValueError):
                generate_equipment_floors(5, bad, random.Random(0))

    def test_rejects_more_floors_than_equipment(self):
        with self.assertRaises(ValueError):
            generate_equipment_floors(2, 5, random.Random(0))


class TestGenerateResources(unittest.TestCase):
    def test_counts_and_uniqueness(self):
        rows = generate_resources(24)
        self.assertEqual(len(rows), 24)
        ids = [r["resource_id"] for r in rows]
        self.assertEqual(len(set(ids)), 24)

    def test_rejects_non_positive_and_non_int(self):
        for bad in (0, -1, 3.0, True):
            with self.assertRaises(ValueError):
                generate_resources(bad)


class TestGenerateMasterData(unittest.TestCase):
    def _config(self):
        return {
            "seed": 1,
            "scale": {"eqp_count": 8, "resource_count": 5, "floor_count": 3},
        }

    def test_output_keys_and_sizes(self):
        data = generate_master_data(self._config())
        self.assertEqual(set(data.keys()), {"eqp_floor", "resources"})
        self.assertEqual(len(data["eqp_floor"]), 8)
        self.assertEqual(len(data["resources"]), 5)

    def test_reproducible_without_explicit_rng(self):
        config = self._config()
        self.assertEqual(generate_master_data(config), generate_master_data(config))


if __name__ == "__main__":
    unittest.main()
