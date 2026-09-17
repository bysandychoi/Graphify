"""생성기 단계를 순서대로 이어 붙이는 진입점.

config.md "seed" 절의 계약(생성기 전체가 random.Random(seed) 인스턴스
하나를 공유한다)을 지키기 위해, 이 모듈이 rng를 한 번만 만들어 모든
단계 함수에 명시적으로 넘긴다 — 각 단계 함수의 rng 기본값(None이면
새로 만듦)은 단독 호출/테스트 편의이며 이 파이프라인은 쓰지 않는다.
"""
import random

from generator._util import effective_lot_count, resolve_ratio_or_count
from generator.master import generate_master_data
from generator.eqp_step import generate_eqp_step_data
from generator.lot_data import generate_lot_data
from generator.eqp_count_distribution import generate_lot_data_with_distribution
from generator.shared_eqp_case import inject_shared_eqp_cases


def _merge_disjoint(*tables: dict) -> dict:
    merged = {}
    for table in tables:
        overlap = set(merged) & set(table)
        if overlap:
            raise ValueError(f"duplicate output keys from generator stages: {overlap}")
        merged.update(table)
    return merged


def _case_ratios(config: dict) -> dict:
    # config["case_ratios"]가 아예 없을 수도, {}일 수도, JSON에서
    # `"case_ratios": null`로 명시됐을 수도 있다 — 셋 다 "없음"으로
    # 취급한다(.get(..., {})만 쓰면 명시적 null일 때 None을 돌려줘
    # 다음 .get() 호출에서 AttributeError가 난다).
    return config.get("case_ratios") or {}


def _generate_lot_data(config: dict, *, process_ids: list, step_ids: list,
                        eqp_step_rows: list, rng: random.Random) -> dict:
    distribution = _case_ratios(config).get("eligible_eqp_count_distribution")
    if distribution is None:
        return generate_lot_data(
            config, process_ids=process_ids, step_ids=step_ids,
            eqp_step_rows=eqp_step_rows, rng=rng,
        )
    return generate_lot_data_with_distribution(
        config, process_ids=process_ids, step_ids=step_ids,
        eqp_step_rows=eqp_step_rows, distribution=distribution, rng=rng,
    )


def _apply_shared_eqp_case(config: dict, *, lots: list, process_ids: list, step_ids: list,
                            eqp_step_rows: list, rng: random.Random) -> list:
    spec = _case_ratios(config).get("shared_eqp_multi_resource")
    if spec is None:
        return lots
    target_count = resolve_ratio_or_count(spec, effective_lot_count(config))
    return inject_shared_eqp_cases(
        lots, process_ids=process_ids, step_ids=step_ids, eqp_step_rows=eqp_step_rows,
        target_count=target_count, rng=rng,
    )


def generate(config: dict) -> dict:
    rng = random.Random(config["seed"])
    master = generate_master_data(config, rng=rng)
    eqp_ids = [row["eqp_id"] for row in master["eqp_floor"]]
    resource_ids = [row["resource_id"] for row in master["resources"]]
    eqp_step_result = generate_eqp_step_data(
        config, eqp_ids=eqp_ids, resource_ids=resource_ids, rng=rng
    )
    process_ids = eqp_step_result["process_ids"]
    step_ids = eqp_step_result["step_ids"]
    eqp_step_rows = eqp_step_result["eqp_step"]
    lot_data = _generate_lot_data(
        config, process_ids=process_ids, step_ids=step_ids,
        eqp_step_rows=eqp_step_rows, rng=rng,
    )
    lot_data["lot_data"] = _apply_shared_eqp_case(
        config, lots=lot_data["lot_data"], process_ids=process_ids, step_ids=step_ids,
        eqp_step_rows=eqp_step_rows, rng=rng,
    )
    return _merge_disjoint(master, {"eqp_step": eqp_step_rows}, lot_data)
