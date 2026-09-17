"""T017: 드문 설비 수 유형(rare_eligible_eqp_count_types) 케이스 주입.

config.md의 `case_ratios.rare_eligible_eqp_count_types`는 특정
`eligible_eqp_count` 값의 건수를 [min_count, max_count] 절대 범위로
직접 지정해 "드문 유형"을 만든다 — `eligible_eqp_count_distribution`
(T015)과 같은 값을 동시에 지정할 수 없고, 유효 lot 수 = 이 필드가
만든 건수 총합 + `eligible_eqp_count_distribution`이 분배하는
나머지다(config.md 필드 목록 참고).

**이 모듈은 각 드문 유형에 정확히 `min_count`만큼만 배정한다** —
`max_count`는 상한 검증에만 쓰고, [min_count, max_count] 범위에서
무작위로 개수를 고르지 않는다. min_count 자체가 이미 "최소 이만큼
보장"이므로 그 이상 늘릴 이유가 없고(다른 case_ratios 필드도 전부
"최소" 의미론이다), T017 완료 기준 "1~수 개 lot에서만 등장"도 실제
등장 건수를 최소값 그대로 두는 쪽이 "드문" 상태에 가장 가깝다.
**config.md의 "5~8건" 같은 서술은 이 설계 결정에 맞춰 갱신해야 한다**
— 거기 남아 있는 "범위 안에서 실현된다"는 뉘앙스는 이 구현과
맞지 않는다.

각 드문 유형의 스펙 객체는 config.md "잘못된 config" 규칙(구조 키
자리에 목록 밖 키가 있으면 에러, 빈 객체는 에러)을 그대로 따른다 —
`min_count`가 없거나 철자가 틀리면 조용히 0건으로 새지 않고 에러를
낸다.

드문 유형이 차지한 lot 수를 유효 lot 수에서 뺀 "나머지"만
`eligible_eqp_count_distribution`에 넘긴다(`generator.eqp_count_distribution.
allocate_target_counts` 그대로 재사용, 나머지가 0이어도 distribution이
있으면 그 구조를 검증한다). 나머지가 있는데 distribution이 없으면
에러를 낸다. lot 조립(어떤 (process,step)에서 후보를 뽑을지)은
`generator.eqp_count_distribution.lots_from_targets`를 그대로
재사용해, T015와 다른 탐색 로직이 따로 생기지 않게 한다.
"""
import random

from generator._util import effective_lot_count
from generator.eqp_count_distribution import (
    allocate_target_counts,
    check_process_and_step_ids,
    lots_from_targets,
    parse_value_key,
)

_RARE_FIELD_NAME = "rare_eligible_eqp_count_types"
_SPEC_KEYS = {"min_count", "max_count"}


def _rare_spec(key: str, spec, max_value: int) -> tuple:
    value = parse_value_key(key, max_value, field_name=_RARE_FIELD_NAME)
    if not isinstance(spec, dict) or not spec:
        raise ValueError(f"{_RARE_FIELD_NAME}[{key!r}] must be a non-empty object, got {spec!r}")
    unknown = set(spec) - _SPEC_KEYS
    if unknown:
        raise ValueError(f"{_RARE_FIELD_NAME}[{key!r}] has unknown keys: {sorted(unknown)}")
    if "min_count" not in spec:
        raise ValueError(f"{_RARE_FIELD_NAME}[{key!r}] must have min_count")

    min_count = spec["min_count"]
    max_count = spec.get("max_count")
    if isinstance(min_count, bool) or not isinstance(min_count, int) or min_count < 0:
        raise ValueError(f"{_RARE_FIELD_NAME}[{key!r}].min_count must be a non-negative int")
    if max_count is not None:
        if isinstance(max_count, bool) or not isinstance(max_count, int) or max_count < min_count:
            raise ValueError(
                f"{_RARE_FIELD_NAME}[{key!r}].max_count must be an int >= min_count"
            )
    return value, min_count


def _collect_rare_counts(rare_types: dict, distribution: dict, max_value: int) -> dict:
    distribution_values = {
        parse_value_key(k, max_value) for k in (distribution or {})
    }
    rare_counts = {}
    for key, spec in rare_types.items():
        value, count = _rare_spec(key, spec, max_value)
        if value in distribution_values:
            raise ValueError(
                f"value {value} appears in both {_RARE_FIELD_NAME} and "
                "eligible_eqp_count_distribution; a value cannot be in both"
            )
        if value in rare_counts:
            raise ValueError(
                f"value {value} appears more than once in {_RARE_FIELD_NAME} "
                "(possibly under different key spellings, e.g. \"5\" and \"05\")"
            )
        rare_counts[value] = count
    return rare_counts


def allocate_rare_and_distribution_targets(
    rare_types: dict, distribution: dict, lot_count: int, rng: random.Random, *,
    max_value: int,
) -> list:
    """rare_types(각 값 -> {"min_count":..,"max_count":..})가 만드는
    절대 건수 배정과, distribution(T015 형식)이 "나머지"에 만드는
    비율 배정을 합쳐 길이 lot_count짜리 목표 리스트를 만든다(순서는
    뒤섞임). distribution이 주어지면 나머지가 0이어도 그 구조(비율
    합=1, 키 형식 등)를 검증한다."""
    if not isinstance(rare_types, dict) or not rare_types:
        raise ValueError(f"{_RARE_FIELD_NAME} must be a non-empty object")

    rare_counts = _collect_rare_counts(rare_types, distribution, max_value)
    total_rare = sum(rare_counts.values())
    remaining = lot_count - total_rare
    if remaining < 0:
        raise ValueError(
            f"{_RARE_FIELD_NAME} alone needs {total_rare} lots, "
            f"exceeding the lot count ({lot_count})"
        )

    if distribution:
        dist_targets = allocate_target_counts(distribution, remaining, rng, max_value=max_value)
    elif remaining > 0:
        raise ValueError(
            f"{remaining} lots remain after {_RARE_FIELD_NAME} but no "
            "eligible_eqp_count_distribution was given to fill them"
        )
    else:
        dist_targets = []

    rare_targets = []
    for value, count in rare_counts.items():
        rare_targets.extend([value] * count)

    combined = rare_targets + dist_targets
    rng.shuffle(combined)
    return combined


def generate_lot_data_with_rare_types(
    config: dict, *, process_ids: list, step_ids: list, eqp_step_rows: list,
    rare_types: dict, distribution: dict = None, rng: random.Random = None,
) -> dict:
    """rng를 안 넘기면 이 함수가 새 random.Random(config["seed"])을 만든다 —
    단독/테스트 호출용 편의이며, 실제 파이프라인은 앞 단계가 쓰던 rng를
    그대로 이어받아 넘긴다."""
    check_process_and_step_ids(process_ids, step_ids)
    if rng is None:
        rng = random.Random(config["seed"])

    lot_count = effective_lot_count(config)
    eqp_count = config["scale"]["eqp_count"]
    targets = allocate_rare_and_distribution_targets(
        rare_types, distribution or {}, lot_count, rng, max_value=eqp_count
    )
    lots = lots_from_targets(
        targets, process_ids=process_ids, step_ids=step_ids,
        eqp_step_rows=eqp_step_rows, rng=rng,
    )
    return {"lot_data": lots}
