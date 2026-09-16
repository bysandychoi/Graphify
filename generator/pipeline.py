"""생성기 단계를 순서대로 이어 붙이는 진입점.

config.md "seed" 절의 계약(생성기 전체가 random.Random(seed) 인스턴스
하나를 공유한다)을 지키기 위해, 이 모듈이 rng를 한 번만 만들어 모든
단계 함수에 명시적으로 넘긴다 — 각 단계 함수의 rng 기본값(None이면
새로 만듦)은 단독 호출/테스트 편의이며 이 파이프라인은 쓰지 않는다.
"""
import random

from generator.master import generate_master_data
from generator.eqp_step import generate_eqp_step_data
from generator.lot_data import generate_lot_data


def _merge_disjoint(*tables: dict) -> dict:
    merged = {}
    for table in tables:
        overlap = set(merged) & set(table)
        if overlap:
            raise ValueError(f"duplicate output keys from generator stages: {overlap}")
        merged.update(table)
    return merged


def generate(config: dict) -> dict:
    rng = random.Random(config["seed"])
    master = generate_master_data(config, rng=rng)
    eqp_ids = [row["eqp_id"] for row in master["eqp_floor"]]
    resource_ids = [row["resource_id"] for row in master["resources"]]
    eqp_step_result = generate_eqp_step_data(
        config, eqp_ids=eqp_ids, resource_ids=resource_ids, rng=rng
    )
    lot_data = generate_lot_data(
        config,
        process_ids=eqp_step_result["process_ids"],
        step_ids=eqp_step_result["step_ids"],
        eqp_step_rows=eqp_step_result["eqp_step"],
        rng=rng,
    )
    return _merge_disjoint(master, {"eqp_step": eqp_step_result["eqp_step"]}, lot_data)
