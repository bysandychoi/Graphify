"""T015: config.md의 case_ratios.eligible_eqp_count_distribution에
맞춰 lot별 eligible_eqp_count(할당 가능 설비 수)가 다양하게 분포하도록
lot_data를 생성한다.

T014(generator/lot_data.py)의 generate_lot_data는 lot마다 무작위로
고른 (process,step) 조합이 우연히 제공하는 eligible_eqp_count를 그대로
쓴다 — 그 값의 분포는 eqp_step 생성 결과에 좌우될 뿐 config로 조절할
수 없다. 이 모듈은 그 위에서, lot마다 목표 eligible_eqp_count를 먼저
정한 뒤(설정된 비율대로), 그 목표를 만족하는 (process,step)을 찾아
후보를 그 개수만큼만 남기고 나머지는 버린다 — eqp를 무작위로
골라내고, 그 eqp가 포함된 쌍만 candidate_pairs에 남긴다(암시된 쌍을
새로 만들지 않는다, T014와 동일한 제약).

**T014의 "(process,step) 조인과 정확히 일치" 근거가 이 모듈에서는
더 이상 성립하지 않는다** — 목표 개수만큼 eqp를 골라내고 나머지를
버리므로, 이 모듈이 만드는 candidate_pairs는 그 (process,step)이
실제로 제공하는 전체 쌍의 **진부분집합**이다. 두 조인 해석(step_id
단독 / (process,step) 조합) 중 어느 쪽과도 모순되지 않는다는 결론
자체는 진부분집합이어도 그대로 유지된다(전체 집합의 부분집합은 항상
두 해석의 부분집합이기도 하다).

목표 개수 배정은 **최대 잔여법(largest remainder method)** 을 쓴다 —
각 카테고리의 "정확한 몫"(비율×유효 lot 수)을 내림해서 기본 배정을
하고, 남는 lot 수만큼 소수부가 큰 카테고리부터 하나씩 더 준다. 이
방식은 항상 합이 정확히 유효 lot 수가 되고 음수가 나올 수 없다(이전
버전의 "가장 큰 카테고리에서 diff만큼 빼거나 더한다"는 방식은 카테고리
수가 lot 수보다 많을 때 그 카테고리를 음수로 만들 수 있었고, 나머지를
한 카테고리에 몰아 히스토그램을 붕괴시킬 수 있었다 — 둘 다 이 방식은
구조적으로 발생하지 않는다). 동점(소수부가 같음)은 값이 작은
카테고리부터 우선한다 — dict/JSON 키 순서에 의존하지 않는 고정
규칙이라, 같은 분포를 어떤 키 순서로 적어도 같은 seed에서 같은
결과가 나온다.

**주의 (T017 관련):** 이 함수는 유효 lot 수 **전부**를
`eligible_eqp_count_distribution`에 배정한다. config.md는 이후
`rare_eligible_eqp_count_types`(T017)가 일부 값을 절대 건수로 먼저
떼어가고 "나머지"만 이 분포가 배정한다고 정했다 — 그 분리는 아직
구현하지 않았다. T017을 구현할 때 이 함수(또는 그 앞단)를 바꿔
`rare_eligible_eqp_count_types`가 차지한 lot 수만큼 뺀 "나머지 lot
수"를 여기 넘기도록 해야 한다.
"""
import re
import random

from generator._util import LOT_ID_WIDTH, check_no_duplicates, effective_lot_count, scaled_count
from generator.lot_data import build_candidate_pairs

_VALUE_KEY_RE = re.compile(r"^[0-9]+$")


def _parse_value_key(key, max_value: int) -> int:
    if not isinstance(key, str) or not _VALUE_KEY_RE.fullmatch(key):
        raise ValueError(
            f"eligible_eqp_count_distribution key must be a non-negative decimal "
            f"integer string, got {key!r}"
        )
    value = int(key)
    if value > max_value:
        raise ValueError(
            f"eligible_eqp_count_distribution key {value} exceeds scale.eqp_count ({max_value})"
        )
    return value


def allocate_target_counts(
    distribution: dict, lot_count: int, rng: random.Random, *, max_value: int
) -> list:
    """{"1": 0.2, "2": 0.6, "3": 0.2} 같은 분포를 받아, 길이가
    lot_count인 목표 eligible_eqp_count 리스트를 만든다(순서는 뒤섞임).
    비율 합은 1이어야 한다(config.md 정적 검증과 같은 기준). 배정
    방식은 이 모듈 docstring의 "최대 잔여법" 참고."""
    if not distribution:
        raise ValueError("distribution must not be empty")
    ratio_sum = sum(distribution.values())
    if abs(ratio_sum - 1.0) > 1e-9:
        raise ValueError(f"distribution ratios must sum to 1, got {ratio_sum}")

    from decimal import Decimal  # pylint: disable=import-outside-toplevel

    exact = {}
    for key, ratio in distribution.items():
        value = _parse_value_key(key, max_value)
        if ratio < 0:
            raise ValueError(f"ratio for {key!r} must be >= 0, got {ratio}")
        exact[value] = Decimal(str(lot_count)) * Decimal(str(ratio))

    floor_counts = {value: int(amount) for value, amount in exact.items()}
    remainder = lot_count - sum(floor_counts.values())
    fractional_order = sorted(
        exact.keys(), key=lambda v: (-(exact[v] - floor_counts[v]), v)
    )
    targets = dict(floor_counts)
    for value in fractional_order[:remainder]:
        targets[value] += 1

    allocation = []
    for value in sorted(targets):
        allocation.extend([value] * targets[value])
    rng.shuffle(allocation)
    return allocation


def _build_pairs_cache(process_ids: list, step_ids: list, eqp_step_rows: list) -> dict:
    # (process,step) 조합별 candidate_pairs를 한 번만 계산해 재사용한다
    # — lot마다 다시 계산하면 lot 수 x 조합 수만큼 eqp_step_rows를
    # 훑게 되어 대규모 데이터에서 매우 느려진다(리뷰에서 실측: 3,000
    # 조합 x lot 10,000에서 50초 이상).
    return {
        (p, s): build_candidate_pairs(p, s, eqp_step_rows)
        for p in process_ids for s in step_ids
    }


def _make_lot_for_target(
    target: int, step_ids: list, pairs_cache: dict, qualifying_cache: dict, rng: random.Random
):
    if target == 0:
        # eligible_eqp_count == 0인 lot(problem.md 7절 "빈 가능 쌍").
        # eqp_step.py는 모든 (process,step)에 최소 1행을 만들므로, 이
        # lot이 가리키는 step은 항상 "사양에는 있지만 이 lot은 쓰지
        # 않는" 상태다 — lot_data.md가 빈 candidate_pairs를 유효한
        # 값으로 인정하므로 스키마 위반은 아니다.
        return rng.choice(step_ids), []

    if target not in qualifying_cache:
        qualifying_cache[target] = [
            combo for combo, pairs in pairs_cache.items()
            if len({p["eqp"] for p in pairs}) >= target
        ]
    combos = qualifying_cache[target]
    if not combos:
        raise ValueError(
            f"no (process, step) combination in eqp_step provides "
            f"eligible_eqp_count >= {target}; "
            "case_ratios.eligible_eqp_count_distribution asks for a value "
            "eqp_step cannot supply"
        )
    process_id, step_id = rng.choice(combos)
    full_pairs = pairs_cache[(process_id, step_id)]
    unique_eqp = sorted({p["eqp"] for p in full_pairs})
    chosen = set(rng.sample(unique_eqp, target))
    return step_id, [p for p in full_pairs if p["eqp"] in chosen]


def generate_lot_data_with_distribution(
    config: dict, *, process_ids: list, step_ids: list, eqp_step_rows: list,
    distribution: dict, rng: random.Random = None,
) -> dict:
    """rng를 안 넘기면 이 함수가 새 random.Random(config["seed"])을 만든다 —
    단독/테스트 호출용 편의이며, 실제 파이프라인은 앞 단계가 쓰던 rng를
    그대로 이어받아 넘긴다."""
    if not process_ids:
        raise ValueError("process_ids must not be empty")
    if not step_ids:
        raise ValueError("step_ids must not be empty")
    check_no_duplicates(process_ids, "process_ids")
    check_no_duplicates(step_ids, "step_ids")
    if rng is None:
        rng = random.Random(config["seed"])

    lot_count = effective_lot_count(config)
    eqp_count = config["scale"]["eqp_count"]
    targets = allocate_target_counts(distribution, lot_count, rng, max_value=eqp_count)
    pairs_cache = _build_pairs_cache(process_ids, step_ids, eqp_step_rows)
    qualifying_cache = {}

    lots = []
    for i, target in enumerate(targets, start=1):
        step_id, pairs = _make_lot_for_target(
            target, step_ids, pairs_cache, qualifying_cache, rng
        )
        lots.append({
            "lot_id": f"LOT_V{i:0{LOT_ID_WIDTH}d}",
            "current_step": step_id,
            "candidate_pairs": pairs,
            "attributes": {},
        })
    return {"lot_data": lots}
